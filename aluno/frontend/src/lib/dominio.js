/**
 * Nomes para o domínio estimado por frente.
 *
 * Empréstimo declarado da Khan Academy: lá cada habilidade não mostra só uma
 * porcentagem, mostra um NÍVEL com nome (Attempted / Familiar / Proficient /
 * Mastered). A razão é boa e vale aqui: "41%" não diz ao aluno se ele está
 * bem ou mal — ele precisa inventar a régua sozinho, e normalmente inventa a
 * régua da escola (abaixo de 60 é vermelho), que não é esta.
 *
 * Nada é recalculado: a faixa é lida do MESMO número que a tela já mostrava
 * (`hubs[].mastery`, de `/skills-map`). E como aquele número é uma estimativa
 * cosmética com teto em 92% (ver `cosmetic_skills_map.py`), os nomes são
 * deliberadamente modestos — "Dominado" começa em 80, não em 95, porque 95
 * não existe naquela escala.
 */

const FAIXAS = [
  { min: 80, nome: "Dominado", cor: "#4FD9FF" },
  { min: 55, nome: "Proficiente", cor: "#6FB6F5" },
  { min: 30, nome: "Familiar", cor: "#8B7BFF" },
  { min: 1, nome: "Iniciado", cor: "#6E7FB8" },
  { min: 0, nome: "Não explorado", cor: "#41506F" },
];

export function faixaDeDominio(mastery) {
  const n = Math.max(0, Math.round(mastery || 0));
  return { ...FAIXAS.find((f) => n >= f.min), valor: n };
}

export default FAIXAS;
