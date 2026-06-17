import os
import pandas as pd


# Définition des chemins


Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Dossier_CSV = os.path.join(Base_dir, "data", "sortie_csv")

Fichier_temporel = os.path.join(Dossier_CSV, "relations_temporelles_evenements.csv")
Fichier_coref = os.path.join(Dossier_CSV, "resultats_mentions_fr.csv") 

def comparer():
    print(" Étape 7 : Croisement coref vs temporalité ")

    if not os.path.exists(Fichier_temporel) or not os.path.exists(Fichier_coref):
        print("Erreur : L'un des fichiers CSV est introuvable.")
        return
    
    
    # Extraction des annotations 
    

    df_temp = pd.read_csv(Fichier_temporel)
    
    sources = df_temp[['doc', 'entite_source', 'source_type']].rename(
        columns={'entite_source': 'entité', 'source_type': 'type_temporalite'}
    )
    cibles = df_temp[['doc', 'entite_cible', 'cible_type']].rename(
        columns={'entite_cible': 'entité', 'cible_type': 'type_temporalite'}
    )
    cibles = cibles[cibles['entité'] != 'Indéterminé']
    
    xml_uniques = pd.concat([sources, cibles]).dropna(subset=['entité'])
    xml_uniques['entité'] = xml_uniques['entité'].astype(str).str.strip()
    xml_uniques = xml_uniques.drop_duplicates(subset=['doc', 'entité', 'type_temporalite'])

    
    # Extraction CorPipe & Création des Chaînes
    

    df_coref = pd.read_csv(Fichier_coref)
    
    # On isole les têtes lexicales 
    coref_base = df_coref[['doc', 'tete_lexicale', 'mention_id']].rename(
        columns={'tete_lexicale': 'entité'}
    ).dropna(subset=['mention_id'])
    coref_base['entité'] = coref_base['entité'].astype(str).str.strip()
    
    
    #  On calcule la longueur totale de la chaîne (nombre d'éléments pour un même ID)

    tailles_chaines = coref_base.groupby(['doc', 'mention_id']).size().reset_index(name='longueur_chaine')
    
    # On crée le texte de la chaîne (tous les mots qui la composent, même identiques)

    textes_chaines = coref_base.groupby(['doc', 'mention_id'])['entité'].apply(
        lambda x: ', '.join(x)
    ).reset_index(name='chaine_complete')
    
    # On fusionne la taille et le texte
    chaines_info = pd.merge(tailles_chaines, textes_chaines, on=['doc', 'mention_id'])

    # On rapatrie ces infos globales sur chaque entité individuelle

    coref_uniques = pd.merge(coref_base, chaines_info, on=['doc', 'mention_id'], how='left')
    
    # 1 ligne par combinaison Doc/Mot/ID

    coref_uniques = coref_uniques.drop_duplicates(subset=['doc', 'entité', 'mention_id'])
    coref_uniques['coref'] = 'Détecté'

    
    # Croisement 
    

    matrice_finale = pd.merge(xml_uniques, coref_uniques, on=['doc', 'entité'], how='outer')
    
    
    # Nettoyage et Formatage
    

    matrice_finale['type_temporalite'] = matrice_finale['type_temporalite'].fillna("Non annoté")
    matrice_finale['coref'] = matrice_finale['coref'].fillna("Non détecté")
    
    # Nettoyage des IDs vides ou NaN
    matrice_finale['mention_id'] = matrice_finale['mention_id'].fillna("Non applicable")
    matrice_finale.loc[matrice_finale['mention_id'] == '', 'mention_id'] = 'Non applicable'
    
    matrice_finale['chaine_complete'] = matrice_finale['chaine_complete'].fillna("Non applicable")
    matrice_finale['longueur_chaine'] = matrice_finale['longueur_chaine'].fillna("Non applicable")
    
    # Formatage propre de la longueur 
    matrice_finale['longueur_chaine'] = matrice_finale['longueur_chaine'].apply(
        lambda x: str(int(x)) if isinstance(x, (int, float)) and pd.notna(x) else str(x)
    )

    # Réorganisation des colonnes

    colonnes_ordonnees = [
        'doc', 'entité', 'type_temporalite', 'coref', 
        'mention_id', 'longueur_chaine', 'chaine_complete'
    ]
    matrice_finale = matrice_finale[colonnes_ordonnees]
    
    matrice_finale = matrice_finale.sort_values(by=['doc', 'mention_id', 'entité'])

    
    # Export
    

    chemin_sortie = os.path.join(Dossier_CSV, "comparaison_coref_temp.csv")
    matrice_finale.to_csv(chemin_sortie, index=False, encoding='utf-8')

    print(f" Fichier généré : {len(matrice_finale)} ")

if __name__ == "__main__":
    comparer()