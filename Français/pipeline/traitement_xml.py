import os
import glob
import xml.etree.ElementTree as ET
import csv


# Définition des chemins 

Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # remonter au dossier "Français" (car le script est dans "pipeline")

Dossier_XML = os.path.join(Base_dir, "data", "xml_source") 
Dossier_CSV = os.path.join(Base_dir, "data", "sortie_csv")



def extraire_entites_xmi(chemin_fichier_xmi):
    
    try:
        tree = ET.parse(chemin_fichier_xmi)
        root = tree.getroot()
    except Exception as e:
        print(f" Lecture impossible de {os.path.basename(chemin_fichier_xmi)} : {e}")
        return []

    # Recherche du texte brut
    sofa_node = root.find('.//{http:///uima/cas.ecore}Sofa')
    texte_complet = sofa_node.get('sofaString') if sofa_node is not None else ""
    
    # Entités à extraire
    cibles = ['EVENT', 'TIMEX3', 'ACTOR', 'BODYPART', 'RML', 'CLINENTITY']
    entites = []
    
    for element in root:
        nom_balise = element.tag.split('}')[-1] 
        
        if nom_balise in cibles:
            try:
                debut = int(element.get('begin'))
                fin = int(element.get('end'))
                texte_entite = texte_complet[debut:fin].replace('\n', ' ').strip()
                
                entites.append({
                    'categorie': nom_balise,
                    'debut': debut,
                    'fin': fin,
                    'texte': texte_entite
                })
            except TypeError:
                continue
                
    return entites




def analyser_corpus_xml():
    """Fonction principale pour être appelée par le run_pipeline.py"""
    print("\n Étape 4 : Extraction des entités cliniques (XML) ")
    
    fichiers = glob.glob(os.path.join(Dossier_XML, "*.xmi"))
    if not fichiers:
        fichiers = glob.glob(os.path.join(Dossier_XML, "*.xml"))
        
    if not fichiers:
        print(f" Aucun fichier XML trouvé dans {Dossier_XML}.")
        return None
        
    print(f" {len(fichiers)} fichiers trouvés dans 'xml_source'.")
    
    toutes_les_entites = {}
    total_entites = 0
    
    for f_path in fichiers:
        doc_id = os.path.basename(f_path).replace('.xmi', '').replace('.xml', '')
        if '_' in doc_id:
            doc_id = doc_id.split('_')[-1]
            
        entites_du_doc = extraire_entites_xmi(f_path)
        toutes_les_entites[doc_id] = entites_du_doc
        total_entites += len(entites_du_doc)
        
    print(f" {total_entites} entités cliniques extraites au total !")
    
    # Sauvegarde CSV 
    os.makedirs(Dossier_CSV, exist_ok=True)
    fichier_sortie = os.path.join(Dossier_CSV, "verif_entites_cliniques.csv")
    
    with open(fichier_sortie, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['doc_id', 'categorie', 'texte', 'debut', 'fin'])
        writer.writeheader()
        
        for doc_id, liste_entites in toutes_les_entites.items():
            for ent in liste_entites:
                writer.writerow({
                    'doc_id': doc_id,
                    'categorie': ent['categorie'],
                    'texte': ent['texte'],
                    'debut': ent['debut'],
                    'fin': ent['fin']
                })
                
    print(f" Fichier généré : {fichier_sortie}")
    return toutes_les_entites

if __name__ == "__main__":
    analyser_corpus_xml()