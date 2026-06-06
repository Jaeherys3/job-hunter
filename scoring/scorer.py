import re
from scoring.english import detect_english_level, ENGLISH_HIGH, ENGLISH_OK

# Scoring oparty na rzadkich technologiach - te które faktycznie wyróżniają ofertę
# Podzielony na 3 poziomy:

# Poziom 1: Twoje core technologie - wysoka waga
TIER1 = {
    "databricks": 30,
    "apache airflow": 25,
    "airflow": 25,
    "azure data factory": 20,
    "adf": 20,
    "pyspark": 20,
    "delta lake": 15,
    "delta table": 15,
    "lakehouse": 15,
}

# Poziom 2: Technologie które znasz dobrze
TIER2 = {
    "azure": 10,
    "spark": 10,
    "etl": 8,
    "elt": 8,
    "data pipeline": 8,
    "pipeline": 5,
    "gcp": 5,
    "aws": 4,
}

# Poziom 3: Ogólne - mała waga bo prawie wszyscy mają
TIER3 = {
    "python": 3,
    "sql": 3,
    "data engineer": 3,
    "data engineering": 3,
}

# Kary za technologie których nie znasz (tylko gdy wymagane)
PENALTIES = {
    "scala":   -10,
    ".net":    -10,
    "java":    -8,
    "golang":  -8,
    "c#":      -8,
    "ruby":    -6,
}

# Normalizacja - max osiągalny score przy idealnym dopasowaniu
# Tier1 max (databricks+airflow+adf+pyspark) = 95, plus trochę tier2
MAX_SCORE = 95

def score_job(job: dict) -> int:
    text = f"{job.get('title', '')} {job.get('description', '')}".lower()

    score = 0
    matched = set()

    for kw, weight in {**TIER1, **TIER2, **TIER3}.items():
        if kw in text:
            # Unikaj podwójnego liczenia aliasów
            base = kw.split()[-1]
            if base not in matched:
                matched.add(base)
                score += weight

    # Kary za brakujące technologie (tylko w sekcji wymagań)
    req_text = _extract_requirements(text)
    for kw, penalty in PENALTIES.items():
        if kw in req_text:
            score += penalty

    level, _ = detect_english_level(text)
    if level == ENGLISH_HIGH:
        score -= 15
    elif level == ENGLISH_OK:
        score -= 7

    return int(min(100, max(0, (score / MAX_SCORE) * 100)))

def _extract_requirements(text: str) -> str:
    for pattern in [
        r"requirements?(.*?)(?:nice to have|benefits|we offer|$)",
        r"wymagani[ae](.*?)(?:mile widziane|oferujemy|$)",
        r"must have(.*?)(?:nice to have|$)",
    ]:
        m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1)
    return text
