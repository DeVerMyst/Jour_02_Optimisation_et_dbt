# Jour 2 : Optimisation SQL, Indexation Stratégique & Transformation avec dbt
## Master 1 IA & Data · YNOV Campus (7 heures)

---

### Objectifs de la journée :
* **Matinée (08h45 - 12h45 · 4h) :**
  1. Diagnostic approfondi avec `EXPLAIN (ANALYZE, BUFFERS)` (lecture des arbres, coûts, temps, blocs de 8 Ko).
  2. Indexation stratégique PostgreSQL (B-Tree, index composites, index partiels, index sur expressions).
  3. Gestion de la mémoire et tris avec `work_mem` (élimination du déversement sur disque Disk Spill).
  4. Initiation pratique à **dbt** (*data build tool*) : premier modèle staging `stg_`, commande `dbt run` et tests YAML.
* **Après-midi (13h45 - 16h45 · 3h) :**
  * **Projet dbt complet de A à Z** : Construction d'un pipeline de transformation analytics complet avec modèles staging, intermediate, marts, tests d'intégrité et documentation du graphe de lignage (Lineage Graph).

---

### Démarrage en 2 minutes :

#### 1. Lancer l'instance PostgreSQL avec Docker :
```bash
docker compose up -d
```
*(PostgreSQL 16 tourne sur le port `5432` et l'interface Web pgweb sur `http://localhost:8081`)*

#### 2. Installer les dépendances avec `uv` :
```bash
uv sync
```

#### 3. Ouvrir les Notebooks :
* **Matin (Optimisation & Indexation) :** `02_Optimisation_et_Indexation_exercices.ipynb`
* **Après-Midi (Projet dbt de Bout en Bout) :** `02_TP_ApresMidi_dbt_Projet_Exercices.ipynb`

---

### Arrêter l'environnement :
```bash
docker compose down
```
