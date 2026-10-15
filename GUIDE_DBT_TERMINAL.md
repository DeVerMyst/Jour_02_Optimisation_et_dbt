# Guide dbt en Ligne de Commande (CLI)
## Du `dbt init` à la Mise en Production Analytics

Ce guide détaille pas à pas la création, la configuration et l'exécution d'un projet **dbt** (*data build tool*) directement depuis le terminal.

---

## 1. Prérequis

Avant de lancer la moindre commande dbt, assurez-vous que :

1. Le conteneur PostgreSQL est actif :
   ```bash
   docker compose up -d
   ```
2. Les dépendances Python du projet sont synchronisées avec `uv` :
   ```bash
   uv sync
   ```
3. La base de données PostgreSQL contient les données brutes (`spotify_tracks_raw`).  
   *(Si ce n'est pas encore fait, exécutez le script d'ingestion ou le début du notebook du matin).*

> **Note sur l'exécution des commandes :**  
> Si votre terminal n'a pas activé l'environnement virtuel local, préfixez chaque commande dbt par `uv run` (exemple : `uv run dbt init`, `uv run dbt run`).  
> Si vous activez votre environnement virtuel (`.venv\Scripts\activate` sous Windows), vous pouvez taper directement `dbt init`, `dbt run`.

---

## 2. Étape 1 : Initialisation avec `dbt init`

Placez-vous dans le répertoire racine du projet :

```bash
uv run dbt init spotify_analytics
```

Un assistant interactif se lance dans le terminal. Répondez aux invites successives avec les paramètres suivants :

| Invite dbt | Réponse à saisir | Explication |
| :--- | :--- | :--- |
| **Which database would you like to use?** | `1` (ou tapez `postgres`) | Sélectionne l'adaptateur `dbt-postgres` |
| **host (hostname for the database)** | `localhost` | Adresse de la machine hôte |
| **port [5432]** | `5432` | Port d'écoute de PostgreSQL |
| **user (dev username)** | `postgres` | Utilisateur défini dans `docker-compose.yml` |
| **pass (dev password)** | `postgres` | Mot de passe défini dans `docker-compose.yml` |
| **dbname (default database)** | `ynov_data_db` | Nom de la base de données du cours |
| **schema (default schema that dbt will build in)** | `analytics` | Schéma PostgreSQL cible pour vos modèles |
| **threads (1 or more)** | `4` | Nombre de modèles compilés en parallèle |

À la fin de la saisie, dbt affiche le message de confirmation confirmant la création du projet.

---

## 3. Anatomie du Projet Généré

Entrez dans le dossier créé :

```bash
cd spotify_analytics
```

Voici l'arborescence générée par `dbt init` :

```text
spotify_analytics/
├── dbt_project.yml        <- Cerveau du projet (nom, versions, configurations de matérialisation)
├── README.md              <- Documentation d'accueil du projet
├── models/                <- Dossier de TOUS vos modèles de transformation SQL
│   └── example/           <- Exemples pré-générés (à supprimer ou remplacer)
│       ├── my_first_dbt_model.sql
│       ├── my_second_dbt_model.sql
│       └── schema.yml
├── analyses/              <- Requêtes analytiques ad-hoc (non matérialisées dans PostgreSQL)
├── macros/                <- Fonctions SQL Jinja réutilisables
├── seeds/                 <- Fichiers CSV statiques (tables de correspondance pays, codes postaux...)
├── snapshots/             <- Historisation des données à évolution lente (SCD Type 2)
└── tests/                 <- Tests SQL singuliers (requêtes qui ne doivent retourner 0 ligne)
```

### Où sont enregistrés les identifiants de connexion ?
`dbt init` a enregistré vos identifiants dans le fichier global utilisateur :
* **Windows :** `C:\Users\<votre_nom>\.dbt\profiles.yml`
* **macOS / Linux :** `~/.dbt/profiles.yml`

Le profil porte par défaut le même nom que le projet (`spotify_analytics`), référencé dans `dbt_project.yml` via la clé `profile: 'spotify_analytics'`.

---

## 4. Étape 2 : Validation de la Connexion avec `dbt debug`

Avant de coder la moindre ligne de SQL, vérifiez que dbt communique parfaitement avec PostgreSQL :

```bash
uv run dbt debug
```

dbt teste 4 éléments critiques :
1. `dbt_project.yml` valide.
2. `profiles.yml` valide et accessible.
3. Dépendances et adaptateur `dbt-postgres` opérationnels.
4. Connexion réseau à PostgreSQL (`ynov_data_db` sur `localhost:5432`).

Si tous les indicateurs sont au vert avec la mention finale **`All checks passed!`**, votre environnement est prêt.

---

## 5. Étape 3 : Structuration des Modèles (`models/`)

Supprimez les exemples par défaut et mettez en place l'architecture moderne en 3 couches préconisée par dbt Labs :

```bash
# Dans spotify_analytics/
rm -rf models/example
mkdir models/staging models/intermediate models/marts
```

### A. Déclaration de la Source (`models/staging/sources.yml`)
Créez le fichier `models/staging/sources.yml` pour déclarer la table brute chargée dans PostgreSQL :

```yaml
version: 2

sources:
  - name: spotify_raw
    database: ynov_data_db
    schema: public
    tables:
      - name: spotify_tracks_raw
        description: "Table brute issue du fichier spotify_tracks.parquet (114 000 lignes)"
```

### B. Couche Staging (`models/staging/stg_spotify_tracks.sql`)
La couche staging nettoie, filtre, type et déduplique les données brutes :

```sql
{{ config(materialized='view') }}

WITH raw_source AS (
    SELECT * FROM {{ source('spotify_raw', 'spotify_tracks_raw') }}
),

deduplicated AS (
    SELECT
        track_id,
        track_name,
        artists,
        album_name,
        popularity,
        duration_ms,
        explicit,
        danceability,
        energy,
        track_genre,
        ROW_NUMBER() OVER (
            PARTITION BY track_id 
            ORDER BY popularity DESC
        ) AS row_num
    FROM raw_source
    WHERE track_id IS NOT NULL
)

SELECT
    track_id,
    track_name,
    artists,
    album_name,
    popularity,
    duration_ms,
    explicit,
    danceability,
    energy,
    track_genre
FROM deduplicated
WHERE row_num = 1
```

> [!NOTE]
> **Comment fonctionne concrètement ce dédoublonnage ?**  
> `deduplicated` n'est pas une fonction SQL : c'est simplement le nom arbitraire de notre table temporaire (CTE).  
> L'élimination des doublons se déroule en **2 étapes** :
> 1. **L'étiquetage (`ROW_NUMBER() OVER (...) AS row_num`) :**  
>    Pour chaque groupe de même `track_id` (`PARTITION BY track_id`), PostgreSQL classe les morceaux du plus populaire au moins populaire (`ORDER BY popularity DESC`). La meilleure version reçoit l'étiquette `row_num = 1`, et les doublons reçoivent `row_num = 2`, `3`...
> 2. **L'élimination (`WHERE row_num = 1`) :**  
>    Le `SELECT` final ne retient que les lignes où `row_num = 1`. Tous les doublons (`row_num >= 2`) sont définitivement écartés. Le morceau devient ainsi 100 % unique.

### C. Couche Marts (`models/marts/dim_artists_stats.sql`)
La couche marts regroupe les données pour les outils de Business Intelligence (BI, Metabase, dashboards).  
Remarquez l'usage de la macro `{{ ref(...) }}` qui crée dynamiquement le graphe de dépendance :

```sql
{{ config(materialized='table') }}

SELECT
    artists,
    COUNT(DISTINCT track_id) AS total_tracks,
    ROUND(AVG(popularity), 2) AS avg_popularity,
    MAX(popularity) AS max_popularity,
    ROUND(AVG(danceability)::numeric, 4) AS avg_danceability,
    ROUND(AVG(energy)::numeric, 4) AS avg_energy
FROM {{ ref('stg_spotify_tracks') }}
GROUP BY artists
HAVING COUNT(DISTINCT track_id) >= 5
ORDER BY avg_popularity DESC
```

---

## 6. Étape 4 : Compilation et Exécution

### 1. Voir le code SQL généré : `dbt compile`
dbt convertit toutes les balises Jinja (`{{ ref(...) }}`, `{{ source(...) }}`) en SQL pur exécutable par PostgreSQL :

```bash
uv run dbt compile
```
Le résultat compilé est consultable dans `target/compiled/spotify_analytics/models/...`. Vous pouvez vérifier le SQL réel qui sera exécuté.

### 2. Exécuter l'ensemble du projet : `dbt run`
```bash
uv run dbt run
```
dbt analyse le graphe de dépendances (DAG) et exécute les modèles dans l'ordre logique :
1. `stg_spotify_tracks` est créé en tant que **VUE** dans le schéma `analytics`.
2. `dim_artists_stats` est créé en tant que **TABLE** dans le schéma `analytics`.

### 3. Exécutions ciblées (Sélecteurs dbt)
Pour ne pas rejouer l'ensemble du projet à chaque modification :

* **Uniquement un modèle précis :**
  ```bash
  uv run dbt run --select stg_spotify_tracks
  ```
* **Tous les modèles d'un dossier :**
  ```bash
  uv run dbt run --select models/staging
  ```
* **Un modèle et tous ses ancêtres en amont (+ en préfixe) :**
  ```bash
  uv run dbt run --select +dim_artists_stats
  ```
* **Un modèle et tous ses descendants en aval (+ en suffixe) :**
  ```bash
  uv run dbt run --select stg_spotify_tracks+
  ```

---

## 7. Étape 5 : Tests de Qualité des Données

dbt intègre un moteur de tests automatisés.

Créez le fichier de test `models/staging/schema.yml` :

```yaml
version: 2

models:
  - name: stg_spotify_tracks
    description: "Données nettoyées et dédupliquées par track_id"
    columns:
      - name: track_id
        description: "Clé primaire unique du titre"
        tests:
          - unique
          - not_null

      - name: track_name
        tests:
          - not_null

      - name: popularity
        tests:
          - not_null
```

Lancez la vérification des tests :

```bash
uv run dbt test
```

dbt exécute des requêtes de validation dans PostgreSQL. Si une contrainte `unique` ou `not_null` est enfreinte, le test échoue et affiche le nombre de lignes en anomalie.

Pour tester un modèle unique :
```bash
uv run dbt test --select stg_spotify_tracks
```

---

## 8. Étape 6 : Documentation & Graphe de Lignage (DAG)

dbt génère automatiquement un site web interactif documentant l'ensemble de vos données, définitions de colonnes et dépendances.

### 1. Générer le catalogue de métadonnées :
```bash
uv run dbt docs generate
```

### 2. Lancer le serveur de visualisation web :
```bash
uv run dbt docs serve --port 8080
```

Ouvrez votre navigateur sur `http://localhost:8080`.  
Cliquez sur le bouton **Lineage Graph** en bas à droite : vous visualisez en direct le DAG dynamique reliant vos sources brutes, vos vues staging et vos tables dimensionnelles marts.

---

## 9. Aide-Mémoire des Commandes dbt

| Commande | Action |
| :--- | :--- |
| `dbt init <nom_projet>` | Crée un nouveau projet avec questionnaire interactif |
| `dbt debug` | Teste la connectivité avec PostgreSQL et vérifie la configuration |
| `dbt compile` | Traduit le code Jinja/SQL dbt en requêtes SQL brutes dans `target/` |
| `dbt run` | Exécute et matérialise les modèles (vues/tables) dans PostgreSQL |
| `dbt test` | Exécute tous les tests de qualité de données déclarés en YAML |
| `dbt build` | **La commande tout-en-un** : exécute `run` puis `test` modèle par modèle |
| `dbt docs generate` | Génère les métadonnées et le catalogue de documentation |
| `dbt docs serve` | Démarre un serveur local pour explorer la documentation et le DAG |
| `dbt clean` | Supprime les dossiers temporaires `target/` et `dbt_packages/` |
