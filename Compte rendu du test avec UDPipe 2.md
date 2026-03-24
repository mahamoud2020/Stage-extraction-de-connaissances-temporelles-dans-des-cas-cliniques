&#x09;				**Compte rendu du test avec UDPipe 2**







**Déploiement d'UDPipe 2**



Pour générer les informations linguistiques (Lemmes, POS tags, dépendances syntaxiques) requises par le format CoNLL-U, j'ai modifié mon script *run\_pipeline.py*.



Plutôt que d'alourdir le pipeline avec un modèle local, j'ai configuré le script pour qu'il interroge directement l'API web d'UDPipe 2 (hébergée sur les serveurs de l'université LINDAT/UFAL). Ce que le script fait :



* Le script lit le texte brut des fichiers XML du corpus.
* Il envoie ce texte à l'API avec le modèle français (*french-gsd-ud*).
* Il récupère en retour un fichier CoNLL-U annoté selon les standards Universal Dependencies (UD)



J'en ai profité pour automatiser entièrement la suite du pipeline. Le script enchaîne l'appel à l'API, l'exécution de CorPipe sur les fichiers générés, puis l'extraction des prédictions (les fichiers *.15.conllu*) vers un fichier CSV.





**Résultats obtenus** 



Le changement d'outil d'analyse grammaticale (spaCy VS UDPipe 2) a eu un impact sur le comportement de CorPipe.

Sur notre lot de documents de test (J'ai utilisé 5 fichiers pour le moment):

Avec *spaCy* : CorPipe avait extrait 425 mentions.

Avec *UDPipe 2* : CorPipe a extrait 778 mentions.





**Conclusion** 



J'ai pu constater que CorPipe est sensible à la qualité des arbres syntaxiques qu'on lui fournit en entrée. Puisque UDPipe 2 et CorPipe partagent la même architecture et les mêmes standards (développés par la même équipe), le modèle s'est montré beaucoup plus performant pour identifier les chaînes de coréférences purement linguistiques.



Cependant cette performance linguistique peut se traduire par une sur-génération massive. Sachant que notre vérité terrain (le corpus) ne compte qu'environ 107 annotations cliniques sur ce lot (5 fichiers) , CorPipe capte énormément de bruit (les pronoms "qui", "il", les déterminants, et les groupes nominaux non médicaux).





&#x20;     			

&#x09;		**Décomposition du fichier sortie**





**L'En-tête** 



Les informations se trouvant en haut du fichier de sortie.



* \# newdoc : indique le début d'un nouveau document.



* \# generator = UDPipe 2, https://lindat.mff.cuni.cz/services/udpipe: indique que appel à l'API a fonctionné.



* \# sent\_id = 1 : c'est l'identifiant de la phrase (sentence).



* \# text = Nous rapportons l'observation... : il s'agit du texte brut de la phrase, tel qu'il était dans le corpus E3C.







**Les 10 colonnes** 



Sous chaque phrase, il y a un grand tableau. Chaque ligne représente un seul un token.

CoNLL-U impose 10 colonnes séparées par des tabulations. 



Par exemple, la ligne 8 de la phrase 2 : 



8  patient  patient  NOUN  \_  Gender=Masc|Number=Sing  6  obj  \_  Entity=c3)|SpaceAfter=No



|Colonne|Nom|Explication|Explication sur le token "patient"|
|-|-|-|-|
|1|ID|La position du mot dans la phrase.|8 (C'est le 8ème mot)|
|2|FORM|Le mot exact tel qu'il est écrit dans le texte.|"patient"|
|3|LEMMA|La forme de base.|"patient"|
|4|UPOS|La catégorie grammaticale (Nom, Verbe, etc).|NOUN (Nom commun)|
|5|XPOS|Un tag POS spécifique à la langue (souvent vide, noté par \_ ).|\_|
|6|FEATS|Les traits morphologiques|Gender=Masc\|Number=Sing (Masculin, Singulier)|
|7|HEAD|L'ID du mot auquel celui-ci est rattaché (arbre syntaxique).|6 ("patient" est rattaché au mot n°6, le verbe "trouve")|
|8|DEPREL|Le lien syntaxique avec le mot "tête".|obj (indique l'objet direct du verbe "trouve")|
|9|DEPS|Dépendances étendues (en général non calculées, noté par \_ ).|\_|
|10|MISC|Les informations diverses, dont la coréférence.|Entity=c3)\|SpaceAfter=No|







**Analyse de la dernière colonne (10)** 



Les prédictions de coréférence se trouvent dans la 10ème colonne, sous une forme spécifique (par exemple : Entity=(c3--2). 

J'ai essayé de comprendre en profondeur cette notation qui suit le standard CorefUD : 



* Le "c" + le nombre (ex : c3) : "c" signifie Cluster (chaîne de coréférence). Le chiffre est l'identifiant unique de l'entité dans le document.Tous les termes qui renvoient au même référent (ex : "un homme", "patient", "qui") partageront la même étiquette c3.



* Les parenthèses () : Elles délimitent la taille de la mention. Une parenthèse ouvrante (c3 marque le premier mot d'un groupe, et la parenthèse fermante c3) en marque la fin. Si la mention ne fait qu'un seul mot (par ex un pronom), elle s'écrit (c3).



* Les tirets (--) et le dernier chiffre (ex : --2) : indique la "tête syntaxique". Le chiffre précise la position du mot noyau au sein de la mention. Par exemple, dans le groupe "un homme de 55 ans", le modèle indique que le 2ème mot ("homme") est le plus important (semantiquement) de l'entité.



