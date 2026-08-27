import os
import subprocess
import sys
import argparse 

try:
    from pipeline.traitement_xml import analyser_corpus_xml
    from pipeline.traitement_fusion import fusionner_donnees
except ImportError:
    pass

def executer_etape(nom_script, description, version_active):
    """
    Exécute un script Python du dossier pipeline en lui passant la version active.
    """
    print(f"\n" + "*"*60)
    print(f" Exécution: {description}")
    print(f" Version utilisée : [{version_active}]")
    print(f"*"*60)
    
    chemin_script = os.path.join("pipeline", nom_script)
    
    if not os.path.exists(chemin_script):
        print(f" Erreur : Le fichier {chemin_script} est introuvable.")
        sys.exit(1)
        
    try:
        # Passage de l'argument --version au sous-script
        subprocess.run([sys.executable, chemin_script, "--version", version_active], check=True)
    except subprocess.CalledProcessError:
        print(f"\n Arrêt du pipeline : Une erreur est constatée lors de l'étape '{nom_script}'.")
        sys.exit(1) 

def main():
    # Configuration des arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="Pipeline coref & extraction des annotations du corpus & analyse de séquences & graphe pattern mining (Multi-Versions)")
    
    parser.add_argument(
        '--etapes', 
        nargs='+', 
        type=int, 
        default=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14], 
        help="Liste des étapes à exécuter (ex: --etapes 12 13 14)."
    )
    
    # L'argument universel de version
    parser.add_argument(
        '--version',
        type=str,
        choices=['complet', 'sans_dct', 'sans_polarity', 'sans_eventtype', 'fusion', 'coref'],
        default='complet',
        help="La version d'expérience à exécuter."
    )
    
    args = parser.parse_args()
    etapes_a_lancer = args.etapes
    version_actuelle = args.version

    print(f"\n" + "*"*60)
    print(f" Lancement du pipeline & version active  : {version_actuelle}")
    print("="*60)

    if 1 in etapes_a_lancer:
        executer_etape("traitement_udpipe.py", "Étape 1 : Parsing syntaxique (UDPipe 2)", version_actuelle)
        
    if 2 in etapes_a_lancer:
        executer_etape("traitement_corpipe.py", "Étape 2 : Résolution des coréférences (CorPipe)", version_actuelle)
        
    if 3 in etapes_a_lancer:
        executer_etape("traitement_extraction.py", "Étape 3 : Extraction des mentions et génération CSV pour TramineR", version_actuelle)

    if 4 in etapes_a_lancer:
        print(f"\n" + "*"*60)
        print(f" Exécution: Étape 4 : Extraction des entités cliniques | Version: [{version_actuelle.upper()}]")
        print(f"*"*60)
        try:
            entites_xml = analyser_corpus_xml()
        except Exception as e:
            print(f"\n Arrêt du pipeline : Une erreur est constatée lors de l'étape 4.")
            print(f" Détail de l'erreur : {e}")
            sys.exit(1)
            
    if 5 in etapes_a_lancer:
        print(f"\n" + "*"*60)
        print(f" Exécution: Étape 5 : Alignement Sémantique (Fusion) | Version: [{version_actuelle.upper()}]")
        print(f"*"*60)
        try:
            fusionner_donnees()
        except Exception as e:
            print(f"\n Arrêt du pipeline : Une erreur est constatée lors de l'étape 5 (Fusion).")
            print(f" Détail de l'erreur : {e}")
            sys.exit(1)

    if 6 in etapes_a_lancer:
        executer_etape("extraction_temporalite.py", "Étape 6 : Extraction des relations temporelles", version_actuelle)

    if 7 in etapes_a_lancer:
        executer_etape("comparaison_annotation_coref_temp.py", "Étape 7 : croisement (Coréférence vs Temporalité)", version_actuelle)

    if 8 in etapes_a_lancer:
        executer_etape("visualisation_core_temp.py", "Étape 8 : Dataviz et statistiques du croisement", version_actuelle)
        
    if 9 in etapes_a_lancer:
        executer_etape("extraction_balise_relation.py", "Étape 9 : Extraction des balises et relations (gSpan)", version_actuelle)

    if 10 in etapes_a_lancer:
        executer_etape("encodage_gspan.py", "Étape 10 : Encodage au format TXT pour gSpan", version_actuelle)

    if 11 in etapes_a_lancer:
        executer_etape("fouille_graphes.py", "Étape 11 : Fouille de sous-graphes fréquents avec gSpan", version_actuelle)
        
    if 12 in etapes_a_lancer:
        executer_etape("visualisation_motifs.py", "Étape 12 : Visualisation graphique des motifs (PNG)", version_actuelle)
        
    if 13 in etapes_a_lancer:
        executer_etape("visualisation_motifs_frequents.py", "Étape 13 : Séquençage des motifs et export CSV pour TraMineR", version_actuelle)
        
    if 14 in etapes_a_lancer:
        executer_etape("visualiser_grand_graphe.py", "Étape 14 : Visualisation Graphe par document)", version_actuelle)

    print("\n" + "*"*60)
    print(" Pipeline terminé sans erreur ")
    print(f" Les fichiers de sortie de la version '{version_actuelle}' ont été mis à jour.")
    print("*"*60)
    
if __name__ == "__main__":
    main()