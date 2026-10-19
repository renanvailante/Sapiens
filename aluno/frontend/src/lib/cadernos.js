/**
 * CADERNOS — como um bloco de 45 questões vira um cartão que se reconhece.
 *
 * Até 2026-10-10 todo caderno tinha a mesma cara: um ícone de livro igual,
 * e o título "ENEM 2023 · Caderno Azul", cortado em "ENEM 20…" na coluna de
 * meia tela. Seis cartões idênticos e a única coisa que os separava — a área
 * — não estava escrita em lugar nenhum. O aluno escolhe um caderno pela
 * MATÉRIA ("vou fazer Matemática"), não pela cor da capa da prova.
 *
 * Então o título do cartão é a área (`disciplinas[0]`, a moda que o servidor
 * já calcula em `_area_dominante`), e a edição vira o cabeçalho do grupo.
 * Cada área tem identidade fixa — glifo e cor — e a cor segue a MATÉRIA,
 * nunca a posição: Matemática é azul em qualquer edição.
 *
 * Nada aqui é inventado: cor de caderno só aparece se a palavra está no dado
 * (`prova`), e o dia só sai da numeração, que é estrutural no ENEM
 * (1–90 no primeiro dia, 91–180 no segundo).
 */

/** As quatro áreas do ENEM, com o nome CURTO que o aluno fala ("vou fazer
 *  Humanas"). `de`/`para` são o degradê do ícone; `pe` é a
 *  borda sólida de baixo (o "pé" do Duolingo), o mesmo matiz escurecido. As
 *  três primeiras seguem a capa do curso da mesma matéria (`cursos.py`):
 *  Matemática, Compreensão de Texto (Linguagens) e Atualidades (Humanas). */
export const AREAS_DO_ENEM = {
  matematica: { nome: "Matemática", glifo: "matematica", de: "#4FD9FF", para: "#2F6BFF", pe: "#1F4F95", tinta: "#9BE7FF" },
  linguagens: { nome: "Linguagens", glifo: "linguagens", de: "#34D399", para: "#0E7490", pe: "#0B5D52", tinta: "#8FF0CB" },
  humanas: { nome: "Humanas", glifo: "humanas", de: "#FB7185", para: "#9D2C64", pe: "#6E1F45", tinta: "#FFB3C1" },
  natureza: { nome: "Natureza", glifo: "natureza", de: "#FBBF24", para: "#D9661F", pe: "#8A4413", tinta: "#FFD98A" },
};

const AREA_GENERICA = { nome: null, glifo: "generico", de: "#A78BFA", para: "#5B3FD0", pe: "#3B2A8A", tinta: "#D3C6FF" };

const semAcento = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** A chave da área a partir do nome que o servidor manda. Casa por pista e
 *  não por igualdade: "Linguagens e Códigos", "Linguagens, Códigos e suas
 *  Tecnologias" e "Linguagens" são a mesma área. */
export function chaveDaArea(nome) {
  const n = semAcento(nome);
  if (!n) return null;
  if (n.includes("matem")) return "matematica";
  if (n.includes("linguag") || n.includes("codigos")) return "linguagens";
  if (n.includes("human")) return "humanas";
  if (n.includes("natureza")) return "natureza";
  return null;
}

/** Identidade visual (cor, glifo) de uma área; área desconhecida não fica
 *  sem cor — cai num violeta neutro, nunca em cinza. */
export function identidadeDaArea(nome) {
  return AREAS_DO_ENEM[chaveDaArea(nome)] || AREA_GENERICA;
}

const CORES_DE_CADERNO = ["azul", "amarelo", "branco", "rosa", "cinza", "verde", "laranja", "roxo"];

/** "Azul", "Amarelo"… só quando a palavra está no próprio `prova`. */
export function corDoCaderno(prova) {
  const p = semAcento(prova);
  const cor = CORES_DE_CADERNO.find((c) => p.includes(c));
  return cor ? cor[0].toUpperCase() + cor.slice(1) : null;
}

/** Como o caderno se chama, legível: "Caderno Azul", "Caderno 5", ou o
 *  próprio texto do dado com a primeira letra maiúscula. */
export function nomeDoCaderno(prova) {
  const cor = corDoCaderno(prova);
  if (cor) return `Caderno ${cor}`;
  const numero = /(?:cad|cd)[^0-9]*0*(\d+)/i.exec(String(prova || ""));
  if (numero) return `Caderno ${numero[1]}`;
  const s = String(prova || "").trim();
  return s ? `Caderno ${s[0].toUpperCase()}${s.slice(1).toLowerCase()}` : "Caderno";
}

/** 1 ou 2, pela numeração (estrutural no ENEM); `null` fora disso. */
export function diaDoCaderno(p) {
  const n = Number(p?.numero_min);
  if (!Number.isFinite(n) || n < 1) return null;
  if (n <= 90) return 1;
  if (n <= 180) return 2;
  return null;
}

/** O que o cartão escreve. `titulo` é a área (a escolha do aluno); sem área
 *  conhecida, a faixa de questões — nunca um título vazio. */
export function rotuloDoCaderno(p) {
  const area = p?.disciplinas?.[0] || null;
  const faixa = p?.numero_min && p?.numero_max ? `Questões ${p.numero_min}–${p.numero_max}` : null;
  const dia = diaDoCaderno(p);
  return {
    titulo: area ? identidadeDaArea(area).nome || area : faixa || "Caderno",
    faixa,
    // A linha de baixo do cartão: "2º dia · nº 136–180". Curta de propósito —
    // no celular o cartão tem 160px, e "Questões 136–180 · 2º dia" quebrava
    // deixando "dia" sozinho numa linha.
    sub: [dia ? `${dia}º dia` : null, p?.numero_min && p?.numero_max ? `nº ${p.numero_min}–${p.numero_max}` : null]
      .filter(Boolean).join(" · "),
    dia,
    edicao: [p?.banca, p?.ano].filter(Boolean).join(" "),
    caderno: nomeDoCaderno(p?.prova),
  };
}

/** Em que pé o aluno está: nunca abriu, no meio, ou terminou. */
export function estadoDoCaderno(respondidas, total) {
  if (!total || respondidas <= 0) return "novo";
  return respondidas >= total ? "concluido" : "andamento";
}

/**
 * Os cadernos agrupados por EDIÇÃO (banca + ano + caderno), na ordem que o
 * servidor manda (ano mais novo primeiro). Dentro do grupo, pela numeração —
 * a ordem em que a prova é aplicada.
 */
export function agruparPorEdicao(provas = []) {
  const grupos = [];
  const porChave = new Map();
  for (const p of provas) {
    const chave = [p.banca || "", p.ano || "", p.prova || ""].join("|");
    let g = porChave.get(chave);
    if (!g) {
      const r = rotuloDoCaderno(p);
      g = { chave, titulo: r.edicao || "Prova", caderno: r.caderno, itens: [] };
      porChave.set(chave, g);
      grupos.push(g);
    }
    g.itens.push(p);
  }
  for (const g of grupos) g.itens.sort((a, b) => (a.numero_min || 0) - (b.numero_min || 0));
  return grupos;
}
