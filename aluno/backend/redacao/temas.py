"""Coletânea de temas de redação — proposta, textos motivadores e recorte.

**Por que isto existe.** Até 2026-09-17 a tela de redação abria com um campo
de texto vazio chamado "Tema proposto (obrigatório)". O aluno que quer treinar
redação e não tem um tema na mão — que é o caso mais comum — precisava sair do
Sapiens, procurar um tema em algum lugar, copiar a frase de volta e só então
começar. Na prática, era o degrau que fazia a maioria não escrever nada.

**Por que constante de produto, e não banco.** Pelo mesmo motivo de
`cursos.py` e de `cursos_conteudo`: um tema é conteúdo editorial revisado, não
estado do aluno. Em arquivo ele ganha revisão antes de publicar, diff do que
mudou, rollback de uma versão ruim e custo ZERO de leitura em produção — a
coletânea é lida do módulo, não do Firestore (ver o incidente de cota de
2026-09-04, e `project_aluno_disciplina_leitura_firestore`).

**O que um tema NÃO pode ter, e o validador de `cursos_conteudo` documenta a
mesma regra: preço.** Escrever sobre um tema daqui custa exatamente o mesmo
que escrever sobre um tema digitado à mão — quem cobra é `redacao_routes`, e
a coletânea não tem opinião sobre dinheiro.

**Os textos motivadores são resumos autorais**, escritos para o Sapiens a
partir de dados públicos (IBGE, INEP, legislação brasileira), e não recortes
de reportagem ou de prova. É a diferença entre montar uma coletânea e
redistribuir a de outra pessoa.

Os temas entram na correção pelo mesmo caminho que um tema digitado: a
`frase` vira `tema_frase` e a decomposição em elementos obrigatórios continua
saindo de `tema_local.elementos_de`. Nada aqui atalha o corretor.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TextoMotivador:
    rotulo: str   # "Texto I", "Texto II"...
    fonte: str    # de onde vem o dado, por extenso
    texto: str


@dataclass(frozen=True)
class Tema:
    tema_id: str
    titulo: str          # o nome curto do card
    frase: str           # a PROPOSTA, do jeito que o ENEM a escreve
    eixo: str            # o agrupamento do catálogo
    resumo: str          # uma linha: o que o tema cobra de quem escreve
    textos_motivadores: tuple[TextoMotivador, ...]


EIXOS: tuple[tuple[str, str], ...] = (
    ("sociedade", "Sociedade e cidadania"),
    ("tecnologia", "Tecnologia e trabalho"),
    ("saude", "Saúde e ambiente"),
    ("educacao", "Educação e cultura"),
)


TEMAS: tuple[Tema, ...] = (
    Tema(
        tema_id="saude-mental-adolescencia",
        titulo="Saúde mental na adolescência",
        frase=(
            "Desafios para o cuidado da saúde mental de adolescentes no Brasil"
        ),
        eixo="saude",
        resumo="Cobra proposta de intervenção com agente público concreto — escola, SUS ou família.",
        textos_motivadores=(
            TextoMotivador(
                "Texto I",
                "Organização Mundial da Saúde — dados públicos sobre saúde mental juvenil",
                "Estima-se que uma em cada sete pessoas de 10 a 19 anos convive com algum "
                "transtorno mental, e que a maior parte desses quadros começa antes dos 25 "
                "anos. A OMS aponta que a maioria dos casos não recebe diagnóstico nem "
                "acompanhamento, e que o intervalo entre os primeiros sintomas e o primeiro "
                "atendimento costuma ser contado em anos, não em meses.",
            ),
            TextoMotivador(
                "Texto II",
                "Lei nº 13.935/2019 — psicologia e serviço social na educação básica",
                "A legislação brasileira prevê a presença de profissionais de psicologia e de "
                "serviço social nas redes públicas de educação básica, com a finalidade de "
                "atender às necessidades e prioridades definidas pelas políticas de educação. "
                "A implantação, porém, depende de cada rede de ensino, e a cobertura efetiva "
                "varia enormemente entre municípios.",
            ),
            TextoMotivador(
                "Texto III",
                "Síntese de indicadores sociais — uso de telas e sono",
                "Pesquisas sobre hábitos de adolescentes brasileiros associam o uso noturno "
                "prolongado de telas à redução das horas de sono e ao aumento de queixas de "
                "ansiedade. O dado isolado não estabelece causa, mas sustenta a discussão "
                "sobre rotina, descanso e desempenho escolar.",
            ),
        ),
    ),
    Tema(
        tema_id="desinformacao-redes",
        titulo="Desinformação nas redes",
        frase=(
            "Caminhos para conter a circulação de desinformação nas redes sociais no Brasil"
        ),
        eixo="tecnologia",
        resumo="Exige separar liberdade de expressão de responsabilidade de plataforma.",
        textos_motivadores=(
            TextoMotivador(
                "Texto I",
                "Constituição Federal de 1988, art. 5º",
                "A Constituição assegura a livre manifestação do pensamento, vedado o "
                "anonimato, e garante o direito de resposta proporcional ao agravo, além da "
                "indenização por dano material, moral ou à imagem. Liberdade de expressão e "
                "responsabilidade pelo que se publica são, no texto constitucional, as duas "
                "faces da mesma garantia.",
            ),
            TextoMotivador(
                "Texto II",
                "Marco Civil da Internet (Lei nº 12.965/2014)",
                "O Marco Civil estabelece princípios para o uso da internet no Brasil, entre "
                "eles a liberdade de expressão, a proteção da privacidade e a "
                "responsabilização dos agentes de acordo com suas atividades. O debate atual "
                "gira em torno de até onde vai o dever das plataformas sobre o conteúdo que "
                "elas distribuem e impulsionam.",
            ),
            TextoMotivador(
                "Texto III",
                "Síntese sobre circulação de conteúdo em aplicativos de mensagem",
                "Conteúdos falsos circulam com mais velocidade em ambientes fechados, como "
                "grupos de mensagem, onde não há correção pública nem contexto. O reenvio "
                "entre pessoas conhecidas confere ao conteúdo uma credibilidade que a fonte "
                "original não teria sozinha.",
            ),
        ),
    ),
    Tema(
        tema_id="trabalho-por-aplicativo",
        titulo="Trabalho por aplicativo",
        frase=(
            "O desafio da proteção social aos trabalhadores de aplicativos no Brasil"
        ),
        eixo="tecnologia",
        resumo="Pede repertório de direito do trabalho sem cair em texto panfletário.",
        textos_motivadores=(
            TextoMotivador(
                "Texto I",
                "Consolidação das Leis do Trabalho — noção de vínculo",
                "A CLT caracteriza a relação de emprego pela pessoalidade, pela habitualidade, "
                "pela onerosidade e pela subordinação. A discussão sobre motoristas e "
                "entregadores de aplicativo gira em torno de quanto dessas quatro "
                "características está presente quando quem organiza o trabalho é um algoritmo.",
            ),
            TextoMotivador(
                "Texto II",
                "Previdência Social — contribuinte individual",
                "Quem trabalha por conta própria pode contribuir para a Previdência como "
                "contribuinte individual e, com isso, ter direito a auxílio por incapacidade, "
                "aposentadoria e demais benefícios. A contribuição, porém, sai integralmente "
                "do próprio rendimento, sem contrapartida de empregador.",
            ),
            TextoMotivador(
                "Texto III",
                "Síntese sobre jornada e rendimento",
                "Levantamentos sobre entregadores em capitais brasileiras descrevem jornadas "
                "que passam de dez horas diárias para alcançar o rendimento pretendido, com "
                "custos de combustível, manutenção e equipamento arcados pelo próprio "
                "trabalhador.",
            ),
        ),
    ),
    Tema(
        tema_id="acesso-ao-livro",
        titulo="Leitura e acesso ao livro",
        frase=(
            "Obstáculos para a formação de leitores no Brasil contemporâneo"
        ),
        eixo="educacao",
        resumo="Tema de baixa polêmica e alta exigência de repertório cultural.",
        textos_motivadores=(
            TextoMotivador(
                "Texto I",
                "Plano Nacional do Livro e Leitura",
                "A política pública brasileira de leitura organiza-se em torno de quatro "
                "eixos: democratização do acesso, fomento à leitura e formação de mediadores, "
                "valorização institucional da leitura e desenvolvimento da economia do livro. "
                "A existência do plano não garante, por si, biblioteca aberta em cada escola.",
            ),
            TextoMotivador(
                "Texto II",
                "Lei nº 12.244/2010 — bibliotecas escolares",
                "A lei determina que toda instituição de ensino do país conte com uma "
                "biblioteca escolar, com acervo mínimo por aluno matriculado e com "
                "profissional habilitado. O cumprimento integral foi sucessivamente adiado, e "
                "boa parte das escolas públicas ainda opera com salas de leitura improvisadas.",
            ),
            TextoMotivador(
                "Texto III",
                "Síntese sobre hábito de leitura",
                "Pesquisas de comportamento leitor no Brasil apontam que a principal razão "
                "declarada para não ler é a falta de tempo, seguida da falta de interesse. "
                "Entre quem lê, a influência de um professor ou de alguém da família aparece "
                "com frequência como origem do hábito.",
            ),
        ),
    ),
    Tema(
        tema_id="mobilidade-urbana",
        titulo="Mobilidade urbana",
        frase=(
            "Caminhos para garantir o direito à mobilidade urbana nas cidades brasileiras"
        ),
        eixo="sociedade",
        resumo="Bom para treinar proposta de intervenção com detalhamento de meio.",
        textos_motivadores=(
            TextoMotivador(
                "Texto I",
                "Política Nacional de Mobilidade Urbana (Lei nº 12.587/2012)",
                "A lei estabelece como princípios a acessibilidade universal, o "
                "desenvolvimento sustentável das cidades, a equidade no acesso ao transporte "
                "público coletivo e a prioridade dos modos de transporte não motorizados sobre "
                "os motorizados.",
            ),
            TextoMotivador(
                "Texto II",
                "Estatuto da Cidade (Lei nº 10.257/2001)",
                "O Estatuto da Cidade trata do direito a cidades sustentáveis, entendido como "
                "o direito à terra urbana, à moradia, ao saneamento ambiental, à "
                "infraestrutura urbana, ao transporte e aos serviços públicos — para as "
                "gerações presentes e futuras.",
            ),
            TextoMotivador(
                "Texto III",
                "Síntese sobre tempo de deslocamento",
                "Em regiões metropolitanas brasileiras, parte relevante dos trabalhadores "
                "gasta mais de duas horas por dia em deslocamento entre casa e trabalho. O "
                "tempo perdido no trajeto concorre diretamente com estudo, descanso e "
                "convívio familiar.",
            ),
        ),
    ),
    Tema(
        tema_id="descarte-de-eletronicos",
        titulo="Lixo eletrônico",
        frase=(
            "Desafios para o descarte responsável de resíduos eletrônicos no Brasil"
        ),
        eixo="saude",
        resumo="Tema técnico: recompensa quem domina logística reversa e responsabilidade compartilhada.",
        textos_motivadores=(
            TextoMotivador(
                "Texto I",
                "Política Nacional de Resíduos Sólidos (Lei nº 12.305/2010)",
                "A lei institui a responsabilidade compartilhada pelo ciclo de vida dos "
                "produtos, envolvendo fabricantes, importadores, distribuidores, comerciantes, "
                "consumidores e o poder público, e prevê sistemas de logística reversa para "
                "produtos eletroeletrônicos e seus componentes.",
            ),
            TextoMotivador(
                "Texto II",
                "Síntese sobre composição dos aparelhos",
                "Aparelhos eletrônicos reúnem metais de valor — cobre, ouro, prata — e também "
                "substâncias perigosas, como chumbo e mercúrio. Descartados em aterro comum, "
                "os segundos contaminam solo e água; recuperados corretamente, os primeiros "
                "voltam à cadeia produtiva.",
            ),
            TextoMotivador(
                "Texto III",
                "Síntese sobre o ciclo de troca de aparelhos",
                "O intervalo médio de troca de telefones celulares no Brasil é contado em "
                "poucos anos, e uma parcela expressiva dos aparelhos substituídos permanece "
                "guardada em gavetas — fora do lixo comum, mas também fora de qualquer "
                "sistema de reciclagem.",
            ),
        ),
    ),
)

TEMAS_POR_ID: dict[str, Tema] = {t.tema_id: t for t in TEMAS}
EIXOS_POR_ID: dict[str, str] = dict(EIXOS)


def listar() -> list[dict]:
    """A coletânea inteira, na ordem editorial, pronta para a tela."""
    return [_serializar(t) for t in TEMAS]


def listar_eixos() -> list[dict]:
    """Os eixos COM os temas de cada um, montados aqui e não no React.

    Mesma razão de `cursos.listar_areas`: a hierarquia do catálogo é decisão
    de produto, e um `groupBy` na tela seria uma segunda fonte de verdade que
    diverge no dia em que um eixo novo entrar sem tema nenhum.
    """
    return [
        {
            "eixo_id": eixo_id,
            "titulo": titulo,
            "temas": [t.tema_id for t in TEMAS if t.eixo == eixo_id],
        }
        for eixo_id, titulo in EIXOS
        if any(t.eixo == eixo_id for t in TEMAS)
    ]


def get(tema_id: str) -> Tema | None:
    return TEMAS_POR_ID.get(tema_id)


def _serializar(t: Tema) -> dict:
    d = asdict(t)
    d["eixo_titulo"] = EIXOS_POR_ID.get(t.eixo, t.eixo)
    return d
