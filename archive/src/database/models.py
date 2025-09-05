"""
Database models and connection management.
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
import logging

from ..config import config

logger = logging.getLogger(__name__)

Base = declarative_base()

class BailiffDict(Base):
    """Dictionary table with bailiffs from dane.gov.pl API."""
    __tablename__ = 'bailiffs_dict'
    
    id = Column(Integer, primary_key=True)
    
    # Original API data
    apelacja = Column(String(100), nullable=False)
    sad_rejonowy_nr = Column(String(200), nullable=False)
    nazwisko = Column(String(100), nullable=False)
    imie = Column(String(100), nullable=False)
    miasto = Column(String(100), nullable=False)
    ulica = Column(String(200), nullable=True)
    kod_pocztowy = Column(String(10), nullable=True)
    
    # Normalized fields for matching
    normalized_fullname = Column(String(200), nullable=True, index=True)
    normalized_lastname = Column(String(100), nullable=True, index=True)
    normalized_firstname = Column(String(100), nullable=True, index=True)
    normalized_city = Column(String(100), nullable=True, index=True)
    
    # API metadata
    api_row_id = Column(String(100), unique=True, nullable=False)
    api_row_no = Column(Integer, nullable=False)
    api_updated_at = Column(DateTime, nullable=True)
    
    # System fields
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class RawNames(Base):
    """Raw names from uploaded files."""
    __tablename__ = 'raw_names'
    
    id = Column(Integer, primary_key=True)
    
    # Source information
    source_file = Column(String(500), nullable=False)
    source_sheet = Column(String(100), nullable=True)
    source_row = Column(Integer, nullable=True)
    source_column = Column(String(50), nullable=True)
    
    # Original text
    raw_text = Column(Text, nullable=False)
    
    # Normalized for matching
    normalized_text = Column(Text, nullable=True, index=True)
    extracted_lastname = Column(String(100), nullable=True)
    extracted_firstname = Column(String(100), nullable=True)
    extracted_city = Column(String(100), nullable=True)
    
    # Processing status
    is_processed = Column(Boolean, default=False, nullable=False)
    processing_notes = Column(Text, nullable=True)
    
    # Additional fields from source files (kom.csv)
    source_city = Column(String(200), nullable=True, comment="City from source file")
    source_email = Column(String(200), nullable=True, comment="Email from source file")
    source_phone = Column(String(50), nullable=True, comment="Phone from source file") 
    source_address = Column(String(500), nullable=True, comment="Address from source file")
    
    # System fields
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class MatchSuggestions(Base):
    """AI/algorithm generated match suggestions."""
    __tablename__ = 'match_suggestions'
    
    id = Column(Integer, primary_key=True)
    
    # References
    raw_id = Column(Integer, ForeignKey('raw_names.id'), nullable=False)
    dict_id = Column(Integer, ForeignKey('bailiffs_dict.id'), nullable=False)
    
    # Scoring details
    total_score = Column(Float, nullable=False)
    lastname_score = Column(Float, nullable=True)
    firstname_score = Column(Float, nullable=True)
    location_score = Column(Float, nullable=True)
    
    # Method used
    matching_method = Column(String(50), nullable=False)  # 'rapidfuzz', 'postgresql', 'combined'
    algorithm_details = Column(Text, nullable=True)  # JSON with algorithm parameters
    
    # Status
    is_reviewed = Column(Boolean, default=False, nullable=False)
    
    # System fields
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    raw_name = relationship("RawNames", backref="suggestions")
    bailiff = relationship("BailiffDict", backref="suggestions")


class NameMappings(Base):
    """Human-approved name mappings."""
    __tablename__ = 'name_mappings'
    
    id = Column(Integer, primary_key=True)
    
    # References
    raw_id = Column(Integer, ForeignKey('raw_names.id'), nullable=False)
    dict_id = Column(Integer, ForeignKey('bailiffs_dict.id'), nullable=True)  # Nullable for "no match" decisions
    
    # Decision
    mapping_type = Column(String(20), nullable=False)  # 'accepted', 'rejected', 'manual_new'
    confidence = Column(String(20), nullable=False)    # 'high', 'medium', 'low'
    
    # Decision maker
    decided_by = Column(String(100), nullable=False)  # User ID or 'system'
    decision_notes = Column(Text, nullable=True)
    
    # Alternative data (for manual_new mappings)
    manual_bailiff_name = Column(String(200), nullable=True)
    manual_bailiff_details = Column(Text, nullable=True)  # JSON
    
    # System fields
    decided_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    raw_name = relationship("RawNames", backref="mappings")
    bailiff = relationship("BailiffDict", backref="mappings")


class DatabaseManager:
    """Database connection and session management."""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize()
    
    def _initialize(self):
        """Initialize database connection."""
        try:
            self.engine = create_engine(
                config.database.connection_string,
                echo=config.debug,  # Log SQL queries in debug mode
                pool_size=10,
                max_overflow=20
            )
            
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info("Database connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def create_tables(self):
        """Create all tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def get_session(self):
        """Get database session."""
        return self.SessionLocal()
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            session = self.get_session()
            session.execute("SELECT 1")
            session.close()
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

# Global database manager
db_manager = DatabaseManager()
