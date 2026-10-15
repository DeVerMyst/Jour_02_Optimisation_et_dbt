"""
Application Streamlit Template - Spotify Data Warehouse Analytics
A completer par les etudiants suite a la demonstration live du formateur.
Pour lancer l'application : uv run streamlit run app_template.py
"""

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text

# 1. Configuration de la page
st.set_page_config(
    page_title="Spotify Warehouse Analytics",
    layout="wide"
)

# 2. Connexion PostgreSQL
DB_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/ynov_data_db"

@st.cache_resource
def get_engine():
    return create_engine(DB_URL)

engine = get_engine()

# 3. Fonctions d'acces aux donnees avec cache
@st.cache_data(ttl=300)
def load_top_artists(min_pop: int = 50, limit: int = 15) -> pd.DataFrame:
    query = """
        SELECT 
            REPLACE(artist_name, ';', ', ') AS artist_name, 
            main_genre, 
            total_tracks, 
            avg_popularity, 
            avg_danceability, 
            avg_tempo
        FROM analytics.dim_artists
        WHERE avg_popularity >= :pop
        ORDER BY avg_popularity DESC
        LIMIT :lim;
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params={"pop": min_pop, "lim": limit})

@st.cache_data(ttl=300)
def load_top_hits(min_pop: int = 70, genre: str = "Tous") -> pd.DataFrame:
    base_query = """
        SELECT 
            track_name, 
            REPLACE(artist_name, ';', ', ') AS artist_name, 
            genre, 
            popularity, 
            danceability, 
            energy, 
            tempo
        FROM analytics.fct_top_hits
        WHERE popularity >= :pop
    """
    params = {"pop": min_pop}
    if genre != "Tous":
        base_query += " AND genre = :g"
        params["g"] = genre
        
    base_query += " ORDER BY popularity DESC LIMIT 200;"
    with engine.connect() as conn:
        return pd.read_sql(text(base_query), conn, params=params)

# 4. Barre laterale (Sidebar)
st.sidebar.title("Filtres Analytics")
pop_filter = st.sidebar.slider("Popularite minimale :", 50, 100, 70, 5)

# 5. Interface Principale
st.title("Spotify Warehouse Analytics")
st.markdown("Dashboard decisionnel connecte aux tables **dbt Marts** (`analytics`).")

df_artists = load_top_artists(min_pop=pop_filter)

# Ligne de KPIs
col1, col2, col3 = st.columns(3)
col1.metric("Artistes Qualifies", len(df_artists))
col2.metric("Popularite Moyenne du Top", f"{df_artists['avg_popularity'].mean():.1f} / 100" if not df_artists.empty else "0")
col3.metric("Top Artiste", df_artists.iloc[0]['artist_name'] if not df_artists.empty else "N/A")

st.markdown("---")

# Graphique Top Artistes (format horizontal propre)
if not df_artists.empty:
    fig_artists = px.bar(
        df_artists,
        x="avg_popularity",
        y="artist_name",
        orientation="h",
        color="main_genre",
        title="Top Artistes par Popularite Moyenne",
        labels={"artist_name": "Artiste", "avg_popularity": "Popularite Moyenne", "main_genre": "Genre"},
        text_auto=".1f"
    )
    fig_artists.update_layout(
        yaxis=dict(autorange="reversed"),
        xaxis=dict(range=[0, 100]),
        height=max(320, len(df_artists) * 35 + 80),
        bargap=0.3
    )
    st.plotly_chart(fig_artists, use_container_width=True)

# TODO: A vous de jouer pour la Mission Extension !
# 1. Ajoutez les filtres par genre
# 2. Creez et connectez le modele dim_genre_profile
# 3. Ajoutez le scatter plot Danceability vs Energy
