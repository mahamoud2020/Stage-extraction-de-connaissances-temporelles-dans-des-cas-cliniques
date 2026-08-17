import os
import pandas as pd
import argparse


# Définition des chemins
# ********************************************************************************

Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Dossier_CSV = os.path.join(Base_dir, "data", "sortie_csv")
Parent_dir = os.path.dirname(Base_dir) # On remonte dans l'arborescence
Dossier_Mining = os.path.join(Parent_dir, "Graphe pattern  mining")

def integrer_coreferences(version_active):
    # Ce script ne s'exécute que si on est en version coref
    if version_active != 'coref':
        print(f" L'intégration de la coréférence n'est pas nécessaire pour la version '{version_active}'.")
        return

    print(" Lancement de l'intégration de la coréférence ")
    
    Dossier_Sortie = os.path.join(Dossier_Mining, "avec_coref")
    Fichier_Coref = os.path.join(Dossier_CSV, "comparaison_coref_temp.csv")
    
    # va chercher le fichier brut généré par l'étape 9 dans son dossier
    Fichier_Graphes = os.path.join(Dossier_Sortie, "balises_relations_attributs.csv")
    Fichier_Sortie_Graphes = os.path.join(Dossier_Sortie, "balises_relations_attributs_coref.csv")

    if not os.path.exists(Dossier_Sortie):
        os.makedirs(Dossier_Sortie)

    if not os.path.exists(Fichier_Coref) or not os.path.exists(Fichier_Graphes):
        print(f" Erreur : Fichiers d'entrée introuvables.")
        print(f" Vérifie que l'étape 9 a bien généré {Fichier_Graphes}")
        return

    
    # Analyse des chaînes de coréférence
    # ************************************************************************
    df_coref = pd.read_csv(Fichier_Coref)
    
    entity_status = {}
    
    for _, row in df_coref.iterrows():
        doc = row['doc']
        xml_id = str(row['xml_id'])
        coref_status = row['coref']
        mention_id = str(row['mention_id'])
        longueur = row['longueur_chaine']
        
        if xml_id == 'Non applicable' or pd.isna(row['xml_id']):
            continue
            
        if coref_status == 'Détecté':
            try:
                longueur_num = int(float(longueur))
            except (ValueError, TypeError):
                longueur_num = 0
                
            if longueur_num > 1:
                entity_status[(doc, xml_id)] = mention_id
            else:
                entity_status[(doc, xml_id)] = "singleton"
        else:
            entity_status[(doc, xml_id)] = "non détecté"

    print(f" -> {len(entity_status)} entités qualifiées via CorPipe.")

    
    # Récupération des arêtes et ajout des colonnes
    # ****************************************************************************
    df_graph = pd.read_csv(Fichier_Graphes, keep_default_na=False)
    
    nouvelles_aretes = []

    for _, row in df_graph.iterrows():
        doc = row['doc_id']
        src_orig_id = str(row['source_id'])
        tgt_orig_id = str(row['target_id'])

        mention_source = entity_status.get((doc, src_orig_id), "non détecté")
        mention_target = entity_status.get((doc, tgt_orig_id), "non détecté")

        nouvelle_arete = row.to_dict()
        nouvelle_arete['mention_source'] = mention_source
        nouvelle_arete['mention_target'] = mention_target
        
        nouvelles_aretes.append(nouvelle_arete)

    df_final = pd.DataFrame(nouvelles_aretes)
    
    if not df_final.empty:
        cols = list(df_final.columns)
        if 'source_id' in cols and 'mention_source' in cols:
            cols.insert(cols.index('source_id') + 1, cols.pop(cols.index('mention_source')))
        if 'target_id' in cols and 'mention_target' in cols:
            cols.insert(cols.index('target_id') + 1, cols.pop(cols.index('mention_target')))
            
        df_final = df_final[cols]
        df_final.to_csv(Fichier_Sortie_Graphes, index=False, encoding='utf-8')
    else:
        print(" Attention : Le DataFrame final est vide.")

    print("\n" + "*"*60)
    print(f" Arêtes traitées : {len(df_final)}")
    print("*"*60)
    print(f" Le fichier avec les colonnes mention_source et mention_target est dispoinble dans : {Fichier_Sortie_Graphes}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', type=str, default='coref')
    args = parser.parse_args()
    
    integrer_coreferences(args.version)