import os
import pandas as pd
import graphviz
import networkx as nx
import networkx.algorithms.isomorphism as iso


# Definir les chemins

Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Dossier_CSV = os.path.join(Base_dir, "data", "sortie_csv")
# dossier dédié pour le stockage de ce resultat
Dossier_Motifs = os.path.join(Dossier_CSV, "motifs_vocabulaire_support40")

# On pointe vers les bons fichiers 
Fichier_Resultats = os.path.join(Dossier_CSV, "resultats_bruts_gspan.txt")
Lexique_Noeuds = os.path.join(Dossier_CSV, "dictionnaire_noeuds.csv")
Lexique_Aretes = os.path.join(Dossier_CSV, "dictionnaire_aretes.csv")
Fichier_Donnees = os.path.join(Dossier_CSV, "graphes_attributs_gspan.csv")
if not os.path.exists(Fichier_Donnees):
    Fichier_Donnees = os.path.join(Dossier_CSV, "balises_relations_attributs.csv")


# Paramètres 

SEUIL_SUPPORT = 40  # On ne garde que les motifs présents dans au moins 40 documents
MAX_EXEMPLES = 4    # Nombre de chaînes  à afficher dans les bulles pour garder l'image lisible


def creer_label_noeud(row, prefix="source"):
    tag = str(row.get(f'{prefix}_tag', ''))
    if tag == 'TIMEX3':
        timex_val = str(row.get(f'{prefix}_timexType', '')).strip()
        if timex_val and timex_val not in ["Non concerné", "nan", "N/A", "None"]: return timex_val
        return "TIMEX3"
    
    label_parts = [tag]
    attributs = ['docTimeRel', 'eventType', 'contextualModality', 'polarity']
    for attr in attributs:
        col_name = f'{prefix}_{attr}'
        if col_name in row:
            val = str(row[col_name]).strip()
            if val and val not in ["Non concerné", "nan", "None"]:
                label_parts.append(val)
    return "_".join(label_parts)

def determiner_couleurs(label_abstrait):
    lbl = label_abstrait.upper()
    if any(k in lbl for k in ['DURATION', 'DATE', 'TIME', 'FREQUENCY', 'TIMEX']): return {'fillcolor': '#F39C12', 'color': '#D68910', 'fontcolor': 'white'}
    elif 'CLINENTITY' in lbl: return {'fillcolor': '#8E44AD', 'color': '#732D91', 'fontcolor': 'white'}
    elif 'EVENT' in lbl: return {'fillcolor': '#16A085', 'color': '#117A65', 'fontcolor': 'white'}
    else: return {'fillcolor': '#34495E', 'color': '#2C3E50', 'fontcolor': 'white'}



def visualiser_frequents_avec_vocabulaire():
    print(f" Lancement de l'analyse traçable des motifs (Seuil : >= {SEUIL_SUPPORT} docs)...")
    if not os.path.exists(Dossier_Motifs): os.makedirs(Dossier_Motifs)

    # Chargement des dictionnaires
    df_noeuds = pd.read_csv(Lexique_Noeuds)
    df_aretes = pd.read_csv(Lexique_Aretes)
    dict_noeuds = dict(zip(df_noeuds['ID_gSpan'].astype(str), df_noeuds['Super_Label']))
    dict_aretes = dict(zip(df_aretes['ID_gSpan'].astype(str), df_aretes['Relation']))

    # Construction des graphes de documents (NetworkX)
    print(" Construction des graphes originaux en mémoire...")
    df_brut = pd.read_csv(Fichier_Donnees, keep_default_na=False)
    docs_list = list(df_brut.groupby('doc_id').groups.keys())
    
    doc_graphs = {}
    for _, row in df_brut.iterrows():
        doc = row['doc_id']
        if doc not in doc_graphs: doc_graphs[doc] = nx.DiGraph()
        
        src_txt = str(row.get('source_texte', '')).strip()
        src_tag = creer_label_noeud(row, "source")
        # On utilise le mot + tag (sans index de ligne) pour garantir la connectivité 
        src_id = f"{src_txt}_{src_tag}" 
        
        tgt_txt = str(row.get('target_texte', '')).strip()
        tgt_tag = creer_label_noeud(row, "target")
        tgt_id = f"{tgt_txt}_{tgt_tag}"
        
        rel = str(row.get('relation_type', '')).strip()
        
        doc_graphs[doc].add_node(src_id, tag=src_tag, texte=src_txt)
        doc_graphs[doc].add_node(tgt_id, tag=tgt_tag, texte=tgt_txt)
        doc_graphs[doc].add_edge(src_id, tgt_id, rel=rel)

    # Chargement et filtrage des motifs (presence >= 40 documents)

    motifs = []
    motif_courant = None
    with open(Fichier_Resultats, 'r', encoding='utf-8') as f:
        for ligne in f:
            ligne = ligne.strip()
            if ligne.startswith("t #"):
                if motif_courant: motifs.append(motif_courant)
                motif_courant = {'id': ligne.split()[-1], 'graph': nx.DiGraph(), 'support': 0, 'where': []}
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

    #  Le Mapping pour capturer les Chemins Complets
    nm = iso.categorical_node_match('tag', 'UNKNOWN')
    em = iso.categorical_edge_match('rel', 'UNKNOWN')

    for i, m in enumerate(motifs_frequents):
        print(f" Analyse et dessin du motif {m['id']} (Support: {m['support']})")
        
        # Liste qui va contenir les chemins complètes 
        instances_capturees = []
        
        for doc_idx in m['where']:
            if len(instances_capturees) >= MAX_EXEMPLES:
                break # On s'arrête si on a assez d'exemples pour l'image
                
            if doc_idx < len(docs_list):
                doc_name = docs_list[doc_idx]
                G_doc = doc_graphs[doc_name]
                G_motif = m['graph']
                
                # Passage du calque sur le document
                matcher = iso.DiGraphMatcher(G_doc, G_motif, node_match=nm, edge_match=em)
                for match in matcher.subgraph_isomorphisms_iter():
                    # match = {id_noeud_doc: id_noeud_motif}
                    chemin_courant = {}
                    num_exemple = len(instances_capturees) + 1
                    
                    for d_node, m_node in match.items():
                        mot = G_doc.nodes[d_node]['texte']
                        # On formate : "mot" (num, doc)
                        chemin_courant[m_node] = f'"{mot}" ({num_exemple}, {doc_name})'
                        
                    instances_capturees.append(chemin_courant)
                    break # On prend 1 seul exemple par document pour favoriser la diversité

        # Dessin du Graphe 
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
            edge_attr={
                'fontname': 'Helvetica-Bold', 
                'fontsize': '14', 
                'color': '#2C3E50',     # Flèches plus sombres pour mieux contraster
                'fontcolor': '#C0392B', # Texte des flèches en rouge foncé
                'penwidth': '2.0',      # Lignes plus épaisses
                'arrowsize': '1.5',     # Pointes de flèches plus grosses
                'len': '4.0'            # Longueur de base des flèches beaucoup plus grande
            }
        )
        
        for nid, data in m['graph'].nodes(data=True):
            tag_abstrait = data['tag']
            couleurs = determiner_couleurs(tag_abstrait)
            
            # On récupère la ligne de texte de chaque exemple pour ce nœud précis
            lignes_html = []
            for instance in instances_capturees:
                lignes_html.append(instance.get(nid, '"Entité" (?, ?)'))
                
            if not lignes_html:
                lignes_html = ['"Aucun exemple"']
                
            # Construction du texte HTML 
            mots_html = "<BR/>".join(lignes_html)
            # L'étiquette (tag_abstrait) est  la première ligne, suivie des mots
            html_label = f'<<FONT POINT-SIZE="14"><I>{tag_abstrait.replace("_", " ")}</I></FONT><BR/><BR/><B>{mots_html}</B>>'
            
            dot.node(str(nid), label=html_label, fillcolor=couleurs['fillcolor'], color=couleurs['color'], fontcolor=couleurs['fontcolor'], penwidth='2')
            
        for src, tgt, data in m['graph'].edges(data=True):
            dot.edge(str(src), str(tgt), label=f" {data['rel']} ")

        try:
            dot.render(os.path.join(Dossier_Motifs, f"motif_dict_id{m['id']}_support{m['support']}"), cleanup=True)
        except Exception as e:
            print(f" Erreur du motif {m['id']}: {e}")

    print("\n" + "*"*60)
    print(f" Les graphes ont été générés dans :")
    print(f" {Dossier_Motifs}")
    

if __name__ == "__main__":
    visualiser_frequents_avec_vocabulaire()