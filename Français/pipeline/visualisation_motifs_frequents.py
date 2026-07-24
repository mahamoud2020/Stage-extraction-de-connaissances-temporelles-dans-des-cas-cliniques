import os
import pandas as pd
import graphviz
import networkx as nx
import networkx.algorithms.isomorphism as iso

# Définir le chemin
Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Parent_dir = os.path.dirname(Base_dir) # On remonte dans l'arborescence
Dossier_Mining = os.path.join(Parent_dir, "Graphe pattern  mining")

# Nouveau dossier pour cette version
Dossier_Ablation = os.path.join(Dossier_Mining, "resultats_sans_attribut_doctimrel")

# Dossier dédié pour le stockage des images
Dossier_Motifs = os.path.join(Dossier_Ablation, "motifs_vocabulaire_support40_sans_doctimrel")

# Fichier CSV pour l'export des instances
Fichier_CSV_Instances = os.path.join(Dossier_Ablation, "motifs_frequents_mots_sans_doctimrel.csv")

# Fichiers de données (Dictionnaires et résultats générés sans DCT)
Fichier_Resultats = os.path.join(Dossier_Ablation, "resultats_bruts_gspan_sans_doctimrel.txt")
Lexique_Noeuds = os.path.join(Dossier_Ablation, "dictionnaire_noeuds_sans_doctimrel.csv")
Lexique_Aretes = os.path.join(Dossier_Ablation, "dictionnaire_aretes_sans_doctimrel.csv")

# Le fichier contenant les données brutes reste le même (Dossier_Mining)
Fichier_Donnees = os.path.join(Dossier_Mining, "balises_relations_attributs.csv")

# Paramètres 
SEUIL_SUPPORT = 40  # On ne garde que les motifs présents dans au moins 40 documents
MAX_EXEMPLES = 4    # Nombre de chaînes à afficher dans les bulles PNG pour garder l'image lisible

def creer_label_noeud(row, prefix="source"):
    """Reconstruit le label abstrait en ignorant volontairement docTimeRel"""
    tag = str(row.get(f'{prefix}_tag', ''))
    if tag == 'TIMEX3':
        timex_val = str(row.get(f'{prefix}_timexType', '')).strip()
        if timex_val and timex_val not in ["Non concerné", "nan", "N/A", "None"]: return timex_val
        return "TIMEX3"
    
    label_parts = [tag]
    
    # --- MODIFICATION ICI : Retrait de 'docTimeRel' pour l'ablation ---
    attributs = ['eventType', 'contextualModality', 'polarity']
    
    for attr in attributs:
        col_name = f'{prefix}_{attr}'
        if col_name in row:
            val = str(row[col_name]).strip()
            if val and val not in ["Non concerné", "nan", "None"]:
                label_parts.append(val)
    return "_".join(label_parts)

def determiner_couleurs(label_abstrait):
    """Associe des couleurs pour Graphviz selon la sémantique de l'entité"""
    lbl = label_abstrait.upper()
    if any(k in lbl for k in ['DURATION', 'DATE', 'TIME', 'FREQUENCY', 'TIMEX']): return {'fillcolor': '#F39C12', 'color': '#D68910', 'fontcolor': 'white'}
    elif 'CLINENTITY' in lbl: return {'fillcolor': '#8E44AD', 'color': '#732D91', 'fontcolor': 'white'}
    elif 'EVENT' in lbl: return {'fillcolor': '#16A085', 'color': '#117A65', 'fontcolor': 'white'}
    else: return {'fillcolor': '#34495E', 'color': '#2C3E50', 'fontcolor': 'white'}

def visualiser_frequents_avec_vocabulaire():
    
    if not os.path.exists(Dossier_Motifs): os.makedirs(Dossier_Motifs)

    # Chargement des dictionnaires
    df_noeuds = pd.read_csv(Lexique_Noeuds)
    df_aretes = pd.read_csv(Lexique_Aretes)
    dict_noeuds = dict(zip(df_noeuds['ID_gSpan'].astype(str), df_noeuds['Super_Label']))
    dict_aretes = dict(zip(df_aretes['ID_gSpan'].astype(str), df_aretes['Relation']))

    df_brut = pd.read_csv(Fichier_Donnees, keep_default_na=False)
    docs_list = list(df_brut.groupby('doc_id').groups.keys())
    
    doc_graphs = {}
    for _, row in df_brut.iterrows():
        doc = row['doc_id']
        # On utilise MultiDiGraph pour ne pas écraser les flèches parallèles 
        if doc not in doc_graphs: doc_graphs[doc] = nx.MultiDiGraph()
        
        src_txt = str(row.get('source_texte', '')).strip()
        src_tag = creer_label_noeud(row, "source")
        src_id = str(row.get('source_id', f"{src_txt}_{src_tag}")).strip()
        
        tgt_txt = str(row.get('target_texte', '')).strip()
        tgt_tag = creer_label_noeud(row, "target")
        tgt_id = str(row.get('target_id', f"{tgt_txt}_{tgt_tag}")).strip()
        
        rel = str(row.get('relation_type', '')).strip()
        
        doc_graphs[doc].add_node(src_id, tag=src_tag, texte=src_txt)
        doc_graphs[doc].add_node(tgt_id, tag=tgt_tag, texte=tgt_txt)
        doc_graphs[doc].add_edge(src_id, tgt_id, rel=rel)

    motifs = []
    motif_courant = None
    with open(Fichier_Resultats, 'r', encoding='utf-8') as f:
        for ligne in f:
            ligne = ligne.strip()
            if ligne.startswith("t #"):
                if motif_courant: motifs.append(motif_courant)
                # MultiDiGraph ici aussi 
                motif_courant = {'id': ligne.split()[-1], 'graph': nx.MultiDiGraph(), 'support': 0, 'where': []}
            elif ligne.startswith("v ") and motif_courant:
                parts = ligne.split()
                motif_courant['graph'].add_node(int(parts[1]), tag=dict_noeuds.get(parts[2], ""))
            elif ligne.startswith("e ") and motif_courant:
                parts = ligne.split()
                motif_courant['graph'].add_edge(int(parts[1]), int(parts[2]), rel=dict_aretes.get(parts[3], ""))
            elif ligne.startswith("Support:") and motif_courant:
                motif_courant['support'] = int(ligne.split()[1])
            elif ligne.startswith("where:") and motif_courant:
                motif_courant['where'] = [int(x) for x in ligne.replace("where: [", "").replace("]", "").split(",") if x.strip()]
    if motif_courant: motifs.append(motif_courant)

    motifs_frequents = [m for m in motifs if m['support'] >= SEUIL_SUPPORT]
    motifs_frequents = sorted(motifs_frequents, key=lambda x: x['support'], reverse=True)

    print(f" -> {len(motifs_frequents)} motifs correspondent au critère (>= {SEUIL_SUPPORT} docs).")

    # Fonction pour comparer les étiquettes des nœuds
    def nm(n1, n2):
        return n1.get('tag') == n2.get('tag')

    # Fonction pour comparer les "paquets" de flèches entre deux nœuds
    def em(d1, d2):
        rels_doc = [data.get('rel') for key, data in d1.items()]
        rels_motif = [data.get('rel') for key, data in d2.items()]
        
        # On vérifie que chaque flèche du motif existe bien dans le document
        for r in rels_motif:
            if r in rels_doc:
                rels_doc.remove(r) # On la retire pour gérer les éventuels doublons
            else:
                return False
        return True

    lignes_csv_exhaustif = []

    for i, m in enumerate(motifs_frequents):
        print(f" Analyse du motif {m['id']} (Support: {m['support']})")
        
        # Construction de la structure abstraite sous forme de texte pour le CSV
        structure_abstraite = []
        for u, v, data in m['graph'].edges(data=True):
            lbl_u = m['graph'].nodes[u]['tag']
            lbl_v = m['graph'].nodes[v]['tag']
            structure_abstraite.append(f"[{lbl_u}] --({data['rel']})--> [{lbl_v}]")
        texte_structure_abstraite = " | ".join(structure_abstraite)
        
        instances_capturees = [] # Limité à 4 pour le PNG
        
        # Parcours de tous les documents où le motif apparaît
        for doc_idx in m['where']:
            if doc_idx < len(docs_list):
                doc_name = docs_list[doc_idx]
                G_doc = doc_graphs[doc_name]
                G_motif = m['graph']
                
                # Passage du calque sur le document (avec le moteur MultiDiGraph)
                matcher = iso.MultiDiGraphMatcher(G_doc, G_motif, node_match=nm, edge_match=em)
                for match in matcher.subgraph_isomorphisms_iter():
                    
                    inv_match = {v: k for k, v in match.items()}
                    
                    # Extraction pour le fichier CSV exhaustif
                    exemples_mots_csv = []
                    for u, v, data in m['graph'].edges(data=True):
                        mot_u = G_doc.nodes[inv_match[u]]['texte']
                        mot_v = G_doc.nodes[inv_match[v]]['texte']
                        exemples_mots_csv.append(f'"{mot_u}" --({data["rel"]})--> "{mot_v}"')
                        
                    lignes_csv_exhaustif.append({
                        'ID_Motif': m['id'],
                        'Support': m['support'],
                        'Document': doc_name,
                        'Structure_Abstraite': texte_structure_abstraite,
                        'Exemples_du_Texte': " | ".join(exemples_mots_csv)
                    })
                    
                    # Extraction pour l'image PNG 
                    if len(instances_capturees) < MAX_EXEMPLES:
                        chemin_courant = {}
                        num_exemple = len(instances_capturees) + 1
                        
                        for d_node, m_node in match.items():
                            mot = G_doc.nodes[d_node]['texte']
                            chemin_courant[m_node] = f'"{mot}" ({num_exemple}, {doc_name})'
                            
                        instances_capturees.append(chemin_courant)
                        
                    break # Dès qu'on trouve 1 occurrence, on passe au doc suivant

        titre = f"Motif n°{m['id']}\n(Présent dans {m['support']} documents sur {len(docs_list)}\n)"
        dot = graphviz.Digraph(name=f"motif_{m['id']}", format='png', engine='fdp',
            graph_attr={
                'overlap': 'scale', 
                'splines': 'true', 
                'sep': '+2.5',      
                'K': '2.5',         
                'label': titre, 
                'labelloc': 't',    
                'fontsize': '24', 
                'fontname': 'Helvetica-Bold', 
                'pad': '1.0'
            },
            node_attr={'shape': 'box', 'style': 'filled,rounded', 'fontname': 'Helvetica', 'margin': '0.3,0.2'},
            edge_attr={'fontname': 'Helvetica-Bold', 'fontsize': '14', 'color': '#2C3E50', 'fontcolor': '#C0392B', 'penwidth': '2.0', 'arrowsize': '1.5', 'len': '4.0'}
        )
        
        for nid, data in m['graph'].nodes(data=True):
            tag_abstrait = data['tag']
            couleurs = determiner_couleurs(tag_abstrait)
            
            lignes_html = []
            for instance in instances_capturees:
                lignes_html.append(instance.get(nid, '"Entité" (?, ?)'))
                
            if not lignes_html:
                lignes_html = ['"Aucun exemple"']
                
            mots_html = "<BR/>".join(lignes_html)
            html_label = f'<<FONT POINT-SIZE="14"><I>{tag_abstrait.replace("_", " ")}</I></FONT><BR/><BR/><B>{mots_html}</B>>'
            
            dot.node(str(nid), label=html_label, fillcolor=couleurs['fillcolor'], color=couleurs['color'], fontcolor=couleurs['fontcolor'], penwidth='2')
            
        for src, tgt, data in m['graph'].edges(data=True):
            dot.edge(str(src), str(tgt), label=f" {data['rel']} ")

        try:
            dot.render(os.path.join(Dossier_Motifs, f"motif_dict_id{m['id']}_support{m['support']}"), cleanup=True)
        except Exception as e:
            print(f" Erreur du motif {m['id']}: {e}")

    if lignes_csv_exhaustif:
        df_export = pd.DataFrame(lignes_csv_exhaustif)
        df_export.to_csv(Fichier_CSV_Instances, index=False, encoding='utf-8')
    
    print(f"Les graphes PNG ont été générés dans {Dossier_Motifs}")
    print(f"\n Le fichier CSV complet a été sauvegardé dans {Fichier_CSV_Instances}")

if __name__ == "__main__":
    visualiser_frequents_avec_vocabulaire()