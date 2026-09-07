// Gerador do ARQUIPÉLAGO — a arquitetura é o mapa.
//
// Entra a descrição de cena (nós, rotas) e sai uma lista plana de "peças":
// volumes primitivos com posição, tamanho, rotação, distrito e tom. Nada
// aqui sabe o que é React ou Three — `Cidade.jsx` só instancia o que esta
// lista descreve.
//
// Vocabulário:
//   ilha         massa de terra em degraus, com falésia na borda e quilha
//                por baixo — cada bioma é uma ilha separada por abismo
//   quarteirão   torre + cornija + laje onde uma habilidade se apoia
//   rota         parábola entre dois nós, como rota de voo; acende com o
//                progresso e fica interrompida quando o pré-requisito falta
//   landmark     a estrutura-assinatura da ilha, em escala monumental
//   vegetação    o que dá caráter de bioma: cerrado, mata, caatinga,
//                amazônia, pantanal, pampas
//   névoa        o que encobre o que só foi percebido, não explorado
//
// Tudo determinístico (hash por `hab_id`/`bioma_id`): mesmo mundo para todo
// aluno, em todo carregamento.
import * as CENA from "./sceneBuilder";
import { BIOMA_ARCHETYPES, ESTADO_TIER } from "./biomaArchetypes";
import { hash01, seededNoise2D } from "./noise";

const CELULA = 3.8;

// ---------------------------------------------------------------- primitivas

function caixa(pecas, bioma, tom, x, base, z, w, h, d, rotY = 0, rotX = 0) {
  if (h <= 0.01 || w <= 0.01) return;
  pecas.push({ forma: "caixa", bioma, tom, pos: [x, base + h / 2, z], size: [w, h, d], rotY, rotX });
}

function caixaCentrada(pecas, bioma, tom, x, y, z, w, h, d, rotY = 0, rotX = 0) {
  pecas.push({ forma: "caixa", bioma, tom, pos: [x, y, z], size: [w, h, d], rotY, rotX });
}

function cilindro(pecas, bioma, tom, x, base, z, diam, h, rotY = 0) {
  if (h <= 0.01) return;
  pecas.push({ forma: "cilindro", bioma, tom, pos: [x, base + h / 2, z], size: [diam, h, diam], rotY, rotX: 0 });
}

function cone(pecas, bioma, tom, x, base, z, diam, h, rotX = 0) {
  const centro = rotX === 0 ? base + h / 2 : base - h / 2;
  pecas.push({ forma: "cone", bioma, tom, pos: [x, centro, z], size: [diam, h, diam], rotY: 0, rotX });
}

function anel(pecas, bioma, tom, x, y, z, diam, rotX = -Math.PI / 2, rotY = 0) {
  pecas.push({ forma: "anel", bioma, tom, pos: [x, y, z], size: [diam, diam, diam], rotY, rotX });
}

function esfera(pecas, bioma, tom, x, y, z, diam) {
  pecas.push({ forma: "esfera", bioma, tom, pos: [x, y, z], size: [diam, diam, diam], rotY: 0, rotX: 0 });
}

/** Arco de volta inteira em aduelas — vão vencido por curva, não por viga. */
function arco(pecas, bioma, tom, cx, base, cz, vao, ang, espessura = 0.42, aduelas = 9) {
  const r = vao / 2;
  for (let i = 0; i < aduelas; i++) {
    const t = ((i + 0.5) / aduelas) * Math.PI;
    const u = -r * Math.cos(t);
    const y = base + r * Math.sin(t);
    caixaCentrada(
      pecas, bioma, tom,
      cx + Math.sin(ang) * u, y, cz + Math.cos(ang) * u,
      espessura, espessura, ((Math.PI * r) / aduelas) * 1.25,
      ang, t - Math.PI / 2,
    );
  }
}

// --------------------------------------------------------------------- ilha

/** Uma ilha: platô em degraus sobre falésia, com quilha apontando para o
 * abismo. É o que faz cada bioma ser um lugar, e não um setor de um mapa. */
function gerarIlha(biomaId, nosDoBioma, pecas) {
  const arq = BIOMA_ARCHETYPES[biomaId];
  const centro = CENA.ANCORA_MUNDO[biomaId];
  const topo = CENA.alturaIlha(biomaId);
  const ruido = seededNoise2D(`ilha:${biomaId}`);

  const alcance = arq.raioIlha + 10;
  const cols = Math.ceil((alcance * 2) / CELULA);
  const celulas = new Map();

  for (let i = 0; i < cols; i++) {
    for (let j = 0; j < cols; j++) {
      const cx = centro.x - alcance + (i + 0.5) * CELULA;
      const cz = centro.z - alcance + (j + 0.5) * CELULA;

      let dentro = Math.hypot(cx - centro.x, cz - centro.z) < arq.raioIlha;
      if (!dentro) {
        for (const no of nosDoBioma) {
          if (Math.hypot(no.position[0] - cx, no.position[2] - cz) < arq.raioIlha * 0.82) {
            dentro = true;
            break;
          }
        }
      }
      // Borda irregular: sem isto a ilha vira um disco perfeito e denuncia
      // que foi gerada por raio.
      if (dentro && ruido(cx * 0.085, cz * 0.085) < -0.4) dentro = false;
      if (!dentro) continue;

      const degrau = Math.round(ruido(cx * 0.055, cz * 0.055) * 1.1) * 1.1;
      celulas.set(`${i}:${j}`, { i, j, cx, cz, topo: topo + degrau });
    }
  }

  for (const cel of celulas.values()) {
    caixa(pecas, biomaId, "medio", cel.cx, cel.topo - 1.5, cel.cz, CELULA, 1.5, CELULA);

    let borda = false;
    for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      if (!celulas.has(`${cel.i + di}:${cel.j + dj}`)) {
        borda = true;
        break;
      }
    }
    // Falésia: a espessura só aparece na borda, que é onde o abismo é lido.
    const fundura = borda ? 7 + hash01(`${biomaId}:${cel.i}:${cel.j}`) * 6 : 3;
    caixa(pecas, biomaId, "escuro", cel.cx, cel.topo - 1.5 - fundura, cel.cz, CELULA * 0.99, fundura, CELULA * 0.99);
  }

  // Quilha: a ilha termina em ponta, flutuando sobre o vazio.
  const raioReal = arq.raioIlha + 2;
  cone(pecas, biomaId, "escuro", centro.x, topo - 7, centro.z, raioReal * 1.7, raioReal * 1.5, Math.PI);

  return celulas;
}

// --------------------------------------------------------------- quarteirão

function gerarQuarteirao(no, pecas) {
  const [x, y, z] = no.position;
  const arq = BIOMA_ARCHETYPES[no.biomaId];
  const solo = CENA.alturaIlha(no.biomaId);
  const rot = Math.round(hash01(`${no.hab_id}:rot`) * 3) * (Math.PI / 2);

  if (no.estado === "unknown") {
    // Massa bruta: o quarteirão existe, sem detalhe e sem luz.
    const h = 1.6 + hash01(`${no.hab_id}:massa`) * 2.6;
    const w = 3.4 + hash01(`${no.hab_id}:mw`) * 2.2;
    caixa(pecas, no.biomaId, "escuro", x, solo, z, w, h, w, rot);
    return;
  }

  const tier = ESTADO_TIER[no.estado];
  const largura = 3.4 + hash01(`${no.hab_id}:w`) * 2.0;
  const baseLaje = y - CENA.LAJE;
  const alturaTorre = baseLaje - 0.3 - solo;

  if (alturaTorre > 0.25) {
    const lt = largura * 0.72;
    caixa(pecas, no.biomaId, "escuro", x, solo, z, lt, alturaTorre, lt, rot);
    if (alturaTorre > 2.6) {
      for (let f = 0; f < 4; f++) {
        const ang = rot + (f * Math.PI) / 2;
        arco(pecas, no.biomaId, "medio", x + Math.sin(ang) * (lt / 2 + 0.1), solo, z + Math.cos(ang) * (lt / 2 + 0.1),
          lt * 0.6, ang + Math.PI / 2, 0.3, 7);
      }
    }
    const linhas = Math.max(1, Math.floor((alturaTorre - 1) / 1.5));
    for (let l = 0; l < linhas; l++) {
      const yj = solo + 1 + l * 1.5;
      if (yj > baseLaje - 0.7) break;
      for (let f = 0; f < 4; f++) {
        const ang = rot + (f * Math.PI) / 2;
        caixa(pecas, no.biomaId, tier.janela, x + Math.sin(ang) * (lt / 2 + 0.04), yj, z + Math.cos(ang) * (lt / 2 + 0.04),
          largura * 0.26, 0.55, 0.12, ang);
      }
    }
  }

  caixa(pecas, no.biomaId, "medio", x, baseLaje - 0.32, z, largura + 0.8, 0.32, largura + 0.8, rot);
  caixa(pecas, no.biomaId, "claro", x, baseLaje, z, largura, CENA.LAJE, largura, rot);
  caixa(pecas, no.biomaId, "medio", x, y, z, 1.3, 0.36, 1.3, rot + 0.45);

  for (const s of [1, -1]) {
    caixa(pecas, no.biomaId, "medio",
      x + Math.cos(rot) * s * (largura / 2 - 0.25), y, z + Math.sin(rot) * s * (largura / 2 - 0.25),
      0.28, 1.5, 0.28, rot);
    caixa(pecas, no.biomaId, arq ? "brilhoFraco" : "medio",
      x + Math.cos(rot) * s * (largura / 2 - 0.25), y + 1.5, z + Math.sin(rot) * s * (largura / 2 - 0.25),
      0.42, 0.16, 0.42, rot);
  }

  // Névoa do que só foi percebido: a silhueta aparece, o conteúdo não.
  if (tier.nevoa) {
    for (let i = 0; i < 4; i++) {
      const ang = (i / 4) * Math.PI * 2 + hash01(`${no.hab_id}:nev${i}`) * 1.2;
      const r = largura * 0.5 + hash01(`${no.hab_id}:nr${i}`) * 1.2;
      esfera(pecas, no.biomaId, "nevoa",
        x + Math.cos(ang) * r, y + 0.5 + hash01(`${no.hab_id}:nh${i}`) * 1.1, z + Math.sin(ang) * r,
        largura * (1.15 + hash01(`${no.hab_id}:nd${i}`) * 0.5));
    }
  }
}

// --------------------------------------------------------------------- rota

/** Rota parabólica entre dois nós — desenho de rota de voo. Quanto mais
 * longo o vão, mais alto o ápice; quanto mais dominada a ligação, mais
 * acesa. Pré-requisito ainda não dominado: a rota sai da origem e se
 * interrompe no meio do caminho (leitura, não trava — o destino continua
 * clicável, como sempre foi). */
function gerarRota(a, pecas) {
  const [x1, y1, z1] = a.from;
  const [x2, y2, z2] = a.to;
  const dx = x2 - x1;
  const dz = z2 - z1;
  const plano = Math.hypot(dx, dz);
  if (plano < 1) return;

  const apice = Math.min(4 + plano * 0.32, 34);
  const segmentos = Math.max(10, Math.min(26, Math.round(plano / 2.4)));
  const acesa = a.peso >= 0.75;
  const tom = acesa ? "brilho" : a.peso >= 0.45 ? "brilhoFraco" : "medio";
  const interrompida = a.relation === "prerequisito" && !a.sourceMastered;
  const ate = interrompida ? Math.floor(segmentos * 0.45) : segmentos;

  const ponto = (t) => [
    x1 + dx * t,
    y1 + (y2 - y1) * t + apice * 4 * t * (1 - t),
    z1 + dz * t,
  ];

  for (let i = 0; i < ate; i++) {
    const p0 = ponto(i / segmentos);
    const p1 = ponto((i + 1) / segmentos);
    const sx = p1[0] - p0[0];
    const sy = p1[1] - p0[1];
    const sz = p1[2] - p0[2];
    const horizontal = Math.hypot(sx, sz);
    caixaCentrada(
      pecas, a.biomaId, tom,
      (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2,
      0.3, 0.14, Math.hypot(horizontal, sy) * 1.06,
      Math.atan2(sx, sz), -Math.atan2(sy, horizontal),
    );
  }

  // Cais de partida e de chegada: a rota encosta em estrutura, não no ar.
  anel(pecas, a.biomaId, acesa ? "brilho" : "brilhoFraco", x1, y1 + 0.5, z1, 1.7);
  if (!interrompida) anel(pecas, a.biomaAlvo ?? a.biomaId, acesa ? "brilho" : "brilhoFraco", x2, y2 + 0.5, z2, 1.7);
}

// ---------------------------------------------------------------- vegetação

/** O que dá caráter de bioma à ilha. Espalhado nas células livres, longe
 * dos quarteirões, sempre determinístico. */
function gerarVegetacao(biomaId, celulas, nosDoBioma, pecas) {
  const arq = BIOMA_ARCHETYPES[biomaId];
  const centro = CENA.ANCORA_MUNDO[biomaId];

  for (const cel of celulas.values()) {
    const semente = `${biomaId}:${cel.i}:${cel.j}`;
    const sorte = hash01(semente);

    let livre = Math.hypot(cel.cx - centro.x, cel.cz - centro.z) > 5.5;
    if (livre) {
      for (const no of nosDoBioma) {
        if (Math.hypot(no.position[0] - cel.cx, no.position[2] - cel.cz) < 3.6) {
          livre = false;
          break;
        }
      }
    }
    if (!livre) continue;

    const x = cel.cx + (hash01(`${semente}:jx`) - 0.5) * CELULA * 0.7;
    const z = cel.cz + (hash01(`${semente}:jz`) - 0.5) * CELULA * 0.7;
    const y = cel.topo;
    const g = (k) => hash01(`${semente}:${k}`);

    switch (arq.vegetacao) {
      case "cerrado": {
        // Campo aberto: pouca coisa, e o que existe é baixo e espalhado.
        if (sorte > 0.26) break;
        if (sorte < 0.11) {
          caixa(pecas, biomaId, "escuro", x, y, z, 2.4 + g("a") * 2.6, 1.1 + g("b") * 1.8, 2.2 + g("c") * 2.2, g("r") * 3);
          caixa(pecas, biomaId, "medio", x, y + 1.1 + g("b") * 1.8, z, 1.5 + g("c") * 1.2, 0.7, 1.4, g("r") * 3);
        } else {
          cilindro(pecas, biomaId, "medio", x, y, z, 0.42, 2.6 + g("h") * 2.2);
          caixa(pecas, biomaId, "claro", x, y + 2.6 + g("h") * 2.2, z, 3.2, 0.5, 3.2, g("r") * 3);
        }
        break;
      }
      case "mata": {
        // Mata fechada: densidade alta, copas em duas camadas.
        if (sorte > 0.5) break;
        const alturaTronco = 3.4 + g("h") * 3.6;
        cilindro(pecas, biomaId, "escuro", x, y, z, 0.55, alturaTronco);
        caixa(pecas, biomaId, "medio", x, y + alturaTronco, z, 3.8, 1.2, 3.8, g("r") * 3);
        caixa(pecas, biomaId, "claro", x, y + alturaTronco + 1.2, z, 2.6, 0.9, 2.6, g("r2") * 3);
        break;
      }
      case "caatinga": {
        // Árido e angular: pedra rachada e cristal.
        if (sorte > 0.34) break;
        if (sorte < 0.16) {
          cone(pecas, biomaId, "claro", x, y, z, 1.8 + g("a") * 1.6, 4.5 + g("b") * 5);
        } else {
          caixa(pecas, biomaId, "escuro", x, y, z, 2.6 + g("c") * 2.2, 1.2 + g("d") * 1.6, 2.4, g("r") * 3);
          cone(pecas, biomaId, "brilhoFraco", x, y + 1.2 + g("d") * 1.6, z, 0.8, 1.8, 0);
        }
        break;
      }
      case "amazonia": {
        // Floresta profunda com torre emergindo acima da copa.
        if (sorte > 0.56) break;
        const alturaTronco = 4.6 + g("h") * 4.4;
        cilindro(pecas, biomaId, "escuro", x, y, z, 0.62, alturaTronco);
        caixa(pecas, biomaId, "medio", x, y + alturaTronco, z, 4.4, 1.5, 4.4, g("r") * 3);
        caixa(pecas, biomaId, "claro", x, y + alturaTronco + 1.5, z, 3.0, 1.0, 3.0, g("r2") * 3);
        if (sorte < 0.08) {
          cilindro(pecas, biomaId, "medio", x, y, z, 0.7, alturaTronco + 5);
          anel(pecas, biomaId, "brilho", x, y + alturaTronco + 5, z, 2.2);
        }
        break;
      }
      case "pantanal": {
        // Água e ilhotas: o chão alaga e as estruturas viram horizontais.
        if (sorte > 0.52) break;
        if (sorte < 0.3) {
          caixa(pecas, biomaId, "agua", x, y - 0.45, z, CELULA * 2.3, 0.34, CELULA * 2.3, g("r") * 3);
        } else {
          caixa(pecas, biomaId, "medio", x, y, z, 2.2 + g("a") * 1.4, 0.34, 1.6 + g("b") * 1.2, g("r") * 3);
          for (let k = 0; k < 3; k++) {
            cilindro(pecas, biomaId, "claro", x + (g(`k${k}`) - 0.5) * 1.8, y + 0.34, z + (g(`m${k}`) - 0.5) * 1.4,
              0.16, 0.9 + g(`n${k}`) * 0.9);
          }
        }
        break;
      }
      default: {
        // Pampas: o vazio é o assunto. Só linhas longas e baixas.
        if (sorte > 0.16) break;
        caixa(pecas, biomaId, "medio", x, y, z, 7.5 + g("a") * 4, 0.5, 0.4, g("r") * 3);
        if (sorte < 0.05) caixa(pecas, biomaId, "claro", x, y, z, 1.1, 6 + g("h") * 3.5, 1.1, g("r") * 3);
        break;
      }
    }
  }
}

// ----------------------------------------------------------------- landmarks

/** A estrutura-assinatura da ilha, em escala monumental: é o que se enxerga
 * do outro lado do arquipélago e orienta a exploração. */
function gerarLandmark(biomaId, pecas) {
  const centro = CENA.ANCORA_MUNDO[biomaId];
  const base = CENA.alturaIlha(biomaId);
  const x = centro.x;
  const z = centro.z;
  const arq = BIOMA_ARCHETYPES[biomaId];

  switch (arq.landmark) {
    case "mirante": {
      // Cerrado: formação rochosa escalonada com plataforma de horizonte.
      for (let i = 0; i < 4; i++) {
        const r = 9 - i * 1.9;
        cilindro(pecas, biomaId, i % 2 ? "medio" : "escuro", x, base + i * 2.2, z, r * 2, 2.2);
      }
      cilindro(pecas, biomaId, "claro", x, base + 8.8, z, 8.4, 0.7);
      for (let i = 0; i < 12; i++) {
        const ang = (i / 12) * Math.PI * 2;
        cilindro(pecas, biomaId, "claro", x + Math.cos(ang) * 3.6, base + 9.5, z + Math.sin(ang) * 3.6, 0.5, 3.2);
      }
      anel(pecas, biomaId, "brilho", x, base + 13.2, z, 8.2);
      cone(pecas, biomaId, "claro", x, base + 9.5, z, 2.2, 3.4);
      break;
    }
    case "passarelas": {
      // Mata Atlântica: passarelas suspensas cruzando sobre a copa.
      for (let i = 0; i < 5; i++) {
        const ang = (i / 5) * Math.PI * 2;
        cilindro(pecas, biomaId, "escuro", x + Math.cos(ang) * 5.5, base, z + Math.sin(ang) * 5.5, 1.5, 9 + i * 0.9);
        caixa(pecas, biomaId, "claro", x + Math.cos(ang) * 5.5, base + 9 + i * 0.9, z + Math.sin(ang) * 5.5, 3.6, 0.5, 3.6, ang);
      }
      for (let i = 0; i < 5; i++) {
        const a1 = (i / 5) * Math.PI * 2;
        const a2 = ((i + 2) / 5) * Math.PI * 2;
        const p1 = [x + Math.cos(a1) * 5.5, base + 9 + i * 0.9, z + Math.sin(a1) * 5.5];
        const p2 = [x + Math.cos(a2) * 5.5, base + 9 + ((i + 2) % 5) * 0.9, z + Math.sin(a2) * 5.5];
        const ddx = p2[0] - p1[0];
        const ddz = p2[2] - p1[2];
        const comp = Math.hypot(ddx, ddz);
        caixaCentrada(pecas, biomaId, "medio", (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2, (p1[2] + p2[2]) / 2,
          1.1, 0.24, comp, Math.atan2(ddx, ddz), -Math.atan2(p2[1] - p1[1], comp));
      }
      cilindro(pecas, biomaId, "brilho", x, base + 14, z, 1.2, 4.5);
      break;
    }
    case "cristal": {
      // Caatinga: formação cristalina saindo da pedra rachada.
      cilindro(pecas, biomaId, "escuro", x, base - 1, z, 13, 2.4);
      for (let i = 0; i < 7; i++) {
        const ang = (i / 7) * Math.PI * 2;
        const r = 2.4 + hash01(`cristal${i}`) * 2.6;
        const h = 7 + hash01(`cristalh${i}`) * 9;
        cone(pecas, biomaId, i % 2 ? "claro" : "medio", x + Math.cos(ang) * r, base + 1.4, z + Math.sin(ang) * r,
          1.6 + hash01(`cristald${i}`) * 1.4, h);
      }
      cone(pecas, biomaId, "brilho", x, base + 1.4, z, 3.2, 18);
      break;
    }
    case "observatorio": {
      // Amazônia: torre de observação rompendo a copa.
      cilindro(pecas, biomaId, "escuro", x, base, z, 6.5, 14);
      for (let i = 0; i < 4; i++) {
        anel(pecas, biomaId, "medio", x, base + 3 + i * 3.2, z, 7.6);
      }
      cilindro(pecas, biomaId, "medio", x, base + 14, z, 9, 1);
      anel(pecas, biomaId, "brilho", x, base + 15.2, z, 9.6);
      cilindro(pecas, biomaId, "claro", x, base + 15, z, 5.4, 3.4);
      cone(pecas, biomaId, "claro", x, base + 18.4, z, 4.4, 4);
      caixaCentrada(pecas, biomaId, "brilho", x + 2.4, base + 20.5, z + 2.4, 0.8, 0.8, 6.5, Math.PI / 4, -0.6);
      break;
    }
    case "delta": {
      // Pantanal: lâmina d'água com plataformas horizontais conectadas.
      cilindro(pecas, biomaId, "agua", x, base - 0.7, z, 22, 0.5);
      for (let i = 0; i < 6; i++) {
        const ang = (i / 6) * Math.PI * 2;
        const r = 5 + (i % 2) * 2.6;
        const px = x + Math.cos(ang) * r;
        const pz = z + Math.sin(ang) * r;
        caixa(pecas, biomaId, i % 2 ? "claro" : "medio", px, base - 0.3, pz, 5.2, 0.55, 4.2, ang);
        caixaCentrada(pecas, biomaId, "medio", (x + px) / 2, base, (z + pz) / 2, 1.5, 0.3, r, ang);
        cilindro(pecas, biomaId, "brilhoFraco", px, base + 0.25, pz, 0.3, 2.6);
      }
      cilindro(pecas, biomaId, "claro", x, base - 0.3, z, 7.5, 1.2);
      anel(pecas, biomaId, "brilho", x, base + 1.4, z, 7);
      break;
    }
    default: {
      // Pampas: monumento no planalto vazio — linha arquitetônica pura.
      caixa(pecas, biomaId, "medio", x, base - 0.8, z, 22, 0.8, 15);
      caixa(pecas, biomaId, "claro", x, base, z, 19, 0.6, 12.5);
      for (let i = 0; i < 8; i++) {
        const px = x - 7.7 + i * 2.2;
        cilindro(pecas, biomaId, "claro", px, base + 0.6, z - 3.4, 1.1, 7.5);
        cilindro(pecas, biomaId, "medio", px, base + 0.6, z + 3.4, 1.1, 7.5);
      }
      caixa(pecas, biomaId, "claro", x, base + 8.1, z, 19.5, 1.3, 12.8);
      caixa(pecas, biomaId, "medio", x, base + 9.4, z, 11, 0.7, 7);
      caixaCentrada(pecas, biomaId, "brilho", x, base + 14.5, z, 4.4, 4.4, 4.4, Math.PI / 4, 0.35);
      break;
    }
  }
}

// ---------------------------------------------------------------------- API

/** Monta o arquipélago inteiro a partir da cena. */
export function construirCidade({ nos, arestas }) {
  const pecas = [];
  const porBioma = {};
  for (const no of nos) (porBioma[no.biomaId] ??= []).push(no);

  for (const id of CENA.BIOMA_IDS) {
    const doBioma = porBioma[id] ?? [];
    const celulas = gerarIlha(id, doBioma, pecas);
    gerarVegetacao(id, celulas, doBioma, pecas);
    gerarLandmark(id, pecas);
  }
  for (const no of nos) gerarQuarteirao(no, pecas);
  for (const a of arestas) gerarRota(a, pecas);

  return pecas;
}
