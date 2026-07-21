import os
import glob
import pandas as pd
import xml.etree.ElementTree as ET

Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Dossier_XML = os.path.join(Base_dir, "data", "xml_source")
Dossier_CSV = os.path.join(Base_dir, "data", "sortie_csv")

def extraire_pour_gspan():
    print(" Lancement de l'extraction des balises concernés et des relations pour la fouille de graphe pattern (gSpan)")
    
    if not os.path.exists(Dossier_CSV):
        os.makedirs(Dossier_CSV)
        
    fichiers_xml = glob.glob(os.path.join(Dossier_XML, "*.xml")) + glob.glob(os.path.join(Dossier_XML, "*.xmi"))
    lignes_aretes = [] 
    tags_cibles = ['EVENT', 'TIMEX3', 'BODYPART', 'CLINENTITY']

    for fichier in fichiers_xml:
        nom_doc = os.path.basename(fichier).replace('.xml', '').replace('.xmi', '')
        
        try:
            tree = ET.parse(fichier)
            root = tree.getroot()
        except ET.ParseError:
            continue

        texte_complet = ""
        for elem in root:
            if elem.tag.endswith('Sofa'):
                texte_complet = elem.attrib.get('sofaString', '')
                break
                
        entites_brutes = []
        liens_objets = {}
        
        for elem in root:
            tag_name = elem.tag.split('}')[-1] 
            attribs = elem.attrib
            
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
            
            elif 'begin' in attribs and 'end' in attribs and tag_name in tags_cibles:
                entite_id = None
                for key, val in attribs.items():
                    if key.endswith('id'):
                        entite_id = val
                        break
                
                if not entite_id: continue
                
                begin = int(attribs['begin'])
                end = int(attribs['end'])
                texte_entite = texte_complet[begin:end].strip()
                if not texte_entite: continue 
                
                entites_brutes.append({
                    'id': entite_id,
                    'begin': begin,
                    'end': end,
                    'type_brut': tag_name,
                    'texte': texte_entite,
                    'attribs': attribs
                })

        entites_groupees = {}
        for ent in entites_brutes:
            pos = (ent['begin'], ent['end'])
            if pos not in entites_groupees:
                entites_groupees[pos] = []
            entites_groupees[pos].append(ent)
            
        entites_enrichies = {} 
        ancien_id_vers_nouveau = {} 
        
        for pos, liste_entites in entites_groupees.items():
            types = list(set([e['type_brut'] for e in liste_entites]))
            if 'EVENT' in types:
                types.remove('EVENT')
                types.insert(0, 'EVENT')
            
            merged_type = '/'.join(types)
            merged_id = '/'.join([e['id'] for e in liste_entites])
            
            docTimeRel = "Non concerné"
            eventType = "Non concerné"
            contextualModality = "Non concerné" 
            polarity = "Non concerné" 
            timexType = "Non concerné"
            
            merged_attribs = {}
            for e in liste_entites:
                for k, v in e['attribs'].items():
                    merged_attribs[k] = str(v)
                    
                if e['type_brut'] == 'EVENT':
                    docTimeRel = e['attribs'].get('docTimeRel', 'Non concerné')
                    eventType = e['attribs'].get('eventType', 'Non concerné')
                    # Ajout de contextualModality 
                    contextualModality = e['attribs'].get('contextualModality', 'ACTUAL')
                    polarity = e['attribs'].get('polarity', 'Non concerné')
                
                elif e['type_brut'] == 'TIMEX3':
                    timexType = e['attribs'].get('timex3Class', 'Non concerné')
                    
            for e in liste_entites:
                ancien_id_vers_nouveau[e['id']] = merged_id
                
            entites_enrichies[merged_id] = {
                'tag': merged_type,
                'texte': liste_entites[0]['texte'],
                'docTimeRel': docTimeRel,
                'eventType': eventType,
                'contextualModality': contextualModality, 
                'polarity': polarity,
                'timexType': timexType,
                'attributs_bruts': merged_attribs
            }

        for source_id, source_data in entites_enrichies.items():
            for attr_nom, attr_valeur in source_data['attributs_bruts'].items():
                liste_ids_potentiels = str(attr_valeur).split()
                
                for potentiel_link_id in liste_ids_potentiels:
                    if potentiel_link_id in liens_objets:
                        lien = liens_objets[potentiel_link_id]
                        target_ancien_id = lien['target']
                        target_id = ancien_id_vers_nouveau.get(target_ancien_id)
                        
                        if target_id and target_id in entites_enrichies:
                            cible_data = entites_enrichies[target_id]
                            
                            lignes_aretes.append({
                                'doc_id': nom_doc,
                                'source_id': source_id,
                                'source_texte': source_data['texte'],
                                'source_tag': source_data['tag'],
                                'source_docTimeRel': source_data['docTimeRel'],
                                'source_eventType': source_data['eventType'],
                                'source_contextualModality': source_data['contextualModality'], 
                                'source_polarity': source_data['polarity'],
                                'source_timexType': source_data['timexType'],
                                'relation_type': lien['role'],
                                'target_id': target_id,
                                'target_texte': cible_data['texte'],
                                'target_tag': cible_data['tag'],
                                'target_docTimeRel': cible_data['docTimeRel'],
                                'target_eventType': cible_data['eventType'],
                                'target_contextualModality': cible_data['contextualModality'], 
                                'target_polarity': cible_data['polarity'],
                                'target_timexType': cible_data['timexType']
                            })

    if lignes_aretes:
        df_graphe = pd.DataFrame(lignes_aretes)
        df_graphe = df_graphe.drop_duplicates() 
        
        chemin_sortie = os.path.join(Dossier_CSV, "balises_relations_attributs.csv")
        df_graphe.to_csv(chemin_sortie, index=False, encoding='utf-8')
        print(f" Nombre de {len(df_graphe)} relations extraites.")
    else:
        print(" Aucune balise n'a pu être extraite.")

if __name__ == "__main__":
    extraire_pour_gspan()