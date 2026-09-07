import { Suspense, useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Billboard, Text } from "@react-three/drei";
import * as THREE from "three";
import Cidade from "./Cidade";
import NoHabilidade3D from "./NoHabilidade3D";
import Balao3D from "./Balao3D";
import CameraRig from "./CameraRig";
import { construirCena, construirBaloes } from "./sceneBuilder";
import { construirCidade } from "./arquitetura";
import { BIOMA_ARCHETYPES } from "./biomaArchetypes";

/** Nome do distrito pairando sobre o landmark. Mesma regra dos balões: some
 * de perto, porque em coordenadas de mundo o texto cresce até cobrir a
 * arquitetura que ele deveria estar nomeando. */
function RotuloDistrito({ ancora }) {
  const ref = useRef();
  useFrame((state) => {
    const grupo = ref.current;
    if (!grupo) return;
    grupo.visible = state.camera.position.distanceTo(grupo.position) > 34;
  });
  return (
    <Billboard ref={ref} position={ancora.position}>
      <Text
        fontSize={0.78}
        color={BIOMA_ARCHETYPES[ancora.biomaId].paleta.claro}
        fillOpacity={0.5}
        letterSpacing={0.22}
        anchorX="center"
        anchorY="middle"
      >
        {ancora.nome.toUpperCase()}
      </Text>
    </Billboard>
  );
}

/** Substitui o `MapaCanvas` SVG: mesmas props (`biomas, nodeIndex, arestas,
 * onClickHab`) + `focusHabId`/`onFecharFoco`, derivadas do MESMO estado que
 * já controla o painel na página — nenhum estado novo em `TreinoHabilidades`. */
export default function MapaMundo3D({ biomas, nodeIndex, arestas, onClickHab, focusHabId, onFecharFoco }) {
  const cena = useMemo(
    () => construirCena({ biomas, arestas }, nodeIndex),
    [biomas, arestas, nodeIndex],
  );
  const pecas = useMemo(() => construirCidade(cena), [cena]);
  const baloes = useMemo(() => construirBaloes({ biomas }, cena.nosVisiveis), [biomas, cena]);
  const noFocado = focusHabId ? cena.nos.find((n) => n.hab_id === focusHabId) : null;

  return (
    <div
      className="relative rounded-3xl overflow-hidden border border-white/10"
      style={{ height: "72vh", minHeight: 480, background: "#03060d" }}
      data-testid="mapa-mundo-3d"
    >
      <Canvas
        shadows
        camera={{ fov: 40, near: 0.1, far: 300 }}
        dpr={[1, 1.75]}
        // Sem tone mapping filmico: a estética é de cor chapada, e o ACES
        // dessatura justamente os tons médios que carregam a identidade de
        // cada distrito.
        gl={{ toneMapping: THREE.NoToneMapping, antialias: true }}
        onPointerMissed={() => {
          if (focusHabId) onFecharFoco?.();
        }}
      >
        <color attach="background" args={["#03060d"]} />
        {/* A câmera de abertura fica a ~86 unidades: o fog precisa começar
            depois disso, senão lava a cidade inteira em vez de só afastar o
            horizonte. */}
        <fog attach="fog" args={["#05091a", 100, 240]} />

        {/* Luz é informação: a chave fria modela a massa, a hemisférica
            devolve o azul do ambiente nas faces em sombra, e um rim quente
            muito fraco desenha a aresta oposta — é o contraste que faz a
            arquitetura ler como volume, sem introduzir âmbar como cor de
            superfície (âmbar continua significando aviso no resto do app). */}
        <hemisphereLight args={["#7FA0E4", "#0A1024", 0.6]} />
        <ambientLight intensity={0.34} />
        <directionalLight
          position={[30, 38, 20]}
          intensity={1.25}
          color="#F4F8FF"
          castShadow
          shadow-mapSize-width={2048}
          shadow-mapSize-height={2048}
          shadow-camera-left={-55}
          shadow-camera-right={55}
          shadow-camera-top={45}
          shadow-camera-bottom={-45}
          shadow-camera-near={1}
          shadow-camera-far={130}
          shadow-bias={-0.0006}
        />
        <directionalLight position={[-28, 16, -24]} intensity={0.34} color="#FFD9BE" />
        {/* Preenchimento vindo de trás da câmera: sem ele as fachadas
            viradas para quem olha ficam quase pretas e a cidade lê como
            silhueta em vez de volume. */}
        <directionalLight position={[-18, 26, 42]} intensity={0.5} color="#CFE1FF" />

        <Suspense fallback={null}>
          <Cidade pecas={pecas} />

          {cena.nosVisiveis.map((n) => (
            <NoHabilidade3D
              key={n.hab_id}
              no={n}
              selecionado={n.hab_id === focusHabId}
              onClickHab={(habId) => onClickHab(nodeIndex[habId])}
            />
          ))}

          {baloes.map((b) => (
            <Balao3D key={b.id} balao={b} />
          ))}

          {cena.biomaAnchors.map((b) => (
            <RotuloDistrito key={b.biomaId} ancora={b} />
          ))}
        </Suspense>

        <CameraRig focoPosicao={noFocado?.position ?? null} />
      </Canvas>
    </div>
  );
}
