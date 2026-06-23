import os
import glob
import pandas as pd
import xml.etree.ElementTree as ET


# Définition des chemins
# ********************************************************************************

Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Dossier_XML = os.path.join(Base_dir, "data", "xml_source")
Dossier_CSV = os.path.join(Base_dir, "data", "sortie_csv")

def extraire_relations_et_entites():
    print(" Étape 7 : Extraction des relations et entités avec IDs")
    
    if not os.path.exists(Dossier_CSV):
        os.makedirs(Dossier_CSV)
        
    fichiers_xml = glob.glob(os.path.join(Dossier_XML, "*.xml")) + glob.glob(os.path.join(Dossier_XML, "*.xmi"))
    toutes_les_lignes_csv = []

    # Liste des balises pertinentes
    tags_cibles = ['EVENT', 'RML', 'BODYPART', 'CLINENTITY', 'ACTOR', 'TIMEX3']

    for fichier in fichiers_xml:
        nom_doc = os.path.basename(fichier).replace('.xml', '').replace('.xmi', '')
        
        try:
            tree = ET.parse(fichier)
            root = tree.getroot()
        except ET.ParseError:
            continue

        #  Extraction du texte complet 
        texte_complet = ""
        for elem in root:
            if elem.tag.endswith('Sofa'):
                texte_complet = elem.attrib.get('sofaString', '')
                break
                
        # Extraction des phrases pour le contexte
        phrases = []
        for elem in root:
            if elem.tag.endswith('Sentence'):
                if 'begin' in elem.attrib and 'end' in elem.attrib:
                    begin_phrase = int(elem.attrib['begin'])
                    end_phrase = int(elem.attrib['end'])
                    phrases.append({
                        'begin': begin_phrase,
                        'end': end_phrase,
                        'texte': texte_complet[begin_phrase:end_phrase]
                    })
        
        entites = {} # Dictionnaire pour stocker les entités valides (avec ID)
        liens_objets = {} # Dictionnaire pour stocker les TLINKs
        entites_avec_liens = set() # Pour marquer celles qui ont des relations
        
        # Premier passage : enregistrement des Entités et des Liens
        for elem in root:
            tag_name = elem.tag.split('}')[-1] 
            attribs = elem.attrib
            
            # Traitement des Liens (TLINK) 
            if 'target' in attribs and tag_name.endswith('Link'):
                xmi_id_lien = None
                for key, val in attribs.items():
                    if key.endswith('id'):
                        xmi_id_lien = val
                        break
                if xmi_id_lien:
                    liens_objets[xmi_id_lien] = {
                        'role': attribs.get('role', 'LIEN_INCONNU'),
                        'target': attribs.get('target')
                    }
            
            # Traitement des Entités 
            elif 'begin' in attribs and 'end' in attribs and tag_name in tags_cibles:
                # Récupération de l'ID
                entite_id = None
                for key, val in attribs.items():
                    if key.endswith('id'):
                        entite_id = val
                        break
                
                # Si l'entité n'a pas d'ID, on l'ignore 
                if not entite_id:
                    continue

                begin = int(attribs['begin'])
                end = int(attribs['end'])
                
                # Récupération du texte
                texte_entite = texte_complet[begin:end].strip()
                if not texte_entite:
                    continue 
                
                # Détermination du contexte
                contexte = "Contexte introuvable"
                for p in phrases:
                    if begin >= p['begin'] and end <= p['end']:
                        contexte = p['texte'].strip().replace('\n', ' ')
                        break
                
                entites[entite_id] = {
                    'type': tag_name,
                    'texte': texte_entite,
                    'contexte': contexte,
                    'attributs_bruts': attribs
                }

        # Construction des paires (Relations)
        for source_id, source_data in entites.items():
            for attr_nom, attr_valeur in source_data['attributs_bruts'].items():
                liste_ids_potentiels = str(attr_valeur).split()
                
                for potentiel_link_id in liste_ids_potentiels:
                    if potentiel_link_id in liens_objets:
                        lien = liens_objets[potentiel_link_id]
                        target_id = lien['target']
                        
                        if target_id in entites:
                            cible_data = entites[target_id]
                            
                            toutes_les_lignes_csv.append({
                                'doc': nom_doc,
                                'source_id': source_id,            # pour les  ID
                                'entite_source': source_data['texte'],
                                'source_type': source_data['type'],
                                'relation': lien['role'],
                                'cible_id': target_id,             # pour les ID
                                'entite_cible': cible_data['texte'],
                                'cible_type': cible_data['type'],
                                'texte_contexte': source_data['contexte']
                            })
                            entites_avec_liens.add(source_id)
                            entites_avec_liens.add(target_id)

        #  Ajout des entités orphelines (Aucune relation)
        for entite_id, entite_data in entites.items():
            if entite_id not in entites_avec_liens:
                toutes_les_lignes_csv.append({
                    'doc': nom_doc,
                    'source_id': entite_id,                # nouvelle colonne pour les ID
                    'entite_source': entite_data['texte'],
                    'source_type': entite_data['type'],
                    'relation': 'Aucune relation', 
                    'cible_id': 'Aucun',                   # nouvelles colonnes pour les ID
                    'entite_cible': 'Indéterminé',
                    'cible_type': 'Aucun',
                    'texte_contexte': entite_data['contexte']
                })

    
    # Export du fichier CSV
    # *****************************************************************

    if toutes_les_lignes_csv:
        df = pd.DataFrame(toutes_les_lignes_csv)
        
        # Réorganisation des colonnes pour une lecture logique
        colonnes_ordonnees = [
            'doc', 'source_id', 'entite_source', 'source_type', 
            'relation', 'cible_id', 'entite_cible', 'cible_type', 'texte_contexte'
        ]
        df = df[colonnes_ordonnees]
        
        # Suppression des doublons
        df = df.drop_duplicates() 
        
        chemin_sortie = os.path.join(Dossier_CSV, "annotation_corpus.csv")
        df.to_csv(chemin_sortie, index=False, encoding='utf-8')
        print(f"{len(df)} lignes exportées dans le CSV : {chemin_sortie}")
    else:
        print("Aucune donnée extraite.")

if __name__ == "__main__":
    extraire_relations_et_entites()