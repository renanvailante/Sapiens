import { Suspense, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import * as THREE from "three";
import Cidade from "./Cidade";
import NoHabilidade3D from "./NoHabilidade3D";
import CameraRig from "./CameraRig";
import { construirCena } from "./sceneBuilder";
import { construirCidade } from "./arquitetura";

const COR_ABISMO = "#04070f";

/** Camadas horizontais quase transparentes preenchendo o vazio entre as
 * ilhas: é o que faz o abismo ter profundidade em vez de ser buraco preto, e
 * o que sugere que o arquipélago continua além do que se vê. */
function NevoaDoAbismo({ raio }) {
  const camadas = useMemo(
    () => [
      { y: -60, opacidade: 0.2 },
      { y: -40, opacidade: 0.17 },
      { y: -24, opacidade: 0.14 },
      { y: -12, opacidade: 0.1 },
      { y: 2, opacidade: 0.07 },
      { y: 18, opacidade: 0.05 },
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
        <directionalLight
          position={[raio * 0.6, raio * 0.9, raio * 0.45]}
          intensity={1.7}
          color="#F6FAFF"
          castShadow
          shadow-mapSize-width={2048}
          shadow-mapSize-height={2048}
          shadow-camera-left={-raio}
          shadow-camera-right={raio}
          shadow-camera-top={raio}
          shadow-camera-bottom={-raio}
          shadow-camera-near={1}
          shadow-camera-far={raio * 4}
          shadow-bias={-0.0008}
        />
        <directionalLight position={[-raio * 0.7, raio * 0.4, -raio * 0.6]} intensity={0.36} color="#FFD9BE" />
        <directionalLight position={[-raio * 0.4, raio * 0.6, raio]} intensity={0.45} color="#CFE1FF" />

        <Suspense fallback={null}>
          <NevoaDoAbismo raio={raio} />
          <Cidade pecas={pecas} />

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
