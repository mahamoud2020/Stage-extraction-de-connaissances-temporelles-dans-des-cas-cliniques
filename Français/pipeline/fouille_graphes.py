import os
import sys
import pandas as pd
import argparse
from gspan_mining import gSpan

# Patch Pandas 2.0 pour la bibliothèque gspan_mining 
def df_append_patch(self, other, ignore_index=False, **kwargs):
    if isinstance(other, dict):
        other = pd.DataFrame([other])
    return pd.concat([self, other], ignore_index=ignore_index)

pd.DataFrame.append = df_append_patch

# Définition des 
#***************************************************************************************************

Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Parent_dir = os.path.dirname(Base_dir) # On remonte dans l'arborescence
Dossier_Mining = os.path.join(Parent_dir, "Graphe pattern  mining")

def lancer_fouille_gspan(version_active, support_ratio=0.15, min_sommets=3, max_sommets=10000):
    print(f" Lancement de l'algorithme gSpan pour la fouille de sous-graphes fréquents (Version : {version_active.upper()})")

    # Détermination du dossier selon la version
    if version_active == 'complet':
        dossier_sortie = os.path.join(Dossier_Mining, "resultats_avec_tous_les_attributs")
    elif version_active == 'sans_dct':
        dossier_sortie = os.path.join(Dossier_Mining, "resultats_sans_attribut_doctimrel")
    elif version_active == 'sans_polarity':
        dossier_sortie = os.path.join(Dossier_Mining, "resultats_sans_attribut_polarity")
    elif version_active == 'sans_eventtype':
        dossier_sortie = os.path.join(Dossier_Mining, "resultats_sans_attribut_eventype")
    elif version_active == 'fusion':
        dossier_sortie = os.path.join(Dossier_Mining, "resultats_fusion_event_clinentity")
    elif version_active == 'coref':
        dossier_sortie = os.path.join(Dossier_Mining, "avec_coref")
    else:
        dossier_sortie = os.path.join(Dossier_Mining, "resultats_avec_tous_les_attributs")

    # Chemins standardisés pour l'entrée et la sortie à l'intérieur du dossier
    Fichier_TXT = os.path.join(dossier_sortie, "graphes_gspan.txt")
    Fichier_Resultats = os.path.join(dossier_sortie, "resultats_bruts_gspan.txt")

    if not os.path.exists(Fichier_TXT):
        print(f" Erreur : Le fichier d'entrée gSpan ({Fichier_TXT}) est introuvable.")
        print(" Il faut exécuter l'étape 10 pour cette version ?")
        return

    if not os.path.exists(dossier_sortie):
        os.makedirs(dossier_sortie)

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
    
    print("*" * 60)
    print(f" Corpus analysé : {total_graphes} documents (graphes).")
    print(f" Configuration  : Support min = {support_ratio*100}% (soit {min_support_calc} graphes minimum).")
    print(f" Paramètres     : Taille des motifs de {min_sommets} à l'infini.")
    print(f" Structure      : Graphes orientés selon les relations (TLINK).")
    print("*" * 60)

    # Configuration et exécution de gSpan
    gs = gSpan(
        database_file_name=Fichier_TXT,
        min_support=min_support_calc,
        min_num_vertices=min_sommets,
        max_num_vertices=max_sommets,
        is_undirected=False,  
        verbose=True,
        visualize=False,      
        where=True            # Garde en mémoire l'ID des documents contenant le motif
    )

    # Lancement de la recherche avec redirection de la console vers un fichier
    original_stdout = sys.stdout
    with open(Fichier_Resultats, 'w', encoding='utf-8') as f_out:
        sys.stdout = f_out
        gs.run()
    sys.stdout = original_stdout
    
    # Filtrage post-fouille pour garantir le minimum de sommets 
    print(f" Filtrage pour isoler les motifs d'au moins {min_sommets} sommets")
    with open(Fichier_Resultats, 'r', encoding='utf-8') as f_in:
        lignes = f_in.readlines()

    motifs_valides = []
    motif_courant = []
    compte_sommets = 0
    motifs_total_avant = 0
    motifs_total_apres = 0

    for ligne in lignes:
        if ligne.startswith("t #"):
            if motif_courant and compte_sommets >= min_sommets:
                motifs_valides.extend(motif_courant)
                motifs_total_apres += 1
            if motif_courant:
                motifs_total_avant += 1
            motif_courant = [ligne]
            compte_sommets = 0
        else:
            motif_courant.append(ligne)
            if ligne.startswith("v "):
                compte_sommets += 1

    if motif_courant:
        motifs_total_avant += 1
        if compte_sommets >= min_sommets:
            motifs_valides.extend(motif_courant)
            motifs_total_apres += 1

    # Réécriture du fichier de résultats complètement propre
    with open(Fichier_Resultats, 'w', encoding='utf-8') as f_out:
        f_out.writelines(motifs_valides)
        
    print(f" {motifs_total_avant} motifs trouvés initialement ,  {motifs_total_apres} vrais motifs conservés.")
    print(f" Les résultats sont sauvegardés dans : {Fichier_Resultats}")
    
    print("\n Statistiques d'exécution :")
    gs.time_stats()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', type=str, default='complet')
    args = parser.parse_args()
    
    lancer_fouille_gspan(args.version, support_ratio=0.15, min_sommets=3)