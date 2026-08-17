import os
import pandas as pd
import argparse

Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Parent_dir = os.path.dirname(Base_dir) # Remonte au dossier parent
Dossier_Mining = os.path.join(Parent_dir, "Graphe pattern  mining")

def encoder_pour_gspan(version_active):
    print(f" Lancement de l'encodage au format gSpan (Version : {version_active.upper()})")

    # Détermination des dossiers et attributs selon la version
    if version_active == 'complet':
        dossier_sortie = os.path.join(Dossier_Mining, "resultats_avec_tous_les_attributs")
        attributs_a_garder = ['docTimeRel', 'eventType', 'contextualModality', 'polarity']
        
    elif version_active == 'sans_dct':
        dossier_sortie = os.path.join(Dossier_Mining, "resultats_sans_attribut_doctimrel")
        attributs_a_garder = ['eventType', 'contextualModality', 'polarity']
        
    elif version_active == 'sans_polarity':
        dossier_sortie = os.path.join(Dossier_Mining, "resultats_sans_attribut_polarity")
        attributs_a_garder = ['docTimeRel', 'eventType', 'contextualModality']
        
    elif version_active == 'sans_eventtype':
        dossier_sortie = os.path.join(Dossier_Mining, "resultats_sans_attribut_eventype")
        attributs_a_garder = ['docTimeRel', 'contextualModality', 'polarity']
        
    elif version_active == 'fusion':
        dossier_sortie = os.path.join(Dossier_Mining, "resultats_fusion_event_clinentity")
        attributs_a_garder = ['docTimeRel', 'eventType', 'contextualModality', 'polarity']
        
    elif version_active == 'coref':
        dossier_sortie = os.path.join(Dossier_Mining, "avec_coref")
        attributs_a_garder = ['docTimeRel', 'eventType', 'contextualModality', 'polarity']
        
    else:
        dossier_sortie = os.path.join(Dossier_Mining, "resultats_avec_tous_les_attributs")
        attributs_a_garder = ['docTimeRel', 'eventType', 'contextualModality', 'polarity']

    # Fichiers d'entrée et de sortie
    if version_active == 'coref':
        # Le fichier enrichi par l'intégration de la coréférence
        Fichier_Entree = os.path.join(dossier_sortie, "balises_relations_attributs_coref.csv")
    else:
        Fichier_Entree = os.path.join(dossier_sortie, "balises_relations_attributs.csv")

    Fichier_Sortie_TXT = os.path.join(dossier_sortie, "graphes_gspan.txt")
    Lexique_Noeuds = os.path.join(dossier_sortie, "dictionnaire_noeuds.csv")
    Lexique_Aretes = os.path.join(dossier_sortie, "dictionnaire_aretes.csv")

    if not os.path.exists(Fichier_Entree):
        print(f" Erreur : Le fichier {Fichier_Entree} est introuvable.")
        if version_active == 'coref':
            print(" Il faut verifier que l'étape de l'intégration de la coréférence est bien exécuté ?")
        return

    if not os.path.exists(dossier_sortie):
        os.makedirs(dossier_sortie)

    df = pd.read_csv(Fichier_Entree, keep_default_na=False)

    dictionnaire_noeuds = {}
    dictionnaire_aretes = {}
    
    compteur_label_noeud = 0
    compteur_label_arete = 0

    def creer_label_noeud(row, prefix="source"):
        tag = str(row[f'{prefix}_tag'])
        
        # Logique de nommage spécifique à TIMEX3
        if tag == 'TIMEX3':
            timex_val = str(row.get(f'{prefix}_timexType', 'Non concerné')).strip()
            if timex_val and timex_val != "Non concerné":
                return timex_val
            return "TIMEX3"
        
        label_parts = [tag]
        
        # On n'ajoute que les attributs autorisés par la configuration actuelle
        for attr in attributs_a_garder:
            val = str(row.get(f'{prefix}_{attr}', "Non concerné")).strip()
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
                
                # Gestion de la source
                # On gère le cas général et le cas coréférence en même temps
                mention_src = str(row.get('mention_source', 'non détecté')).strip()
                orig_src_id = str(row.get('source_id', f"{row.get('source_texte', '')}_{row.get('source_tag', '')}")).strip()
                
                if mention_src not in ["singleton", "non détecté", "nan", ""]:
                    src_id = f"{nom_doc}_{mention_src}"
                else:
                    src_id = f"{nom_doc}_{orig_src_id}"
                
                if src_id not in id_global_vers_local:
                    label_str = creer_label_noeud(row, "source")
                    if label_str not in dictionnaire_noeuds:
                        dictionnaire_noeuds[label_str] = compteur_label_noeud
                        compteur_label_noeud += 1
                    
                    id_global_vers_local[src_id] = local_id_counter
                    f_out.write(f"v {local_id_counter} {dictionnaire_noeuds[label_str]}\n")
                    local_id_counter += 1
                
                # Gestion de la cible
                mention_tgt = str(row.get('mention_target', 'non détecté')).strip()
                orig_tgt_id = str(row.get('target_id', f"{row.get('target_texte', '')}_{row.get('target_tag', '')}")).strip()
                
                if mention_tgt not in ["singleton", "non détecté", "nan", ""]:
                    tgt_id = f"{nom_doc}_{mention_tgt}"
                else:
                    tgt_id = f"{nom_doc}_{orig_tgt_id}"
                    
                if tgt_id not in id_global_vers_local:
                    label_str = creer_label_noeud(row, "target")
                    if label_str not in dictionnaire_noeuds:
                        dictionnaire_noeuds[label_str] = compteur_label_noeud
                        compteur_label_noeud += 1
                    
                    id_global_vers_local[tgt_id] = local_id_counter
                    f_out.write(f"v {local_id_counter} {dictionnaire_noeuds[label_str]}\n")
                    local_id_counter += 1

            for _, row in donnees_doc.iterrows():
                rel_str = str(row.get('relation_type', 'UNKNOWN')).strip()
                if rel_str not in dictionnaire_aretes:
                    dictionnaire_aretes[rel_str] = compteur_label_arete
                    compteur_label_arete += 1
                
                # Récupération des IDs fusionnés ou non pour l'arête
                mention_src = str(row.get('mention_source', 'non détecté')).strip()
                orig_src_id = str(row.get('source_id', f"{row.get('source_texte', '')}_{row.get('source_tag', '')}")).strip()
                if mention_src not in ["singleton", "non détecté", "nan", ""]:
                    src_id = f"{nom_doc}_{mention_src}"
                else:
                    src_id = f"{nom_doc}_{orig_src_id}"
                    
                mention_tgt = str(row.get('mention_target', 'non détecté')).strip()
                orig_tgt_id = str(row.get('target_id', f"{row.get('target_texte', '')}_{row.get('target_tag', '')}")).strip()
                if mention_tgt not in ["singleton", "non détecté", "nan", ""]:
                    tgt_id = f"{nom_doc}_{mention_tgt}"
                else:
                    tgt_id = f"{nom_doc}_{orig_tgt_id}"
                
                local_src = id_global_vers_local[src_id]
                local_tgt = id_global_vers_local[tgt_id]
                
                # On ne trace pas d'arête si un nœud pointe vers lui-même après la fusion
                if local_src != local_tgt:
                    f_out.write(f"e {local_src} {local_tgt} {dictionnaire_aretes[rel_str]}\n")
            
            graph_id += 1

    df_lex_noeuds = pd.DataFrame(list(dictionnaire_noeuds.items()), columns=['Super_Label', 'ID_gSpan'])
    df_lex_noeuds.to_csv(Lexique_Noeuds, index=False, encoding='utf-8')
    
    df_lex_aretes = pd.DataFrame(list(dictionnaire_aretes.items()), columns=['Relation', 'ID_gSpan'])
    df_lex_aretes.to_csv(Lexique_Aretes, index=False, encoding='utf-8')
    
    print(f" {graph_id} graphes enregistrés dans '{os.path.basename(dossier_sortie)}'.")
    print(f" Dictionnaire généré : {len(dictionnaire_noeuds)} labels de nœuds distincts, {len(dictionnaire_aretes)} types de relations.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', type=str, default='complet')
    args = parser.parse_args()
    
    encoder_pour_gspan(args.version)