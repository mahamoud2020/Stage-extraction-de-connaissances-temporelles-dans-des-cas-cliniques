import os
import glob
import csv
import re


# Gestion automatique des chemins

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONLLU_OUTPUT = os.path.join(BASE_DIR, "data", "conllu_sorti")
DOSSIER_CSV = os.path.join(BASE_DIR, "data", "sortie_csv")


# Fonction linguistique et syntaxique 


def determiner_nature_syntagme(tokens_mention, tete):
    if not tete:
        return 'Autre'
        
    upos_tete = tete['upos']
    lemme_tete = tete['lemma'].lower()
    form_tete = tete['form']
    feats_tete = tete.get('feats', '') 
    lemmes_maillon = [t['lemma'].lower() for t in tokens_mention]

    # Règle : Tête = VERB ou AUX (La règle du regard du focus du mot à gauche de la tête ) 
    if upos_tete in ['VERB', 'AUX']:
        idx_tete = next((i for i, t in enumerate(tokens_mention) if t['id'] == tete['id']), 0)
        
        if idx_tete == 0:
            return 'Sujet_zero'
        else:
            premier_mot = tokens_mention[0]
            upos_premier = premier_mot['upos']
            feats_premier = premier_mot.get('feats', '')
            
            if upos_premier == 'DET':
                if 'Poss=Yes' in feats_premier: return 'Poss'
                if 'PronType=Dem' in feats_premier: return 'SNdem'
                if 'Definite=Def' in feats_premier: return 'SNdef'
                return 'SNind'
            elif upos_premier == 'PROPN':
                return 'Np'
            elif upos_premier == 'PRON':
                if 'Poss=Yes' in feats_premier: return 'Poss'
                return 'Pro'
            elif upos_premier == 'NUM':
                return 'SNnum'
            else:
                return 'SN∅'
                
    # Recherhche des dépendants (déterminant ou numéral) 
    id_tete = int(tete['id'])
    determinant = None
    num_modifier = None
    
    for t in tokens_mention:
        if t['head'] == str(id_tete):
            if t['upos'] == 'DET':
                determinant = t
                break
            elif (t['upos'] == 'NUM' or 'nummod' in t['deprel']) and int(t['id']) < id_tete:
                num_modifier = t
                
    if not determinant and not num_modifier and len(tokens_mention) > 1:
        if tokens_mention[0]['upos'] == 'DET':
            determinant = tokens_mention[0]
        elif tokens_mention[0]['upos'] == 'NUM' and int(tokens_mention[0]['id']) < id_tete:
            num_modifier = tokens_mention[0]

    # Règle pour "X"
    if upos_tete == 'X':
        if determinant:
            feats_det = determinant.get('feats', '')
            if 'Poss=Yes' in feats_det: return 'Poss'
            if 'PronType=Dem' in feats_det: return 'SNdem'
            if 'Definite=Def' in feats_det: return 'SNdef'
            return 'SNind'
        else:
            contient_chiffre = any(any(char.isdigit() for char in t['form']) for t in tokens_mention)
            contient_symbole = any(re.search(r'[=<>)]', t['form']) for t in tokens_mention)
            
            if contient_chiffre or contient_symbole:
                return 'Autre'
            else:
                return 'SN∅'

    # Règle standard 
    if re.match(r'^[A-Z]{2,}\d*$', form_tete) and not determinant:
        return 'SN∅'

    if upos_tete == 'ADJ':
        if determinant: return 'Pro' 
        else: return 'Autre' 

    if 'un' in lemmes_maillon and 'autre' in lemmes_maillon: return 'Pro'
    
    if upos_tete == 'PRON':
        if 'Poss=Yes' in feats_tete: return 'Poss'
        return 'Pro'
        
    if upos_tete == 'DET':
        if 'Poss=Yes' in feats_tete: return 'Poss'
        if 'PronType=Dem' in feats_tete: return 'SNdem'
        if 'Definite=Def' in feats_tete: return 'SNdef'
        return 'SNind'

    if upos_tete == 'PROPN': return 'Np'
        
    if upos_tete == 'NOUN':
        if determinant:
            feats_det = determinant.get('feats', '')
            if 'Poss=Yes' in feats_det: return 'Poss'
            if 'PronType=Dem' in feats_det: return 'SNdem'
            if 'Definite=Def' in feats_det: return 'SNdef'
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



# Logique d'éxtraction 


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
                    token = {'id': cols[0], 'form': cols[1], 'lemma': cols[2], 'upos': cols[3], 'feats': cols[5], 'head': cols[6], 'deprel': cols[7], 'misc': cols[9]}
                    
                    debuts = []
                    fins = []
                    simples = []
                    
                    if "Entity=" in token['misc']:
                        match = re.search(r'Entity=([^|]+)', token['misc'])
                        if match:
                            ent_str = re.sub(r'--\d+', '', match.group(1))
                            simples = re.findall(r'\((\w+)\)', ent_str)
                            ent_str_sans_simples = re.sub(r'\(\w+\)', '', ent_str)
                            debuts = re.findall(r'\((\w+)(?!\))', ent_str_sans_simples)
                            fins = re.findall(r'(?<!\()(\w+)\)', ent_str_sans_simples)
                            
                    for ent_id in debuts + simples:
                        if ent_id not in mentions_ouvertes:
                            mentions_ouvertes[ent_id] = []
                        mentions_ouvertes[ent_id].append([])
                        
                    for ent_id, piles in mentions_ouvertes.items():
                        for pile in piles:
                            pile.append(token)
                            
                    for ent_id in fins + simples:
                        if ent_id in mentions_ouvertes and len(mentions_ouvertes[ent_id]) > 0:
                            tokens_mention = mentions_ouvertes[ent_id].pop()
                            tete = trouver_tete_lexicale(tokens_mention)
                            
                            # Nettoyage total (sauts de ligne et points-virgules)
                            texte_nettoye = " ".join([t['form'] for t in tokens_mention])
                            texte_nettoye = texte_nettoye.replace('\n', ' ').replace('\r', ' ').replace(';', ',')
                            
                            tete_form = tete['form'].replace('\n', ' ').replace('\r', ' ').replace(';', ',')
                            
                            mentions_finales.append({
                                'doc': doc_id, 'mention_id': ent_id,
                                'texte_maillon': texte_nettoye,
                                'tete_lexicale': tete_form,
                                'upos_tete': tete['upos'],
                                'nature': determiner_nature_syntagme(tokens_mention, tete),
                                'fonction': traduire_fonction(tete['deprel'])
                            })
                            
                            if len(mentions_ouvertes[ent_id]) == 0:
                                del mentions_ouvertes[ent_id]
                                
    return mentions_finales



# Script principal 


def main():
    print("\n Démarrage de l'étape 3 : Extraction des mentions et création des CSV")
    
    os.makedirs(DOSSIER_CSV, exist_ok=True)
    
    # On vérifie la présence des fichiers
    fichiers_finaux = glob.glob(os.path.join(CONLLU_OUTPUT, "*.15.conllu"))
    if not fichiers_finaux:
        print(f" Erreur : aucun fichier .15.conllu trouvé dans '{CONLLU_OUTPUT}'.")
        return

    # Lancement de l'extraction
    mentions = extraire_mentions_conllu(CONLLU_OUTPUT)
    
    if not mentions:
        print(" Erreur : aucune mention extraite.")
        return

    # 1. Création du CSV détaillé
    CSV_MENTIONS = os.path.join(DOSSIER_CSV, "resultats_mentions_fr.csv")
    with open(CSV_MENTIONS, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['doc', 'mention_id', 'texte_maillon', 'tete_lexicale', 'upos_tete', 'nature', 'fonction'])
        writer.writeheader()
        writer.writerows(mentions)
    print(f"   Fichier détaillé généré : {CSV_MENTIONS}")

    # 2. Création du CSV TraMineR
    chaines = {}
    for m in mentions:
        id_CR = f"{m['doc']}_CHAINE_{m['mention_id']}"
        if id_CR not in chaines:
            chaines[id_CR] = []
        chaines[id_CR].append(m)
        
    longueur_max = max(len(maillons) for maillons in chaines.values()) if chaines else 0
    
    en_tetes = ['id_CR', 'doc', 'mention_id', 'Longueur', 'nature_premier_maillon', 'FS_premier_maillon']
    for i in range(1, longueur_max + 1):
        en_tetes.append(f'M{i}')
        
    CSV_SEQUENCES = os.path.join(DOSSIER_CSV, "sequences_coreferences_fr.csv")
    with open(CSV_SEQUENCES, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=en_tetes)
        writer.writeheader()
        
        for id_CR, maillons in chaines.items():
            ligne = {
                'id_CR': id_CR,
                'doc': maillons[0]['doc'],
                'mention_id': maillons[0]['mention_id'],
                'Longueur': len(maillons),
                'nature_premier_maillon': maillons[0]['nature'],
                'FS_premier_maillon': maillons[0]['fonction']
            }
            
            for i, maillon in enumerate(maillons):
                ligne[f'M{i+1}'] = maillon['nature']
                
            writer.writerow(ligne)
            
    print(f"   Fichier TraMineR généré  : {CSV_SEQUENCES}")
    print("\n Terminé ! Le pipeline a sorti les deux tableaux.")

if __name__ == "__main__":
    main()