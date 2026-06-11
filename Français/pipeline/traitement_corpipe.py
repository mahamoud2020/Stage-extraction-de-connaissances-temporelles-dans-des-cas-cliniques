import os
import glob
import subprocess


# Gestion automatique des chemins 


Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

Conllu_input = os.path.join(Base_dir, "data", "conllu_entree")
Conllu_output = os.path.join(Base_dir, "data", "conllu_sorti")

# CorPipe est un dossier séparé, situé au même niveau que le dossier Français"
Dossier_parent_global  = os.path.dirname(Base_dir)
Corpipe_script  = os.path.join(Dossier_parent_global, "crac2025-corpipe", "corpipe25.py")


# Script principal 


def main():
    # Création du dossier de sortie s'il n'existe pas
    os.makedirs(Conllu_output, exist_ok=True)
    
    fichiers_entree = glob.glob(os.path.join(Conllu_input, "*.conllu"))
    
    if not fichiers_entree:
        print(f" Étape 2 ignorée : aucun fichier d'entrée trouvé dans {Conllu_input}.")
        return



# Mode incrémental 
    fichiers_a_traiter = []
    for f_path in fichiers_entree:
        nom_fichier = os.path.basename(f_path) # ex: doc1.conllu
        # On remplace l'extension pour chercher le fichier généré par CorPipe
        nom_attendu = nom_fichier.replace(".conllu", ".15.conllu")
        fichier_attendu = os.path.join(Conllu_output, nom_attendu)
        
        if not os.path.exists(fichier_attendu):
            fichiers_a_traiter.append(f_path)


    if not fichiers_a_traiter:
        print(" Étape 2 ignorée : tous les fichiers sont déjà passés par CorPipe.")
        return

    print(f" Démarrage de l'étape 2 : inférence CorPipe ({len(fichiers_a_traiter)} nouveaux fichiers à traiter)")
    
    # Préparation de la commande pour le terminal
    try:
        cmd = [
            "python", Corpipe_script, 
            "--load", "ufal/corpipe25-corefud1.3-large-251101", 
            "--test"
        ] + fichiers_a_traiter + [
            "--exp", Conllu_output, 
            "--segment", "2560"
        ]
        
        # Exécution de CorPipe
        subprocess.run(cmd, check=True)
        print("\n Étape 2 terminée avec succès !")
        
    except subprocess.CalledProcessError as e:
        print(f"\n Erreur lors de l'exécution de CorPipe. Code d'erreur : {e.returncode}")
    except FileNotFoundError:
        print(f"\n Erreur : impossible de trouver le script CorPipe à cet emplacement :\n{Corpipe_script}")

if __name__ == "__main__":
    main()