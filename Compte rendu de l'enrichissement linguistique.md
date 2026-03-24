&#x09;	**Compte rendu de l'enrichissement linguistique des fichiers** 





**Problème soulevé ce matin :**





Le format CoNLL-U exigé par l'outil CorPipe impose une structure stricte de 10 colonnes par mot (ID, Forme, Lemme, POS tag, etc.). Jusqu'ici, mon script de conversion (que j'ai présenté) se contentait d'extraire le texte brut et de le segmenter (tokenisation) à partir des balises XML du corpus E3C.



Cependant, les fichiers XML d'origine n'indiquent que les concepts médicaux sans fournir d'analyse grammaticale. 

Pour respecter la structure CoNLL-U et éviter les erreurs de lecture du modèle, j'avais donc neutralisé les colonnes non renseignées avec le caractère "\_".







**Solution utilisée aujourd'hui :**



Pour remplir ces colonnes vides et enrichir les données, j'ai modifié le script de conversion Python en y intégrant spaCy (fr\_core\_news\_sm).

&#x20;

Lors de cette intégration, j'ai porté une attention particulière à la tokenisation. Plutôt que de laisser spaCy redécouper les phrases (ce qui aurait cassé notre alignement avec les annotations d'origine du corpus E3C), je lui ai fourni la liste exacte des mots déjà segmentés. J'ai ensuite demandé à spaCy de calculer pour chaque mot :



* Son lemme (la forme de base du mot).
* Son étiquette morphosyntaxique (POS tag : Nom, Verbe, Déterminant, etc.).
* Ses traits morphologiques (genre, nombre) 
* ses dépendances syntaxiques.





J'ai testé la modification et le pipeline génère des fichiers CoNLL-U enrichis et complets, remplaçant les tirets par des données linguistiques.

