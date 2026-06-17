import os
import glob
import pandas as pd
import xml.etree.ElementTree as ET


# Définition des chemins

Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Dossier_XML = os.path.join(Base_dir, "data", "xml_source")
Dossier_CSV = os.path.join(Base_dir, "data", "sortie_csv")

def extraire_relations():
    print(" Étape 6 : Extraction exhaustive de toutes les balises")
    
    if not os.path.exists(Dossier_CSV):
        os.makedirs(Dossier_CSV)
        
    fichiers_xml = glob.glob(os.path.join(Dossier_XML, "*.xml")) + glob.glob(os.path.join(Dossier_XML, "*.xmi"))
    toutes_les_relations = []

    # Liste des balises  à ignorer 
    tags_a_exclure = ['Token', 'Sentence', 'DocumentMetaData', 'METADATA', 'TagsetDescription']

    for fichier in fichiers_xml:
        nom_doc = os.path.basename(fichier).replace('.xml', '').replace('.xmi', '')
        
        try:
            tree = ET.parse(fichier)
            root = tree.getroot()
        except ET.ParseError:
            continue

        # Extraction du texte complet
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
        
        entites = {} 
        liens_objets = {} 
        entites_avec_liens = set()
        
        # Enregistrement des éléments
        for elem in root:
            tag_name = elem.tag.split('}')[-1] 
            attribs = elem.attrib
            
            xmi_id = None
            for key, val in attribs.items():
                if key.endswith('id'):
                    xmi_id = val
                    break
            
            if not xmi_id:
                continue
                
            if 'target' in attribs and tag_name.endswith('Link'):
                liens_objets[xmi_id] = {
                    'role': attribs.get('role', 'LIEN_INCONNU'),
                    'target': attribs.get('target')
                }
            
            # 
            elif 'begin' in attribs and 'end' in attribs and tag_name not in tags_a_exclure:
                begin = int(attribs['begin'])
                end = int(attribs['end'])
                
                contexte = "Contexte introuvable"
                for p in phrases:
                    if begin >= p['begin'] and end <= p['end']:
                        contexte = p['texte'].strip().replace('\n', ' ')
                        break
                
                entites[xmi_id] = {
                    'type': tag_name,
                    'texte': texte_complet[begin:end],
                    'contexte': contexte,
                    'attributs_bruts': attribs
                }

        # 
        for source_id, source_data in entites.items():
            for attr_nom, attr_valeur in source_data['attributs_bruts'].items():
                liste_ids_potentiels = attr_valeur.split()
                
                for potentiel_link_id in liste_ids_potentiels:
                    if potentiel_link_id in liens_objets:
                        lien = liens_objets[potentiel_link_id]
                        target_id = lien['target']
                        
                        if target_id in entites:
                            cible_data = entites[target_id]
                            
                            toutes_les_relations.append({
                                'doc': nom_doc,
                                'entite_source': source_data['texte'],
                                'source_type': source_data['type'],
                                'relation': lien['role'],
                                'entite_cible': cible_data['texte'],
                                'cible_type': cible_data['type'],
                                'texte_contexte': source_data['contexte']
                            })
                            entites_avec_liens.add(source_id)
                            entites_avec_liens.add(target_id)

        # Ajout des entités orphelines (Non annotées)
        for entite_id, entite_data in entites.items():
            if entite_id not in entites_avec_liens:
                toutes_les_relations.append({
                    'doc': nom_doc,
                    'entite_source': entite_data['texte'],
                    'source_type': entite_data['type'],
                    'relation': 'Non annoté',
                    'entite_cible': 'Indéterminé',
                    'cible_type': 'Aucun',
                    'texte_contexte': entite_data['contexte']
                })

    # Export
    if toutes_les_relations:
        df = pd.DataFrame(toutes_les_relations)
        chemin_sortie = os.path.join(Dossier_CSV, "relations_temporelles_evenements.csv")
        df.to_csv(chemin_sortie, index=False, encoding='utf-8')
        print(f"{len(df)} lignes médicales exportées dans le CSV.")

if __name__ == "__main__":
    extraire_relations()