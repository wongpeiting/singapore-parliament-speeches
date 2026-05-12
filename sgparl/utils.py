import re

import nltk
import pandas as pd


_nltk_ready = False


def _ensure_nltk_data():
    """Download punkt tokenizer if not already present (checked once per process)."""
    global _nltk_ready
    if _nltk_ready:
        return
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)
    _nltk_ready = True


# All recognised title/rank prefixes, shared across both regex paths.
# Sorted longest-first so regex alternation matches greedily.
_PREFIXES = (
    r"Assoc\.?\s*Prof\.?"   # Academic
    r"|Prof\.?|Dr"
    r"|Mr|Mrs|Miss|Mdm|Ms"  # Standard
    r"|Madam|Encik|Inche|Cik"  # Gendered (Malay)
    r"|Haji|Hajjah"          # Islamic honorific
    r"|BG|MG|RAdm|RADM|Cdre"  # Military/naval
    r"|Maj|Col|LTC|CPT|SLTC|Brig"
    r"|Tun|Dato|Tuan"        # Honorary
    r"|Hon\.?|Er|Ir"         # Engineering / honorary
)


def get_mp_name(x):
    """Extract clean MP name from raw speaker string.

    Handles both post-2012 format ("The Minister for Health (Mr Ong Ye Kung)")
    and pre-2012 format ("Mr D. S. Marshall (Cairnhill)", "Mr R. Jumabhoy").

    Ported from transform/__init__.py, extended for pre-2012 names.
    """
    if pd.isna(x) if not isinstance(x, str) else x == "":
        return ""

    # Normalise whitespace and strip military [NS] flag
    x = re.sub(r'[\r\n]+', ' ', x).strip()
    x = re.sub(r'\s+', ' ', x)
    x = re.sub(r'\s*\[NS\]\s*', ' ', x).strip()

    # Speaker/Deputy Speaker in the Chair — not a named MP
    if re.search(r"\[.*Speaker.*in the Chair\]", x, re.IGNORECASE):
        return x.strip()
    if "SPEAKER" in x:
        temp = re.search(r"\(([^()]+)\(", x)
        if temp:
            match = re.sub(r"^(?:Mr|Mrs|Miss|Mdm|Ms|Dr|Prof)\s+", "", temp.group(1))
            return match.strip()
        else:
            return ""

    # Strip leading "The Minister for...(Mr Name)" — extract name from parens
    paren_match = re.search(
        r"\((?:" + _PREFIXES + r")\s+([^)]+)\)", x
    )
    if paren_match:
        name = paren_match.group(1).strip()
        # Remove constituency in nested parens or trailing constituency
        name = re.sub(r"\s*\([^)]*\)\s*$", "", name)
        return name.strip().rstrip(".")

    # Direct "Mr Name" format — match name including periods (for initials)
    # and apostrophes (for names like Ch'ng)
    match = re.search(
        r"(?:" + _PREFIXES + r")\s+([\w\s.'\u2019-]+)", x
    )
    if match:
        name = match.group(1).strip()
        # Remove constituency in parens at the end: "D. S. Marshall (Cairnhill)"
        name = re.sub(r"\s*\([^)]*\)\s*$", "", name)
        # Remove trailing punctuation
        name = name.rstrip(".:;,")
        # Collapse initials: "D. S. Marshall" -> "D S Marshall"
        # (keep readable but remove trailing dots)
        name = re.sub(r"\.\s*", ". ", name).strip().rstrip(".")
        # Remove " and Mr ..." artifacts (two speakers merged)
        name = re.sub(r"\s+and\s+(?:Mr|Mrs|Dr|Prof)\b.*$", "", name)
        return name.strip()

    # Fallback: no recognized prefix found
    return ""


def count_syllables(word):
    """Count syllables in a word using vowel-group heuristic.

    Ported from transform/speeches.py.
    """
    vowels = "aeiouy"
    word = word.lower()
    count = 0
    prev_char_was_vowel = False

    for char in word:
        if char in vowels:
            if not prev_char_was_vowel:
                count += 1
            prev_char_was_vowel = True
        else:
            prev_char_was_vowel = False

    if word.endswith(("e", "es", "ed")) and not word.endswith(("le", "ble", "ple")):
        count -= 1
    if count == 0:
        count = 1

    return count


def calc_number_of_syllables(text):
    """Calculate total syllables in a text string."""
    _ensure_nltk_data()
    words = nltk.word_tokenize(text)
    return sum(count_syllables(word) for word in words)


def calc_number_of_sentences(text):
    """Count sentences by splitting on sentence-ending punctuation."""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s for s in sentences if s.strip()]
    return max(len(sentences), 1)


def count_words_and_characters(text):
    """Return (num_words, num_characters) for a text string."""
    words = text.split()
    num_words = len(words)
    num_characters = len(re.findall(r"[a-zA-Z]", text))
    return num_words, num_characters
