import os
import glob
import pandas as pd
import xml.etree.ElementTree as ET
import argparse

# Définition des chemins
Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Pointera sur .../Français
Parent_dir = os.path.dirname(Base_dir) # Remonte au dossier .../coref_e3c_corpipe_
Dossier_XML = os.path.join(Base_dir, "data", "xml_source") 

def extraire_pour_gspan(version_active):
    print(f" Lancement de l'extraction des balises et relations (Version : {version_active.upper()})")
    
    # Détermination du dossier de sortie en fonction de la version
    if version_active == 'complet':
        dossier_sortie = os.path.join(Parent_dir, "Graphe pattern  mining", "resultats_avec_tous_les_attributs")
    elif version_active == 'sans_dct':
        dossier_sortie = os.path.join(Parent_dir, "Graphe pattern  mining", "resultats_sans_attribut_doctimrel")
    elif version_active == 'sans_polarity':
        dossier_sortie = os.path.join(Parent_dir, "Graphe pattern  mining", "resultats_sans_attribut_polarity")
    elif version_active == 'sans_eventtype':
        dossier_sortie = os.path.join(Parent_dir, "Graphe pattern  mining", "resultats_sans_attribut_eventype")
    elif version_active == 'fusion':
        dossier_sortie = os.path.join(Parent_dir, "Graphe pattern  mining", "resultats_fusion_event_clinentity")
    elif version_active == 'coref':
        # La coréférence utilise sa propre extraction plus tard, mais on prépare le dossier au cas où
        dossier_sortie = os.path.join(Parent_dir, "Graphe pattern  mining", "avec_coref")
    else:
        dossier_sortie = os.path.join(Parent_dir, "Graphe pattern  mining", "resultats_avec_tous_les_attributs")

    if not os.path.exists(dossier_sortie):
        os.makedirs(dossier_sortie)
        
    fichiers_xml = glob.glob(os.path.join(Dossier_XML, "*.xml")) + glob.glob(os.path.join(Dossier_XML, "*.xmi"))
    lignes_aretes = [] 

    # Uniquement EVENT, CLINENTITY et TIMEX3
    tags_cibles = ['EVENT', 'TIMEX3', 'CLINENTITY']

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
            
            # Traitement des Liens (TLINKs)
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
                    
                # Le DCT est consideré comme un attribut, pas un sommet
                if e['type_brut'] == 'EVENT':
                    docTimeRel = e['attribs'].get('docTimeRel', 'Non concerné')
                    eventType = e['attribs'].get('eventType', 'Non concerné')
                    contextualModality = e['attribs'].get('contextualModality', 'Non concerné')
                    polarity = e['attribs'].get('polarity', 'Non concerné')
                
                elif e['type_brut'] == 'TIMEX3':
                    timexType = e['attribs'].get('type', e['attribs'].get('timex3Class', 'Non concerné'))
                    
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
        
        # Le nom du fichier de base (le CSV d'extraction brut ne change pas de nom, juste de dossier)
        # Exception pour la coréférence: elle lit depuis balises_relations_attributs.csv pour créer balises_relations_attributs_coref.csv
        # Pour les autres versions, on sauvegarde directement dans leur dossier.
        chemin_sortie = os.path.join(dossier_sortie, "balises_relations_attributs.csv")
        df_graphe.to_csv(chemin_sortie, index=False, encoding='utf-8')
        print(f" -> Succès : {len(df_graphe)} relations extraites.")
        print(f" -> Sauvegardé dans : {chemin_sortie}")
    else:
        print(" Aucune relation n'a pu être extraite.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', type=str, default='complet')
    args = parser.parse_args()
    
    extraire_pour_gspan(args.version)