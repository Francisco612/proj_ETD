"""
Módulo de Visualização (Semana 4) — Dashboard Analítico Desacoplado.

Consome os dados analíticos exclusivamente através de chamadas HTTP à API REST,
removendo qualquer acoplamento com a base de dados física local.
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# Configuração da página do Streamlit
st.set_page_config(
    page_title="Music Analytics Dashboard",
    page_icon="🎵",
    layout="wide"
)

API_BASE_URL = "http://127.0.0.1:8000/api/v1"

def fetch_from_api(endpoint: str, params: dict = None):
    """Auxiliar para fazer pedidos seguros à API REST."""
    try:
        url = f"{API_BASE_URL}/{endpoint}"
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Erro na API ({response.status_code}): {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("Não foi possível ligar à API REST. Garanta que o servidor Uvicorn está a correr em http://127.0.0.1:8000")
        st.stop()

# --- CABEÇALHO DA APLICAÇÃO ---
st.title("🎵 Music & Entertainment Analytics Dashboard")
st.markdown("### Arquitetura de Microsserviços — Dashboard acoplado via API REST & Swagger")
st.markdown("---")

# --- CAPTURA DE FILTROS VIA API ---
st.sidebar.header("🔍 Filtros Dinâmicos (API)")

artistas_api = fetch_from_api("artists/list")
opcoes_artistas = ["Todos"] + artistas_api if artistas_api else ["Todos"]
artista_selecionado = st.sidebar.selectbox("Escolha um Artista Alvo:", opcoes_artistas)

paises_api = fetch_from_api("countries/list")
opcoes_paises = ["Todos"] + paises_api if paises_api else ["Todos"]
pais_selecionado = st.sidebar.selectbox("Filtrar por País de Origem:", opcoes_paises)

st.sidebar.markdown("---")
st.sidebar.markdown("**Modo de Conexão:** `HTTP / REST API`")
st.sidebar.markdown("**Documentação:** [Aceder ao Swagger](http://127.0.0.1:8000/docs)")

# --- CAPTURA E EXIBIÇÃO DE KPIs ---
kpis = fetch_from_api("kpis")
if kpis:
    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.metric(label="Volume de Microdados (Silver)", value=f"{kpis['total_linhas_silver']:,}".replace(",", " "))
    with kpi2:
        st.metric(label="Artistas Monitorizados (Gold)", value=kpis['total_artistas_gold'])
    with kpi3:
        st.metric(label="Mercados Geográficos", value=kpis['total_paises_gold'])

st.markdown("---")

# --- BLOCO VISUAL 1: MACRO TENDÊNCIAS ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("🔥 Top 10 Géneros Musicais Dominantes")
    genres_data = fetch_from_api("genres/top10")
    if genres_data:
        df_genres = pd.DataFrame(genres_data)
        fig_genres = px.bar(
            df_genres,
            x="frequencia_nas_playlists",
            y="mb_genres",
            orientation="h",
            labels={"frequencia_nas_playlists": "Aparições em Playlists", "mb_genres": "Género Musical"},
            color="frequencia_nas_playlists",
            color_continuous_scale="Viridis"
        )
        fig_genres.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False, height=400)
        st.plotly_chart(fig_genres, use_container_width=True)

with col2:
    st.subheader("🌍 Distribuição de Consumo por Região")
    countries_data = fetch_from_api("countries/distribution")
    if countries_data:
        df_countries = pd.DataFrame(countries_data)
        fig_countries = px.pie(
            df_countries,
            values="total_faixas_ouvidas",
            names="mb_country",
            hole=0.4,
            labels={"total_faixas_ouvidas": "Faixas Ouvidas", "mb_country": "País / Região"},
            color_discrete_sequence=px.colors.sequential.RdBu
        )
        fig_countries.update_layout(height=400)
        st.plotly_chart(fig_countries, use_container_width=True)

st.markdown("---")

# --- BLOCO VISUAL 2: CORRELAÇÃO DE ARTISTAS ---
st.subheader("📊 Concentração de Audiência: Alcance vs. Playlists Únicas")
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
            "playlists_unicas": "Presença em Playlists Únicas",
            "total_seguidores_alcancados": "Total de Seguidores Alcançados",
            "total_aparicoes": "Total de Aparições"
        },
        text="artist_name"
    )
    fig_scatter.update_traces(textposition='top center')
    fig_scatter.update_layout(height=500)
    st.plotly_chart(fig_scatter, use_container_width=True)

st.markdown("---")

# --- BLOCO VISUAL 3: INSPEÇÃO DA TABELA DE FACTOS ---
st.subheader("🔎 Inspecção de Microdados em Tempo Real (Via API)")
fact_data = fetch_from_api("fact/sample", params={"artista": artista_selecionado, "pais": pais_selecionado})

if fact_data:
    df_fact_sample = pd.DataFrame(fact_data)
    df_fact_sample.columns = ["Playlist", "Faixa", "Artista", "Álbum", "Duração (Min)", "País"]
    st.dataframe(df_fact_sample, use_container_width=True)