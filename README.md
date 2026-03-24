# Pipeline de résolution de coréférences - Corpus E3C 



Ce dépôt contient le code et les résultats du pipeline automatisé permettant d'extraire des entités et de résoudre des coréférences sur les cas cliniques en français du corpus E3C, en utilisant le modèle **CorPipe** (architecture mT5-large).



## Architecture du Pipeline



Le script principal `run\_pipeline.py` exécute les 4 étapes suivantes de manière séquentielle :



1\. **Prétraitement et Conversion (XMI vers CoNLL-U) :** Extraction de la tokenisation d'origine et enrichissement linguistique (Lemmatisation, POS tags, arbres de dépendances) grâce au modèle `fr\_core\_news\_sm` de **spaCy**.

2\. **Inférence (CorPipe) :** Exécution du modèle sur les fichiers `.conllu` pour extraire les mentions et les chaînes de coréférence.

3\. **Extraction CSV :** Structuration des prédictions brutes dans un fichier tabulaire (`data/resultats\_coreferences.csv`).

4\. **Évaluation :** Comparaison entre les prédictions du modèle et les annotations manuelles du corpus E3C (vérité terrain).






## Installation et Utilisation



**1. Installer les dépendances :**



pip install -r requirements.txt

python -m spacy download fr\_core\_news\_sm



**2. Télécharger le modèle CorPipe :**



git clone https://github.com/ufal/crac2025-corpipe.git](https://github.com/ufal/crac2025-corpipe.git)





**3. Lancer le pipeline :**



python run\_pipeline.py

