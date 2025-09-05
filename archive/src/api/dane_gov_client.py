"""
API client for fetching bailiffs data from dane.gov.pl
"""
import requests
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import time

from ..config import config

logger = logging.getLogger(__name__)

@dataclass
class BailiffRecord:
    """Single bailiff record from API."""
    apelacja: str
    sad_rejonowy_nr: str
    nazwisko: str  
    imie: str
    miasto: str
    ulica: str
    kod_pocztowy: str
    row_id: str
    row_no: int
    updated_at: str

class DaneGovAPIClient:
    """Client for fetching bailiffs data from dane.gov.pl API."""
    
    def __init__(self):
        self.base_url = config.api.dane_gov_base_url
        self.bailiffs_endpoint = config.api.bailiffs_endpoint
        self.timeout = config.api.request_timeout
        self.max_retries = config.api.max_retries
        
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
    
    def get_bailiffs_meta(self) -> Dict[str, Any]:
        """Get metadata about bailiffs dataset."""
        response = self._make_request(self.bailiffs_endpoint)
        return response.get("meta", {})
    
    def get_bailiffs_page(self, page: int = 1, page_size: Optional[int] = None) -> Dict[str, Any]:
        """Get single page of bailiffs data."""
        params = {"page": page}
        if page_size:
            params["page_size"] = page_size
            
        return self._make_request(self.bailiffs_endpoint, params)
    
    def get_all_bailiffs(self) -> List[BailiffRecord]:
        """Fetch all bailiffs records from API."""
        logger.info("Fetching all bailiffs data from dane.gov.pl API")
        
        all_records = []
        page = 1
        
        while True:
            try:
                response = self.get_bailiffs_page(page)
                data = response.get("data", [])
                
                if not data:
                    break
                    
                # Parse records
                for item in data:
                    try:
                        attrs = item["attributes"]
                        record = BailiffRecord(
                            apelacja=attrs["col1"]["val"],
                            sad_rejonowy_nr=attrs["col2"]["val"], 
                            nazwisko=attrs["col3"]["val"],
                            imie=attrs["col4"]["val"],
                            miasto=attrs["col5"]["val"],
                            ulica=attrs["col6"]["val"],
                            kod_pocztowy=attrs["col7"]["val"],
                            row_id=item["id"],
                            row_no=item["meta"]["row_no"],
                            updated_at=item["meta"]["updated_at"]
                        )
                        all_records.append(record)
                        
                    except KeyError as e:
                        logger.warning(f"Missing field in record {item.get('id', 'unknown')}: {e}")
                        continue
                
                logger.info(f"Processed page {page}, total records: {len(all_records)}")
                
                # Check if we have more pages
                links = response.get("links", {})
                if not links.get("next"):
                    break
                    
                page += 1
                
            except Exception as e:
                logger.error(f"Failed to fetch page {page}: {e}")
                break
        
        logger.info(f"Finished fetching bailiffs data. Total records: {len(all_records)}")
        return all_records
    
    def search_bailiffs(self, search_term: str) -> List[BailiffRecord]:
        """Search bailiffs by name (client-side filtering for now)."""
        all_bailiffs = self.get_all_bailiffs()
        search_lower = search_term.lower()
        
        filtered = []
        for bailiff in all_bailiffs:
            if (search_lower in bailiff.nazwisko.lower() or 
                search_lower in bailiff.imie.lower()):
                filtered.append(bailiff)
                
        return filtered
