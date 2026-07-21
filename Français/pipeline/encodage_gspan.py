import os
import pandas as pd

Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Dossier_CSV = os.path.join(Base_dir, "data", "sortie_csv")

Fichier_Entree = os.path.join(Dossier_CSV, "balises_relations_attributs.csv")
Fichier_Sortie_TXT = os.path.join(Dossier_CSV, "graphes_gspan.txt")
Lexique_Noeuds = os.path.join(Dossier_CSV, "dictionnaire_noeuds.csv")
Lexique_Aretes = os.path.join(Dossier_CSV, "dictionnaire_aretes.csv")

def encoder_pour_gspan():
    print(" Lancement de l'encodage au format gSpan")

    if not os.path.exists(Fichier_Entree):
        print(f" Erreur : Le fichier {Fichier_Entree} est introuvable.")
        return

    df = pd.read_csv(Fichier_Entree, keep_default_na=False)

    dictionnaire_noeuds = {}
    dictionnaire_aretes = {}
    
    compteur_label_noeud = 0
    compteur_label_arete = 0

    def creer_label_noeud(row, prefix="source"):
        tag = str(row[f'{prefix}_tag'])
        
        if tag == 'TIMEX3':
            timex_val = str(row[f'{prefix}_timexType']).strip()
            if timex_val and timex_val != "Non concerné":
                return timex_val
            return "TIMEX3"
        
        label_parts = [tag]
        
        # On ajoute contextualModality dans la structure du label
        attributs = ['docTimeRel', 'eventType', 'contextualModality', 'polarity']
        
        for attr in attributs:
            val = str(row[f'{prefix}_{attr}']).strip()
            if val and val != "Non concerné" and val != "nan":
                label_parts.append(val)
                
        return "_".join(label_parts)

    groupes_documents = df.groupby('doc_id')
    
    with open(Fichier_Sortie_TXT, 'w', encoding='utf-8') as f_out:
        graph_id = 0
        for nom_doc, donnees_doc in groupes_documents:
            f_out.write(f"t # {graph_id}\n")
            
            id_global_vers_local = {}
            local_id_counter = 0
            
            for _, row in donnees_doc.iterrows():
                src_id = str(row['source_id'])
                if src_id not in id_global_vers_local:
                    label_str = creer_label_noeud(row, "source")
                    if label_str not in dictionnaire_noeuds:
                        dictionnaire_noeuds[label_str] = compteur_label_noeud
                        compteur_label_noeud += 1
                    
                    id_global_vers_local[src_id] = local_id_counter
                    f_out.write(f"v {local_id_counter} {dictionnaire_noeuds[label_str]}\n")
                    local_id_counter += 1
                
                tgt_id = str(row['target_id'])
                if tgt_id not in id_global_vers_local:
                    label_str = creer_label_noeud(row, "target")
                    if label_str not in dictionnaire_noeuds:
                        dictionnaire_noeuds[label_str] = compteur_label_noeud
                        compteur_label_noeud += 1
                    
                    id_global_vers_local[tgt_id] = local_id_counter
                    f_out.write(f"v {local_id_counter} {dictionnaire_noeuds[label_str]}\n")
                    local_id_counter += 1

            for _, row in donnees_doc.iterrows():
                rel_str = row['relation_type']
                if rel_str not in dictionnaire_aretes:
                    dictionnaire_aretes[rel_str] = compteur_label_arete
                    compteur_label_arete += 1
                
                local_src = id_global_vers_local[str(row['source_id'])]
                local_tgt = id_global_vers_local[str(row['target_id'])]
                
                f_out.write(f"e {local_src} {local_tgt} {dictionnaire_aretes[rel_str]}\n")
            
            graph_id += 1

    df_lex_noeuds = pd.DataFrame(list(dictionnaire_noeuds.items()), columns=['Super_Label', 'ID_gSpan'])
    df_lex_noeuds.to_csv(Lexique_Noeuds, index=False, encoding='utf-8')
    
    df_lex_aretes = pd.DataFrame(list(dictionnaire_aretes.items()), columns=['Relation', 'ID_gSpan'])
    df_lex_aretes.to_csv(Lexique_Aretes, index=False, encoding='utf-8')
    print(" Encodage terminé")

if __name__ == "__main__":
    encoder_pour_gspan()