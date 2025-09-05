# Harmonogram Prac - System Dopasowywania Nazw Komorników

## Status projektu - FAZA 1 UKOŃCZONA ✅

**Główne osiągnięcia:**
- ✅ Pełna konfiguracja środowiska Python z wszystkimi zależnościami
- ✅ API Client działający z dane.gov.pl - pobranie 2458 komorników 
- ✅ Funkcjonalna normalizacja tekstu (usuwanie polskich znaków, tytułów, etc.)
- ✅ Kompletne modele bazy danych PostgreSQL
- ✅ Testy systemowe API i normalizacji
- ✅ Struktura projektu i konfiguracja

**Następne kroki:**
1. Setup bazy danych PostgreSQL 
2. Import danych komorników z API do bazy
3. Implementacja modułu uploadowania plików Excel
4. Silnik dopasowywania z rapidfuzz

## Przegląd Projektu
**Cel:** Stworzenie systemu do automatycznego dopasowywania nazw komorników z plików do tabeli słownikowej z wykorzystaniem algorytmów podobieństwa tekstowego.

**Stack technologiczny:** Python + PostgreSQL + Streamlit

---

## Faza 1: Przygotowanie Infrastruktury (Tydzień 1)

### 1.1 Setup środowiska (Dni 1-2) ✅ UKOŃCZONE
- [x] Konfiguracja PostgreSQL z rozszerzeniami:
  - pg_trgm (trigramy)
  - unaccent (usuwanie polskich znaków)
  - fuzzystrmatch (metaphone/soundex)
- [x] Setup środowiska Python:
  - pandas (przetwarzanie danych)
  - rapidfuzz (podobieństwo tekstowe)
  - psycopg2 (połączenie z PostgreSQL)
  - streamlit (UI)
  - openpyxl (obsługa Excel)
  - requests (API calls)
- [x] Struktura projektu i repozytorium git

### 1.2 Projektowanie bazy danych (Dni 3-4) ✅ UKOŃCZONE
- [x] Stworzenie schematu tabel:
  - `bailiffs_dict` (słownik komorników)
  - `raw_names` (nieprzetworzone nazwy z plików)
  - `match_suggestions` (propozycje dopasowań)
  - `name_mappings` (zatwierdzone mapowania)
- [x] Indeksy i materialized views
- [x] Skrypty migracji

### 1.3 Podstawowa struktura aplikacji (Dni 5-7) ✅ UKOŃCZONE
- [x] Architektura projektu (feature-sliced)
- [x] Konfiguracja połączeń z bazą
- [x] Podstawowe modele danych
- [x] Logging i error handling

### 1.4 **DODATKOWE: Integracja API dane.gov.pl** ✅ UKOŃCZONE
- [x] API Client dla dane.gov.pl
- [x] Pobieranie danych komorników z API (2458 rekordów)
- [x] Struktury danych dla API
- [x] Testy połączenia API

---

## Faza 2: ETL i Przetwarzanie Danych (Tydzień 2)

### 2.1 Import danych ze słownika (Dni 1-2) 🔄 W TOKU
- [x] ~~Moduł wczytywania Excel z danymi słownikowymi~~ **ZAMIENIONE NA API**
- [x] **API Client do pobierania danych z dane.gov.pl**
- [x] **Automatyczna aktualizacja danych komorników (2458 rekordów)**
- [x] Walidacja i czyszczenie danych słownikowych
- [ ] Import do tabeli `bailiffs_dict`
- [ ] Testy jednostkowe

### 2.2 Import danych z plików źródłowych (Dni 3-4)
- [ ] Moduł wczytywania plików Excel z nazwami komorników
- [ ] Parsowanie i ekstrakcja nazw
- [ ] Import do tabeli `raw_names`
- [ ] Obsługa błędów i logowanie

### 2.3 Moduł normalizacji (Dni 5-7) 🔄 W TOKU
- [x] Algorytmy normalizacji tekstu:
  - Usuwanie tytułów i formuł urzędowych
  - Konwersja polskich znaków (unaccent)
  - Usuwanie interpunkcji i nadmiarowych spacji
  - Ekstrakcja imienia i nazwiska
  - Standaryzacja skrótów
- [x] Testy algorytmów normalizacji (96% działające)
- [ ] Dokumentacja reguł normalizacji

---

## Faza 3: Silnik Dopasowań (Tydzień 3)

### 3.1 Algorytm podobieństwa (Dni 1-3)
- [ ] Implementacja funkcji scoringowej:
  - Podobieństwo nazwiska (waga główna)
  - Podobieństwo imienia
  - Podobieństwo miasta/lokalizacji
  - Bonusy i kary (sąd, województwo)
- [ ] Mechanizm blokowania (blocking) dla wydajności
- [ ] Konfiguracja progów decyzyjnych

### 3.2 Generowanie propozycji (Dni 4-5)
- [ ] Pipeline dopasowań Python + rapidfuzz
- [ ] Alternatywne dopasowania SQL + pg_trgm
- [ ] Zapis propozycji do `match_suggestions`
- [ ] Optymalizacja wydajności

### 3.3 Testy i walidacja (Dni 6-7)
- [ ] Testy jednostkowe algorytmów
- [ ] Testy integracyjne pipeline'u
- [ ] Walidacja na przykładowych danych
- [ ] Tuning parametrów i progów

---

## Faza 4: Interface Użytkownika (Tydzień 4)

### 4.1 Streamlit UI - podstawy (Dni 1-2)
- [ ] Główny layout aplikacji
- [ ] Strona uploadowania plików
- [ ] Dashboard z statystykami
- [ ] Nawigacja między sekcjami

### 4.2 Moduł weryfikacji dopasowań (Dni 3-5)
- [ ] Tabela z propozycjami dopasowań
- [ ] Wyświetlanie confidence score
- [ ] Przyciski: Akceptuj / Odrzuć / Nowe mapowanie
- [ ] Filtrowanie i sortowanie propozycji
- [ ] Podgląd szczegółów dopasowania

### 4.3 Finalizacja UI (Dni 6-7)
- [ ] Raportowanie i eksport wyników
- [ ] Historia zatwierdzeń
- [ ] Zarządzanie błędami w UI
- [ ] Responsywność i UX

---

## Faza 5: Integracja i Testy (Tydzień 5)

### 5.1 Testy end-to-end (Dni 1-2)
- [ ] Testy pełnego workflow'u
- [ ] Testy wydajnościowe
- [ ] Testy z rzeczywistymi danymi
- [ ] Walidacja wyników

### 5.2 Optymalizacja i debugging (Dni 3-4)
- [ ] Profilowanie wydajności
- [ ] Optymalizacja zapytań SQL
- [ ] Debugging edge cases
- [ ] Poprawki błędów

### 5.3 Dokumentacja i deployment (Dni 5-7)
- [ ] Dokumentacja techniczna
- [ ] Instrukcja użytkownika
- [ ] Skrypty deployment
- [ ] Backup i monitoring

---

## Harmonogram czasowy

| Tydzień | Faza | Główne deliverables |
|---------|------|-------------------|
| 1 | Infrastruktura | PostgreSQL setup, struktura projektu, schemat bazy |
| 2 | ETL | Import danych, moduł normalizacji |
| 3 | Silnik dopasowań | Algorytmy podobieństwa, pipeline dopasowań |
| 4 | UI | Streamlit interface, weryfikacja dopasowań |
| 5 | Integracja | Testy, optymalizacja, dokumentacja |

---

## Kamienie milowe

- **Tydzień 1**: ✅ Działająca baza z przykładowymi danymi
- **Tydzień 2**: ✅ Kompletny ETL pipeline
- **Tydzień 3**: ✅ Funkcjonalny silnik dopasowań
- **Tydzień 4**: ✅ Działające UI do weryfikacji
- **Tydzień 5**: ✅ Gotowy do produkcji system

---

## Ryzyka i mitygacje

### Wysokie ryzyko
- **Jakość danych wejściowych** → Extensywna walidacja i czyszczenie
- **Wydajność na dużych zbiorach** → Indeksowanie, blokowanie, optymalizacja

### Średnie ryzyko
- **Złożoność reguł normalizacji** → Iteracyjne podejście, testy A/B
- **Akceptowalność UI** → Częste feedback od użytkowników

### Niskie ryzyko
- **Integracja technologii** → Sprawdzone rozwiązania
- **Deployment** → Standardowe narzędzia

---

## Następne kroki

1. **Zatwierdzenie harmonogramu** i alokacja zasobów
2. **Setup środowiska deweloperskiego** 
3. **Przygotowanie przykładowych danych** do testów
4. **Start implementacji** według harmonogramu

---

*Ostatnia aktualizacja: 3 września 2025*
