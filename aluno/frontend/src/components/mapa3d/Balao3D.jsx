import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Billboard, Text } from "@react-three/drei";
import { BIOMA_ARCHETYPES } from "./biomaArchetypes";

/** Uma placa de texto flutuando sobre a cidade — ambiente, não instrução:
 * sem clique, sem estado. Vira o rosto para a câmera e usa a luz do próprio
 * distrito na borda, para pertencer ao lugar onde está.
 *
 * Some quando a câmera se aproxima: o texto vive em coordenadas de mundo,
 * então de perto ele cresce até cobrir a arquitetura — e nessa distância o
 * aluno está lendo o lugar, não a legenda. */
export default function Balao3D({ balao }) {
  const paleta = BIOMA_ARCHETYPES[balao.biomaId]?.paleta ?? BIOMA_ARCHETYPES.perceber.paleta;
  const ref = useRef();

  useFrame((state) => {
    const grupo = ref.current;
    if (!grupo) return;
    const distancia = state.camera.position.distanceTo(grupo.position);
    grupo.visible = distancia > 34;
  });

  return (
    <Billboard ref={ref} position={balao.position}>
      <mesh position={[0, 0, -0.03]}>
        <planeGeometry args={[balao.largura, balao.altura]} />
        <meshBasicMaterial color="#080f1f" transparent opacity={0.62} />
      </mesh>
      <mesh position={[-balao.largura / 2, 0, -0.02]}>
        <planeGeometry args={[0.035, balao.altura]} />
        <meshBasicMaterial color={paleta.brilho} transparent opacity={0.8} />
      </mesh>
      <Text
        fontSize={0.21}
        color="#B9CEE8"
        maxWidth={balao.largura - 0.4}
        textAlign="center"
        anchorX="center"
        anchorY="middle"
        lineHeight={1.35}
      >
        {balao.texto}
      </Text>
    </Billboard>
  );
}
