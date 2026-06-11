import os
import pandas as pd

#  On calcule le chemin exact de manière robuste, peu importe d'où on lance le script
Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
chemin_csv = os.path.join(Base_dir, "data", "sortie_csv", "relations_temporelles_evenements.csv")

def compter():
    # Vérification de sécurité
    if not os.path.exists(chemin_csv):
        print(f"Erreur : Le fichier est introuvable au chemin : {chemin_csv}")
        return
        
    #  Charger le fichier CSV
    df = pd.read_csv(chemin_csv)
    
    #  Isoler les entités sources et cibles
    sources = df[['doc', 'source_id', 'source_type']].rename(columns={'source_id': 'id', 'source_type': 'type'})
    cibles = df[['doc', 'cible_id', 'cible_type']].rename(columns={'cible_id': 'id', 'cible_type': 'type'})
    
    #  Fusionner les deux et supprimer les doublons (pour ne pas compter 2 fois la même entité)
    entites_uniques = pd.concat([sources, cibles]).drop_duplicates()
    
    # Faire les totaux
    comptage = entites_uniques['type'].value_counts()
    
    
    print("Bilan des informations temporelles")
    print("*"*50)
    print(f"Total des relations TIMEX3     : {len(df)}")
    print(f"Total des EVENT uniques : {len(entites_uniques)}")
    print("*" * 50)
    print(f"Événements (EVENT)             : {comptage.get('EVENT', 0)}")
    print(f"Expressions temporelles (TIMEX3): {comptage.get('TIMEX3', 0)}")
    print("*"*50 + "\n")

if __name__ == "__main__":
    compter()