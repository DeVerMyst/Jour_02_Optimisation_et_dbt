# Mission Défi : Extension dbt & Dashboard Streamlit
## Enrichir le Data Warehouse pour Alimenter une Application Décisionnelle

Ce document détaille le travail d'extension à réaliser une fois que vous avez récupéré le template de base `app.py` présenté lors du live-coding.

---

## 1. Contexte & Objectif Métier

Le template de base `app.py` interroge les tables `analytics.dim_artists` et `analytics.fct_top_hits`.  
Votre direction éditoriale souhaite maintenant une vision macroéconomique comparative : **comprendre la signature audio de chaque genre musical** pour identifier les genres les plus dynamiques et les plus dansants.

Plutôt que d'écrire des calculs d'agrégation complexes et lents en Python dans Streamlit, **vous devez faire faire le travail lourd à dbt dans PostgreSQL**, puis simplement afficher le résultat final dans Streamlit.

---

## 2. Défi dbt : Créer le Modèle `dim_genre_profile`

### A. Spécifications du modèle SQL
Créez le fichier `spotify_dbt/models/marts/dim_genre_profile.sql` :

* **Matérialisation :** `table` (via `{{ config(materialized='table') }}`).
* **Dépendance :** Référencez `{{ ref('stg_spotify_tracks') }}`.
* **Colonnes à calculer par `genre` :**
  1. `genre` : Le nom du genre.
  2. `total_tracks` : Nombre total de titres du genre.
  3. `avg_danceability` : Danceability moyenne (arrondie à 3 décimales).
  4. `avg_energy` : Énergie moyenne (arrondie à 3 décimales).
  5. `avg_valence` : Positivité / humeur musicale moyenne (arrondie à 3 décimales).
  6. `avg_tempo` : Tempo moyen en BPM (arrondi à 1 décimale).
  7. `avg_popularity` : Popularité moyenne (arrondie à 1 décimale).
  8. `hit_ratio` : Pourcentage de titres ayant une `popularity >= 70` :
     ```sql
     ROUND(
         (COUNT(CASE WHEN popularity >= 70 THEN 1 END)::numeric / COUNT(*)) * 100, 
         1
     ) AS hit_ratio
     ```
* **Filtre de volumétrie :** Écartez les genres contenant moins de 100 morceaux avec `HAVING COUNT(*) >= 100`.
* **Tri :** Par défaut ordonné par `hit_ratio DESC`.

### B. Compilation et Exécution dans le Terminal
Dans votre terminal :

```bash
uv run dbt run --select dim_genre_profile
```

### C. Déclaration des Tests de Qualité
Dans votre fichier `spotify_dbt/models/marts/schema.yml`, ajoutez les contraintes pour votre nouveau modèle :

```yaml
  - name: dim_genre_profile
    description: "Profil moyen des caractéristiques audio et taux de hits par genre musical"
    columns:
      - name: genre
        description: "Identifiant unique du genre"
        tests:
          - unique
          - not_null
      - name: hit_ratio
        tests:
          - not_null
```

Validez vos tests :
```bash
uv run dbt test --select dim_genre_profile
```

---

## 3. Défi Streamlit : Ajouter l'Onglet "Radar & Profil des Genres"

Ouvrez le fichier `app.py` fourni par votre formateur.

### A. Ajouter la fonction de chargement avec Cache
Créez la fonction qui interroge la nouvelle table matérialisée par dbt :

```python
@st.cache_data(ttl=300)
def load_genre_profiles():
    query = """
        SELECT 
            genre, 
            total_tracks, 
            avg_danceability, 
            avg_energy, 
            avg_valence, 
            avg_tempo, 
            avg_popularity, 
            hit_ratio
        FROM analytics.dim_genre_profile
        ORDER BY hit_ratio DESC;
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)
```

### B. Ajouter un onglet ou une section dédiée dans l'interface
Ajoutez un nouvel onglet dans Streamlit :

```python
# Exemple d'intégration dans app.py
df_genres = load_genre_profiles()

st.subheader("Analyse Comparative des Genres Musicaux")

col_left, col_right = st.columns(2)

with col_left:
    # Top genres par proportion de hits
    fig_hits = px.bar(
        df_genres.head(15),
        x="hit_ratio",
        y="genre",
        orientation="h",
        title="Top 15 Genres par Taux de Succès (% de Hits >= 70)",
        labels={"hit_ratio": "% de Hits", "genre": "Genre"},
        color="hit_ratio",
        color_continuous_scale="Viridis",
        text_auto=".1f"
    )
    fig_hits.update_layout(yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_hits, use_container_width=True)

with col_right:
    # Scatter plot interactif : Énergie vs Danceability
    fig_bubble = px.scatter(
        df_genres,
        x="avg_danceability",
        y="avg_energy",
        size="total_tracks",
        color="hit_ratio",
        hover_name="genre",
        hover_data=["avg_popularity", "avg_tempo"],
        title="Cartographie des Genres (Taille = Volume de Titres)",
        labels={
            "avg_danceability": "Danceability Moyenne",
            "avg_energy": "Énergie Moyenne",
            "hit_ratio": "% Hits"
        }
    )
    st.plotly_chart(fig_bubble, use_container_width=True)
```

---

## 4. Défi Bonus (Pour les plus rapides) : Filtrage par Format de Morceau

Dans l'industrie musicale, la durée d'un morceau impacte fortement sa consommation en streaming.

1. **Dans dbt :**  
   Modifiez le modèle `fct_top_hits.sql` pour ajouter une dimension dérivée `duration_format` :
   ```sql
   CASE 
       WHEN duration_ms < 150000 THEN 'Court (< 2m30)'
       WHEN duration_ms BETWEEN 150000 AND 240000 THEN 'Standard (2m30 - 4m)'
       ELSE 'Long (> 4m)'
   END AS duration_format
   ```
2. **Rejouez dbt :**
   ```bash
   uv run dbt run --select fct_top_hits
   ```
3. **Dans Streamlit :**  
   Ajoutez un sélecteur `st.sidebar.radio("Format de morceau :", ["Tous", "Court (< 2m30)", "Standard (2m30 - 4m)", "Long (> 4m)"])` et filtrez dynamiquement vos requêtes !

---

## 5. Critères d'Évaluation du Défi

* [ ] Le modèle `dim_genre_profile.sql` compile et s'exécute sans erreur (`dbt run`).
* [ ] Les tests dbt `unique` et `not_null` sont validés (`dbt test`).
* [ ] L'application Streamlit tourne sans saccade (`http://localhost:8501`).
* [ ] Les requêtes SQL dans Python utilisent impérativement le décorateur `@st.cache_data`.
* [ ] Les graphiques Plotly sont lisibles, interactifs et étiquetés proprement.
