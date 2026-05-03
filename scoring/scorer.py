import re

# Profil kandydata — technologie z wagami ważności
# Suma wag CORE = 100, żeby score był intuicyjny
PROFILE = {
    # === CORE (znasz bardzo dobrze) ===
    "databricks":        20,
    "azure":             15,
    "airflow":           13,
    "apache airflow":    13,
    "pyspark":           12,
    "spark":             10,
    "python":            10,
    "sql":               10,
    "etl":               8,
    "elt":               8,
    "data engineer":     10,
    "data engineering":  10,
    "adf":               8,
    "azure data factory": 8,
    "pipeline":          5,
    # === ZNANE (masz doświadczenie) ===
    "gcp":               5,
    "aws":               4,
    "delta lake":        7,
    "delta table":       7,
    "lakehouse":         7,
    "s3":                3,
    "athena":            3,
}

# Technologie słabsze — kara tylko jeśli są w sekcji WYMAGANYCH
WEAK_SKILLS = {
    "scala":       -8,
    "kafka":       -4,
    "kubernetes":  -4,
    "terraform":   -4,
    ".net":        -8,
    "java":        -8,
}

# Kara za wysoki wymóg angielskiego (Twoje obawy)
HIGH_ENGLISH   = ["c1", "c2", "fluent english", "advanced english", "native english"]
MEDIUM_ENGLISH = ["b2", "good english", "strong english command", "upper intermediate"]

# Maksymalny możliwy wynik — tylko unikalne tagi core (nie liczymy aliasów)
# airflow + apache airflow to to samo, więc bierzemy tylko raz
_UNIQUE_CORE = {
    "databricks", "azure", "airflow", "pyspark", "spark", "python",
    "sql", "etl", "data engineer", "adf", "pipeline",
    "gcp", "aws", "delta lake", "lakehouse",
}
MAX_SCORE = sum(PROFILE[k] for k in _UNIQUE_CORE)

def score_job(job: dict) -> int:
    """Zwraca score 0-100 na podstawie dopasowania oferty do profilu kandydata."""
    text = f"{job.get('title', '')} {job.get('description', '')}".lower()

    # Punkty za dopasowanie (bez podwójnego liczenia aliasów)
    matched_keys = set()
    matched_score = 0
    for keyword, weight in PROFILE.items():
        if keyword in text:
            # Unikaj podwójnego liczenia aliasów (airflow / apache airflow)
            base_key = keyword.split()[-1]  # "apache airflow" -> "airflow"
            if base_key not in matched_keys:
                matched_keys.add(base_key)
                matched_score += weight

    # Kary za słabe technologie (tylko w sekcji wymagań)
    requirements_text = _extract_requirements(text)
    penalty = sum(
        p for kw, p in WEAK_SKILLS.items()
        if kw in requirements_text
    )

    # Kara za angielski
    english_penalty = 0
    if any(kw in text for kw in HIGH_ENGLISH):
        english_penalty = -15
    elif any(kw in text for kw in MEDIUM_ENGLISH):
        english_penalty = -7

    raw = matched_score + penalty + english_penalty
    normalized = int(min(100, max(0, (raw / MAX_SCORE) * 100)))
    return normalized

def _extract_requirements(text: str) -> str:
    """Wyciąga sekcję wymagań — kary aplikujemy tylko do wymaganych technologii."""
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
