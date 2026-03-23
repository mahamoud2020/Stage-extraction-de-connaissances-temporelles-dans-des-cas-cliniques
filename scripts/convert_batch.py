"""
Script de conversion par lots (batch processing) du format XMI vers le format CoNLL-U.

Ce script permet d'automatiser la conversion de l'ensemble du corpus E3C (fichiers XML) vers le format d'entrée requis par 
le modèle de coréférence (CoNLL-U à 10 colonnes). 
Il intègre spaCy pour enrichir les données avec des lemmes, des POS tags et des dépendances syntaxiques, 
tout en préservant la tokenisation stricte du corpus E3C.
"""

import os
import glob
import spacy
from spacy.tokens import Doc
from cassis import load_typesystem, load_cas_from_xmi

# Configurations des chemins
INPUT_DIR = "data/xml_source"
OUTPUT_DIR = "data/conllu_entree"

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
    # --- NOUVEAU : Chargement de spaCy ---
    print("Chargement du modèle linguistique spaCy (fr_core_news_sm)...")
    try:
        nlp = spacy.load("fr_core_news_sm")
    except OSError:
        print("Erreur : Le modèle français n'est pas installé.")
        print("Veuillez lancer : python -m spacy download fr_core_news_sm")
        return
    # -------------------------------------

    typesystem = load_typesystem(TYPESYSTEM_XML)
    xml_files = glob.glob(os.path.join(INPUT_DIR, "*.xml"))
    
    if not xml_files:
        print(f"Aucun fichier XML trouvé dans le répertoire {INPUT_DIR}")
        return
        
    print(f"{len(xml_files)} documents trouvés. Début du prétraitement par lots...\n")
    
    for file_path in xml_files:
        filename = os.path.basename(file_path)
        doc_id = os.path.splitext(filename)[0] 
        out_path = os.path.join(OUTPUT_DIR, f"{doc_id}.conllu")
        
        try:
            with open(file_path, 'rb') as f:
                cas = load_cas_from_xmi(f, typesystem=typesystem, lenient=True)
                
            text = cas.sofa_string
            sentences = list(cas.select('de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence'))
            tokens = list(cas.select('de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Token'))

            with open(out_path, 'w', encoding='utf-8') as out_f:
                out_f.write(f"# newdoc id = {doc_id}\n")
                
                sent_id = 1
                for sentence in sentences:
                    out_f.write(f"# sent_id = {sent_id}\n")
                    out_f.write(f"# text = {text[sentence.begin:sentence.end]}\n")
                    
                    sent_tokens = [t for t in tokens if t.begin >= sentence.begin and t.end <= sentence.end]
                    
                    # Préparation des mots pour spaCy 
                    mots_de_la_phrase = []
                    for token in sent_tokens:
                        token_text = text[token.begin:token.end].strip()
                        if token_text:
                            mots_de_la_phrase.append(token_text)
                    
                    if not mots_de_la_phrase:
                        continue
                    
                    # Forcer spaCy à utiliser la tokenisation du corpus E3C
                    doc = Doc(nlp.vocab, words=mots_de_la_phrase)
                    # Appliquer le pipeline (POS, Lemmes, Dépendances, etc)
                    for name, proc in nlp.pipeline:
                        doc = proc(doc)

                    # ***********************
                    
                    word_id = 1
                    # Extraction des attributs avec spaCy 
                    for spacy_token in doc:
                        forme = spacy_token.text
                        lemme = spacy_token.lemma_ if spacy_token.lemma_ else "_"
                        upos = spacy_token.pos_ if spacy_token.pos_ else "_"
                        xpos = "_"
                        feats = str(spacy_token.morph) if spacy_token.morph else "_"
                        
                        # Gestion de l'arbre de dépendance 
                        head = spacy_token.head.i + 1 if spacy_token.head.i != spacy_token.i else 0
                        deprel = spacy_token.dep_ if spacy_token.dep_ else "_"
                        
                        deps = "_"
                        misc = "_"
                        
                        # Assemblage de la ligne
                        line = f"{word_id}\t{forme}\t{lemme}\t{upos}\t{xpos}\t{feats}\t{head}\t{deprel}\t{deps}\t{misc}\n"
                        out_f.write(line)
                        word_id += 1
                    # 
                    
                    out_f.write("\n")
                    sent_id += 1
                    
            print(f"Document {doc_id} prétraité avec succès.")
            
        except Exception as e:
            print(f"Erreur lors du traitement du document {doc_id} : {e}")

    print("\nOpération terminée. Le corpus pré-formaté est disponible dans le répertoire de sortie.")

if __name__ == "__main__":
    main()