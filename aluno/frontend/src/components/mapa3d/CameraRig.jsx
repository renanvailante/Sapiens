import { useEffect, useRef } from "react";
import { CameraControls } from "@react-three/drei";
import CameraControlsImpl from "camera-controls";

// Câmera de exploração, não de gráfico inclinado: órbita horizontal livre em
// 360°, inclinação ampla (do quase-zenital ao rasante), pan sem restrição de
// eixo e zoom que vai do arquipélago inteiro até encostar numa estrutura.
//
// O único limite que resta é o que impede a câmera de virar de cabeça para
// baixo ou de mergulhar por baixo do mundo — abaixo da linha do horizonte só
// existe abismo, e uma câmera invertida perde a referência de "para cima".
const POLAR_PADRAO = 0.88; // ~50° a partir do zênite
const AZIMUTE_PADRAO = 0.62;

export default function CameraRig({ focoPosicao, raioMundo }) {
  const ref = useRef();
  const montouRef = useRef(false);
  const distanciaPadrao = Math.max(80, raioMundo * 1.95);

  useEffect(() => {
    const controles = ref.current;
    if (!controles) return;

    if (!montouRef.current) {
      controles.rotateTo(AZIMUTE_PADRAO, POLAR_PADRAO, false);
      controles.dollyTo(distanciaPadrao, false);
      controles.moveTo(0, 30, 0, false);
    }

    if (focoPosicao) {
      const [fx, fy, fz] = focoPosicao;
      // Pula direto no primeiro foco (deep-link `?hab=`, onde o painel já
      // abre junto) — só anima nas trocas seguintes.
      controles.setLookAt(fx + 46, fy + 40, fz + 54, fx, fy + 6, fz, montouRef.current);
    } else if (montouRef.current) {
      controles.rotateTo(AZIMUTE_PADRAO, POLAR_PADRAO, true);
      controles.dollyTo(distanciaPadrao, true);
      controles.moveTo(0, 30, 0, true);
    }

    montouRef.current = true;
  }, [focoPosicao, distanciaPadrao]);

  return (
    <CameraControls
      ref={ref}
      makeDefault
      minPolarAngle={0.08}
      maxPolarAngle={Math.PI * 0.495}
      minDistance={26}
      maxDistance={Math.max(240, raioMundo * 3)}
      smoothTime={0.42}
      draggingSmoothTime={0.1}
      dollyToCursor
      infinityDolly={false}
      touches={{
        // 1 dedo desloca o mundo, 2 dedos dão zoom e giro — o par de gestos
        // que qualquer mapa de toque já ensinou.
        one: CameraControlsImpl.ACTION.TOUCH_TRUCK,
        two: CameraControlsImpl.ACTION.TOUCH_DOLLY_ROTATE,
        three: CameraControlsImpl.ACTION.TOUCH_TRUCK,
      }}
      mouseButtons={{
        left: CameraControlsImpl.ACTION.TRUCK,
        right: CameraControlsImpl.ACTION.ROTATE,
        middle: CameraControlsImpl.ACTION.DOLLY,
        wheel: CameraControlsImpl.ACTION.DOLLY,
      }}
    />
  );
}
