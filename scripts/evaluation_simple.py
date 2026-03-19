"""
Script d'évaluation de la détection de mentions (Mention Detection).

Ce script compare les entités cliniques extraites manuellement dans le corpus E3C avec les prédictions générées par le modèle 
de coréférence (mT5-large / CorPipe).

L'évaluation repose sur trois scores fondamentaux :
- Vrais Positifs (TP) : Le modèle a trouvé une entité correctement marquée par l'annotateur humain.
- Faux Positifs (FP) : Le modèle a extrait une entité qui n'était pas marquée dans la référence .
- Faux Négatifs (FN) : Le modèle a omis une entité qui était présente dans la référence.

À partir de ces valeurs, le script calcule :
- La Précision : La proportion d'entités correctes parmi toutes celles extraites par le modèle.
- Le Rappel : La proportion d'entités extraites par le modèle parmi toutes celles qu'il fallait trouver.
- Le F1-Score : La moyenne harmonique de la précision et du rappel (mesure de performance globale).
"""

import os
import glob
import csv
import string
# Cette bibliothèque est utile pour la lecture et la manipulation d’annotations (UIMA/XMI)
# load_typesystem permet de charger la structure des annotations (types, attributs)
# load_cas_from_xmi permet de charger un fichier XMI contenant les annotations
from cassis import load_typesystem, load_cas_from_xmi

        
# Configurations des chemins
# Ce dossier contient les fichiers de référence annotés manuellement
XML_DIR = "data/xml_source"

# Fichier contenant les résultats de l'inférence du modèle
PREDICTIONS_CSV = "data/resultats_coreferences.csv"

# Définition stricte du système de types pour lire les fichiers UIMA/XMI du corpus E3C

TYPESYSTEM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<typeSystemDescription xmlns="http://uima.apache.org/resourceSpecifier">
  <types>
    <typeDescription>
      <name>de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Token</name>
      <supertypeName>uima.tcas.Annotation</supertypeName>
      <features>
        <featureDescription><name>order</name><rangeTypeName>uima.cas.Integer</rangeTypeName></featureDescription>
      </features>
    </typeDescription>
    <typeDescription>
      <name>de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence</name>
      <supertypeName>uima.tcas.Annotation</supertypeName>
    </typeDescription>
    <typeDescription>
      <name>webanno.custom.CLINENTITY</name>
      <supertypeName>uima.tcas.Annotation</supertypeName>
      <features>
        <featureDescription><name>entityID</name><rangeTypeName>uima.cas.String</rangeTypeName></featureDescription>
        <featureDescription><name>xtra</name><rangeTypeName>uima.cas.String</rangeTypeName></featureDescription>
        <featureDescription><name>entityIDEN</name><rangeTypeName>uima.cas.String</rangeTypeName></featureDescription>
        <featureDescription><name>discontinuous</name><rangeTypeName>uima.cas.String</rangeTypeName></featureDescription>
      </features>
    </typeDescription>
  </types>
</typeSystemDescription>
"""



def normaliser_texte(texte):
    """
    Nettoie une chaîne de caractères pour standardiser la comparaison.
    
    Convertit le texte en minuscules et supprime la ponctuation afin d'éviter 
    que des variations de formatage (ex: "Patient." vs "patient") ne soient 
    comptées comme des erreurs.
    """
    texte = texte.lower().strip()
    return texte.translate(str.maketrans('', '', string.punctuation))


def main():
    print("Chargement des annotations manuelles ")
    typesystem = load_typesystem(TYPESYSTEM_XML)
    xml_files = glob.glob(os.path.join(XML_DIR, "*.xml"))
    
    # Dictionnaire stockant les entités de référence par document
    gold_mentions = {}
    
    for file_path in xml_files:
        doc_id = os.path.splitext(os.path.basename(file_path))[0]
        try:
            with open(file_path, 'rb') as f:
                cas = load_cas_from_xmi(f, typesystem=typesystem, lenient=True)
            
            text = cas.sofa_string
            entities = cas.select('webanno.custom.CLINENTITY')
            mentions = [normaliser_texte(text[e.begin:e.end]) for e in entities]
            
            gold_mentions[doc_id] = mentions
        except Exception as e:
            # Affiche les erreurs liées aux attributs non gérés dans certains fichiers XMI
            print(f"Impossible de lire certaines balises XML sur {doc_id} ({e})")

    print("Chargement des prédictions du modèle...")
    # Dictionnaire stockant les entités prédites par le modèle
    ia_mentions = {}
    
    try:
        with open(PREDICTIONS_CSV, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                # Nettoyage de l'extension ".00" ajoutée par CorPipe
                doc_id = row['Document'].replace('.00', '')
                mention = normaliser_texte(row['Mention_Texte'])
                
                if doc_id not in ia_mentions:
                    ia_mentions[doc_id] = []
                ia_mentions[doc_id].append(mention)
    except Exception as e:
        print(f"Erreur de lecture du fichier des prédictions : {e}")
        return

    print("Comparaison et calcul des métriques \n")
    
    # Initialisation des compteurs d'évaluation
    vrais_positifs = 0
    faux_positifs = 0
    faux_negatifs = 0

    # Fusion des listes de documents pour évaluer l'ensemble du corpus de manière exhaustive
    tous_les_docs = set(gold_mentions.keys()).union(set(ia_mentions.keys()))

    for doc_id in tous_les_docs:
        vraies_entites = gold_mentions.get(doc_id, [])
        entites_predites = ia_mentions.get(doc_id, [])
        
        # Copies locales pour itération et suppression dynamique
        vraies_restantes = vraies_entites.copy()
        predites_restantes = entites_predites.copy()
        
        # Alignement strict entre prédictions et référence
        for pred in entites_predites:
            if pred in vraies_restantes:
                vrais_positifs += 1
                vraies_restantes.remove(pred)
                predites_restantes.remove(pred)
                
        # Les prédictions ne correspondant à aucune entité de référence sont des Faux Positifs
        faux_positifs += len(predites_restantes)
        # Les entités de référence non trouvées par le modèle sont des Faux Négatifs
        faux_negatifs += len(vraies_restantes)

    # Calcul des métriques de performance
    precision = vrais_positifs / (vrais_positifs + faux_positifs) if (vrais_positifs + faux_positifs) > 0 else 0
    rappel = vrais_positifs / (vrais_positifs + faux_negatifs) if (vrais_positifs + faux_negatifs) > 0 else 0
    f1_score = 2 * (precision * rappel) / (precision + rappel) if (precision + rappel) > 0 else 0

    # Affichage des résultats
    print("******************************************")
    print("Résultats de la détection de mentions")
    print("*******************************************")
    print(f"Mentions cliniques annotées manuellement (donc verité terrain) : {vrais_positifs + faux_negatifs}")
    print(f"Toutes les mentions (Modèle)       : {vrais_positifs + faux_positifs}")
    print("------------------------------------------")
    print(f"Vrais Positifs (TP)             : {vrais_positifs}")
    print(f"Faux Positifs (FP)              : {faux_positifs}")
    print(f"Faux Négatifs (FN)              : {faux_negatifs}")
    print("------------------------------------------")
    print(f"PRÉCISION                       : {precision * 100:.2f} %")
    print(f"RAPPEL                          : {rappel * 100:.2f} %")
    print(f"F1-SCORE                        : {f1_score * 100:.2f} %")
    print("==========================================")

if __name__ == "__main__":
    main()