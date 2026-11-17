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


def valores(coluna: pd.Series) -> list[str]:
    return sorted(valor for valor in coluna.dropna().unique() if valor)


def valores_perfis(coluna: pd.Series) -> list[str]:
    return sorted({perfil for item in coluna.dropna() for perfil in item.split("; ") if perfil})


def texto(valor: str) -> str:
    return valor if valor else "Informação não fornecida no catálogo."


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
    [data-testid="collapsedControl"] {
        background: #173c35 !important;
        border: 1px solid #173c35 !important;
        border-radius: .6rem !important;
        box-shadow: 0 2px 6px rgba(23, 60, 53, .22);
        color: #ffffff !important;
        opacity: 1 !important;
    }
    [data-testid="stSidebarCollapseButton"] *,
    [data-testid="stSidebarCollapsedControl"] *,
    [data-testid="collapsedControl"] * {
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
    button[data-baseweb="tab"] {
        color: #52645d !important;
        opacity: 1 !important;
        font-weight: 600 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] { color: #a84d32 !important; }
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
    st.caption("Catálogo de produtos para vendas")
    st.divider()
    busca = st.text_input("Buscar produto", placeholder="Nome, código ou descrição")
    linhas = st.multiselect("Linha", valores(produtos["linha"]))
    categorias = st.multiselect("Categoria", valores(produtos["categoria"]))
    fragrancias = st.multiselect("Fragrância", valores(produtos["fragrancia"]))
    perfis_olfativos = st.multiselect("Perfil olfativo", valores_perfis(produtos["perfis_olfativos"]))
    somente_disponiveis = st.toggle("Somente disponíveis", value=False)
    limite_preco = float(produtos["preco_atual_reais"].max())
    faixa_preco = st.slider("Faixa de preço", 0.0, limite_preco, (0.0, limite_preco), step=1.0)

filtrados = produtos.copy()
if busca:
    pesquisa = busca.casefold()
    campos_pesquisa = ("nome", "identificador", "descricao_apresentacao", "sobre_o_produto")
    mascara = pd.Series(False, index=filtrados.index)
    for campo in campos_pesquisa:
        mascara |= filtrados[campo].str.casefold().str.contains(pesquisa, regex=False, na=False)
    filtrados = filtrados[mascara]
if linhas:
    filtrados = filtrados[filtrados["linha"].isin(linhas)]
if categorias:
    filtrados = filtrados[filtrados["categoria"].isin(categorias)]
if fragrancias:
    filtrados = filtrados[filtrados["fragrancia"].isin(fragrancias)]
if perfis_olfativos:
    filtrados = filtrados[
        filtrados["perfis_olfativos"].apply(lambda perfis: any(perfil in perfis.split("; ") for perfil in perfis_olfativos))
    ]
if somente_disponiveis:
    filtrados = filtrados[filtrados["disponivel"]]
filtrados = filtrados[filtrados["preco_atual_reais"].between(*faixa_preco, inclusive="both")]
filtrados = filtrados.sort_values(["nome", "identificador"])

pagina_catalogo, pagina_produto = st.tabs(["Catálogo", "Detalhe do produto"])

with pagina_catalogo:
    st.title("Produtos Avatim")
    st.caption("Consulte o catálogo e abra a ficha completa de cada item.")
    a, b, c = st.columns(3)
    a.metric("Produtos encontrados", len(filtrados))
    b.metric("Disponíveis", int(filtrados["disponivel"].sum()))
    c.metric("Preço médio", moeda(filtrados["preco_atual_reais"].mean()))
    st.divider()

    if filtrados.empty:
        st.info("Nenhum produto encontrado com estes filtros.")
    else:
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
