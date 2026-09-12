import { autorizarGoogleAgenda } from "./firebase";

/**
 * Leitura da agenda do Google direto do navegador do aluno.
 *
 * O backend não participa: ele não tem client secret do Google, não guarda
 * refresh token e não consegue abrir o calendário de ninguém sozinho. O aluno
 * autoriza no popup, esta função lê os eventos da semana com o token dele e o
 * que sobe para o Sapiens são os eventos — nunca a credencial.
 *
 * Isso tem um preço honesto: o token vale uma sessão. Toda importação pede a
 * autorização de novo. É o que se paga por não ficar com a chave da agenda de
 * ninguém guardada, e é a troca certa para um dado desta natureza.
 */

const ENDPOINT = "https://www.googleapis.com/calendar/v3/calendars/primary/events";
const MAX_EVENTOS = 250;

/** Eventos entre `de` e `ate` (Date), já expandidos ocorrência a ocorrência. */
export async function lerEventosDaSemana(de, ate) {
  const token = await autorizarGoogleAgenda();
  const params = new URLSearchParams({
    timeMin: de.toISOString(),
    timeMax: ate.toISOString(),
    // `singleEvents` expande a recorrência em ocorrências datadas: sem isso, a
    // aula semanal chegaria como UMA entrada com regra de repetição, e o
    // backend teria de reimplementar o calendário do Google para saber em que
    // terças ela cai.
    singleEvents: "true",
    orderBy: "startTime",
    maxResults: String(MAX_EVENTOS),
  });

  const resposta = await fetch(`${ENDPOINT}?${params}`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!resposta.ok) {
    // 403 aqui quase sempre é a Google Calendar API desligada no projeto do
    // Firebase, não falta de permissão do aluno — e a mensagem crua do Google
    // ("Request had insufficient authentication scopes") manda a pessoa
    // procurar no lugar errado.
    if (resposta.status === 403) {
      throw new Error(
        "O Google recusou a leitura da agenda. Se você autorizou e mesmo assim deu erro, " +
        "use a opção do endereço iCal abaixo — ela funciona sempre."
      );
    }
    if (resposta.status === 401) {
      throw new Error("A autorização do Google expirou. Tente de novo.");
    }
    throw new Error("Não consegui ler sua agenda do Google agora.");
  }

  const dados = await resposta.json();
  return (dados.items || []).filter((e) => e && e.status !== "cancelled");
}
