# Guide Pratique : Streamlit & Plotly pour la Data
## Transformer un Data Warehouse dbt / PostgreSQL en Dashboard Interactif

Ce guide s'adresse aux Data Engineers et Data Scientists souhaitant concevoir rapidement une application analytique interactive connectée à une base de données relationnelle.

---

## 1. Comprendre le Modèle d'Exécution de Streamlit

Contrairement aux frameworks web traditionnels (Flask, FastAPI, Django) qui gèrent des routes HTTP et un frontend séparé (React, Vue) :

* **Un script Streamlit s'exécute de haut en bas à chaque interaction.**
* Dès qu'un utilisateur déplace un curseur (*slider*) ou sélectionne un élément dans un menu déroulant (*selectbox*), Streamlit ré-exécute l'intégralité du script Python avec la nouvelle valeur.
* **Le piège majeur en Data Engineering :**  
  Si votre script exécute une requête SQL lourde à la racine, cette requête sera envoyée à PostgreSQL à chaque mouvement de curseur !  
  $\rightarrow$ **Solution obligatoire : le cache Streamlit (`@st.cache_data`).**

---

## 2. Connexion à PostgreSQL & Mise en Cache des Requêtes

### A. Connexion via SQLAlchemy

```python
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/ynov_data_db"

@st.cache_resource
def get_database_engine():
    """Crée et met en cache le pool de connexions à PostgreSQL."""
    return create_engine(DB_URL)

engine = get_database_engine()
```

### B. Le décorateur `@st.cache_data`

`@st.cache_data` stocke le résultat d'une fonction en mémoire vive. Si la fonction est appelée avec les mêmes arguments, Streamlit renvoie immédiatement le DataFrame sans interroger PostgreSQL :

```python
@st.cache_data(ttl=300)  # Expire au bout de 5 minutes (TTL = Time To Live)
def load_top_artists(min_popularity: int = 50, limit: int = 10) -> pd.DataFrame:
    query = """
        SELECT 
            REPLACE(artist_name, ';', ', ') AS artist_name, 
            main_genre, 
            total_tracks, 
            avg_popularity, 
            avg_danceability
        FROM analytics.dim_artists
        WHERE avg_popularity >= :min_pop
        ORDER BY avg_popularity DESC
        LIMIT :limit;
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params={"min_pop": min_popularity, "limit": limit})
```

---

## 3. Les Éléments d'Interface (Widgets & Layout)

### A. Barre Latérale (`st.sidebar`)
La barre latérale isole les paramètres de filtrage du contenu principal :

```python
st.sidebar.header("Filtres Analytics")

# Menu déroulant simple
selected_genre = st.sidebar.selectbox(
    "Choisir un genre :",
    options=["Tous", "rock", "pop", "dance", "electronic", "classical"]
)

# Curseur numérique
min_popularity = st.sidebar.slider(
    "Popularité minimale :",
    min_value=0,
    max_value=100,
    value=70,
    step=5
)

# Sélecteur multiple
selected_metrics = st.sidebar.multiselect(
    "Indicateurs audio à afficher :",
    options=["danceability", "energy", "tempo"],
    default=["danceability", "energy"]
)
```

### B. Titres et Cartes de KPIs (`st.columns` & `st.metric`)

```python
st.title("Spotify Warehouse Analytics")
st.markdown("Dashboard interactif connecté aux tables marts matérialisées par **dbt**.")

# Création de 3 colonnes de métriques
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Total Morceaux Analysés", value="114 000")

with col2:
    st.metric(label="Popularité Moyenne", value="68.4 / 100", delta="+2.1 vs baseline")

with col3:
    st.metric(label="Nombre d'Artistes", value="31 437")
```

---

## 4. Visualisations Interactives avec Plotly Express

Plotly Express (`px`) génère des visualisations 100 % interactives (zoom, infobulles au survol, filtres de légende).

### A. Graphique en Barres Horizontales : Top Artistes

> **Astuce Design :** Privilégiez toujours un graphique à barres **horizontales** (`orientation="h"`) pour des classements ou des entités textuelles (noms d'artistes). Cela évite d'incliner le texte à -45° et empêche Plotly d'étirer démesurément une barre unique sur toute la largeur de l'écran.

```python
import plotly.express as px

df_artists = load_top_artists(min_popularity=min_popularity)

fig_bar = px.bar(
    df_artists,
    x="avg_popularity",
    y="artist_name",
    orientation="h",
    color="main_genre",
    title="Top Artistes par Popularité Moyenne",
    labels={"artist_name": "Artiste", "avg_popularity": "Popularité Moyenne", "main_genre": "Genre"},
    text_auto=".1f"
)
fig_bar.update_layout(
    yaxis=dict(autorange="reversed"),
    xaxis=dict(range=[0, 100], title="Popularité Moyenne"),
    height=max(320, len(df_artists) * 35 + 80),
    bargap=0.3
)

# Affichage dans Streamlit
st.plotly_chart(fig_bar, use_container_width=True)
```

### B. Nuage de Points : Danceability vs Energy

```python
fig_scatter = px.scatter(
    df_hits,
    x="danceability",
    y="energy",
    color="genre",
    hover_name="track_name",
    hover_data=["artist_name", "popularity"],
    title="Distribution Audio : Danceability vs Énergie",
    opacity=0.7
)

st.plotly_chart(fig_scatter, use_container_width=True)
```

### C. Tableau de Données Interactif (`st.dataframe`)

```python
st.subheader("Détail des Données Marts")
st.dataframe(
    df_artists,
    use_container_width=True,
    hide_index=True
)

# Bouton de téléchargement CSV
csv_data = df_artists.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Exporter en CSV",
    data=csv_data,
    file_name="spotify_top_artists.csv",
    mime="text/csv"
)
```

---

## 5. Exemple Minimal Complet (`app_minimal.py`)

Voici une application complète fonctionnelle en 45 lignes :

```python
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text

# Configuration de la page
st.set_page_config(page_title="Spotify dbt Analytics", layout="wide")

# Connexion DB & Cache
DB_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/ynov_data_db"

@st.cache_resource
def get_engine():
    return create_engine(DB_URL)

@st.cache_data(ttl=300)
def get_data(min_pop: int):
    engine = get_engine()
    query = text("""
        SELECT 
            REPLACE(artist_name, ';', ', ') AS artist_name, 
            main_genre, 
            total_tracks, 
            avg_popularity
        FROM analytics.dim_artists
        WHERE avg_popularity >= :pop
        ORDER BY avg_popularity DESC
        LIMIT 10;
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"pop": min_pop})

# Sidebar
st.sidebar.header("Paramètres")
pop_filter = st.sidebar.slider("Popularité min :", 0, 100, 60, 5)

# Interface principale
st.title("Spotify dbt Marts Explorer")
df = get_data(pop_filter)

col1, col2 = st.columns(2)
col1.metric("Artistes qualifiés", len(df))
col2.metric("Popularité max", f"{df['avg_popularity'].max():.1f}" if not df.empty else "0")

if not df.empty:
    fig = px.bar(
        df, 
        x="avg_popularity", 
        y="artist_name", 
        orientation="h",
        color="main_genre", 
        title="Top Artistes",
        text_auto=".1f"
    )
    fig.update_layout(
        yaxis=dict(autorange="reversed"), 
        xaxis=dict(range=[0, 100]), 
        height=max(300, len(df)*35+80),
        bargap=0.3
    )
    st.plotly_chart(fig, use_container_width=True)

st.dataframe(df, use_container_width=True)
```

---

## 6. Lancement de l'Application

Dans votre terminal :

```bash
uv run streamlit run app.py
```

L'application s'ouvre automatiquement dans votre navigateur par défaut à l'adresse `http://localhost:8501`.  
À chaque modification enregistrée dans votre fichier `app.py`, cliquez sur **"Always rerun"** dans le coin supérieur droit du navigateur pour activer le rafraîchissement à chaud.
