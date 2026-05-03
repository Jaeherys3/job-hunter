import os
import re

# Profil kandydata - słowa kluczowe z wag (im ważniejsza technologia, tym wyżej)
PROFILE = {
    # Core skills - duże wagi
    "databricks": 20,
    "azure": 15,
    "apache airflow": 15,
    "airflow": 12,
    "pyspark": 12,
    "spark": 10,
    "python": 10,
    "sql": 10,
    "etl": 8,
    "elt": 8,
    "data engineering": 10,
    "data engineer": 10,
    "adf": 8,
    "azure data factory": 8,
    "pipeline": 5,
    # Znane technologie - niższe wagi
    "gcp": 5,
    "aws": 4,
    "s3": 3,
    "athena": 3,
    "delta lake": 7,
    "delta table": 7,
    "lakehouse": 7,
    # Języki
    "english": 0,   # neutralne - nie podnosimy za to score
    # Dyskwalifikatory (język)
}

# Technologie których NIE znasz dobrze - lekka kara jeśli są WYMAGANE
WEAK_SKILLS = {
    "scala": -5,
    "kafka": -3,
    "kubernetes": -3,
    "terraform": -3,
    ".net": -5,
    "java": -5,
}

# Słowa sugerujące wysoki wymóg językowy - kara jeśli angielski słaby
HIGH_ENGLISH_KEYWORDS = ["c1", "c2", "fluent english", "advanced english", "native english"]
MEDIUM_ENGLISH_KEYWORDS = ["b2", "good english", "strong english command"]

def score_job(job: dict) -> int:
    """
    Zwraca score 0-100 na podstawie dopasowania oferty do profilu.
    """
    text = f"{job.get('title', '')} {job.get('description', '')}".lower()

    score = 0
    max_possible = sum(v for v in PROFILE.values() if v > 0)

    # Punkty za dopasowanie
    matched = 0
    for keyword, weight in PROFILE.items():
        if keyword in text and weight > 0:
            matched += weight

    # Kary za brakujące technologie (tylko jeśli są wymagane)
    penalties = 0
    required_section = _extract_requirements_section(text)
    for keyword, penalty in WEAK_SKILLS.items():
        if keyword in required_section:
            penalties += penalty

    # Kara za bardzo wysoki wymóg angielskiego
    english_penalty = 0
    for kw in HIGH_ENGLISH_KEYWORDS:
        if kw in text:
            english_penalty = -15
            break
    if english_penalty == 0:
        for kw in MEDIUM_ENGLISH_KEYWORDS:
            if kw in text:
                english_penalty = -5
                break

    # Normalizacja do 0-100
    raw = matched + penalties + english_penalty
    normalized = int(min(100, max(0, (raw / max_possible) * 100)))

    return normalized

def _extract_requirements_section(text: str) -> str:
    """Wyciąga sekcję wymagań z tekstu oferty."""
    patterns = [
        r"requirements?(.*?)(?:nice to have|benefits|we offer|$)",
        r"wymagani[ae](.*?)(?:mile widziane|oferujemy|benefity|$)",
        r"must have(.*?)(?:nice to have|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1)
    return text  # fallback: cały tekst
