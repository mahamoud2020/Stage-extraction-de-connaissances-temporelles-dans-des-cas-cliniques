import os
import pandas as pd
import graphviz
import networkx as nx
import networkx.algorithms.isomorphism as iso
import argparse

# Définir le chemin 
Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Parent_dir = os.path.dirname(Base_dir)
Dossier_Mining = os.path.join(Parent_dir, "Graphe pattern  mining")

def visualiser_motifs(version_active):
    print(f" Lancement de la visualisation des graphes (Version : {version_active.upper()})")

    # Détermination du dossier selon la version
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

    # Chemin d'entrée
    Fichier_Resultats = os.path.join(dossier_version, "resultats_bruts_gspan.txt")
    Lexique_Noeuds = os.path.join(dossier_version, "dictionnaire_noeuds.csv")
    Lexique_Aretes = os.path.join(dossier_version, "dictionnaire_aretes.csv")

    if version_active == 'coref':
        Fichier_Donnees_Brutes = os.path.join(dossier_version, "balises_relations_attributs_coref.csv")
    else:
        Fichier_Donnees_Brutes = os.path.join(dossier_version, "balises_relations_attributs.csv")

    # Dossier de sortie
    Dossier_Sortie_Docs = os.path.join(dossier_version, "graphes_motifs")
    if not os.path.exists(Dossier_Sortie_Docs): 
        os.makedirs(Dossier_Sortie_Docs)

    if not os.path.exists(Fichier_Resultats):
        print(f" Erreur : {Fichier_Resultats} introuvable.")
        return

    def creer_label_noeud(row, prefix="source"):
        tag = str(row.get(f'{prefix}_tag', ''))
        
        # Logique de fusion (Rétrocompatibilité pour la version fusion)
        if version_active == 'fusion':
            import re
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

    # Chargement dictionnaires
    df_noeuds = pd.read_csv(Lexique_Noeuds)
    df_aretes = pd.read_csv(Lexique_Aretes)
    dict_noeuds = dict(zip(df_noeuds['ID_gSpan'].astype(str), df_noeuds['Super_Label']))
    dict_aretes = dict(zip(df_aretes['ID_gSpan'].astype(str), df_aretes['Relation']))

    # Construction des graphes de documents (NetworkX)
    print(" Construction des graphes en mémoire")
    df_brut = pd.read_csv(Fichier_Donnees_Brutes, keep_default_na=False)
    docs_list = list(df_brut.groupby('doc_id').groups.keys())
    
    doc_graphs = {}
    for _, row in df_brut.iterrows():
        doc = row['doc_id']
        
        if doc not in doc_graphs: doc_graphs[doc] = nx.MultiDiGraph()
        
        # Logique d'identification (Gère automatiquement la présence ou non de la coref)
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
            motif_courant = {'id': motif_id, 'graph': nx.MultiDiGraph(), 'support': 0, 'where': []}
            
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
    
    print(f" -> Dessin de {len(motifs)} motifs...")
    
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

    compteur_utilisation_docs = {doc: 0 for doc in docs_list}

    for i, m in enumerate(motifs):
        
        # On trie d'abord les documents par leur compteur d'utilisation
        docs_potentiels = [docs_list[idx] for idx in m['where'] if idx < len(docs_list)]
        docs_potentiels.sort(key=lambda d: compteur_utilisation_docs[d])
        
        doc_exemple = "Inconnu"
        mots_trouves = {}
        
        for doc_name in docs_potentiels:
            G_doc = doc_graphs[doc_name]
            G_motif = m['graph']
            
            matcher = iso.MultiDiGraphMatcher(G_doc, G_motif, node_match=nm, edge_match=em)
            match_trouve = False
            
            for match in matcher.subgraph_isomorphisms_iter():
                for d_node, m_node in match.items():
                    mots_trouves[m_node] = G_doc.nodes[d_node]['texte']
                match_trouve = True
                break # On sort du générateur d'isomorphisme
                
            if match_trouve:
                doc_exemple = doc_name
                compteur_utilisation_docs[doc_name] += 1
                break # On a notre exemple, on ne vérifie pas les autres documents !

        titre = f"Motif n°{m['id']} (Présent dans {m['support']} documents)\nExemple tiré du document : {doc_exemple}"
        if version_active == 'coref':
            titre += "\n(avec la coréférence)"
        
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
            node_attr={'shape': 'box', 'style': 'filled,rounded', 'fontname': 'Helvetica', 'margin': '0.3,0.15'},
            edge_attr={'fontname': 'Helvetica-Bold', 'fontsize': '11', 'color': '#34495E', 'fontcolor': '#C0392B', 'arrowsize': '1.2', 'len': '3.0'}
        )
        
        for nid, data in m['graph'].nodes(data=True):
            nlabel_abstrait = data['tag']
            mot_reel = mots_trouves.get(nid, "Entité") 
            couleurs = determiner_couleurs(nlabel_abstrait)
            
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
            print(f" Erreur motif {m['id']}: {e}")

    print(f"\n {len(motifs)} graphes PNG ont été générés dans {Dossier_Sortie_Docs}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', type=str, default='complet')
    args = parser.parse_args()
    
    visualiser_motifs(args.version)