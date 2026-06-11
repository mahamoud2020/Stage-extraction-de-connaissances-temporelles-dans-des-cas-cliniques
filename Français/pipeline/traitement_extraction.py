import os
import glob
import csv
import re


# Défintion des chemins

Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Conllu_output = os.path.join(Base_dir, "data", "conllu_sorti")
Dossier_CSV = os.path.join(Base_dir, "data", "sortie_csv")


# Logique de classification (determine la nature) 


def trouver_tete_lexicale(tokens_mention):
    ids_mention = [token['id'] for token in tokens_mention]
    candidats = []
    
    for token in tokens_mention:
        if token['head'] not in ids_mention:
            candidats.append(token)
            
    if not candidats:
        return tokens_mention[0]
        
    if len(candidats) > 1:
        candidats_forts = [t for t in candidats if t['upos'] not in ['DET', 'ADP', 'CCONJ', 'SCONJ', 'PUNCT', 'SYM']]
        if candidats_forts:
            return candidats_forts[0]
            
    return candidats[0]



def determiner_nature_syntagme(tokens_mention, tete):
    if not tete: return 'Autre'
    upos_tete = tete['upos']
    lemme_tete = tete['lemma'].lower()
    form_tete = tete['form']
    form_tete_lower = form_tete.lower()
    feats_tete = tete.get('feats', '') 

    premier_mot = tokens_mention[0]
    upos_premier = premier_mot['upos']
    form_premier = premier_mot['form']
    feats_premier = premier_mot.get('feats', '')
    lemmes_maillon = [t['lemma'].lower() for t in tokens_mention]

    def evaluer_sn_par_determinant(feats_det):
        
        if 'Poss=Yes' in feats_det: return 'SNposs' 
        if 'PronType=Dem' in feats_det: return 'SNdem'
        if 'Definite=Def' in feats_det: return 'SNdef'
        return 'SNind'

    id_tete_str = str(tete['id'])
    
    determinant = next((t for t in tokens_mention if t['head'] == id_tete_str and t['upos'] == 'DET'), None)
    if not determinant and tokens_mention[0]['upos'] == 'DET': 
        determinant = tokens_mention[0]

    num_modifier = next((t for t in tokens_mention if t['head'] == id_tete_str and (t['upos'] == 'NUM' or 'nummod' in t['deprel']) and int(t['id']) < int(tete['id'])), None)
    if not num_modifier and tokens_mention[0]['upos'] == 'NUM' and int(tokens_mention[0]['id']) < int(tete['id']):
        num_modifier = tokens_mention[0]

    if upos_tete == 'X':
        if determinant:
            return evaluer_sn_par_determinant(determinant.get('feats', ''))
        for t in tokens_mention:
            if any(char.isdigit() or char in '=<>+' for char in t['form']):
                return 'Autre'
        return 'SN∅'

    if not determinant and upos_premier in ['PROPN', 'NOUN', 'VERB'] and len(form_premier) >= 5:
        if re.match(r'^[Ll][aeiouyAEIOUYhH]', form_premier):
            return 'SNdef'

    if upos_tete == 'ADJ' and lemme_tete == 'dernier' and upos_premier == 'DET':
        return 'Pro'

    if upos_tete in ['ADJ', 'NUM', 'PROPN']:
        if upos_premier == 'DET': return evaluer_sn_par_determinant(feats_premier)
        elif upos_premier == 'NUM': return 'SNnum'

    titres = {'mme', 'madame', 'm.', 'mr.', 'mr', 'monsieur', 'mlle', 'mademoiselle', 'pr', 'dr'}
    if form_tete_lower in titres: return 'Np'

    if upos_tete in ['VERB', 'AUX']:
        idx_tete = next((i for i, t in enumerate(tokens_mention) if t['id'] == tete['id']), 0)
        if idx_tete == 0: return 'Sujet_zero'
        
        sujet = next((t for t in tokens_mention if t['head'] == id_tete_str and 'subj' in t['deprel']), None)
        if sujet:
            if sujet['upos'] == 'PRON': return 'Pro'
            if sujet['upos'] == 'PROPN': return 'Np'
            det_sujet = next((t for t in tokens_mention if t['head'] == str(sujet['id']) and t['upos'] == 'DET'), None)
            if det_sujet: return evaluer_sn_par_determinant(det_sujet.get('feats', ''))
            return 'SN∅'
        
        if upos_premier == 'DET': return evaluer_sn_par_determinant(feats_premier)
        elif upos_premier == 'PROPN': return 'Np'
        elif upos_premier == 'PRON': return 'Pro'
        else: return 'SN∅'

    if 'un' in lemmes_maillon and 'autre' in lemmes_maillon and lemme_tete in ['un', 'autre']: 
        return 'Pro'

    
    if upos_tete == 'DET':
        if 'Poss=Yes' in feats_tete: 
            return 'Poss' # Si c'est juste "notre" ou "son", on garde Poss
        res = evaluer_sn_par_determinant(feats_tete)
        # Sécurité : un DET isolé ne peut pas être un SNposs, c'est un Poss
        if res == 'SNposs': return 'Poss'
        return res

    if upos_tete == 'PRON': return 'Poss' if 'Poss=Yes' in feats_tete else 'Pro'
    if upos_tete == 'PROPN': return 'Np'
    if upos_tete == 'NOUN':
        if determinant: return evaluer_sn_par_determinant(determinant.get('feats', ''))
        elif num_modifier: return 'SNnum' 
        return 'SN∅'
        
    return 'Autre'



def traduire_fonction(deprel):
    deprel_base = deprel.split(':')[0] 
    mapping = {
        'nsubj': 'Suj', 
        'obj': 'OD', 
        'obl': 'Obl'
    }
    return mapping.get(deprel_base, 'autre')

def recalibrer_mention_verbale(tokens_mention, tete_actuelle, nature_actuelle):
    if nature_actuelle == 'Sujet_zero':
        return tokens_mention, tete_actuelle, tete_actuelle['upos'], nature_actuelle
    id_verbe = int(tete_actuelle['id'])
    id_limite = id_verbe
    for t in tokens_mention:
        if t['head'] == str(id_verbe) and t['upos'] == 'AUX' and int(t['id']) < id_limite:
            id_limite = int(t['id'])
    tokens_gauche = [t for t in tokens_mention if int(t['id']) < id_limite]
    if not tokens_gauche:
        return tokens_mention, tete_actuelle, tete_actuelle['upos'], nature_actuelle
    
    mots_outils = {"le", "la", "les", "l'", "un", "une", "des", "ce", "cette", "ces", "au", "aux", "du"}
    mots_gauche_lower = [t['form'].lower() for t in tokens_gauche]
    
    if len(tokens_gauche) <= 2 and all(m in mots_outils for m in mots_gauche_lower):
        nouvelle_nature = nature_actuelle
        if any(m in {"le", "la", "les", "l'", "au", "aux", "du", "ce", "cette", "ces"} for m in mots_gauche_lower):
            nouvelle_nature = 'SNdef'
        elif any(m in {"un", "une", "des"} for m in mots_gauche_lower):
            nouvelle_nature = 'SNind'
        return tokens_mention, tete_actuelle, 'NOUN', nouvelle_nature

    while len(tokens_gauche) > 0 and tokens_gauche[-1]['upos'] in ['PUNCT', 'AUX', 'CCONJ', 'SCONJ']:
        tokens_gauche.pop()
    
    if not tokens_gauche:
        return tokens_mention, tete_actuelle, tete_actuelle['upos'], nature_actuelle
    
    nouvelle_tete = trouver_tete_lexicale(tokens_gauche)
    return tokens_gauche, nouvelle_tete, nouvelle_tete['upos'], determiner_nature_syntagme(tokens_gauche, nouvelle_tete)

def extraire_mentions_conllu(repertoire):
    mentions_finales = []
    fichiers = glob.glob(os.path.join(repertoire, "*.15.conllu"))
    for f_path in fichiers:
        doc_id = os.path.basename(f_path).split('.')[0]
        with open(f_path, 'r', encoding='utf-8') as f:
            mentions_ouvertes = {} 
            for line in f:
                if line.startswith('#') or not line.strip(): continue
                cols = line.strip().split('\t')
                if len(cols) > 9 and '-' not in cols[0]:
                    token = {'id': cols[0], 'form': cols[1], 'lemma': cols[2], 'upos': cols[3], 'feats': cols[5], 'head': cols[6], 'deprel': cols[7], 'misc': cols[9]}
                    debuts, fins, simples = [], [], []
                    match = re.search(r'Entity=([^|]+)', token['misc'])
                    if match:
                        ent_str = re.sub(r'--\d+', '', match.group(1))
                        simples = re.findall(r'\((\w+)\)', ent_str)
                        debuts = re.findall(r'\((\w+)(?!\))', re.sub(r'\(\w+\)', '', ent_str))
                        fins = re.findall(r'(?<!\()(\w+)\)', re.sub(r'\(\w+\)', '', ent_str))
                    for eid in debuts + simples:
                        if eid not in mentions_ouvertes: mentions_ouvertes[eid] = []
                        mentions_ouvertes[eid].append([])
                    for eid, piles in mentions_ouvertes.items():
                        for p in piles: p.append(token)
                    for eid in fins + simples:
                        if eid in mentions_ouvertes:
                            tokens_m = mentions_ouvertes[eid].pop()
                            tete = trouver_tete_lexicale(tokens_m)
                            upos, nature = tete['upos'], determiner_nature_syntagme(tokens_m, tete)
                            if upos in ['VERB', 'AUX']:
                                tokens_m, tete, upos, nature = recalibrer_mention_verbale(tokens_m, tete, nature)
                            
                            t_form = tete['form'].replace('\n', ' ').replace(';', ',')
                            
                            det_attache = next((t for t in tokens_m if t['head'] == str(tete['id']) and t['upos'] == 'DET'), None)
                            if not det_attache and tokens_m[0]['upos'] == 'DET': 
                                det_attache = tokens_m[0]

                            mots_l_immunises = {'listeria', 'lésion', 'lésions', 'lymphome', 'localisation', 'lombaire', 'longueur', 'largeur', 'liquide'}
                            
                            if not det_attache and upos in ['PROPN', 'NOUN', 'VERB'] and len(t_form) >= 5:
                                if re.match(r'^[Ll][aeiouyAEIOUYhH]', t_form) and t_form.lower() not in mots_l_immunises:
                                    upos, nature = 'NOUN', 'SNdef'
                            
                            titres = {'mme', 'madame', 'm.', 'mr.', 'mr', 'monsieur', 'mlle', 'mademoiselle', 'pr', 'dr'}
                            if t_form.lower() in titres:
                                upos, nature = 'NOUN', 'Np'

                            mentions_finales.append({
                                'doc': doc_id, 'mention_id': eid, 'nature': nature,
                                'texte_maillon': " ".join([t['form'] for t in tokens_m]).replace('\n', ' ').replace(';', ','),
                                'tete_lexicale': t_form, 'upos_tete': upos,
                                'fonction': traduire_fonction(tete['deprel'])
                            })
                            if not mentions_ouvertes[eid]: del mentions_ouvertes[eid]
    return mentions_finales



def main():
    os.makedirs(Dossier_CSV, exist_ok=True)
    mentions = extraire_mentions_conllu(Conllu_output)
    if not mentions: return
    with open(os.path.join(Dossier_CSV, "resultats_mentions_fr.csv"), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['doc', 'mention_id', 'texte_maillon', 'tete_lexicale', 'upos_tete', 'nature', 'fonction'])
        w.writeheader()
        w.writerows(mentions)
    
    chaines = {}
    for m in mentions:
        cid = f"{m['doc']}_{m['mention_id']}"
        if cid not in chaines: chaines[cid] = []
        chaines[cid].append(m)
    valides = {k: v for k, v in chaines.items() if len(v) >= 2}
    if valides:
        max_L = max(len(v) for v in valides.values())
        heads = ['id_CR', 'doc', 'mention_id', 'Longueur', 'nature_premier', 'FS_premier'] + [f'M{i}' for i in range(1, max_L+1)]
        with open(os.path.join(Dossier_CSV, "sequences_coreferences_fr.csv"), 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=heads)
            w.writeheader()
            for cid, ms in valides.items():
                row = {'id_CR': cid, 'doc': ms[0]['doc'], 'mention_id': ms[0]['mention_id'], 'Longueur': len(ms), 'nature_premier': ms[0]['nature'], 'FS_premier': ms[0]['fonction']}
                for i, m in enumerate(ms): row[f'M{i+1}'] = m['nature']
                w.writerow(row)

if __name__ == "__main__": 
    main()