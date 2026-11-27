CREATE OR REPLACE FUNCTION hybrid_search(
    user_query TEXT,
    query_vector vector(384),
    result_limit INTEGER DEFAULT 8
)
RETURNS TABLE (
    id TEXT,
    name TEXT,
    vendor TEXT,
    category_path TEXT,
    price NUMERIC,
    url TEXT,
    score DOUBLE PRECISION,
    semantic_similarity DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
WITH lexical AS MATERIALIZED (
    SELECT
        l.id,
        l.ordinality AS lexical_rank
    FROM smart_search(user_query, 40)
        WITH ORDINALITY AS l
),
semantic_candidates AS MATERIALIZED (
    SELECT
        e.product_id AS id,
        e.embedding <=> query_vector AS distance
    FROM product_embeddings e
    WHERE query_vector IS NOT NULL
    ORDER BY e.embedding <=> query_vector
    LIMIT 80
),
semantic AS (
    SELECT
        s.id,
        1.0 - s.distance AS similarity,
        row_number() OVER (
            ORDER BY s.distance, s.id
        ) AS semantic_rank
    FROM semantic_candidates s
),
combined AS (
    SELECT
        coalesce(l.id, s.id) AS id,
        (
            coalesce(1.3 / (60 + l.lexical_rank), 0)
            +
            coalesce(1.0 / (60 + s.semantic_rank), 0)
        )::double precision AS relevance,
        s.similarity
    FROM lexical l
    FULL JOIN semantic s ON l.id = s.id
    WHERE l.id IS NOT NULL
       OR s.similarity >= 0.84
),
ranked AS (
    SELECT
        p.*,
        c.relevance,
        c.similarity,
        row_number() OVER (
            PARTITION BY p.normalized_name
            ORDER BY c.relevance DESC, p.id
        ) AS name_rank
    FROM combined c
    JOIN search_products p ON p.id = c.id
)
SELECT
    r.id,
    r.name,
    r.vendor,
    r.category_path,
    r.price,
    r.url,
    r.relevance,
    r.similarity
FROM ranked r
WHERE r.name_rank = 1
ORDER BY r.relevance DESC, r.id
LIMIT greatest(1, least(coalesce(result_limit, 8), 50));
$$;
