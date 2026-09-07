// Gerador da CIDADE — a arquitetura é o mapa.
//
// Entra a descrição de cena (nós, conexões, biomas) e sai uma lista plana de
// "peças": volumes primitivos com posição, tamanho, rotação, distrito e tom.
// Nada aqui sabe o que é React ou Three — `Cidade.jsx` só instancia o que
// esta lista descreve.
//
// O vocabulário construtivo é sempre o mesmo, em qualquer distrito:
//
//   plinto      base contínua da cidade, em blocos de grade com mureta na borda
//   torre       a massa que sustenta um quarteirão acima do plinto
//   cornija     a linha clara de 30cm que separa a massa do piso
//   laje        o piso do quarteirão, onde a habilidade se apoia
//   janela      inserto luminoso na fachada — acende conforme o estado
//   ponte       tabuleiro + guarda-corpo + arco + pilares
//   escadaria   degraus reais quando as duas pontas estão em pavimentos diferentes
//   portão      pilastras + verga; selado enquanto o pré-requisito não é dominado
//   landmark    a peça-assinatura de cada distrito
//   adereço     arcos soltos, escadas para lugar nenhum, obeliscos, blocos suspensos
//
// Tudo é determinístico (hash por `hab_id`/`bioma_id`): a cidade é a mesma
// para todo aluno, em todo carregamento.
import * as CENA from "./sceneBuilder";
import { BIOMA_ARCHETYPES, ESTADO_TIER } from "./biomaArchetypes";
import { hash01, seededNoise2D } from "./noise";

const CELULA = 3.6;

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

function cone(pecas, bioma, tom, x, base, z, diam, h, rotY = 0) {
  pecas.push({ forma: "cone", bioma, tom, pos: [x, base + h / 2, z], size: [diam, h, diam], rotY, rotX: 0 });
}

function anel(pecas, bioma, tom, x, y, z, diam, rotX = -Math.PI / 2, rotY = 0) {
  pecas.push({ forma: "anel", bioma, tom, pos: [x, y, z], size: [diam, diam, diam], rotY, rotX });
}

/** Arco de volta inteira montado em aduelas (caixas tangentes ao arco). É o
 * que impede a cidade de virar "caixas e linhas": vão vencido por curva. */
function arco(pecas, bioma, tom, cx, base, cz, vao, ang, espessura = 0.42, aduelas = 9) {
  const r = vao / 2;
  for (let i = 0; i < aduelas; i++) {
    const t = ((i + 0.5) / aduelas) * Math.PI;
    const u = -r * Math.cos(t);
    const y = base + r * Math.sin(t);
    const comprimento = ((Math.PI * r) / aduelas) * 1.25;
    caixaCentrada(
      pecas, bioma, tom,
      cx + Math.sin(ang) * u, y, cz + Math.cos(ang) * u,
      espessura, espessura, comprimento,
      ang, t - Math.PI / 2,
    );
  }
}

// ------------------------------------------------------------------- plinto

/** O chão da cidade: blocos de grade cobrindo o entorno dos quarteirões, com
 * mureta em toda borda livre. É o que dá a leitura de "diorama" contínuo em
 * vez de plataformas soltas no vazio. */
function gerarPlinto(nos, pecas) {
  const ruido = seededNoise2D("plinto");
  const cols = Math.ceil(CENA.WORLD_WIDTH / CELULA);
  const rows = Math.ceil(CENA.WORLD_DEPTH / CELULA);
  const ocupadas = new Map();

  for (let i = 0; i < cols; i++) {
    for (let j = 0; j < rows; j++) {
      const cx = -CENA.WORLD_WIDTH / 2 + (i + 0.5) * CELULA;
      const cz = -CENA.WORLD_DEPTH / 2 + (j + 0.5) * CELULA;

      let distNo = Infinity;
      let dono = null;
      for (const no of nos) {
        const d = Math.hypot(no.position[0] - cx, no.position[2] - cz);
        if (d < distNo) {
          distNo = d;
          dono = no.biomaId;
        }
      }
      const { biomaId, distancia } = CENA.biomaMaisProximo(cx, cz);
      if (distancia < distNo) dono = biomaId;
      if (distNo > 7.4 && distancia > 9.5) continue;

      const degrau = ruido(cx * 0.055, cz * 0.055) > 0.2 ? 0.5 : 0;
      ocupadas.set(`${i}:${j}`, { i, j, cx, cz, dono, topo: CENA.BASE_TOPO - degrau });
    }
  }

  for (const cel of ocupadas.values()) {
    caixa(pecas, cel.dono, "escuro", cel.cx, cel.topo - CENA.BASE_ESPESSURA, cel.cz,
      CELULA, CENA.BASE_ESPESSURA, CELULA);

    for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      if (ocupadas.has(`${cel.i + di}:${cel.j + dj}`)) continue;
      caixa(
        pecas, cel.dono, "medio",
        cel.cx + (di * CELULA) / 2, cel.topo, cel.cz + (dj * CELULA) / 2,
        di === 0 ? CELULA : 0.5, 0.9, dj === 0 ? CELULA : 0.5,
      );
    }
  }

  return ocupadas;
}

// --------------------------------------------------------------- quarteirão

/** Um quarteirão: torre + cornija + laje + janelas + pedestal. Nó `unknown`
 * vira massa bruta — o quarteirão existe, mas sem detalhe e sem luz. */
function gerarQuarteirao(no, pecas) {
  const [x, y, z] = no.position;
  const rot = Math.round(hash01(`${no.hab_id}:rot`) * 3) * (Math.PI / 2);

  if (no.estado === "unknown") {
    const h = 0.9 + hash01(`${no.hab_id}:massa`) * 2.1;
    const w = 2.5 + hash01(`${no.hab_id}:mw`) * 1.3;
    caixa(pecas, no.biomaId, "escuro", x, CENA.BASE_TOPO, z, w, h, w, rot);
    caixa(pecas, no.biomaId, "escuro", x, CENA.BASE_TOPO + h, z, w * 0.6, 0.45, w * 0.6, rot);
    return;
  }

  const tier = ESTADO_TIER[no.estado];
  const largura = 3.1 + hash01(`${no.hab_id}:w`) * 1.8;
  const baseLaje = y - CENA.LAJE;
  const alturaTorre = baseLaje - 0.3 - CENA.BASE_TOPO;

  if (alturaTorre > 0.25) {
    const larguraTorre = largura * 0.74;
    caixa(pecas, no.biomaId, "escuro", x, CENA.BASE_TOPO, z, larguraTorre, alturaTorre, larguraTorre, rot);

    // Arcada no térreo das torres altas: a massa deixa de ser um bloco e
    // passa a ter apoio visível.
    if (alturaTorre > 3.4) {
      for (let f = 0; f < 4; f++) {
        const ang = rot + (f * Math.PI) / 2;
        const off = larguraTorre / 2 + 0.12;
        arco(
          pecas, no.biomaId, "medio",
          x + Math.sin(ang) * off, CENA.BASE_TOPO, z + Math.cos(ang) * off,
          larguraTorre * 0.62, ang + Math.PI / 2, 0.34, 7,
        );
      }
    }

    // Janelas: a luz que marca o estado da habilidade, fachada por fachada.
    const linhas = Math.max(1, Math.floor((alturaTorre - 1.2) / 1.5));
    for (let l = 0; l < linhas; l++) {
      const yj = CENA.BASE_TOPO + 1.1 + l * 1.5;
      if (yj > baseLaje - 0.7) break;
      for (let f = 0; f < 4; f++) {
        const ang = rot + (f * Math.PI) / 2;
        const off = larguraTorre / 2 + 0.04;
        caixa(
          pecas, no.biomaId, tier.janela,
          x + Math.sin(ang) * off, yj, z + Math.cos(ang) * off,
          largura * 0.28, 0.6, 0.12, ang,
        );
      }
    }
  }

  caixa(pecas, no.biomaId, "medio", x, baseLaje - 0.3, z, largura + 0.75, 0.3, largura + 0.75, rot);
  caixa(pecas, no.biomaId, "claro", x, baseLaje, z, largura, CENA.LAJE, largura, rot);
  caixa(pecas, no.biomaId, "medio", x, y, z, 1.2, 0.34, 1.2, rot + 0.45);

  // Guarda-corpo de canto: dois murinhos que dão escala à laje.
  const cantos = [[1, 1], [-1, -1]];
  for (const [sx, sz] of cantos) {
    caixa(
      pecas, no.biomaId, "medio",
      x + Math.cos(rot) * sx * (largura / 2 - 0.2) - Math.sin(rot) * sz * (largura / 2 - 0.2),
      y,
      z + Math.sin(rot) * sx * (largura / 2 - 0.2) + Math.cos(rot) * sz * (largura / 2 - 0.2),
      0.9, 0.5, 0.24, rot,
    );
  }
}

// ------------------------------------------------------------------ conexão

/** Uma relação vira caminho construído: escadaria quando muda de pavimento,
 * ponte com arco e pilares quando é no mesmo nível. O quanto ela está acesa
 * vem do mesmo `peso` de sempre. */
function gerarConexao(a, pecas) {
  const [x1, y1, z1] = a.from;
  const [x2, y2, z2] = a.to;
  const dx = x2 - x1;
  const dz = z2 - z1;
  const dist = Math.hypot(dx, dz);
  if (dist < 1.2) return;

  const ang = Math.atan2(dx, dz);
  const dy = y2 - y1;
  const tom = a.peso >= 0.75 ? "claro" : a.peso >= 0.45 ? "medio" : "escuro";
  const acesa = a.peso >= 0.75;
  const b = a.biomaId;
  const perp = [Math.cos(ang), -Math.sin(ang)];

  if (dist > 22) {
    // Avenida: vão muito longo não vira ponte no céu. Numa cidade, ligação
    // de ponta a ponta é via no chão — e é isso que mantém o skyline legível
    // em vez de virar um emaranhado de rampas cruzando por cima de tudo.
    // Cota levemente própria por avenida: várias delas se cruzam, e no mesmo
    // plano exato o z-buffer não decide quem está em cima (aparece como
    // listrado sujo nas superfícies).
    const passeio = CENA.BASE_TOPO + 0.09 + hash01(`${a.id}:cota`) * 0.07;
    caixaCentrada(pecas, b, tom, (x1 + x2) / 2, passeio, (z1 + z2) / 2, 2.2, 0.16, dist * 0.94, ang);
    const postes = Math.max(2, Math.floor(dist / 9));
    for (let i = 1; i <= postes; i++) {
      const t = i / (postes + 1);
      const px = x1 + dx * t;
      const pz = z1 + dz * t;
      for (const s of [1, -1]) {
        const lx = px + perp[0] * s * 1.5;
        const lz = pz + perp[1] * s * 1.5;
        caixa(pecas, b, "medio", lx, passeio, lz, 0.2, 1.9, 0.2, ang);
        caixa(pecas, b, acesa ? "brilho" : "brilhoFraco", lx, passeio + 1.9, lz, 0.38, 0.22, 0.38, ang);
      }
    }
    if (a.relation === "prerequisito") gerarPortao({ ...a, from: [x1, passeio, z1], to: [x2, passeio, z2] }, pecas, ang, perp);
    return;
  }

  if (Math.abs(dy) > 0.8 && dist <= 15) {
    // Escadaria: degrau real, com espelho e piso, mais os dois montantes.
    // Só para vãos curtos — num vão longo, 40 degraus viram uma rampa maciça
    // que atravessa a cidade inteira e come toda a leitura do conjunto.
    const degraus = Math.max(7, Math.round(Math.abs(dy) / 0.34));
    const passo = dist / degraus;
    const subida = dy / degraus;
    for (let i = 0; i < degraus; i++) {
      const t = (i + 0.5) / degraus;
      const py = y1 + subida * i;
      caixa(
        pecas, b, tom,
        x1 + dx * t, py - 0.4, z1 + dz * t,
        1.5, 0.4 + Math.abs(subida), passo * 1.08, ang,
      );
    }
    if (dist < 12) {
      const meioY = (y1 + y2) / 2;
      const inclinacao = -Math.atan2(dy, dist);
      for (const s of [1, -1]) {
        caixaCentrada(
          pecas, b, acesa ? "claro" : "medio",
          (x1 + x2) / 2 + perp[0] * s * 0.86, meioY - 0.1, (z1 + z2) / 2 + perp[1] * s * 0.86,
          0.18, 0.5, Math.hypot(dist, dy), ang, inclinacao,
        );
      }
    }
  } else if (Math.abs(dy) > 0.8) {
    // Viaduto: tabuleiro inclinado apoiado em pilares. É como um vão longo
    // vence desnível numa cidade — não com uma escadaria de 40 degraus.
    const comprimento = Math.hypot(dist, dy);
    const inclinacao = -Math.atan2(dy, dist);
    const meioY = (y1 + y2) / 2;
    caixaCentrada(pecas, b, tom, (x1 + x2) / 2, meioY - 0.3, (z1 + z2) / 2, 1.7, 0.32, comprimento, ang, inclinacao);
    for (const s of [1, -1]) {
      caixaCentrada(
        pecas, b, acesa ? "brilhoFraco" : "medio",
        (x1 + x2) / 2 + perp[0] * s * 0.84, meioY + 0.1, (z1 + z2) / 2 + perp[1] * s * 0.84,
        0.15, 0.24, comprimento * 0.98, ang, inclinacao,
      );
    }
    for (const t of [0.28, 0.55, 0.82]) {
      const py = y1 + dy * t;
      const altura = py - 0.5 - CENA.BASE_TOPO;
      if (altura < 1.2) continue;
      caixa(pecas, b, "escuro", x1 + dx * t, CENA.BASE_TOPO, z1 + dz * t, 0.62, altura, 0.62, ang);
      caixa(pecas, b, "medio", x1 + dx * t, py - 0.62, z1 + dz * t, 1.1, 0.3, 1.1, ang);
    }
  } else {
    // Ponte: tabuleiro + guarda-corpo + arco sob o vão + pilares até o plinto.
    const meioY = (y1 + y2) / 2;
    caixaCentrada(pecas, b, tom, (x1 + x2) / 2, meioY - 0.32, (z1 + z2) / 2, 1.9, 0.34, dist, ang);
    for (const s of [1, -1]) {
      caixaCentrada(
        pecas, b, acesa ? "brilhoFraco" : "medio",
        (x1 + x2) / 2 + perp[0] * s * 0.92, meioY + 0.12, (z1 + z2) / 2 + perp[1] * s * 0.92,
        0.16, 0.26, dist * 0.98, ang,
      );
    }

    const alturaLivre = meioY - 0.5 - CENA.BASE_TOPO;
    if (dist > 7 && alturaLivre > 1.6) {
      const vao = Math.min(dist * 0.5, alturaLivre * 1.9);
      arco(pecas, b, "medio", (x1 + x2) / 2, meioY - 0.5 - vao / 2, (z1 + z2) / 2, vao, ang, 0.38, 9);
      for (const t of [0.22, 0.78]) {
        caixa(
          pecas, b, "escuro",
          x1 + dx * t, CENA.BASE_TOPO, z1 + dz * t,
          0.7, meioY - 0.5 - CENA.BASE_TOPO, 0.7, ang,
        );
      }
    } else if (dist > 4 && alturaLivre > 1) {
      caixa(pecas, b, "escuro", (x1 + x2) / 2, CENA.BASE_TOPO, (z1 + z2) / 2, 0.7, alturaLivre, 0.7, ang);
    }
  }

  if (a.relation === "prerequisito") gerarPortao(a, pecas, ang, perp);
}

/** Portão de pré-requisito: pilastras + verga sobre o caminho, seladas
 * enquanto a habilidade de origem não estiver dominada. É LEITURA, não trava:
 * o nó de destino continua clicável (o backend nunca bloqueou nada). */
function gerarPortao(a, pecas, ang, perp) {
  const [x1, y1, z1] = a.from;
  const [x2, y2, z2] = a.to;
  const t = 0.26;
  const px = x1 + (x2 - x1) * t;
  const pz = z1 + (z2 - z1) * t;
  const py = y1 + (y2 - y1) * t;
  const selado = !a.sourceMastered;
  const tomPortao = selado ? "medio" : "claro";
  const b = a.biomaId;

  for (const s of [1, -1]) {
    caixa(
      pecas, b, tomPortao,
      px + perp[0] * s * 1.15, py, pz + perp[1] * s * 1.15,
      0.42, 2.4, 0.42, ang,
    );
  }
  caixa(pecas, b, tomPortao, px, py + 2.4, pz, 3.1, 0.42, 0.5, ang);
  caixa(
    pecas, b, selado ? "escuro" : "brilho",
    px, py + 2.05, pz,
    selado ? 2.3 : 2.6, selado ? 2.0 : 0.16, selado ? 0.18 : 0.2, ang,
  );
}

// ----------------------------------------------------------------- landmarks

/** A peça-assinatura de cada distrito — o que faz olhar de longe e saber
 * onde se está. */
function gerarLandmark(biomaId, pecas) {
  const arq = BIOMA_ARCHETYPES[biomaId];
  const a = CENA.ANCORA_MUNDO[biomaId];
  const base = CENA.alturaDeNivel(arq.nivelBase) - CENA.LAJE;
  const x = a.x;
  const z = a.z;

  switch (arq.landmark) {
    case "patio": {
      // Pátio de observação: lâmina d'água luminosa cercada de colunas.
      cilindro(pecas, biomaId, "claro", x, base, z, 11, 0.55);
      cilindro(pecas, biomaId, "brilhoFraco", x, base + 0.55, z, 6.4, 0.12);
      for (let i = 0; i < 10; i++) {
        const ang = (i / 10) * Math.PI * 2;
        cilindro(pecas, biomaId, "medio", x + Math.cos(ang) * 4.6, base + 0.55, z + Math.sin(ang) * 4.6, 0.5, 2.6);
      }
      anel(pecas, biomaId, "brilho", x, base + 3.4, z, 5.6);
      cone(pecas, biomaId, "claro", x, base + 0.6, z, 1.6, 2.2);
      break;
    }
    case "escadaria": {
      // Duas escadarias que se cruzam e sobem para um patamar com arco.
      for (const giro of [0, Math.PI / 2]) {
        for (let i = 0; i < 9; i++) {
          const u = -6 + i * 1.35;
          caixa(
            pecas, biomaId, i % 2 ? "claro" : "medio",
            x + Math.sin(giro) * u, base + i * 0.5, z + Math.cos(giro) * u,
            3.0, 0.5 + 0.5, 1.35, giro,
          );
        }
      }
      caixa(pecas, biomaId, "claro", x, base + 4.5, z, 5.2, 0.6, 5.2);
      arco(pecas, biomaId, "claro", x, base + 5.1, z, 4.2, 0, 0.45, 9);
      caixa(pecas, biomaId, "brilho", x, base + 5.3, z, 0.9, 0.9, 0.9, Math.PI / 4);
      break;
    }
    case "torre-grade": {
      // Torre-grade: pavimentos abertos empilhados — estrutura à mostra.
      const pav = 6;
      for (let p = 0; p < pav; p++) {
        const y = base + p * 2.1;
        const r = 2.6 - p * 0.18;
        for (let c = 0; c < 4; c++) {
          const ang = (c / 4) * Math.PI * 2 + Math.PI / 4;
          caixa(pecas, biomaId, "medio", x + Math.cos(ang) * r, y, z + Math.sin(ang) * r, 0.42, 2.1, 0.42);
        }
        caixa(pecas, biomaId, p % 2 ? "claro" : "medio", x, y + 2.1, z, r * 2.5, 0.4, r * 2.5, Math.PI / 4);
        if (p % 2 === 0) caixa(pecas, biomaId, "brilhoFraco", x, y + 0.7, z, r * 1.5, 0.7, 0.14, Math.PI / 4);
      }
      cone(pecas, biomaId, "brilho", x, base + pav * 2.1, z, 1.5, 2.4);
      break;
    }
    case "observatorio": {
      // Observatório: torre cilíndrica, balcão em anel e luneta apontada.
      cilindro(pecas, biomaId, "escuro", x, base, z, 4.6, 6.5);
      cilindro(pecas, biomaId, "medio", x, base + 6.5, z, 5.6, 0.5);
      anel(pecas, biomaId, "claro", x, base + 6.9, z, 6.2);
      cilindro(pecas, biomaId, "claro", x, base + 7.0, z, 3.4, 1.9);
      for (let i = 0; i < 6; i++) {
        const ang = (i / 6) * Math.PI * 2;
        caixa(pecas, biomaId, "brilhoFraco", x + Math.cos(ang) * 2.35, base + 2.2, z + Math.sin(ang) * 2.35, 0.5, 3.2, 0.14, -ang);
      }
      caixaCentrada(pecas, biomaId, "brilho", x + 1.2, base + 9.4, z + 1.2, 0.6, 0.6, 3.6, Math.PI / 4, -0.55);
      cone(pecas, biomaId, "claro", x, base + 8.9, z, 1.2, 1.6);
      break;
    }
    case "anfiteatro": {
      // Bacia: degraus concêntricos descendo até um núcleo de luz. É para cá
      // que as pontes dos outros distritos desembocam.
      const aneis = [[9.5, 1.7], [7.6, 1.15], [5.8, 0.6], [4.0, 0.1]];
      for (const [r, y] of aneis) {
        cilindro(pecas, biomaId, "medio", x, base + y, z, r * 2, 0.55);
      }
      cilindro(pecas, biomaId, "claro", x, base, z, 5.2, 0.2);
      cilindro(pecas, biomaId, "brilho", x, base + 0.2, z, 2.6, 0.3);
      for (let i = 0; i < 8; i++) {
        const ang = (i / 8) * Math.PI * 2;
        caixa(pecas, biomaId, "claro", x + Math.cos(ang) * 9.9, base + 1.7, z + Math.sin(ang) * 9.9, 0.7, 2.6, 0.7, -ang);
      }
      anel(pecas, biomaId, "brilhoFraco", x, base + 4.6, z, 7.4);
      break;
    }
    case "portico": {
      // Pórtico do cume: colunata pesada e um volume suspenso sobre ela.
      caixa(pecas, biomaId, "medio", x, base - 0.6, z, 12, 0.6, 7.5);
      caixa(pecas, biomaId, "claro", x, base, z, 11, 0.5, 6.8);
      for (let i = 0; i < 6; i++) {
        const px = x - 4.2 + i * 1.7;
        cilindro(pecas, biomaId, "claro", px, base + 0.5, z - 1.6, 0.85, 3.6);
        cilindro(pecas, biomaId, "medio", px, base + 0.5, z + 1.6, 0.85, 3.6);
      }
      caixa(pecas, biomaId, "claro", x, base + 4.1, z, 11.4, 0.75, 7.2);
      caixa(pecas, biomaId, "medio", x, base + 4.85, z, 6.5, 0.4, 4.4);
      caixaCentrada(pecas, biomaId, "brilho", x, base + 7.4, z, 2.6, 2.6, 2.6, Math.PI / 4, 0.3);
      for (const s of [1, -1]) {
        caixa(pecas, biomaId, "brilhoFraco", x + s * 5.2, base + 0.5, z, 0.3, 3.4, 0.3);
      }
      break;
    }
    default:
      break;
  }
}

// ------------------------------------------------------------------ adereços

/** Arcos soltos, escadas que não levam a lugar nenhum, obeliscos e blocos
 * suspensos: é o que enche o vazio entre quarteirões e faz o conjunto ler
 * como cidade, não como diagrama. */
function gerarAderecos(nos, ocupadas, pecas) {
  for (const cel of ocupadas.values()) {
    const semente = `${cel.i}:${cel.j}:adereco`;
    const sorte = hash01(semente);
    if (sorte > 0.5) continue;

    let livre = true;
    for (const no of nos) {
      if (Math.hypot(no.position[0] - cel.cx, no.position[2] - cel.cz) < 4.6) {
        livre = false;
        break;
      }
    }
    if (!livre) continue;
    for (const id of CENA.BIOMA_IDS) {
      const a = CENA.ANCORA_MUNDO[id];
      if (Math.hypot(a.x - cel.cx, a.z - cel.cz) < 9) {
        livre = false;
        break;
      }
    }
    if (!livre) continue;

    const tipo = Math.floor(hash01(`${semente}:tipo`) * 5);
    const rot = hash01(`${semente}:rot`) * Math.PI * 2;
    const b = cel.dono;
    const topo = cel.topo;

    switch (tipo) {
      case 0: // arco solto
        arco(pecas, b, "medio", cel.cx, topo, cel.cz, 2.6 + hash01(semente + "v") * 1.4, rot, 0.36, 8);
        break;
      case 1: { // escada para lugar nenhum
        const n = 5 + Math.floor(hash01(`${semente}:n`) * 4);
        for (let i = 0; i < n; i++) {
          caixa(
            pecas, b, i % 2 ? "claro" : "medio",
            cel.cx + Math.sin(rot) * (i * 0.62 - 1.2), topo, cel.cz + Math.cos(rot) * (i * 0.62 - 1.2),
            1.7, 0.42 + i * 0.42, 0.62, rot,
          );
        }
        break;
      }
      case 2: { // obelisco
        const h = 2.4 + hash01(`${semente}:h`) * 2.6;
        caixa(pecas, b, "medio", cel.cx, topo, cel.cz, 0.9, h, 0.9, rot);
        cone(pecas, b, "brilhoFraco", cel.cx, topo + h, cel.cz, 0.9, 0.9, rot);
        break;
      }
      case 3: { // muro baixo com vão
        caixa(pecas, b, "escuro", cel.cx, topo, cel.cz, 3.2, 1.1, 0.5, rot);
        caixa(pecas, b, "medio", cel.cx, topo + 1.1, cel.cz, 3.2, 0.25, 0.7, rot);
        break;
      }
      default: { // bloco suspenso
        const h = 3.4 + hash01(`${semente}:s`) * 2.4;
        caixaCentrada(
          pecas, b, "claro", cel.cx, topo + h, cel.cz,
          1.9, 1.9, 1.9, rot, 0.28,
        );
        caixa(pecas, b, "brilhoFraco", cel.cx, topo + h - 1.4, cel.cz, 0.16, 1.2, 0.16);
        break;
      }
    }
  }
}

// ---------------------------------------------------------------------- API

/** Monta a cidade inteira a partir da cena. Retorna a lista plana de peças —
 * ~1.5k volumes, todos instanciáveis por (distrito × tom × forma). */
export function construirCidade({ nos, arestas }) {
  const pecas = [];
  const ocupadas = gerarPlinto(nos, pecas);
  for (const no of nos) gerarQuarteirao(no, pecas);
  for (const a of arestas) gerarConexao(a, pecas);
  for (const id of CENA.BIOMA_IDS) gerarLandmark(id, pecas);
  gerarAderecos(nos, ocupadas, pecas);
  return pecas;
}
