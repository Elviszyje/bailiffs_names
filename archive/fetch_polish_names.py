#!/usr/bin/env python3
"""
Skrypt do pobrania pełnej listy polskich imion z API dane.gov.pl
i aktualizacji algorytmu ekstrakcji nazwisk
"""

import requests
import json
import sqlite3
import sys

def fetch_polish_names():
    """Pobierz pełną listę polskich imion z oficjalnego API"""
    
    # API endpoints for Polish names - na razie tylko żeńskie, męskie wymaga znalezienia właściwego ID
    endpoints = {
        'female': 'https://api.dane.gov.pl/1.4/resources/63924,lista-imion-zenskich-w-rejestrze-pesel-stan-na-22012025-imie-pierwsze/data'
    }
    
    all_names = set()
    
    for gender, url in endpoints.items():
        print(f"Pobieranie imion {gender}...")
        try:
            # Pobierz wszystkie dane z paginacją
            page = 1
            limit = 1000
            total_names_for_gender = 0
            
            while True:
                params = {
                    'page[limit]': limit,
                    'page[offset]': (page - 1) * limit
                }
                
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                if not data.get('data'):
                    break
                    
                page_names = 0
                for item in data['data']:
                    if isinstance(item, dict) and 'attributes' in item:
                        if 'col1' in item['attributes'] and 'val' in item['attributes']['col1']:
                            name = item['attributes']['col1']['val'].strip().title()
                            if name and len(name) > 1 and name.isalpha():
                                all_names.add(name)
                                page_names += 1
                
                total_names_for_gender += page_names
                print(f"  Strona {page}: {page_names} imion")
                
                # Jeśli otrzymaliśmy mniej niż limit, to koniec
                if len(data['data']) < limit:
                    break
                    
                page += 1
                
                # Zabezpieczenie przed nieskończoną pętlą
                if page > 100:
                    print(f"  Osiągnięto limit 100 stron")
                    break
            
            print(f"  Łącznie pobrano {total_names_for_gender} imion {gender}")
                
        except Exception as e:
            print(f"  Błąd pobierania {gender}: {e}")
            continue
    
    # Dodaj popularne męskie imiona z naszej obecnej listy, aby nie stracić funkcjonalności
    common_male_names = {
        'Adam', 'Adrian', 'Aleksander', 'Andrzej', 'Antoni', 'Artur', 'Bartosz', 
        'Damian', 'Daniel', 'Dawid', 'Dominik', 'Filip', 'Grzegorz', 'Hubert',
        'Jakub', 'Jan', 'Jarosław', 'Kamil', 'Karol', 'Krzysztof', 'Łukasz',
        'Maciej', 'Marcin', 'Marek', 'Mateusz', 'Michał', 'Paweł', 'Piotr',
        'Przemysław', 'Rafał', 'Robert', 'Sebastian', 'Sławomir', 'Stanisław',
        'Tomasz', 'Wojciech', 'Zbigniew'
    }
    
    all_names.update(common_male_names)
    print(f"Dodano {len(common_male_names)} popularnych męskich imion")
    
    print(f"\nŁącznie pobrano {len(all_names)} unikalnych imion")
    return sorted(list(all_names))

def create_names_list_file(names):
    """Stwórz plik z listą imion"""
    
    # Stwórz kod Python z listą imion
    python_code = f'''#!/usr/bin/env python3
"""
Pełna lista polskich imion pobrana z oficjalnego API dane.gov.pl
Wygenerowano automatycznie: {len(names)} imion
"""

POLISH_FIRST_NAMES = {{
{chr(10).join(f"    '{name}'," for name in names[:50])}
    # ... i więcej - pełna lista w get_polish_names()
}}

def get_polish_names():
    """Zwróć pełną listę polskich imion"""
    return {{
{chr(10).join(f"        '{name}'," for name in names)}
    }}

def is_polish_name(name):
    """Sprawdź czy podane słowo to polskie imię"""
    return name.title() in get_polish_names()
'''
    
    with open('polish_names.py', 'w', encoding='utf-8') as f:
        f.write(python_code)
    
    print(f"Zapisano listę imion do pliku polish_names.py")
    return len(names)

def update_name_extraction_files(names):
    """Aktualizuj pliki z ekstrakcją nazwisk"""
    
    names_set_code = "{\n" + ",\n".join(f"        '{name}'" for name in names) + "\n    }"
    
    # Lista plików do aktualizacji
    files_to_update = [
        'scripts/file_upload.py',
        'update_name_extraction.py', 
        'update_bailiffs_dict.py',
        'test_name_extraction.py'
    ]
    
    for file_path in files_to_update:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Znajdź i zamień listę polish_first_names
            import re
            pattern = r'polish_first_names\s*=\s*\{[^}]+\}'
            
            if re.search(pattern, content, re.DOTALL):
                new_content = re.sub(
                    pattern, 
                    f'polish_first_names = {names_set_code}',
                    content,
                    flags=re.DOTALL
                )
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print(f"✅ Zaktualizowano {file_path}")
            else:
                print(f"⚠️  Nie znaleziono polish_first_names w {file_path}")
                
        except FileNotFoundError:
            print(f"⚠️  Plik {file_path} nie istnieje")
        except Exception as e:
            print(f"❌ Błąd aktualizacji {file_path}: {e}")

def main():
    print("🚀 Pobieranie oficjalnej listy polskich imion z dane.gov.pl")
    print("=" * 60)
    
    # Pobierz imiona
    names = fetch_polish_names()
    
    if not names:
        print("❌ Nie udało się pobrać imion!")
        return False
    
    # Stwórz plik z imionami
    count = create_names_list_file(names)
    
    # Aktualizuj pliki
    print(f"\n📝 Aktualizacja plików z nową listą {count} imion...")
    update_name_extraction_files(names)
    
    print(f"\n🎯 Gotowe! Pobrano i zaimplementowano {count} oficjalnych polskich imion")
    print("\nNastępne kroki:")
    print("1. Uruchom update_name_extraction.py - aby zaktualizować raw_names")
    print("2. Uruchom update_bailiffs_dict.py - aby zaktualizować bailiffs_dict") 
    print("3. Przeliczy dopasowania dla sesji")
    
    return True

if __name__ == "__main__":
    main()
