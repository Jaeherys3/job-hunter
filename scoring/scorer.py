import re

# Profil kandydata
PROFILE = {
    # === CORE - bardzo wysokie wagi ===
    "databricks":         20,
    "azure":              12,
    "airflow":            12,
    "apache airflow":     12,
    "pyspark":            12,
    "spark":              10,
    "python":             8,
    "sql":                8,
    "etl":                8,
    "elt":                8,
    "data engineer":      10,
    "data engineering":   10,
    "adf":                8,
    "azure data factory": 10,
    "pipeline":           5,
    "delta lake":         8,
    "delta":              5,
    "lakehouse":          8,
    # === ZNANE ===
    "gcp":                5,
    "aws":                4,
    "s3":                 3,
    "kafka":              3,
    # === BONUS za typ stanowiska ===
    "senior":             5,
    "lead":               3,
    "data platform":      8,
    "big data":           6,
}

# Kara za technologie których nie znasz (tylko gdy wymagane)
WEAK_SKILLS = {
    "scala":   -8,
    ".net":    -8,
    "java":    -6,
    "golang":  -6,
    "ruby":    -6,
}

HIGH_ENGLISH   = ["c1", "c2", "fluent english", "advanced english", "native english"]
MEDIUM_ENGLISH = ["b2", "good english", "strong english command", "upper intermediate"]

# Bazowy bonus za bycie ofertą data engineering (nawet bez szczegółowych tagów)
DATA_ROLE_KEYWORDS = ["data engineer", "data engineering", "data platform", "data pipeline"]

def score_job(job: dict) -> int:
    text = f"{job.get('title', '')} {job.get('description', '')}".lower()

    matched_keys = set()
    matched_score = 0
    for keyword, weight in PROFILE.items():
        if keyword in text:
            base_key = keyword.split()[-1]
            if base_key not in matched_keys:
                matched_keys.add(base_key)
                matched_score += weight

    # Kary tylko w sekcji wymagań
    requirements_text = _extract_requirements(text)
    penalty = sum(p for kw, p in WEAK_SKILLS.items() if kw in requirements_text)

    # Kara za angielski
    english_penalty = 0
    if any(kw in text for kw in HIGH_ENGLISH):
        english_penalty = -15
    elif any(kw in text for kw in MEDIUM_ENGLISH):
        english_penalty = -7

    # Bazowy bonus — jeśli to oferta data engineering to dostaje +15 punktów startu
    # (bo listy na portalu nie mają pełnych opisów z technologiami)
    base_bonus = 15 if any(kw in text for kw in DATA_ROLE_KEYWORDS) else 0

    # Max możliwy = suma unikalnych kluczowych technologii
    max_score = 95
    raw = matched_score + penalty + english_penalty + base_bonus
    normalized = int(min(100, max(0, (raw / max_score) * 100)))
    return normalized

def _extract_requirements(text: str) -> str:
    patterns = [
        r"requirements?(.*?)(?:nice to have|benefits|we offer|$)",
        r"wymagani[ae](.*?)(?:mile widziane|oferujemy|benefity|$)",
        r"must have(.*?)(?:nice to have|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1)
    return text
