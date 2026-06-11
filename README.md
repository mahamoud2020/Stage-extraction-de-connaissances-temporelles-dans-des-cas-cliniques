# Pipeline de résolution de coréférences et d'extraction des informations temporelles- Corpus E3C 

Ce dépôt contient le code et les résultats du pipeline automatisé permettant d'extraire des entités et de résoudre des coréférences sur les cas cliniques en français du corpus E3C. Il utilise l'outil **UDPipe 2** pour le parsing syntaxique et le modèle **CorPipe** (architecture mT5-large) pour l'inférence.

---

## 🗂️ Architecture du Projet

L'architecture est modulaire pour séparer les données, le code d'exécution et les outils externes partagés (CorPipe) :

```text
📁 Projet_Global/
│
├── analyse_de_sequence         #  Analyse de séquence   
|
├── 📁 crac2025-corpipe/        # Dépôt officiel CorPipe cloné
├── 📁 scripts/                 # Scripts partagés (convert_batch, evaluation, extraction_csv, run_batch_corpipe)
│
└── 📁 Français/                # Répertoire de travail
    │
    ├── 📁 data/
    │   ├── xml_source/         # Fichiers XML de départ
    │   ├── conllu_entree/      # Fichiers parsés par UDPipe
    │   ├── conllu_sorti/       # Fichiers traités par CorPipe 
    │   └── sortie_csv/         # Tableaux de résultats finaux
    │
    ├── 📁 pipeline/            
    │   ├── traitement_udpipe.py    # Prend en entrée le texte brut, fais la tokenisation et l'analyse syntaxique, génère des fichiers .conllu
    │   ├── traitement_corpipe.py   # Utilise les fichiers .conllu générés à l'étape 1, détecte les mentions et crée des liens entre elles
    │   └── traitement_extraction.py # Utilise les fichiers .15.conllu générés à l'étape 2 et extraits des infos (tête lexicale, nature, etc) 
    │
    └── run_pipeline.py         # Programme principal à exécuter 


```


## Étapes du Pipeline

Le script principal `run_pipeline.py` exécute dynamiquement les 3 étapes suivantes :

1\. **Parsing Syntaxique (`traitement_udpipe.py`) :** Extraction de la tokenisation d'origine et enrichissement linguistique (lemmatisation, POS tags, arbres de dépendances) via l'API d'UDPipe 2 (modèle `french-gsd-ud`). Conversion des XML en `.conllu`.

2\. **Inférence (`traitement_corpipe.py`) :** Exécution du modèle CorPipe sur les fichiers `.conllu` pour extraire les mentions et lier les chaînes de coréférences.

3\. **Extraction et CSV (`traitement_extraction.py`) :** Traitement linguistique des entités (extraction des têtes lexicales, natures, fonctions syntaxiques) et génération des fichiers tabulaires dans `data/sortie_csv/` (dont un format adapté pour l'analyse de séquences TraMineR).