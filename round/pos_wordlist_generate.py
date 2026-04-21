import random
from nltk.corpus import wordnet as wn
import json


def get_words_by_pos(pos_tag):
    """Returns a list of unique words for a given part of speech."""
    words = set()
    for synset in wn.all_synsets(pos_tag):
        # We take the first lemma of each synset for simplicity
        name = synset.lemmas()[0].name().replace('_', ' ')
        # Take only the first word
        name = name.split()[0]
        if name in words:
            continue
        words.add(name)
    return list(words)


def create_wordlist():
    wordlist = {
        "adjective": get_words_by_pos('a'),
        "noun": get_words_by_pos('n')
    }
    with open("wordlist.json", "w") as f:
        json.dump(wordlist, f)

create_wordlist()