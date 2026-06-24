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
    print(" Étape 6 : Extraction des balises et des relations")
    
    if not os.path.exists(Dossier_CSV):
        os.makedirs(Dossier_CSV)
        
    fichiers_xml = glob.glob(os.path.join(Dossier_XML, "*.xml")) + glob.glob(os.path.join(Dossier_XML, "*.xmi"))
    toutes_les_lignes_csv = []

    # Liste des balises à extraire
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
        
        entites_brutes = [] # Liste temporaire avant fusion
        liens_objets = {} # Dictionnaire pour stocker les TLINKs
        entites_avec_liens = set() # Pour marquer celles qui ont des relations
        
        # enregistrement des Entités brutes et des Liens
        for elem in root:
            tag_name = elem.tag.split('}')[-1] 
            attribs = elem.attrib
            
            # Traitement des relations (TLINK) 
            if 'target' in attribs and tag_name.endswith('Link'):
                xmi_id_lien = None
                for key, val in attribs.items():
                    if key.endswith('id'):
                        xmi_id_lien = val
                        break
                if xmi_id_lien:
                    liens_objets[xmi_id_lien] = {
                        'role': attribs.get('role', 'Lien_inconnu'),
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
                
                # Déterminer le contexte
                contexte = "Contexte introuvable"
                for p in phrases:
                    if begin >= p['begin'] and end <= p['end']:
                        contexte = p['texte'].strip().replace('\n', ' ')
                        break
                
                
                # Gestion de l'attribut "role" pour  ACTOR
                # ***********************************************************************************

                type_final = tag_name
                if tag_name == 'ACTOR' and 'role' in attribs:
                    type_final = f"ACTOR ({attribs['role']})"
                
                entites_brutes.append({
                    'id': entite_id,
                    'begin': begin,
                    'end': end,
                    'type': type_final, # On utilise le type enrichi
                    'texte': texte_entite,
                    'contexte': contexte,
                    'attribs': attribs
                })

        
        # Regroupement et Fusion des annotations superposées (ex: EVENT/CLINENTITY)
        # ********************************************************************************
        
        # Grouper par position exacte (begin, end)
        entites_groupees = {}
        for ent in entites_brutes:
            pos = (ent['begin'], ent['end'])
            if pos not in entites_groupees:
                entites_groupees[pos] = []
            entites_groupees[pos].append(ent)
            
        entites = {} # Dictionnaire final des entités fusionnées
        ancien_id_vers_nouveau = {} # Dictionnaire de traduction des IDs pour les relations
        
        # Fusionner
        for pos, liste_entites in entites_groupees.items():
            if len(liste_entites) == 1:
                # Annotation simple
                e = liste_entites[0]
                merged_id = e['id']
                merged_type = e['type']
                merged_attribs = e['attribs']
            else:
                # Double annotation superposée
                types = []
                for e in liste_entites:
                    if e['type'] not in types:
                        types.append(e['type'])
                
                # On place 'EVENT' en premier si présent pour la lisibilité
                if 'EVENT' in types:
                    types.remove('EVENT')
                    types.insert(0, 'EVENT')
                    
                merged_type = '/'.join(types) # Ex: EVENT/ACTOR (PATIENT)
                merged_id = '/'.join([e['id'] for e in liste_entites]) # les IDs de l'élement ayant une double annotation Ex: 5646/6696
                
                # Fusionner les attributs bruts pour ne perdre aucune relation
                merged_attribs = {}
                for e in liste_entites:
                    for k, v in e['attribs'].items():
                        if k in merged_attribs:
                            merged_attribs[k] += f" {v}"
                        else:
                            merged_attribs[k] = str(v)
                            
            # Enregistrer la traduction des IDs pour que les liens retrouvent leur cible
            for e in liste_entites:
                ancien_id_vers_nouveau[e['id']] = merged_id
                
            # Stocker l'entité finale
            entites[merged_id] = {
                'type': merged_type,
                'texte': liste_entites[0]['texte'],
                'contexte': liste_entites[0]['contexte'],
                'attributs_bruts': merged_attribs
            }

        # ********************************************************************************

        # Construction des paires (Relations centrées sur l'entité)
        for source_id, source_data in entites.items():
            for attr_nom, attr_valeur in source_data['attributs_bruts'].items():
                liste_ids_potentiels = str(attr_valeur).split()
                
                for potentiel_link_id in liste_ids_potentiels:
                    if potentiel_link_id in liens_objets:
                        lien = liens_objets[potentiel_link_id]
                        target_ancien_id = lien['target']
                        
                        # Traduire l'ancien ID cible vers le nouvel ID fusionné (s'il y a eu fusion)
                        target_id = ancien_id_vers_nouveau.get(target_ancien_id)
                        
                        if target_id and target_id in entites:
                            cible_data = entites[target_id]
                            
                            # Création de la ligne pour la relation sortante (l'entité est la source)
                            toutes_les_lignes_csv.append({
                                'doc': nom_doc,
                                'entite_id': source_id,
                                'entite_texte': source_data['texte'],
                                'entite_type': source_data['type'],
                                'sens_relation': 'Sortante',
                                'relation': lien['role'],
                                'entite_liee_id': target_id,
                                'entite_liee_texte': cible_data['texte'],
                                'entite_liee_type': cible_data['type'],
                                'texte_contexte': source_data['contexte']
                            })
                            
                            # 2. Création de la ligne pour la relation entrante (l'entité est la cible)
                            toutes_les_lignes_csv.append({
                                'doc': nom_doc,
                                'entite_id': target_id,
                                'entite_texte': cible_data['texte'],
                                'entite_type': cible_data['type'],
                                'sens_relation': 'Entrante',
                                'relation': lien['role'],
                                'entite_liee_id': source_id,
                                'entite_liee_texte': source_data['texte'],
                                'entite_liee_type': source_data['type'],
                                'texte_contexte': cible_data['contexte']
                            })
                            
                            entites_avec_liens.add(source_id)
                            entites_avec_liens.add(target_id)

        #  Ajout des entités orphelines (Aucune relation)
        for entite_id, entite_data in entites.items():
            if entite_id not in entites_avec_liens:
                toutes_les_lignes_csv.append({
                    'doc': nom_doc,
                    'entite_id': entite_id,
                    'entite_texte': entite_data['texte'],
                    'entite_type': entite_data['type'],
                    'sens_relation': 'Aucune', 
                    'relation': 'Aucune relation', 
                    'entite_liee_id': 'Aucun',
                    'entite_liee_texte': 'Indéterminé',
                    'entite_liee_type': 'Aucun',
                    'texte_contexte': entite_data['contexte']
                })

    
    # Export du fichier CSV
    # *****************************************************************

    if toutes_les_lignes_csv:
        df = pd.DataFrame(toutes_les_lignes_csv)
        
        # Réorganisation des colonnes avec la nouvelle logique
        colonnes_ordonnees = [
            'doc', 'entite_id', 'entite_texte', 'entite_type', 
            'sens_relation', 'relation', 'entite_liee_id', 'entite_liee_texte', 'entite_liee_type', 'texte_contexte'
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