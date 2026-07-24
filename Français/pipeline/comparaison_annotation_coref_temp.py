import os
import pandas as pd
import re

# Définition des chemins
# *******************************************************************************************
Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Dossier_CSV = os.path.join(Base_dir, "data", "sortie_csv")

Fichier_temporel = os.path.join(Dossier_CSV, "annotation_corpus.csv")
Fichier_coref = os.path.join(Dossier_CSV, "resultats_mentions_fr.csv") 

# Fonction de correspondance STRICTE 
# ******************************************************************************************
def verifier_concordance_lexicale(xml_text, tete_lexicale):
    x = str(xml_text).lower().strip()
    tt = str(tete_lexicale).lower().strip()

    # Correspondance 
    # 
    if x == tt:
        return True
        
     

    # L'utilisation de \b garantit qu'on ne cherche que le mot exact 
    
    if re.search(rf'\b{re.escape(tt)}\b', x):
        return True

    return False

# Fonction Principale
# ****************************************************************************
def comparer():
    print(" Étape 7 : Croisement strict (Tête Lexicale vs Annotations XML)...")

    if not os.path.exists(Fichier_temporel) or not os.path.exists(Fichier_coref):
        print(" Erreur : L'un des fichiers CSV est introuvable.")
        return
    
    # Extraction XML 
    # ***********************************************************************************
    df_temp = pd.read_csv(Fichier_temporel)
    
    xml_uniques = df_temp[['doc', 'entite_id', 'entite_texte', 'entite_type']].rename(
        columns={'entite_id': 'xml_id', 'entite_texte': 'entité', 'entite_type': 'type_temporalite'}
    )
    
    xml_uniques = xml_uniques[xml_uniques['entité'] != 'Indéterminé']
    xml_uniques = xml_uniques.dropna(subset=['entité'])
    xml_uniques = xml_uniques.drop_duplicates(subset=['doc', 'xml_id'])
    xml_uniques['entité'] = xml_uniques['entité'].astype(str).str.strip()

    # Extraction CorPipe 
    # ******************************************************************************
    df_coref = pd.read_csv(Fichier_coref).dropna(subset=['mention_id'])
    
    tailles_chaines = df_coref.groupby(['doc', 'mention_id']).size().reset_index(name='longueur_chaine')
    textes_chaines = df_coref.groupby(['doc', 'mention_id'])['tete_lexicale'].apply(lambda x: ' | '.join(x.astype(str))).reset_index(name='chaine_complete')
    chaines_info = pd.merge(tailles_chaines, textes_chaines, on=['doc', 'mention_id'])

    coref_uniques = df_coref[['doc', 'mention_id', 'texte_maillon', 'tete_lexicale']].drop_duplicates()
    coref_uniques = pd.merge(coref_uniques, chaines_info, on=['doc', 'mention_id'], how='left')

    # Croisement 
    # *************************************************************************************
    matched_xml_ids = set()
    matched_coref_ids = set()
    lignes_finales = []

    documents = set(xml_uniques['doc']).union(set(coref_uniques['doc']))

    for doc in documents:
        xml_doc = xml_uniques[xml_uniques['doc'] == doc]
        coref_doc = coref_uniques[coref_uniques['doc'] == doc]

        for _, x_row in xml_doc.iterrows():
            xml_text = str(x_row['entité'])
            xml_type = x_row['type_temporalite']
            xml_id = str(x_row['xml_id'])
            x_uid = f"{doc}_{xml_id}" 

            for _, c_row in coref_doc.iterrows():
                tm = str(c_row['texte_maillon'])
                tt = str(c_row['tete_lexicale'])
                m_id = str(c_row['mention_id'])
                c_uid = f"{doc}_{m_id}_{tm}"

                # L'appel se fait uniquement sur la tête lexicale
                if verifier_concordance_lexicale(xml_text, tt):
                    lignes_finales.append({
                        'doc': doc,
                        'xml_id': xml_id, 
                        'entité': xml_text, 
                        'type_temporalite': xml_type,
                        'coref': 'Détecté',
                        'mention_id': m_id,
                        'longueur_chaine': c_row['longueur_chaine'],
                        'chaine_complete': c_row['chaine_complete']
                    })
                    matched_xml_ids.add(x_uid)
                    matched_coref_ids.add(c_uid)

    # Ajout des XML orphelins
    for _, x_row in xml_uniques.iterrows():
        x_uid = f"{x_row['doc']}_{str(x_row['xml_id'])}"
        if x_uid not in matched_xml_ids:
            lignes_finales.append({
                'doc': x_row['doc'], 
                'xml_id': x_row['xml_id'],
                'entité': x_row['entité'], 
                'type_temporalite': x_row['type_temporalite'],
                'coref': 'Non détecté', 
                'mention_id': 'Non applicable', 
                'longueur_chaine': 0, 
                'chaine_complete': 'Non applicable'
            })

    # Ajout des Coref orphelins
    for _, c_row in coref_uniques.iterrows():
        c_uid = f"{c_row['doc']}_{c_row['mention_id']}_{c_row['texte_maillon']}"
        if c_uid not in matched_coref_ids:
            lignes_finales.append({
                'doc': c_row['doc'], 
                'xml_id': 'Non applicable',
                'entité': c_row['texte_maillon'], 
                'type_temporalite': 'Non annoté',
                'coref': 'Détecté', 
                'mention_id': c_row['mention_id'], 
                'longueur_chaine': c_row['longueur_chaine'], 
                'chaine_complete': c_row['chaine_complete']
            })

    # Formatage  et Export
    # *******************************************************************************
    matrice_finale = pd.DataFrame(lignes_finales)
    
    matrice_finale['longueur_chaine'] = matrice_finale['longueur_chaine'].apply(
        lambda x: str(int(x)) if isinstance(x, (int, float)) and pd.notna(x) and x > 0 else "Non applicable"
    )

    colonnes_ordonnees = ['doc', 'xml_id', 'entité', 'type_temporalite', 'coref', 'mention_id', 'longueur_chaine', 'chaine_complete']
    matrice_finale = matrice_finale[colonnes_ordonnees].drop_duplicates()
    matrice_finale = matrice_finale.sort_values(by=['doc', 'mention_id', 'entité'])

    chemin_sortie = os.path.join(Dossier_CSV, "comparaison_coref_temp.csv")
    matrice_finale.to_csv(chemin_sortie, index=False, encoding='utf-8')

    print(f" Fichier généré : {len(matrice_finale)} ")

if __name__ == "__main__":
    comparer()