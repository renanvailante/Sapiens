import { useLayoutEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { hash01 } from "./noise";

// O céu do continente: nuvens à deriva e revoadas de aves. São elementos de
// ATMOSFERA, não de informação — nada aqui é clicável, nada carrega estado, e
// nada deve competir com a paisagem. O que eles entregam é escala: quando há
// algo se movendo devagar no ar, o mundo parado embaixo parece grande.
//
// Ambos são instanciados e animados por matriz: dezenas de corpos custam uma
// chamada de desenho cada grupo.

const COR_NUVEM = "#93B4E0";
const COR_AVE = "#BBD2EE";

/** Nuvens: aglomerados de blocos achatados que atravessam o mundo devagar e
 * reaparecem do outro lado. A deriva é lenta de propósito — nuvem rápida lê
 * como fumaça e chama atenção para si. */
export function Nuvens({ raio }) {
  const ref = useRef();
  const alcance = raio * 1.5;

  const blocos = useMemo(() => {
    const lista = [];
    const nuvens = 18;
    for (let n = 0; n < nuvens; n++) {
      const g = (k) => hash01(`nuvem:${n}:${k}`);
      const base = {
        x: (g("x") - 0.5) * alcance * 2,
        y: raio * 0.34 + g("y") * raio * 0.45,
        z: (g("z") - 0.5) * alcance * 2,
        escala: 0.45 + g("e") * 0.85,
        deriva: 3 + g("d") * 5,
      };
      const partes = 3 + Math.floor(g("p") * 3);
      for (let i = 0; i < partes; i++) {
        const h = (k) => hash01(`nuvem:${n}:${i}:${k}`);
        lista.push({
          ...base,
          dx: (h("dx") - 0.5) * 190 * base.escala,
          dy: (h("dy") - 0.5) * 34 * base.escala,
          dz: (h("dz") - 0.5) * 150 * base.escala,
          largura: (110 + h("w") * 160) * base.escala,
          altura: (26 + h("a") * 30) * base.escala,
          fundura: (95 + h("f") * 130) * base.escala,
          giro: h("g") * Math.PI,
        });
      }
    }
    return lista;
  }, [alcance, raio]);

  useLayoutEffect(() => {
    if (ref.current) ref.current.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  }, []);

  useFrame((state) => {
    const malha = ref.current;
    if (!malha) return;
    const t = state.clock.elapsedTime;
    const m = new THREE.Matrix4();
    const q = new THREE.Quaternion();
    const p = new THREE.Vector3();
    const e = new THREE.Vector3();

    blocos.forEach((b, i) => {
      // Deriva contínua com retorno pela outra borda: o céu não tem fim.
      const avanco = ((b.x + b.dx + t * b.deriva + alcance) % (alcance * 2)) - alcance;
      p.set(avanco, b.y + b.dy + Math.sin(t * 0.12 + i) * 4, b.z + b.dz);
      q.setFromEuler(new THREE.Euler(0, b.giro, 0));
      e.set(b.largura, b.altura, b.fundura);
      m.compose(p, q, e);
      malha.setMatrixAt(i, m);
    });
    malha.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={ref} args={[undefined, undefined, blocos.length]} frustumCulled={false}>
      <icosahedronGeometry args={[0.5, 1]} />
      <meshStandardMaterial
        color={COR_NUVEM}
        transparent
        opacity={0.11}
        depthWrite={false}
        roughness={1}
        flatShading
      />
    </instancedMesh>
  );
}

/** Aves: revoadas em formação, girando devagar sobre as ilhas. Cada ave é um
 * corpo pequeno e alongado que aponta para onde voa; a formação inteira
 * descreve um círculo largo, com leve sobe-e-desce. */
export function Aves({ ancoras }) {
  const ref = useRef();

  const { revoadas, total } = useMemo(() => {
    // Revoadas sobre as regiões MAIS revoadas soltas cruzando o vazio: o céu
    // precisa ter movimento em qualquer direção que o aluno olhe.
    const pontos = [...ancoras, ...ancoras.map((a, i) => ({
      x: a.x * 0.35 + (hash01(`vagante:${i}:x`) - 0.5) * 2600,
      z: a.z * 0.35 + (hash01(`vagante:${i}:z`) - 0.5) * 2600,
      y: a.y + 240,
    }))];
    const lista = pontos.map((a, i) => {
      const g = (k) => hash01(`revoada:${i}:${k}`);
      return {
        cx: a.x + (g("x") - 0.5) * 260,
        cz: a.z + (g("z") - 0.5) * 260,
        cy: a.y + 150 + g("y") * 220,
        raio: 260 + g("r") * 460,
        velocidade: 0.07 + g("v") * 0.06,
        fase: g("f") * Math.PI * 2,
        aves: 6 + Math.floor(g("n") * 5),
      };
    });
    return { revoadas: lista, total: lista.reduce((acc, r) => acc + r.aves, 0) };
  }, [ancoras]);

  useLayoutEffect(() => {
    if (ref.current) ref.current.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  }, []);

  useFrame((state) => {
    const malha = ref.current;
    if (!malha) return;
    const t = state.clock.elapsedTime;
    const m = new THREE.Matrix4();
    const q = new THREE.Quaternion();
    const euler = new THREE.Euler(0, 0, 0, "YXZ");
    const p = new THREE.Vector3();
    const e = new THREE.Vector3();

    let i = 0;
    for (const r of revoadas) {
      const angulo = r.fase + t * r.velocidade;
      for (let k = 0; k < r.aves; k++) {
        // Formação em V: cada ave fica um pouco atrás e ao lado da anterior.
        const fila = Math.ceil(k / 2);
        const lado = k % 2 === 0 ? 1 : -1;
        const atraso = fila * 0.028;
        const a = angulo - atraso;
        const raioAve = r.raio + (k === 0 ? 0 : lado * fila * 13);
        p.set(
          r.cx + Math.cos(a) * raioAve,
          r.cy + Math.sin(t * 0.5 + k * 0.7) * 12,
          r.cz + Math.sin(a) * raioAve,
        );
        // Aponta na direção do voo e inclina levemente na curva.
        euler.set(Math.sin(t * 2.4 + k) * 0.12, -a + Math.PI / 2, 0, "YXZ");
        q.setFromEuler(euler);
        // A batida de asa é a variação da envergadura, não uma animação nova.
        const envergadura = 24 + Math.sin(t * 5.5 + k * 1.3) * 9;
        e.set(envergadura, 4.5, 10);
        m.compose(p, q, e);
        malha.setMatrixAt(i, m);
        i += 1;
      }
    }
    malha.instanceMatrix.needsUpdate = true;
  });

  if (!total) return null;

  return (
    <instancedMesh ref={ref} args={[undefined, undefined, total]} frustumCulled={false}>
      <octahedronGeometry args={[0.5, 0]} />
      <meshStandardMaterial color={COR_AVE} roughness={0.7} emissive={COR_AVE} emissiveIntensity={0.06} flatShading />
    </instancedMesh>
  );
}
