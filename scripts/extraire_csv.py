"""
Ce script agit comme un parseur post-inférence . Il lit  les fichiers au format CoNLL-U générés par CorPipe, analyse 
la 10ème colonne (qui contient les annotations de coréférence sous forme de balises ouvrantes 
et fermantes imbriquées, ex: `Entity=(c3(c4)`), et reconstitue les mentions multi-tokens complètes. 

Les données extraites sont ensuite structurées et exportées au format CSV.
"""

import os
import glob
import csv
import re

# Configuration des chemins

# Répertoire contenant les fichiers de sortie générés par l'inférence du modèle
INPUT_DIR = "data/conllu_sortie"
# Chemin du fichier tabulaire de destination
OUTPUT_CSV = "data/resultats_coreferences.csv"

def main():
    """
    Fonction principale de parsing et d'exportation des données.
    """
    print("Début de l'extraction et de la structuration des entités...")
    
    # Récupération exhaustive des fichiers générés par le modèle
    files = glob.glob(os.path.join(INPUT_DIR, "*.conllu"))
    
    if not files:
        print(f"Aucun fichier trouvé dans {INPUT_DIR}. Vérifiez l'étape d'inférence.")
        return

    # Liste globale pour stocker l'ensemble des mentions reconstituées du corpus
    all_mentions = []

    # Itération sur chaque fichier prédit
    for filepath in files:
        filename = os.path.basename(filepath)
        
        # Dictionnaire agissant comme un buffer mémoire pour gérer les mentions s'étendant
        # sur plusieurs tokens (multi-mots) ou les entités imbriquées.
        open_entities = {} 
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Exclusion des lignes vides et des métadonnées (commentaires CoNLL-U)
                if not line or line.startswith('#'):
                    continue
                
                cols = line.split('\t')
                
                # Vérification de l'intégrité du format CoNLL-U (10 colonnes requises)
                if len(cols) < 10:
                    continue
                    
                word = cols[1]       # Extraction de la forme de surface (Token)
                misc = cols[9]       # Extraction des attributs de coréférence
                
                # Filtrage : traitement exclusif des lignes annotées par le modèle
                if misc.startswith('Entity='):
                    entity_str = misc[7:] # Isolement de la valeur (ex: "(c3--1)c4)")
                    
                    # Étape 1 : Détection des ouvertures d'entités (Regex: "(c" suivi d'un identifiant numérique)
                    openings = re.findall(r'\((c\d+)', entity_str)
                    for op in openings:
                        if op not in open_entities:
                            open_entities[op] = [] # Initialisation de la mémoire pour cette nouvelle entité
                    
                    # Étape 2 : Concaténation
                    # Le token courant est ajouté à toutes les chaînes d'entités actuellement ouvertes
                    for ent in open_entities:
                        open_entities[ent].append(word)
                        
                    # Étape 3 : Détection des fermetures d'entités (Regex: "c" suivi d'un identifiant puis ")")
                    closings = re.findall(r'(c\d+)\)', entity_str)
                    for cl in closings:
                        if cl in open_entities:
                            # Reconstitution de la mention complète par jointure des tokens
                            mention_text = " ".join(open_entities[cl])
                            
                            # Enregistrement de la mention structurée
                            all_mentions.append({
                                'Document': filename.replace('.conllu', ''),
                                'ID_Entite': cl,
                                'Mention_Texte': mention_text
                            })
                            
                            del open_entities[cl]

    # Phase d'exportation 
    print(f"Extraction finalisée. Total des mentions identifiées : {len(all_mentions)}.")
    print("Génération du fichier d'export structuré (CSV)")
    
    # Exportation au format CSV 
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['Document', 'ID_Entite', 'Mention_Texte']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        
        writer.writeheader()
        for mention in all_mentions:
            writer.writerow(mention)
            
    print(f"Opération réussie. Fichier disponible à l'emplacement : {OUTPUT_CSV}")

if __name__ == "__main__":
    main()