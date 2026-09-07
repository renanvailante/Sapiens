import { Billboard, Text } from "@react-three/drei";

/** Um balão de texto flutuante — decorativo, sem clique, sem estado. Vira o
 * rosto pra câmera (Billboard) e flutua com um seno lento independente por
 * balão (deslocamento de fase pela posição, sem precisar de estado). */
export default function Balao3D({ balao }) {
  return (
    <Billboard position={balao.position}>
      <mesh position={[0, 0, -0.02]}>
        <planeGeometry args={[balao.largura, balao.altura]} />
        <meshBasicMaterial color="#0a1526" transparent opacity={0.55} />
      </mesh>
      <mesh position={[-balao.largura / 2, 0, -0.015]}>
        <planeGeometry args={[0.02, balao.altura]} />
        <meshBasicMaterial color="#4FD9FF" transparent opacity={0.6} />
      </mesh>
      <Text
        fontSize={0.2}
        color="#A7BCD9"
        maxWidth={balao.largura - 0.35}
        textAlign="center"
        anchorX="center"
        anchorY="middle"
        lineHeight={1.3}
      >
        {balao.texto}
      </Text>
    </Billboard>
  );
}
