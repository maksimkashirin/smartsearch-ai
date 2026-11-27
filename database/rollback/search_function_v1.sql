CREATE OR REPLACE FUNCTION smart_search(
    user_query TEXT,
    result_limit INTEGER DEFAULT 12
)
RETURNS TABLE (
    id TEXT,
    name TEXT,
    vendor TEXT,
    category_path TEXT,
    price NUMERIC,
    url TEXT,
    score DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
WITH query AS (
    SELECT normalize_query(user_query) AS q
),
prepared AS (
    SELECT
        q,
        plainto_tsquery('russian', q) AS tsq
    FROM query
),
candidates AS (
    SELECT
        p.*,
        q.q,
        q.tsq,
        replace(lower(coalesce(c.name, '')), 'ё', 'е')
            AS family_name
    FROM search_products p
    CROSS JOIN prepared q
    LEFT JOIN categories c ON c.id = p.group_id
    WHERE q.q <> ''
      AND (
          p.search_vector @@ q.tsq
          OR p.normalized_name %> q.q
          OR lower(coalesce(c.name, '')) %> q.q
          OR strpos(lower(coalesce(c.name, '')), q.q) > 0
      )
),
ranked AS (
    SELECT
        p.*,
        (
            p.family_name = p.q
            OR (
                strpos(p.q, ' ') > 0
                AND strpos(p.family_name, p.q) = 1
            )
        ) AS family_hit,
        (
            5.0 * ts_rank_cd(p.search_vector, p.tsq, 32)
            + 3.0 * word_similarity(p.q, p.normalized_name)
            + 2.0 * word_similarity(p.q, lower(p.category_path))
            + 5.0 * word_similarity(p.q, p.family_name)
            + CASE
                WHEN p.family_name = p.q THEN 18.0
                WHEN strpos(p.family_name, p.q) = 1 THEN 12.0
                ELSE 0.0
              END
            + CASE
                WHEN p.normalized_name = p.q THEN 10.0
                WHEN strpos(p.normalized_name, p.q) = 1 THEN 7.0
                WHEN strpos(p.normalized_name, p.q) > 0 THEN 3.0
                ELSE 0.0
              END
            + CASE
                WHEN p.q IN (
                    'сервер', 'серверы', 'серверное оборудование'
                )
                AND p.category_path ~* '^Серверы и опции / [^/]*сервер'
                THEN 12.0
                ELSE 0.0
              END
            - CASE
                WHEN p.normalized_name ~
                    '^(сертификат|техподдержка|продление)'
                AND p.q !~ '(поддержк|сертификат|продлен)'
                THEN 6.0
                ELSE 0.0
              END
        )::double precision AS relevance
    FROM candidates p
),
unique_names AS (
    SELECT
        r.*,
        row_number() OVER (
            PARTITION BY r.normalized_name
            ORDER BY r.relevance DESC, r.id
        ) AS name_rank
    FROM ranked r
),
grouped AS (
    SELECT
        r.*,
        row_number() OVER (
            PARTITION BY coalesce(
                'g:' || nullif(r.group_id, ''),
                'n:' || r.normalized_name
            )
            ORDER BY r.relevance DESC, r.id
        ) AS group_rank
    FROM unique_names r
    WHERE r.name_rank = 1
)
SELECT
    d.id,
    d.name,
    d.vendor,
    d.category_path,
    d.price,
    d.url,
    d.relevance
FROM grouped d
ORDER BY
    d.family_hit DESC,
    CASE WHEN d.family_hit THEN 1 ELSE d.group_rank END,
    d.relevance DESC,
    d.id
LIMIT greatest(1, least(coalesce(result_limit, 12), 100));
$$;
