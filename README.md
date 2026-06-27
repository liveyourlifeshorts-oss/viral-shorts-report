# Brief Poranny — Viral YouTube Shorts (35+)

Codzienny raport (generowany automatycznie o 8:00) z najszybciej rosnących
YouTube Shorts z ostatnich 24h, w kategoriach tematycznych statystycznie
popularnych wśród widzów 35+ (finanse, nieruchomości, motoryzacja, zdrowie,
historia/nostalgia, parenting).

**Wynik dostępny jako strona internetowa (GitHub Pages)** — bez potrzeby
trzymania własnego serwera czy komputera włączonego 24/7. Wszystko działa
w darmowej infrastrukturze GitHub Actions + GitHub Pages.

---

## ⚠️ Ważne ograniczenie, które trzeba zrozumieć

YouTube Data API **nie udostępnia danych demograficznych widzów** dla
cudzych filmów (wiek, płeq, lokalizacja widzów to dane prywatne, dostępne
tylko właścicielowi kanału przez YouTube Analytics API). Nie da się więc
zbudować raportu, który dokładnie "wie", że dany film obejrzało X% osób
35+.

To, co ta aplikacja robi w zamian (to standardowe podejście w branży
marketingowej):
- Szuka Shorts w kategoriach tematycznych, które **statystycznie** przyciągają
  starszą publiczność (finanse, nieruchomości, motoryzacja klasyczna,
  historia, zdrowie 40+, parenting) — a nie treści typowo młodzieżowych
  (tańce, lip-sync, gaming dla nastolatków).
- Liczy "viral score" na bazie tempa przyrostu wyświetleń, engagement rate
  i absolutnej popularności.
- Lekko penalizuje filmy z sygnałami treści młodzieżowych w tytule/opisie.

Jeśli potrzebujesz dokładnych danych demograficznych — to wymagałoby
dostępu do YouTube Analytics API **własnych kanałów** (nie cudzych) albo
płatnego narzędzia firm trzecich (np. Tubular Labs, Pex), które mają umowy
z YouTube na dane agregowane.

---

## Jak to działa

```
GitHub Actions (cron, codziennie 8:00)
        │
        ▼
scripts/fetch_report.py  ──► YouTube Data API v3
        │
        ▼
docs/data/latest.json  (+ archiwum w docs/data/history/)
        │
        ▼
GitHub Pages (docs/index.html)  ──► Twój dashboard w przeglądarce
```

Wykorzystanie quoty API: ok. 9 zapytań `search.list` dziennie (900
jednostek z dostępnych 10 000) + kilka darmowych zapytań `videos.list` o
szczegóły. Bezpieczny margines, nawet jeśli zechcesz dodać więcej kategorii.

---

## Krok 1 — Zdobycie klucza YouTube Data API v3

1. Wejdź na [Google Cloud Console](https://console.cloud.google.com/).
2. Zaloguj się kontem Google (możesz użyć już istniejącego, nie trzeba
   konta firmowego).
3. W górnym pasku kliknij wybór projektu → **Nowy projekt**. Nazwij go np.
   `viral-shorts-report` i kliknij **Utwórz**.
4. Po utworzeniu projektu, w menu po lewej wybierz **APIs & Services →
   Library** (Biblioteka).
5. Wyszukaj **"YouTube Data API v3"** i kliknij **Enable** (Włącz).
6. Przejdź do **APIs & Services → Credentials** (Dane uwierzytelniające).
7. Kliknij **+ Create Credentials → API key**.
8. Skopiuj wygenerowany klucz — to jest Twój `YOUTUBE_API_KEY`.
9. (Polecane, dla bezpieczeństwa) Kliknij **Edit API key** i pod
   "API restrictions" wybierz **Restrict key**, zaznacz tylko
   "YouTube Data API v3". Dzięki temu klucz nie zadziała nigdzie innym.

Klucz jest darmowy, nie wymaga podania danych płatności. Domyślny limit to
10 000 jednostek dziennie — w pełni wystarczające dla tej aplikacji.

---

## Krok 2 — Wgranie kodu do repozytorium GitHub

1. Wejdź na [github.com/new](https://github.com/new) i utwórz nowe
   repozytorium (np. `viral-shorts-report`). Może być **publiczne** lub
   **prywatne** — w obu przypadkach GitHub Actions i Pages działają
   bezpłatnie dla osobistych kont (w przypadku repo prywatnego, Pages
   wymaga GitHub Pro — jeśli masz konto darmowe, ustaw repo jako
   publiczne).
2. Pobierz/skopiuj wszystkie pliki z tego projektu do nowego repozytorium
   (struktura katalogów musi zostać zachowana tak, jak jest).
3. Wgraj (push) pliki do repozytorium, np.:
   ```
   git init
   git add .
   git commit -m "Pierwsza wersja aplikacji raportu"
   git branch -M main
   git remote add origin https://github.com/TWOJA-NAZWA/viral-shorts-report.git
   git push -u origin main
   ```

---

## Krok 3 — Dodanie klucza API jako Secret w GitHub

1. W repozytorium na GitHub przejdź do **Settings → Secrets and variables
   → Actions**.
2. Kliknij **New repository secret**.
3. Nazwa: `YOUTUBE_API_KEY`
4. Wartość: wklej klucz skopiowany w Kroku 1.
5. Kliknij **Add secret**.

Dzięki temu klucz nigdy nie jest widoczny publicznie w kodzie — workflow
odwołuje się do niego jako `secrets.YOUTUBE_API_KEY`.

---

## Krok 4 — Włączenie GitHub Pages

1. W repozytorium przejdź do **Settings → Pages**.
2. Pod "Build and deployment" → **Source** wybierz **GitHub Actions**
   (nie "Deploy from a branch" — workflow już to obsługuje).
3. Zapisz. Po pierwszym uruchomieniu workflow (patrz Krok 5), strona będzie
   dostępna pod adresem:
   `https://TWOJA-NAZWA.github.io/viral-shorts-report/`

---

## Krok 5 — Pierwsze uruchomienie (manualne, do testu)

1. W repozytorium przejdź do zakładki **Actions**.
2. Po lewej kliknij workflow **"Codzienny raport viral YouTube Shorts"**.
3. Kliknij **Run workflow** → **Run workflow** (przycisk po prawej).
4. Po ok. 1-2 minutach workflow powinien się zakończyć (zielony ✓).
5. Otwórz adres strony z Kroku 4 — powinien wyświetlić się raport.

Jeśli coś nie zadziała, kliknij na uruchomiony workflow w zakładce Actions,
żeby zobaczyć szczegółowe logi błędów (np. nieprawidłowy klucz API).

---

## Od teraz — automatyczne działanie

Workflow jest skonfigurowany w `.github/workflows/daily-report.yml`, żeby
uruchamiać się **codziennie o 8:00 czasu polskiego** (uwzględnia zarówno
czas letni, jak i zimowy). Nie musisz nic więcej robić — GitHub Actions
zrobi to automatycznie, nawet gdy Twój komputer jest wyłączony.

> Uwaga: harmonogramy `cron` w GitHub Actions czasem mają kilka-kilkunastominutowe
> opóźnienie w godzinach szczytu (to ograniczenie infrastruktury GitHub,
> nie błąd konfiguracji) — raport może się czasem wygenerować o 8:05-8:15
> zamiast punktualnie o 8:00.

---

## Dostosowywanie kategorii i zapytań

Otwórz `scripts/fetch_report.py` i edytuj słownik `CATEGORIES` na początku
pliku — możesz dodawać/usuwać kategorie tematyczne i zapytania wyszukiwania
według własnych potrzeb. Pamiętaj o limicie ok. 9-10 zapytań dziennie
(każde zapytanie wyszukiwania = 100 jednostek quoty z dostępnych 10 000).

## Struktura projektu

```
.
├── .github/workflows/daily-report.yml   ← harmonogram + automatyzacja
├── scripts/
│   ├── fetch_report.py                  ← logika pobierania i rankingu
│   └── requirements.txt
├── docs/
│   ├── index.html                       ← dashboard (GitHub Pages)
│   └── data/
│       ├── latest.json                  ← najnowszy raport
│       └── history/YYYY-MM-DD.json      ← archiwum dzienne
└── README.md
```
