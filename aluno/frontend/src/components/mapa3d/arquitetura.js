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
//               borda e quilha mergulhando no vazio
//   montanha    cume que fecha o horizonte da ilha e abre vale
//   rio         curso d'água que atravessa a ilha e despenca no abismo
//   lago        espelho d'água numa depressão do terreno
//   bosque      árvores em adensamento variável, conforme o bioma
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

const CELULA = 5.2;

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

/** Bloco irregular — a base de toda rocha, moita e copa: um poliedro
 * achatado em proporções diferentes, que nunca lê como caixa. */
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

// --------------------------------------------------------------------- ilha

/** A massa de terra: platôs em degraus largos, penhasco estratificado na
 * borda e quilha mergulhando no vazio. Devolve a grade para que rio, bosque
 * e montanha saibam onde há chão e em que cota. */
function gerarIlha(biomaId, nosDoBioma, pecas) {
  const arq = BIOMA_ARCHETYPES[biomaId];
  const centro = CENA.ANCORA_MUNDO[biomaId];
  const topo = CENA.alturaIlha(biomaId);
  const ruido = seededNoise2D(`ilha:${biomaId}`);

  const alcance = arq.raioIlha + 26;
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
          if (Math.hypot(no.position[0] - cx, no.position[2] - cz) < 13) {
            dentro = true;
            break;
          }
        }
      }
      // Recorte orgânico: sem isto a ilha vira um disco e denuncia o raio.
      if (dentro && ruido(cx * 0.035, cz * 0.035) < -0.34) dentro = false;
      if (!dentro) continue;

      // Vale e platô: poucos degraus, bem marcados.
      const degrau = Math.round(ruido(cx * 0.026, cz * 0.026) * 1.7) * 1.7;
      celulas.set(`${i}:${j}`, { i, j, cx, cz, topo: topo + degrau });
    }
  }

  for (const cel of celulas.values()) {
    caixa(pecas, biomaId, "medio", cel.cx, cel.topo - 1.8, cel.cz, CELULA, 1.8, CELULA);

    let borda = false;
    for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      if (!celulas.has(`${cel.i + di}:${cel.j + dj}`)) {
        borda = true;
        break;
      }
    }

    if (borda) {
      // Penhasco em estratos: três camadas recuando, como rocha cortada.
      const fundura = 16 + hash01(`${biomaId}:${cel.i}:${cel.j}`) * 16;
      caixa(pecas, biomaId, "escuro", cel.cx, cel.topo - 1.8 - fundura * 0.34, cel.cz, CELULA * 0.99, fundura * 0.34, CELULA * 0.99);
      caixa(pecas, biomaId, "escuro", cel.cx, cel.topo - 1.8 - fundura * 0.72, cel.cz, CELULA * 0.86, fundura * 0.38, CELULA * 0.86);
      caixa(pecas, biomaId, "escuro", cel.cx, cel.topo - 1.8 - fundura, cel.cz, CELULA * 0.66, fundura * 0.28, CELULA * 0.66);
    } else {
      caixa(pecas, biomaId, "escuro", cel.cx, cel.topo - 6.8, cel.cz, CELULA * 0.98, 5, CELULA * 0.98);
    }
  }

  // Quilha: a raiz de rocha que segura a ilha sobre o vazio. Em três massas
  // desencontradas, não numa peça só — um cone único vira uma faceta enorme
  // e chapada que engole o penhasco logo acima dela.
  const raioReal = arq.raioIlha + 4;
  const quilhas = [
    [0, 0, 1.05, 1.15],
    [raioReal * 0.42, raioReal * 0.3, 0.62, 0.75],
    [-raioReal * 0.36, -raioReal * 0.4, 0.5, 0.6],
  ];
  for (const [dx, dz, escala, prof] of quilhas) {
    cone(pecas, biomaId, "escuro", centro.x + dx, topo - 9, centro.z + dz,
      raioReal * escala, raioReal * prof, Math.PI);
  }

  return { celulas, origemX, origemZ, cols, topo, centro };
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

/** Cumes que fecham o horizonte da ilha e abrem vale. Sempre na periferia:
 * no meio da ilha esconderiam os quarteirões. */
function gerarMontanhas(biomaId, grade, nos, pecas, quantidade, alturaBase) {
  if (quantidade <= 0) return;
  const arq = BIOMA_ARCHETYPES[biomaId];
  const celulas = [...grade.celulas.values()];
  let postas = 0;

  for (let k = 0; k < 60 && postas < quantidade; k++) {
    const cel = celulas[Math.floor(hash01(`${biomaId}:mont${k}`) * celulas.length)];
    if (!cel) continue;
    if (Math.hypot(cel.cx - grade.centro.x, cel.cz - grade.centro.z) < arq.raioIlha * 0.45) continue;
    if (!longeDosNos(nos, cel.cx, cel.cz, 16)) continue;

    const h = alturaBase * (0.7 + hash01(`${biomaId}:mh${k}`) * 0.9);
    const base = cel.topo - 2;
    // Base larga e perfil baixo: massa de rocha, não cone isolado.
    cone(pecas, biomaId, "escuro", cel.cx, base, cel.cz, h * 2.4, h * 0.8);
    cone(pecas, biomaId, "escuro", cel.cx + h * 0.32, base, cel.cz - h * 0.26, h * 1.5, h * 0.5);
    cone(pecas, biomaId, "medio", cel.cx - h * 0.2, base, cel.cz + h * 0.22, h * 1.2, h * 0.42);
    // Ombro claro só no alto, para a silhueta ler contra a névoa.
    cone(pecas, biomaId, "medio", cel.cx, base + h * 0.55, cel.cz, h * 0.62, h * 0.3);
    postas += 1;
  }
}

// --------------------------------------------------------------------- água

/** Rio que atravessa a ilha e despenca no abismo, mais um lago numa
 * depressão. A água é o que impede a paisagem de virar só pedra e caixa. */
function gerarAgua(biomaId, grade, nos, pecas, perfil) {
  const centro = grade.centro;

  if (perfil.rio) {
    const dir = hash01(`${biomaId}:riodir`) * Math.PI * 2;
    const passo = CELULA * 0.62;
    const perp = dir + Math.PI / 2;
    let ultimo = null;

    for (let s = -18; s < 60; s++) {
      const t = s * passo;
      const desvio = Math.sin(s * 0.22 + hash01(`${biomaId}:riofase`) * 6) * 9;
      const x = centro.x + Math.cos(dir) * t + Math.cos(perp) * desvio;
      const z = centro.z + Math.sin(dir) * t + Math.sin(perp) * desvio;
      const topo = topoEm(grade, x, z);

      if (topo === null) {
        // O rio chegou à borda: vira queda d'água caindo para a névoa.
        if (ultimo) {
          const queda = 30 + hash01(`${biomaId}:queda`) * 22;
          caixa(pecas, biomaId, "agua", ultimo.x, ultimo.topo - 0.4 - queda, ultimo.z, 4.4, queda, 1.8, dir);
          for (let n = 0; n < 4; n++) {
            pedra(pecas, biomaId, "nevoa",
              ultimo.x + (hash01(`${biomaId}:qn${n}`) - 0.5) * 9,
              ultimo.topo - queda - 2 + hash01(`${biomaId}:qh${n}`) * 6,
              ultimo.z + (hash01(`${biomaId}:qz${n}`) - 0.5) * 9,
              13, 7, 13);
          }
        }
        break;
      }

      const largura = 3.6 + Math.sin(s * 0.4) * 1.1;
      caixa(pecas, biomaId, "agua", x, topo - 0.55, z, largura, 0.45, passo * 1.4, dir);
      // Margens: a água precisa de barranco, senão vira fita colada no chão.
      for (const lado of [1, -1]) {
        caixa(pecas, biomaId, "escuro",
          x + Math.cos(perp) * lado * (largura / 2 + 0.8), topo - 1.3,
          z + Math.sin(perp) * lado * (largura / 2 + 0.8),
          1.6, 1.3, passo * 1.4, dir);
      }
      ultimo = { x, z, topo };
    }
  }

  if (perfil.lago) {
    const celulas = [...grade.celulas.values()];
    let alvo = null;
    for (const cel of celulas) {
      if (!longeDosNos(nos, cel.cx, cel.cz, 15)) continue;
      if (!alvo || cel.topo < alvo.topo) alvo = cel;
    }
    if (alvo) {
      const raio = CELULA * (1.6 + hash01(`${biomaId}:lago`) * 1.1);
      cilindro(pecas, biomaId, "agua", alvo.cx, alvo.topo - 0.8, alvo.cz, raio * 2, 0.55);
      for (let k = 0; k < 8; k++) {
        const ang = (k / 8) * Math.PI * 2;
        pedra(pecas, biomaId, "escuro",
          alvo.cx + Math.cos(ang) * raio * 1.05, alvo.topo - 0.6, alvo.cz + Math.sin(ang) * raio * 1.05,
          4.4, 2, 3.6, ang);
      }
    }
  }
}

// ------------------------------------------------------------ bosque e rocha

const PERFIL_NATUREZA = {
  cerrado: { arvores: 0.2, rochas: 0.3, montanhas: 3, alturaMontanha: 24, rio: true, lago: false, arvore: "esparsa" },
  mata: { arvores: 0.6, rochas: 0.08, montanhas: 4, alturaMontanha: 28, rio: true, lago: true, arvore: "densa" },
  caatinga: { arvores: 0.14, rochas: 0.4, montanhas: 6, alturaMontanha: 32, rio: false, lago: false, arvore: "seca" },
  amazonia: { arvores: 0.66, rochas: 0.06, montanhas: 3, alturaMontanha: 26, rio: true, lago: true, arvore: "gigante" },
  pantanal: { arvores: 0.3, rochas: 0.05, montanhas: 0, alturaMontanha: 0, rio: true, lago: true, arvore: "touceira" },
  pampas: { arvores: 0.06, rochas: 0.12, montanhas: 1, alturaMontanha: 18, rio: true, lago: false, arvore: "solitaria" },
};

function gerarArvore(pecas, biomaId, tipo, x, y, z, g) {
  switch (tipo) {
    case "densa": {
      const h = 6 + g("h") * 5;
      cilindro(pecas, biomaId, "escuro", x, y, z, 1.4, h);
      pedra(pecas, biomaId, "medio", x, y + h + 1.4, z, 5.4, 4.8, 5.4, g("r") * 3);
      pedra(pecas, biomaId, "claro", x + 0.9, y + h + 3.2, z - 0.7, 3.2, 2.8, 3.2, g("r2") * 3);
      break;
    }
    case "gigante": {
      const h = 10 + g("h") * 8;
      cilindro(pecas, biomaId, "escuro", x, y, z, 2.2, h);
      pedra(pecas, biomaId, "medio", x, y + h + 2, z, 8, 7, 8, g("r") * 3);
      pedra(pecas, biomaId, "claro", x - 1.3, y + h + 4.4, z + 1, 4.8, 4.2, 4.8, g("r2") * 3);
      break;
    }
    case "seca": {
      // Caatinga: tronco nu e ramos angulares — vegetação sem copa.
      const h = 4.5 + g("h") * 3.5;
      cilindro(pecas, biomaId, "escuro", x, y, z, 0.8, h);
      for (let k = 0; k < 3; k++) {
        const ang = g(`b${k}`) * Math.PI * 2;
        caixaCentrada(pecas, biomaId, "medio",
          x + Math.cos(ang) * 1.6, y + h * (0.6 + k * 0.14), z + Math.sin(ang) * 1.6,
          0.5, 0.5, 3.4, ang, -0.7);
      }
      break;
    }
    case "touceira": {
      // Pantanal: moitas baixas e juncos na beira d'água.
      pedra(pecas, biomaId, "medio", x, y + 1, z, 5.5, 2.4, 5, g("r") * 3);
      for (let k = 0; k < 4; k++) {
        cilindro(pecas, biomaId, "claro", x + (g(`j${k}`) - 0.5) * 4, y, z + (g(`k${k}`) - 0.5) * 4, 0.28, 2.6 + g(`l${k}`) * 2.2);
      }
      break;
    }
    case "solitaria": {
      const h = 7 + g("h") * 4.5;
      cilindro(pecas, biomaId, "escuro", x, y, z, 1.5, h);
      pedra(pecas, biomaId, "medio", x, y + h + 1.2, z, 5, 4.4, 5, g("r") * 3);
      break;
    }
    default: {
      // Cerrado: copa larga e baixa, tronco torto, muito espaço em volta.
      const h = 4.5 + g("h") * 3;
      cilindro(pecas, biomaId, "escuro", x, y, z, 1.2, h);
      pedra(pecas, biomaId, "medio", x, y + h + 1, z, 5.6, 3.4, 5.4, g("r") * 3);
      break;
    }
  }
}

function gerarBosqueERochas(biomaId, grade, nos, pecas, perfil) {
  for (const cel of grade.celulas.values()) {
    const semente = `${biomaId}:${cel.i}:${cel.j}`;
    const g = (k) => hash01(`${semente}:${k}`);
    if (!longeDosNos(nos, cel.cx, cel.cz, 11)) continue;
    if (Math.hypot(cel.cx - grade.centro.x, cel.cz - grade.centro.z) < 15) continue;

    const sorte = hash01(semente);
    const x = cel.cx + (g("jx") - 0.5) * CELULA * 0.8;
    const z = cel.cz + (g("jz") - 0.5) * CELULA * 0.8;

    if (sorte < perfil.arvores) {
      gerarArvore(pecas, biomaId, perfil.arvore, x, cel.topo, z, g);
      // Adensamento: onde tem uma árvore, costuma ter outra ao lado.
      if (perfil.arvores > 0.5 && g("par") > 0.45) {
        gerarArvore(pecas, biomaId, perfil.arvore, x + 4.5, cel.topo, z + 3, (k) => hash01(`${semente}:2${k}`));
      }
    } else if (sorte < perfil.arvores + perfil.rochas) {
      // Afloramento rochoso: blocos irregulares empilhados.
      const n = 2 + Math.floor(g("n") * 3);
      for (let k = 0; k < n; k++) {
        pedra(pecas, biomaId, k === 0 ? "escuro" : "medio",
          x + (g(`rx${k}`) - 0.5) * 5, cel.topo + 0.6 + k * 1.5, z + (g(`rz${k}`) - 0.5) * 5,
          5.5 - k * 1.1, 3.4 - k * 0.5, 4.8 - k * 0.9, g(`rr${k}`) * 3, g(`rp${k}`) * 0.5);
      }
    }
  }
}

/** Ilhotas soltas orbitando a ilha: reforçam a leitura de arquipélago e dão
 * o que olhar no meio do vazio. */
function gerarIlhotas(biomaId, grade, pecas) {
  const arq = BIOMA_ARCHETYPES[biomaId];
  const perfil = PERFIL_NATUREZA[arq.vegetacao] ?? PERFIL_NATUREZA.cerrado;
  for (let k = 0; k < 3; k++) {
    const ang = hash01(`${biomaId}:ilhota${k}`) * Math.PI * 2;
    const dist = arq.raioIlha + 16 + hash01(`${biomaId}:ilhotad${k}`) * 30;
    const x = grade.centro.x + Math.cos(ang) * dist;
    const z = grade.centro.z + Math.sin(ang) * dist;
    const y = grade.topo + (hash01(`${biomaId}:ilhotay${k}`) - 0.35) * 26;
    const r = 3.4 + hash01(`${biomaId}:ilhotar${k}`) * 3.6;

    cilindro(pecas, biomaId, "medio", x, y - 1.6, z, r * 2, 1.6);
    cone(pecas, biomaId, "escuro", x, y - 1.6, z, r * 1.8, r * 2.6, Math.PI);
    if (hash01(`${biomaId}:ilhotav${k}`) > 0.4) {
      gerarArvore(pecas, biomaId, perfil.arvore, x, y, z, (kk) => hash01(`${biomaId}:ilhotaa${k}${kk}`));
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
    for (let k = 0; k < 3; k++) {
      pedra(pecas, no.biomaId, k === 0 ? "escuro" : "medio",
        x + (g(`px${k}`) - 0.5) * 6, solo + 1 + k * 1.8, z + (g(`pz${k}`) - 0.5) * 6,
        8 - k * 1.6, 4.5 - k * 0.8, 7 - k * 1.4, g(`pr${k}`) * 3, g(`pp${k}`) * 0.4);
    }
    return;
  }

  const tier = ESTADO_TIER[no.estado];
  const largura = 5.5 + g("w") * 3;
  const baseLaje = y - CENA.LAJE;
  const alturaTorre = baseLaje - 0.3 - solo;

  if (alturaTorre > 0.25) {
    const lt = largura * 0.7;
    caixa(pecas, no.biomaId, "escuro", x, solo, z, lt, alturaTorre, lt, rot);
    if (alturaTorre > 3.4) {
      for (let f = 0; f < 4; f++) {
        const ang = rot + (f * Math.PI) / 2;
        arco(pecas, no.biomaId, "medio", x + Math.sin(ang) * (lt / 2 + 0.14), solo, z + Math.cos(ang) * (lt / 2 + 0.14),
          lt * 0.6, ang + Math.PI / 2, 0.42, 7);
      }
    }
    const linhas = Math.max(1, Math.floor((alturaTorre - 1.4) / 2.1));
    for (let l = 0; l < linhas; l++) {
      const yj = solo + 1.4 + l * 2.1;
      if (yj > baseLaje - 1) break;
      for (let f = 0; f < 4; f++) {
        const ang = rot + (f * Math.PI) / 2;
        caixa(pecas, no.biomaId, tier.janela, x + Math.sin(ang) * (lt / 2 + 0.05), yj, z + Math.cos(ang) * (lt / 2 + 0.05),
          largura * 0.24, 0.8, 0.14, ang);
      }
    }
  }

  caixa(pecas, no.biomaId, "medio", x, baseLaje - 0.45, z, largura + 1.2, 0.45, largura + 1.2, rot);
  caixa(pecas, no.biomaId, "claro", x, baseLaje, z, largura, CENA.LAJE, largura, rot);
  caixa(pecas, no.biomaId, "medio", x, y, z, 2, 0.5, 2, rot + 0.45);
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

  const apice = Math.min(7 + plano * 0.14, 46);
  const segmentos = Math.max(14, Math.min(34, Math.round(plano / 5)));
  const acesa = a.peso >= 0.75;
  const tom = acesa ? "brilho" : "brilhoFraco";
  const espessura = acesa ? 0.2 : 0.13;
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
 * outro lado do continente e orienta a exploração. */
function gerarLandmark(biomaId, pecas) {
  const centro = CENA.ANCORA_MUNDO[biomaId];
  const base = CENA.alturaIlha(biomaId);
  const x = centro.x;
  const z = centro.z;
  const arq = BIOMA_ARCHETYPES[biomaId];

  switch (arq.landmark) {
    case "mirante": {
      // Cerrado: rocha escalonada com plataforma de horizonte no topo.
      for (let i = 0; i < 5; i++) {
        const r = 20 - i * 3.4;
        cilindro(pecas, biomaId, i % 2 ? "medio" : "escuro", x, base + i * 4.4, z, r * 2, 4.4);
      }
      cilindro(pecas, biomaId, "claro", x, base + 22, z, 17, 1.4);
      for (let i = 0; i < 14; i++) {
        const ang = (i / 14) * Math.PI * 2;
        cilindro(pecas, biomaId, "claro", x + Math.cos(ang) * 7.4, base + 23.4, z + Math.sin(ang) * 7.4, 1.1, 7);
      }
      anel(pecas, biomaId, "brilho", x, base + 31, z, 17);
      cone(pecas, biomaId, "claro", x, base + 23.4, z, 4.4, 8);
      break;
    }
    case "passarelas": {
      // Mata Atlântica: passarelas suspensas cruzando sobre a copa.
      for (let i = 0; i < 5; i++) {
        const ang = (i / 5) * Math.PI * 2;
        const px = x + Math.cos(ang) * 13;
        const pz = z + Math.sin(ang) * 13;
        cilindro(pecas, biomaId, "escuro", px, base, pz, 3.4, 22 + i * 2.2);
        caixa(pecas, biomaId, "claro", px, base + 22 + i * 2.2, pz, 8.5, 1.1, 8.5, ang);
      }
      for (let i = 0; i < 5; i++) {
        const a1 = (i / 5) * Math.PI * 2;
        const a2 = ((i + 2) / 5) * Math.PI * 2;
        const p1 = [x + Math.cos(a1) * 13, base + 22 + i * 2.2, z + Math.sin(a1) * 13];
        const p2 = [x + Math.cos(a2) * 13, base + 22 + ((i + 2) % 5) * 2.2, z + Math.sin(a2) * 13];
        const ddx = p2[0] - p1[0];
        const ddz = p2[2] - p1[2];
        const comp = Math.hypot(ddx, ddz);
        caixaCentrada(pecas, biomaId, "medio", (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2, (p1[2] + p2[2]) / 2,
          2.6, 0.5, comp, Math.atan2(ddx, ddz), -Math.atan2(p2[1] - p1[1], comp));
      }
      cilindro(pecas, biomaId, "brilho", x, base + 34, z, 2.6, 11);
      break;
    }
    case "cristal": {
      // Caatinga: formação cristalina rompendo a pedra rachada.
      cilindro(pecas, biomaId, "escuro", x, base - 2.4, z, 30, 5);
      for (let i = 0; i < 8; i++) {
        const ang = (i / 8) * Math.PI * 2;
        const r = 5.5 + hash01(`cristal${i}`) * 6;
        cone(pecas, biomaId, i % 2 ? "claro" : "medio", x + Math.cos(ang) * r, base + 2.6, z + Math.sin(ang) * r,
          3.8 + hash01(`cristald${i}`) * 3, 17 + hash01(`cristalh${i}`) * 22);
      }
      cone(pecas, biomaId, "brilho", x, base + 2.6, z, 7.5, 44);
      break;
    }
    case "observatorio": {
      // Amazônia: torre de observação rompendo a copa da floresta.
      cilindro(pecas, biomaId, "escuro", x, base, z, 15, 33);
      for (let i = 0; i < 5; i++) anel(pecas, biomaId, "medio", x, base + 7 + i * 6.4, z, 17.5);
      cilindro(pecas, biomaId, "medio", x, base + 33, z, 21, 2.4);
      anel(pecas, biomaId, "brilho", x, base + 35.8, z, 22.5);
      cilindro(pecas, biomaId, "claro", x, base + 35.4, z, 12.5, 8);
      cone(pecas, biomaId, "claro", x, base + 43.4, z, 10, 9.5);
      caixaCentrada(pecas, biomaId, "brilho", x + 5.6, base + 48, z + 5.6, 1.8, 1.8, 15, Math.PI / 4, -0.6);
      break;
    }
    case "delta": {
      // Pantanal: lâmina d'água com plataformas horizontais conectadas.
      cilindro(pecas, biomaId, "agua", x, base - 1.6, z, 52, 1.2);
      for (let i = 0; i < 6; i++) {
        const ang = (i / 6) * Math.PI * 2;
        const r = 12 + (i % 2) * 6;
        const px = x + Math.cos(ang) * r;
        const pz = z + Math.sin(ang) * r;
        caixa(pecas, biomaId, i % 2 ? "claro" : "medio", px, base - 0.7, pz, 12, 1.3, 10, ang);
        caixaCentrada(pecas, biomaId, "medio", (x + px) / 2, base, (z + pz) / 2, 3.4, 0.7, r, ang);
        cilindro(pecas, biomaId, "brilhoFraco", px, base + 0.6, pz, 0.7, 6.5);
      }
      cilindro(pecas, biomaId, "claro", x, base - 0.7, z, 18, 2.8);
      anel(pecas, biomaId, "brilho", x, base + 3.4, z, 17);
      break;
    }
    default: {
      // Pampas: monumento no planalto vazio — linha arquitetônica pura.
      caixa(pecas, biomaId, "medio", x, base - 1.8, z, 52, 1.8, 36);
      caixa(pecas, biomaId, "claro", x, base, z, 45, 1.4, 30);
      for (let i = 0; i < 8; i++) {
        const px = x - 18.2 + i * 5.2;
        cilindro(pecas, biomaId, "claro", px, base + 1.4, z - 8, 2.6, 18);
        cilindro(pecas, biomaId, "medio", px, base + 1.4, z + 8, 2.6, 18);
      }
      caixa(pecas, biomaId, "claro", x, base + 19.4, z, 46, 3, 30.5);
      caixa(pecas, biomaId, "medio", x, base + 22.4, z, 26, 1.6, 17);
      caixaCentrada(pecas, biomaId, "brilho", x, base + 34, z, 10.5, 10.5, 10.5, Math.PI / 4, 0.35);
      break;
    }
  }
}

// ---------------------------------------------------------------------- API

/** Monta o continente inteiro a partir da cena. */
export function construirCidade({ nos, arestas }) {
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
  for (const no of nos) gerarQuarteirao(no, pecas);
  for (const a of arestas) gerarRota(a, pecas);

  return pecas;
}
