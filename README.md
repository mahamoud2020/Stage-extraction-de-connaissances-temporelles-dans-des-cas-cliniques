Pipeline de Coréférence E3C (Test)

Installation

Installer les dépendances :

pip install -r requirements.txt





Cloner le dépôt CorPipe à la racine de ce dossier :

git clone \[https://github.com/ufal/crac2025-corpipe.git](https://github.com/ufal/crac2025-corpipe.git)





Utilisation

Pour lancer l'intégralité de la chaîne (Conversion -> Inférence -> Extraction -> Évaluation), exécutez le script  :

python run\_pipeline.py





Note : Les fichiers XML sources doivent être placés dans le dossier data/xml\_source/.

Sorties

Les résultats de l'inférence sont générés dans data/conllu\_sortie/.

Un récapitulatif structuré est créé dans data/resultats\_coreferences.csv.



