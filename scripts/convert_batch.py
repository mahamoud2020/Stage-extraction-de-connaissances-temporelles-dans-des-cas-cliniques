"""
Script de conversion par lots (batch processing) du format XMI vers le format CoNLL-U.

Ce script permet d'automatiser la conversion de l'ensemble du corpus E3C (fichiers XML) vers le format d'entrée requis par 
le modèle de coréférence (CoNLL-U à 10 colonnes). 
Il itère sur un répertoire source, extrait dynamiquement l'identifiant de chaque document, et génère les fichiers pré-formatés 
correspondants dans un répertoire cible.

Cette étape de prétraitement permet d'outrepasser les contraintes syntaxiques du parseur natif du modèle en fournissant 
des fichiers où seules la segmentation des phrases et la tokenisation sont renseignées, les autres attributs linguistiques 
étant neutralisés par des traits de soulignement ("_").
"""

import os
import glob # Permet de récupérer des fichiers via des motifs (ex : *.xml)

# La bibliothèque "cassis" est utilisée pour la lecture et la manipulation d’annotations (UIMA/XMI)
# load_typesystem permet de charger la structure des annotations (types, attributs)
# load_cas_from_xmi permet de charger un fichier XMI contenant les annotations
from cassis import load_typesystem, load_cas_from_xmi


# Configurations des chemins
# Répertoire contenant les fichiers du corpus E3C
INPUT_DIR = "data/xml_source"

# Répertoire de destination pour les fichiers convertis, prêts pour l'inférence
OUTPUT_DIR = "data/conllu_entree"

# Définition du système de types UIMA nécessaire à la lecture des fichiers.
# Limités aux annotations de segmentation (Token et Sentence).
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
  </types>
</typeSystemDescription>
"""

def main():
    """
    Fonction principale exécutant le traitement par lots sur le corpus.
    """
    typesystem = load_typesystem(TYPESYSTEM_XML)
    
    # Récupération exhaustive des chemins de tous les fichiers XML du répertoire source
    xml_files = glob.glob(os.path.join(INPUT_DIR, "*.xml"))
    
    if not xml_files:
        print(f"Aucun fichier XML trouvé dans le répertoire {INPUT_DIR}")
        return
        
    print(f"{len(xml_files)} documents trouvés. Début du prétraitement par lots...\n")
    
    # Itération sur chaque document du corpus
    for file_path in xml_files:
        # Extraction de l'identifiant unique du document (ex: FR100003) pour nommer la sortie
        filename = os.path.basename(file_path)
        doc_id = os.path.splitext(filename)[0] 
        out_path = os.path.join(OUTPUT_DIR, f"{doc_id}.conllu")
        
        try:
            # Lecture des annotations 
            with open(file_path, 'rb') as f:
                cas = load_cas_from_xmi(f, typesystem=typesystem, lenient=True)
                
            text = cas.sofa_string
            sentences = list(cas.select('de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence'))
            tokens = list(cas.select('de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Token'))

            # Génération du fichier cible au format CoNLL-U
            with open(out_path, 'w', encoding='utf-8') as out_f:
                # Injection dynamique de l'identifiant du document dans l'en-tête (standard CorefUD)
                out_f.write(f"# newdoc id = {doc_id}\n")
                
                sent_id = 1
                for sentence in sentences:
                    # Écriture des métadonnées de la phrase courante
                    out_f.write(f"# sent_id = {sent_id}\n")
                    out_f.write(f"# text = {text[sentence.begin:sentence.end]}\n")
                    
                    # Sélection des tokens inclus dans les limites de la phrase
                    sent_tokens = [t for t in tokens if t.begin >= sentence.begin and t.end <= sentence.end]
                    
                    word_id = 1
                    for token in sent_tokens:
                        token_text = text[token.begin:token.end].strip()
                        if not token_text:
                            continue
                            
                        # Structuration tabulaire (10 colonnes).
                        # Neutralisation des champs syntaxiques par des "_" pour éviter les rejets du parseur.
                        line = f"{word_id}\t{token_text}\t{token_text}\t_\t_\t_\t_\t_\t_\t_\n"
                        out_f.write(line)
                        word_id += 1
                    
                    # Respect de la convention CoNLL-U : ligne vide marquant la fin d'une phrase
                    out_f.write("\n")
                    sent_id += 1
                    
            print(f"Document {doc_id} prétraité avec succès.")
            
        except Exception as e:
            print(f"Erreur lors du traitement du document {doc_id} : {e}")

    print("\nOpération terminée. Le corpus pré-formaté est disponible dans le répertoire de sortie.")

if __name__ == "__main__":
    main()