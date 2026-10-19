/**
 * O cabeçalho de uma seção do Estudar: um ícone colorido com pé, o título e
 * uma frase. O mesmo desenho do `.cartao-gordo-icone` dos cartões abaixo, para
 * a seção e os itens dela parecerem uma coisa só (ver `index.css`, "O CARTÃO
 * GORDO").
 */
export default function CabecaDeSecao({ icone: Icone, titulo, frase, cor, nivel = 2, testid, children }) {
  const Titulo = nivel === 3 ? "h3" : "h2";
  return (
    <div className="mb-5 flex flex-wrap items-center gap-x-4 gap-y-3" data-testid={testid}>
      <div className="flex min-w-0 flex-1 items-start gap-3.5">
        {Icone && (
          <span
            className="cartao-gordo-icone"
            style={{ "--de": cor?.de, "--para": cor?.para, "--pe": cor?.pe, width: 44, height: 44, borderRadius: 14 }}
            aria-hidden="true"
          >
            <Icone strokeWidth={2.2} style={{ width: 22, height: 22 }} />
          </span>
        )}
        <div className="min-w-0">
          <Titulo
            className={`font-display font-extrabold tracking-tight text-white ${nivel === 3 ? "text-lg" : "text-xl md:text-2xl"}`}
          >
            {titulo}
          </Titulo>
          {frase && <p className="mt-0.5 text-sm leading-snug text-white/65">{frase}</p>}
        </div>
      </div>
      {children}
    </div>
  );
}
