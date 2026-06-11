import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


# Définition des chemins

Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Dossier_CSV = os.path.join(Base_dir, "data", "sortie_csv")
Fichier_csv = os.path.join(Dossier_CSV, "comparaison_coref_temp.csv")

def visualiser_anaalyse():
    print(" Chargement des données et calcul des statistiques")
    
    if not os.path.exists(Fichier_csv):
        print(f"Erreur : Le fichier {Fichier_csv} est introuvable.")
        return

    df = pd.read_csv(Fichier_csv)

    
    #  Créer des filtres 
    
    # Coréférence (CorPipe a trouvé  mais pas WebAnno)
    df_coref_only = df[df['type_temporel'] == 'Non annoté']
    
    # Temporalité  (WebAnno a trouvé mais pas CorPipe)
    df_temp_only = df[df['mention_id'] == 'Non détecté']
    
    # Présent dans les deux cas
    df_both = df[(df['type_temporel'] != 'Non annoté') & (df['mention_id'] != 'Non détecté')]

    
    #  Affichage statistiques 
    
    print("\n" + "*"*60)
    print(" Analyse statistique global")
    print("*"*60)
    print(f" Total des entités uniques  : {len(df)}")
    print(f" Entités annotés dans le corpus et détectés par CorPipe  : {len(df_both)}")
    print(f" Coréférence uniquement : {len(df_coref_only)}")
    print(f" Temporalité uniquement: {len(df_temp_only)}")
    
    print("\n Affichage des 10 coréférences uniquement :")
    print(df_coref_only['entité'].value_counts().head(10).to_string())
    
    print("\n Affichage des 10 temporalités uniquement :")
    print(df_temp_only['entité'].value_counts().head(10).to_string())
   

    
    # Visualisation 
    
    print(" Génération des graphiques en cours ")
    
    # Configuration du style visuel
    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Analyse du Croisement : Coréférence vs Temporalité', fontsize=16, fontweight='bold')

    
    # Graphique 1 : Distribution globale (Barplot)
    tailles = [len(df_both), len(df_coref_only), len(df_temp_only)]
    labels = ['Coref et temp', 'Coréférence unique', 'Temporalité unique']
    couleurs = ['#2ecc71', '#e74c3c', '#3498db']
    
    # Ajout de hue=labels et legend=False
    sns.barplot(x=labels, y=tailles, hue=labels, palette=couleurs, legend=False, ax=axes[0])
    
    sns.barplot(x=labels, y=tailles, palette=couleurs, ax=axes[0])
    axes[0].set_title('Répartition globale des entités', fontsize=12)
    axes[0].set_ylabel('Nombre d\'entités')
    for i, v in enumerate(tailles):
        axes[0].text(i, v + 20, str(v), ha='center', fontweight='bold')

    
    # Graphique 2 : Top 10 Coréférence uniquement
    top_coref = df_coref_only['entité'].value_counts().head(10)
    
    # Ajout de hue=top_coref.index et legend=False
    sns.barplot(x=top_coref.values, y=top_coref.index, hue=top_coref.index, palette='Reds_r', legend=False, ax=axes[1])
    axes[1].set_title('Top 10 : Coréférences uniquement \n(Non annotées en temporalité dans le corpus)', fontsize=12)
    axes[1].set_xlabel('Fréquence')




    # Graphique 3 : Top 10 Temporalité uniquement
    
    
    top_temp = df_temp_only['entité'].value_counts().head(10)
    
    # Ajout de hue=top_temp.index et legend=False
    sns.barplot(x=top_temp.values, y=top_temp.index, hue=top_temp.index, palette='Blues_r', legend=False, ax=axes[2])
 
    axes[2].set_title('Top 10 : Temporalités uniquement\n(Non détectées en coréférence par CorPipe)', fontsize=12)
    axes[2].set_xlabel('Fréquence')



    # Sauvegarde
    plt.tight_layout()
    chemin_image = os.path.join(Dossier_CSV, "dashboard_croisement.png")
    plt.savefig(chemin_image, dpi=300)
    print(f"Image est sauvegardée dans : {chemin_image}")
    
    # Affichage à l'écran 
    plt.show()

if __name__ == "__main__":
    visualiser_anaalyse()