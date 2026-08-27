import os
import pandas as pd
import graphviz
import networkx as nx
import networkx.algorithms.isomorphism as iso
import argparse
import re

# Définir le chemin 
Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Parent_dir = os.path.dirname(Base_dir)
Dossier_Mining = os.path.join(Parent_dir, "Graphe pattern  mining")

# Paramètres
SEUIL_SUPPORT = 40
MAX_EXEMPLES = 4

def visualiser_frequents_avec_vocabulaire(version_active):
    print(f"\n Lancement de l'extraction des séquences TraMineR (Version : {version_active.upper})")

    #  Détermination du dossier selon la version
    if version_active == 'complet':
        dossier_version = os.path.join(Dossier_Mining, "resultats_avec_tous_les_attributs")
        attributs_a_garder = ['docTimeRel', 'eventType', 'contextualModality', 'polarity']
    elif version_active == 'sans_dct':
        dossier_version = os.path.join(Dossier_Mining, "resultats_sans_attribut_doctimrel")
        attributs_a_garder = ['eventType', 'contextualModality', 'polarity']
    elif version_active == 'sans_polarity':
        dossier_version = os.path.join(Dossier_Mining, "resultats_sans_attribut_polarity")
        attributs_a_garder = ['docTimeRel', 'eventType', 'contextualModality']
    elif version_active == 'sans_eventtype':
        dossier_version = os.path.join(Dossier_Mining, "resultats_sans_attribut_eventype")
        attributs_a_garder = ['docTimeRel', 'contextualModality', 'polarity']
    elif version_active == 'fusion':
        dossier_version = os.path.join(Dossier_Mining, "resultats_fusion_event_clinentity")
        attributs_a_garder = ['docTimeRel', 'eventType', 'contextualModality', 'polarity']
    elif version_active == 'coref':
        dossier_version = os.path.join(Dossier_Mining, "avec_coref")
        attributs_a_garder = ['docTimeRel', 'eventType', 'contextualModality', 'polarity']
    else:
        dossier_version = os.path.join(Dossier_Mining, "resultats_avec_tous_les_attributs")
        attributs_a_garder = ['docTimeRel', 'eventType', 'contextualModality', 'polarity']

    # Dossier d'entrée
    Fichier_Resultats = os.path.join(dossier_version, "resultats_bruts_gspan.txt")
    Lexique_Noeuds = os.path.join(dossier_version, "dictionnaire_noeuds.csv")
    Lexique_Aretes = os.path.join(dossier_version, "dictionnaire_aretes.csv")

    if version_active == 'coref':
        Fichier_Donnees_Brutes = os.path.join(dossier_version, "balises_relations_attributs_coref.csv")
    else:
        Fichier_Donnees_Brutes = os.path.join(dossier_version, "balises_relations_attributs.csv")

    # Dossier de sortie
    Dossier_Sortie_Docs = os.path.join(dossier_version, "motifs_vocabulaire_support40")
    Fichier_CSV_Exhaustif = os.path.join(dossier_version, "motifs_frequents_mots.csv")
    Fichier_CSV_Sequences = os.path.join(dossier_version, "motifs_frequents_sequences_traminer.csv")

    if not os.path.exists(Dossier_Sortie_Docs): 
        os.makedirs(Dossier_Sortie_Docs)
        
    if not os.path.exists(Fichier_Resultats):
        print(f" Erreur : {Fichier_Resultats} introuvable.")
        return

    def creer_label_noeud(row, prefix="source"):
        tag = str(row.get(f'{prefix}_tag', ''))
        
        if version_active == 'fusion':
            has_event = re.search(r'\bEVENT\b', tag)
            has_clinentity = re.search(r'\bCLINENTITY\b', tag)
            if has_event and has_clinentity:
                tag = 'EVENT'
                
        if tag == 'TIMEX3':
            timex_val = str(row.get(f'{prefix}_timexType', '')).strip()
            if timex_val and timex_val != "Non concerné": return timex_val
            return "TIMEX3"
        
        label_parts = [tag]
        for attr in attributs_a_garder:
            val = str(row.get(f'{prefix}_{attr}', "Non concerné")).strip()
            if val and val != "Non concerné" and val != "nan":
                label_parts.append(val)
        return "_".join(label_parts)

    def determiner_couleurs(label_abstrait):
        lbl = label_abstrait.upper()
        if any(k in lbl for k in ['DURATION', 'DATE', 'TIME', 'FREQUENCY', 'TIMEX']):
            return {'fillcolor': '#F39C12', 'color': '#D68910', 'fontcolor': 'white'}
        elif 'CLINENTITY' in lbl:
            return {'fillcolor': '#8E44AD', 'color': '#732D91', 'fontcolor': 'white'}
        elif 'EVENT' in lbl:
            return {'fillcolor': '#16A085', 'color': '#117A65', 'fontcolor': 'white'}
        else:
            return {'fillcolor': '#34495E', 'color': '#2C3E50', 'fontcolor': 'white'}

    df_noeuds = pd.read_csv(Lexique_Noeuds)
    df_aretes = pd.read_csv(Lexique_Aretes)
    dict_noeuds = dict(zip(df_noeuds['ID_gSpan'].astype(str), df_noeuds['Super_Label']))
    dict_aretes = dict(zip(df_aretes['ID_gSpan'].astype(str), df_aretes['Relation']))

    print(" -> Construction des graphes en mémoire...")
    df_brut = pd.read_csv(Fichier_Donnees_Brutes, keep_default_na=False)
    docs_list = list(df_brut.groupby('doc_id').groups.keys())
    
    #  Création et export du dictionnaire des documents 
    Chemin_Dict_Docs = os.path.join(dossier_version, "dictionnaire_documents.csv")
    df_dict_docs = pd.DataFrame({
        't_index': range(len(docs_list)),
        'Document': docs_list
    })
    df_dict_docs.to_csv(Chemin_Dict_Docs, index=False, encoding='utf-8')
    print(f" Dictionnaire des documents généré : {Chemin_Dict_Docs}")
    

    doc_graphs = {}
    for _, row in df_brut.iterrows():
        doc = row['doc_id']
        
        if doc not in doc_graphs: doc_graphs[doc] = nx.MultiDiGraph()
        
        mention_src = str(row.get('mention_source', 'non détecté')).strip()
        orig_src_id = str(row.get('source_id', f"{row.get('source_texte', '')}_{row.get('source_tag', '')}")).strip()
        if mention_src not in ["singleton", "non détecté", "nan", ""]:
            src_id = f"{doc}_{mention_src}"
        else:
            src_id = f"{doc}_{orig_src_id}"
            
        mention_tgt = str(row.get('mention_target', 'non détecté')).strip()
        orig_tgt_id = str(row.get('target_id', f"{row.get('target_texte', '')}_{row.get('target_tag', '')}")).strip()
        if mention_tgt not in ["singleton", "non détecté", "nan", ""]:
            tgt_id = f"{doc}_{mention_tgt}"
        else:
            tgt_id = f"{doc}_{orig_tgt_id}"
        
        src_txt = str(row.get('source_texte', '')).strip()
        src_tag = creer_label_noeud(row, "source")
        
        tgt_txt = str(row.get('target_texte', '')).strip()
        tgt_tag = creer_label_noeud(row, "target")
        
        rel = str(row.get('relation_type', '')).strip()
        
        doc_graphs[doc].add_node(src_id, tag=src_tag, texte=src_txt)
        doc_graphs[doc].add_node(tgt_id, tag=tgt_tag, texte=tgt_txt)
        doc_graphs[doc].add_edge(src_id, tgt_id, rel=rel)

    motifs = []
    motif_courant = None

    with open(Fichier_Resultats, 'r', encoding='utf-8') as f:
        lignes = f.readlines()
        
    for ligne in lignes:
        ligne = ligne.strip()
        if ligne.startswith("t #"):
            if motif_courant is not None:
                motifs.append(motif_courant)
            motif_id = ligne.split()[-1]
            motif_courant = {'id': motif_id, 'graph': nx.MultiDiGraph(), 'support': 0, 'where': [], 'dfs_edges': []}
            
        elif ligne.startswith("v ") and motif_courant:
            parts = ligne.split()
            noeud_local_id = int(parts[1])
            label_gspan = parts[2]
            motif_courant['graph'].add_node(noeud_local_id, tag=dict_noeuds.get(label_gspan, ""))
            
        elif ligne.startswith("e ") and motif_courant:
            parts = ligne.split()
            src = int(parts[1])
            tgt = int(parts[2])
            label_gspan = parts[3]
            nom_relation = dict_aretes.get(label_gspan, "")
            motif_courant['graph'].add_edge(src, tgt, rel=nom_relation)
            motif_courant['dfs_edges'].append((src, tgt, nom_relation))
            
        elif ligne.startswith("Support:") and motif_courant:
            motif_courant['support'] = int(ligne.split()[1])
            
        elif ligne.startswith("where:") and motif_courant:
            where_str = ligne.replace("where: [", "").replace("]", "")
            motif_courant['where'] = [int(x.strip()) for x in where_str.split(",") if x.strip()]

    if motif_courant is not None:
        motifs.append(motif_courant)

    motifs_frequents = [m for m in motifs if m['support'] >= SEUIL_SUPPORT]
    motifs_frequents = sorted(motifs_frequents, key=lambda x: x['support'], reverse=True)
    
    print(f" {len(motifs_frequents)} motifs correspondent au critère (>= {SEUIL_SUPPORT} docs).")
    
    def nm(n1, n2):
        return n1.get('tag') == n2.get('tag')

    def em(d1, d2):
        rels_doc = [data.get('rel') for key, data in d1.items()]
        rels_motif = [data.get('rel') for key, data in d2.items()]
        for r in rels_motif:
            if r in rels_doc:
                rels_doc.remove(r)
            else:
                return False
        return True

    lignes_csv_exhaustif = []
    lignes_csv_sequences = [] 

    for i, m in enumerate(motifs_frequents):
        structure_abstraite = []
        for u, v, rel in m['dfs_edges']:
            lbl_u = m['graph'].nodes[u]['tag']
            lbl_v = m['graph'].nodes[v]['tag']
            structure_abstraite.append(f"[{lbl_u}] --({rel})--> [{lbl_v}]")
        texte_structure_abstraite = " | ".join(structure_abstraite)
        
        instances_capturees = [] 
        docs_illustres = set() 
        
        for doc_idx in m['where']:
            if doc_idx < len(docs_list):
                doc_name = docs_list[doc_idx]
                G_doc = doc_graphs[doc_name]
                G_motif = m['graph']
                
                matcher = iso.MultiDiGraphMatcher(G_doc, G_motif, node_match=nm, edge_match=em)
                
                for match in matcher.subgraph_isomorphisms_iter():
                    inv_match = {v: k for k, v in match.items()}
                    
                    exemples_mots_csv = []
                    ligne_sequence = {
                        'ID_Motif': m['id'],
                        'Support': m['support'],
                        'Document': doc_name,
                        'Structure_Abstraite': texte_structure_abstraite
                    }
                    
                    dernier_v_id = None
                    idx_mot = 1
                    idx_rel = 1
                    aretes_textes = [] 
                    
                    for index_arete, (u, v, rel) in enumerate(m['dfs_edges']):
                        mot_u = G_doc.nodes[inv_match[u]]['texte']
                        mot_v = G_doc.nodes[inv_match[v]]['texte']
                        
                        exemples_mots_csv.append(f'"{mot_u}" --({rel})--> "{mot_v}"')
                        aretes_textes.append(f"{mot_u}-[{rel}]->{mot_v}")
                        
                        if index_arete == 0:
                            ligne_sequence[f'Mot_{idx_mot}'] = mot_u
                            ligne_sequence[f'Relation_{idx_rel}'] = rel
                            idx_mot += 1
                            idx_rel += 1
                            ligne_sequence[f'Mot_{idx_mot}'] = mot_v
                        else:
                            if u == dernier_v_id:
                                ligne_sequence[f'Relation_{idx_rel}'] = rel
                                idx_rel += 1
                                idx_mot += 1
                                ligne_sequence[f'Mot_{idx_mot}'] = mot_v
                            else:
                                ligne_sequence[f'Relation_{idx_rel}'] = "[RETOUR]"
                                idx_rel += 1
                                idx_mot += 1
                                ligne_sequence[f'Mot_{idx_mot}'] = mot_u
                                
                                ligne_sequence[f'Relation_{idx_rel}'] = rel
                                idx_rel += 1
                                idx_mot += 1
                                ligne_sequence[f'Mot_{idx_mot}'] = mot_v
                                
                        dernier_v_id = v
                        
                    aretes_textes.sort()
                    signature_match = " | ".join(aretes_textes)
                    
                    deja_present = False
                    for existing_row in lignes_csv_exhaustif:
                        if existing_row['Document'] == doc_name and existing_row.get('_Signature') == signature_match and existing_row['ID_Motif'] == m['id']:
                            deja_present = True
                            break
                            
                    if not deja_present:
                        lignes_csv_exhaustif.append({
                            'ID_Motif': m['id'],
                            'Support': m['support'],
                            'Document': doc_name,
                            'Structure_Abstraite': texte_structure_abstraite,
                            'Exemples_du_Texte': " | ".join(exemples_mots_csv),
                            '_Signature': signature_match
                        })
                        lignes_csv_sequences.append(ligne_sequence)
                    
                    if len(instances_capturees) < MAX_EXEMPLES and not deja_present:
                        if doc_name not in docs_illustres:
                            chemin_courant = {}
                            num_exemple = len(instances_capturees) + 1
                            for d_node, m_node in match.items():
                                mot = G_doc.nodes[d_node]['texte']
                                chemin_courant[m_node] = f'"{mot}" ({num_exemple}, {doc_name})'
                            instances_capturees.append(chemin_courant)
                            docs_illustres.add(doc_name)

        noms_versions = {
            'complet': 'complète',
            'sans_dct': 'sans DCT',
            'sans_polarity': 'sans polarité',
            'sans_eventtype': "sans type d'événement",
            'fusion': 'avec fusion (EVENT/CLINENTITY)',
            'coref': 'avec coréférence'
        }
        titre_version = noms_versions.get(version_active, version_active)
        
        titre = f"Motif n°{m['id']}\n(Présent dans {m['support']} documents)\n(Version : {titre_version})"
        
        dot = graphviz.Digraph(
            name=f"motif_{m['id']}",
            format='png',
            engine='fdp',
            graph_attr={'overlap': 'scale', 'splines': 'true', 'sep': '+1.5', 'K': '2.0', 'dpi': '300', 'label': titre, 'labelloc': 't', 'fontsize': '18', 'fontname': 'Helvetica-Bold', 'fontcolor': '#2C3E50', 'pad': '1.0'},
            node_attr={'shape': 'box', 'style': 'filled,rounded', 'fontname': 'Helvetica', 'margin': '0.3,0.15'},
            edge_attr={'fontname': 'Helvetica-Bold', 'fontsize': '11', 'color': '#34495E', 'fontcolor': '#C0392B', 'arrowsize': '1.2', 'len': '3.0'}
        )
        
        for nid, data in m['graph'].nodes(data=True):
            nlabel_abstrait = data['tag']
            couleurs = determiner_couleurs(nlabel_abstrait)
            
            lignes_html = []
            for instance in instances_capturees:
                lignes_html.append(instance.get(nid, '"Entité" (?, ?)'))
            if not lignes_html:
                lignes_html = ['"Aucun exemple"']
                
            mots_html = "<BR/>".join(lignes_html)
            html_label = f'<<FONT POINT-SIZE="14"><I>{nlabel_abstrait.replace("_", " ")}</I></FONT><BR/><BR/><B>{mots_html}</B>>'
            
            dot.node(str(nid), label=html_label, fillcolor=couleurs['fillcolor'], color=couleurs['color'], fontcolor=couleurs['fontcolor'], penwidth='2')
            
        for src, tgt, data in m['graph'].edges(data=True):
            dot.edge(str(src), str(tgt), label=f" {data['rel']} ")

        nom_fichier_base = os.path.join(Dossier_Sortie_Docs, f"motif_n°{m['id']}_support{m['support']}")
        try:
            dot.render(nom_fichier_base, cleanup=True)
        except Exception as e:
            print(f" Erreur motif {m['id']}: {e}")

    if lignes_csv_exhaustif:
        df_ex = pd.DataFrame(lignes_csv_exhaustif)
        df_ex = df_ex.drop(columns=['_Signature'], errors='ignore') 
        df_ex.to_csv(Fichier_CSV_Exhaustif, index=False, encoding='utf-8')
        
    if lignes_csv_sequences:
        df_sequences = pd.DataFrame(lignes_csv_sequences)
        cols_base = ['ID_Motif', 'Support', 'Document', 'Structure_Abstraite']
        
        max_mot = 0
        for c in df_sequences.columns:
            if c.startswith('Mot_'):
                num = int(c.split('_')[1])
                if num > max_mot:
                    max_mot = num
                    
        cols_etapes = []
        for i in range(1, max_mot + 1):
            if f'Mot_{i}' in df_sequences.columns: 
                cols_etapes.append(f'Mot_{i}')
            if f'Relation_{i}' in df_sequences.columns: 
                cols_etapes.append(f'Relation_{i}')
        
        df_sequences = df_sequences[cols_base + cols_etapes]
        df_sequences.to_csv(Fichier_CSV_Sequences, index=False, encoding='utf-8')

    print(f" {len(motifs_frequents)} graphes PNG générés dans le dossier associé.")
    print(f" Fichier CSV exhaustif brut  prêt.")
    print(f" Fichier CSV exhaustif lissé en séquences pour TraMineR prêt.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', type=str, default='complet')
    args = parser.parse_args()
    
    visualiser_frequents_avec_vocabulaire(args.version)