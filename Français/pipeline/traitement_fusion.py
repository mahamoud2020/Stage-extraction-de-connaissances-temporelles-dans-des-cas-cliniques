import os
import csv


# Définition des chemins

Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Dossier_CSV = os.path.join(Base_dir, "data", "sortie_csv")

Fichier_XML = os.path.join(Dossier_CSV, "verif_entites_cliniques.csv")
Fichier_mentions = os.path.join(Dossier_CSV, "resultats_mentions_fr.csv") 
Fichier_fusion = os.path.join(Dossier_CSV, "mentions_enrichies_finales.csv")


def charger_entites_xml():
    """Charge le fichier des entités XML dans un dictionnaire."""
    entites_par_doc = {}
    if not os.path.exists(Fichier_XML):
        print(f" Le fichier XML {Fichier_XML} est introuvable. Peut-être l'étape 4  n'est pas lancée ou n'a pas fonctionné ?")
        return entites_par_doc

    try:
        with open(Fichier_XML, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                doc_id = row['doc_id']
                if doc_id not in entites_par_doc:
                    entites_par_doc[doc_id] = []
                entites_par_doc[doc_id].append({
                    'categorie': row['categorie'],
                    'texte': row['texte'].lower().strip()
                })
    except Exception as e:
        print(f" Problème lors de la lecture du fichier XML : {e}")
        
    return entites_par_doc




def fusionner_donnees():
    print("\n Démarrage Étape 5 : Alignement Sémantique (Tête Lexicale) ")
    
    entites_xml = charger_entites_xml()
    if not entites_xml:
        print(" Aucune entité XML n'a été chargée. La fusion va générer le fichier, mais toutes les étiquettes seront à 'O'.")
        
        
    if not os.path.exists(Fichier_mentions):
        print(f" Le fichier {Fichier_mentions} est introuvable.")
        return

    lignes_enrichies = []
    champs = []
    mentions_matchees = 0
    
    with open(Fichier_mentions, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        champs = reader.fieldnames + ['entite_semantique']
        
        for row in reader:
            doc_id = row['doc']
            tete = row['tete_lexicale'].lower().strip()
            
            entite_trouvee = "O" 
            
            if doc_id in entites_xml:
                for entite in entites_xml[doc_id]:
                    txt_xml = entite['texte']
                    # On cherche si la tête est le mot exact de l'entité XML
                    # ou si elle fait partie de l'entité XML 
                    if tete == txt_xml or tete in txt_xml.split():
                        entite_trouvee = entite['categorie']
                        break 
            
            row['entite_semantique'] = entite_trouvee
            if entite_trouvee != "O":
                mentions_matchees += 1
                
            lignes_enrichies.append(row)

    # Sauvegarde du fichier final
    with open(Fichier_fusion, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=champs)
        writer.writeheader()
        writer.writerows(lignes_enrichies)
        
    print(f" Fusion effectuée !")
    print(f" {mentions_matchees} mentions ont reçu une étiquette spécifique.")
    print(f" Fichier final généré : {Fichier_fusion}")

if __name__ == "__main__":
    fusionner_donnees()