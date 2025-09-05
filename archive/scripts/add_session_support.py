"""
Add session support to the database for handling multiple file uploads.
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, func, Float, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Database models
Base = declarative_base()

class AnalysisSession(Base):
    """Track different analysis sessions for uploaded files."""
    __tablename__ = 'analysis_sessions'
    
    id = Column(Integer, primary_key=True)
    session_name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    original_filename = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    total_records = Column(Integer, nullable=True)
    processed_records = Column(Integer, default=0, nullable=False)
    matched_records = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default='uploaded', nullable=False)  # uploaded, processing, completed, error
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

def add_session_support():
    """Add session support to existing database."""
    engine = create_engine('sqlite:///bailiffs_matching.db', echo=True)
    
    # Create the new table
    AnalysisSession.__table__.create(bind=engine, checkfirst=True)
    
    # Add session_id column to existing tables
    with engine.connect() as conn:
        try:
            # Add session_id to raw_names
            conn.execute(text('ALTER TABLE raw_names ADD COLUMN session_id INTEGER REFERENCES analysis_sessions(id)'))
            print("✅ Added session_id to raw_names")
        except Exception as e:
            print(f"Session_id already exists in raw_names or error: {e}")
        
        try:
            # Add session_id to match_suggestions  
            conn.execute(text('ALTER TABLE match_suggestions ADD COLUMN session_id INTEGER REFERENCES analysis_sessions(id)'))
            print("✅ Added session_id to match_suggestions")
        except Exception as e:
            print(f"Session_id already exists in match_suggestions or error: {e}")
            
        try:
            # Add session_id to name_mappings
            conn.execute(text('ALTER TABLE name_mappings ADD COLUMN session_id INTEGER REFERENCES analysis_sessions(id)'))
            print("✅ Added session_id to name_mappings")
        except Exception as e:
            print(f"Session_id already exists in name_mappings or error: {e}")
        
        conn.commit()
    
    print("✅ Session support added to database!")

if __name__ == "__main__":
    add_session_support()
