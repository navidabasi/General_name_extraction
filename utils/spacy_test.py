# spacy_min.py
import re, unicodedata, sys
import spacy

# tiny normalizer to match later with exact keys
SPACE = re.compile(r"\s+")
def key_relaxed(s: str) -> str:
    s = SPACE.sub(" ", (s or "").strip()).casefold().replace("’","'")
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = "".join(ch for ch in s if ch.isalnum() or ch.isspace() or ch in "-'")
    s = SPACE.sub(" ", s).strip()
    return s if len(s.split()) >= 2 else ""

# load only NER for speed
nlp = spacy.load("en_core_web_sm", disable=["tagger","lemmatizer","morphologizer","parser","attribute_ruler","senter","tok2vec"])
nlp.enable_pipe("ner")

# read text from stdin or use a default sample
texts = [sys.stdin.read()] if not sys.stdin.isatty() else [
   """Please provide the dates of birth of everyone in your group and the full names of everyone in your group.
Traveler 1:
First Name: L
Last Name: Bronze
Date of Birth: 1955-12-03
Traveler 2:
First Name: C
Last Name: Bronze
Date of Birth: 1956-05-28"""
]

for doc in nlp.pipe(texts, batch_size=32):
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            disp = ent.text.strip()
            if len(disp()) < 2:
                continue

            false_positives = ["traveler", "travelers", "customer", "customers", 
                             "adult", "child", "infant", "youth", "guest", "guests"]
            if disp.lower() in false_positives:
                continue
            normalized = key_relaxed(disp)
            if normalized:  # Only print if normalization succeeded
                print(disp, "=>", normalized)
