from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


CSV_PATH = Path("data/produtos_avatim.csv")
FRAGRANCES_PATH = Path("data/fragrancias_avatim.csv")

st.set_page_config(page_title="Avatim | Produtos", page_icon="🌿", layout="wide")


@st.cache_data(show_spinner=False)
def carregar_catalogo(path: str, modificado_em: int) -> pd.DataFrame:
    produtos = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
    for coluna in ("preco_atual_reais", "preco_anterior_reais"):
        produtos[coluna] = pd.to_numeric(produtos[coluna], errors="coerce")
    produtos["disponivel"] = produtos["disponibilidade"].str.casefold().isin({"instock", "em_estoque", "disponível"})
    return produtos


@st.cache_data(show_spinner=False)
def carregar_fragrancias(path: str, modificado_em: int) -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame(columns=["identificador", "sobre_a_fragancia", "perfis_olfativos"])
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")[["identificador", "sobre_a_fragancia", "perfis_olfativos"]]


def moeda(valor: float | None) -> str:
    if pd.isna(valor):
        return "Preço não informado"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def valores_perfis(coluna: pd.Series) -> list[str]:
    return sorted({perfil for item in coluna.dropna() for perfil in item.split("; ") if perfil})


def etiquetas(valor: str) -> set[str]:
    return {item.strip() for item in valor.split(";") if item.strip()}


def filtrar_por_etiquetas(dados: pd.DataFrame, coluna: str, selecionados: list[str]) -> pd.DataFrame:
    if not selecionados:
        return dados
    escolhas = set(selecionados)
    return dados[dados[coluna].apply(lambda valor: bool(etiquetas(valor) & escolhas))]


def texto(valor: str) -> str:
    return valor if valor else "Informação não fornecida no catálogo."


ATENDIMENTOS = {
    "Cuidar do corpo": ["Corpo"],
    "Perfumar ambientes": ["Ambiente"],
    "Encontrar um presente": ["Kits"],
    "Conhecer produtos masculinos": ["Homem"],
    "Encontrar acessórios e bem-estar": ["Acessórios"],
}


def filtrar_busca(dados: pd.DataFrame, busca: str) -> pd.DataFrame:
    if not busca:
        return dados
    pesquisa = busca.casefold()
    campos_pesquisa = ("nome", "identificador", "descricao_apresentacao", "sobre_o_produto")
    mascara = pd.Series(False, index=dados.index)
    for campo in campos_pesquisa:
        mascara |= dados[campo].str.casefold().str.contains(pesquisa, regex=False, na=False)
    return dados[mascara]


def perfis_em_comum(produto: pd.Series, perfis: list[str]) -> list[str]:
    return sorted(etiquetas(produto["perfis_olfativos"]) & set(perfis))


def motivos_da_sugestao(produto: pd.Series, atendimento: str, perfis: list[str]) -> str:
    motivos = []
    if atendimento in ATENDIMENTOS:
        motivos.append(f"atende a necessidade de {atendimento.casefold()}")
    perfis_compativeis = perfis_em_comum(produto, perfis)
    if perfis_compativeis:
        motivos.append(f"tem perfil {', '.join(perfis_compativeis).casefold()}")
    if produto["disponivel"]:
        motivos.append("está disponível")
    return " e ".join(motivos).capitalize() + "."


def fala_de_apoio(produto: pd.Series, para_quem: str) -> str:
    apresentacao = produto["descricao_apresentacao"].strip() or produto["sobre_o_produto"].strip()
    if len(apresentacao) > 220:
        apresentacao = f"{apresentacao[:217].rsplit(' ', 1)[0]}..."
    inicio = "Para presentear, " if para_quem == "Para presente" else "Para o dia a dia, "
    return f"{inicio}{apresentacao}" if apresentacao else "Apresente as características e o modo de uso deste produto."


def selecionar_sugestoes(dados: pd.DataFrame, atendimento: str, perfis: list[str]) -> pd.DataFrame:
    if dados.empty or atendimento not in ATENDIMENTOS:
        return dados.head(0)
    sugestoes = dados.copy()
    sugestoes["_pontuacao"] = 0
    sugestoes.loc[sugestoes["disponivel"], "_pontuacao"] += 2
    sugestoes.loc[sugestoes["descricao_apresentacao"].ne(""), "_pontuacao"] += 1
    sugestoes["_pontuacao"] += sugestoes.apply(lambda produto: len(perfis_em_comum(produto, perfis)) * 3, axis=1)
    return sugestoes.sort_values(
        ["_pontuacao", "preco_atual_reais", "nome"], ascending=[False, True, True], na_position="last"
    ).head(3)


def sugestao_complementar(produto: pd.Series, catalogo: pd.DataFrame) -> pd.Series | None:
    candidatos = catalogo[catalogo["identificador"] != produto["identificador"]].copy()
    if candidatos.empty:
        return None
    mesma_fragrancia = candidatos["fragrancia"].eq(produto["fragrancia"]) & produto["fragrancia"].ne("")
    outra_categoria = candidatos["categoria"].ne(produto["categoria"])
    compativeis = candidatos[mesma_fragrancia & outra_categoria]
    if compativeis.empty:
        compativeis = candidatos[candidatos["linha"].eq(produto["linha"]) & candidatos["subcategoria"].ne(produto["subcategoria"])]
    if compativeis.empty:
        return None
    return compativeis.sort_values(["disponivel", "nome"], ascending=[False, True]).iloc[0]


if not CSV_PATH.exists():
    st.error("Não encontrei `data/produtos_avatim.csv`.")
    st.stop()

produtos = carregar_catalogo(str(CSV_PATH), CSV_PATH.stat().st_mtime_ns)
produtos = produtos.merge(
    carregar_fragrancias(
        str(FRAGRANCES_PATH),
        FRAGRANCES_PATH.stat().st_mtime_ns if FRAGRANCES_PATH.exists() else 0,
    ),
    on="identificador",
    how="left",
).fillna({"sobre_a_fragancia": "", "perfis_olfativos": ""})

st.markdown(
    """
    <style>
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] { background: #fbfaf7 !important; }
    [data-testid="stMainBlockContainer"] { background: #fbfaf7; }
    [data-testid="stSidebar"] { background: #173c35; }
    [data-testid="stSidebar"] * { color: #f7f0e3; }
    .produto-titulo { color: #173c35; font-size: 2.15rem; font-weight: 700; margin-bottom: 0; }
    .produto-meta { color: #65736d; font-size: .95rem; }
    .preco { color: #a84d32; font-size: 1.7rem; font-weight: 700; }
    .preco-anterior { color: #7b8580; text-decoration: line-through; }
    .card-nome { color: #173c35; font-size: 1.1rem; font-weight: 700; line-height: 1.3; min-height: 3rem; }
    .card-rotulo { color: #65736d; font-size: .72rem; font-weight: 700; letter-spacing: .04rem; margin-top: .7rem; }
    .card-valor { color: #263f38; font-size: .9rem; margin-bottom: 0; }
    [data-testid="stMetric"] {
        background: #ffffff !important;
        border: 1px solid #e3ddd2;
        border-radius: .8rem;
        box-shadow: 0 2px 8px rgba(23, 60, 53, .08);
        min-height: 7.25rem;
        padding: 1rem;
    }
    [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * { color: #52645d !important; }
    [data-testid="stMetricValue"], [data-testid="stMetricValue"] * { color: #173c35 !important; }
    [data-testid="stMainBlockContainer"] h1,
    [data-testid="stMainBlockContainer"] h2,
    [data-testid="stMainBlockContainer"] h3 {
        color: #173c35 !important;
        opacity: 1 !important;
        text-shadow: none !important;
    }
    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p {
        color: #52645d !important;
        opacity: 1 !important;
    }
    /* Controles do menu lateral no desktop e no mobile (nomes variam por versão do Streamlit). */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"],
    [data-testid="stExpandSidebarButton"] {
        background: #173c35 !important;
        border: 1px solid #173c35 !important;
        border-radius: .6rem !important;
        box-shadow: 0 2px 6px rgba(23, 60, 53, .22);
        color: #ffffff !important;
        opacity: 1 !important;
    }
    [data-testid="stSidebarCollapseButton"] *,
    [data-testid="stSidebarCollapsedControl"] *,
    [data-testid="collapsedControl"] *,
    [data-testid="stExpandSidebarButton"] * {
        color: #ffffff !important;
        fill: #ffffff !important;
        opacity: 1 !important;
    }
    /* Streamlit Cloud usa estes seletores para o controle de menu no cabeçalho. */
    button[kind="header"],
    button[data-testid="baseButton-header"],
    button[data-testid="baseButton-headerNoPadding"] {
        background: #173c35 !important;
        color: #ffffff !important;
        border: 1px solid #173c35 !important;
        border-radius: .55rem !important;
        opacity: 1 !important;
    }
    button[kind="header"] svg,
    button[data-testid="baseButton-header"] svg,
    button[data-testid="baseButton-headerNoPadding"] svg {
        fill: #ffffff !important;
        stroke: #ffffff !important;
        opacity: 1 !important;
    }
    button[data-baseweb="tab"],
    [data-testid="stTab"],
    [data-testid="stTab"] * {
        color: #52645d !important;
        opacity: 1 !important;
        font-weight: 600 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"],
    [data-testid="stTab"][data-selected],
    [data-testid="stTab"][data-selected] * { color: #a84d32 !important; }
    @media (max-width: 640px) {
        [data-testid="stMainBlockContainer"] { padding-left: 1rem; padding-right: 1rem; }
        [data-testid="stMetric"] { min-height: 6.4rem; padding: .8rem; }
        .produto-titulo { font-size: 1.8rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.title("Avatim")
    st.caption("Roteiro rápido para apoiar o atendimento")
    st.divider()
    st.subheader("Entenda a cliente")
    para_quem = st.radio("A compra é para?", ["Para mim", "Para presente"], horizontal=True)
    atendimento = st.selectbox(
        "O que ela procura?",
        ["Escolha uma necessidade", *ATENDIMENTOS],
    )
    opcoes_tipo = produtos.copy()
    if atendimento in ATENDIMENTOS:
        opcoes_tipo = filtrar_por_etiquetas(opcoes_tipo, "categoria", ATENDIMENTOS[atendimento])
    tipos_de_produto = ["Todos", *sorted(tipo for tipo in opcoes_tipo["subcategoria"].unique() if tipo)]
    if st.session_state.get("refino_tipo_produto") not in tipos_de_produto:
        st.session_state["refino_tipo_produto"] = "Todos"
    tipo_produto = st.pills(
        "Tipo de produto (opcional)",
        tipos_de_produto,
        selection_mode="single",
        default="Todos",
        key="refino_tipo_produto",
        help="Use quando a cliente já souber que procura, por exemplo, um sabonete, óleo ou hidratante.",
        width="stretch",
        wrap=True,
    )
    opcoes_perfil = opcoes_tipo
    if tipo_produto != "Todos":
        opcoes_perfil = opcoes_perfil[opcoes_perfil["subcategoria"].eq(tipo_produto)]
    perfis_disponiveis = valores_perfis(opcoes_perfil["perfis_olfativos"])
    perfis_selecionados = st.session_state.get("refino_perfil_olfativo", [])
    if any(perfil not in perfis_disponiveis for perfil in perfis_selecionados):
        st.session_state["refino_perfil_olfativo"] = [
            perfil for perfil in perfis_selecionados if perfil in perfis_disponiveis
        ]
    perfis_olfativos = st.multiselect(
        "Perfil olfativo desejado (opcional)",
        perfis_disponiveis,
        key="refino_perfil_olfativo",
        help="Ao escolher mais de um perfil, serão mostrados produtos com qualquer um deles.",
    )
    somente_disponiveis = st.toggle("Somente disponíveis", value=False)
    limite_preco = float(produtos["preco_atual_reais"].max())
    faixa_preco = st.slider("Quanto pretende investir?", 0.0, limite_preco, (0.0, limite_preco), step=1.0)
    with st.expander("Localizar produto já conhecido"):
        busca = st.text_input("Nome ou código", placeholder="Ex.: difusor, 1071580500")

filtrados = produtos.copy()
filtrados = filtrar_busca(filtrados, busca)
if atendimento in ATENDIMENTOS:
    filtrados = filtrar_por_etiquetas(filtrados, "categoria", ATENDIMENTOS[atendimento])
if tipo_produto != "Todos":
    filtrados = filtrados[filtrados["subcategoria"].eq(tipo_produto)]
if perfis_olfativos:
    filtrados = filtrados[
        filtrados["perfis_olfativos"].apply(lambda perfis: bool(etiquetas(perfis) & set(perfis_olfativos)))
    ]
if somente_disponiveis:
    filtrados = filtrados[filtrados["disponivel"]]
if faixa_preco != (0.0, limite_preco):
    filtrados = filtrados[filtrados["preco_atual_reais"].between(*faixa_preco, inclusive="both")]
filtrados = filtrados.sort_values(["nome", "identificador"])
sugestoes = selecionar_sugestoes(filtrados, atendimento, perfis_olfativos)

pagina_catalogo, pagina_produto = st.tabs(["Catálogo", "Detalhe do produto"])

with pagina_catalogo:
    st.title("Produtos Avatim")
    st.caption("Use o roteiro lateral para encontrar opções alinhadas ao atendimento.")
    a, b = st.columns(2)
    a.metric("Produtos encontrados", len(filtrados))
    b.metric("Disponíveis", int(filtrados["disponivel"].sum()))
    st.divider()

    if filtrados.empty:
        st.info("Nenhum produto encontrado para este atendimento. Ajuste o perfil ou a faixa de valor.")
    else:
        if atendimento not in ATENDIMENTOS:
            st.info("Comece escolhendo o que a cliente procura para receber sugestões guiadas.")
        else:
            st.subheader("Sugestões para este atendimento")
            st.caption("Escolha uma delas para apresentar e use a justificativa como apoio na conversa.")
            colunas_sugestoes = st.columns(len(sugestoes), gap="large")
            for coluna, (_, sugestao) in zip(colunas_sugestoes, sugestoes.iterrows()):
                with coluna:
                    with st.container(border=True):
                        if sugestao["url_imagem_principal"]:
                            st.image(sugestao["url_imagem_principal"], width="stretch")
                        st.markdown(f'<p class="card-nome">{sugestao["nome"]}</p>', unsafe_allow_html=True)
                        st.markdown(f'<p class="preco">{moeda(sugestao["preco_atual_reais"])}</p>', unsafe_allow_html=True)
                        st.badge(
                            "Disponível" if sugestao["disponivel"] else "Indisponível",
                            color="green" if sugestao["disponivel"] else "red",
                        )
                        st.caption(f"POR QUE SUGERIR · {motivos_da_sugestao(sugestao, atendimento, perfis_olfativos)}")
                        st.write(f"**Fala de apoio:** {fala_de_apoio(sugestao, para_quem)}")
            st.divider()
        st.caption("Role a página para explorar os produtos filtrados.")
        colunas = st.columns(3, gap="large")
        for posicao, (_, produto_card) in enumerate(filtrados.iterrows()):
            with colunas[posicao % 3]:
                with st.container(border=True):
                    if produto_card["url_imagem_principal"]:
                        st.image(produto_card["url_imagem_principal"], width="stretch")
                    else:
                        st.info("Imagem não disponível")
                    st.markdown(f'<p class="card-nome">{produto_card["nome"]}</p>', unsafe_allow_html=True)
                    st.markdown(f'<p class="preco">{moeda(produto_card["preco_atual_reais"])}</p>', unsafe_allow_html=True)
                    st.badge(
                        "Disponível" if produto_card["disponivel"] else "Indisponível",
                        color="green" if produto_card["disponivel"] else "red",
                    )
                    for rotulo, valor in (
                        ("CATEGORIA", produto_card["categoria"]),
                        ("LINHA", produto_card["linha"]),
                        ("SUBCATEGORIA", produto_card["subcategoria"]),
                        ("FRAGRÂNCIA", produto_card["fragrancia"]),
                        ("PERFIL OLFATIVO", produto_card["perfis_olfativos"]),
                    ):
                        if valor:
                            st.markdown(f'<p class="card-rotulo">{rotulo}</p><p class="card-valor">{valor}</p>', unsafe_allow_html=True)
                    st.link_button("Ver no site da Avatim", produto_card["url"], width="stretch")

with pagina_produto:
    indice_padrao = st.session_state.get("produto_selecionado", filtrados.index[0] if not filtrados.empty else produtos.index[0])
    opcoes = filtrados.index.tolist() if not filtrados.empty else produtos.index.tolist()
    indice = st.selectbox(
        "Produto",
        opcoes,
        index=opcoes.index(indice_padrao) if indice_padrao in opcoes else 0,
        format_func=lambda item: produtos.at[item, "nome"],
        key="selecao_detalhe",
    )
    produto = produtos.loc[indice]
    coluna_imagem, coluna_dados = st.columns([1, 1.35], gap="large")
    with coluna_imagem:
        if produto["url_imagem_principal"]:
            st.image(produto["url_imagem_principal"], use_container_width=True)
        else:
            st.info("Imagem principal não fornecida no catálogo.")
    with coluna_dados:
        st.markdown(f'<p class="produto-titulo">{produto["nome"]}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="produto-meta">Código: {produto["identificador"]} · {produto["linha"] or "Linha não informada"}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="preco">{moeda(produto["preco_atual_reais"])}</p>', unsafe_allow_html=True)
        if pd.notna(produto["preco_anterior_reais"]):
            st.markdown(f'<span class="preco-anterior">De {moeda(produto["preco_anterior_reais"])}</span>', unsafe_allow_html=True)
        st.badge("Disponível" if produto["disponivel"] else "Indisponível", color="green" if produto["disponivel"] else "red")
        st.write("")
        st.write(texto(produto["descricao_apresentacao"]))
        x, y, z = st.columns(3)
        x.caption("CATEGORIA")
        x.write(texto(produto["categoria"]))
        y.caption("LINHA")
        y.write(texto(produto["linha"]))
        z.caption("FRAGRÂNCIA")
        z.write(texto(produto["fragrancia"]))
        st.caption(f"SUBCATEGORIA · {texto(produto['subcategoria'])}")
        if produto["perfis_olfativos"]:
            st.caption(f"PERFIS OLFATIVOS · {produto['perfis_olfativos']}")
        st.link_button("Ver no site da Avatim", produto["url"], use_container_width=True)

    st.divider()
    sobre, uso = st.columns(2, gap="large")
    with sobre:
        st.subheader("Sobre o produto")
        st.write(texto(produto["sobre_o_produto"]))
    with uso:
        st.subheader("Como usar")
        st.write(texto(produto["como_usar"]))
    if produto["sobre_a_fragancia"]:
        st.subheader("Sobre a fragrância")
        st.write(produto["sobre_a_fragancia"])

    complemento = sugestao_complementar(produto, produtos[produtos["disponivel"]])
    if complemento is not None:
        st.divider()
        st.subheader("Sugestão de complemento")
        st.caption("Uma opção compatível para ampliar a experiência da cliente.")
        coluna_complemento, coluna_acao = st.columns([3, 1])
        with coluna_complemento:
            st.write(f"**{complemento['nome']}** · {moeda(complemento['preco_atual_reais'])}")
            if complemento["fragrancia"] == produto["fragrancia"] and produto["fragrancia"]:
                st.caption("Compatível por compartilhar a mesma fragrância em outra categoria.")
            else:
                st.caption("Compatível por pertencer à mesma linha em outra subcategoria.")
        with coluna_acao:
            st.link_button("Ver no site", complemento["url"], use_container_width=True)
