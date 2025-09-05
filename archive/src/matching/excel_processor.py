"""
Excel file processing module for raw bailiff names.
"""
import pandas as pd
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union
import os
from datetime import datetime

from ..database.models import db_manager, RawNames
from ..matching.normalizer import normalizer

logger = logging.getLogger(__name__)

class ExcelProcessor:
    """Handles Excel file processing and raw name extraction."""
    
    def __init__(self):
        self.supported_formats = ['.xlsx', '.xls', '.csv']
    
    def validate_file(self, file_path: Union[str, Path]) -> bool:
        """Validate if file exists and has supported format."""
        path = Path(file_path)
        
        if not path.exists():
            logger.error(f"File does not exist: {file_path}")
            return False
        
        if path.suffix.lower() not in self.supported_formats:
            logger.error(f"Unsupported file format: {path.suffix}")
            return False
        
        return True
    
    def read_excel_file(self, file_path: Union[str, Path], sheet_name: Optional[str] = None) -> pd.DataFrame:
        """Read Excel file into pandas DataFrame."""
        path = Path(file_path)
        
        try:
            if path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path, encoding='utf-8')
                logger.info(f"Loaded CSV file: {len(df)} rows")
            else:
                # Try to read Excel file
                if sheet_name:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                else:
                    df = pd.read_excel(file_path)
                logger.info(f"Loaded Excel file: {len(df)} rows, sheet: {sheet_name or 'default'}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise
    
    def get_sheet_names(self, file_path: Union[str, Path]) -> List[str]:
        """Get list of sheet names in Excel file."""
        path = Path(file_path)
        
        if path.suffix.lower() == '.csv':
            return ['CSV']
        
        try:
            excel_file = pd.ExcelFile(file_path)
            # Convert to strings to handle both int and str sheet names
            return [str(name) for name in excel_file.sheet_names]
        except Exception as e:
            logger.error(f"Failed to get sheet names from {file_path}: {e}")
            return []
    
    def extract_text_columns(self, df: pd.DataFrame) -> List[str]:
        """Identify columns that likely contain text/names."""
        text_columns = []
        
        for col in df.columns:
            # Check if column contains mostly text
            non_null_values = df[col].dropna()
            if len(non_null_values) == 0:
                continue
                
            # Sample a few values to determine if it's likely text
            sample_size = min(10, len(non_null_values))
            sample = non_null_values.head(sample_size)
            
            text_count = 0
            for value in sample:
                if isinstance(value, str) and len(value.strip()) > 2:
                    # Check if it contains letters (potential names)
                    if any(c.isalpha() for c in value):
                        text_count += 1
            
            # If majority of samples are text-like, consider it a text column
            if text_count >= sample_size * 0.7:
                text_columns.append(col)
        
        logger.info(f"Identified text columns: {text_columns}")
        return text_columns
    
    def extract_raw_names(self, 
                         file_path: Union[str, Path], 
                         column_name: Optional[str] = None,
                         sheet_name: Optional[str] = None) -> List[Dict]:
        """Extract raw names from Excel file."""
        
        if not self.validate_file(file_path):
            return []
        
        try:
            df = self.read_excel_file(file_path, sheet_name)
            
            if df.empty:
                logger.warning(f"File {file_path} is empty")
                return []
            
            # If no column specified, try to find text columns
            if not column_name:
                text_columns = self.extract_text_columns(df)
                if not text_columns:
                    logger.error("No suitable text columns found in file")
                    return []
                column_name = text_columns[0]  # Use first text column
                logger.info(f"Auto-selected column: {column_name}")
            
            # Check if specified column exists
            if column_name not in df.columns:
                logger.error(f"Column '{column_name}' not found in file")
                return []
            
            # Extract non-empty values from the column
            raw_names = []
            for idx, value in enumerate(df[column_name], start=1):
                if pd.notna(value) and isinstance(value, str) and value.strip():
                    raw_names.append({
                        'source_file': str(file_path),
                        'source_sheet': sheet_name or 'default',
                        'source_row': idx + 1,  # +1 for header row
                        'source_column': column_name,
                        'raw_text': value.strip()
                    })
            
            logger.info(f"Extracted {len(raw_names)} raw names from {file_path}")
            return raw_names
            
        except Exception as e:
            logger.error(f"Failed to extract names from {file_path}: {e}")
            return []
    
    def process_and_normalize_names(self, raw_names: List[Dict]) -> List[RawNames]:
        """Process raw names through normalization pipeline."""
        processed_names = []
        
        for raw_name in raw_names:
            try:
                # Normalize the text
                normalized_data = normalizer.normalize_raw_text(raw_name['raw_text'])
                
                # Create database record
                db_record = RawNames(
                    source_file=raw_name['source_file'],
                    source_sheet=raw_name.get('source_sheet'),
                    source_row=raw_name.get('source_row'),
                    source_column=raw_name.get('source_column'),
                    raw_text=raw_name['raw_text'],
                    normalized_text=normalized_data['normalized_text'],
                    extracted_lastname=normalized_data.get('extracted_lastname'),
                    extracted_firstname=normalized_data.get('extracted_firstname'),
                    processing_notes=normalized_data.get('processing_notes'),
                    is_processed=True
                )
                
                processed_names.append(db_record)
                
            except Exception as e:
                logger.error(f"Failed to process raw name '{raw_name['raw_text']}': {e}")
                # Create record with error note
                db_record = RawNames(
                    source_file=raw_name['source_file'],
                    source_sheet=raw_name.get('source_sheet'),
                    source_row=raw_name.get('source_row'),
                    source_column=raw_name.get('source_column'),
                    raw_text=raw_name['raw_text'],
                    normalized_text='',
                    processing_notes=f'Processing failed: {str(e)}',
                    is_processed=False
                )
                processed_names.append(db_record)
        
        logger.info(f"Processed {len(processed_names)} names")
        return processed_names
    
    def save_to_database(self, processed_names: List[RawNames]) -> bool:
        """Save processed names to database."""
        if not processed_names:
            logger.warning("No names to save")
            return False
        
        session = None
        try:
            session = db_manager.get_session()
            
            # Batch insert
            batch_size = 100
            saved = 0
            
            for i in range(0, len(processed_names), batch_size):
                batch = processed_names[i:i+batch_size]
                session.add_all(batch)
                session.commit()
                saved += len(batch)
                
                if i % (batch_size * 10) == 0:  # Progress every 1000 records
                    logger.info(f"Saved {saved}/{len(processed_names)} names...")
            
            session.close()
            logger.info(f"Successfully saved {saved} raw names to database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save names to database: {e}")
            if session:
                try:
                    session.rollback()
                    session.close()
                except:
                    pass  # Ignore errors during cleanup
            return False
    
    def process_file(self, 
                    file_path: Union[str, Path], 
                    column_name: Optional[str] = None,
                    sheet_name: Optional[str] = None,
                    save_to_db: bool = True) -> Dict:
        """Complete file processing pipeline."""
        
        logger.info(f"Starting file processing: {file_path}")
        
        # Extract raw names
        raw_names = self.extract_raw_names(file_path, column_name, sheet_name)
        
        if not raw_names:
            return {
                'success': False,
                'message': 'No names extracted from file',
                'extracted_count': 0,
                'processed_count': 0,
                'saved_count': 0
            }
        
        # Process and normalize
        processed_names = self.process_and_normalize_names(raw_names)
        
        result = {
            'success': True,
            'extracted_count': len(raw_names),
            'processed_count': len(processed_names),
            'saved_count': 0,
            'file_path': str(file_path),
            'column_name': column_name,
            'sheet_name': sheet_name
        }
        
        # Save to database if requested
        if save_to_db:
            if self.save_to_database(processed_names):
                result['saved_count'] = len(processed_names)
                result['message'] = f'Successfully processed {len(processed_names)} names'
            else:
                result['success'] = False
                result['message'] = 'Failed to save to database'
        else:
            result['processed_names'] = processed_names
            result['message'] = f'Processed {len(processed_names)} names (not saved)'
        
        return result

# Global processor instance
excel_processor = ExcelProcessor()
