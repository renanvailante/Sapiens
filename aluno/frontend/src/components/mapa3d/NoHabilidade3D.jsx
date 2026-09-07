import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Text } from "@react-three/drei";
import { BIOMA_ARCHETYPES, ESTADO_TIER } from "./biomaArchetypes";
import { hash01 } from "./noise";

// Geometria por bioma — sempre primitiva do Three.js (caixa, cone, octaedro,
// cilindro, toro), nunca um asset `.glb`: mantém o pipeline em zero e a
// estética "mundo matemático" (formas limpas, não modelos esculpidos).
function Geometria({ tipo }) {
  switch (tipo) {
    case "disc-ring":
      return <cylinderGeometry args={[0.55, 0.62, 0.12, 28]} />;
    case "stepped-block":
      return <boxGeometry args={[0.7, 0.9, 0.7]} />;
    case "crystal-prism":
      return <octahedronGeometry args={[0.62, 0]} />;
    case "obelisk":
      return <coneGeometry args={[0.42, 1.5, 6]} />;
    case "hub-node":
      return <torusGeometry args={[0.5, 0.16, 12, 28]} />;
    case "tribunal-block":
      return <cylinderGeometry args={[0.6, 0.75, 0.55, 8]} />;
    default:
      return <boxGeometry args={[0.6, 0.6, 0.6]} />;
  }
}

/** Uma habilidade = um ponto de interesse no mundo. Nunca renderiza
 * `hab_id`/código de ontologia — só `no.nome` (já é uma frase em português)
 * no label de hover, exatamente como o mapa SVG anterior. */
export default function NoHabilidade3D({ no, selecionado, onClickHab }) {
  const arquetipo = BIOMA_ARCHETYPES[no.biomaId];
  const tier = ESTADO_TIER[no.estado];
  const [hover, setHover] = useState(false);
  const meshRef = useRef();
  const rotBase = useMemo(() => hash01(no.hab_id) * Math.PI * 2, [no.hab_id]);

  useFrame((state) => {
    if (!meshRef.current) return;
    const t = state.clock.elapsedTime;
    const pulso = tier.pulse ? 1 + Math.sin(t * 2.2 + rotBase) * 0.06 : 1;
    const destaque = selecionado ? 1.18 : hover ? 1.08 : 1;
    meshRef.current.scale.setScalar(tier.scale * pulso * destaque);
  });

  if (!tier) return null; // guarda equivalente ao `!cor` do SVG antigo

  const mostrarLabel = (hover || selecionado) && tier.label;

  return (
    <group position={no.position}>
      <mesh
        ref={meshRef}
        rotation={[0, rotBase, 0]}
        castShadow
        receiveShadow
        onClick={(e) => {
          e.stopPropagation();
          onClickHab(no.hab_id);
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHover(true);
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          setHover(false);
          document.body.style.cursor = "auto";
        }}
      >
        <Geometria tipo={arquetipo.nodeGeometry} />
        <meshStandardMaterial
          color={tier.emissiveIntensity > 0 ? arquetipo.tint.base : arquetipo.tint.deep}
          emissive={arquetipo.tint.emissive}
          emissiveIntensity={tier.emissiveIntensity * (selecionado ? 1.4 : 1)}
          roughness={0.35}
          metalness={0.3}
          transparent={tier.opacity < 1}
          opacity={tier.opacity}
        />
      </mesh>

      {selecionado && (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.03, 0]}>
          <ringGeometry args={[0.78, 0.92, 32]} />
          <meshBasicMaterial color={arquetipo.tint.base} transparent opacity={0.7} />
        </mesh>
      )}

      {mostrarLabel && (
        <Text
          position={[0, 1.35, 0]}
          fontSize={0.26}
          color="#E8F2FF"
          anchorX="center"
          anchorY="bottom"
          outlineWidth={0.02}
          outlineColor="#03060d"
          maxWidth={3}
          textAlign="center"
        >
          {no.nome.length > 40 ? `${no.nome.slice(0, 39)}…` : no.nome}
        </Text>
      )}
    </group>
  );
}
