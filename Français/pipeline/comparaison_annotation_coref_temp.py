import os
import pandas as pd
import re


# Définition des chemins
# *******************************************************************************************

Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Dossier_CSV = os.path.join(Base_dir, "data", "sortie_csv")

# Nouveaux pointages 
Fichier_temporel = os.path.join(Dossier_CSV, "annotation_corpus.csv")
Fichier_coref = os.path.join(Dossier_CSV, "resultats_mentions_fr.csv") 


# Fonction de correspondance de texte
# ******************************************************************************************

def verifier_concordance_lexicale(xml_text, texte_maillon, tete_lexicale):
    x = str(xml_text).lower().strip()
    tm = str(texte_maillon).lower().strip()
    tt = str(tete_lexicale).lower().strip()

    # Correspondance tête ou mention complète
    if x == tm or x == tt:
        return True
        
    # Correspondance par mots entiers (Protection robuste contre les inclusions abusives)
    # \b garantit qu'on extrait le mot exact et non des syllabes
    mots_x = set(re.findall(r'\b\w+\b', x))
    mots_tm = set(re.findall(r'\b\w+\b', tm))
    mots_tt = set(re.findall(r'\b\w+\b', tt))
    
    # Vérification d'inclusion propre (Si les mots de l'un sont strictement inclus dans l'autre)
    if mots_x and (mots_x.issubset(mots_tm) or mots_x.issubset(mots_tt)):
        return True
    if mots_tm and mots_tm.issubset(mots_x):
        return True
    if mots_tt and mots_tt.issubset(mots_x):
        return True

    return False


# Fonction Principale
# ****************************************************************************

def comparer():
    print(" Étape 8 : Croisement mentions vs annotations")

    if not os.path.exists(Fichier_temporel) or not os.path.exists(Fichier_coref):
        print(" Erreur : L'un des fichiers CSV est introuvable.")
        return
    
    
    # Extraction XML 
    # ***********************************************************************************


    df_temp = pd.read_csv(Fichier_temporel)
    
    # On récupère les sources avec leur ID
    sources = df_temp[['doc', 'source_id', 'entite_source', 'source_type']].rename(
        columns={'source_id': 'xml_id', 'entite_source': 'entité', 'source_type': 'type_temporalite'})
    
    # On récupère les cibles avec leur ID
    cibles = df_temp[['doc', 'cible_id', 'entite_cible', 'cible_type']].rename(
        columns={'cible_id': 'xml_id', 'entite_cible': 'entité', 'cible_type': 'type_temporalite'})
    
    # On exclut les cibles vides générées par les entités orphelines
    cibles = cibles[(cibles['entité'] != 'Indéterminé') & (cibles['xml_id'] != 'Aucun')]
    
    # On rassemble tout
    # On dédoublonne uniquement sur l'ID de la balise pour ne pas traiter 
    # la même balise plusieurs fois mais on garde les mots identiques s'ils ont des ID différents.
    xml_uniques = pd.concat([sources, cibles]).dropna(subset=['entité'])
    xml_uniques = xml_uniques.drop_duplicates(subset=['doc', 'xml_id'])
    xml_uniques['entité'] = xml_uniques['entité'].astype(str).str.strip()

    
    # 2. Extraction CorPipe 
    # ******************************************************************************

    df_coref = pd.read_csv(Fichier_coref).dropna(subset=['mention_id'])
    
    tailles_chaines = df_coref.groupby(['doc', 'mention_id']).size().reset_index(name='longueur_chaine')
    textes_chaines = df_coref.groupby(['doc', 'mention_id'])['tete_lexicale'].apply(lambda x: ', '.join(x.astype(str))).reset_index(name='chaine_complete')
    chaines_info = pd.merge(tailles_chaines, textes_chaines, on=['doc', 'mention_id'])

    coref_uniques = df_coref[['doc', 'mention_id', 'texte_maillon', 'tete_lexicale']].drop_duplicates()
    coref_uniques = pd.merge(coref_uniques, chaines_info, on=['doc', 'mention_id'], how='left')

    
    #  Croisement 
    # ********************************************************************************


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
            x_uid = f"{doc}_{xml_id}" # Utilisation de l'ID pour un suivi 

            for _, c_row in coref_doc.iterrows():
                tm = str(c_row['texte_maillon'])
                tt = str(c_row['tete_lexicale'])
                m_id = str(c_row['mention_id'])
                c_uid = f"{doc}_{m_id}_{tm}"

                if verifier_concordance_lexicale(xml_text, tm, tt):
                    lignes_finales.append({
                        'doc': doc,
                        'xml_id': xml_id,  # Ajout de l'ID pour traçabilité
                        'entité': xml_text, 
                        'type_temporalite': xml_type,
                        'coref': 'Détecté',
                        'mention_id': m_id,
                        'longueur_chaine': c_row['longueur_chaine'],
                        'chaine_complete': c_row['chaine_complete']
                    })
                    matched_xml_ids.add(x_uid)
                    matched_coref_ids.add(c_uid)

    # Ajout des  XML uniquement
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

    # Ajout des Coref uniquement
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

    
    # Formatage final et Export
    # *******************************************************************************

    matrice_finale = pd.DataFrame(lignes_finales)
    
    matrice_finale['longueur_chaine'] = matrice_finale['longueur_chaine'].apply(
        lambda x: str(int(x)) if isinstance(x, (int, float)) and pd.notna(x) and x > 0 else "Non applicable"
    )

    # Réorganisation
    colonnes_ordonnees = ['doc', 'xml_id', 'entité', 'type_temporalite', 'coref', 'mention_id', 'longueur_chaine', 'chaine_complete']
    matrice_finale = matrice_finale[colonnes_ordonnees].drop_duplicates()
    matrice_finale = matrice_finale.sort_values(by=['doc', 'mention_id', 'entité'])

    chemin_sortie = os.path.join(Dossier_CSV, "comparaison_coref_temp.csv")
    matrice_finale.to_csv(chemin_sortie, index=False, encoding='utf-8')

    print(f"Fichier généré : {len(matrice_finale)} annotations uniques croisées.")

if __name__ == "__main__":
    comparer()