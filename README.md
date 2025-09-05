# System Dopasowywania Komorników

System do automatycznego dopasowywania komorników sądowych z wykorzystaniem algorytmów fuzzy matching i komprehensywnej bazy polskich imion i nazwisk.

## Funkcjonalności

- **Analiza dopasowań**: Inteligentne dopasowywanie komorników na podstawie imion, nazwisk i lokalizacji
- **Zarządzanie bazą komorników**: Przeglądanie, dodawanie, edytowanie i usuwanie rekordów komorników
- **Import danych**: Możliwość importu nowych danych z plików CSV i Excel
- **Statystyki i wizualizacje**: Szczegółowe statystyki dopasowań z wykresami

## Technologie

- **Python 3.13+**
- **Streamlit** - interfejs webowy
- **SQLite** - baza danych
- **rapidfuzz** - algorytmy fuzzy matching
- **pandas** - przetwarzanie danych
- **plotly** - wizualizacje

## Instalacja

1. Sklonuj repozytorium:
```bash
git clone https://github.com/username/bailiffs_names.git
cd bailiffs_names
```

2. Zainstaluj zależności:
```bash
pip install -r requirements.txt
```

3. Uruchom aplikację:
```bash
streamlit run app.py
```

## Konfiguracja

Aplikacja korzysta z następujących plików:
- `bailiffs_matching.db` - główna baza danych SQLite
- `polish_first_names_full.pkl` - baza polskich imion (24,427 rekordów)
- `polish_surnames_full.pkl` - baza polskich nazwisk (609,472 rekordów)
- `files/` - folder z danymi źródłowymi

## Struktura projektu

- `app.py` - główna aplikacja Streamlit
- `requirements.txt` - zależności Python
- `files/` - dane źródłowe (pliki Excel z bazą PESEL)
- `archive/` - pliki deweloperskie i dokumentacja

## Dane źródłowe

System wykorzystuje oficjalne dane z rejestru PESEL udostępnione przez Ministerstwo Cyfryzacji, zawierające:
- Imiona męskie i żeńskie osób żyjących
- Nazwiska męskie i żeńskie z uwzględnieniem osób zmarłych

## Deployment

Aplikacja jest gotowa do wdrożenia na Streamlit Community Cloud. Po utworzeniu repozytorium GitHub, można ją uruchomić bezpośrednio z poziomu platformy.

## Licencja

Projekt wykorzystuje dane publiczne udostępnione przez Ministerstwo Cyfryzacji.
