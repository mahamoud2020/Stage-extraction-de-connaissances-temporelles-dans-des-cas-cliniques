import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


# Définition des chemins
# ***********************************************************************************************

Base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Fichier_CSV = os.path.join(Base_dir, "data", "sortie_csv", "comparaison_coref_temp.csv")
Dossier_Sortie = os.path.join(Base_dir, "data", "sortie_csv")

def generer_charts():
    print(" Étape 8 : Lancement des analyses statistiques et graphiques")
    
    if not os.path.exists(Fichier_CSV):
        print(" Fichier introuvable. Veuillez lancer l'étape 7 d'abord")
        return

    # Chargement du fichier
    df = pd.read_csv(Fichier_CSV)
    
    # Conversion de la longueur en numérique (0 pour les "Non applicable")
    df['longueur_num'] = pd.to_numeric(df['longueur_chaine'], errors='coerce').fillna(0)
    
    sns.set_theme(style="whitegrid")

    
    # Graphique 1 : analyse globale
    # ********************************************************************************************

    print(" Génération du graphique global")
    fig1, axes1 = plt.subplots(1, 2, figsize=(16, 7))
    
    df_xml_only_g = df[(df['type_temporalite'] != 'Non annoté') & (df['coref'] == 'Non détecté')]
    df_coref_only_g = df[(df['type_temporalite'] == 'Non annoté') & (df['coref'] == 'Détecté')]
    df_both_g = df[(df['type_temporalite'] != 'Non annoté') & (df['coref'] == 'Détecté')]
    sizes_g = [len(df_xml_only_g), len(df_coref_only_g), len(df_both_g)]
    
    labels_g = [
        f'Temporalité unique\n({sizes_g[0]})', 
        f'Coréf unique\n({sizes_g[1]})', 
        f'Coréf et temp \n({sizes_g[2]})'
    ]
    colors_g = ['#ff9999', '#66b3ff', '#99ff99']
    
    axes1[0].pie(sizes_g, explode=(0.05, 0.05, 0.05), labels=labels_g, colors=colors_g, autopct='%1.1f%%', 
                 startangle=140, textprops={'fontsize': 11, 'fontweight': 'bold'})
    axes1[0].set_title('Répartition Globale des Entités\n(Singletons inclus)', fontsize=14, fontweight='bold', pad=20)
    
    df_xml_total = df[df['type_temporalite'] != 'Non annoté']
    type_counts = df_xml_total['type_temporalite'].value_counts()
    sns.barplot(x=type_counts.values, y=type_counts.index, ax=axes1[1], palette='viridis', hue=type_counts.index, legend=False)
    axes1[1].set_title('Distribution des Balises', fontsize=14, fontweight='bold', pad=20)
    axes1[1].set_xlabel("Nombre de balises extraites", fontsize=12)
    axes1[1].set_ylabel('Type de balise', fontsize=12)
    for i, v in enumerate(type_counts.values):
        axes1[1].text(v + (max(type_counts.values)*0.01), i, str(v), color='black', va='center', fontweight='bold')
        
    plt.tight_layout()
    img_global = os.path.join(Dossier_Sortie, "graphique_global.png")
    fig1.savefig(img_global, dpi=300, bbox_inches='tight')
    plt.close(fig1)
    print(f" Sauvegardé : {img_global}")

    
    # Graphique 2 : analyse détaillée
    # *********************************************************************************
    
    print(" Génération du graphique détaillé ")
    fig2, axes2 = plt.subplots(1, 2, figsize=(18, 8))
    
    # Séparation avec singletons vs sans singletons

    df_xml_only = df[(df['type_temporalite'] != 'Non annoté') & (df['coref'] == 'Non détecté')]
    df_inter_chaine = df[(df['type_temporalite'] != 'Non annoté') & (df['coref'] == 'Détecté') & (df['longueur_num'] >= 2)]
    df_inter_single = df[(df['type_temporalite'] != 'Non annoté') & (df['coref'] == 'Détecté') & (df['longueur_num'] == 1)]
    df_cp_chaine = df[(df['type_temporalite'] == 'Non annoté') & (df['coref'] == 'Détecté') & (df['longueur_num'] >= 2)]
    df_cp_single = df[(df['type_temporalite'] == 'Non annoté') & (df['coref'] == 'Détecté') & (df['longueur_num'] == 1)]
    
    sizes_d = [len(df_xml_only), len(df_inter_chaine), len(df_inter_single), len(df_cp_chaine), len(df_cp_single)]
    labels_d = [
        f'1. Temporalité unique \n({sizes_d[0]})', 
        f'2. Coréf et temp (sans singleton)\n({sizes_d[1]})',
        f'3. Coréf et temp (avec singleton)\n({sizes_d[2]})',
        f'4. Coréf unique (sans singleton)\n({sizes_d[3]})',
        f'5. Coréf unique (avec singleton)\n({sizes_d[4]})'
    ]
    colors_d = ['#ff9999', '#1f77b4', '#aec7e8', '#2ca02c', '#98df8a']
    
    axes2[0].pie(sizes_d, explode=(0.05, 0.05, 0.05, 0.05, 0.05), labels=labels_d, colors=colors_d, autopct='%1.1f%%', 
                 startangle=140, textprops={'fontsize': 10, 'fontweight': 'bold'})
    axes2[0].set_title('Analyse détaillée', fontsize=15, fontweight='bold', pad=20)
    
    # Graphique à Barres Groupées 
    df_xml_detail = df[df['type_temporalite'] != 'Non annoté'].copy()
    
    def classer_balise(row):
        if row['coref'] == 'Non détecté':
            return '1. Manqué par CorPipe'
        elif row['longueur_num'] == 1:
            return '2. Détecté (avec singleton)'
        else:
            return '3. Détecté (sans singleton)'

    df_xml_detail['Performance'] = df_xml_detail.apply(classer_balise, axis=1)

    ordre_balises = df_xml_detail['type_temporalite'].value_counts().index
    ordre_legende = ['1. Manqué par CorPipe', '2. Détecté (avec singleton)', '3. Détecté (sans singleton)']
    couleurs_barres = ['#ff9999', '#aec7e8', '#1f77b4'] 

    sns.countplot(
        data=df_xml_detail, 
        y='type_temporalite', 
        hue='Performance', 
        ax=axes2[1], 
        palette=couleurs_barres, 
        order=ordre_balises,
        hue_order=ordre_legende
    )
    
    axes2[1].set_title('Analyse croisée des coréférences et des balises extraites', fontsize=15, fontweight='bold', pad=20)
    axes2[1].set_xlabel("Nombre d'entités", fontsize=12)
    axes2[1].set_ylabel('Type de balise', fontsize=12)
    
    for container in axes2[1].containers:
        axes2[1].bar_label(container, fmt='%d', padding=3, fontsize=9, fontweight='bold')

    axes2[1].legend(title='Résultat CorPipe', loc='lower right', frameon=True)

    plt.tight_layout()
    
    img_detail = os.path.join(Dossier_Sortie, "graphique_detaille.png")
    fig2.savefig(img_detail, dpi=300, bbox_inches='tight')
    plt.close(fig2)
    print(f" Sauvegardé : {img_detail}")
    
    print(" Étape 8 terminée parfaitement.")

if __name__ == "__main__":
    generer_charts()