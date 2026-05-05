# Pipeline de résolution de coréférences - Corpus E3C (Français) 

Ce dépôt contient le code et les résultats du pipeline automatisé permettant d'extraire des entités et de résoudre des coréférences sur les cas cliniques en français du corpus E3C. Il utilise l'outil **UDPipe 2** pour le parsing syntaxique et le modèle **CorPipe** (architecture mT5-large) pour l'inférence.

---

## 🗂️ Architecture du Projet

L'architecture est modulaire pour séparer clairement les données, le code d'exécution et les outils externes partagés (CorPipe, scripts d'évaluation) :

```text
📁 Ton_Projet_Global/
│
├── 📁 crac2025-corpipe/        # Dépôt officiel CorPipe cloné
├── 📁 scripts/                 # Scripts partagés (convert_batch, evaluation...)
│
└── 📁 Français/                # Répertoire de travail
    │
    ├── 📁 data/
    │   ├── xml_source/         # Fichiers XML de départ
    │   ├── conllu_entree/      # Fichiers parsés par UDPipe
    │   ├── conllu_sorti/       # Fichiers traités par CorPipe (.15.conllu)
    │   └── sortie_csv/         # Tableaux de résultats finaux
    │
    ├── 📁 pipeline/            # Cœur du traitement
    │   ├── traitement_udpipe.py
    │   ├── traitement_corpipe.py
    │   └── traitement_extraction.py
    │
    └── run_pipeline.py         # Le chef d'orchestre


Étapes du Pipeline

Le script principal run_pipeline.py exécute dynamiquement les 3 étapes suivantes :