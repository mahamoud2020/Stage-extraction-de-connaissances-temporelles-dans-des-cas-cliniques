import os
import pandas as pd
import graphviz
import networkx as nx
import networkx.algorithms.isomorphism as iso

# Définition des chemins
Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Dossier_CSV = os.path.join(Base_dir, "data", "sortie_csv")

Fichier_Resultats = os.path.join(Dossier_CSV, "resultats_bruts_gspan.txt")
Lexique_Noeuds = os.path.join(Dossier_CSV, "dictionnaire_noeuds.csv")
Lexique_Aretes = os.path.join(Dossier_CSV, "dictionnaire_aretes.csv")
Fichier_Donnees_Brutes = os.path.join(Dossier_CSV, "balises_relations_attributs.csv")

# Fichier de stockage des motifs de graphe
Dossier_Sortie_Docs = os.path.join(Dossier_CSV, "graphes_motifs")


def creer_label_noeud(row, prefix="source"):
    tag = str(row[f'{prefix}_tag'])
    if tag == 'TIMEX3':
        timex_val = str(row[f'{prefix}_timexType']).strip()
        if timex_val and timex_val != "Non concerné":
            return timex_val
        return "TIMEX3"
    
    label_parts = [tag]
    
    #  contextualModality
    attributs = ['docTimeRel', 'eventType', 'contextualModality', 'polarity']
    
    for attr in attributs:
        val = str(row[f'{prefix}_{attr}']).strip()
        if val and val != "Non concerné" and val != "nan":
            label_parts.append(val)
    return "_".join(label_parts)

def determiner_couleurs(label_abstrait):
    """ Détermine la couleur Graphviz en fonction du type  de l'entité """
    lbl = label_abstrait.upper()
    
    #  Temporalité : orange 
    if any(k in lbl for k in ['DURATION', 'DATE', 'TIME', 'FREQUENCY', 'TIMEX']):
        return {'fillcolor': '#F39C12', 'color': '#D68910', 'fontcolor': 'white'}
        
    #  Entité Clinique (CLINENTITY) : violet 
    elif 'CLINENTITY' in lbl:
        return {'fillcolor': '#8E44AD', 'color': '#732D91', 'fontcolor': 'white'}
        
    # ÉVENT : vert 
    elif 'EVENT' in lbl:
        return {'fillcolor': '#16A085', 'color': '#117A65', 'fontcolor': 'white'}
        
    # Par défaut : gris bleuté 
    else:
        return {'fillcolor': '#34495E', 'color': '#2C3E50', 'fontcolor': 'white'}

def visualiser_motifs():
    print(" Lancement de la visualisation des motifs avec Graphviz")
    
    if not os.path.exists(Dossier_Sortie_Docs):
        os.makedirs(Dossier_Sortie_Docs)

    if not os.path.exists(Fichier_Resultats):
        print(f" Erreur : Le fichier {Fichier_Resultats} est introuvable.")
        return

    # Chargement des dictionnaires
    df_noeuds = pd.read_csv(Lexique_Noeuds)
    df_aretes = pd.read_csv(Lexique_Aretes)
    dict_noeuds = dict(zip(df_noeuds['ID_gSpan'].astype(str), df_noeuds['Super_Label']))
    dict_aretes = dict(zip(df_aretes['ID_gSpan'].astype(str), df_aretes['Relation']))

    # Construction des graphes de documents (NetworkX) pour le mapping mathématique
    
    df_brut = pd.read_csv(Fichier_Donnees_Brutes, keep_default_na=False)
    docs_list = list(df_brut.groupby('doc_id').groups.keys())
    
    doc_graphs = {}
    for idx, row in df_brut.iterrows():
        doc = row['doc_id']
        if doc not in doc_graphs: doc_graphs[doc] = nx.DiGraph()
        
        src_txt = str(row['source_texte']).strip()
        src_tag = creer_label_noeud(row, "source")
        
        # relier les flèches bout à bout sur les mêmes mots 
        src_id = f"{src_txt}_{src_tag}" 
        
        tgt_txt = str(row['target_texte']).strip()
        tgt_tag = creer_label_noeud(row, "target")
        tgt_id = f"{tgt_txt}_{tgt_tag}"
        
        rel = str(row.get('relation_type', '')).strip()
        
        doc_graphs[doc].add_node(src_id, tag=src_tag, texte=src_txt)
        doc_graphs[doc].add_node(tgt_id, tag=tgt_tag, texte=tgt_txt)
        doc_graphs[doc].add_edge(src_id, tgt_id, rel=rel)

    # Lecture des motifs gSpan
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

    motifs = sorted(motifs, key=lambda x: x['support'], reverse=True)
    
    # Dessin des Motifs avec Graphviz et Isomorphisme 
    nm = iso.categorical_node_match('tag', 'UNKNOWN')
    em = iso.categorical_edge_match('rel', 'UNKNOWN')

    # pour suivre l'utilisation des documents
    compteur_utilisation_docs = {doc: 0 for doc in docs_list}

    for i, m in enumerate(motifs):
        # Liste pour stocker tous les exemples valides trouvés pour ce motif
        candidats_valides = []
        
        for doc_idx in m['where']:
            if doc_idx < len(docs_list):
                doc_name = docs_list[doc_idx]
                G_doc = doc_graphs[doc_name]
                G_motif = m['graph']
                
                # on cherche le motif  dans le document
                matcher = iso.DiGraphMatcher(G_doc, G_motif, node_match=nm, edge_match=em)
                for match in matcher.subgraph_isomorphisms_iter():
                    # match associe : {id_noeud_doc: id_noeud_motif}
                    mots_pour_ce_candidat = {}
                    for d_node, m_node in match.items():
                        mots_pour_ce_candidat[m_node] = G_doc.nodes[d_node]['texte']
                        
                    # On stocke ce document comme un candidat possible
                    candidats_valides.append({
                        'nom': doc_name,
                        'mots': mots_pour_ce_candidat,
                        'score_utilisation': compteur_utilisation_docs[doc_name]
                    })
                    break # On a trouvé une occurrence dans ce document, on passe au doc_idx suivant

        # Sélection du meilleur candidat (celui le moins utilisé jusqu'à présent)
        if candidats_valides:
            # Trie les candidats par score d'utilisation croissant
            candidats_valides = sorted(candidats_valides, key=lambda x: x['score_utilisation'])
            
            # Le gagnant est le premier de la liste
            meilleur_candidat = candidats_valides[0]
            doc_exemple = meilleur_candidat['nom']
            mots_trouves = meilleur_candidat['mots']
            
            # ce document vient d'être utilisé 
            compteur_utilisation_docs[doc_exemple] += 1
            
        else:
            doc_exemple = "Inconnu"
            mots_trouves = {}

        titre = f"Motif n°{m['id']} (Présent dans {m['support']} documents)\\nExemple tiré du document : {doc_exemple}"
        
        dot = graphviz.Digraph(
            name=f"motif_{m['id']}",
            format='png',
            engine='fdp',         # Moteur pour les réseaux organiques 2D
            graph_attr={
                'overlap': 'scale',   # Étire l'espace 2D pour qu'aucune boîte ne se touche
                'splines': 'true',    # Autorise les flèches à se courber
                'sep': '+1.5',        # Marge de sécurité de l'espace vide
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
                'len': '3.0'          # Donne des flèches plus longues pour un graphe aéré
            }
        )
        
        for nid, data in m['graph'].nodes(data=True):
            nlabel_abstrait = data['tag']
            
            # on prend les mots valides
            mot_reel = mots_trouves.get(nid, "Entité") 
            
            couleurs = determiner_couleurs(nlabel_abstrait)
            
            # Construction d'un label HTML
            html_label = f'<<B>{mot_reel}</B><BR/><FONT POINT-SIZE="10">{nlabel_abstrait.replace("_", " ")}</FONT>>'
            
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
        dot.render(nom_fichier_base, cleanup=True)

    print(f" {len(motifs)} graphes sont générés dans : {Dossier_Sortie_Docs}")

if __name__ == "__main__":
    visualiser_motifs()