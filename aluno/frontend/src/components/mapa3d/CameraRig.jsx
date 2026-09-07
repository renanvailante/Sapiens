import { useEffect, useRef } from "react";
import { CameraControls } from "@react-three/drei";
import CameraControlsImpl from "camera-controls";

// "Órbita limitada" (decisão de produto confirmada): ângulo elevado por
// padrão, pan + zoom livres, rotação limitada a ±~22° em torno do padrão —
// estilo Civilization/Age of Empires, não uma órbita 3D livre.
const AZIMUTE_PADRAO = 0.62; // radianos — três-quartos, pra as fachadas laterais aparecerem junto com o topo
const POLAR_PADRAO = 0.82; // ~47° a partir do zênite = ~43° de elevação, batendo com o "~45° de cima" pedido
// A cidade tem ~90 unidades de ponta a ponta: com fov 40° é preciso recuar
// bem para o conjunto caber no enquadramento de abertura.
const DISTANCIA_PADRAO = 72;
const ALVO_PADRAO = [0, 0, 0];

/** Câmera do mundo 3D, construída sobre `CameraControls` do drei (que já
 * embute `camera-controls`): enquadramento elevado padrão, pan/zoom livres,
 * órbita limitada, e dolly suave até o nó focado. `focoPosicao` é a MESMA
 * informação que já abre/fecha o painel na página (`briefingHab?.hab_id`
 * convertido em posição) — nenhum estado novo sobe para `TreinoHabilidades`. */
export default function CameraRig({ focoPosicao }) {
  const ref = useRef();
  const montouRef = useRef(false);

  useEffect(() => {
    const controles = ref.current;
    if (!controles) return;

    if (!montouRef.current) {
      controles.rotateTo(AZIMUTE_PADRAO, POLAR_PADRAO, false);
      controles.dollyTo(DISTANCIA_PADRAO, false);
      controles.moveTo(...ALVO_PADRAO, false);
    }

    if (focoPosicao) {
      const [fx, fy, fz] = focoPosicao;
      // Pula direto no primeiro foco (ex.: deep-link `?hab=HAB-03`, onde o
      // painel também já abre direto) — só anima nas trocas seguintes.
      controles.setLookAt(fx + 8, fy + 8.5, fz + 10, fx, fy + 1.2, fz, montouRef.current);
    } else if (montouRef.current) {
      controles.setLookAt(
        ALVO_PADRAO[0] + DISTANCIA_PADRAO * 0.55,
        DISTANCIA_PADRAO * 0.62,
        ALVO_PADRAO[2] + DISTANCIA_PADRAO * 0.55,
        ALVO_PADRAO[0],
        ALVO_PADRAO[1],
        ALVO_PADRAO[2],
        true,
      );
    }

    montouRef.current = true;
  }, [focoPosicao]);

  return (
    <CameraControls
      ref={ref}
      minPolarAngle={Math.PI * 0.16}
      maxPolarAngle={Math.PI * 0.47}
      minAzimuthAngle={AZIMUTE_PADRAO - Math.PI * 0.26}
      maxAzimuthAngle={AZIMUTE_PADRAO + Math.PI * 0.26}
      minDistance={12}
      maxDistance={135}
      smoothTime={0.5}
      draggingSmoothTime={0.12}
      dollyToCursor={false}
      touches={{
        // 1 dedo = pan (mesmo comportamento do drag no mapa SVG anterior);
        // 2 dedos = pinça pra zoom + a órbita limitada acima.
        one: CameraControlsImpl.ACTION.TOUCH_TRUCK,
        two: CameraControlsImpl.ACTION.TOUCH_DOLLY_ROTATE,
        three: CameraControlsImpl.ACTION.TOUCH_DOLLY_TRUCK,
      }}
      mouseButtons={{
        left: CameraControlsImpl.ACTION.TRUCK,
        right: CameraControlsImpl.ACTION.ROTATE,
        wheel: CameraControlsImpl.ACTION.DOLLY,
        middle: CameraControlsImpl.ACTION.DOLLY,
      }}
    />
  );
}
