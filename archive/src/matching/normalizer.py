"""
Text normalization utilities for bailiff names matching.
"""
import re
import unicodedata
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class NameNormalizer:
    """Handles text normalization for bailiff names."""
    
    # Common titles and formulas to remove
    TITLES_TO_REMOVE = [
        r"komornik\s+sądowy",
        r"przy\s+sądzie\s+rejonowym",
        r"kancelaria\s+komornicza\s+nr\.?\s*\d*",
        r"zastępca\s+komornika",
        r"komornik",
        r"sądowy",
        r"mgr",
        r"dr", 
        r"prof\.",
        r"adwokat",
        r"radca\s+prawny"
    ]
    
    # Court abbreviations to standardize
    COURT_ABBREVIATIONS = {
        r"sr\.?": "sąd rejonowy",
        r"so\.?": "sąd okręgowy", 
        r"sa\.?": "sąd apelacyjny",
        r"s\.?\s*r\.?": "sąd rejonowy"
    }
    
    def __init__(self):
        self.title_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.TITLES_TO_REMOVE]
        self.court_patterns = [(re.compile(pattern, re.IGNORECASE), replacement) 
                              for pattern, replacement in self.COURT_ABBREVIATIONS.items()]
    
    def remove_polish_chars(self, text: str) -> str:
        """Remove Polish diacritical marks from text."""
        if not text:
            return ""
        
        # Direct character mapping for Polish diacritics
        polish_chars = {
            'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
            'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N', 'Ó': 'O', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z'
        }
        
        result = text
        for polish_char, latin_char in polish_chars.items():
            result = result.replace(polish_char, latin_char)
        
        return result
    
    def clean_text(self, text: str) -> str:
        """Basic text cleaning - remove extra spaces, punctuation."""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize spaces
        cleaned = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common punctuation but keep hyphens in names
        cleaned = re.sub(r'[.,;:()\"\'`]', ' ', cleaned)
        
        # Clean up multiple spaces again
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def remove_titles_and_formulas(self, text: str) -> str:
        """Remove official titles and legal formulas."""
        if not text:
            return ""
            
        result = text
        
        # Remove titles
        for pattern in self.title_patterns:
            result = pattern.sub(' ', result)
        
        # Remove numbers (usually office numbers)
        result = re.sub(r'\bnr\.?\s*\d+\w*\b', ' ', result, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        result = re.sub(r'\s+', ' ', result).strip()
        
        return result
    
    def standardize_court_abbreviations(self, text: str) -> str:
        """Standardize court abbreviations."""
        if not text:
            return ""
            
        result = text
        for pattern, replacement in self.court_patterns:
            result = pattern.sub(replacement, result)
            
        return result
    
    def extract_name_parts(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract first name and last name from normalized text."""
        if not text:
            return None, None
            
        # Split into tokens
        tokens = text.split()
        
        if not tokens:
            return None, None
        
        # Simple heuristic: last token is surname, first token is first name
        # This works for most Polish names but may need refinement
        
        if len(tokens) == 1:
            # Only one name - assume it's lastname
            return None, tokens[0]
        elif len(tokens) == 2:
            # Two names - first name, last name
            return tokens[0], tokens[1]
        else:
            # Multiple names - first token as first name, last token as last name
            # Middle tokens are ignored for now (could be middle names or double names)
            return tokens[0], tokens[-1]
    
    def normalize_for_matching(self, text: str) -> str:
        """Full normalization pipeline for text matching."""
        if not text:
            return ""
        
        # 1. Basic cleaning
        result = self.clean_text(text)
        
        # 2. Remove titles and formulas
        result = self.remove_titles_and_formulas(result)
        
        # 3. Standardize abbreviations
        result = self.standardize_court_abbreviations(result)
        
        # 4. Remove Polish characters
        result = self.remove_polish_chars(result)
        
        # 5. Convert to lowercase
        result = result.lower()
        
        # 6. Final cleanup
        result = self.clean_text(result)
        
        return result
    
    def normalize_bailiff_record(self, raw_record: dict) -> dict:
        """Normalize a complete bailiff record for matching."""
        normalized = {}
        
        # Extract individual fields
        nazwisko = raw_record.get('nazwisko', '')
        imie = raw_record.get('imie', '') 
        miasto = raw_record.get('miasto', '')
        
        # Normalize individual fields
        normalized['normalized_lastname'] = self.normalize_for_matching(nazwisko)
        normalized['normalized_firstname'] = self.normalize_for_matching(imie)
        normalized['normalized_city'] = self.normalize_for_matching(miasto)
        
        # Create full name for matching
        full_name = f"{imie} {nazwisko}".strip()
        normalized['normalized_fullname'] = self.normalize_for_matching(full_name)
        
        return normalized
    
    def normalize_raw_text(self, raw_text: str) -> dict:
        """Normalize raw text from files and extract name parts."""
        normalized_text = self.normalize_for_matching(raw_text)
        
        # Try to extract name parts
        first_name, last_name = self.extract_name_parts(normalized_text)
        
        return {
            'normalized_text': normalized_text,
            'extracted_firstname': first_name,
            'extracted_lastname': last_name,
            'processing_notes': f"Normalized from: '{raw_text}'"
        }

# Global normalizer instance
normalizer = NameNormalizer()
