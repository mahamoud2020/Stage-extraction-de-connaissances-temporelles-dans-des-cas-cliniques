import os
import csv
import xml.etree.ElementTree as ET


# Définition des chemins 

Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Dossier_XML = os.path.join(Base_dir, "data", "xml_source") 
Dossier_sortie = os.path.join(Base_dir, "data", "sortie_csv")

NAMESPACES = {
    'xmi': 'http://www.omg.org/XMI',
    'cas': 'http:///uima/cas.ecore',
    'custom': 'http:///webanno/custom.ecore',
    'type4': 'http:///de/tudarmstadt/ukp/dkpro/core/api/segmentation/type.ecore' # Ajout pour les phrases
}

XMI_ID = '{http://www.omg.org/XMI}id'



def extraire_relations_fichier(chemin_fichier):
    nom_fichier = os.path.basename(chemin_fichier)
    print(f" Analyse de : {nom_fichier}...")
    
    try:
        tree = ET.parse(chemin_fichier)
        root = tree.getroot()
    except ET.ParseError:
        print(f" Erreur : Impossible de lire {nom_fichier}.")
        return []

    # Récupération du texte global (SofaString)
    sofa = root.find('cas:Sofa', NAMESPACES)
    texte_global = sofa.get('sofaString') if sofa is not None else ""
    
    if not texte_global:
        return []

    # Extraction et indexation de toutes les phrases complètes du document
    phrases = []
    for elem in root.findall('type4:Sentence', NAMESPACES):
        b = elem.get('begin')
        e = elem.get('end')
        if b is not None and e is not None:
            b_idx, e_idx = int(b), int(e)
            texte_phrase = texte_global[b_idx:e_idx].strip().replace('\n', ' ').replace(';', ',')
            phrases.append({
                'begin': b_idx,
                'end': e_idx,
                'texte': texte_phrase
            })

    # Indexation des concepts (avec sauvegarde des positions begin/end)
    concepts = {}
    tags_entites = ['custom:EVENT', 'custom:TIMEX3', 'custom:CLINENTITY', 'custom:BODYPART', 'custom:ACTOR']
    compteur_entites = 0
    
    for tag in tags_entites:
        for elem in root.findall(tag, NAMESPACES):
            xmi_id = elem.get(XMI_ID)
            begin = elem.get('begin')
            end = elem.get('end')
            
            b_idx = int(begin) if begin is not None else 0
            e_idx = int(end) if end is not None else 0
            texte_extrait = texte_global[b_idx:e_idx].strip() if begin and end else ""
            
            concepts[xmi_id] = {
                'id': xmi_id, 
                'type': tag.split(':')[-1], 
                'texte': texte_extrait.replace('\n', ' ').replace(';', ','), 
                'begin': b_idx,
                'end': e_idx,
                'elem': elem
            }
            compteur_entites += 1

    # Indexation des balises de relations (Links)
    liens = {}
    tags_liens = ['custom:EVENTTLINKLink', 'custom:TIMEX3TimexLinkLink']
    compteur_liens = 0
    
    for tag in tags_liens:
        for elem in root.findall(tag, NAMESPACES):
            xmi_id = elem.get(XMI_ID)
            liens[xmi_id] = {'role': elem.get('role'), 'target': elem.get('target')}
            compteur_liens += 1
            
    print(f" Trouvé : {compteur_entites} entités, {len(phrases)} phrases et {compteur_liens} liaisons.")

    # Reconstruction des relations et recherche du contexte du texte 
    relations_fichier = []
    doc_id = nom_fichier.split('.')[0]

    for c_id, info in concepts.items():
        elem = info['elem']
        attribut_lien = elem.get('TLINK') or elem.get('timexLink')
        
        if attribut_lien:
            ids_liens = attribut_lien.split()
            for l_id in ids_liens:
                if l_id in liens:
                    info_lien = liens[l_id]
                    cible_id = info_lien['target']
                    
                    if cible_id in concepts:
                        info_cible = concepts[cible_id]
                        
                        # Recherche de la phrase complète contenant l'événement source
                        contexte_texte = "Phrase introuvable"
                        for p in phrases:
                            if p['begin'] <= info['begin'] <= p['end']:
                                contexte_texte = p['texte']
                                break
                        
                        relations_fichier.append({
                            'doc': doc_id,
                            'source_id': c_id, 
                            'source_type': info['type'], 
                            'entite_source': info['texte'],
                            'relation_temporelle': info_lien['role'],
                            'cible_id': cible_id, 
                            'cible_type': info_cible['type'], 
                            'entite_cible': info_cible['texte'],
                            'contexte_texte': contexte_texte # affiche texte complete
                        })
                        
    print(f"  Bilan : {len(relations_fichier)} relations temporelles reconstruites.")
    return relations_fichier


def main():
    print(f"\n Recherche de fichiers dans : {Dossier_XML}")
    
    if not os.path.exists(Dossier_XML):
        print(f" Erreur : Le dossier {Dossier_XML} n'existe pas !")
        return

    fichiers = [os.path.join(Dossier_XML, f) for f in os.listdir(Dossier_XML) 
                if os.path.isfile(os.path.join(Dossier_XML, f)) and not f.startswith('.')]
    
    print(f" {len(fichiers)} fichier(s) trouvé(s) au total.\n")
    
    os.makedirs(Dossier_sortie, exist_ok=True)
    toutes_les_relations = []
    
    for chemin in fichiers:
        relations = extraire_relations_fichier(chemin)
        toutes_les_relations.extend(relations)
        
    if not toutes_les_relations:
        print("\n Aucune relation temporelle n'a pu être exportée.")
        return

    fichier_csv = os.path.join(Dossier_sortie, "relations_temporelles_evenements.csv")
    champs = ['doc', 'source_id', 'source_type', 'entite_source', 'relation_temporelle', 'cible_id', 'cible_type', 'entite_cible', 'contexte_texte']
    
    with open(fichier_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=champs)
        writer.writeheader()
        writer.writerows(toutes_les_relations)
        
    print(f"\n Extraction effectuée ! {len(toutes_les_relations)} relations exportées avec leur contexte dans : {fichier_csv}")

if __name__ == "__main__":
    main()