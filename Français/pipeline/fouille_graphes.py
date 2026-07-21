import os
import sys
import pandas as pd
from gspan_mining import gSpan

# Patch Pandas 2.0 pour la bibliothèque gspan_mining
def df_append_patch(self, other, ignore_index=False, **kwargs):
    if isinstance(other, dict):
        other = pd.DataFrame([other])
    return pd.concat([self, other], ignore_index=ignore_index)

pd.DataFrame.append = df_append_patch

# Définition des chemins
# ********************************************************************************
Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Dossier_CSV = os.path.join(Base_dir, "data", "sortie_csv")
Fichier_TXT = os.path.join(Dossier_CSV, "graphes_gspan.txt")
Fichier_Resultats = os.path.join(Dossier_CSV, "resultats_bruts_gspan.txt")

def lancer_fouille_gspan(support_ratio=0.15, min_sommets=3, max_sommets=10000):
    print(" Lancement de l'algorithme gSpan pour la fouille de sous-graphes fréquents")

    if not os.path.exists(Fichier_TXT):
        print(f" Erreur : Le fichier d'entrée gSpan ({Fichier_TXT}) est introuvable.")
        print(" Il faut d'abord exécuter l'étape 10.")
        return

    # Calcul dynamique du nombre total de graphes
    total_graphes = 0
    with open(Fichier_TXT, 'r', encoding='utf-8') as f:
        for ligne in f:
            if ligne.startswith("t #"):
                total_graphes += 1
                
    if total_graphes == 0:
        print(" Erreur : Aucun graphe trouvé dans le fichier texte.")
        return

    # Calcul du support minimum en valeur absolue basé sur le ratio
    min_support_calc = max(1, int(total_graphes * support_ratio))
    
    print("-" * 60)
    print(f" Nombre de document  (graphe): {total_graphes} ")
    print(f" Configuration  : Support min = {support_ratio*100}% (soit {min_support_calc} graphes minimum).")
    print(f" Paramètres     : Taille des motifs de {min_sommets}")
    

    # Configuration et exécution de gSpan
    gs = gSpan(
        database_file_name=Fichier_TXT,
        min_support=min_support_calc,
        min_num_vertices=min_sommets,
        max_num_vertices=max_sommets,
        is_undirected=False,  # Notre graphe est orienté !
        verbose=True,
        visualize=False,      # False : pour ne pas bloquer le pipeline 
        where=True            # True : pour garder en mémoire l'ID des graphes où le motif apparaît
    )

    
    
    # On capture tout ce que gSpan veut écrire dans la console et on le met dans le TXT
    original_stdout = sys.stdout
    with open(Fichier_Resultats, 'w', encoding='utf-8') as f_out:
        sys.stdout = f_out
        gs.run()
    sys.stdout = original_stdout
    
    
    
    with open(Fichier_Resultats, 'r', encoding='utf-8') as f_in:
        lignes = f_in.readlines()

    motifs_valides = []
    motif_courant = []
    compte_sommets = 0
    motifs_total_avant = 0
    motifs_total_apres = 0

    for ligne in lignes:
        if ligne.startswith("t #"):
            # Enregistrement du motif précédent s'il est valide
            if motif_courant and compte_sommets >= min_sommets:
                motifs_valides.extend(motif_courant)
                motifs_total_apres += 1
            if motif_courant:
                motifs_total_avant += 1
            # Initialisation du nouveau motif
            motif_courant = [ligne]
            compte_sommets = 0
        else:
            motif_courant.append(ligne)
            if ligne.startswith("v "):
                compte_sommets += 1

    # Prise en compte du tout dernier motif du fichier
    if motif_courant:
        motifs_total_avant += 1
        if compte_sommets >= min_sommets:
            motifs_valides.extend(motif_courant)
            motifs_total_apres += 1

    # Réécriture du fichier de résultats 
    with open(Fichier_Resultats, 'w', encoding='utf-8') as f_out:
        f_out.writelines(motifs_valides)
        
    print(f" Nettoyage terminé :  {motifs_total_apres} .")
    print(f" Les résultats sont sauvegardés dans : {Fichier_Resultats}")
    
    # Affichage des statistiques de temps
    print("\n Statistiques d'exécution :")
    gs.time_stats()

if __name__ == "__main__":
    lancer_fouille_gspan(support_ratio=0.15, min_sommets=3)