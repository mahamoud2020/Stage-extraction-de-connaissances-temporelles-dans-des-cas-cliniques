import os
import glob
import requests
import time
import subprocess
import csv
import re 
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

# Nouvelle fonction linguistiques (à partir du script de Federzoni)

def traduire_nature(upos):
    """Traduit l'étiquette universelle (UPOS) vers l'étiquette simplifiée comme le script de Federzoni."""
    mapping = {'PRON': 'Pro', 'NOUN': 'Nom', 'PROPN': 'Nom', 'DET': 'Det', 'ADJ': 'Adj', 'NUM': 'Num'}
    return mapping.get(upos, 'Autre')

def traduire_fonction(deprel):
    """Traduit la dépendance syntaxique vers la fonction simplifiée."""
    deprel_base = deprel.split(':')[0] # Coupe "nsubj:pass" en "nsubj"
    if deprel_base == 'nsubj': return 'Suj'
    if deprel_base == 'obj': return 'OD'
    if deprel_base == 'iobj': return 'OI'
    if deprel_base == 'obl': return 'Obl'
    return 'autre'

def trouver_tete_lexicale(tokens_mention):
    """
    Trouve la tête d'un groupe de mots. 
    Logique : La tête est le mot dont le parent syntaxique (head) n'est pas dans le groupe.
    """
    ids_mention = [token['id'] for token in tokens_mention]
    for token in tokens_mention:
        if token['head'] not in ids_mention:
            return token # On a trouvé le chef !
    return tokens_mention[0] # Sécurité

# Requête API 

def appeler_udpipe2(texte_brut):
    params = {"model": "french-gsd-ud-2.12-230717", "tokenizer": "", "tagger": "", "parser": ""}
    try:
        response = requests.post(UDPIPE_API_URL, data=params, files={'data': texte_brut})
        return response.json().get('result') if response.status_code == 200 else None
    except: return None

# Nouvelle fonction d'extraction (à partir du script de Federzoni)

def extraire_mentions_conllu(repertoire):
    mentions_finales = []
    fichiers = glob.glob(os.path.join(repertoire, "*.15.conllu"))
    print(f"  [Info] Analyse de {len(fichiers)} fichiers de résultats trouvés dans {repertoire}...")
    
    for f_path in fichiers:
        doc_id = os.path.basename(f_path).split('.')[0]
        print(f"    -> Lecture des mentions de {doc_id}...")
        
        with open(f_path, 'r', encoding='utf-8') as f:
            mentions_ouvertes = {} 
            
            for line in f:
                if line.startswith('#') or not line.strip(): 
                    continue
                cols = line.strip().split('\t')
                
                # On s'assure qu'on lit bien une ligne de mot valide (sans les fusions type 1-2)
                if len(cols) > 9 and '-' not in cols[0]:
                    token = {
                        'id': cols[0], 'form': cols[1], 'lemma': cols[2],
                        'upos': cols[3], 'head': cols[6], 'deprel': cols[7],
                        'misc': cols[9]
                    }
                    
                    simples, debuts, fins = [], [], []
                    
                    if "Entity=" in token['misc']:
                        match = re.search(r'Entity=([^|]+)', token['misc'])
                        if match:
                            ent_str = match.group(1)
                            simples = re.findall(r'\((\w+)\)', ent_str)      
                            debuts = re.findall(r'\((\w+)(?!\))', ent_str)   
                            fins = re.findall(r'(?<!\()(\w+)\)', ent_str)    
                    
                    for ent_id in debuts + simples:
                        if ent_id not in mentions_ouvertes:
                            mentions_ouvertes[ent_id] = []
                            
                    for ent_id in mentions_ouvertes.keys():
                        mentions_ouvertes[ent_id].append(token)
                        
                    for ent_id in fins + simples:
                        if ent_id in mentions_ouvertes:
                            tokens_mention = mentions_ouvertes.pop(ent_id)
                            
                            tete = trouver_tete_lexicale(tokens_mention)
                            texte_complet = " ".join([t['form'] for t in tokens_mention])
                            
                            mentions_finales.append({
                                'doc': doc_id,
                                'mention_id': ent_id,
                                'texte_maillon': texte_complet,
                                'tete_lexicale': tete['form'],
                                'nature': traduire_nature(tete['upos']),
                                'fonction': traduire_fonction(tete['deprel'])
                            })
    return mentions_finales

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
        fichiers_entree = glob.glob(os.path.join(CONLLU_INPUT, "*.conllu"))
        
        if not fichiers_entree:
            print("Erreur : Aucun fichier .conllu trouvé dans data/conllu_entree")
        else:
            cmd = ["python", "crac2025-corpipe/corpipe25.py", 
                   "--load", "ufal/corpipe25-corefud1.3-large-251101", 
                   "--test"] + fichiers_entree + ["--exp", "data", "--segment", "2560"]
            
            subprocess.run(cmd, check=True)
            
    except Exception as e: 
        print(f"Erreur CorPipe: {e}")

    # 3. Extraction CSV
    print("\nÉtape 3 : Extraction des données vers CSV...")
    mentions_predites = extraire_mentions_conllu(CONLLU_OUTPUT)
    with open(CSV_RESULTATS, 'w', newline='', encoding='utf-8') as csvfile:
        # ici adaptation du script de Federzoni pour mise à jour des en-têtes du CSV
        writer = csv.DictWriter(csvfile, fieldnames=['doc', 'mention_id', 'texte_maillon', 'tete_lexicale', 'nature', 'fonction'])
        writer.writeheader()
        writer.writerows(mentions_predites)

    # 4. Évaluation (Comparaison Mentions)
    print("\n**************************************************")
    print("Résultats de la détection (UDPipe 2 + CorPipe + Analyse Linguistique)")
    print("**************************************************")
    
    print(f"Total des mentions identifiées par le modèle : {len(mentions_predites)}")
    print(f"Fichier CSV généré : {CSV_RESULTATS}")
    print("\nPipeline terminé avec succès !")

if __name__ == "__main__":
    main()