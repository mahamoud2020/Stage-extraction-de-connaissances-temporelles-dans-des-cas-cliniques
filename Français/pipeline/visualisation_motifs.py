import os
import pandas as pd
import graphviz
import networkx as nx
import networkx.algorithms.isomorphism as iso

Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Parent_dir = os.path.dirname(Base_dir)
Dossier_Mining = os.path.join(Parent_dir, "Graphe pattern  mining")

# Nouveau dossier pour cette version
Dossier_Ablation = os.path.join(Dossier_Mining, "resultats_sans_attribut_doctimrel")

Fichier_Resultats = os.path.join(Dossier_Ablation, "resultats_bruts_gspan_sans_doctimrel.txt")
Lexique_Noeuds = os.path.join(Dossier_Ablation, "dictionnaire_noeuds_sans_doctimrel.csv")
Lexique_Aretes = os.path.join(Dossier_Ablation, "dictionnaire_aretes_sans_doctimrel.csv")

# Le fichier de données est dans Graphe pattern mining
Fichier_Donnees_Brutes = os.path.join(Dossier_Mining, "balises_relations_attributs.csv")

# Nouveau dossier de sortie
Dossier_Sortie_Docs = os.path.join(Dossier_Ablation, "graphes_motifs_sans_doctimrel")

def creer_label_noeud(row, prefix="source"):
    """Reconstruit le label abstrait complet d'un noeud à partir de ses attributs"""
    tag = str(row.get(f'{prefix}_tag', ''))
    if tag == 'TIMEX3':
        timex_val = str(row.get(f'{prefix}_timexType', '')).strip()
        if timex_val and timex_val != "Non concerné": return timex_val
        return "TIMEX3"
    
    label_parts = [tag]
    
    # Suppression de l'attribut 'docTimeRel'
    attributs = ['eventType', 'contextualModality', 'polarity']
    
    for attr in attributs:
        val = str(row.get(f'{prefix}_{attr}', "Non concerné")).strip()
        if val and val != "Non concerné" and val != "nan":
            label_parts.append(val)
    return "_".join(label_parts)

def determiner_couleurs(label_abstrait):
    """Associe des couleurs spécifiques selon la catégorie sémantique du noeud"""
    lbl = label_abstrait.upper()
    if any(k in lbl for k in ['DURATION', 'DATE', 'TIME', 'FREQUENCY', 'TIMEX']):
        return {'fillcolor': '#F39C12', 'color': '#D68910', 'fontcolor': 'white'} # Orange pour le temps
    elif 'CLINENTITY' in lbl:
        return {'fillcolor': '#8E44AD', 'color': '#732D91', 'fontcolor': 'white'} # Violet pour l'entité clinique
    elif 'EVENT' in lbl:
        return {'fillcolor': '#16A085', 'color': '#117A65', 'fontcolor': 'white'} # Vert pour les événements
    else:
        return {'fillcolor': '#34495E', 'color': '#2C3E50', 'fontcolor': 'white'} # Gris pour le reste

def visualiser_motifs():
    print(f" Lancement de la visualisation des graphes dans : {Dossier_Mining}")
    if not os.path.exists(Dossier_Sortie_Docs): 
        os.makedirs(Dossier_Sortie_Docs)
        
    if not os.path.exists(Fichier_Resultats):
        print(f" Erreur : {Fichier_Resultats} introuvable.")
        return

    df_noeuds = pd.read_csv(Lexique_Noeuds)
    df_aretes = pd.read_csv(Lexique_Aretes)
    dict_noeuds = dict(zip(df_noeuds['ID_gSpan'].astype(str), df_noeuds['Super_Label']))
    dict_aretes = dict(zip(df_aretes['ID_gSpan'].astype(str), df_aretes['Relation']))

    
    df_brut = pd.read_csv(Fichier_Donnees_Brutes, keep_default_na=False)
    docs_list = list(df_brut.groupby('doc_id').groups.keys())
    
    doc_graphs = {}
    for _, row in df_brut.iterrows():
        doc = row['doc_id']
        if doc not in doc_graphs: doc_graphs[doc] = nx.DiGraph()
        
        src_id = str(row.get('source_id', f"{row['source_texte']}_{row['source_tag']}")).strip()
        tgt_id = str(row.get('target_id', f"{row['target_texte']}_{row['target_tag']}")).strip()
        
        src_txt = str(row['source_texte']).strip()
        src_tag = creer_label_noeud(row, "source")
        
        tgt_txt = str(row['target_texte']).strip()
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
            motif_courant = {'id': motif_id, 'graph': nx.DiGraph(), 'support': 0, 'where': []}
            
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
            
        elif ligne.startswith("Support:") and motif_courant:
            motif_courant['support'] = int(ligne.split()[1])
            
        elif ligne.startswith("where:") and motif_courant:
            where_str = ligne.replace("where: [", "").replace("]", "")
            motif_courant['where'] = [int(x.strip()) for x in where_str.split(",") if x.strip()]

    if motif_courant is not None:
        motifs.append(motif_courant)

    # Tri des motifs par fréquence d'apparition (support décroissant)
    motifs = sorted(motifs, key=lambda x: x['support'], reverse=True)
    
    print(f" Dessin de {len(motifs)} motifs...")
    nm = iso.categorical_node_match('tag', 'UNKNOWN')
    em = iso.categorical_edge_match('rel', 'UNKNOWN')

    # Dictionnaire pour répartir l'utilisation des documents sources
    compteur_utilisation_docs = {doc: 0 for doc in docs_list}

    for i, m in enumerate(motifs):
        candidats_valides = []
        
        for doc_idx in m['where']:
            if doc_idx < len(docs_list):
                doc_name = docs_list[doc_idx]
                G_doc = doc_graphs[doc_name]
                G_motif = m['graph']
                
                # Cherche le motif abstrait dans le graphe réel du document
                matcher = iso.DiGraphMatcher(G_doc, G_motif, node_match=nm, edge_match=em)
                for match in matcher.subgraph_isomorphisms_iter():
                    mots_pour_ce_candidat = {}
                    for d_node, m_node in match.items():
                        mots_pour_ce_candidat[m_node] = G_doc.nodes[d_node]['texte']
                        
                    candidats_valides.append({
                        'nom': doc_name,
                        'mots': mots_pour_ce_candidat,
                        'score_utilisation': compteur_utilisation_docs[doc_name]
                    })
                    break # Une occurrence trouvée suffit pour ce document

        if candidats_valides:
            # Privilégie un document qui n'a pas encore été beaucoup utilisé comme exemple
            candidats_valides = sorted(candidats_valides, key=lambda x: x['score_utilisation'])
            meilleur_candidat = candidats_valides[0]
            doc_exemple = meilleur_candidat['nom']
            mots_trouves = meilleur_candidat['mots']
            compteur_utilisation_docs[doc_exemple] += 1
        else:
            doc_exemple = "Inconnu"
            mots_trouves = {}

        titre = f"Motif n°{m['id']} (Présent dans {m['support']} documents)\nExemple tiré du document : {doc_exemple}"
        
        dot = graphviz.Digraph(
            name=f"motif_{m['id']}",
            format='png',
            engine='fdp',         
            graph_attr={
                'overlap': 'scale',   
                'splines': 'true',    
                'sep': '+1.5',        
                'K': '2.0',           
                'dpi': '300',         
                'label': titre,
                'labelloc': 't',      
                'fontsize': '18',
                'fontname': 'Helvetica-Bold',
                'fontcolor': '#2C3E50',
                'pad': '1.0'
            },
            node_attr={
                'shape': 'box',
                'style': 'filled,rounded',
                'fontname': 'Helvetica',
                'margin': '0.3,0.15'
            },
            edge_attr={
                'fontname': 'Helvetica-Bold',
                'fontsize': '11',
                'color': '#34495E',
                'fontcolor': '#C0392B',
                'arrowsize': '1.2',
                'len': '3.0' 
            }
        )
        
        for nid, data in m['graph'].nodes(data=True):
            nlabel_abstrait = data['tag']
            mot_reel = mots_trouves.get(nid, "Entité") 
            couleurs = determiner_couleurs(nlabel_abstrait)
            
            # Label HTML avec le vrai mot en gras et la classe en dessous
            html_label = f'<<B>"{mot_reel}"</B><BR/><FONT POINT-SIZE="10">({nlabel_abstrait.replace("_", " ")})</FONT>>'
            
            dot.node(
                str(nid), 
                label=html_label,
                fillcolor=couleurs['fillcolor'],
                color=couleurs['color'],
                fontcolor=couleurs['fontcolor'],
                penwidth='2'
            )
            
        for src, tgt, data in m['graph'].edges(data=True):
            dot.edge(str(src), str(tgt), label=f" {data['rel']} ")

        nom_fichier_base = os.path.join(Dossier_Sortie_Docs, f"motif_n°{m['id']}_support{m['support']}")
        
        try:
            dot.render(nom_fichier_base, cleanup=True)
        except Exception as e:
            print(f" Erreur du motif {m['id']}: {e}")

    print(f"\n {len(motifs)} graphes ont été générés dans {Dossier_Sortie_Docs}")

if __name__ == "__main__":
    visualiser_motifs()