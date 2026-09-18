"""Transforma os markdowns de autoria em conteúdo publicável de curso.

**O que este script é.** A ponte entre o lugar onde o curso é ESCRITO
(`cursos/<nome>/*.md`, um arquivo por estação, produzido fora do produto) e o
lugar onde o curso é SERVIDO (`aluno/backend/conteudo/cursos/<curso_id>/`, o
contrato validado de `cursos_conteudo.py`). Ele roda na máquina de quem
publica, nunca em produção: o que vai para o servidor é o JSON gerado, que
entra por commit e é validado pela suíte.

**Por que existe em vez de alguém digitar o JSON.** O markdown é a fonte:
foi ele que a equipe (e a IA de conteúdo) escreveu e é nele que a revisão
pedagógica acontece. Copiar 24 estações e 240 exercícios à mão para JSON
introduziria erro em silêncio — e tornaria impossível corrigir o texto na
fonte e republicar.

O que o script NÃO presume
--------------------------
**O nome do arquivo não diz nada.** `mat basica 4.md` é a estação 06 e
`mat basica 6.md` é a 04. Número e título saem do CONTEÚDO (o frontmatter e o
corpo), nunca do caminho. Dois arquivos que declarem a mesma estação são
resolvidos pela regra do §"Duplicatas" — sem adivinhação silenciosa.

As quatro transformações que não são cópia
------------------------------------------
1. **Tabela vira bloco `tabela`.** O subconjunto de markdown dos cursos não
   tem tabela de propósito (ver `conteudo/cursos/README.md`), e o conteúdo
   original tem oito delas. A regra do contrato para isso é explícita: o que
   passa do subconjunto vira um TIPO DE BLOCO, não um markdown mais esperto.

2. **O feedback é repartido por alternativa.** No markdown ele é um parágrafo
   só, que explica a conta certa e depois comenta cada distrator ("B soma
   primeiro. C ignora o 4."). O produto tem um lugar melhor para cada metade:
   a explicação vira `solucao` e cada comentário vira o `feedback` DAQUELA
   alternativa — que é o que o aluno recebe quando erra escolhendo justamente
   ela.

3. **As alternativas são embaralhadas.** No markdown, 231 das 233 respostas
   certas são a alternativa A. Publicado assim, o curso ensina a clicar na
   primeira opção e nenhuma resposta significa nada — nem para o aluno nem
   para a análise. O embaralhamento é determinístico (semeado pelo
   `question_id`): reprocessar o mesmo markdown produz exatamente o mesmo
   JSON, então o diff de uma revisão de texto continua legível.

   É por isso que a repartição do item 2 vem ANTES: uma vez que cada
   comentário está preso à sua alternativa, nenhuma letra sobra solta no
   texto, e embaralhar deixa de poder mentir sobre "a alternativa C".

4. **A conclusão é 70% dos exercícios, não 100%.** Dez exercícios por estação
   com exigência de acertar os dez transformaria cada estação num muro. O
   critério `minimo_de_acertos` deixa os últimos como prática de quem quer.

Uso
---
    python scripts/ingerir_curso_markdown.py --verificar    # nada é escrito
    python scripts/ingerir_curso_markdown.py                # escreve o JSON

Depois de escrever, valide sempre — é a suíte que decide se o conteúdo entra:

    python -m pytest tests/test_cursos_conteudo.py -q
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
REPO = BACKEND.parent.parent
sys.path.insert(0, str(BACKEND))

import cursos_ingestao as ci  # noqa: E402  (precisa do sys.path acima)
from cursos_ingestao import duracao, slug  # noqa: E402

SCHEMA_VERSION = ci.SCHEMA_VERSION
VERSAO_DO_CONTEUDO = "2026-09-16"

# ---------------------------------------------------------------------------
# O que este script sabe sobre ESTE curso
# ---------------------------------------------------------------------------
#
# Tudo o que é específico de Matemática Básica mora aqui, em cima, em tabelas.
# Ingerir um curso novo é acrescentar uma entrada em `CURSOS`, não mexer no
# parser.

# Habilidades observáveis do banco de treino (`HAB-01..HAB-56`) que a estação
# de fato exercita. Só entram casamentos que alguém defenderia numa revisão:
# uma habilidade errada aqui contamina o mapa de habilidades do aluno com
# evidência que ele nunca produziu. Estação sem casamento claro fica sem
# `habilidades` — e continua registrando `conceitos`, que é o vocabulário do
# próprio curso.
HABILIDADES_POR_ESTACAO = {
    4: ["HAB-03", "HAB-04"],
    5: ["HAB-05"],
    6: ["HAB-05", "HAB-42"],
    13: ["HAB-03", "HAB-04"],
    17: ["HAB-08", "HAB-09"],
    18: ["HAB-25", "HAB-26"],
    19: ["HAB-19", "HAB-44", "HAB-46"],
    20: ["HAB-43", "HAB-48"],
    21: ["HAB-42", "HAB-47"],
    22: ["HAB-05"],
    24: ["HAB-42", "HAB-47"],
}

# As trilhas: quais estações, em que ordem. É a única coisa que o markdown não
# diz, porque é decisão de curso e não de estação — e é a ordem que o aluno vai
# encontrar na tela.
TRILHAS_MATEMATICA = [
    {
        "trilha_id": "numeros-e-operacoes",
        "titulo": "Números e operações",
        "resumo": "A conta que o resto do curso vai usar sem avisar.",
        "estacoes": [1, 2, 7, 8, 9],
    },
    {
        "trilha_id": "proporcao-e-porcentagem",
        "titulo": "Proporção e porcentagem",
        "resumo": "O assunto que mais cai no ENEM, do conceito ao contexto.",
        "estacoes": [3, 4, 5, 6, 13],
    },
    {
        "trilha_id": "algebra",
        "titulo": "Álgebra",
        "resumo": "Da letra solta à equação que resolve o problema.",
        "estacoes": [10, 11, 12, 14, 15, 16],
    },
    {
        "trilha_id": "medidas-dados-e-graficos",
        "titulo": "Medidas, dados e gráficos",
        "resumo": "Ler o que a prova mostra antes de calcular qualquer coisa.",
        "estacoes": [17, 18, 19, 20],
    },
    {
        "trilha_id": "matematica-do-enem",
        "titulo": "A matemática do ENEM",
        "resumo": "Tudo junto, no formato em que a prova cobra.",
        "estacoes": [21, 22, 23, 24],
    },
]

CURSOS = {
    "matematica-basica": {
        "origem": "cursos/matemática básica",
        "trilhas": TRILHAS_MATEMATICA,
        "habilidades": HABILIDADES_POR_ESTACAO,
    },
}


# ---------------------------------------------------------------------------
# O parser não mora mais aqui
# ---------------------------------------------------------------------------
#
# Ele virou `cursos_ingestao`, no backend, e é o MESMO código que o painel do
# admin usa para publicar uma estação a partir de texto colado. Duas cópias do
# mesmo formato divergiriam em um mês — e a divergência apareceria como "a
# estação que eu publiquei pelo site ficou diferente da que o script gerou".
#
# O que continua aqui é o que é deste curso e desta forma de publicar: a
# origem dos arquivos, as trilhas, as habilidades por estação, os desafios em
# prosa, a escolha entre duas fontes do mesmo número e a escrita em disco.

# Desafio cuja resposta escrita é uma frase, não um valor. Um humano leu as
# três e encodou o número que a frase afirma — o script NÃO adivinha "o
# primeiro número do parágrafo", que é como se publica um gabarito errado sem
# ninguém perceber. Qualquer desafio novo com resposta em prosa PARA a carga
# até alguém decidir o que ele pede.
DESAFIOS_EM_PROSA = {
    # "99% do original, ou seja, 1% menor."
    5: {"valor": 99, "tolerancia": 0.5, "unidade": "%"},
    # "135% da população inicial, ou seja, crescimento total de 35%."
    6: {"valor": 135, "tolerancia": 0.5, "unidade": "%"},
    # "aproximadamente 27,5% ao ano"
    19: {"valor": 27.5, "tolerancia": 0.6, "unidade": "% ao ano"},
}


RESUMO_DO_VIDEO = "Aula conduzida pelo 1º colocado de Medicina da USP."


@dataclass
class EstacaoLida:
    """O que o compilador leu, mais o arquivo de onde veio.

    O arquivo não interessa ao compilador (que lê texto, não caminho) e
    interessa muito aqui: é ele que aparece em "duas fontes para a estação 12,
    usando esta".
    """
    numero: int
    titulo: str
    objetivo: str
    conceitos: list[str]
    pre_requisitos_numeros: list[int]
    blocos: list[dict]
    arquivo: str
    exercicios: int


def ler_estacao(caminho: Path) -> EstacaoLida:
    """Um arquivo de autoria vira uma estação lida. A leitura é do compilador.

    **O nome do arquivo não diz nada**: `mat basica 4.md` é a estação 06. O
    número sai do frontmatter (ou do título), nunca do caminho.
    """
    bruto = caminho.read_text(encoding="utf-8")
    numero = ci.numero_declarado(bruto)
    if not numero:
        raise ValueError(f"{caminho.name}: frontmatter sem `station_id`")
    lida = ci.ler_estacao_de_texto(
        bruto,
        prefixo=f"mb-{numero:02d}",
        encodados=DESAFIOS_EM_PROSA,
        # Marca de versão final nestes arquivos: quando a revisão encontrou um
        # gabarito impossível, a questão foi reescrita logo abaixo e só a
        # última levou os metadados. Sem isto, o rascunho seria publicado junto.
        exigir_id=True,
        resumo_do_video=RESUMO_DO_VIDEO,
    )
    return EstacaoLida(
        numero=numero,
        titulo=lida.titulo,
        objetivo=lida.objetivo,
        conceitos=lida.conceitos,
        pre_requisitos_numeros=lida.pre_requisitos_numeros,
        blocos=lida.blocos,
        arquivo=caminho.name,
        exercicios=lida.exercicios,
    )


def escolher(candidatas: list[EstacaoLida]) -> EstacaoLida:
    """Duas fontes para a mesma estação: vence a mais completa.

    Acontece quando um arquivo veio truncado e a versão inteira foi escrita ao
    lado, sem apagar o original. O critério é o número de exercícios (e, no
    empate, o nome do arquivo), e a escolha é SEMPRE registrada na saída — uma
    versão vencendo em silêncio é como se publica a metade errada de um curso.
    """
    return sorted(candidatas, key=lambda e: (-e.exercicios, -len(e.blocos), e.arquivo))[0]


def montar(curso_id: str, config: dict, avisos: list[str]) -> tuple[dict, dict[str, dict]]:
    origem = REPO / config["origem"]
    if not origem.is_dir():
        raise SystemExit(f"Pasta de origem não encontrada: {origem}")

    por_numero: dict[int, list[EstacaoLida]] = {}
    for arquivo in sorted(origem.glob("*.md")):
        try:
            lida = ler_estacao(arquivo)
        except ValueError as exc:
            avisos.append(f"IGNORADO {arquivo.name}: {exc}")
            continue
        por_numero.setdefault(lida.numero, []).append(lida)

    escolhidas: dict[int, EstacaoLida] = {}
    for numero, candidatas in sorted(por_numero.items()):
        vencedora = escolher(candidatas)
        escolhidas[numero] = vencedora
        if len(candidatas) > 1:
            perdedoras = ", ".join(c.arquivo for c in candidatas if c is not vencedora)
            avisos.append(
                f"estação {numero:02d}: duas fontes — usando `{vencedora.arquivo}` "
                f"({vencedora.exercicios} exercícios), descartando {perdedoras}"
            )

    ids: dict[int, str] = {
        n: f"mb-{n:02d}-{slug(e.titulo)}" for n, e in escolhidas.items()
    }

    esperadas = {n for t in config["trilhas"] for n in t["estacoes"]}
    faltando = sorted(esperadas - set(escolhidas))
    if faltando:
        raise SystemExit(
            "Estações declaradas nas trilhas e ausentes na origem: "
            + ", ".join(f"{n:02d}" for n in faltando)
        )
    sobrando = sorted(set(escolhidas) - esperadas)
    if sobrando:
        avisos.append(
            "estações lidas e não citadas em trilha nenhuma (não serão publicadas): "
            + ", ".join(f"{n:02d}" for n in sobrando)
        )

    manifesto = {
        "schema_version": SCHEMA_VERSION,
        "curso_id": curso_id,
        "versao": VERSAO_DO_CONTEUDO,
        "trilhas": [
            {
                "trilha_id": t["trilha_id"],
                "titulo": t["titulo"],
                **({"resumo": t["resumo"]} if t.get("resumo") else {}),
                "estacoes": [ids[n] for n in t["estacoes"]],
            }
            for t in config["trilhas"]
        ],
    }

    arquivos: dict[str, dict] = {}
    for numero in sorted(esperadas):
        lida = escolhidas[numero]
        contam = [b for b in lida.blocos if b["tipo"] == "exercicio"]
        # 70% e não 100%: dez exercícios obrigatórios por estação fariam de
        # cada uma um muro, e o que sobra não some — vira prática de quem quer
        # (ver o topo do arquivo).
        minimo = max(1, round(len(contam) * 0.7))
        dados = {
            "schema_version": SCHEMA_VERSION,
            "estacao_id": ids[numero],
            "titulo": lida.titulo,
            "objetivo": lida.objetivo,
            "versao": VERSAO_DO_CONTEUDO,
            "duracao_minutos": duracao(lida.blocos, len(contam)),
            "numero": numero,
            "conceitos": lida.conceitos,
            "conclusao": {"tipo": "minimo_de_acertos", "minimo": minimo},
            "fonte": {"arquivo": lida.arquivo, "pasta": config["origem"]},
            "blocos": lida.blocos,
        }
        habilidades = config["habilidades"].get(numero)
        if habilidades:
            dados["habilidades"] = habilidades
        pre = [ids[n] for n in lida.pre_requisitos_numeros if n in ids and n != numero]
        if pre:
            dados["pre_requisitos"] = pre
        arquivos[ids[numero]] = dados

    return manifesto, arquivos


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--curso", default="matematica-basica", choices=sorted(CURSOS))
    parser.add_argument("--verificar", action="store_true", help="não escreve nada")
    parser.add_argument("--destino", default=str(BACKEND / "conteudo" / "cursos"))
    args = parser.parse_args()

    avisos: list[str] = []
    manifesto, arquivos = montar(args.curso, CURSOS[args.curso], avisos)

    for aviso in avisos:
        print(f"  ! {aviso}")

    total_ex = sum(
        1 for d in arquivos.values() for b in d["blocos"] if b["tipo"] == "exercicio"
    )
    total_desafios = sum(
        1 for d in arquivos.values() for b in d["blocos"] if b["tipo"] == "desafio"
    )
    gabaritos: dict[str, int] = {}
    for d in arquivos.values():
        for b in d["blocos"]:
            if b["tipo"] == "exercicio":
                pos = [a["id"] for a in b["alternativas"]].index(b["gabarito"])
                gabaritos["ABCDEFGH"[pos]] = gabaritos.get("ABCDEFGH"[pos], 0) + 1

    print(f"\n{args.curso}: {len(arquivos)} estações, {total_ex} exercícios, {total_desafios} desafios")
    print("  posição do gabarito: " + ", ".join(f"{k}={v}" for k, v in sorted(gabaritos.items())))

    if args.verificar:
        print("\n(--verificar: nada foi escrito)")
        return 0

    raiz = Path(args.destino) / args.curso
    (raiz / "estacoes").mkdir(parents=True, exist_ok=True)
    for antigo in (raiz / "estacoes").glob("*.json"):
        antigo.unlink()

    def escrever(caminho: Path, dados: dict):
        caminho.write_text(
            json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )

    escrever(raiz / "curso.json", manifesto)
    for estacao_id, dados in arquivos.items():
        escrever(raiz / "estacoes" / f"{estacao_id}.json", dados)

    print(f"\nEscrito em {raiz}")
    print("Valide antes de publicar: python -m pytest tests/test_cursos_conteudo.py -q")
    return 0


if __name__ == "__main__":
    sys.exit(main())
