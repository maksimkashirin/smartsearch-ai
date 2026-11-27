CREATE OR REPLACE FUNCTION baseline_search(
    user_query TEXT,
    result_limit INTEGER DEFAULT 8
)
RETURNS TABLE (
    id TEXT,
    name TEXT,
    vendor TEXT,
    category_path TEXT,
    price NUMERIC,
    url TEXT
)
LANGUAGE sql
STABLE
AS $$
SELECT
    p.id,
    p.name,
    p.vendor,
    p.category_path,
    p.price,
    p.url
FROM search_products p
WHERE btrim(user_query) <> ''
  AND strpos(
      lower(p.name),
      lower(btrim(user_query))
  ) > 0
ORDER BY
    CASE
        WHEN lower(p.name) = lower(btrim(user_query))
        THEN 0
        WHEN strpos(
            lower(p.name),
            lower(btrim(user_query))
        ) = 1
        THEN 1
        ELSE 2
    END,
    length(p.name),
    p.id
LIMIT greatest(1, least(result_limit, 50));
$$;
