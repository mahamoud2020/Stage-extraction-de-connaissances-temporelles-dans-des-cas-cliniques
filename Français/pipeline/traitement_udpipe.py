import os
import glob
import time
import requests
from cassis import load_typesystem, load_cas_from_xmi



# Gestion des chemins
# BASE_DIR remonte d'un dossier ("pipeline") pour pointer sur la racine ("Français")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INPUT_DIR = os.path.join(BASE_DIR, "data", "xml_source")
CONLLU_INPUT = os.path.join(BASE_DIR, "data", "conllu_entree")

# TypeSystem écrit en dur pour éviter les problèmes de fichiers introuvables/vides
TYPESYSTEM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<typeSystemDescription xmlns="http://uima.apache.org/resourceSpecifier">
  <types>
    <typeDescription>
      <name>de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence</name>
      <supertypeName>uima.tcas.Annotation</supertypeName>
    </typeDescription>
  </types>
</typeSystemDescription>
"""


# Fonctions utilitaires 


def appeler_udpipe2(texte):
    """
    Envoie le texte à l'API UDPipe 2 et retourne le résultat au format CoNLL-U.
    """
    url = "https://lindat.mff.cuni.cz/services/udpipe/api/process"
    
    # Paramètres de l'API (modèle français par défaut)
    params = {
        "model": "french-gsd-ud-2.12-230717", 
        "tokenizer": "",
        "tagger": "",
        "parser": "",
        "data": texte
    }
    
    try:
        response = requests.post(url, data=params)
        response.raise_for_status()
        resultat = response.json()
        return resultat.get("result", "")
    except Exception as e:
        print(f"   Erreur de connexion à UDPipe : {e}")
        return None



# Fonction principal 


def main():
    # Création du dossier de sortie s'il n'existe pas
    os.makedirs(CONLLU_INPUT, exist_ok=True)
    
    fichiers_xml = glob.glob(os.path.join(INPUT_DIR, "*.xml"))
    
    if not fichiers_xml:
        print(f" Erreur : aucun fichier XML trouvé dans {INPUT_DIR}.")
        return

    print(f" Démarrage de l'étape 1 : UDPipe 2 ({len(fichiers_xml)} fichiers trouvés au total)")
    
    # Chargement du TypeSystem directement depuis la variable texte
    try:
        typesystem = load_typesystem(TYPESYSTEM_XML)
    except Exception as e:
        print(f" Erreur : impossible de charger le TypeSystem interne\nDétails : {e}")
        return

    fichiers_traites = 0
    
    for file_path in fichiers_xml:
        doc_id = os.path.splitext(os.path.basename(file_path))[0]
        fichier_sortie = os.path.join(CONLLU_INPUT, f"{doc_id}.conllu")
        
        # Mode incrémental : On ne traite le fichier que s'il n'existe pas déjà
        if not os.path.exists(fichier_sortie):
            print(f"   Traitement de {doc_id}...")
            
            with open(file_path, 'rb') as f:
                cas = load_cas_from_xmi(f, typesystem=typesystem, lenient=True)
            
            texte_brut = cas.sofa_string
            res = appeler_udpipe2(texte_brut)
            
            if res:
                with open(fichier_sortie, 'w', encoding='utf-8') as out:
                    out.write(f"# newdoc id = {doc_id}\n" + res)
                print(f"    {doc_id} enregistré.")
            else:
                print(f"    Échec pour {doc_id}.")
            
            # Petite pause pour ne pas saturer les serveurs d'UDPipe
            time.sleep(0.5)
            fichiers_traites += 1

    # Bilan de l'exécution
    if fichiers_traites == 0:
        print(" Étape 1 ignorée : tous les fichiers .conllu sont déjà présents dans le dossier.")
    else:
        print(f" Étape 1 terminée ! ({fichiers_traites} nouveaux fichiers traités)")

if __name__ == "__main__":
    main()