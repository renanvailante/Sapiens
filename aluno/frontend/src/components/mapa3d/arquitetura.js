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
const CELULA = 19;
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

function aro(pecas, bioma, tom, x, y, z, diam, rotX = -Math.PI / 2, rotY = 0) {
  pecas.push({ bioma, tom, forma: "aro", pos: [x, y, z], size: [diam, diam, diam], rotX, rotY });
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

// -------------------------------------------------------------- continente

/** Distância de um ponto ao segmento AB — usada para engrossar corredores de
 * terra entre âncoras vizinhas. */
function distSegmento(px, pz, ax, az, bx, bz) {
  const dx = bx - ax;
  const dz = bz - az;
  const L = dx * dx + dz * dz;
  const t = L ? Math.max(0, Math.min(1, ((px - ax) * dx + (pz - az) * dz) / L)) : 0;
  return Math.hypot(px - (ax + dx * t), pz - (az + dz * t));
}

/** UMA massa de terra, contínua. A pegada é a união de três coisas: um disco
 * em cada âncora de bioma, um corredor entre âncoras vizinhas e um raio de
 * cada âncora até o centro. Por construção não existe buraco no miolo — a
 * única coisa que recorta é o ruído da COSTA, e ele só age onde o campo já
 * está perto de zero.
 *
 * Os seis biomas continuam distintos (cor e cota próprias), mas a cota faz
 * rampa na fronteira em vez de degrau: dentro de um continente, uma parede
 * vertical entre regiões denunciaria que são ilhas coladas. */
function gerarContinente(nos, pecas) {
  const ruido = seededNoise2D("continente");
  const porBiomaNos = {};
  for (const no of nos) (porBiomaNos[no.biomaId] ??= []).push(no);

  const ancoras = CENA.BIOMA_IDS.map((id) => {
    const c = CENA.ANCORA_MUNDO[id];
    let raio = BIOMA_ARCHETYPES[id].raioIlha;
    for (const no of porBiomaNos[id] ?? []) {
      raio = Math.max(raio, Math.hypot(no.position[0] - c.x, no.position[2] - c.z) + 70);
    }
    return { id, x: c.x, z: c.z, topo: CENA.alturaIlha(id), raio };
  });

  // Silhueta de LAJE alongada, não união de discos: a referência é uma massa
  // comprida de contorno limpo, e a união deixava lóbulos denunciando os seis
  // centros. A superelipse (expoente 2.8) dá o retângulo de cantos redondos.
  const centro = {
    x: CENA.CENTRO_X,
    z: ancoras.reduce((acc, a) => acc + a.z, 0) / ancoras.length,
  };
  let meiaX = 0;
  let meiaZ = 0;
  for (const no of nos) {
    meiaX = Math.max(meiaX, Math.abs(no.position[0] - centro.x));
    meiaZ = Math.max(meiaZ, Math.abs(no.position[2] - centro.z));
  }
  meiaX += 300;
  meiaZ += 260;
  const EXPOENTE = 2.8;

  const campo = (x, z) => {
    const u = Math.abs((x - centro.x) / meiaX);
    const v = Math.abs((z - centro.z) / meiaZ);
    return 1 - Math.pow(Math.pow(u, EXPOENTE) + Math.pow(v, EXPOENTE), 1 / EXPOENTE);
  };

  const origemX = centro.x - meiaX - CELULA * 3;
  const origemZ = centro.z - meiaZ - CELULA * 3;
  const cols = Math.ceil((meiaX * 2 + CELULA * 6) / CELULA);
  const linhas = Math.ceil((meiaZ * 2 + CELULA * 6) / CELULA);

  const celulas = new Map();
  for (let i = 0; i < cols; i++) {
    for (let j = 0; j < linhas; j++) {
      const cx = origemX + (i + 0.5) * CELULA;
      const cz = origemZ + (j + 0.5) * CELULA;
      const f = campo(cx, cz);
      if (f <= 0) continue;
      // Recorte só na COSTA: no miolo (f alto) nada é removido, e é isso que
      // garante continente sem buraco.
      if (f < 0.3 && ruido(cx * 0.009, cz * 0.009) < -0.12) continue;

      // Bioma da célula = âncora mais próxima; a cota mistura as duas mais
      // próximas para a fronteira virar rampa.
      let a0 = null, a1 = null, d0 = Infinity, d1 = Infinity;
      for (const a of ancoras) {
        const d = Math.hypot(cx - a.x, cz - a.z);
        if (d < d0) { a1 = a0; d1 = d0; a0 = a; d0 = d; }
        else if (d < d1) { a1 = a; d1 = d; }
      }
      const mistura = a1 ? Math.max(0, Math.min(1, (d1 - d0) / (0.4 * (d0 + d1)))) : 1;
      const base = a1 ? a1.topo + (a0.topo - a1.topo) * (0.5 + mistura * 0.5) : a0.topo;
      // Planície lisa no miolo, rocha quebrada nas pontas: o degrau do relevo
      // cresce com o maciço, senão o meio fica tão acidentado quanto a borda.
      const macico = CENA.fatorMacico(cx);
      // Duas oitavas: a lenta desenha a planície, a rápida só age no maciço.
      // Com uma frequência só, a ponta inteira caía num degrau único e virava
      // um prato liso do tamanho da região.
      const lento = ruido(cx * 0.004, cz * 0.004) * 2.4;
      const rapido = ruido(cx * 0.013, cz * 0.013) * 3.4 * macico;
      // Terceira oitava, curta: sem ela o maciço inteiro caía em dois ou três
      // patamares e virava uma mesa de pedra do tamanho da ponta.
      const miudo = ruido(cx * 0.032, cz * 0.032) * 2.6 * macico;
      const degrau = Math.round(lento + rapido + miudo) * (2.4 + macico * 9);

      celulas.set(`${i}:${j}`, {
        i, j, cx, cz, bioma: a0.id, macico,
        topo: base + CENA.relevoContinental(cx) + degrau,
      });
    }
  }

  for (const cel of celulas.values()) {
    caixa(pecas, cel.bioma, "medio", cel.cx, cel.topo - 3.6, cel.cz, CELULA, 3.6, CELULA);

    let borda = false;
    for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      if (!celulas.has(`${cel.i + di}:${cel.j + dj}`)) { borda = true; break; }
    }

    if (borda) {
      // Penhasco em estratos só na costa REAL do continente.
      const fundura = 60 + hash01(`cont:${cel.i}:${cel.j}`) * 60;
      caixa(pecas, cel.bioma, "escuro", cel.cx, cel.topo - 3.6 - fundura * 0.34, cel.cz, CELULA * 0.99, fundura * 0.34, CELULA * 0.99);
      caixa(pecas, cel.bioma, "escuro", cel.cx, cel.topo - 3.6 - fundura * 0.72, cel.cz, CELULA * 0.84, fundura * 0.38, CELULA * 0.84);
      caixa(pecas, cel.bioma, "escuro", cel.cx, cel.topo - 3.6 - fundura, cel.cz, CELULA * 0.62, fundura * 0.28, CELULA * 0.62);
      if (hash01(`cont:solto${cel.i}:${cel.j}`) > 0.7) {
        pedra(pecas, cel.bioma, "escuro", cel.cx, cel.topo - 11, cel.cz, 15, 9, 13,
          hash01(`cont:sr${cel.i}${cel.j}`) * 3, 0.4);
      }
    } else {
      caixa(pecas, cel.bioma, "escuro", cel.cx, cel.topo - 17, cel.cz, CELULA * 0.98, 14, CELULA * 0.98);
    }
  }

  // Quilha: a raiz de rocha que faz a laje flutuar. Corre ao longo do
  // comprimento e mergulha mais fundo sob os maciços das pontas — é o peso
  // deles que a silhueta de baixo precisa contar.
  for (let k = 0; k <= 8; k++) {
    const t = k / 8;
    const qx = centro.x + (t - 0.5) * 2 * meiaX * 0.86;
    const macico = CENA.fatorMacico(qx);
    const base = CENA.alturaIlha("relacionar") + CENA.relevoContinental(qx) - 30;
    const larg = meiaZ * (0.95 + macico * 0.5);
    const prof = larg * (0.85 + macico * 0.9);
    let bioma = ancoras[0].id;
    for (const a of ancoras) {
      if (Math.abs(qx - a.x) < Math.abs(qx - ancoras.find((b) => b.id === bioma).x)) bioma = a.id;
    }
    cone(pecas, bioma, "escuro", qx, base, centro.z, larg * 1.7, prof, Math.PI);
    cone(pecas, bioma, "escuro", qx + meiaX * 0.06, base - 18, centro.z - meiaZ * 0.22,
      larg * 0.85, prof * 0.7, Math.PI);
  }

  // Cada bioma enxerga a sua fatia do continente, mas `todas` continua
  // disponível: um rio não pode achar que chegou à borda do mundo só porque
  // cruzou a fronteira do bioma vizinho.
  const grades = {};
  for (const a of ancoras) {
    grades[a.id] = {
      celulas: new Map(), todas: celulas, origemX, origemZ, cols,
      topo: a.topo, centro: { x: a.x, z: a.z }, extensao: a.raio,
    };
  }
  for (const cel of celulas.values()) grades[cel.bioma].celulas.set(`${cel.i}:${cel.j}`, cel);

  const extensaoTotal = Math.max(meiaX, meiaZ);
  return { grades, celulas, origemX, origemZ, cols, centro, extensaoTotal, ancoras, meiaX, meiaZ };
}

/** Cota do terreno num ponto qualquer do continente (null fora dele). Olha
 * SEMPRE o mapa completo: a fronteira entre biomas não é borda de mundo. */
function topoEm(grade, x, z) {
  const i = Math.floor((x - grade.origemX) / CELULA);
  const j = Math.floor((z - grade.origemZ) / CELULA);
  return (grade.todas ?? grade.celulas).get(`${i}:${j}`)?.topo ?? null;
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
    if ((cel.macico ?? 0) > 0.45) continue; // o maciço já é o relevo dali
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
    // Mata é coisa de planície; no maciço o chão é rocha. Mas "rocha" não
    // pode virar placa lisa: sem entulho, a ponta inteira lê como uma mesa de
    // pedra. Então lá o sorteio vira só afloramento e lasca solta.
    const planicie = 1 - (cel.macico ?? 0);
    const rochoso = planicie < 0.35;

    const sorte = hash01(semente);
    const x = cel.cx + (g("jx") - 0.5) * CELULA * 0.8;
    const z = cel.cz + (g("jz") - 0.5) * CELULA * 0.8;

    // Piso de vegetação: cerrado é ralo em ÁRVORE, mas planície pelada lê
    // como laje de concreto na vista de mapa. Cada bioma mantém a sua espécie
    // e a sua cor; o que se garante aqui é que exista mata.
    const densidade = Math.max(perfil.arvores, 0.42) * planicie;
    if (!rochoso && sorte < densidade) {
      gerarArvore(pecas, biomaId, perfil.arvore, x, cel.topo, z, g);
      // Adensamento: onde tem uma árvore, costuma ter outras ao lado.
      const vizinhas = densidade > 0.5 ? 3 : 2;
      for (let v = 1; v <= vizinhas; v++) {
        if (g(`par${v}`) < 0.45) continue;
        const ang = g(`pa${v}`) * Math.PI * 2;
        const r = CELULA * (0.28 + g(`pr${v}`) * 0.3);
        gerarArvore(pecas, biomaId, perfil.arvore, x + Math.cos(ang) * r, cel.topo, z + Math.sin(ang) * r,
          (k) => hash01(`${semente}:${v}${k}`), ESCALA_NATUREZA * (0.7 + g(`pe${v}`) * 0.4));
      }
    } else if (rochoso ? sorte < 0.5 : sorte < perfil.arvores + perfil.rochas) {
      // Afloramento rochoso: blocos irregulares empilhados.
      const n = 2 + Math.floor(g("n") * 4);
      for (let k = 0; k < n; k++) {
        pedra(pecas, biomaId, k === 0 ? "escuro" : "medio",
          x + (g(`rx${k}`) - 0.5) * 14, cel.topo + 1.4 + k * 3.6, z + (g(`rz${k}`) - 0.5) * 14,
          14 - k * 2.6, 8 - k * 1.2, 12 - k * 2.2, g(`rr${k}`) * 3, g(`rp${k}`) * 0.5);
      }
    }

    // Sub-bosque: o que enche o chão entre uma coisa e outra. Sem isto o
    // terreno grande fica com cara de tabuleiro vazio. Com ele em TODA célula
    // custava 28 mil peças a mais sem diferença visível na vista de mapa —
    // medido, não estimado.
    if (rochoso || g("sub") > 0.42) {
      const n = rochoso ? 1 + Math.floor(g("subn") * 2) : 1 + Math.floor(g("subn") * 3);
      // No maciço o entulho é MATACÃO, não seixo: a 4 unidades ele some na
      // vista de mapa e a ponta volta a ler como uma laje lisa.
      const E = rochoso ? 4.5 + g("se") * 4 : 1;
      for (let k = 0; k < n; k++) {
        const sx = cel.cx + (g(`sx${k}`) - 0.5) * CELULA;
        const sz = cel.cz + (g(`sz${k}`) - 0.5) * CELULA;
        if (g(`st${k}`) > 0.55) {
          pedra(pecas, biomaId, "escuro", sx, cel.topo + 0.7 * E, sz,
            4.4 * E, 1.8 * E, 3.6 * E, g(`sr${k}`) * 3, rochoso ? (g(`sp${k}`) - 0.5) * 0.5 : 0);
        } else {
          pedra(pecas, biomaId, "medio", sx, cel.topo + 1.1 * E, sz,
            3.2 * E, 2.4 * E, 3 * E, g(`sr${k}`) * 3, rochoso ? (g(`sp${k}`) - 0.5) * 0.5 : 0);
        }
      }
    }
  }
}

/** Os dois conjuntos de rocha gigante, um em cada ponta da planície.
 *
 * Poucas massas GRANDES, não muitas pequenas: a primeira tentativa espalhou
 * noventa cones do mesmo tamanho e o resultado leu como um acampamento de
 * barracas. A referência resolve penhasco com blocos angulares volumosos, e é
 * o poliedro em proporções desiguais — não o cone — que dá essa leitura. */
function gerarMacicos(continente, nos, pecas) {
  const celulas = [...continente.celulas.values()].filter((c) => c.macico > 0.5);
  if (!celulas.length) return;
  let postas = 0;

  for (let k = 0; k < 900 && postas < 48; k++) {
    const cel = celulas[Math.floor(hash01(`macico:${k}`) * celulas.length)];
    if (!cel) continue;
    if (!longeDosNos(nos, cel.cx, cel.cz, 96)) continue;

    const g = (t) => hash01(`macico:${k}:${t}`);
    // Estreito e alto: com largura e altura parecidas o icosaedro vira uma
    // bola facetada, e o conjunto lê como pedregulho em vez de penhasco.
    const largura = (105 + g("w") * 135) * (0.55 + cel.macico * 0.7);
    const altura = largura * (1.35 + g("h") * 1.15);
    const base = cel.topo + altura * 0.32;
    const giro = g("g") * Math.PI * 2;

    // Massa principal: bloco alto e desaprumado.
    pedra(pecas, cel.bioma, "medio", cel.cx, base, cel.cz,
      largura, altura, largura * (0.46 + g("d") * 0.44), giro, (g("t") - 0.5) * 0.22);
    // Face iluminada no alto — é o que separa o volume do fundo.
    pedra(pecas, cel.bioma, "claro", cel.cx, base + altura * 0.4, cel.cz,
      largura * 0.6, altura * 0.5, largura * 0.5, giro + 0.4, (g("t2") - 0.5) * 0.3);

    // Lascas encostadas: um bloco sozinho lê como pedra jogada; o grupo lê
    // como rocha partida, que é o que a referência mostra.
    const lascas = 2 + Math.floor(g("n") * 3);
    for (let n = 0; n < lascas; n++) {
      const ang = giro + n * (Math.PI * 2 / lascas) + g(`la${n}`) * 0.6;
      const esc = 0.4 + g(`le${n}`) * 0.4;
      pedra(pecas, cel.bioma, n % 2 ? "escuro" : "medio",
        cel.cx + Math.cos(ang) * largura * 0.62,
        cel.topo + altura * esc * 0.34,
        cel.cz + Math.sin(ang) * largura * 0.62,
        largura * esc, altura * esc * 1.1, largura * esc * 0.8,
        ang, (g(`lt${n}`) - 0.5) * 0.5);
    }

    // Uma agulha a cada três grupos: dá pico ao conjunto sem virar espinheiro.
    if (g("agulha") > 0.66) {
      cone(pecas, cel.bioma, "claro", cel.cx, base + altura * 0.45, cel.cz,
        largura * 0.55, altura * 1.1, (g("ai") - 0.5) * 0.2);
    }
    postas += 1;
  }
}

/** Ilhotas satélites: pedaços de terra soltos orbitando o continente, em
 * cotas diferentes. São elas que dão profundidade ao vazio em volta e o que
 * a referência usa para o mundo não terminar numa borda seca. */
function gerarIlhotasSatelites(continente, pecas) {
  const { ancoras, centro, extensaoTotal } = continente;
  for (let k = 0; k < 26; k++) {
    const ang = (k / 26) * Math.PI * 2 + hash01(`sat:${k}:a`) * 0.5;
    const dist = extensaoTotal * (1.08 + hash01(`sat:${k}:d`) * 0.55);
    // Segue o alongamento do continente: satélite em círculo perfeito
    // entregaria que a costa foi desenhada por raio.
    const x = centro.x + Math.cos(ang) * dist * 1.35;
    const z = centro.z + Math.sin(ang) * dist * 0.85;

    let perto = ancoras[0];
    for (const a of ancoras) {
      if (Math.hypot(x - a.x, z - a.z) < Math.hypot(x - perto.x, z - perto.z)) perto = a;
    }
    const biomaId = perto.id;
    const perfil = PERFIL_NATUREZA[BIOMA_ARCHETYPES[biomaId].vegetacao] ?? PERFIL_NATUREZA.cerrado;
    const y = perto.topo + (hash01(`sat:${k}:y`) - 0.3) * 260;
    const r = 16 + hash01(`sat:${k}:r`) * 34;

    cilindro(pecas, biomaId, "medio", x, y - 5, z, r * 2, 5);
    cone(pecas, biomaId, "escuro", x, y - 5, z, r * 1.85, r * 2.4, Math.PI);
    for (let b = 0; b < 3; b++) {
      const ab = hash01(`sat:${k}:b${b}`) * Math.PI * 2;
      pedra(pecas, biomaId, "escuro", x + Math.cos(ab) * r * 0.7, y - 12, z + Math.sin(ab) * r * 0.7,
        r * 0.7, r * 0.5, r * 0.6, ab, 0.3);
    }
    const n = 1 + Math.floor(hash01(`sat:${k}:n`) * 4);
    for (let v = 0; v < n; v++) {
      const av = hash01(`sat:${k}:av${v}`) * Math.PI * 2;
      const rv = hash01(`sat:${k}:rv${v}`) * r * 0.6;
      gerarArvore(pecas, biomaId, perfil.arvore, x + Math.cos(av) * rv, y, z + Math.sin(av) * rv,
        (kk) => hash01(`sat:${k}:${v}${kk}`));
    }
  }
}

// --------------------------------------------------------------- quarteirão

function gerarQuarteirao(no, pecas) {
  const [x, y, z] = no.position;
  const solo = CENA.alturaIlha(no.biomaId) + CENA.relevoContinental(x);
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
  const base = CENA.alturaIlha(biomaId) + CENA.relevoContinental(centro.x);
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
function gerarSerraGemea(pecas, continente) {
  const bioma = "perceber"; // rocha fria da região vizinha, para não destoar
  // Dentro do maciço da ESQUERDA, não solta no vazio ao lado dele: na
  // referência as duas montanhas e o vale do rio fazem parte do conjunto de
  // rocha daquela ponta. Recuada em Z para não cair em cima dos nós de lá.
  const cx = continente.centro.x - continente.meiaX * 0.74;
  const cz = continente.centro.z - continente.meiaZ * 0.52;
  const solo = CENA.alturaIlha(bioma) + CENA.relevoContinental(cx);

  const meiaLargura = 300; // metade da distância entre os dois cumes
  const alturaPico = 1080;
  const baseMacico = solo - 150;
  const fundoVale = solo - 430;
  const comprimentoVale = 1000;
  // As medidas abaixo foram desenhadas para uma serra de 720 de meia-largura,
  // quando ela ficava solta no vazio. Agora que ela mora dentro do maciço,
  // tudo escala junto — senão os contrafortes cobrem meia planície.
  const E = meiaLargura / 720;

  for (const lado of [-1, 1]) {
    const mx = cx + lado * meiaLargura;

    // Maciço em estratos: cada camada recua e sobe, como rocha dobrada.
    const camadas = [
      // Raios bem menores que os originais: lá a serra ficava longe e podia
      // ser larga; aqui, sobre o continente, cone de base larga com pouca
      // altura vira platô chapado em vez de pico.
      [600 * E, 0.34, "escuro"],
      [470 * E, 0.64, "escuro"],
      [340 * E, 0.86, "medio"],
      [215 * E, 1.0, "medio"],
    ];
    for (const [raioCamada, fracao, tom] of camadas) {
      cone(pecas, bioma, tom, mx, baseMacico, cz, raioCamada * 2, alturaPico * fracao);
    }
    // Cume claro: é o que faz o pico ler contra a névoa, de longe.
    cone(pecas, bioma, "claro", mx, baseMacico + alturaPico * 0.78, cz, 215 * E, alturaPico * 0.32);

    // Contrafortes e lascas de rocha no sopé, dando pé ao maciço.
    for (let k = 0; k < 9; k++) {
      const ang = hash01(`serra:${lado}:cf${k}`) * Math.PI * 2;
      const r = (520 + hash01(`serra:${lado}:cr${k}`) * 300) * E;
      pedra(pecas, bioma, k % 2 ? "escuro" : "medio",
        mx + Math.cos(ang) * r, baseMacico + 40 + hash01(`serra:${lado}:ch${k}`) * 120,
        cz + Math.sin(ang) * r * 0.8,
        250 * E, 170 * E, 210 * E, ang, hash01(`serra:${lado}:cp${k}`) * 0.4);
    }

    // Paredão do vale: a face interna, cortada a pique até o fundo.
    for (let t = -6; t <= 6; t++) {
      const pz = cz + t * (comprimentoVale / 13);
      const recuo = Math.abs(t) * 14 * E;
      caixa(pecas, bioma, "escuro",
        mx - lado * (170 * E - recuo), fundoVale, pz,
        150 * E, Math.abs(fundoVale - baseMacico) + 240, comprimentoVale / 12);
      caixa(pecas, bioma, "medio",
        mx - lado * (250 * E - recuo), fundoVale, pz,
        110 * E, Math.abs(fundoVale - baseMacico) + 60, comprimentoVale / 12);
    }
  }

  // Fundo do vale e o rio que o percorre.
  for (let t = -7; t <= 7; t++) {
    const pz = cz + t * (comprimentoVale / 15);
    caixa(pecas, bioma, "escuro", cx, fundoVale - 90, pz, 620 * E, 90, comprimentoVale / 14);
    const desvio = Math.sin(t * 0.55) * 70 * E;
    caixa(pecas, bioma, "agua", cx + desvio, fundoVale - 6, pz, 130 * E, 8, comprimentoVale / 14);
    for (const lado of [1, -1]) {
      caixa(pecas, bioma, "escuro", cx + desvio + lado * 95 * E, fundoVale - 22, pz, 62 * E, 26, comprimentoVale / 14);
    }
  }
  // A queda no fim do vale, saindo do mundo.
  caixa(pecas, bioma, "agua", cx + Math.sin(7 * 0.55) * 70 * E, fundoVale - 470, cz + comprimentoVale / 2, 150 * E, 470, 40);

  // Bruma presa entre as paredes — o que dá profundidade ao vale.
  for (let k = 0; k < 10; k++) {
    pedra(pecas, bioma, "nevoa",
      cx + (hash01(`serra:nev${k}`) - 0.5) * 520 * E,
      fundoVale + 60 + hash01(`serra:nevh${k}`) * 420,
      cz + (hash01(`serra:nevz${k}`) - 0.5) * comprimentoVale,
      460 * E, 190, 380 * E);
  }
}


// ----------------------------------------------------------- templo central

/** O santuário no meio do mundo, flutuando sobre o vazio — nunca encostado
 * na terra. Fica SELADO (pedra cinza, sem luz nenhuma) enquanto houver
 * missão por dominar, e acende quando as 56 caem. Não é bioma, não é missão
 * e não é clicável: é o que o mundo inteiro está apontando.
 *
 * Desenhado numa escala de referência e ampliado, como os demais marcos. */
function gerarTemploCentral(pecas, completo, continente) {
  const l = [];
  const b = "templo";
  const y = 0;
  // Selado: pedra morta. A referência é um santuário claro com luz violeta,
  // então travado usa DOIS cinzas escuros — um só valor apagaria as facetas e
  // o santuário viraria um borrão, que foi exatamente o que aconteceu antes.
  const T = completo
    ? { massa: "escuro", corpo: "medio", face: "claro", luz: "brilho", halo: "brilhoFraco" }
    : { massa: "travado", corpo: "travado", face: "travadoClaro", luz: "travadoClaro", halo: "travado" };

  // Rochedo facetado terminando em ponta no vazio.
  cone(l, b, T.massa, 0, y, 0, 82, 68, Math.PI);
  for (let k = 0; k < 9; k++) {
    const ang = (k / 9) * Math.PI * 2;
    const r = 24 + (k % 2) * 7;
    pedra(l, b, T.massa, Math.cos(ang) * r, y - 9 - (k % 3) * 5, Math.sin(ang) * r,
      28, 22, 24, ang, 0.32);
  }
  cilindro(l, b, T.corpo, 0, y - 2, 0, 64, 4);
  for (let i = 0; i < 3; i++) cilindro(l, b, T.corpo, 0, y + 2 + i * 2, 0, 36 - i * 5, 2);

  // Santuário central: colunata, arquitrave, frontão e o símbolo aceso.
  for (let i = 0; i < 6; i++) {
    const px = -10 + i * 4;
    cilindro(l, b, T.face, px, y + 8, -6.5, 2.4, 15);
    cilindro(l, b, T.face, px, y + 8, 6.5, 2.4, 15);
  }
  caixa(l, b, T.face, 0, y + 23, 0, 27, 2.6, 19);
  cone(l, b, T.face, 0, y + 25.6, 0, 27, 10, 0);
  caixa(l, b, T.corpo, 0, y + 8, 0, 15, 15, 9);
  caixa(l, b, T.luz, 0, y + 10, -4.8, 7, 10, 1.4);

  // Coroa de agulhas: o que faz o santuário ser reconhecível de longe. Alturas
  // alternadas, cada uma com lanterna e esfera acesa no topo — a assinatura da
  // referência é o anel de torres, não a torre única.
  for (let k = 0; k < 13; k++) {
    const ang = (k / 13) * Math.PI * 2 + 0.2;
    const r = 25 + (k % 3) * 5;
    const h = 15 + (k % 4) * 9;
    const px = Math.cos(ang) * r;
    const pz = Math.sin(ang) * r;
    cilindro(l, b, T.corpo, px, y + 2, pz, 6.5, h);
    cilindro(l, b, T.face, px, y + 2 + h, pz, 8, 5);
    cone(l, b, T.face, px, y + 7 + h, pz, 8, 9, 0);
    pedra(l, b, T.luz, px, y + 2 + h + 17, pz, 5, 5, 5);
  }

  // Anéis de luz orbitando o rochedo, em planos desencontrados.
  for (const [raioAnel, inclina, giro] of [[50, 0.16, 0], [58, -0.24, 0.7], [66, 0.09, 1.5], [72, -0.13, 2.3]]) {
    aro(l, b, T.halo, 0, y - 8, 0, raioAnel * 2, -Math.PI / 2 + inclina, giro);
  }

  // Paira no centro exato do continente, alto o bastante para a ponta do
  // rochedo nunca encostar no relevo — ele não pode tocar a terra.
  const centro = continente?.centro ?? { x: 0, z: 0 };
  let alturaMax = 0;
  for (const id of CENA.BIOMA_IDS) alturaMax = Math.max(alturaMax, CENA.alturaIlha(id));
  const ESCALA_TEMPLO = 7;
  ampliar(pecas, l, centro.x, 0, centro.z, ESCALA_TEMPLO);
  const subir = alturaMax + 170 + 68 * ESCALA_TEMPLO;
  for (const p of pecas.slice(pecas.length - l.length)) p.pos[1] += subir;
}

/** Monta o continente inteiro a partir da cena. */
export function construirCidade({ nos, arestas, completo }) {
  const pecas = [];
  const porBioma = {};
  for (const no of nos) (porBioma[no.biomaId] ??= []).push(no);

  // O terreno é gerado UMA vez, para o continente inteiro; cada bioma recebe
  // depois a sua fatia para plantar mata, água e relevo próprios.
  const continente = gerarContinente(nos, pecas);
  for (const id of CENA.BIOMA_IDS) {
    const doBioma = porBioma[id] ?? [];
    const perfil = PERFIL_NATUREZA[BIOMA_ARCHETYPES[id].vegetacao] ?? PERFIL_NATUREZA.cerrado;
    const grade = continente.grades[id];
    gerarMontanhas(id, grade, doBioma, pecas, perfil.montanhas, perfil.alturaMontanha);
    gerarAgua(id, grade, doBioma, pecas, perfil);
    gerarBosqueERochas(id, grade, doBioma, pecas, perfil);
    gerarLandmark(id, pecas);
  }
  gerarMacicos(continente, nos, pecas);
  gerarIlhotasSatelites(continente, pecas);
  gerarSerraGemea(pecas, continente);
  gerarTemploCentral(pecas, Boolean(completo), continente);
  for (const no of nos) gerarQuarteirao(no, pecas);
  for (const a of arestas) gerarRota(a, pecas);

  return pecas;
}
