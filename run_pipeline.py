import os
import glob
import requests
import time
import subprocess
import csv
from cassis import load_typesystem, load_cas_from_xmi

# Configuration
INPUT_DIR = "data/xml_source"
CONLLU_INPUT = "data/conllu_entree"
CONLLU_OUTPUT = "data"
CSV_RESULTATS = "data/resultats_coreferences.csv"
UDPIPE_API_URL = "https://lindat.mff.cuni.cz/services/udpipe/api/process"

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

# 

def appeler_udpipe2(texte_brut):
    params = {"model": "french-gsd-ud-2.12-230717", "tokenizer": "", "tagger": "", "parser": ""}
    try:
        response = requests.post(UDPIPE_API_URL, data=params, files={'data': texte_brut})
        return response.json().get('result') if response.status_code == 200 else None
    except: return None

def extraire_mentions_conllu(repertoire):
    mentions = []
    # On cherche tous les fichiers qui finissent par .conllu dans le dossier data/
    
    fichiers = glob.glob(os.path.join(repertoire, "*.15.conllu"))
    
    print(f"  [Info] Analyse de {len(fichiers)} fichiers de résultats trouvés dans {repertoire}...")
    
    for f_path in fichiers:
        doc_id = os.path.basename(f_path).split('.')[0] # Récupère FR100003
        print(f"    -> Lecture des mentions de {doc_id}...")
        
        with open(f_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('#') or not line.strip(): 
                    continue
                cols = line.strip().split('\t')
                
                # On vérifie la colonne 10 (index 9) pour la coréférence
                if len(cols) > 9 and "Entity=" in cols[9]:
                    mentions.append({
                        'doc': doc_id, 
                        'token': cols[1], 
                        'lemma': cols[2], 
                        'pos': cols[3], 
                        'coref': cols[9]
                    })
    return mentions

# Main pipeline

def main():
    # 1. Conversion UDPipe 2
    print("Étape 1 : Conversion via UDPipe 2 API...")
    typesystem = load_typesystem(TYPESYSTEM_XML)
    for file_path in glob.glob(os.path.join(INPUT_DIR, "*.xml")):
        doc_id = os.path.splitext(os.path.basename(file_path))[0]
        with open(file_path, 'rb') as f:
            cas = load_cas_from_xmi(f, typesystem=typesystem, lenient=True)
        res = appeler_udpipe2(cas.sofa_string)
        if res:
            with open(os.path.join(CONLLU_INPUT, f"{doc_id}.conllu"), 'w', encoding='utf-8') as out:
                out.write(f"# newdoc id = {doc_id}\n" + res)
        time.sleep(0.5)

    
    # 2. Corpipe
    print("\nÉtape 2 : Inférence CorPipe...")
    try:
        # On utilise glob pour donner la liste exacte des fichiers à CorPipe
        fichiers_entree = glob.glob(os.path.join(CONLLU_INPUT, "*.conllu"))
        
        if not fichiers_entree:
            print("Erreur : Aucun fichier .conllu trouvé dans data/conllu_entree")
        else:
            # On lance CorPipe sur la liste des fichiers
            cmd = ["python", "crac2025-corpipe/corpipe25.py", 
                   "--load", "ufal/corpipe25-corefud1.3-large-251101", 
                   "--test"] + fichiers_entree + ["--exp", "data"]
            
            subprocess.run(cmd, check=True)
            
    except Exception as e: 
        print(f"Erreur CorPipe: {e}")

    # 3. Extraction CSV
    print("\nÉtape 3 : Extraction des données vers CSV...")
    mentions_predites = extraire_mentions_conllu(CONLLU_OUTPUT)
    with open(CSV_RESULTATS, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['doc', 'token', 'lemma', 'pos', 'coref'])
        writer.writeheader()
        writer.writerows(mentions_predites)

    # 4. Évaluation (Comparaison Mentions)
    print("\n**************************************************")
    print("Résultats de la détection (UDPipe 2 + CorPipe)")
    print("**************************************************")
    
    # Pour l'exemple, on affiche le total. 
    # (Note: l'évaluation précise FN/FP nécessite de recharger les annotations XML)
    print(f"Total des mentions identifiées par le modèle : {len(mentions_predites)}")
    print(f"Fichier CSV généré : {CSV_RESULTATS}")
    print("\nPipeline terminé avec succès !")

if __name__ == "__main__":
    main()