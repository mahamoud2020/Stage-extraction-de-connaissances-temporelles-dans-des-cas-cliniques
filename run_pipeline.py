import subprocess
import os
import sys

def run_script(script_path, description):
    print(f"\n{'='*50}")
    print(f"Étape : {description}")
    print(f"{'='*50}")
    
    # Exécute le script en affichant sa sortie dans le terminal
    result = subprocess.run([sys.executable, script_path])
    
    if result.returncode != 0:
        print(f"\nErreur lors de l'exécution de {script_path}. Arrêt du pipeline.")
        sys.exit(1)

def main():
    print("Démararrage du pipeline de coréférence du corpus E3C")
    
    # On indique que les scripts se trouvent dans le dossier "scripts"
    scripts_dir = "scripts"
    
    # On lance les 4 étapes dans l'ordre
    run_script(os.path.join(scripts_dir, "convert_batch.py"), "Conversion XMI -> CoNLL-U")
    run_script(os.path.join(scripts_dir, "run_batch_corpipe.py"), "Inférence du modèle (CorPipe)")
    run_script(os.path.join(scripts_dir, "extraire_csv.py"), "Extraction des prédictions (CSV)")
    run_script(os.path.join(scripts_dir, "evaluation_simple.py"), "Évaluation Mention Detection")
    
    print("\nPipeline terminé avec succès !")

if __name__ == "__main__":
    main()