import { useMemo } from "react";
import * as THREE from "three";
import { elevationAt, pesosBioma, WORLD_WIDTH, WORLD_DEPTH } from "./sceneBuilder";
import { BIOMA_ARCHETYPES } from "./biomaArchetypes";

// Resolução baixa de propósito: ~10.6k vértices bastam pra estética de
// "mundo matemático" (superfícies limpas, não terreno fotorrealista) e
// mantêm o custo de montagem (uma vez, não por frame) desprezível.
const SEG_X = 128;
const SEG_Z = 82;

export default function Terreno() {
  const geometria = useMemo(() => {
    const geo = new THREE.PlaneGeometry(WORLD_WIDTH, WORLD_DEPTH, SEG_X, SEG_Z);
    geo.rotateX(-Math.PI / 2);
    const pos = geo.attributes.position;
    const cores = new Float32Array(pos.count * 3);
    const cor1 = new THREE.Color();
    const cor2 = new THREE.Color();
    const cor = new THREE.Color();
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);
      pos.setY(i, elevationAt(x, z));
      // Cor é blendada pelo MESMO peso da elevação — fronteira entre biomas
      // é uma transição suave, nunca um corte duro (Voronoi).
      const { id1, id2, w1, w2 } = pesosBioma(x, z);
      cor1.set(BIOMA_ARCHETYPES[id1].tint.deep);
      cor2.set(BIOMA_ARCHETYPES[id2].tint.deep);
      cor.copy(cor1).lerp(cor2, w2);
      cores[i * 3] = cor.r;
      cores[i * 3 + 1] = cor.g;
      cores[i * 3 + 2] = cor.b;
    }
    geo.setAttribute("color", new THREE.BufferAttribute(cores, 3));
    geo.computeVertexNormals();
    return geo;
  }, []);

  return (
    <mesh geometry={geometria} receiveShadow>
      <meshStandardMaterial vertexColors roughness={0.78} metalness={0.06} />
    </mesh>
  );
}
