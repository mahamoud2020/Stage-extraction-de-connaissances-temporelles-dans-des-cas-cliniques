# Pipeline de résolution de coréférences - Corpus E3C (French Layer)



Ce dépôt contient le code et les résultats du pipeline automatisé permettant d'extraire des entités et de résoudre des coréférences sur les cas cliniques en français du corpus E3C, en utilisant le modèle \*\*CorPipe\*\* (architecture mT5-large).



## Architecture du Pipeline



Le script principal `run\_pipeline.py` exécute les 4 étapes suivantes de manière séquentielle :



1\. \*\*Prétraitement et Conversion (XMI vers CoNLL-U) :\*\* Extraction de la tokenisation d'origine et enrichissement linguistique (Lemmatisation, POS tags, arbres de dépendances) grâce au modèle `fr\_core\_news\_sm` de \*\*spaCy\*\*.

2\. \*\*Inférence (CorPipe) :\*\* Exécution du modèle sur les fichiers `.conllu` pour extraire les mentions et les chaînes de coréférence.

3\. \*\*Extraction CSV :\*\* Structuration des prédictions brutes dans un fichier tabulaire (`data/resultats\_coreferences.csv`).

4\. \*\*Évaluation :\*\* Comparaison stricte entre les prédictions du modèle et les annotations manuelles du corpus E3C (vérité terrain).



## Premiers résultats (Détection de mentions)



L'évaluation sur le premier lot de documents montre une \*\*sur-génération importante\*\* de la part du modèle brut :

\- Mentions cliniques annotées manuellement : \*\*107\*\*

\- Mentions extraites par le modèle : \*\*425\*\*

\- \*\*Précision :\*\* 1.18 % | \*\*Rappel :\*\* 4.67 % | \*\*F1-Score :\*\* 1.88 %



\*\*Analyse :\*\* CorPipe extrait avec succès les mentions linguistiques (pronoms "il", "elle", déterminants + noms communs non médicaux), ce qui crée beaucoup de "bruit" (420 faux positifs) face aux annotations strictement médicales d'E3C. 

\*\*Prochaine étape :\*\* Utiliser les colonnes Lemme/POS générées par spaCy pour appliquer un filtrage sémantique croisé avec un dictionnaire médical (UMLS).



## Installation et Utilisation



\*\*1. Installer les dépendances :\*\*

```bash

pip install -r requirements.txt

python -m spacy download fr\_core\_news\_sm



\*\*2. Télécharger le modèle CorPipe

```bash

git clone \[https://github.com/ufal/crac2025-corpipe.git](https://github.com/ufal/crac2025-corpipe.git)





\*\*3. Lancer le pipeline

```bash

python run\_pipeline.py

