import os
import glob
import requests
import time
import subprocess
import csv
import re 
from cassis import load_typesystem, load_cas_from_xmi

# --- CONFIGURATION (Chemins relatifs au dossier 'francais') ---
INPUT_DIR = "data/xml_source"
CONLLU_INPUT = "data/conllu_entree"
CONLLU_OUTPUT = "data/conllu_sorti"
CSV_RESULTATS = "data/resultats_coreferences_fr.csv"
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

# --- FONCTIONS LINGUISTIQUES ---

def determiner_nature_syntagme(tokens_mention, tete):
    if not tete: return '∅'
    upos_tete = tete['upos']
    
    if upos_tete == 'PRON':
        return 'Pro'
    elif upos_tete == 'PROPN':
        return 'Np'
    elif upos_tete == 'NOUN':
        id_tete = tete['id']
        determinant = None
        num_modifier = None
        
        for t in tokens_mention:
            if t['head'] == id_tete:
                if t['upos'] == 'DET':
                    determinant = t
                    break
                elif t['upos'] == 'NUM' or 'nummod' in t['deprel']:
                    num_modifier = t
                
        if not determinant and not num_modifier:
            if tokens_mention[0]['upos'] == 'DET':
                determinant = tokens_mention[0]
            elif tokens_mention[0]['upos'] == 'NUM':
                num_modifier = tokens_mention[0]
            
        if determinant:
            lemme_det = determinant['lemma'].lower()
            if lemme_det in ['le', 'la', 'les', 'l\'', 'l', 'au', 'aux']:
                return 'SNdef'
            elif lemme_det in ['ce', 'cet', 'cette', 'ces']:
                return 'SNdem'
            elif lemme_det in ['mon', 'ton', 'son', 'ma', 'ta', 'sa', 'mes', 'tes', 'ses', 'notre', 'votre', 'leur', 'nos', 'vos', 'leurs']:
                return 'Poss'
            else:
                return 'SNind'
        elif num_modifier:
            return 'SNnum'
        else:
            return 'SN∅'
    return 'Autre'

def traduire_fonction(deprel):
    deprel_base = deprel.split(':')[0] 
    if deprel_base == 'nsubj': return 'Suj'
    if deprel_base == 'obj': return 'OD'
    if deprel_base == 'iobj': return 'OI'
    if deprel_base == 'obl': return 'Obl'
    return 'autre'

def trouver_tete_lexicale(tokens_mention):
    ids_mention = [token['id'] for token in tokens_mention]
    for token in tokens_mention:
        if token['head'] not in ids_mention:
            return token 
    return tokens_mention[0] 

# --- REQUÊTE API ---

def appeler_udpipe2(texte_brut):
    # Modèle Français
    params = {"model": "french-gsd-ud-2.12-230717", "tokenizer": "", "tagger": "", "parser": ""}
    try:
        response = requests.post(UDPIPE_API_URL, data=params, files={'data': texte_brut})
        return response.json().get('result') if response.status_code == 200 else None
    except: return None

# --- EXTRACTION CONLLU ---

def extraire_mentions_conllu(repertoire):
    mentions_finales = []
    fichiers = glob.glob(os.path.join(repertoire, "*.15.conllu"))
    print(f"  [Info] Analyse de {len(fichiers)} fichiers dans {repertoire}...")
    
    for f_path in fichiers:
        doc_id = os.path.basename(f_path).split('.')[0]
        with open(f_path, 'r', encoding='utf-8') as f:
            mentions_ouvertes = {} 
            for line in f:
                if line.startswith('#') or not line.strip(): continue
                cols = line.strip().split('\t')
                if len(cols) > 9 and '-' not in cols[0]:
                    token = {'id': cols[0], 'form': cols[1], 'lemma': cols[2], 'upos': cols[3], 'head': cols[6], 'deprel': cols[7], 'misc': cols[9]}
                    if "Entity=" in token['misc']:
                        match = re.search(r'Entity=([^|]+)', token['misc'])
                        if match:
                            ent_str = re.sub(r'--\d+', '', match.group(1)) # Nettoyage CorPipe
                            simples = re.findall(r'\((\w+)\)', ent_str)
                            ent_str_sans_simples = re.sub(r'\(\w+\)', '', ent_str)
                            debuts = re.findall(r'\((\w+)(?!\))', ent_str_sans_simples)
                            fins = re.findall(r'(?<!\()(\w+)\)', ent_str_sans_simples)
                            for ent_id in debuts + simples:
                                if ent_id not in mentions_ouvertes: mentions_ouvertes[ent_id] = []
                            for ent_id in mentions_ouvertes.keys():
                                mentions_ouvertes[ent_id].append(token)
                            for ent_id in fins + simples:
                                if ent_id in mentions_ouvertes:
                                    tokens_mention = mentions_ouvertes.pop(ent_id)
                                    tete = trouver_tete_lexicale(tokens_mention)
                                    mentions_finales.append({
                                        'doc': doc_id, 'mention_id': ent_id,
                                        'texte_maillon': " ".join([t['form'] for t in tokens_mention]),
                                        'tete_lexicale': tete['form'],
                                        'nature': determiner_nature_syntagme(tokens_mention, tete),
                                        'fonction': traduire_fonction(tete['deprel'])
                                    })
    return mentions_finales

# --- MAIN PIPELINE ---

def main():
    # Création des dossiers si nécessaire
    os.makedirs(CONLLU_INPUT, exist_ok=True)
    os.makedirs(CONLLU_OUTPUT, exist_ok=True)

    print("Étape 1 : UDPipe 2 (Français)...")
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

    print("\nÉtape 2 : Inférence CorPipe (Remonte à la racine)...")
    fichiers_entree = glob.glob(os.path.join(CONLLU_INPUT, "*.conllu"))
    if fichiers_entree:
        # NOTE: ../crac2025-corpipe pour sortir du dossier francais
        cmd = ["python", "../crac2025-corpipe/corpipe25.py", 
               "--load", "ufal/corpipe25-corefud1.3-large-251101", 
               "--test"] + fichiers_entree + ["--exp", CONLLU_OUTPUT, "--segment", "2560"]
        subprocess.run(cmd, check=True)

    print("\nÉtape 3 : Extraction CSV...")
    mentions = extraire_mentions_conllu(CONLLU_OUTPUT)
    with open(CSV_RESULTATS, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['doc', 'mention_id', 'texte_maillon', 'tete_lexicale', 'nature', 'fonction'])
        writer.writeheader()
        writer.writerows(mentions)

    print(f"\nTerminé ! Résultats : {CSV_RESULTATS}")

if __name__ == "__main__":
    main()