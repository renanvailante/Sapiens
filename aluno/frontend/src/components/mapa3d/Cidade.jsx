import { useLayoutEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { BIOMA_ARCHETYPES } from "./biomaArchetypes";

// Renderiza a cidade inteira com `InstancedMesh`: as ~1.5k peças viram
// algumas dezenas de chamadas de desenho, agrupadas por (distrito × tom ×
// forma). Sem isso, cada arco/degrau/janela seria um mesh próprio e o mapa
// não sustentaria a densidade que a arquitetura exige.
//
// `flatShading` é deliberado: é o que dá a leitura de massa chapada, com as
// três faces de um volume em três valores distintos — a gramática visual de
// Monument Valley, e o que faz volume ser lido sem textura nenhuma.

const MATERIAL_POR_TOM = {
  claro: { roughness: 0.6, metalness: 0.05, emissiva: 0, sombra: true },
  medio: { roughness: 0.72, metalness: 0.06, emissiva: 0, sombra: true },
  escuro: { roughness: 0.86, metalness: 0.03, emissiva: 0, sombra: true },
  brilho: { roughness: 0.32, metalness: 0, emissiva: 1.8, sombra: false },
  brilhoFraco: { roughness: 0.45, metalness: 0, emissiva: 0.5, sombra: false },
};

function corDaPeca(biomaId, tom) {
  const paleta = BIOMA_ARCHETYPES[biomaId]?.paleta ?? BIOMA_ARCHETYPES.perceber.paleta;
  if (tom === "brilho" || tom === "brilhoFraco") return paleta.brilho;
  return paleta[tom] ?? paleta.medio;
}

function Geometria({ forma }) {
  switch (forma) {
    case "cilindro":
      return <cylinderGeometry args={[0.5, 0.5, 1, 16]} />;
    case "cone":
      return <coneGeometry args={[0.5, 1, 6]} />;
    case "anel":
      return <torusGeometry args={[0.5, 0.055, 8, 32]} />;
    default:
      return <boxGeometry args={[1, 1, 1]} />;
  }
}

function Grupo({ chave, forma, biomaId, tom, pecas }) {
  const ref = useRef();
  const config = MATERIAL_POR_TOM[tom];
  const cor = corDaPeca(biomaId, tom);

  useLayoutEffect(() => {
    const malha = ref.current;
    if (!malha) return;
    const matriz = new THREE.Matrix4();
    const quat = new THREE.Quaternion();
    // 'YXZ': primeiro a guinada (direção do vão), depois a inclinação —
    // é o que permite aduela de arco e montante de escada apontarem certo.
    const euler = new THREE.Euler(0, 0, 0, "YXZ");
    const pos = new THREE.Vector3();
    const escala = new THREE.Vector3();

    pecas.forEach((peca, i) => {
      euler.set(peca.rotX || 0, peca.rotY || 0, 0, "YXZ");
      quat.setFromEuler(euler);
      pos.set(peca.pos[0], peca.pos[1], peca.pos[2]);
      escala.set(peca.size[0], peca.size[1], peca.size[2]);
      matriz.compose(pos, quat, escala);
      malha.setMatrixAt(i, matriz);
    });
    malha.instanceMatrix.needsUpdate = true;
    malha.computeBoundingSphere();
  }, [pecas]);

  return (
    <instancedMesh
      key={chave}
      ref={ref}
      args={[undefined, undefined, pecas.length]}
      castShadow={config.sombra}
      receiveShadow={config.sombra}
      frustumCulled={false}
    >
      <Geometria forma={forma} />
      <meshStandardMaterial
        color={cor}
        emissive={config.emissiva > 0 ? cor : "#000000"}
        emissiveIntensity={config.emissiva}
        roughness={config.roughness}
        metalness={config.metalness}
        flatShading
      />
    </instancedMesh>
  );
}

export default function Cidade({ pecas }) {
  const grupos = useMemo(() => {
    const mapa = new Map();
    for (const peca of pecas) {
      const chave = `${peca.bioma}:${peca.tom}:${peca.forma}`;
      let grupo = mapa.get(chave);
      if (!grupo) {
        grupo = { chave, biomaId: peca.bioma, tom: peca.tom, forma: peca.forma, pecas: [] };
        mapa.set(chave, grupo);
      }
      grupo.pecas.push(peca);
    }
    return [...mapa.values()];
  }, [pecas]);

  return (
    <group>
      {grupos.map((g) => (
        <Grupo key={g.chave} chave={g.chave} forma={g.forma} biomaId={g.biomaId} tom={g.tom} pecas={g.pecas} />
      ))}
    </group>
  );
}
