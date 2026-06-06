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

# Fold polskich diakrytykow -> ASCII, zeby wzorce lapaly "płynny" i "plynny".
_PL_MAP = str.maketrans("ąćęłńóśźż", "acelnoszz")


def _fold(*texts: str) -> str:
    return " ".join(t for t in texts if t).lower().translate(_PL_MAP)


# --- Frazy oznaczajace poziom POWYZEJ B1 (ang. + pol., zapis po foldzie = ASCII) ---
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
    # polski (ASCII po foldzie)
    r"\bbiegl\w*\b",                              # biegla / bieglej / biegle
    r"\bplynn\w*(?:\s+\w+){0,3}\s+angielsk\w*",   # plynny/plynnego ... angielski
    r"\bzaawansowan\w* angielsk\w*\b",
    r"\bswobodn\w* (?:komunikacj\w*|poslugiwani\w*)",
]

# --- Frazy oznaczajace ~B2 (graniczne dla B1) ---
MEDIUM_ENGLISH_PATTERNS = [
    r"\bb2\b",
    r"\bupper[- ]intermediate\b",
    r"\bvery good (?:command of )?english\b",
    r"\bgood (?:command of )?english\b",
    r"\bstrong english\b",
    # polski (ASCII po foldzie)
    r"\bdobr\w* (?:znajomosc )?(?:jezyk\w* )?angielsk\w*\b",
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
    text = _fold(*texts)

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


# --- Ocena na podstawie USTRUKTURYZOWANEJ listy jezykow (np. JustJoin: en C1) ---
# Izolujemy poziom KONKRETNIE angielskiego - "fr C1" nie moze odrzucic oferty,
# w ktorej angielski jest na B1.
_EN_CODES = {"en", "eng", "english", "angielski"}
CEFR_HIGH = {"c1", "c2"}
CEFR_OK = {"b2"}
CEFR_LOW = {"a1", "a2", "b1"}   # w zasiegu B1 -> nie karzemy


def _cefr_bucket(level: str) -> str | None:
    lvl = (level or "").strip().lower()
    if lvl in CEFR_HIGH:
        return ENGLISH_HIGH
    if lvl in CEFR_OK:
        return ENGLISH_OK
    if lvl in CEFR_LOW:
        return ENGLISH_NONE
    return None  # nieznany/ brak poziomu


# Sygnaly w TRESCI ktore dotycza KONKRETNIE angielskiego (wymagaja "english"/"angielsk"
# w poblizu), wiec nie zlapia "fluent French" ani francuskiego C1.
HIGH_EN_SPECIFIC = [
    r"\bfluent (?:in )?english\b",
    r"\bfluency in english\b",
    r"\bnative(?:[- ]?like)? english\b",
    r"\bnear[- ]?native english\b",
    r"\b(?:advanced|excellent|proficient|proficiency)\b[^.]{0,20}\benglish\b",
    r"\benglish\b[^.]{0,20}\b(?:c1|c2|advanced|fluent|native|proficien\w*)\b",
    # polski (ASCII po foldzie)
    r"plynn\w*(?:\s+\w+){0,3}\s+angielsk\w*",
    r"biegl\w*(?:\s+\w+){0,3}\s+angielsk\w*",
    r"angielsk\w*(?:\s+\w+){0,3}\s+(?:biegl\w*|plynn\w*|zaawansowan\w*|c1|c2)",
    r"zaawansowan\w*(?:\s+\w+){0,3}\s+angielsk\w*",
]
OK_EN_SPECIFIC = [
    r"\b(?:good|very good|strong|upper[- ]intermediate)\b[^.]{0,20}\benglish\b",
    r"\benglish\b[^.]{0,15}\bb2\b",
    # polski (ASCII po foldzie)
    r"(?:dobr\w*|komunikatywn\w*)(?:\s+\w+){0,3}\s+angielsk\w*",
    r"angielsk\w*(?:\s+\w+){0,3}\s+(?:b2|komunikatywn\w*|dobr\w*)",
]
_HIGH_EN_RE = [re.compile(p) for p in HIGH_EN_SPECIFIC]
_OK_EN_RE = [re.compile(p) for p in OK_EN_SPECIFIC]


def assess_english(languages: list | None, *fallback_texts: str) -> tuple[str, str]:
    """
    Ocena poziomu angielskiego, warstwowo (od najmocniejszego sygnalu):

    1. TRESC z angielsko-specyficznym sygnalem PLYNNOSCI (fluent/native/płynny/biegły...)
       -> HIGH. Wygrywa nawet nad tagiem "B2" w strukturze (oferta realnie chce plynnosci).
    2. USTRUKTURYZOWANY poziom angielskiego (np. JustJoin "en C1") - izolujemy angielski,
       wiec "fr C1" nie zaszkodzi.
    3. TRESC z sygnalem ~B2 -> OK.
    4. Brak ustrukturyzowanego poziomu -> ostateczny fallback (regex po calym tekscie).

    Zwraca (poziom, etykieta_dopasowania).
    """
    text = _fold(*fallback_texts)

    # 1. Tresc: plynnosc angielskiego (najsilniejszy sygnal)
    for rx in _HIGH_EN_RE:
        m = rx.search(text)
        if m:
            return ENGLISH_HIGH, m.group(0).strip()

    # 2. Ustrukturyzowany poziom angielskiego
    struct = None
    for lang in languages or []:
        if str(lang.get("code", "")).lower() in _EN_CODES:
            struct = _cefr_bucket(lang.get("level"))
            struct_lvl = str(lang.get("level", "")).upper()
            break
    if struct == ENGLISH_HIGH:
        return ENGLISH_HIGH, f"EN {struct_lvl}"

    # 3. Tresc: sygnal ~B2
    for rx in _OK_EN_RE:
        m = rx.search(text)
        if m:
            return ENGLISH_OK, m.group(0).strip()
    if struct == ENGLISH_OK:
        return ENGLISH_OK, f"EN {struct_lvl}"
    if struct == ENGLISH_NONE:
        return ENGLISH_NONE, f"EN {struct_lvl}"  # B1/A2 -> w zasiegu

    # 4. Brak ustrukturyzowanego poziomu (np. NFJ "en MUST" bez poziomu) -> pelny regex
    return detect_english_level(*fallback_texts)


def foreign_required_languages(languages: list | None) -> list:
    """Zwraca kody wymaganych jezykow INNYCH niz angielski (np. ['fr', 'de'])."""
    out = []
    for lang in languages or []:
        code = str(lang.get("code", "")).lower()
        if code and code not in _EN_CODES and lang.get("required"):
            out.append(code)
    return out


def required_languages_outside(languages: list | None, known_codes) -> list:
    """
    Zwraca kody jezykow WYMAGANYCH (required=True), ktorych NIE ma na liscie
    znanych przez kandydata (known_codes). To wlasnie one dyskwalifikuja oferte.
    Np. known={'pl','en','ru'}, oferta wymaga 'fr' -> zwroci ['fr'].
    """
    known = {str(c).lower() for c in known_codes}
    out = []
    for lang in languages or []:
        code = str(lang.get("code", "")).lower()
        if code and lang.get("required") and code not in known:
            out.append(code)
    return out


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
