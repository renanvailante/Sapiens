import { Suspense, useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";
import Cidade from "./Cidade";
import NoHabilidade3D from "./NoHabilidade3D";
import CameraRig from "./CameraRig";
import { construirCena, ANCORA_MUNDO, BIOMA_IDS, alturaIlha } from "./sceneBuilder";
import { Nuvens, Aves } from "./Ceu";
import { construirCidade } from "./arquitetura";

const COR_ABISMO = "#04070f";

/** Camadas horizontais quase transparentes preenchendo o vazio entre as
 * ilhas: é o que faz o abismo ter profundidade em vez de ser buraco preto, e
 * o que sugere que o arquipélago continua além do que se vê. */
function NevoaDoAbismo({ raio }) {
  const camadas = useMemo(
    () => [
      { y: -260, opacidade: 0.2 },
      { y: -180, opacidade: 0.17 },
      { y: -110, opacidade: 0.14 },
      { y: -55, opacidade: 0.1 },
      { y: 10, opacidade: 0.07 },
      { y: 80, opacidade: 0.05 },
    ],
    [],
  );
  return (
    <group>
      {camadas.map((c) => (
        <mesh key={c.y} rotation={[-Math.PI / 2, 0, 0]} position={[0, c.y, 0]}>
          <circleGeometry args={[raio * 2.6, 72]} />
          <meshBasicMaterial
            color="#25406B"
            transparent
            opacity={c.opacidade}
            depthWrite={false}
            side={THREE.DoubleSide}
          />
        </mesh>
      ))}
    </group>
  );
}

/** O sol acompanha o ponto para onde a câmera olha, com o frustum de sombra
 * apertado em volta dele. Num continente desta escala, um shadow map único
 * cobrindo tudo daria menos de um texel por metro de terreno — a sombra
 * viraria mancha. Seguindo o alvo, a sombra é nítida onde se está olhando, e
 * o que fica longe já está dissolvido na névoa de qualquer jeito. */
function SolQueSegue({ raio }) {
  const luzRef = useRef();
  const alvoRef = useRef();
  const alvo = useMemo(() => new THREE.Vector3(), []);
  // Teto fixo: proporcional ao raio, um mundo enorme devolveria a sombra
  // borrada que o sol-que-segue existe justamente para evitar.
  const extensao = Math.min(340, Math.max(150, raio * 0.12));

  useFrame(({ controls }) => {
    const luz = luzRef.current;
    const objetoAlvo = alvoRef.current;
    if (!luz || !objetoAlvo) return;
    if (controls?.getTarget) controls.getTarget(alvo);
    luz.position.set(alvo.x + extensao * 1.1, alvo.y + extensao * 1.8, alvo.z + extensao * 0.85);
    objetoAlvo.position.copy(alvo);
    objetoAlvo.updateMatrixWorld();
    luz.target = objetoAlvo;
  });

  return (
    <>
      <object3D ref={alvoRef} />
      <directionalLight
        ref={luzRef}
        intensity={1.7}
        color="#F6FAFF"
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        shadow-camera-left={-extensao}
        shadow-camera-right={extensao}
        shadow-camera-top={extensao}
        shadow-camera-bottom={-extensao}
        shadow-camera-near={1}
        shadow-camera-far={extensao * 5}
        shadow-bias={-0.0012}
      />
    </>
  );
}

/** Mundo em sangria total — sem card, sem moldura, sem rótulo permanente.
 * Mesmas props de sempre (`biomas, nodeIndex, arestas, onClickHab`) +
 * `focusHabId`/`onFecharFoco`, derivadas do MESMO estado que já controla o
 * painel na página. */
export default function MapaMundo3D({ biomas, nodeIndex, arestas, onClickHab, focusHabId, onFecharFoco }) {
  const cena = useMemo(
    () => construirCena({ biomas, arestas }, nodeIndex),
    [biomas, arestas, nodeIndex],
  );
  const pecas = useMemo(() => construirCidade(cena), [cena]);
  const noFocado = focusHabId ? cena.nos.find((n) => n.hab_id === focusHabId) : null;
  const raio = cena.limites.raio;
  // As revoadas orbitam sobre as regiões — no vazio entre elas não haveria
  // nada para dar referência ao movimento.
  const ancorasDoCeu = useMemo(
    () => BIOMA_IDS.map((id) => ({ x: ANCORA_MUNDO[id].x, z: ANCORA_MUNDO[id].z, y: alturaIlha(id) })),
    [],
  );

  return (
    <div className="absolute inset-0" style={{ background: COR_ABISMO }} data-testid="mapa-mundo-3d">
      <Canvas
        shadows
        camera={{ fov: 42, near: 0.5, far: raio * 8 }}
        dpr={[1, 1.75]}
        // Sem tone mapping filmico: a estética é de cor chapada, e o ACES
        // dessatura justamente os neons que dão identidade a cada ilha.
        gl={{ toneMapping: THREE.NoToneMapping, antialias: true }}
        onPointerMissed={() => {
          if (focusHabId) onFecharFoco?.();
        }}
      >
        <color attach="background" args={[COR_ABISMO]} />
        {/* Névoa densa: as ilhas distantes se dissolvem, e o mundo passa a
            parecer maior do que o pedaço que cabe na tela. */}
        <fogExp2 attach="fog" args={["#0B1938", 0.3 / raio]} />

        <hemisphereLight args={["#8FB0F0", "#0A1024", 0.7]} />
        <ambientLight intensity={0.42} />
        <SolQueSegue raio={raio} />
        <directionalLight position={[-raio * 0.7, raio * 0.4, -raio * 0.6]} intensity={0.36} color="#FFD9BE" />
        <directionalLight position={[-raio * 0.4, raio * 0.6, raio]} intensity={0.45} color="#CFE1FF" />

        <Suspense fallback={null}>
          <NevoaDoAbismo raio={raio} />
          <Cidade pecas={pecas} />

          <Nuvens raio={raio} />
          <Aves ancoras={ancorasDoCeu} />

          {cena.nosVisiveis.map((n) => (
            <NoHabilidade3D
              key={n.hab_id}
              no={n}
              selecionado={n.hab_id === focusHabId}
              onClickHab={(habId) => onClickHab(nodeIndex[habId])}
            />
          ))}
        </Suspense>

        <CameraRig focoPosicao={noFocado?.position ?? null} raioMundo={raio} />
      </Canvas>
    </div>
  );
}
