import os
import pandas as pd
import graphviz
import argparse

# Définition des chemins 
Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Parent_dir = os.path.dirname(Base_dir)
Dossier_Mining = os.path.join(Parent_dir, "Graphe pattern  mining")

def visualiser_documents_entiers(version_active):
    print(f" Création des graphes complets par document (Version : {version_active.upper()}) ")
    
    # 1. Détermination du dossier selon la version
    if version_active == 'complet':
        dossier_version = os.path.join(Dossier_Mining, "resultats_avec_tous_les_attributs")
    elif version_active == 'sans_dct':
        dossier_version = os.path.join(Dossier_Mining, "resultats_sans_attribut_doctimrel")
    elif version_active == 'sans_polarity':
        dossier_version = os.path.join(Dossier_Mining, "resultats_sans_attribut_polarity")
    elif version_active == 'sans_eventtype':
        dossier_version = os.path.join(Dossier_Mining, "resultats_sans_attribut_eventype")
    elif version_active == 'fusion':
        dossier_version = os.path.join(Dossier_Mining, "resultats_fusion_event_clinentity")
    elif version_active == 'coref':
        dossier_version = os.path.join(Dossier_Mining, "avec_coref")
    else:
        dossier_version = os.path.join(Dossier_Mining, "resultats_avec_tous_les_attributs")

    # Dossier d'entrée
    if version_active == 'coref':
        Fichier_Donnees = os.path.join(dossier_version, "balises_relations_attributs_coref.csv")
    else:
        Fichier_Donnees = os.path.join(dossier_version, "balises_relations_attributs.csv")

    # Dossier de sortie
    Dossier_Sortie_Docs = os.path.join(dossier_version, "graphes_documents_complets")
    
    if not os.path.exists(Dossier_Sortie_Docs):
        os.makedirs(Dossier_Sortie_Docs)

    if not os.path.exists(Fichier_Donnees):
        print(f" Erreur : Le fichier d'extraction {Fichier_Donnees} est introuvable.")
        if version_active == 'coref':
            print(" Il faut d'abord lancer le script integration_coreference.py ?")
        return

    # Fonctions de dessin
    def determiner_couleurs(tag):
        lbl = str(tag).upper()
        if 'TIMEX' in lbl: return {'fillcolor': '#F39C12', 'color': '#D68910', 'fontcolor': 'white'}
        elif 'CLINENTITY' in lbl: return {'fillcolor': '#8E44AD', 'color': '#732D91', 'fontcolor': 'white'}
        elif 'EVENT' in lbl: return {'fillcolor': '#16A085', 'color': '#117A65', 'fontcolor': 'white'}
        else: return {'fillcolor': '#34495E', 'color': '#2C3E50', 'fontcolor': 'white'}

    df = pd.read_csv(Fichier_Donnees, keep_default_na=False)
    groupes_documents = df.groupby('doc_id')

    compteur = 0

    for nom_doc, donnees_doc in groupes_documents:
        print(f" Dessin du document  : {nom_doc} ")
        
        titre = f"Graphe Global du Document : {nom_doc}"
        if version_active == 'coref':
            titre += "\n(Intégrant la coréférence)"
        
        # Configuration des graphes 
        dot = graphviz.Digraph(
            name=f"doc_{nom_doc}",
            format='png',         
            engine='fdp',
            graph_attr={
                'overlap': 'scale',   
                'splines': 'true',    
                'sep': '+1.5',        
                'K': '0.8',           
                'label': titre,
                'labelloc': 't',      
                'fontsize': '30',
                'fontname': 'Helvetica-Bold',
                'fontcolor': '#2C3E50',
                'pad': '1.0',
                'bgcolor': '#F8F9FA'
            },
            node_attr={'shape': 'box', 'style': 'filled,rounded', 'fontname': 'Helvetica', 'margin': '0.3,0.15'},
            edge_attr={'fontname': 'Helvetica-Bold', 'fontsize': '10', 'color': '#7F8C8D', 'fontcolor': '#C0392B', 'arrowsize': '0.8'}
        )
        
        noeuds_vus = set()
        
        for _, row in donnees_doc.iterrows():
            
            # Gestion de la source
            mention_src = str(row.get('mention_source', 'non détecté')).strip()
            orig_src_id = str(row.get('source_id', f"{row.get('source_texte', '')}_{row.get('source_tag', '')}")).strip()
            
            # Si c'est une chaîne (pas un singleton ni non détecté), on utilise l'ID de la chaîne pour fusionner
            if mention_src not in ["singleton", "non détecté", "", "nan"]:
                src_id = f"{nom_doc}_{mention_src}"
            else:
                src_id = f"{nom_doc}_{orig_src_id}"
                
            src_texte = str(row.get('source_texte', '')).strip()
            src_tag = str(row.get('source_tag', '')).strip()
            
            # Ajout Noeud Source
            if src_id not in noeuds_vus:
                couleurs = determiner_couleurs(src_tag)
                
                html_label = f'<<B>"{src_texte}"</B><BR/><FONT POINT-SIZE="10">({src_tag.replace("_", " ")})</FONT>>'
                dot.node(src_id, label=html_label, fillcolor=couleurs['fillcolor'], color=couleurs['color'], fontcolor=couleurs['fontcolor'])
                noeuds_vus.add(src_id)
                
            # Gestion de la cible
            mention_tgt = str(row.get('mention_target', 'non détecté')).strip()
            orig_tgt_id = str(row.get('target_id', f"{row.get('target_texte', '')}_{row.get('target_tag', '')}")).strip()
            
            if mention_tgt not in ["singleton", "non détecté", "", "nan"]:
                tgt_id = f"{nom_doc}_{mention_tgt}"
            else:
                tgt_id = f"{nom_doc}_{orig_tgt_id}"
                
            tgt_texte = str(row.get('target_texte', '')).strip()
            tgt_tag = str(row.get('target_tag', '')).strip()
            
            # Ajout Noeud Cible
            if tgt_id not in noeuds_vus:
                couleurs = determiner_couleurs(tgt_tag)
                html_label = f'<<B>"{tgt_texte}"</B><BR/><FONT POINT-SIZE="10">({tgt_tag.replace("_", " ")})</FONT>>'
                dot.node(tgt_id, label=html_label, fillcolor=couleurs['fillcolor'], color=couleurs['color'], fontcolor=couleurs['fontcolor'])
                noeuds_vus.add(tgt_id)
                
            # Ajout Arête (Graphviz fusionne visuellement grâce aux IDs partagés)
            dot.edge(src_id, tgt_id, label=f" {row.get('relation_type', '')} ")

        nom_fichier_base = os.path.join(Dossier_Sortie_Docs, f"graphe_global_{nom_doc}")
        try:
            dot.render(nom_fichier_base, cleanup=True)
        except Exception as e:
            print(f" Erreur pour {nom_doc} : {e}")
            
        compteur += 1

    print(f"\n {compteur} graphes ont été générés dans :{Dossier_Sortie_Docs}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', type=str, default='complet')
    args = parser.parse_args()
    
    visualiser_documents_entiers(args.version)