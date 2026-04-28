import os
import glob
import subprocess


# Gestion automatique des chemins 

# BASE_DIR remonte d'un dossier ("pipeline") pour pointer sur la racine ("Français")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONLLU_INPUT = os.path.join(BASE_DIR, "data", "conllu_entree")
CONLLU_OUTPUT = os.path.join(BASE_DIR, "data", "conllu_sorti")

# CorPipe est un dossier séparé, situé au même niveau que le dossier Français"
DOSSIER_PARENT_GLOBAL = os.path.dirname(BASE_DIR)
CORPIPE_SCRIPT = os.path.join(DOSSIER_PARENT_GLOBAL, "crac2025-corpipe", "corpipe25.py")


# Script principal 


def main():
    # Création du dossier de sortie s'il n'existe pas
    os.makedirs(CONLLU_OUTPUT, exist_ok=True)
    
    fichiers_entree = glob.glob(os.path.join(CONLLU_INPUT, "*.conllu"))
    
    if not fichiers_entree:
        print(f" Étape 2 ignorée : aucun fichier d'entrée trouvé dans {CONLLU_INPUT}.")
        return



# Mode incrémental 
    fichiers_a_traiter = []
    for f_path in fichiers_entree:
        nom_fichier = os.path.basename(f_path) # ex: doc1.conllu
        # On remplace l'extension pour chercher le fichier généré par CorPipe
        nom_attendu = nom_fichier.replace(".conllu", ".15.conllu")
        fichier_attendu = os.path.join(CONLLU_OUTPUT, nom_attendu)
        
        if not os.path.exists(fichier_attendu):
            fichiers_a_traiter.append(f_path)


    if not fichiers_a_traiter:
        print(" Étape 2 ignorée : tous les fichiers sont déjà passés par CorPipe.")
        return

    print(f" Démarrage de l'étape 2 : inférence CorPipe ({len(fichiers_a_traiter)} nouveaux fichiers à traiter)")
    
    # Préparation de la commande pour le terminal
    try:
        cmd = [
            "python", CORPIPE_SCRIPT, 
            "--load", "ufal/corpipe25-corefud1.3-large-251101", 
            "--test"
        ] + fichiers_a_traiter + [
            "--exp", CONLLU_OUTPUT, 
            "--segment", "2560"
        ]
        
        # Exécution de CorPipe
        subprocess.run(cmd, check=True)
        print("\n Étape 2 terminée avec succès !")
        
    except subprocess.CalledProcessError as e:
        print(f"\n Erreur lors de l'exécution de CorPipe. Code d'erreur : {e.returncode}")
    except FileNotFoundError:
        print(f"\n Erreur : impossible de trouver le script CorPipe à cet emplacement :\n{CORPIPE_SCRIPT}")

if __name__ == "__main__":
    main()