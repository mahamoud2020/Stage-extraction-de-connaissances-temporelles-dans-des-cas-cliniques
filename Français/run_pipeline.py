import os
import subprocess
import sys
import argparse 

# Import des étapes depuis le dossier pipeline
from pipeline.traitement_xml import analyser_corpus_xml
from pipeline.traitement_fusion import fusionner_donnees

def executer_etape(nom_script, description):
    
    print(f"\n Exécution: {description}")
    print(f"*"*60)
    
    chemin_script = os.path.join("pipeline", nom_script)
    
    if not os.path.exists(chemin_script):
        print(f" Erreur : Le fichier {chemin_script} est introuvable.")
        sys.exit(1)
        
    try:
        subprocess.run([sys.executable, chemin_script], check=True)
    except subprocess.CalledProcessError:
        print(f"\n Arrêt du pipeline : Une erreur est constatée lors de l'étape '{nom_script}'.")
        sys.exit(1) 

def main():
    # Configuration des arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="Pipeline NLP Clinique.")
    parser.add_argument(
        '--etapes', 
        nargs='+', 
        type=int, 
        # Mise à jour, le pipeline s'arrête maintenant à l'étape 8
        default=[1, 2, 3, 4, 5, 6, 7, 8], 
        help="Liste des étapes à exécuter (ex: --etapes 3 4 5 6 7 8)."
    )
    
    args = parser.parse_args()
    etapes_a_lancer = args.etapes

    
    print(f"\n Démarrage du pipeline ")
    print("*"*60)

    # On exécute selon l'étape souhaitée
    if 1 in etapes_a_lancer:
        executer_etape("traitement_udpipe.py", "Étape 1 : Parsing syntaxique (UDPipe 2)")
        
    if 2 in etapes_a_lancer:
        executer_etape("traitement_corpipe.py", "Étape 2 : Résolution des coréférences (CorPipe)")
        
    if 3 in etapes_a_lancer:
        executer_etape("traitement_extraction.py", "Étape 3 : Extraction des mentions et génération CSV pour TramineR")

    if 4 in etapes_a_lancer:
        print(f"\n" + "*"*60)
        print(f" Exécution: Étape 4 : Extraction des entités cliniques (XML)")
        print(f"*"*60)
        try:
            entites_xml = analyser_corpus_xml()
        except Exception as e:
            print(f"\n Arrêt du pipeline : Une erreur est constatée lors de l'étape 4 (XML).")
            print(f" Détail de l'erreur : {e}")
            sys.exit(1)
            
    if 5 in etapes_a_lancer:
        print(f"\n" + "*"*60)
        print(f" Exécution: Étape 5 : Alignement Sémantique (Fusion)")
        print(f"*"*60)
        try:
            fusionner_donnees()
        except Exception as e:
            print(f"\n Arrêt du pipeline : Une erreur est constatée lors de l'étape 5 (Fusion).")
            print(f" Détail de l'erreur : {e}")
            sys.exit(1)

    if 6 in etapes_a_lancer:
        
        executer_etape("extraction_temporalite.py", "Étape 6 : Extraction des relations temporelles cliniques")

    if 7 in etapes_a_lancer:
        executer_etape("comparaison_annotation_coref_temp.py", "Étape 7 : croisement (Coréférence vs Temporalité)")

    if 8 in etapes_a_lancer:
        executer_etape("visualisation_core_temp.py", "Étape 8 : Dataviz et statistiques du croisement")

    print("\n" + "*"*60)
    print(" Pipeline terminé parfaitement ")
    print(" Les tableaux et graphiques sont disponibles dans 'data/sortie_csv/'")
    
    

if __name__ == "__main__":
    main()