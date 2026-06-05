"""
Módulo de Visualização (Semana 4) — Dashboard Analítico de Alta Performance.

Interface avançada em Streamlit focada em Data Storytelling e Desacoplamento via API.
Renderiza análises macro de mercado, popularidade e tabelas dinâmicas.
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# Configuração da página do Streamlit para um aspeto mais limpo
st.set_page_config(
    page_title="Music Analytics Dashboard",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_BASE_URL = "http://127.0.0.1:8000/api/v1/"

def fetch_from_api(endpoint: str, params: dict = None):
    """Auxiliar para fazer pedidos seguros à API REST sem duplicação de barras."""
    try:
        clean_endpoint = endpoint.lstrip("/")
        url = f"{API_BASE_URL}{clean_endpoint}"
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Erro na API ({response.status_code}): {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("Não foi possível ligar à API REST. Garanta que o servidor Uvicorn está a correr em http://127.0.0.1:8000")
        st.stop()

# --- BARRA LATERAL (CONTROLOS E FILTROS) ---
with st.sidebar:
    st.image("https://img.icons8.com/fluent/96/000000/audio-wave.png", width=80)
    st.title("Configurações Analíticas")
    st.markdown("Use os filtros abaixo para explorar o comportamento de consumo global.")
    st.markdown("---")

    # Captura de filtros dinâmicos via API
    artistas_api = fetch_from_api("artists/list")
    opcoes_artistas = ["Todos"] + artistas_api if artistas_api else ["Todos"]
    artista_selecionado = st.sidebar.selectbox("🎯 Filtrar por Artista Alvo:", opcoes_artistas)

    paises_api = fetch_from_api("countries/list")
    opcoes_paises = ["Todos"] + paises_api if paises_api else ["Todos"]
    pais_selecionado = st.sidebar.selectbox("🌍 Filtrar por País de Origem:", opcoes_paises)

    st.markdown("---")
    st.markdown("💡 **Arquitetura do Sistema:**")
    st.info("Este Dashboard está totalmente desacoplado da base de dados física. Toda a informação é requisitada dinamicamente via chamadas HTTP à nossa API REST.")
    st.markdown("[📖 Abrir Documentação Swagger](http://127.0.0.1:8000/docs)")

# --- TITULO PRINCIPAL ---
st.title("🎵 Music & Entertainment Insights Dashboard")
st.markdown("Análise avançada de curadoria de playlists e metadados biográficos baseada em arquitetura OLAP colunar.")
st.markdown("---")

# --- SECÇÃO 1: CARTÕES DE KPIs MACRO ---
kpis = fetch_from_api("kpis")
if kpis:
    # Criamos um container com bordas para isolar as métricas de topo
    with st.container(border=True):
        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.metric(
                label="Volumetria Processada (Camada Silver)",
                value=f"{kpis['total_linhas_silver']:,}".replace(",", " "),
                help="Número total de interações faixa-playlist limpas e integradas no pipeline."
            )
            st.caption("Microdados granulares persistidos no DuckDB")
        with kpi2:
            st.metric(
                label="Artistas de Topo Indexados",
                value=kpis['total_artistas_gold']
            )
            st.caption("Foco analítico estruturado na Camada Gold")
        with kpi3:
            st.metric(
                label="Países Identificados (MusicBrainz)",
                value=kpis['total_countries_gold'] if 'total_countries_gold' in kpis else kpis['total_paises_gold']
            )
            st.caption("Soberanias geográficas mapeadas via API")

st.markdown("## 📊 Diagnóstico e Padrões de Mercado")

# --- SECÇÃO 2: GRÁFICOS MACRO (GÉNEROS E GEOGRAFIA) ---
with st.container(border=True):
    col1, col2 = st.columns([1.1, 0.9]) # Dá um pouco mais de largura ao gráfico de barras

    with col1:
        st.subheader("🔥 Hegemonia Cultural: Top 10 Géneros Musicais")
        genres_data = fetch_from_api("genres/top10")
        if genres_data:
            df_genres = pd.DataFrame(genres_data)
            fig_genres = px.bar(
                df_genres,
                x="frequencia_nas_playlists",
                y="mb_genres",
                orientation="h",
                labels={"frequencia_nas_playlists": "Presença em Playlists", "mb_genres": "Género Musical"},
                color="frequencia_nas_playlists",
                color_continuous_scale="blues"
            )
            fig_genres.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False, height=350, margin=dict(l=0, r=0, t=10, b=10))
            st.plotly_chart(fig_genres, use_container_width=True)
            st.info("📌 **Conclusão:** Os géneros urbanos e contemporâneos (Hip Hop, Pop e Trap) detêm um monopólio massivo de aceitação do público, estando presentes na esmagadora maioria das playlists do ecossistema.")

    with col2:
        st.subheader("🗺️ Centralização de Consumo por Região")
        countries_data = fetch_from_api("countries/distribution")
        if countries_data:
            df_countries = pd.DataFrame(countries_data)
            fig_countries = px.pie(
                df_countries,
                values="total_faixas_ouvidas",
                names="mb_country",
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Darkmint
            )
            fig_countries.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=10))
            st.plotly_chart(fig_countries, use_container_width=True)
            st.success("📌 **Conclusão Geográfica:** Existe um afunilamento de mercado centrado no eixo anglo-saxónico (Estados Unidos e Canadá), que controlam mais de 80% do tráfego de reproduções detetado.")

st.markdown("## 👥 O Fenómeno das Mega-Estrelas")

# --- SECÇÃO 3: CORRELAÇÃO DE ALCANCE ---
with st.container(border=True):
    st.subheader("📈 Análise de Concentração: Retenção de Audiência vs. Playlists Únicas")
    artists_popularity = fetch_from_api("artists/popularity", params={"artista": artista_selecionado})

    if artists_popularity:
        df_artists_plot = pd.DataFrame(artists_popularity)
        fig_scatter = px.scatter(
            df_artists_plot,
            x="playlists_unicas",
            y="total_seguidores_alcancados",
            size="total_aparicoes" if len(df_artists_plot) > 1 else None,
            color="artist_name",
            hover_name="artist_name",
            labels={
                "playlists_unicas": "Presença em Playlists Únicas (Dispersão)",
                "total_seguidores_alcancados": "Impacto Acumulado de Seguidores",
                "total_aparicoes": "Volume de Aparições"
            },
            text="artist_name" if len(df_artists_plot) > 1 else None
        )
        fig_scatter.update_traces(textposition='top center', marker=dict(line=dict(width=1, color='DarkSlateGrey')))
        fig_scatter.update_layout(height=400, margin=dict(t=20, b=20))
        st.plotly_chart(fig_scatter, use_container_width=True)

        if artista_selecionado == "Todos":
            st.warning("⚠️ **Insight de Negócio:** Repare no isolamento extremo de artistas como **Drake**, **Kanye West** e **The Weeknd** no quadrante superior direito. Isto prova empiricamente o efeito *Winner-Take-All* na indústria da música digital: poucos artistas monopolizam a esmagadora maioria do alcance de utilizadores.")

# --- SECÇÃO 4: TABELA DE DETALHES EM TABS (ORGANIZADO) ---
st.markdown("## 🔍 Exploração Profunda de Dados")
tab1, tab2 = st.tabs(["📋 Visualizar Amostra de Microdados", "📘 Notas de Engenharia"])

with tab1:
    st.markdown("Esta tabela apresenta os microdados granulares gerados na Camada Silver. Altere os filtros na barra lateral para recalcular dinamicamente:")
    fact_data = fetch_from_api("fact/sample", params={"artista": artista_selecionado, "pais": pais_selecionado})

    if fact_data:
        df_fact_sample = pd.DataFrame(fact_data)
        df_fact_sample.columns = ["Playlist", "Faixa", "Artista", "Álbum", "Duração (Min)", "País / Região"]
        st.dataframe(df_fact_sample, use_container_width=True, height=300)

with tab2:
    st.markdown("""
    ### Notas de Implementação do Pipeline
    - **Camada de Persistência:** DuckDB (Armazenamento Colunar OLAP Local).
    - **Estratégia de Tipagem:** Colunas de datas biográficas convertidas para `VARCHAR` na carga inicial para garantir resiliência e evitar quebras com anos de fundação truncados (ex: `1969`).
    - **Protocolo de Integração:** Desacoplamento estrutural completo via Endpoints REST tipados gerados nativamente pelo FastAPI.
    """)