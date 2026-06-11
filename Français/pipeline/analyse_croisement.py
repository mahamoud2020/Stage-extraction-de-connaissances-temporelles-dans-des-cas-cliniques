import os
import pandas as pd


# Configuration des chemins

Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Dossier_CSV = os.path.join(Base_dir, "data", "sortie_csv")

Fichier_temporel = os.path.join(Dossier_CSV, "relations_temporelles_evenements.csv")
Fichier_coref = os.path.join(Dossier_CSV, "resultats_mentions_fr.csv") 

def comparer_coref_temp():
    print("Chargement et préparation des données")

    if not os.path.exists(Fichier_temporel) or not os.path.exists(Fichier_coref):
        print("Erreur : L'un des fichiers CSV est introuvable dans data/sortie_csv/")
        return
    
    
    # Extraction des temporalités (EVENT / TIMEX3)
    
    df_temp = pd.read_csv(Fichier_temporel)
    
    # On sépare les sources et les cibles pour capturer toutes les entités
    sources = df_temp[['doc', 'source_texte', 'source_type']].rename(
        columns={'source_texte': 'texte_match', 'source_type': 'type_temporel'}
    )
    cibles = df_temp[['doc', 'cible_texte', 'cible_type']].rename(
        columns={'cible_texte': 'texte_match', 'cible_type': 'type_temporel'}
    )
    
    # Fusion des sources/cibles et suppression des doublons par [doc, texte]
    temp_uniques = pd.concat([sources, cibles]).dropna(subset=['texte_match'])
    temp_uniques['texte_match'] = temp_uniques['texte_match'].astype(str).str.strip()
    
    # On garde la première catégorie (EVENT/TIMEX3) rencontrée pour chaque mot unique d'un doc
    temp_uniques = temp_uniques.drop_duplicates(subset=['doc', 'texte_match'])

    
    # Extraction des coréférences (Mention_ID)
    
    df_coref = pd.read_csv(Fichier_coref)
    
    # On cible la tête lexicale comme clé de correspondance 
    coref_uniques = df_coref[['doc', 'tete_lexicale', 'mention_id']].rename(
        columns={'tete_lexicale': 'texte_match'}
    )
    coref_uniques['texte_match'] = coref_uniques['texte_match'].astype(str).str.strip()
    
    # On regroupe les IDs (ex: "c3, c5") 
    coref_grouped = coref_uniques.groupby(['doc', 'texte_match'])['mention_id'].apply(
        lambda x: ', '.join(x.dropna().astype(str).unique())
    ).reset_index()

    
    # Croisement
    
    print("Fusion et alignement des couches d'annotation")
    matrice_finale = pd.merge(temp_uniques, coref_grouped, on=['doc', 'texte_match'], how='outer')
    
    # On remplace le vide par des étiquettes sémantiques explicites
    matrice_finale['type_temporel'] = matrice_finale['type_temporel'].fillna("Non annoté")
    matrice_finale['mention_id'] = matrice_finale['mention_id'].fillna("Non détecté")

    
    matrice_finale = matrice_finale.rename(columns={'texte_match': 'entité'})

    # Réorganisation des colonnes 
    colonnes_ordonnees = ['doc', 'entité', 'type_temporel', 'mention_id']
    matrice_finale = matrice_finale[colonnes_ordonnees]
    
    
    # Export
    
    chemin_sortie = os.path.join(Dossier_CSV, "comparaison_coref_temp.csv")
    matrice_finale.to_csv(chemin_sortie, index=False, encoding='utf-8')

    print("\n" + "*"*60)
    print("Fichier de comparaison généré")
    print("*"*60)
    print(f"Fichier enregistré : {chemin_sortie}")
    print(f" Nombre total de lignes uniques générées : {len(matrice_finale)}")
    print("*" * 60)
    print(" Aperçu des premières lignes du fichier :")
    print(matrice_finale.head(10).to_string(index=False))
    print("*"*60 + "\n")

if __name__ == "__main__":
    comparer_coref_temp()