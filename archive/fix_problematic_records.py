#!/usr/bin/env python3
"""
Ulepszony algorytm scoringu z lepszym obsługiwaniem miast
"""

import sqlite3
import sys
sys.path.append('.')
from rapidfuzz import fuzz

def create_city_mappings():
    """Mapowanie miast i obszarów metropolitalnych"""
    return {
        'gdańsk': ['pruszcz gdański', 'gdynia', 'sopot', 'rumia'],
        'warszawa': ['piaseczno', 'pruszków', 'legionowo', 'otwock'],
        'kraków': ['wieliczka', 'skawina', 'krzeszowice'],
        'wrocław': ['kobierzyce', 'siechnice', 'żórawina'],
        'poznań': ['swarzędz', 'luboń', 'puszczykowo'],
        'łódź': ['zgierz', 'pabianice', 'konstantynów łódzki'],
    }

def enhanced_city_score(raw_city, bailiff_city, bailiff_court=None):
    """Ulepszone obliczanie zgodności miasta"""
    if not raw_city or not bailiff_city:
        return 0.0
    
    raw_city_clean = str(raw_city).lower().strip()
    bailiff_city_clean = str(bailiff_city).lower().strip()
    
    # Direct match
    direct_score = fuzz.ratio(raw_city_clean, bailiff_city_clean)
    
    # Check metropolitan area mappings
    city_mappings = create_city_mappings()
    metro_bonus = 0
    
    for main_city, suburbs in city_mappings.items():
        if main_city in raw_city_clean:
            if bailiff_city_clean in suburbs or any(suburb in bailiff_city_clean for suburb in suburbs):
                metro_bonus = 30  # Bonus for metropolitan area match
        elif raw_city_clean in suburbs:
            if main_city in bailiff_city_clean:
                metro_bonus = 30
    
    # Check court location if available
    court_bonus = 0
    if bailiff_court:
        court_clean = str(bailiff_court).lower()
        if raw_city_clean in court_clean:
            court_bonus = 20  # Bonus if raw city appears in court name
    
    final_score = min(100.0, direct_score + metro_bonus + court_bonus)
    return final_score

def update_problematic_records():
    """Update scoring for problematic records"""
    
    print("=== AKTUALIZACJA PROBLEMATYCZNYCH REKORDÓW ===")
    
    # Connect to database
    conn = sqlite3.connect('bailiffs_matching.db')
    cursor = conn.cursor()
    
    # Find records with perfect name matches but low combined scores
    cursor.execute("""
        SELECT ms.id, ms.raw_id, ms.bailiff_id,
               ms.fullname_score, ms.lastname_score, ms.firstname_score, ms.city_score, ms.combined_score,
               rn.raw_text, rn.extracted_firstname, rn.extracted_lastname, rn.source_city,
               bd.normalized_fullname, bd.normalized_firstname, bd.normalized_lastname, 
               bd.original_miasto, bd.original_sad
        FROM match_suggestions ms
        JOIN raw_names rn ON ms.raw_id = rn.id
        JOIN bailiffs_dict bd ON ms.bailiff_id = bd.id
        WHERE ms.lastname_score = 100.0 
          AND ms.firstname_score = 100.0 
          AND ms.combined_score < 85.0
        ORDER BY ms.lastname_score DESC, ms.firstname_score DESC
        LIMIT 50
    """)
    
    problematic_records = cursor.fetchall()
    print(f"Znaleziono {len(problematic_records)} problematycznych rekordów")
    
    updated_count = 0
    
    for record in problematic_records:
        (ms_id, raw_id, bailiff_id, fullname_score, lastname_score, firstname_score, 
         old_city_score, old_combined_score, raw_text, raw_first, raw_last, raw_city,
         bailiff_fullname, bailiff_first, bailiff_last, bailiff_city, bailiff_court) = record
        
        # Recalculate city score with enhanced algorithm
        new_city_score = enhanced_city_score(raw_city, bailiff_city, bailiff_court)
        
        # Recalculate combined score with adjusted weights for perfect name matches
        if lastname_score == 100.0 and firstname_score == 100.0:
            # Higher weight for perfect name matches
            new_combined_score = (
                fullname_score * 0.3 +     # 30% for full name
                lastname_score * 0.4 +     # 40% for lastname (increased)
                firstname_score * 0.3      # 30% for firstname (increased)
            )
        else:
            # Standard weighting
            new_combined_score = (
                fullname_score * 0.4 +
                lastname_score * 0.35 +
                firstname_score * 0.25
            )
        
        # City bonus for enhanced city score
        if new_city_score > 70:
            city_bonus = min(10, new_city_score / 10)
            new_combined_score += city_bonus
        
        # Ensure combined score doesn't exceed 100
        new_combined_score = min(100.0, new_combined_score)
        
        # Determine new confidence level
        if new_combined_score >= 90:
            confidence = 'high'
        elif new_combined_score >= 70:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        # Update only if there's significant improvement
        if new_combined_score > old_combined_score + 5:
            cursor.execute("""
                UPDATE match_suggestions 
                SET city_score = ?, combined_score = ?, confidence_level = ?
                WHERE id = ?
            """, (new_city_score, new_combined_score, confidence, ms_id))
            
            updated_count += 1
            
            print(f"  Rekord {raw_id}: {old_combined_score:.1f}% → {new_combined_score:.1f}% "
                  f"(miasto: {old_city_score:.1f}% → {new_city_score:.1f}%)")
    
    # Commit changes
    conn.commit()
    print(f"✅ Zaktualizowano {updated_count} problematycznych rekordów")
    
    # Test record 9859 specifically
    print(f"\n=== TEST REKORDU 9859 PO AKTUALIZACJI ===")
    cursor.execute("""
        SELECT ms.fullname_score, ms.lastname_score, ms.firstname_score, 
               ms.city_score, ms.combined_score, ms.confidence_level,
               rn.raw_text, rn.extracted_firstname, rn.extracted_lastname, rn.source_city,
               bd.normalized_fullname, bd.normalized_firstname, bd.normalized_lastname,
               bd.original_miasto, bd.original_sad
        FROM match_suggestions ms
        JOIN raw_names rn ON ms.raw_id = rn.id
        JOIN bailiffs_dict bd ON ms.bailiff_id = bd.id
        WHERE rn.id = 9859
        ORDER BY ms.combined_score DESC
        LIMIT 1
    """)
    
    record = cursor.fetchone()
    if record:
        print(f"Najlepsze dopasowanie dla rekordu 9859:")
        print(f"  Raw: '{record[7]} {record[8]}' z {record[9]}")
        print(f"  Bailiff: '{record[11]} {record[12]}' z {record[13]}")
        print(f"  Sąd: {record[14]}")
        print(f"  Scores: fullname={record[0]:.1f}%, lastname={record[1]:.1f}%, firstname={record[2]:.1f}%, city={record[3]:.1f}%")
        print(f"  Combined score: {record[4]:.1f}% ({record[5]})")
    
    conn.close()
    print(f"\n✅ AKTUALIZACJA ZAKOŃCZONA!")

if __name__ == "__main__":
    update_problematic_records()
