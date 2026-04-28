import os
import subprocess
import sys

def executer_etape(nom_script, description):
    print(f"\n" + "="*60)
    print(f"   Exécution: {description}")
    print(f"="*60)
    
    # Chemin vers le script dans le dossier pipeline
    chemin_script = os.path.join("pipeline", nom_script)
    
    if not os.path.exists(chemin_script):
        print(f" Erreur : Le fichier {chemin_script} est introuvable.")
        sys.exit(1)
        
    try:
        # subprocess.run est la méthode sécurisée pour lancer d'autres scripts
        subprocess.run([sys.executable, chemin_script], check=True)
    except subprocess.CalledProcessError:
        print(f"\n Arret du pipeline : Une erreur est constatée lors de l'étape '{nom_script}'.")
        sys.exit(1) 

def main():
    print("\n" + "*"*60)
    print("   Démarrage du pipeline ")
    print("*"*60)

    # Lancement ordonné des 3 modules
    executer_etape("traitement_udpipe.py", "ÉTAPE 1 : Parsing syntaxique (UDPipe 2)")
    executer_etape("traitement_corpipe.py", "ÉTAPE 2 : Inférence des coréférences (CorPipe)")
    executer_etape("traitement_extraction.py", "ÉTAPE 3 : Extraction des mentions et génération CSV")

    print("\n" + "*"*60)
    print("  Pipeline terminé !")
    print("  Les tableaux de résultats sont disponibles dans 'data/sortie_csv/'")
    print("*"*60 + "\n")

if __name__ == "__main__":
    main()