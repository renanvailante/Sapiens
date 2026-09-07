import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Text } from "@react-three/drei";
import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { BIOMA_ARCHETYPES, ESTADO_TIER } from "./biomaArchetypes";
import { hash01 } from "./noise";

// Cada habilidade é o objeto que coroa o seu quarteirão — uma peça de
// arquitetura pequena, do vocabulário do distrito, não um marcador genérico.
// As formas são montadas UMA vez por tipo (merge de primitivas) e reusadas
// pelos 56 nós, com a base em y=0 para assentarem no pedestal.

// `mergeGeometries` devolve null se as partes não combinarem em índice e
// atributos — e as primitivas de poliedro (octaedro, icosaedro) nascem SEM
// índice enquanto caixa/cilindro/toro nascem COM. Normalizar tudo para não
// indexado é o que faz o merge valer para qualquer combinação de peças.
function montar(partes) {
  const normalizadas = partes.map((g) => (g.index ? g.toNonIndexed() : g));
  const geo = mergeGeometries(normalizadas, false) ?? normalizadas[0];
  geo.computeVertexNormals();
  return geo;
}

const GEOMETRIAS = {
  // Perceber — anel de observação sobre um disco raso.
  anel: () => {
    const disco = new THREE.CylinderGeometry(0.42, 0.5, 0.16, 20).translate(0, 0.08, 0);
    const aro = new THREE.TorusGeometry(0.52, 0.075, 10, 30).rotateX(Math.PI / 2).translate(0, 0.42, 0);
    const agulha = new THREE.ConeGeometry(0.11, 0.7, 8).translate(0, 0.5, 0);
    return montar([disco, aro, agulha]);
  },
  // Relacionar — pequena ziggurat: três lances que sobem em degrau.
  ziggurat: () => {
    const a = new THREE.BoxGeometry(1.0, 0.24, 1.0).translate(0, 0.12, 0);
    const b = new THREE.BoxGeometry(0.7, 0.24, 0.7).translate(0.1, 0.36, 0.1);
    const c = new THREE.BoxGeometry(0.42, 0.3, 0.42).translate(0.2, 0.63, 0.2);
    return montar([a, b, c]);
  },
  // Representar — cristal apoiado num pino: a ideia virando estrutura.
  cristal: () => {
    const pino = new THREE.CylinderGeometry(0.1, 0.14, 0.5, 8).translate(0, 0.25, 0);
    const cristal = new THREE.OctahedronGeometry(0.44, 0).translate(0, 0.92, 0);
    const base = new THREE.BoxGeometry(0.62, 0.12, 0.62).translate(0, 0.06, 0);
    return montar([base, pino, cristal]);
  },
  // Investigar — obelisco com marcador no topo.
  obelisco: () => {
    const base = new THREE.BoxGeometry(0.62, 0.16, 0.62).translate(0, 0.08, 0);
    const fuste = new THREE.CylinderGeometry(0.13, 0.26, 1.35, 4).rotateY(Math.PI / 4).translate(0, 0.84, 0);
    const ponta = new THREE.OctahedronGeometry(0.19, 0).translate(0, 1.66, 0);
    return montar([base, fuste, ponta]);
  },
  // Integrar — núcleo entre dois anéis cruzados.
  nucleo: () => {
    const base = new THREE.CylinderGeometry(0.34, 0.42, 0.16, 16).translate(0, 0.08, 0);
    const a1 = new THREE.TorusGeometry(0.4, 0.06, 8, 26).translate(0, 0.6, 0);
    const a2 = new THREE.TorusGeometry(0.4, 0.06, 8, 26).rotateY(Math.PI / 2).translate(0, 0.6, 0);
    const centro = new THREE.IcosahedronGeometry(0.2, 0).translate(0, 0.6, 0);
    return montar([base, a1, a2, centro]);
  },
  // Decidir — volume suspenso sobre um pedestal fino.
  cubo: () => {
    const base = new THREE.BoxGeometry(0.72, 0.12, 0.72).translate(0, 0.06, 0);
    const haste = new THREE.CylinderGeometry(0.08, 0.08, 0.55, 6).translate(0, 0.34, 0);
    const volume = new THREE.BoxGeometry(0.56, 0.56, 0.56).rotateY(Math.PI / 4).translate(0, 0.95, 0);
    return montar([base, haste, volume]);
  },
};

const cacheGeometria = {};
function geometriaDe(forma) {
  if (!cacheGeometria[forma]) cacheGeometria[forma] = (GEOMETRIAS[forma] ?? GEOMETRIAS.cristal)();
  return cacheGeometria[forma];
}

/** Um ponto de interesse do mapa. Nunca renderiza `hab_id` nem código de
 * ontologia — só `no.nome`, que já é uma frase em português. */
export default function NoHabilidade3D({ no, selecionado, onClickHab }) {
  const arq = BIOMA_ARCHETYPES[no.biomaId];
  const tier = ESTADO_TIER[no.estado];
  const [hover, setHover] = useState(false);
  const objetoRef = useRef();
  const giroBase = useMemo(() => hash01(`${no.hab_id}:giro`) * Math.PI * 2, [no.hab_id]);
  const geometria = useMemo(() => geometriaDe(arq.formaNo), [arq.formaNo]);

  useFrame((state) => {
    const obj = objetoRef.current;
    if (!obj) return;
    const t = state.clock.elapsedTime;
    const pulso = tier?.pulsa ? 1 + Math.sin(t * 2 + giroBase) * 0.05 : 1;
    const destaque = selecionado ? 1.22 : hover ? 1.1 : 1;
    // ESCALA_NO: o objeto precisa ser legível na vista do arquipélago
    // inteiro — no tamanho "real" de mobiliário ele sumiria no telhado do
    // próprio quarteirão.
    obj.scale.setScalar(11 * (tier?.escala ?? 1) * pulso * destaque);
    obj.rotation.y = giroBase + (selecionado ? t * 0.35 : t * 0.06);
    obj.position.y = selecionado ? 1.2 + Math.sin(t * 1.6) * 0.6 : 0;
  });

  if (!tier) return null; // `unknown` continua sendo massa bruta, sem objeto

  const mostrarRotulo = (hover || selecionado) && tier.rotulo;

  return (
    <group position={no.position}>
      <mesh ref={objetoRef} geometry={geometria} castShadow receiveShadow>
        <meshStandardMaterial
          color={arq.paleta.claro}
          emissive={arq.paleta.brilho}
          emissiveIntensity={tier.emissiva * (selecionado ? 1.5 : 1)}
          roughness={0.34}
          metalness={0.12}
          flatShading
        />
      </mesh>

      {/* Alvo de clique generoso: o objeto é pequeno, a área clicável não. */}
      <mesh
        position={[0, 8, 0]}
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
        <boxGeometry args={[17, 22, 17]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>

      {selecionado && (
        <>
          <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.04, 0]}>
            <ringGeometry args={[9, 10.4, 56]} />
            <meshBasicMaterial color={arq.paleta.brilho} transparent opacity={0.75} />
          </mesh>
          <mesh position={[0, 95, 0]}>
            <cylinderGeometry args={[1.1, 1.1, 190, 12, 1, true]} />
            <meshBasicMaterial
              color={arq.paleta.brilho}
              transparent
              opacity={0.18}
              depthWrite={false}
              blending={THREE.AdditiveBlending}
              side={THREE.DoubleSide}
            />
          </mesh>
        </>
      )}

      {mostrarRotulo && (
        <Text
          position={[0, 24, 0]}
          fontSize={2.1}
          color="#EEF6FF"
          anchorX="center"
          anchorY="bottom"
          outlineWidth={0.08}
          outlineColor="#03060d"
          maxWidth={44}
          textAlign="center"
        >
          {no.nome.length > 42 ? `${no.nome.slice(0, 41)}…` : no.nome}
        </Text>
      )}
    </group>
  );
}
