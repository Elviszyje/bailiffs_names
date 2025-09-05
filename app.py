"""
Streamlit application for bailiff name matching review and approval.
"""

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, func, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import plotly.express as px
import plotly.graph_objects as go
import os
import tempfile

# Database models (simplified for Streamlit)
Base = declarative_base()

class AnalysisSession(Base):
    __tablename__ = 'analysis_sessions'
    
    id = Column(Integer, primary_key=True)
    session_name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    original_filename = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    total_records = Column(Integer, nullable=True)
    processed_records = Column(Integer, default=0, nullable=False)
    matched_records = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default='uploaded', nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

class BailiffDict(Base):
    __tablename__ = 'bailiffs_dict'
    id = Column(Integer, primary_key=True)
    original_nazwisko = Column(Text, nullable=False)
    original_imie = Column(String(100), nullable=True)
    original_miasto = Column(String(100), nullable=True)
    original_sad = Column(Text, nullable=True)
    adres = Column(Text, nullable=True)
    kod_pocztowy = Column(String(20), nullable=True)
    telefon = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    normalized_lastname = Column(String(100), nullable=True)
    normalized_firstname = Column(String(100), nullable=True)
    normalized_city = Column(String(100), nullable=True)
    bank = Column(String(200), nullable=True)
    numer_konta = Column(String(100), nullable=True)
    normalized_fullname = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

class RawNames(Base):
    __tablename__ = 'raw_names'
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('analysis_sessions.id'), nullable=True)
    source_file = Column(String(500), nullable=False)
    source_sheet = Column(String(100), nullable=True)
    source_row = Column(Integer, nullable=True)
    source_column = Column(String(100), nullable=True)
    raw_text = Column(Text, nullable=False)
    normalized_text = Column(Text, nullable=True)
    extracted_lastname = Column(String(100), nullable=True)
    extracted_firstname = Column(String(100), nullable=True)
    is_processed = Column(Boolean, default=False, nullable=False)
    processing_notes = Column(Text, nullable=True)
    source_city = Column(String(200), nullable=True)
    source_email = Column(String(200), nullable=True)
    source_phone = Column(String(50), nullable=True)
    source_address = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

class MatchSuggestions(Base):
    __tablename__ = 'match_suggestions'
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('analysis_sessions.id'), nullable=True)
    raw_id = Column(Integer, ForeignKey('raw_names.id'), nullable=False)
    bailiff_id = Column(Integer, ForeignKey('bailiffs_dict.id'), nullable=False)
    fullname_score = Column(Float, nullable=False)
    lastname_score = Column(Float, nullable=True)
    firstname_score = Column(Float, nullable=True)
    city_score = Column(Float, nullable=True)
    combined_score = Column(Float, nullable=False)
    algorithm_used = Column(String(50), nullable=False)
    confidence_level = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    raw_name = relationship("RawNames", backref="suggestions")
    bailiff = relationship("BailiffDict", backref="suggestions")

class NameMappings(Base):
    __tablename__ = 'name_mappings'
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('analysis_sessions.id'), nullable=True)
    raw_id = Column(Integer, ForeignKey('raw_names.id'), nullable=False)
    bailiff_id = Column(Integer, ForeignKey('bailiffs_dict.id'), nullable=True)
    mapping_type = Column(String(20), nullable=False)  # 'accepted', 'rejected', 'manual_new'
    confidence_level = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, default=func.now(), nullable=False)

@st.cache_resource
def get_database_connection():
    """Initialize database connection."""
    engine = create_engine("sqlite:///bailiffs_matching.db", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal

def get_sessions_list():
    """Get list of all analysis sessions."""
    engine, SessionLocal = get_database_connection()
    session = SessionLocal()
    
    try:
        sessions = session.query(AnalysisSession).order_by(AnalysisSession.created_at.desc()).all()
        
        sessions_data = []
        for analysis_session in sessions:
            # Get stats
            total_suggestions = session.query(MatchSuggestions).filter(
                MatchSuggestions.session_id == analysis_session.id
            ).count()
            
            mapped_count = session.query(NameMappings).filter(
                NameMappings.session_id == analysis_session.id
            ).count()
            
            sessions_data.append({
                'id': analysis_session.id,
                'session_name': analysis_session.session_name,
                'description': analysis_session.description,
                'filename': analysis_session.original_filename,
                'total_records': analysis_session.total_records or 0,
                'processed_records': analysis_session.processed_records or 0,
                'matched_records': mapped_count,
                'total_suggestions': total_suggestions,
                'status': analysis_session.status,
                'created_at': analysis_session.created_at,
                'updated_at': analysis_session.updated_at
            })
        
        return sessions_data
        
    finally:
        session.close()

def load_data(session_id=None):
    """Load data from database for specific session."""
    engine, SessionLocal = get_database_connection()
    session = SessionLocal()
    
    try:
        # Load suggestions with related data for specific session
        query = session.query(MatchSuggestions).join(RawNames).join(BailiffDict)
        
        if session_id:
            query = query.filter(MatchSuggestions.session_id == session_id)
        
        suggestions_query = query.all()
        
        suggestions_data = []
        for suggestion in suggestions_query:
            suggestions_data.append({
                'suggestion_id': suggestion.id,
                'raw_id': suggestion.raw_id,
                'bailiff_id': suggestion.bailiff_id,
                'raw_text': suggestion.raw_name.raw_text,
                'bailiff_name': suggestion.bailiff.original_nazwisko,
                'raw_city': suggestion.raw_name.source_city,
                'bailiff_city': suggestion.bailiff.original_miasto,
                'combined_score': suggestion.combined_score,
                'fullname_score': suggestion.fullname_score,
                'city_score': suggestion.city_score,
                'confidence_level': suggestion.confidence_level,
                'algorithm_used': suggestion.algorithm_used
            })
        
        # Check for existing mappings in this session
        mappings_query = session.query(NameMappings)
        if session_id:
            mappings_query = mappings_query.filter(NameMappings.session_id == session_id)
        
        mappings = mappings_query.all()
        mapped_raw_ids = {mapping.raw_id for mapping in mappings}
        
        return pd.DataFrame(suggestions_data), mapped_raw_ids
        
    finally:
        session.close()

def save_mapping(raw_id, bailiff_id, mapping_type, notes="", reviewed_by="User", session_id=None):
    """Save a human decision to the database."""
    engine, SessionLocal = get_database_connection()
    session = SessionLocal()
    
    try:
        # Get session_id from raw_names if not provided
        if session_id is None:
            raw_name = session.query(RawNames).filter(RawNames.id == raw_id).first()
            if raw_name:
                session_id = raw_name.session_id
        
        # Check if mapping already exists
        existing = session.query(NameMappings).filter(NameMappings.raw_id == raw_id).first()
        
        if existing:
            # Update existing mapping
            existing.bailiff_id = bailiff_id
            existing.mapping_type = mapping_type
            existing.notes = notes
            existing.reviewed_by = reviewed_by
            existing.reviewed_at = func.now()
            existing.session_id = session_id
        else:
            # Create new mapping
            mapping = NameMappings(
                raw_id=raw_id,
                bailiff_id=bailiff_id,
                mapping_type=mapping_type,
                notes=notes,
                reviewed_by=reviewed_by,
                session_id=session_id
            )
            session.add(mapping)
        
        session.commit()
        return True
        
    except Exception as e:
        st.error(f"Błąd podczas zapisywania: {e}")
        session.rollback()
        return False
        
    finally:
        session.close()

def show_file_upload():
    """Show file upload interface."""
    
    with st.form("file_upload_form"):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            uploaded_file = st.file_uploader(
                "Wybierz plik CSV lub Excel",
                type=['csv', 'xlsx', 'xls'],
                help="Obsługiwane formaty: CSV, Excel (.xlsx, .xls)"
            )
        
        with col2:
            session_name = st.text_input(
                "Nazwa sesji",
                placeholder="np. Analiza_Sierpień_2024",
                help="Unikalna nazwa dla tej sesji analizy"
            )
        
        description = st.text_area(
            "Opis (opcjonalnie)",
            placeholder="Dodatkowe informacje o tym pliku...",
            height=100
        )
        
        # Sheet selector for Excel files
        sheet_name = None
        if uploaded_file and uploaded_file.name.endswith(('.xlsx', '.xls')):
            # Try to read sheet names
            try:
                excel_file = pd.ExcelFile(uploaded_file)
                sheet_options = excel_file.sheet_names
                sheet_name = st.selectbox("Wybierz arkusz", sheet_options)
            except Exception as e:
                st.error(f"Błąd odczytu arkuszy: {e}")
        
        submitted = st.form_submit_button("🚀 Wgraj i przeanalizuj", type="primary")
    
    # Outside the form - handle submission
    if submitted and uploaded_file and session_name:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{uploaded_file.name}") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            temp_path = tmp_file.name
        
        try:
            # Import file processing functions
            import sys
            import os
            current_dir = os.getcwd()
            scripts_path = os.path.join(current_dir, 'archive', 'scripts')
            print(f"🔍 DEBUG: Obecny katalog: {current_dir}")
            print(f"🔍 DEBUG: Ścieżka do skryptów: {scripts_path}")
            print(f"🔍 DEBUG: Czy ścieżka istnieje: {os.path.exists(scripts_path)}")
            print(f"🔍 DEBUG: Zawartość katalogu scripts: {os.listdir(scripts_path) if os.path.exists(scripts_path) else 'Katalog nie istnieje'}")
            
            if scripts_path not in sys.path:
                sys.path.append(scripts_path)
                print(f"✅ DEBUG: Dodano ścieżkę do sys.path: {scripts_path}")
            else:
                print(f"✅ DEBUG: Ścieżka już była w sys.path: {scripts_path}")
            
            print("🔍 DEBUG: Próba importu file_upload...")
            from file_upload import create_analysis_session, process_uploaded_file, delete_session, delete_all_sessions
            print("✅ DEBUG: Import file_upload zakończony pomyślnie")
            
            with st.spinner("Tworzenie sesji..."):
                print(f"🔍 DEBUG: Tworzenie sesji - nazwa: {session_name}, plik: {uploaded_file.name}")
                session_id, message = create_analysis_session(
                    session_name=session_name,
                    filename=uploaded_file.name,
                    description=description
                )
                print(f"🔍 DEBUG: Wynik tworzenia sesji - ID: {session_id}, wiadomość: {message}")
            
            if session_id is not None:
                st.success(f"✅ Sesja utworzona: {message}")
                
                with st.spinner("Przetwarzanie pliku..."):
                    print(f"🔍 DEBUG APP: PRZED wywołaniem process_uploaded_file - ścieżka: {temp_path}, session_id: {session_id}, arkusz: {sheet_name}")
                    print(f"🔍 DEBUG APP: Plik istnieje: {os.path.exists(temp_path)}")
                    print(f"🔍 DEBUG APP: Rozmiar pliku: {os.path.getsize(temp_path) if os.path.exists(temp_path) else 'NIE ISTNIEJE'}")
                    
                    success, result_message = process_uploaded_file(
                        file_path=temp_path,
                        session_id=session_id,
                        sheet_name=sheet_name
                    )
                    print(f"🔍 DEBUG APP: PO wywołaniu process_uploaded_file - sukces: {success}, wiadomość: {result_message}")
                    
                    # Sprawdź końcowy stan
                    try:
                        engine, SessionLocal = get_database_connection()
                        db_session = SessionLocal()
                        final_count = db_session.query(RawNames).filter(RawNames.session_id == session_id).count()
                        print(f"🔍 DEBUG APP: KOŃCOWA liczba rekordów w sesji {session_id}: {final_count}")
                        db_session.close()
                    except Exception as e:
                        print(f"❌ DEBUG APP: Błąd sprawdzania końcowego stanu: {e}")
                
                if success:
                    st.success(f"✅ {result_message}")
                    
                    # Run matching algorithm
                    with st.spinner("Uruchamianie algorytmu dopasowywania..."):
                        try:
                            print("🔍 DEBUG: Rozpoczynanie algorytmu dopasowywania...")
                            print(f"🔍 DEBUG: Session ID: {session_id}")
                            print(f"🔍 DEBUG: Ścieżka skryptów: {scripts_path}")
                            print(f"🔍 DEBUG: sys.path zawiera: {sys.path}")
                            
                            print("🔍 DEBUG: Próba importu session_matching...")
                            from session_matching import run_matching_for_session
                            print("✅ DEBUG: Import session_matching zakończony pomyślnie")
                            
                            print(f"🔍 DEBUG: Uruchamianie run_matching_for_session({session_id})...")
                            match_success, match_message = run_matching_for_session(session_id)
                            print(f"🔍 DEBUG: Wynik dopasowywania: success={match_success}, message={match_message}")
                            
                            if match_success:
                                st.success(f"✅ Dopasowywanie zakończone: {match_message}")
                            else:
                                st.warning(f"⚠️ Problem z dopasowywaniem: {match_message}")
                        except Exception as e:
                            print(f"❌ DEBUG: Błąd podczas dopasowywania: {e}")
                            print(f"❌ DEBUG: Typ błędu: {type(e).__name__}")
                            import traceback
                            print(f"❌ DEBUG: Traceback: {traceback.format_exc()}")
                            st.warning(f"⚠️ Błąd podczas dopasowywania: {e}")
                else:
                    st.error(f"❌ {result_message}")
            else:
                st.error(f"❌ Błąd tworzenia sesji: {message}")
                
        except Exception as e:
            st.error(f"❌ Błąd podczas przetwarzania: {e}")
        finally:
            # Clean up temp file
            try:
                import os
                os.unlink(temp_path)
            except:
                pass
    
    elif submitted:
        if not uploaded_file:
            st.error("❌ Wybierz plik do wgrania")
        if not session_name:
            st.error("❌ Podaj nazwę sesji")
    
    # Auto-refresh button outside form
    if st.button("🔄 Odśwież teraz", key="refresh_after_upload"):
        if 'data_loaded' in st.session_state:
            del st.session_state.data_loaded
        st.rerun()

def main():
    st.set_page_config(
        page_title="System dopasowywania komorników", 
        page_icon="⚖️",
        layout="wide"
    )
    
    # Custom CSS to reduce header padding + HTML title
    st.markdown("""
        <style>
        /* Ukryj toolbar Streamlit */
        .stToolbar {
            display: none !important;
        }
        
        /* Ukryj header Streamlit */
        header[data-testid="stHeader"] {
            display: none !important;
        }
        
        /* Zmniejsz padding głównego kontenera */
        .main > div {
            padding-top: 0.5rem !important;
        }
        
        /* Usuń margines i padding z nagłówka */
        h1 {
            margin-top: 0 !important;
            padding-top: 0 !important;
            margin-bottom: 1rem !important;
        }
        
        /* Zmniejsz padding bloku aplikacji */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }
        
        /* Usuń domyślny header space */
        .main .block-container {
            padding-top: 1rem !important;
        }
        
        /* Custom title styling */
        .custom-title {
            font-size: 2.5rem !important;
            font-weight: 600 !important;
            margin: 0 !important;
            padding: 0.5rem 0 1rem 0 !important;
            color: rgb(49, 51, 63) !important;
            line-height: 1.2 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Custom HTML title instead of st.title to avoid default margins
    st.markdown('<h1 class="custom-title">⚖️ System dopasowywania komorników</h1>', unsafe_allow_html=True)
    
    # Main navigation tabs - always visible
    tab_main, tab_bailiffs, tab_upload, tab_sessions = st.tabs(["🔍 Analiza dopasowań", "👨‍💼 Baza komorników", "📁 Wgraj nowy plik", "🗂️ Zarządzanie sesjami"])
    
    with tab_upload:
        st.header("📁 Wgrywanie nowych plików")
        show_file_upload()
    
    with tab_bailiffs:
        show_bailiffs_management()
    
    with tab_sessions:
        show_sessions_management()

    with tab_main:
        # Session selector
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Get available sessions
            sessions = get_sessions_list()
            
            if sessions:
                session_options = {f"{s['session_name']} ({s['total_records']} rekordów)": s['id'] for s in sessions}
                selected_session_display = st.selectbox(
                    "Wybierz sesję analizy:",
                    options=list(session_options.keys()),
                    help="Wybierz którą sesję chcesz przeglądać"
                )
                selected_session_id = session_options[selected_session_display]
            else:
                st.warning("🆕 Brak dostępnych sesji. Przejdź do zakładki 'Wgraj nowy plik' aby rozpocząć.")
                selected_session_id = None
        
        with col2:
            if st.button("🔄 Odśwież sesje"):
                if 'data_loaded' in st.session_state:
                    del st.session_state.data_loaded
                st.rerun()
        
        st.markdown("---")
        
        # Load data for selected session
        if selected_session_id:
            if 'data_loaded' not in st.session_state or st.session_state.get('current_session_id') != selected_session_id:
                with st.spinner("Ładowanie danych..."):
                    st.session_state.suggestions_df, st.session_state.mapped_raw_ids = load_data(selected_session_id)
                    st.session_state.data_loaded = True
                    st.session_state.current_session_id = selected_session_id
            
            suggestions_df = st.session_state.suggestions_df
            mapped_raw_ids = st.session_state.mapped_raw_ids
        else:
            suggestions_df = pd.DataFrame()
            mapped_raw_ids = set()
        
        if suggestions_df.empty:
            if selected_session_id:
                st.error("Brak danych do wyświetlenia. Upewnij się, że uruchomiłeś algorytm dopasowywania dla tej sesji.")
                return
            else:
                st.info("🆕 Wybierz sesję z menu powyżej lub wgraj nowy plik w zakładce 'Wgraj nowy plik'")
                return
        
        # Filters section
        st.header("🔍 Filtry")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            confidence_filter = st.selectbox(
                "Poziom pewności",
                ["Wszystkie", "high", "medium", "low"],
                index=0
            )
        
        with col2:
            score_threshold = st.slider(
                "Minimalny wynik dopasowania",
                min_value=0.0,
                max_value=100.0,
                value=70.0,
                step=5.0
            )
        
        with col3:
            show_only_unmapped = st.checkbox("Pokaż tylko niedopasowane", value=True)
        
        # Apply filters
        filtered_df = suggestions_df.copy()
        
        if confidence_filter != "Wszystkie":
            filtered_df = filtered_df[filtered_df['confidence_level'] == confidence_filter]
        
        filtered_df = filtered_df[filtered_df['combined_score'] >= score_threshold]
        
        if show_only_unmapped:
            filtered_df = filtered_df[~filtered_df['raw_id'].isin(mapped_raw_ids)]
        
        # Sub-tabs for analysis
        subtab1, subtab2, subtab3 = st.tabs(["🔍 Przegląd dopasowań", "📊 Statystyki", "📋 Export"])
        
        with subtab1:
            st.header("Przegląd i zatwierdzanie dopasowań")
            
            if filtered_df.empty:
                st.info("Brak wyników spełniających kryteria filtrów.")
                return
            
            # Mass approval section
            st.subheader("🚀 Masowe zatwierdzanie")
            
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                mass_threshold = st.number_input(
                    "Próg pewności (%)",
                    min_value=60.0,
                    max_value=100.0,
                    value=90.0,
                    step=5.0,
                    help="Automatycznie zatwierdź najlepsze dopasowania powyżej tego progu"
                )
        
        with col2:
            # Calculate how many would be auto-approved
            auto_approve_candidates = filtered_df[
                (~filtered_df['raw_id'].isin(mapped_raw_ids)) &
                (filtered_df['combined_score'] >= mass_threshold)
            ].groupby('raw_id').first()
            
            candidates_count = len(auto_approve_candidates)
            st.metric("Do zatwierdzenia", candidates_count)
        
        with col3:
            if st.button(
                f"✅ Zatwierdź wszystkie powyżej {mass_threshold}%",
                type="primary",
                disabled=candidates_count == 0,
                help=f"Automatycznie zatwierdzi {candidates_count} najlepszych dopasowań"
            ):
                progress_bar = st.progress(0)
                success_count = 0
                
                for idx, (raw_id, best_match) in enumerate(auto_approve_candidates.iterrows()):
                    if save_mapping(
                        raw_id, 
                        best_match['bailiff_id'], 
                        "accepted", 
                        f"Auto-zatwierdzono - wynik: {best_match['combined_score']:.1f}%",
                        "Auto-System"
                    ):
                        success_count += 1
                    
                    progress_bar.progress((idx + 1) / len(auto_approve_candidates))
                
                st.success(f"✅ Automatycznie zatwierdzono {success_count} dopasowań!")
                # Force reload data
                del st.session_state.data_loaded
                st.rerun()
        
        st.markdown("---")
        
        # Group by raw_id to show suggestions for each name
        grouped = filtered_df.groupby('raw_id')
        
        # Pagination
        items_per_page = st.selectbox("Elementów na stronę", [5, 10, 20, 50], index=1)
        total_groups = len(grouped)
        total_pages = (total_groups - 1) // items_per_page + 1
        
        page = st.number_input(
            f"Strona (1-{total_pages})", 
            min_value=1, 
            max_value=total_pages, 
            value=1
        )
        
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        
        groups_list = list(grouped)
        current_groups = groups_list[start_idx:end_idx]
        
        for i, (raw_id, group) in enumerate(current_groups):
            st.markdown(f"### Nazwa {start_idx + i + 1}")
            
            # Get raw name info
            first_row = group.iloc[0]
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Oryginalna nazwa:** {first_row['raw_text']}")
                st.markdown(f"**Miasto źródłowe:** {first_row['raw_city'] or 'Brak'}")
                
                # Check if already mapped
                if raw_id in mapped_raw_ids:
                    st.success("✅ Ta nazwa została już dopasowana")
                    st.markdown("---")
                    continue
            
            with col2:
                st.markdown(f"**ID:** {raw_id}")
                st.markdown(f"**Liczba sugestii:** {len(group)}")
            
            # Show suggestions
            st.markdown("**Sugerowane dopasowania:**")
            
            for idx, (_, suggestion) in enumerate(group.iterrows()):
                with st.expander(
                    f"Opcja {idx + 1}: {suggestion['bailiff_name']} "
                    f"(Wynik: {suggestion['combined_score']:.1f}% - {suggestion['confidence_level']})"
                ):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.write(f"**Dopasowana nazwa:** {suggestion['bailiff_name']}")
                        st.write(f"**Miasto:** {suggestion['bailiff_city'] or 'Brak'}")
                        st.write(f"**Wynik pełnej nazwy:** {suggestion['fullname_score']:.1f}%")
                        st.write(f"**Wynik miasta:** {suggestion['city_score']:.1f}%")
                        st.write(f"**Algorytm:** {suggestion['algorithm_used']}")
                    
                    with col2:
                        if st.button(f"✅ Zatwierdź", key=f"accept_{suggestion['suggestion_id']}"):
                            if save_mapping(raw_id, suggestion['bailiff_id'], "accepted"):
                                st.success("Dopasowanie zaakceptowane!")
                                del st.session_state.data_loaded
                                st.rerun()
                    
                    with col3:
                        if st.button(f"❌ Odrzuć", key=f"reject_{suggestion['suggestion_id']}"):
                            if save_mapping(raw_id, None, "rejected"):
                                st.info("Dopasowanie odrzucone")
                                del st.session_state.data_loaded
                                st.rerun()            # Manual input option
            with st.expander("📝 Ręczne dopasowanie"):
                manual_notes = st.text_area(
                    "Notatki",
                    placeholder="Opcjonalne notatki...",
                    key=f"notes_{raw_id}"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"💡 Ręczne dopasowanie", key=f"manual_{raw_id}"):
                        if save_mapping(raw_id, None, "manual_new", manual_notes):
                            st.info("Oznaczono do ręcznego dopasowania")
                            del st.session_state.data_loaded
                            st.rerun()
                
                with col2:
                    if st.button(f"🚫 Brak dopasowania", key=f"no_match_{raw_id}"):
                        if save_mapping(raw_id, None, "no_match", manual_notes):
                            st.info("Oznaczono jako brak dopasowania")
                            del st.session_state.data_loaded
                            st.rerun()
            
            st.markdown("---")
        
        with subtab2:
            st.header("Statystyki dopasowań")
            
            # Calculate statistics
            total_suggestions = len(suggestions_df)
            unique_raw_names = suggestions_df['raw_id'].nunique()
            already_mapped = len(mapped_raw_ids)
            remaining = unique_raw_names - already_mapped
            confidence_counts = suggestions_df['confidence_level'].value_counts()
            
            # Display key metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Łączna liczba sugestii", total_suggestions)
            with col2:
                st.metric("Unikalne nazwy do dopasowania", unique_raw_names)
            with col3:
                st.metric("Już dopasowane", already_mapped)
            with col4:
                st.metric("Do przejrzenia", remaining)
            
            st.markdown("---")
        
        # Score distribution
        fig_scores = px.histogram(
            suggestions_df, 
            x='combined_score', 
            nbins=20,
            title="Rozkład wyników dopasowań",
            labels={'combined_score': 'Wynik dopasowania (%)', 'count': 'Liczba sugestii'}
        )
        st.plotly_chart(fig_scores, use_container_width=True)
        
        # Confidence levels
        fig_confidence = px.pie(
            values=confidence_counts.values,
            names=confidence_counts.index,
            title="Rozkład poziomów pewności"
        )
        st.plotly_chart(fig_confidence, use_container_width=True)
        
        # Top cities by matches
        city_stats = suggestions_df.groupby('bailiff_city').size().sort_values(ascending=False).head(15)
        fig_cities = px.bar(
            x=city_stats.values,
            y=city_stats.index,
            orientation='h',
            title="Top 15 miast według liczby sugestii",
            labels={'x': 'Liczba sugestii', 'y': 'Miasto'}
        )
        st.plotly_chart(fig_cities, use_container_width=True)
        
        with subtab3:
            st.header("Export wyników")
        
        engine, SessionLocal = get_database_connection()
        session = SessionLocal()
        
        try:
            # Load approved mappings
            mappings = session.query(NameMappings).join(RawNames).all()
            
            export_data = []
            for mapping in mappings:
                raw_name = session.query(RawNames).get(mapping.raw_id)
                bailiff = session.query(BailiffDict).get(mapping.bailiff_id) if mapping.bailiff_id is not None else None
                
                export_data.append({
                    'source_file': raw_name.source_file if raw_name else '',
                    'source_row': raw_name.source_row if raw_name else '',
                    'raw_text': raw_name.raw_text if raw_name else '',
                    'source_city': raw_name.source_city if raw_name else '',
                    'mapping_type': mapping.mapping_type,
                    'matched_name': bailiff.original_nazwisko if bailiff else '',
                    'matched_city': bailiff.original_miasto if bailiff else '',
                    'matched_email': bailiff.email if bailiff else '',
                    'matched_phone': bailiff.telefon if bailiff else '',
                    'notes': mapping.notes,
                    'reviewed_by': mapping.reviewed_by,
                    'reviewed_at': mapping.reviewed_at
                })
            
            if export_data:
                export_df = pd.DataFrame(export_data)
                
                st.write(f"**Gotowe do eksportu:** {len(export_df)} dopasowań")
                
                # Show preview
                st.subheader("Podgląd danych")
                st.dataframe(export_df.head())
                
                # Download button
                csv = export_df.to_csv(index=False)
                st.download_button(
                    label="📥 Pobierz CSV",
                    data=csv,
                    file_name="bailiff_mappings.csv",
                    mime="text/csv"
                )
            else:
                st.info("Brak zatwierdzonych dopasowań do eksportu.")
        
        finally:
            session.close()

def show_bailiffs_management():
    """Display bailiffs database management interface"""
    st.header("👨‍💼 Zarządzanie bazą komorników")
    
    engine, SessionLocal = get_database_connection()
    session = SessionLocal()
    try:
        # Main tabs for bailiffs management
        bailiff_tab1, bailiff_tab2, bailiff_tab3 = st.tabs(["📋 Lista komorników", "➕ Dodaj nowego", "📊 Statystyki bazy"])
        
        with bailiff_tab1:
            st.subheader("Lista wszystkich komorników")
            
            # Search and filter options
            col1, col2, col3 = st.columns(3)
            with col1:
                search_name = st.text_input("🔍 Szukaj po nazwisku:", placeholder="np. Kowalski")
            with col2:
                search_city = st.text_input("🏙️ Szukaj po mieście:", placeholder="np. Warszawa")
            with col3:
                search_court = st.text_input("🏛️ Szukaj po sądzie:", placeholder="np. Rejonowy")
            
            # Build query with filters
            query = session.query(BailiffDict)
            
            if search_name:
                query = query.filter(BailiffDict.normalized_lastname.contains(search_name.lower()))
            if search_city:
                query = query.filter(BailiffDict.normalized_city.contains(search_city.lower()))
            if search_court:
                query = query.filter(BailiffDict.original_sad.contains(search_court))
            
            bailiffs = query.order_by(BailiffDict.normalized_lastname, BailiffDict.normalized_firstname).all()
            
            if bailiffs:
                st.write(f"**Znaleziono {len(bailiffs)} komorników**")
                
                # Pagination
                items_per_page = 20
                total_pages = (len(bailiffs) + items_per_page - 1) // items_per_page
                
                if total_pages > 1:
                    page = st.selectbox("Strona:", range(1, total_pages + 1), key="bailiff_page")
                    start_idx = (page - 1) * items_per_page
                    end_idx = start_idx + items_per_page
                    bailiffs_page = bailiffs[start_idx:end_idx]
                else:
                    bailiffs_page = bailiffs
                
                # Display bailiffs table
                for bailiff in bailiffs_page:
                    with st.expander(f"👨‍💼 {bailiff.normalized_lastname} {bailiff.normalized_firstname or ''} - {bailiff.normalized_city}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Dane podstawowe:**")
                            st.write(f"**ID:** {bailiff.id}")
                            st.write(f"**Nazwisko:** {bailiff.original_nazwisko}")
                            if bailiff.original_imie:
                                st.write(f"**Imię:** {bailiff.original_imie}")
                            st.write(f"**Miasto:** {bailiff.original_miasto}")
                            st.write(f"**Sąd:** {bailiff.original_sad}")
                            
                        with col2:
                            st.write("**Dane kontaktowe:**")
                            if bailiff.adres:
                                st.write(f"**Adres:** {bailiff.adres}")
                            if bailiff.kod_pocztowy:
                                st.write(f"**Kod pocztowy:** {bailiff.kod_pocztowy}")
                            if bailiff.telefon:
                                st.write(f"**Telefon:** {bailiff.telefon}")
                            if bailiff.email:
                                st.write(f"**Email:** {bailiff.email}")
                        
                        if bailiff.bank or bailiff.numer_konta:
                            st.write("**Dane bankowe:**")
                            if bailiff.bank:
                                st.write(f"**Bank:** {bailiff.bank}")
                            if bailiff.numer_konta:
                                st.write(f"**Numer konta:** {bailiff.numer_konta}")
                        
                        # Edit button
                        if st.button(f"✏️ Edytuj", key=f"edit_{bailiff.id}"):
                            st.session_state[f"edit_bailiff_{bailiff.id}"] = True
                        
                        # Edit form (if edit mode is activated)
                        if st.session_state.get(f"edit_bailiff_{bailiff.id}", False):
                            st.markdown("---")
                            st.write("**Edycja danych komornika:**")
                            
                            with st.form(f"edit_form_{bailiff.id}"):
                                new_nazwisko = st.text_input("Nazwisko:", value=bailiff.original_nazwisko or "")
                                new_imie = st.text_input("Imię:", value=bailiff.original_imie or "")
                                new_miasto = st.text_input("Miasto:", value=bailiff.original_miasto or "")
                                new_sad = st.text_area("Sąd:", value=bailiff.original_sad or "")
                                new_adres = st.text_input("Adres:", value=bailiff.adres or "")
                                new_kod = st.text_input("Kod pocztowy:", value=bailiff.kod_pocztowy or "")
                                new_telefon = st.text_input("Telefon:", value=bailiff.telefon or "")
                                new_email = st.text_input("Email:", value=bailiff.email or "")
                                new_bank = st.text_input("Bank:", value=bailiff.bank or "")
                                new_konto = st.text_input("Numer konta:", value=bailiff.numer_konta or "")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    save_edit = st.form_submit_button("💾 Zapisz zmiany")
                                with col2:
                                    cancel_edit = st.form_submit_button("❌ Anuluj")
                                
                                if save_edit:
                                    # Update bailiff data
                                    bailiff.original_nazwisko = new_nazwisko
                                    bailiff.original_imie = new_imie
                                    bailiff.original_miasto = new_miasto
                                    bailiff.original_sad = new_sad
                                    bailiff.adres = new_adres
                                    bailiff.kod_pocztowy = new_kod
                                    bailiff.telefon = new_telefon
                                    bailiff.email = new_email
                                    bailiff.bank = new_bank
                                    bailiff.numer_konta = new_konto
                                    
                                    # Update normalized fields
                                    bailiff.normalized_lastname = new_nazwisko.lower() if new_nazwisko else ""
                                    bailiff.normalized_firstname = new_imie.lower() if new_imie else ""
                                    bailiff.normalized_city = new_miasto.lower() if new_miasto else ""
                                    bailiff.normalized_fullname = f"{new_nazwisko.lower()} {new_imie.lower() if new_imie else ''}".strip()
                                    
                                    session.commit()
                                    st.success("✅ Dane komornika zostały zaktualizowane!")
                                    del st.session_state[f"edit_bailiff_{bailiff.id}"]
                                    st.rerun()
                                
                                if cancel_edit:
                                    del st.session_state[f"edit_bailiff_{bailiff.id}"]
                                    st.rerun()
            else:
                st.info("Nie znaleziono komorników spełniających kryteria.")
        
        with bailiff_tab2:
            st.subheader("Dodaj nowego komornika")
            
            with st.form("add_bailiff_form"):
                st.write("**Dane podstawowe:**")
                col1, col2 = st.columns(2)
                with col1:
                    new_nazwisko = st.text_input("Nazwisko:*", placeholder="np. Kowalski")
                    new_imie = st.text_input("Imię:", placeholder="np. Jan")
                    new_miasto = st.text_input("Miasto:*", placeholder="np. Warszawa")
                with col2:
                    new_sad = st.text_area("Sąd:*", placeholder="np. Sąd Rejonowy w Warszawie")
                    new_adres = st.text_input("Adres:", placeholder="np. ul. Główna 123")
                    new_kod = st.text_input("Kod pocztowy:", placeholder="np. 00-001")
                
                st.write("**Dane kontaktowe:**")
                col1, col2 = st.columns(2)
                with col1:
                    new_telefon = st.text_input("Telefon:", placeholder="np. 123 456 789")
                    new_email = st.text_input("Email:", placeholder="np. komornik@example.com")
                with col2:
                    new_bank = st.text_input("Bank:", placeholder="np. PKO BP")
                    new_konto = st.text_input("Numer konta:", placeholder="np. 12 3456 7890 1234 5678 9012 3456")
                
                submitted = st.form_submit_button("➕ Dodaj komornika")
                
                if submitted:
                    if new_nazwisko and new_miasto and new_sad:
                        # Create new bailiff
                        new_bailiff = BailiffDict(
                            original_nazwisko=new_nazwisko,
                            original_imie=new_imie,
                            original_miasto=new_miasto,
                            original_sad=new_sad,
                            adres=new_adres,
                            kod_pocztowy=new_kod,
                            telefon=new_telefon,
                            email=new_email,
                            bank=new_bank,
                            numer_konta=new_konto,
                            normalized_lastname=new_nazwisko.lower(),
                            normalized_firstname=new_imie.lower() if new_imie else "",
                            normalized_city=new_miasto.lower(),
                            normalized_fullname=f"{new_nazwisko.lower()} {new_imie.lower() if new_imie else ''}".strip()
                        )
                        
                        session.add(new_bailiff)
                        session.commit()
                        st.success("✅ Nowy komornik został dodany do bazy!")
                        st.rerun()
                    else:
                        st.error("❌ Proszę wypełnić wymagane pola: Nazwisko, Miasto, Sąd")
        
        with bailiff_tab3:
            st.subheader("Statystyki bazy komorników")
            
            # Basic statistics
            total_bailiffs = session.query(BailiffDict).count()
            bailiffs_with_email = session.query(BailiffDict).filter(BailiffDict.email.isnot(None), BailiffDict.email != "").count()
            bailiffs_with_phone = session.query(BailiffDict).filter(BailiffDict.telefon.isnot(None), BailiffDict.telefon != "").count()
            bailiffs_with_bank = session.query(BailiffDict).filter(BailiffDict.numer_konta.isnot(None), BailiffDict.numer_konta != "").count()
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Łączna liczba komorników", total_bailiffs)
            with col2:
                email_percent = f"{bailiffs_with_email/total_bailiffs*100:.1f}%" if total_bailiffs > 0 else "0%"
                st.metric("Z adresem email", bailiffs_with_email, email_percent)
            with col3:
                phone_percent = f"{bailiffs_with_phone/total_bailiffs*100:.1f}%" if total_bailiffs > 0 else "0%"
                st.metric("Z numerem telefonu", bailiffs_with_phone, phone_percent)
            with col4:
                bank_percent = f"{bailiffs_with_bank/total_bailiffs*100:.1f}%" if total_bailiffs > 0 else "0%"
                st.metric("Z danymi bankowymi", bailiffs_with_bank, bank_percent)
            
            st.markdown("---")
            
            # Cities statistics
            city_stats = session.query(
                BailiffDict.normalized_city,
                func.count(BailiffDict.id).label('count')
            ).group_by(BailiffDict.normalized_city).order_by(func.count(BailiffDict.id).desc()).limit(15).all()
            
            if city_stats:
                st.write("**Top 15 miast według liczby komorników:**")
                cities_df = pd.DataFrame(city_stats, columns=['Miasto', 'Liczba komorników'])
                cities_df['Miasto'] = cities_df['Miasto'].str.title()
                
                fig_cities = px.bar(
                    cities_df,
                    x='Liczba komorników',
                    y='Miasto',
                    orientation='h',
                    title="Rozkład komorników według miast"
                )
                fig_cities.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_cities, use_container_width=True)
    
    finally:
        session.close()

def show_sessions_management():
    """Display sessions management interface"""
    # Import functions for session deletion
    from file_upload import delete_session, delete_all_sessions
    
    st.header("🗂️ Zarządzanie sesjami analizy")
    
    # Get list of sessions
    sessions = get_sessions_list()
    
    if not sessions:
        st.info("🔍 Brak sesji do zarządzania")
        return
    
    # Main tabs for session management 
    session_tab1, session_tab2 = st.tabs(["📋 Lista sesji", "🗑️ Usuwanie sesji"])
    
    with session_tab1:
        st.subheader("Lista wszystkich sesji")
        
        # Display sessions in a nice table format
        for i, session in enumerate(sessions):
            with st.expander(f"📁 {session['session_name']} ({session['status']})", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Nazwa pliku:** {session['filename']}")
                    st.write(f"**Status:** {session['status']}")
                    st.write(f"**Utworzono:** {session['created_at'].strftime('%Y-%m-%d %H:%M')}")
                
                with col2:
                    st.write(f"**Rekordów ogółem:** {session['total_records']}")
                    st.write(f"**Przetworzono:** {session['processed_records']}")
                    st.write(f"**Dopasowano:** {session['matched_records']}")
                
                if session['description']:
                    st.write(f"**Opis:** {session['description']}")
    
    with session_tab2:
        st.subheader("Usuwanie sesji")
        
        # Warning message
        st.warning("⚠️ **UWAGA:** Usunięcie sesji jest nieodwracalne! Wszystkie dane związane z sesją zostaną permanently usunięte.")
        
        # Option 1: Delete individual session
        st.markdown("### 🗑️ Usuń pojedynczą sesję")
        
        # Session selector for deletion
        session_options = {f"{s['session_name']} (ID: {s['id']})": s['id'] for s in sessions}
        
        selected_session_name = st.selectbox(
            "Wybierz sesję do usunięcia:",
            options=list(session_options.keys()),
            help="Wybierz sesję którą chcesz usunąć wraz z wszystkimi związanymi danymi"
        )
        
        if selected_session_name:
            selected_session_id = session_options[selected_session_name]
            selected_session = next(s for s in sessions if s['id'] == selected_session_id)
            
            # Show session details before deletion
            st.info(f"""
            **Sesja do usunięcia:**
            - **Nazwa:** {selected_session['session_name']}
            - **Plik:** {selected_session['filename']}
            - **Rekordów:** {selected_session['total_records']}
            - **Status:** {selected_session['status']}
            """)
            
            # Confirmation checkbox
            confirm_single = st.checkbox(
                f"Potwierdzam usunięcie sesji '{selected_session['session_name']}'",
                key="confirm_single_deletion"
            )
            
            if st.button("🗑️ Usuń wybraną sesję", disabled=not confirm_single, type="primary"):
                with st.spinner("Usuwanie sesji..."):
                    try:
                        success, message = delete_session(selected_session_id)
                        if success:
                            st.success(f"✅ {message}")
                            st.rerun()  # Refresh the page to update the list
                        else:
                            st.error(f"❌ {message}")
                    except Exception as e:
                        st.error(f"❌ Błąd podczas usuwania sesji: {str(e)}")
        
        st.markdown("---")
        
        # Option 2: Delete all sessions
        st.markdown("### 🚨 Usuń wszystkie sesje")
        st.error("🚨 **UWAGA KRYTYCZNA:** Ta operacja usunie WSZYSTKIE sesje i związane z nimi dane!")
        
        # Double confirmation for delete all
        confirm_all_1 = st.checkbox("Rozumiem że to usunie WSZYSTKIE sesje", key="confirm_all_1")
        confirm_all_2 = st.checkbox("Jestem pewien że chcę usunąć wszystkie dane", key="confirm_all_2") 
        
        if confirm_all_1 and confirm_all_2:
            # Show what will be deleted
            total_sessions = len(sessions)
            total_records = sum(s['total_records'] for s in sessions if s['total_records'])
            
            st.warning(f"""
            **Zostanie usunięte:**
            - **Sesji:** {total_sessions}
            - **Rekordów:** {total_records}
            - **Wszystkie dopasowania i sugestie**
            - **Wszystkie mapowania nazw**
            """)
            
            if st.button("🚨 USUŃ WSZYSTKIE SESJE", type="secondary"):
                with st.spinner("Usuwanie wszystkich sesji..."):
                    try:
                        success, message = delete_all_sessions()
                        if success:
                            st.success(f"✅ {message}")
                            st.rerun()  # Refresh the page
                        else:
                            st.error(f"❌ {message}")
                    except Exception as e:
                        st.error(f"❌ Błąd podczas usuwania wszystkich sesji: {str(e)}")

if __name__ == "__main__":
    main()
