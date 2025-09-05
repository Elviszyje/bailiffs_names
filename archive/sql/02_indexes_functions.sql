-- Additional indexes and functions for text matching
-- Run after the Python models have created the base tables

-- Create trigram indexes for fast similarity search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bailiffs_dict_normalized_fullname_trgm 
ON bailiffs_dict USING gin (normalized_fullname gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bailiffs_dict_normalized_lastname_trgm 
ON bailiffs_dict USING gin (normalized_lastname gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bailiffs_dict_normalized_firstname_trgm 
ON bailiffs_dict USING gin (normalized_firstname gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_raw_names_normalized_text_trgm 
ON raw_names USING gin (normalized_text gin_trgm_ops);

-- Create function for normalized text similarity search
CREATE OR REPLACE FUNCTION find_similar_bailiffs(
    input_text TEXT,
    similarity_threshold REAL DEFAULT 0.3,
    max_results INTEGER DEFAULT 10
) RETURNS TABLE (
    bailiff_id INTEGER,
    full_name TEXT,
    similarity_score REAL,
    apelacja TEXT,
    miasto TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        bd.id,
        CONCAT(bd.imie, ' ', bd.nazwisko) as full_name,
        similarity(bd.normalized_fullname, unaccent(lower(input_text))) as sim_score,
        bd.apelacja,
        bd.miasto
    FROM bailiffs_dict bd
    WHERE 
        bd.is_active = true 
        AND similarity(bd.normalized_fullname, unaccent(lower(input_text))) > similarity_threshold
    ORDER BY sim_score DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Create materialized view for quick similarity lookup
CREATE MATERIALIZED VIEW IF NOT EXISTS bailiff_similarity_cache AS
SELECT 
    bd1.id as source_id,
    bd2.id as target_id,
    similarity(bd1.normalized_fullname, bd2.normalized_fullname) as similarity_score
FROM bailiffs_dict bd1
CROSS JOIN bailiffs_dict bd2  
WHERE 
    bd1.id < bd2.id 
    AND similarity(bd1.normalized_fullname, bd2.normalized_fullname) > 0.3
    AND bd1.is_active = true 
    AND bd2.is_active = true;

-- Create index on the materialized view
CREATE INDEX IF NOT EXISTS idx_bailiff_similarity_cache_score 
ON bailiff_similarity_cache (similarity_score DESC);

-- Function to refresh the similarity cache
CREATE OR REPLACE FUNCTION refresh_similarity_cache() RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY bailiff_similarity_cache;
END;
$$ LANGUAGE plpgsql;
