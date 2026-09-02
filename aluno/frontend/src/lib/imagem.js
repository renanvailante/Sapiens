/**
 * Redimensiona a foto do cartão-resposta antes de enviar ao OCR.
 *
 * A foto original de um celular moderno (12 MP) vira cerca de 11 MB de base64
 * dentro de um JSON, indo para a memória de uma VM de 512 MB que aceita 80
 * requisições simultâneas — alguns envios juntos derrubavam a instância. E
 * consome os dados móveis do aluno à toa: o OCR reconhece bolhas preenchidas,
 * não precisa de resolução de impressão.
 *
 * 1600 px no lado maior mantém as marcações perfeitamente legíveis e derruba o
 * payload para algumas centenas de KB.
 */
const LADO_MAXIMO = 1600;
const QUALIDADE_JPEG = 0.82;

function carregarImagem(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => { URL.revokeObjectURL(url); resolve(img); };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("Arquivo de imagem inválido.")); };
    img.src = url;
  });
}

function lerComoBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Não foi possível ler o arquivo."));
    reader.readAsDataURL(file);
  });
}

export async function reduzirImagemParaEnvio(file) {
  try {
    const img = await carregarImagem(file);
    const maior = Math.max(img.width, img.height);
    // Já é pequena: reenviar pelo canvas só perderia qualidade sem ganho.
    if (maior <= LADO_MAXIMO) return await lerComoBase64(file);

    const escala = LADO_MAXIMO / maior;
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(img.width * escala);
    canvas.height = Math.round(img.height * escala);
    const ctx = canvas.getContext("2d");
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", QUALIDADE_JPEG);
  } catch {
    // Navegador sem canvas utilizável, HEIC que o `<img>` não decodifica: o
    // envio original ainda pode funcionar (e o servidor tem seu próprio
    // limite), então tentar é melhor que falhar aqui.
    return await lerComoBase64(file);
  }
}
