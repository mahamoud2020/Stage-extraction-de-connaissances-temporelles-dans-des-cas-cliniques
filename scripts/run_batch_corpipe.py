"""
Script d'automatisation de l'inférence (wrapper) pour l'outil CorPipe.

Ce script permet d'exécuter le modèle de résolution de coréférence sur l'ensemble du corpus pré-formaté. 
L'objectif principal est d'optimiser l'utilisation des ressources matérielles (mémoire et temps de calcul). 
En construisant une commande unique qui regroupe tous les fichiers d'entrée, le script force le système à ne charger les poids 
du modèle de langue (mT5-large) qu'une seule fois en mémoire. 
Le modèle peut traiter ensuite le lot complet de manière séquentielle.
"""

import os
import glob
import subprocess

# Configurer les chemins
# Répertoire contenant les fichiers CoNLL-U préparés pour l'inférence
INPUT_DIR = "data/conllu_entree"

# Répertoire de destination où le modèle sauvegardera les fichiers annotés
OUTPUT_DIR = "data/conllu_sortie"



def main():
    """
    Fonction principale permettant de construire et exécuter la commande système pour l'inférence.
    """

    # Récupération exhaustive des chemins de tous les fichiers à traiter
    files_to_process = glob.glob(os.path.join(INPUT_DIR, "*.conllu"))
    
    if not files_to_process:
        print(f"Aucun fichier d'entrée trouvé dans {INPUT_DIR}")
        return
        
    print(f"Initialisation de l'inférence sur un lot de {len(files_to_process)} documents.")
    print("Optimisation : chargement unique du modèle en mémoire pour le traitement continu.")
    
    # Construction de la commande d'exécution
    # Les arguments correspondent aux paramètres requis par  CorPipe :
    # --load  : Spécifie le modèle pré-entraîné à utiliser (ici, le modèle large de l'UFAL)
    # --exp   : Définit le répertoire de sortie pour les résultats 
    # --epoch : Fixe le numéro d'époque à 0 (paramètre technique de l'outil)
    # --test  : Active le mode inférence (évaluation) au lieu du mode entraînement
    command = [
        "python", "crac2025-corpipe/corpipe25.py",
        "--load", "ufal/corpipe25-corefud1.3-large-251101",
        "--exp", OUTPUT_DIR,
        "--epoch", "0",
        "--test"
    ] + files_to_process  # Ajout de l'ensemble des chemins d'entrée en tant qu'arguments finaux
    
    # Exécution de la commande via le sous-processus système
    # Cette étape délègue le contrôle au script principal de CorPipe
    subprocess.run(command)
    
    print("\nInférence terminée avec succès.")
    print(f"Les prédictions du modèle sont disponibles dans le répertoire : {OUTPUT_DIR}")

if __name__ == "__main__":
    main()