import { useMemo } from "react";
import * as THREE from "three";

/** Uma relação = um caminho/ponte elevada, nunca uma linha achatada — pra
 * valer como paisagem, não como grafo redesenhado em 3D. Visível só quando
 * as duas pontas já são != "unknown" (mesma regra do mapa SVG anterior);
 * opacidade/emissive pela mesma escala de "peso" de sempre. Só `relation ===
 * "prerequisito"` ganha o motivo de portão — puramente visual, nunca torna o
 * nó de destino de fato inclicável (o backend nunca bloqueou nada aqui). */
export default function Aresta3D({ aresta }) {
  const curva = useMemo(() => {
    const [x1, y1, z1] = aresta.from;
    const [x2, y2, z2] = aresta.to;
    const meio = new THREE.Vector3((x1 + x2) / 2, Math.max(y1, y2) + 1.3, (z1 + z2) / 2);
    return new THREE.CatmullRomCurve3([
      new THREE.Vector3(x1, y1 + 0.05, z1),
      meio,
      new THREE.Vector3(x2, y2 + 0.05, z2),
    ]);
  }, [aresta.from, aresta.to]);

  const geometria = useMemo(() => new THREE.TubeGeometry(curva, 20, 0.12, 6, false), [curva]);

  const ehPrerequisito = aresta.relation === "prerequisito";
  const selado = ehPrerequisito && !aresta.sourceMastered;
  const opacidade = (selado ? 0.35 : 1) * (0.35 + aresta.peso * 0.65);

  return (
    <>
      <mesh geometry={geometria}>
        <meshStandardMaterial
          color={selado ? "#1a2438" : "#9fd3ff"}
          emissive={selado ? "#000000" : "#4FD9FF"}
          emissiveIntensity={selado ? 0 : aresta.peso * 0.8}
          transparent
          opacity={opacidade}
          roughness={0.5}
        />
      </mesh>
      {ehPrerequisito && <PortalPrerequisito curva={curva} selado={selado} />}
    </>
  );
}

function PortalPrerequisito({ curva, selado }) {
  const { p1, p2, topo } = useMemo(() => {
    const ponto = curva.getPointAt(0.28);
    const tangente = curva.getTangentAt(0.28);
    const perpendicular = new THREE.Vector3(-tangente.z, 0, tangente.x).normalize();
    return {
      p1: ponto.clone().add(perpendicular.clone().multiplyScalar(0.32)),
      p2: ponto.clone().add(perpendicular.clone().multiplyScalar(-0.32)),
      topo: ponto,
    };
  }, [curva]);

  const emissivo = selado ? "#000000" : "#4FD9FF";
  const intensidade = selado ? 0 : 0.6;

  return (
    <group>
      <mesh position={[p1.x, p1.y + 0.45, p1.z]}>
        <boxGeometry args={[0.1, 0.9, 0.1]} />
        <meshStandardMaterial color="#2b3a5c" emissive={emissivo} emissiveIntensity={intensidade} />
      </mesh>
      <mesh position={[p2.x, p2.y + 0.45, p2.z]}>
        <boxGeometry args={[0.1, 0.9, 0.1]} />
        <meshStandardMaterial color="#2b3a5c" emissive={emissivo} emissiveIntensity={intensidade} />
      </mesh>
      <mesh position={[topo.x, topo.y + 0.92, topo.z]}>
        <boxGeometry args={[0.78, 0.12, 0.12]} />
        <meshStandardMaterial color="#2b3a5c" emissive={emissivo} emissiveIntensity={intensidade} />
      </mesh>
      {selado && (
        <mesh position={[topo.x, topo.y + 0.45, topo.z]}>
          <planeGeometry args={[0.6, 0.85]} />
          <meshStandardMaterial color="#0a0f1c" transparent opacity={0.82} side={THREE.DoubleSide} />
        </mesh>
      )}
    </group>
  );
}
