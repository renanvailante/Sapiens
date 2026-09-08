// Gerador do CONTINENTE FLUTUANTE — paisagem natural atravessada por
// arquitetura impossível.
//
// Entra a descrição de cena (nós, rotas) e sai uma lista plana de "peças":
// volumes primitivos com posição, tamanho, rotação, distrito e tom. Nada
// aqui sabe o que é React ou Three — `Cidade.jsx` só instancia o que esta
// lista descreve.
//
// Vocabulário da paisagem:
//   ilha        massa de terra em platôs, com penhasco estratificado na
//               borda e raiz de rocha mergulhando no vazio
//   montanha    serra de base larga que fecha o horizonte e abre vale
//   rio         curso d'água que atravessa a ilha e despenca no abismo
//   lago        espelho d'água numa depressão do terreno
//   bosque      árvores com densidade e forma próprias de cada bioma, mais
//               sub-bosque (moitas, pedras soltas, troncos caídos)
//   rocha       afloramento — e é também o que é uma habilidade ainda não
//               descoberta: natureza bruta, antes de virar construção
//   ilhota      plataforma natural solta, orbitando a ilha principal
//
// Vocabulário construído:
//   quarteirão  torre + cornija + laje onde uma habilidade se apoia
//   rota        parábola fina entre dois nós, como rota de voo
//   landmark    a estrutura-assinatura da ilha, em escala monumental
//
// Tudo determinístico (hash por `hab_id`/`bioma_id`): mesmo mundo para todo
// aluno, em todo carregamento.
import * as CENA from "./sceneBuilder";
import { BIOMA_ARCHETYPES, ESTADO_TIER } from "./biomaArchetypes";
import { hash01, seededNoise2D } from "./noise";

/** Lado da placa de terreno. Cresce junto com o mundo: placa pequena num
 * continente grande vira cascalho e devolve a leitura de maquete. */
const CELULA = 12;
/** Landmarks e quarteirões são desenhados numa escala de referência e depois
 * ampliados — mexer em 60 números à mão a cada mudança de escala do mundo é
 * como a proporção entre eles se perde. */
const ESCALA_MARCO = 4.6;
const ESCALA_NATUREZA = 2.4;

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

/** Bloco irregular — base de toda rocha, moita e copa: um poliedro em
 * proporções desiguais, que nunca lê como caixa. */
function pedra(pecas, bioma, tom, x, y, z, dx, dy, dz, rotY = 0, rotX = 0) {
  pecas.push({ forma: "esfera", bioma, tom, pos: [x, y, z], size: [dx, dy, dz], rotY, rotX });
}

/** Arco de volta inteira em aduelas — vão vencido por curva, não por viga. */
function arco(pecas, bioma, tom, cx, base, cz, vao, ang, espessura = 0.42, aduelas = 9) {
  const r = vao / 2;
  for (let i = 0; i < aduelas; i++) {
    const t = ((i + 0.5) / aduelas) * Math.PI;
    const u = -r * Math.cos(t);
    caixaCentrada(
      pecas, bioma, tom,
      cx + Math.sin(ang) * u, base + r * Math.sin(t), cz + Math.cos(ang) * u,
      espessura, espessura, ((Math.PI * r) / aduelas) * 1.25,
      ang, t - Math.PI / 2,
    );
  }
}

/** Amplia um conjunto de peças em torno de um ponto de apoio. É o que
 * permite desenhar landmark e quarteirão numa escala confortável de ler no
 * código e ampliá-los junto com o mundo sem redigitar cada número. */
function ampliar(destino, locais, ancoraX, ancoraY, ancoraZ, k) {
  for (const p of locais) {
    p.pos = [
      ancoraX + (p.pos[0] - ancoraX) * k,
      ancoraY + (p.pos[1] - ancoraY) * k,
      ancoraZ + (p.pos[2] - ancoraZ) * k,
    ];
    p.size = [p.size[0] * k, p.size[1] * k, p.size[2] * k];
    destino.push(p);
  }
}

// --------------------------------------------------------------------- ilha

/** A massa de terra: platôs em degraus largos, penhasco estratificado na
 * borda e raiz de rocha mergulhando no vazio. Devolve a grade para que rio,
 * bosque e montanha saibam onde há chão e em que cota. */
function gerarIlha(biomaId, nosDoBioma, pecas) {
  const arq = BIOMA_ARCHETYPES[biomaId];
  const centro = CENA.ANCORA_MUNDO[biomaId];
  const topo = CENA.alturaIlha(biomaId);
  const ruido = seededNoise2D(`ilha:${biomaId}`);

  // A pegada segue os nós: com o mundo espalhado, eles saem muito além do
  // raio nominal, e a ilha precisa ir junto ou eles ficam boiando fora dela.
  let extensao = arq.raioIlha;
  for (const no of nosDoBioma) {
    extensao = Math.max(extensao, Math.hypot(no.position[0] - centro.x, no.position[2] - centro.z) + 34);
  }
  const alcance = extensao + CELULA * 2;
  const cols = Math.ceil((alcance * 2) / CELULA);
  const origemX = centro.x - alcance;
  const origemZ = centro.z - alcance;
  const celulas = new Map();

  for (let i = 0; i < cols; i++) {
    for (let j = 0; j < cols; j++) {
      const cx = origemX + (i + 0.5) * CELULA;
      const cz = origemZ + (j + 0.5) * CELULA;

      let dentro = Math.hypot(cx - centro.x, cz - centro.z) < arq.raioIlha;
      if (!dentro) {
        for (const no of nosDoBioma) {
          if (Math.hypot(no.position[0] - cx, no.position[2] - cz) < 34) {
            dentro = true;
            break;
          }
        }
      }
      // Recorte orgânico: sem isto a ilha vira um disco e denuncia o raio.
      if (dentro && ruido(cx * 0.0072, cz * 0.0072) < -0.34) dentro = false;
      if (!dentro) continue;

      // Vale e platô: poucos degraus, bem marcados.
      const degrau = Math.round(ruido(cx * 0.0055, cz * 0.0055) * 2.2) * 3.6;
      celulas.set(`${i}:${j}`, { i, j, cx, cz, topo: topo + degrau });
    }
  }

  for (const cel of celulas.values()) {
    caixa(pecas, biomaId, "medio", cel.cx, cel.topo - 3.2, cel.cz, CELULA, 3.2, CELULA);

    let borda = false;
    for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      if (!celulas.has(`${cel.i + di}:${cel.j + dj}`)) {
        borda = true;
        break;
      }
    }

    if (borda) {
      // Penhasco em estratos: três camadas recuando, como rocha cortada.
      const fundura = 42 + hash01(`${biomaId}:${cel.i}:${cel.j}`) * 40;
      caixa(pecas, biomaId, "escuro", cel.cx, cel.topo - 3.2 - fundura * 0.34, cel.cz, CELULA * 0.99, fundura * 0.34, CELULA * 0.99);
      caixa(pecas, biomaId, "escuro", cel.cx, cel.topo - 3.2 - fundura * 0.72, cel.cz, CELULA * 0.84, fundura * 0.38, CELULA * 0.84);
      caixa(pecas, biomaId, "escuro", cel.cx, cel.topo - 3.2 - fundura, cel.cz, CELULA * 0.62, fundura * 0.28, CELULA * 0.62);
      // Blocos desprendidos na quebra do penhasco.
      if (hash01(`${biomaId}:solto${cel.i}:${cel.j}`) > 0.65) {
        pedra(pecas, biomaId, "escuro", cel.cx, cel.topo - 9, cel.cz, 13, 8, 11,
          hash01(`${biomaId}:sr${cel.i}${cel.j}`) * 3, 0.4);
      }
    } else {
      caixa(pecas, biomaId, "escuro", cel.cx, cel.topo - 15.2, cel.cz, CELULA * 0.98, 12, CELULA * 0.98);
    }
  }

  // Raiz de rocha, em três massas desencontradas: uma peça só vira faceta
  // chapada e engole o penhasco logo acima dela.
  const raioReal = extensao * 0.8;
  for (const [dx, dz, escala, prof] of [
    [0, 0, 1.05, 1.15],
    [raioReal * 0.42, raioReal * 0.3, 0.62, 0.75],
    [-raioReal * 0.36, -raioReal * 0.4, 0.5, 0.6],
  ]) {
    cone(pecas, biomaId, "escuro", centro.x + dx, topo - 26, centro.z + dz,
      raioReal * escala, raioReal * prof, Math.PI);
  }

  return { celulas, origemX, origemZ, cols, topo, centro, extensao };
}

/** Cota do terreno num ponto qualquer da ilha (null fora dela). */
function topoEm(grade, x, z) {
  const i = Math.floor((x - grade.origemX) / CELULA);
  const j = Math.floor((z - grade.origemZ) / CELULA);
  return grade.celulas.get(`${i}:${j}`)?.topo ?? null;
}

function longeDosNos(nos, x, z, raio) {
  for (const no of nos) {
    if (Math.hypot(no.position[0] - x, no.position[2] - z) < raio) return false;
  }
  return true;
}

// ---------------------------------------------------------------- montanhas

/** Serras que fecham o horizonte da ilha e abrem vale. Sempre na periferia:
 * no meio da ilha esconderiam os quarteirões. */
function gerarMontanhas(biomaId, grade, nos, pecas, quantidade, alturaBase) {
  if (quantidade <= 0) return;
  const celulas = [...grade.celulas.values()];
  let postas = 0;

  for (let k = 0; k < 220 && postas < quantidade; k++) {
    const cel = celulas[Math.floor(hash01(`${biomaId}:mont${k}`) * celulas.length)];
    if (!cel) continue;
    if (Math.hypot(cel.cx - grade.centro.x, cel.cz - grade.centro.z) < grade.extensao * 0.42) continue;
    if (!longeDosNos(nos, cel.cx, cel.cz, 52)) continue;

    const h = alturaBase * (0.7 + hash01(`${biomaId}:mh${k}`) * 0.95);
    const base = cel.topo - 5;
    // Base larga e perfil escalonado: serra, não cone isolado.
    cone(pecas, biomaId, "escuro", cel.cx, base, cel.cz, h * 2.4, h * 0.8);
    cone(pecas, biomaId, "escuro", cel.cx + h * 0.34, base, cel.cz - h * 0.28, h * 1.5, h * 0.52);
    cone(pecas, biomaId, "medio", cel.cx - h * 0.22, base, cel.cz + h * 0.24, h * 1.2, h * 0.44);
    cone(pecas, biomaId, "medio", cel.cx, base + h * 0.55, cel.cz, h * 0.62, h * 0.3);
    // Contrafortes: pedras grandes no sopé, que dão pé à montanha.
    for (let n = 0; n < 3; n++) {
      const ang = hash01(`${biomaId}:cf${k}${n}`) * Math.PI * 2;
      pedra(pecas, biomaId, "escuro",
        cel.cx + Math.cos(ang) * h * 1.1, base + 2, cel.cz + Math.sin(ang) * h * 1.1,
        h * 0.4, h * 0.22, h * 0.34, ang, 0.2);
    }
    postas += 1;
  }
}

// --------------------------------------------------------------------- água

function gerarCurso(biomaId, grade, pecas, semente, dirBase) {
  const centro = grade.centro;
  const dir = dirBase;
  const passo = CELULA * 0.55;
  const perp = dir + Math.PI / 2;
  let ultimo = null;

  for (let s = -40; s < 160; s++) {
    const t = s * passo;
    const desvio = Math.sin(s * 0.11 + hash01(`${semente}:fase`) * 6) * 26;
    const x = centro.x + Math.cos(dir) * t + Math.cos(perp) * desvio;
    const z = centro.z + Math.sin(dir) * t + Math.sin(perp) * desvio;
    const topo = topoEm(grade, x, z);

    if (topo === null) {
      // O rio chegou à borda: vira queda d'água caindo para a névoa.
      if (ultimo) {
        const queda = 70 + hash01(`${semente}:queda`) * 50;
        caixa(pecas, biomaId, "agua", ultimo.x, ultimo.topo - 0.9 - queda, ultimo.z, 9, queda, 3.4, dir);
        for (let n = 0; n < 5; n++) {
          pedra(pecas, biomaId, "nevoa",
            ultimo.x + (hash01(`${semente}:qn${n}`) - 0.5) * 24,
            ultimo.topo - queda - 4 + hash01(`${semente}:qh${n}`) * 16,
            ultimo.z + (hash01(`${semente}:qz${n}`) - 0.5) * 24,
            34, 18, 34);
        }
      }
      break;
    }

    const largura = 7.5 + Math.sin(s * 0.3) * 2.4;
    caixa(pecas, biomaId, "agua", x, topo - 1.1, z, largura, 0.9, passo * 1.4, dir);
    // Margens: a água precisa de barranco, senão vira fita colada no chão.
    for (const lado of [1, -1]) {
      caixa(pecas, biomaId, "escuro",
        x + Math.cos(perp) * lado * (largura / 2 + 1.8), topo - 2.6,
        z + Math.sin(perp) * lado * (largura / 2 + 1.8),
        3.6, 2.6, passo * 1.4, dir);
      if (hash01(`${semente}:seixo${s}${lado}`) > 0.72) {
        pedra(pecas, biomaId, "medio",
          x + Math.cos(perp) * lado * (largura / 2 + 4), topo - 0.4,
          z + Math.sin(perp) * lado * (largura / 2 + 4),
          5, 2.6, 4.2, hash01(`${semente}:sr${s}`) * 3);
      }
    }
    ultimo = { x, z, topo };
  }
}

/** Rios que atravessam a ilha e despencam no abismo, mais um lago numa
 * depressão. A água é o que impede a paisagem de virar só pedra e caixa. */
function gerarAgua(biomaId, grade, nos, pecas, perfil) {
  if (perfil.rio) {
    const dir = hash01(`${biomaId}:riodir`) * Math.PI * 2;
    gerarCurso(biomaId, grade, pecas, `${biomaId}:rio1`, dir);
    // Um segundo curso, cruzando o primeiro em ângulo aberto.
    gerarCurso(biomaId, grade, pecas, `${biomaId}:rio2`, dir + 1.9 + hash01(`${biomaId}:rio2ang`) * 0.7);
  }

  if (perfil.lago) {
    const celulas = [...grade.celulas.values()];
    let alvo = null;
    for (const cel of celulas) {
      if (!longeDosNos(nos, cel.cx, cel.cz, 45)) continue;
      if (!alvo || cel.topo < alvo.topo) alvo = cel;
    }
    if (alvo) {
      const raio = CELULA * (1.8 + hash01(`${biomaId}:lago`) * 1.3);
      cilindro(pecas, biomaId, "agua", alvo.cx, alvo.topo - 1.6, alvo.cz, raio * 2, 1.2);
      for (let k = 0; k < 10; k++) {
        const ang = (k / 10) * Math.PI * 2;
        pedra(pecas, biomaId, "escuro",
          alvo.cx + Math.cos(ang) * raio * 1.05, alvo.topo - 1.2, alvo.cz + Math.sin(ang) * raio * 1.05,
          10, 4.5, 8, ang);
      }
    }
  }
}

// ------------------------------------------------------------ bosque e rocha

const PERFIL_NATUREZA = {
  cerrado: { arvores: 0.26, rochas: 0.34, montanhas: 5, alturaMontanha: 62, rio: true, lago: false, arvore: "esparsa" },
  mata: { arvores: 0.66, rochas: 0.1, montanhas: 6, alturaMontanha: 72, rio: true, lago: true, arvore: "densa" },
  caatinga: { arvores: 0.2, rochas: 0.46, montanhas: 8, alturaMontanha: 84, rio: false, lago: false, arvore: "seca" },
  amazonia: { arvores: 0.72, rochas: 0.08, montanhas: 5, alturaMontanha: 68, rio: true, lago: true, arvore: "gigante" },
  pantanal: { arvores: 0.36, rochas: 0.07, montanhas: 0, alturaMontanha: 0, rio: true, lago: true, arvore: "touceira" },
  pampas: { arvores: 0.1, rochas: 0.16, montanhas: 2, alturaMontanha: 46, rio: true, lago: false, arvore: "solitaria" },
};

function gerarArvore(pecas, biomaId, tipo, x, y, z, g, e = ESCALA_NATUREZA) {
  switch (tipo) {
    case "densa": {
      const h = (6 + g("h") * 5) * e;
      cilindro(pecas, biomaId, "escuro", x, y, z, 1.4 * e, h);
      pedra(pecas, biomaId, "medio", x, y + h + 1.4 * e, z, 5.4 * e, 4.8 * e, 5.4 * e, g("r") * 3);
      pedra(pecas, biomaId, "claro", x + 0.9 * e, y + h + 3.2 * e, z - 0.7 * e, 3.2 * e, 2.8 * e, 3.2 * e, g("r2") * 3);
      break;
    }
    case "gigante": {
      const h = (10 + g("h") * 8) * e;
      cilindro(pecas, biomaId, "escuro", x, y, z, 2.2 * e, h);
      pedra(pecas, biomaId, "medio", x, y + h + 2 * e, z, 8 * e, 7 * e, 8 * e, g("r") * 3);
      pedra(pecas, biomaId, "claro", x - 1.3 * e, y + h + 4.4 * e, z + 1 * e, 4.8 * e, 4.2 * e, 4.8 * e, g("r2") * 3);
      break;
    }
    case "seca": {
      // Caatinga: tronco nu e ramos angulares — vegetação sem copa.
      const h = (4.5 + g("h") * 3.5) * e;
      cilindro(pecas, biomaId, "escuro", x, y, z, 0.8 * e, h);
      for (let k = 0; k < 3; k++) {
        const ang = g(`b${k}`) * Math.PI * 2;
        caixaCentrada(pecas, biomaId, "medio",
          x + Math.cos(ang) * 1.6 * e, y + h * (0.6 + k * 0.14), z + Math.sin(ang) * 1.6 * e,
          0.5 * e, 0.5 * e, 3.4 * e, ang, -0.7);
      }
      break;
    }
    case "touceira": {
      // Pantanal: moitas baixas e juncos na beira d'água.
      pedra(pecas, biomaId, "medio", x, y + 1 * e, z, 5.5 * e, 2.4 * e, 5 * e, g("r") * 3);
      for (let k = 0; k < 4; k++) {
        cilindro(pecas, biomaId, "claro", x + (g(`j${k}`) - 0.5) * 4 * e, y, z + (g(`k${k}`) - 0.5) * 4 * e,
          0.28 * e, (2.6 + g(`l${k}`) * 2.2) * e);
      }
      break;
    }
    case "solitaria": {
      const h = (7 + g("h") * 4.5) * e;
      cilindro(pecas, biomaId, "escuro", x, y, z, 1.5 * e, h);
      pedra(pecas, biomaId, "medio", x, y + h + 1.2 * e, z, 5 * e, 4.4 * e, 5 * e, g("r") * 3);
      break;
    }
    default: {
      // Cerrado: copa larga e baixa, tronco torto, muito espaço em volta.
      const h = (4.5 + g("h") * 3) * e;
      cilindro(pecas, biomaId, "escuro", x, y, z, 1.2 * e, h);
      pedra(pecas, biomaId, "medio", x, y + h + 1 * e, z, 5.6 * e, 3.4 * e, 5.4 * e, g("r") * 3);
      break;
    }
  }
}

function gerarBosqueERochas(biomaId, grade, nos, pecas, perfil) {
  for (const cel of grade.celulas.values()) {
    const semente = `${biomaId}:${cel.i}:${cel.j}`;
    const g = (k) => hash01(`${semente}:${k}`);
    if (!longeDosNos(nos, cel.cx, cel.cz, 26)) continue;
    if (Math.hypot(cel.cx - grade.centro.x, cel.cz - grade.centro.z) < 48) continue;

    const sorte = hash01(semente);
    const x = cel.cx + (g("jx") - 0.5) * CELULA * 0.8;
    const z = cel.cz + (g("jz") - 0.5) * CELULA * 0.8;

    if (sorte < perfil.arvores) {
      gerarArvore(pecas, biomaId, perfil.arvore, x, cel.topo, z, g);
      // Adensamento: onde tem uma árvore, costuma ter outras ao lado.
      const vizinhas = perfil.arvores > 0.5 ? 3 : 1;
      for (let v = 1; v <= vizinhas; v++) {
        if (g(`par${v}`) < 0.45) continue;
        const ang = g(`pa${v}`) * Math.PI * 2;
        const r = CELULA * (0.28 + g(`pr${v}`) * 0.3);
        gerarArvore(pecas, biomaId, perfil.arvore, x + Math.cos(ang) * r, cel.topo, z + Math.sin(ang) * r,
          (k) => hash01(`${semente}:${v}${k}`), ESCALA_NATUREZA * (0.7 + g(`pe${v}`) * 0.4));
      }
    } else if (sorte < perfil.arvores + perfil.rochas) {
      // Afloramento rochoso: blocos irregulares empilhados.
      const n = 2 + Math.floor(g("n") * 4);
      for (let k = 0; k < n; k++) {
        pedra(pecas, biomaId, k === 0 ? "escuro" : "medio",
          x + (g(`rx${k}`) - 0.5) * 14, cel.topo + 1.4 + k * 3.6, z + (g(`rz${k}`) - 0.5) * 14,
          14 - k * 2.6, 8 - k * 1.2, 12 - k * 2.2, g(`rr${k}`) * 3, g(`rp${k}`) * 0.5);
      }
    }

    // Sub-bosque: o que enche o chão entre uma coisa e outra. Sem isto o
    // terreno grande fica com cara de tabuleiro vazio.
    if (g("sub") > 0.45) {
      const n = 1 + Math.floor(g("subn") * 3);
      for (let k = 0; k < n; k++) {
        const sx = cel.cx + (g(`sx${k}`) - 0.5) * CELULA;
        const sz = cel.cz + (g(`sz${k}`) - 0.5) * CELULA;
        if (g(`st${k}`) > 0.55) {
          pedra(pecas, biomaId, "escuro", sx, cel.topo + 0.7, sz, 4.4, 1.8, 3.6, g(`sr${k}`) * 3);
        } else {
          pedra(pecas, biomaId, "medio", sx, cel.topo + 1.1, sz, 3.2, 2.4, 3, g(`sr${k}`) * 3);
        }
      }
    }
  }
}

/** Ilhotas soltas orbitando a ilha: reforçam a leitura de arquipélago e dão
 * o que olhar no meio do vazio. */
function gerarIlhotas(biomaId, grade, pecas) {
  const arq = BIOMA_ARCHETYPES[biomaId];
  const perfil = PERFIL_NATUREZA[arq.vegetacao] ?? PERFIL_NATUREZA.cerrado;
  for (let k = 0; k < 6; k++) {
    const ang = hash01(`${biomaId}:ilhota${k}`) * Math.PI * 2;
    const dist = grade.extensao + 40 + hash01(`${biomaId}:ilhotad${k}`) * 150;
    const x = grade.centro.x + Math.cos(ang) * dist;
    const z = grade.centro.z + Math.sin(ang) * dist;
    const y = grade.topo + (hash01(`${biomaId}:ilhotay${k}`) - 0.35) * 90;
    const r = 12 + hash01(`${biomaId}:ilhotar${k}`) * 16;

    cilindro(pecas, biomaId, "medio", x, y - 4, z, r * 2, 4);
    cone(pecas, biomaId, "escuro", x, y - 4, z, r * 1.8, r * 2.6, Math.PI);
    const n = 1 + Math.floor(hash01(`${biomaId}:ilhotan${k}`) * 3);
    for (let v = 0; v < n; v++) {
      const av = hash01(`${biomaId}:ilhotaav${k}${v}`) * Math.PI * 2;
      const rv = hash01(`${biomaId}:ilhotarv${k}${v}`) * r * 0.6;
      gerarArvore(pecas, biomaId, perfil.arvore, x + Math.cos(av) * rv, y, z + Math.sin(av) * rv,
        (kk) => hash01(`${biomaId}:ilhotaa${k}${v}${kk}`));
    }
  }
}

// --------------------------------------------------------------- quarteirão

function gerarQuarteirao(no, pecas) {
  const [x, y, z] = no.position;
  const solo = CENA.alturaIlha(no.biomaId);
  const rot = Math.round(hash01(`${no.hab_id}:rot`) * 3) * (Math.PI / 2);
  const g = (k) => hash01(`${no.hab_id}:${k}`);

  if (no.estado === "unknown") {
    // Ainda não descoberto: natureza bruta, sem nada construído em cima.
    for (let k = 0; k < 4; k++) {
      pedra(pecas, no.biomaId, k === 0 ? "escuro" : "medio",
        x + (g(`px${k}`) - 0.5) * 22, solo + 3 + k * 5.5, z + (g(`pz${k}`) - 0.5) * 22,
        26 - k * 4.5, 14 - k * 2.4, 22 - k * 4, g(`pr${k}`) * 3, g(`pp${k}`) * 0.4);
    }
    return;
  }

  const locais = [];
  const tier = ESTADO_TIER[no.estado];
  const largura = 5.5 + g("w") * 3;
  const alturaLocal = (y - solo) / ESCALA_MARCO; // altura do pavimento, na escala de desenho
  const baseLaje = alturaLocal - CENA.LAJE / ESCALA_MARCO;
  const alturaTorre = baseLaje - 0.3;

  if (alturaTorre > 0.25) {
    const lt = largura * 0.7;
    caixa(locais, no.biomaId, "escuro", x, 0, z, lt, alturaTorre, lt, rot);
    if (alturaTorre > 3.4) {
      for (let f = 0; f < 4; f++) {
        const ang = rot + (f * Math.PI) / 2;
        arco(locais, no.biomaId, "medio", x + Math.sin(ang) * (lt / 2 + 0.14), 0, z + Math.cos(ang) * (lt / 2 + 0.14),
          lt * 0.6, ang + Math.PI / 2, 0.42, 7);
      }
    }
    const linhas = Math.max(1, Math.floor((alturaTorre - 1.4) / 2.1));
    for (let l = 0; l < linhas; l++) {
      const yj = 1.4 + l * 2.1;
      if (yj > baseLaje - 1) break;
      for (let f = 0; f < 4; f++) {
        const ang = rot + (f * Math.PI) / 2;
        caixa(locais, no.biomaId, tier.janela, x + Math.sin(ang) * (lt / 2 + 0.05), yj, z + Math.cos(ang) * (lt / 2 + 0.05),
          largura * 0.24, 0.8, 0.14, ang);
      }
    }
  }

  caixa(locais, no.biomaId, "medio", x, baseLaje - 0.45, z, largura + 1.2, 0.45, largura + 1.2, rot);
  caixa(locais, no.biomaId, "claro", x, baseLaje, z, largura, CENA.LAJE / ESCALA_MARCO, largura, rot);

  ampliar(pecas, locais, x, solo, z, ESCALA_MARCO);
}

// --------------------------------------------------------------------- rota

/** Rota parabólica entre dois nós — fio de energia sobre a paisagem, não
 * protagonista: fina, discreta, e só acesa de verdade quando a ligação já
 * foi dominada. Pré-requisito ainda não dominado sai da origem e se
 * interrompe no meio do caminho (leitura, não trava). */
function gerarRota(a, pecas) {
  const [x1, y1, z1] = a.from;
  const [x2, y2, z2] = a.to;
  const dx = x2 - x1;
  const dz = z2 - z1;
  const plano = Math.hypot(dx, dz);
  if (plano < 1) return;

  const apice = Math.min(24 + plano * 0.13, 210);
  const segmentos = Math.max(18, Math.min(44, Math.round(plano / 20)));
  const acesa = a.peso >= 0.75;
  const tom = acesa ? "brilho" : "brilhoFraco";
  const espessura = acesa ? 0.85 : 0.55;
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
      espessura, espessura, Math.hypot(horizontal, sy) * 1.05,
      Math.atan2(sx, sz), -Math.atan2(sy, horizontal),
    );
  }
}

// ----------------------------------------------------------------- landmarks

/** A estrutura-assinatura da ilha, em escala monumental: o que se enxerga do
 * outro lado do continente e orienta a exploração. Desenhada numa escala de
 * referência e ampliada por `ESCALA_MARCO`. */
function gerarLandmark(biomaId, pecas) {
  const centro = CENA.ANCORA_MUNDO[biomaId];
  const base = CENA.alturaIlha(biomaId);
  const x = centro.x;
  const z = centro.z;
  const arq = BIOMA_ARCHETYPES[biomaId];
  const l = [];

  switch (arq.landmark) {
    case "mirante": {
      // Cerrado: rocha escalonada com plataforma de horizonte no topo.
      for (let i = 0; i < 5; i++) {
        cilindro(l, biomaId, i % 2 ? "medio" : "escuro", x, base + i * 4.4, z, (20 - i * 3.4) * 2, 4.4);
      }
      cilindro(l, biomaId, "claro", x, base + 22, z, 17, 1.4);
      for (let i = 0; i < 14; i++) {
        const ang = (i / 14) * Math.PI * 2;
        cilindro(l, biomaId, "claro", x + Math.cos(ang) * 7.4, base + 23.4, z + Math.sin(ang) * 7.4, 1.1, 7);
      }
      anel(l, biomaId, "brilho", x, base + 31, z, 17);
      cone(l, biomaId, "claro", x, base + 23.4, z, 4.4, 8);
      break;
    }
    case "passarelas": {
      // Mata Atlântica: passarelas suspensas cruzando sobre a copa.
      for (let i = 0; i < 5; i++) {
        const ang = (i / 5) * Math.PI * 2;
        const px = x + Math.cos(ang) * 13;
        const pz = z + Math.sin(ang) * 13;
        cilindro(l, biomaId, "escuro", px, base, pz, 3.4, 22 + i * 2.2);
        caixa(l, biomaId, "claro", px, base + 22 + i * 2.2, pz, 8.5, 1.1, 8.5, ang);
      }
      for (let i = 0; i < 5; i++) {
        const a1 = (i / 5) * Math.PI * 2;
        const a2 = ((i + 2) / 5) * Math.PI * 2;
        const p1 = [x + Math.cos(a1) * 13, base + 22 + i * 2.2, z + Math.sin(a1) * 13];
        const p2 = [x + Math.cos(a2) * 13, base + 22 + ((i + 2) % 5) * 2.2, z + Math.sin(a2) * 13];
        const ddx = p2[0] - p1[0];
        const ddz = p2[2] - p1[2];
        const comp = Math.hypot(ddx, ddz);
        caixaCentrada(l, biomaId, "medio", (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2, (p1[2] + p2[2]) / 2,
          2.6, 0.5, comp, Math.atan2(ddx, ddz), -Math.atan2(p2[1] - p1[1], comp));
      }
      cilindro(l, biomaId, "brilho", x, base + 34, z, 2.6, 11);
      break;
    }
    case "cristal": {
      // Caatinga: formação cristalina rompendo a pedra rachada.
      cilindro(l, biomaId, "escuro", x, base - 2.4, z, 30, 5);
      for (let i = 0; i < 8; i++) {
        const ang = (i / 8) * Math.PI * 2;
        const r = 5.5 + hash01(`cristal${i}`) * 6;
        cone(l, biomaId, i % 2 ? "claro" : "medio", x + Math.cos(ang) * r, base + 2.6, z + Math.sin(ang) * r,
          3.8 + hash01(`cristald${i}`) * 3, 17 + hash01(`cristalh${i}`) * 22);
      }
      cone(l, biomaId, "brilho", x, base + 2.6, z, 7.5, 44);
      break;
    }
    case "observatorio": {
      // Amazônia: torre de observação rompendo a copa da floresta.
      cilindro(l, biomaId, "escuro", x, base, z, 15, 33);
      for (let i = 0; i < 5; i++) anel(l, biomaId, "medio", x, base + 7 + i * 6.4, z, 17.5);
      cilindro(l, biomaId, "medio", x, base + 33, z, 21, 2.4);
      anel(l, biomaId, "brilho", x, base + 35.8, z, 22.5);
      cilindro(l, biomaId, "claro", x, base + 35.4, z, 12.5, 8);
      cone(l, biomaId, "claro", x, base + 43.4, z, 10, 9.5);
      caixaCentrada(l, biomaId, "brilho", x + 5.6, base + 48, z + 5.6, 1.8, 1.8, 15, Math.PI / 4, -0.6);
      break;
    }
    case "delta": {
      // Pantanal: lâmina d'água com plataformas horizontais conectadas.
      cilindro(l, biomaId, "agua", x, base - 1.6, z, 52, 1.2);
      for (let i = 0; i < 6; i++) {
        const ang = (i / 6) * Math.PI * 2;
        const r = 12 + (i % 2) * 6;
        const px = x + Math.cos(ang) * r;
        const pz = z + Math.sin(ang) * r;
        caixa(l, biomaId, i % 2 ? "claro" : "medio", px, base - 0.7, pz, 12, 1.3, 10, ang);
        caixaCentrada(l, biomaId, "medio", (x + px) / 2, base, (z + pz) / 2, 3.4, 0.7, r, ang);
        cilindro(l, biomaId, "brilhoFraco", px, base + 0.6, pz, 0.7, 6.5);
      }
      cilindro(l, biomaId, "claro", x, base - 0.7, z, 18, 2.8);
      anel(l, biomaId, "brilho", x, base + 3.4, z, 17);
      break;
    }
    default: {
      // Pampas: monumento no planalto vazio — linha arquitetônica pura.
      caixa(l, biomaId, "medio", x, base - 1.8, z, 52, 1.8, 36);
      caixa(l, biomaId, "claro", x, base, z, 45, 1.4, 30);
      for (let i = 0; i < 8; i++) {
        const px = x - 18.2 + i * 5.2;
        cilindro(l, biomaId, "claro", px, base + 1.4, z - 8, 2.6, 18);
        cilindro(l, biomaId, "medio", px, base + 1.4, z + 8, 2.6, 18);
      }
      caixa(l, biomaId, "claro", x, base + 19.4, z, 46, 3, 30.5);
      caixa(l, biomaId, "medio", x, base + 22.4, z, 26, 1.6, 17);
      caixaCentrada(l, biomaId, "brilho", x, base + 34, z, 10.5, 10.5, 10.5, Math.PI / 4, 0.35);
      break;
    }
  }

  ampliar(pecas, l, x, base, z, ESCALA_MARCO);
}


// ------------------------------------------------------- serra gêmea (borda)

/** O marco natural do continente: duas montanhas colossais na borda do
 * mundo, separadas por um vale que desce muito abaixo do nível das ilhas,
 * com um rio correndo no fundo até despencar no abismo.
 *
 * Existe para dar limite e medida ao mundo — é a coisa contra a qual todo o
 * resto parece pequeno, e o que diz "o continente acaba ali". Fica fora de
 * qualquer bioma: não tem missão, não é clicável, é paisagem. */
function gerarSerraGemea(pecas) {
  let minX = Infinity;
  let somaZ = 0;
  for (const id of CENA.BIOMA_IDS) {
    const a = CENA.ANCORA_MUNDO[id];
    minX = Math.min(minX, a.x);
    somaZ += a.z;
  }
  const bioma = "perceber"; // rocha fria da região vizinha, para não destoar
  const cx = minX - 1750;
  const cz = somaZ / CENA.BIOMA_IDS.length;

  const meiaLargura = 720; // metade da distância entre os dois cumes
  const alturaPico = 1750;
  const baseMacico = -420;
  const fundoVale = -980;
  const comprimentoVale = 2300;

  for (const lado of [-1, 1]) {
    const mx = cx + lado * meiaLargura;

    // Maciço em estratos: cada camada recua e sobe, como rocha dobrada.
    const camadas = [
      [1320, 0.34, "escuro"],
      [980, 0.62, "escuro"],
      [700, 0.84, "medio"],
      [450, 1.0, "medio"],
    ];
    for (const [raioCamada, fracao, tom] of camadas) {
      cone(pecas, bioma, tom, mx, baseMacico, cz, raioCamada * 2, alturaPico * fracao);
    }
    // Cume claro: é o que faz o pico ler contra a névoa, de longe.
    cone(pecas, bioma, "claro", mx, baseMacico + alturaPico * 0.78, cz, 450, alturaPico * 0.3);

    // Contrafortes e lascas de rocha no sopé, dando pé ao maciço.
    for (let k = 0; k < 9; k++) {
      const ang = hash01(`serra:${lado}:cf${k}`) * Math.PI * 2;
      const r = 940 + hash01(`serra:${lado}:cr${k}`) * 460;
      pedra(pecas, bioma, k % 2 ? "escuro" : "medio",
        mx + Math.cos(ang) * r, baseMacico + 40 + hash01(`serra:${lado}:ch${k}`) * 120,
        cz + Math.sin(ang) * r * 0.8,
        400, 230, 320, ang, hash01(`serra:${lado}:cp${k}`) * 0.4);
    }

    // Paredão do vale: a face interna, cortada a pique até o fundo.
    for (let t = -6; t <= 6; t++) {
      const pz = cz + t * (comprimentoVale / 13);
      const recuo = Math.abs(t) * 14;
      caixa(pecas, bioma, "escuro",
        mx - lado * (170 - recuo), fundoVale, pz,
        150, Math.abs(fundoVale - baseMacico) + 240, comprimentoVale / 12);
      caixa(pecas, bioma, "medio",
        mx - lado * (250 - recuo), fundoVale, pz,
        110, Math.abs(fundoVale - baseMacico) + 60, comprimentoVale / 12);
    }
  }

  // Fundo do vale e o rio que o percorre.
  for (let t = -7; t <= 7; t++) {
    const pz = cz + t * (comprimentoVale / 15);
    caixa(pecas, bioma, "escuro", cx, fundoVale - 90, pz, 620, 90, comprimentoVale / 14);
    const desvio = Math.sin(t * 0.55) * 70;
    caixa(pecas, bioma, "agua", cx + desvio, fundoVale - 6, pz, 130, 8, comprimentoVale / 14);
    for (const lado of [1, -1]) {
      caixa(pecas, bioma, "escuro", cx + desvio + lado * 95, fundoVale - 22, pz, 62, 26, comprimentoVale / 14);
    }
  }
  // A queda no fim do vale, saindo do mundo.
  caixa(pecas, bioma, "agua", cx + Math.sin(7 * 0.55) * 70, fundoVale - 470, cz + comprimentoVale / 2, 150, 470, 40);

  // Bruma presa entre as paredes — o que dá profundidade ao vale.
  for (let k = 0; k < 10; k++) {
    pedra(pecas, bioma, "nevoa",
      cx + (hash01(`serra:nev${k}`) - 0.5) * 520,
      fundoVale + 60 + hash01(`serra:nevh${k}`) * 420,
      cz + (hash01(`serra:nevz${k}`) - 0.5) * comprimentoVale,
      460, 190, 380);
  }
}


// ----------------------------------------------------------- templo central

/** O santuário no meio do mundo, flutuando sobre o vazio — nunca encostado
 * na terra. Fica SELADO (pedra cinza, sem luz nenhuma) enquanto houver
 * missão por dominar, e acende quando as 56 caem. Não é bioma, não é missão
 * e não é clicável: é o que o mundo inteiro está apontando.
 *
 * Desenhado numa escala de referência e ampliado, como os demais marcos. */
function gerarTemploCentral(pecas, completo) {
  const l = [];
  const b = "templo";
  const y = 0;
  // Selado: tudo vira pedra morta. Aberto: pedra clara com luz violeta.
  const T = completo
    ? { massa: "escuro", corpo: "medio", face: "claro", luz: "brilho", halo: "brilhoFraco" }
    : { massa: "travado", corpo: "travado", face: "travado", luz: "travado", halo: "travado" };

  // Rochedo facetado que sustenta o santuário e termina em ponta no vazio.
  cone(l, b, T.massa, 0, y, 0, 78, 62, Math.PI);
  for (let k = 0; k < 7; k++) {
    const ang = (k / 7) * Math.PI * 2;
    pedra(l, b, T.massa, Math.cos(ang) * 26, y - 10, Math.sin(ang) * 26, 30, 20, 26, ang, 0.3);
  }
  cilindro(l, b, T.corpo, 0, y - 2, 0, 62, 4);

  // Templo: plataforma escalonada, colunata, frontão e o símbolo aceso.
  for (let i = 0; i < 3; i++) cilindro(l, b, T.corpo, 0, y + 2 + i * 2, 0, 34 - i * 5, 2);
  for (let i = 0; i < 6; i++) {
    const px = -10 + i * 4;
    cilindro(l, b, T.face, px, y + 8, -6, 2.2, 14);
    cilindro(l, b, T.face, px, y + 8, 6, 2.2, 14);
  }
  caixa(l, b, T.face, 0, y + 22, 0, 26, 2.4, 18);
  cone(l, b, T.face, 0, y + 24.4, 0, 26, 9, 0);
  caixa(l, b, T.luz, 0, y + 9, 0, 7, 9, 1.2);

  // Coroa de agulhas com esfera acesa no alto — a assinatura da referência.
  for (let k = 0; k < 9; k++) {
    const ang = (k / 9) * Math.PI * 2 + 0.25;
    const r = 24 + (k % 3) * 4;
    const h = 16 + (k % 4) * 7;
    const px = Math.cos(ang) * r;
    const pz = Math.sin(ang) * r;
    cilindro(l, b, T.corpo, px, y + 2, pz, 5.5, h);
    cone(l, b, T.face, px, y + 2 + h, pz, 6.5, 7);
    pedra(l, b, T.luz, px, y + 2 + h + 10, pz, 4.4, 4.4, 4.4);
  }

  // Anéis de luz orbitando o rochedo.
  for (const [raioAnel, inclina] of [[46, 0.16], [54, -0.22], [62, 0.08]]) {
    anel(l, b, T.halo, 0, y - 6, 0, raioAnel * 2, -Math.PI / 2 + inclina);
  }

  // Alto o bastante para pairar sobre tudo, no centro exato do arquipélago.
  let alturaMax = 0;
  for (const id of CENA.BIOMA_IDS) alturaMax = Math.max(alturaMax, CENA.alturaIlha(id));
  ampliar(pecas, l, 0, 0, 0, 6);
  for (const p of pecas.slice(pecas.length - l.length)) p.pos[1] += alturaMax + 620;
}

// ---------------------------------------------------------------------- API

/** Monta o continente inteiro a partir da cena. */
export function construirCidade({ nos, arestas, completo }) {
  const pecas = [];
  const porBioma = {};
  for (const no of nos) (porBioma[no.biomaId] ??= []).push(no);

  for (const id of CENA.BIOMA_IDS) {
    const doBioma = porBioma[id] ?? [];
    const perfil = PERFIL_NATUREZA[BIOMA_ARCHETYPES[id].vegetacao] ?? PERFIL_NATUREZA.cerrado;
    const grade = gerarIlha(id, doBioma, pecas);
    gerarMontanhas(id, grade, doBioma, pecas, perfil.montanhas, perfil.alturaMontanha);
    gerarAgua(id, grade, doBioma, pecas, perfil);
    gerarBosqueERochas(id, grade, doBioma, pecas, perfil);
    gerarIlhotas(id, grade, pecas);
    gerarLandmark(id, pecas);
  }
  gerarSerraGemea(pecas);
  gerarTemploCentral(pecas, Boolean(completo));
  for (const no of nos) gerarQuarteirao(no, pecas);
  for (const a of arestas) gerarRota(a, pecas);

  return pecas;
}
