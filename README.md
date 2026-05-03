# 🔍 Job Hunter

Automatyczny scraper ofert pracy dla Data Engineerów. Codziennie o wybranej godzinie przeszukuje JustJoin.it i Pracuj.pl, ocenia oferty pod kątem Twojego profilu i wysyła digest na WhatsApp.

---

## Struktura projektu

```
job-hunter/
├── main.py                  # główny skrypt - tu zaczynasz
├── setup_scheduler.py       # konfiguracja automatycznego uruchamiania
├── requirements.txt
├── .env                     # Twoje dane (NIE commituj!)
├── .env.example             # szablon .env
├── .gitignore
│
├── scrapers/
│   ├── justjoin.py          # scraper JustJoin.it
│   └── pracuj.py            # scraper Pracuj.pl (RSS)
│
├── scoring/
│   └── scorer.py            # ocenianie ofert (keyword matching)
│
├── database/
│   └── db.py                # SQLite - pamięta co już widziałeś
│
├── notifications/
│   └── whatsapp.py          # wysyłka przez CallMeBot
│
└── data/                    # tworzy się automatycznie
    ├── jobs.db              # baza danych
    └── scheduler.log        # logi z automatycznych uruchomień
```

---

## Instalacja krok po kroku

### 1. Sklonuj repo i otwórz w VS Code

```bash
git clone https://github.com/TWOJ_USERNAME/job-hunter.git
cd job-hunter
code .
```

### 2. Utwórz wirtualne środowisko

W terminalu VS Code (`Ctrl+` `):

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
```

### 3. Zainstaluj zależności

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Skonfiguruj CallMeBot (WhatsApp)

1. Otwórz WhatsApp i dodaj kontakt: **+34 644 97 93 94**
2. Wyślij do niego dokładnie tę wiadomość: `I allow callmebot to send me messages`
3. Otrzymasz odpowiedź z Twoim **API key**
4. Więcej info: https://www.callmebot.com/blog/free-api-whatsapp-messages/

### 5. Utwórz plik .env

```bash
cp .env.example .env
```

Otwórz `.env` i uzupełnij:
```
WHATSAPP_PHONE=48725405574
WHATSAPP_APIKEY=TWOJ_APIKEY
```

### 6. Przetestuj czy działa

```bash
# Test WhatsApp - powinieneś dostać wiadomość
python main.py --test

# Podgląd ofert bez wysyłki
python main.py --dry

# Pełny run (scraping + wysyłka)
python main.py
```

### 7. Ustaw automatyczne uruchamianie (opcjonalnie)

Uruchom **jako Administrator** (kliknij prawym na terminal → "Uruchom jako administrator"):

```bash
python setup_scheduler.py
```

Skrypt doda zadanie do Windows Task Scheduler — codziennie o 08:00.

---

## Jak dostosować pod siebie

### Zmienić słowa kluczowe do scoringu

Otwórz `scoring/scorer.py` i edytuj słownik `PROFILE`:

```python
PROFILE = {
    "databricks": 20,   # główna technologia - wysoka waga
    "azure": 15,
    # ... dodaj swoje
}
```

### Zmienić wyszukiwane frazy

**JustJoin.it** — edytuj `scrapers/justjoin.py`:
```python
SEARCH_PARAMS = [
    {"keyword": "data engineer databricks", "remoteOnly": "true"},
    # dodaj własne...
]
```

**Pracuj.pl** — edytuj `scrapers/pracuj.py`:
```python
SEARCHES = [
    "data+engineer+databricks",
    # dodaj własne...
]
```

### Zmienić minimalny próg scoringu

W `.env`:
```
MIN_SCORE=60   # tylko oferty z dopasowaniem >= 60%
```

---

## Tworzenie repozytorium GitHub

```bash
git init
git add .
git commit -m "feat: initial job hunter setup"
git branch -M main
git remote add origin https://github.com/TWOJ_USERNAME/job-hunter.git
git push -u origin main
```

> ⚠️ `.env` jest w `.gitignore` — Twoje dane NIE zostaną wysłane na GitHub.

---

## Rozwiązywanie problemów

| Problem | Rozwiązanie |
|---|---|
| WhatsApp nie przychodzi | Sprawdź czy wysłałeś wiadomość do CallMeBot i dostałeś odpowiedź z API key |
| Brak ofert | Uruchom `python main.py --dry` żeby zobaczyć co scraper pobiera |
| Błąd importu | Sprawdź czy masz aktywne venv: `venv\Scripts\activate` |
| Oferty się nie wysyłają drugi raz | To normalne — DB pamięta już wysłane. Skasuj `data/jobs.db` żeby zresetować |

---

## Planowane rozszerzenia

- [ ] Modyfikacja CV pod konkretną ofertę (Claude API)
- [ ] Scraper NoFluffJobs
- [ ] Filtr po widełkach wynagrodzenia
- [ ] Tygodniowy raport statystyk
