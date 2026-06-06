"""
Wykrywanie wymaganego poziomu angielskiego w ofercie.

Jedno wspolne zrodlo prawdy dla main.py i scorer.py.
Twoj poziom: B1. Logika:
  - HIGH  (C1/C2/fluent/native/biegly)  -> realnie poza zasiegiem -> domyslnie ODRZUC
  - B2    (B2/upper-intermediate/dobry) -> graniczne -> domyslnie ZOSTAW, ale oznacz
  - brak informacji                     -> ZOSTAW (nie karz za brak danych)

Kluczowe: uzywamy granic slow (\\b), zeby "B2B" nie wpadlo jako "B2",
a "EC2" jako "C2".
"""

import re

# --- Frazy oznaczajace poziom POWYZEJ B1 (ang. + pol.) ---
HIGH_ENGLISH_PATTERNS = [
    r"\bc1\b",
    r"\bc2\b",
    r"\bfluent\b",
    r"\bfluency\b",
    r"\badvanced english\b",
    r"\benglish\s*[-:]?\s*advanced\b",
    r"\bnative\b",
    r"\bnear[- ]?native\b",
    r"\bexcellent (?:english|command of english)\b",
    r"\bproficient\b",
    r"\bproficiency\b",
    # polski
    r"\bbiegł\w*\b",                       # biegła / biegłej / biegle
    r"\bzaawansowan\w* angielsk\w*\b",
    r"\bswobodn\w* (?:komunikacj\w*|posługiwani\w*)",
]

# --- Frazy oznaczajace ~B2 (graniczne dla B1) ---
MEDIUM_ENGLISH_PATTERNS = [
    r"\bb2\b",
    r"\bupper[- ]intermediate\b",
    r"\bvery good (?:command of )?english\b",
    r"\bgood (?:command of )?english\b",
    r"\bstrong english\b",
    # polski
    r"\bdobr\w* (?:znajomość )?(?:język\w* )?angielsk\w*\b",
    r"\bkomunikatywn\w* angielsk\w*\b",
]

_HIGH_RE = [re.compile(p) for p in HIGH_ENGLISH_PATTERNS]
_MED_RE = [re.compile(p) for p in MEDIUM_ENGLISH_PATTERNS]

# Poziomy zwracane przez detect_english_level()
ENGLISH_NONE = "none"      # brak informacji
ENGLISH_OK = "ok"          # B2 / graniczne
ENGLISH_HIGH = "high"      # C1/C2/fluent -> powyzej Twojego poziomu


def detect_english_level(*texts: str) -> tuple[str, str]:
    """
    Zwraca (poziom, dopasowana_frazа).
    poziom in {ENGLISH_NONE, ENGLISH_OK, ENGLISH_HIGH}.
    Przyjmuje dowolna liczbe pol tekstowych (title, description, requirements...).
    """
    text = " ".join(t for t in texts if t).lower()

    for rx in _HIGH_RE:
        m = rx.search(text)
        if m:
            return ENGLISH_HIGH, m.group(0)

    for rx in _MED_RE:
        m = rx.search(text)
        if m:
            return ENGLISH_OK, m.group(0)

    return ENGLISH_NONE, ""


def english_label(level: str, matched: str) -> str:
    """Czytelna etykieta do digestu/logow."""
    if level == ENGLISH_HIGH:
        return f"!! Wysoki angielski ({matched.upper()})"
    if level == ENGLISH_OK:
        return f"Angielski ~B2 ({matched})"
    return ""


if __name__ == "__main__":
    # Szybki test pulapek
    cases = [
        ("Kontrakt B2B, Data Engineer", ENGLISH_NONE),       # B2B != B2
        ("AWS EC2, S3, Databricks", ENGLISH_NONE),           # EC2 != C2
        ("English: C1 required", ENGLISH_HIGH),
        ("Wymagany angielski na poziomie B2", ENGLISH_OK),
        ("Fluent English is a must", ENGLISH_HIGH),
        ("Biegła znajomość języka angielskiego", ENGLISH_HIGH),
        ("Komunikatywny angielski w mowie i piśmie", ENGLISH_OK),
        ("Dobra znajomość języka angielskiego", ENGLISH_OK),
        ("Python, SQL, Spark", ENGLISH_NONE),
        ("Native English speaker preferred", ENGLISH_HIGH),
        ("Umowa B2B + angielski C2", ENGLISH_HIGH),           # B2B ignorowane, C2 lapane
    ]
    ok = 0
    for text, expected in cases:
        level, matched = detect_english_level(text)
        status = "OK " if level == expected else "BLAD"
        if level == expected:
            ok += 1
        print(f"[{status}] {text[:45]:<45} -> {level:<5} ({matched})")
    print(f"\n{ok}/{len(cases)} przeszlo")
