import os
import pandas as pd
import graphviz


# Définir le chemin 

Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Pointeur sur Français/
Parent_dir = os.path.dirname(Base_dir) # Remonte d'un cran vers coref_e3c_corpipe_


Dossier_Mining = os.path.join(Parent_dir, "Graphe pattern  mining")

# On cherche le fichier de données 
Fichier_Graphes = os.path.join(Dossier_Mining, "graphes_attributs_gspan.csv")
Fichier_Balises = os.path.join(Dossier_Mining, "balises_relations_attributs.csv")
Fichier_Donnees = Fichier_Graphes if os.path.exists(Fichier_Graphes) else Fichier_Balises

# Le sous-dossier où atterriront tes belles images PNG
Dossier_Sortie_Docs = os.path.join(Dossier_Mining, "graphes_documents_complets")


# Fonctions de dessin

def determiner_couleurs(tag):
    lbl = str(tag).upper()
    if 'TIMEX' in lbl: return {'fillcolor': '#F39C12', 'color': '#D68910', 'fontcolor': 'white'}
    elif 'CLINENTITY' in lbl: return {'fillcolor': '#8E44AD', 'color': '#732D91', 'fontcolor': 'white'}
    elif 'EVENT' in lbl: return {'fillcolor': '#16A085', 'color': '#117A65', 'fontcolor': 'white'}
    else: return {'fillcolor': '#34495E', 'color': '#2C3E50', 'fontcolor': 'white'}

def visualiser_documents_entiers():
    print(" Création des graphes de chaque document au format PNG ")
    
    if not os.path.exists(Dossier_Sortie_Docs):
        os.makedirs(Dossier_Sortie_Docs)

    if not os.path.exists(Fichier_Donnees):
        print(f" Erreur : Le fichier d'extraction {Fichier_Donnees} est introuvable.")
        return

    df = pd.read_csv(Fichier_Donnees, keep_default_na=False)
    groupes_documents = df.groupby('doc_id')

    limite_docs = None 
    compteur = 0

    for nom_doc, donnees_doc in groupes_documents:
        if limite_docs and compteur >= limite_docs:
            break
            
        print(f" Dessin du document  : {nom_doc} ")
        
        titre = f"Graphe Global du Document : {nom_doc}"
        
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
            
            
             
            
            
            src_id = str(row.get('source_id', f"{row['source_texte']}_{row['source_tag']}")).strip()
            src_texte = str(row['source_texte']).strip()
            src_tag = str(row['source_tag']).strip()
            
            # Ajout Noeud Source
            if src_id not in noeuds_vus:
                couleurs = determiner_couleurs(src_tag)
                
                html_label = f'<<B>"{src_texte}"</B><BR/><FONT POINT-SIZE="10">({src_tag.replace("_", " ")})</FONT>>'
                dot.node(src_id, label=html_label, fillcolor=couleurs['fillcolor'], color=couleurs['color'], fontcolor=couleurs['fontcolor'])
                noeuds_vus.add(src_id)
                
            # Traitement Cible identique
            tgt_id = str(row.get('target_id', f"{row['target_texte']}_{row['target_tag']}")).strip()
            tgt_texte = str(row['target_texte']).strip()
            tgt_tag = str(row['target_tag']).strip()
            
            # Ajout Noeud Cible
            if tgt_id not in noeuds_vus:
                couleurs = determiner_couleurs(tgt_tag)
                html_label = f'<<B>"{tgt_texte}"</B><BR/><FONT POINT-SIZE="10">({tgt_tag.replace("_", " ")})</FONT>>'
                dot.node(tgt_id, label=html_label, fillcolor=couleurs['fillcolor'], color=couleurs['color'], fontcolor=couleurs['fontcolor'])
                noeuds_vus.add(tgt_id)
                
            # Ajout Arête 
            dot.edge(src_id, tgt_id, label=f" {row['relation_type']} ")

        nom_fichier_base = os.path.join(Dossier_Sortie_Docs, f"graphe_global_{nom_doc}")
        try:
            dot.render(nom_fichier_base, cleanup=True)
        except Exception as e:
            print(f" Erreur pour {nom_doc} : {e}")
            
        compteur += 1

    print(f"\n {compteur} graphes ont été générés ")
    

if __name__ == "__main__":
    visualiser_documents_entiers()