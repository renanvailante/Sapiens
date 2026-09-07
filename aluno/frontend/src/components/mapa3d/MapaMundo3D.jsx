import { Suspense, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { Billboard, Text } from "@react-three/drei";
import Terreno from "./Terreno";
import NoHabilidade3D from "./NoHabilidade3D";
import Aresta3D from "./Aresta3D";
import Balao3D from "./Balao3D";
import CameraRig from "./CameraRig";
import { construirCena, construirBaloes } from "./sceneBuilder";

/** Substitui o `MapaCanvas` SVG: mesmas props (`biomas, nodeIndex, arestas,
 * onClickHab`) + `focusHabId`/`onFecharFoco`, derivadas do MESMO estado que
 * já controla o painel na página — nenhum estado novo em `TreinoHabilidades`. */
export default function MapaMundo3D({ biomas, nodeIndex, arestas, onClickHab, focusHabId, onFecharFoco }) {
  const { nos, arestas: arestasCena, biomaAnchors } = useMemo(
    () => construirCena({ biomas, arestas }, nodeIndex),
    [biomas, arestas, nodeIndex],
  );
  const baloes = useMemo(() => construirBaloes({ biomas }, nos), [biomas, nos]);
  const noFocado = focusHabId ? nos.find((n) => n.hab_id === focusHabId) : null;

  return (
    <div
      className="relative rounded-3xl overflow-hidden border border-white/10"
      style={{ height: "72vh", minHeight: 480, background: "#03060d" }}
      data-testid="mapa-mundo-3d"
    >
      <Canvas
        shadows
        camera={{ fov: 42, near: 0.1, far: 220 }}
        dpr={[1, 1.75]}
        onPointerMissed={() => { if (focusHabId) onFecharFoco?.(); }}
      >
        <color attach="background" args={["#03060d"]} />
        <fog attach="fog" args={["#03060d", 65, 170]} />
        <hemisphereLight args={["#6FA8FF", "#03060d", 0.7]} />
        <ambientLight intensity={0.28} />
        <directionalLight
          position={[22, 30, 14]}
          intensity={1.3}
          color="#EAF4FF"
          castShadow
          shadow-mapSize-width={1024}
          shadow-mapSize-height={1024}
          shadow-camera-left={-45}
          shadow-camera-right={45}
          shadow-camera-top={35}
          shadow-camera-bottom={-35}
          shadow-camera-far={90}
        />

        <Suspense fallback={null}>
          <Terreno />

          {arestasCena.map((a) => (
            <Aresta3D key={a.id} aresta={a} />
          ))}

          {nos.map((n) => (
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

          {biomaAnchors.map((b) => (
            <Billboard key={b.biomaId} position={b.position}>
              <Text
                fontSize={0.5}
                color="#E8F2FF"
                fillOpacity={0.4}
                letterSpacing={0.08}
                anchorX="center"
                anchorY="middle"
              >
                {b.nome.toUpperCase()}
              </Text>
            </Billboard>
          ))}
        </Suspense>

        <CameraRig focoPosicao={noFocado?.position ?? null} />
      </Canvas>
    </div>
  );
}
