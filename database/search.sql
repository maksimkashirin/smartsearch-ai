CREATE MATERIALIZED VIEW IF NOT EXISTS search_products AS
WITH RECURSIVE category_tree AS (
    SELECT
        c.id,
        c.name::text AS category_path,
        ARRAY[c.id] AS visited
    FROM categories c
    WHERE c.parent_id IS NULL
       OR c.parent_id = ''
       OR NOT EXISTS (
           SELECT 1 FROM categories parent
           WHERE parent.id = c.parent_id
       )

    UNION ALL

    SELECT
        c.id,
        t.category_path || ' / ' || c.name,
        t.visited || c.id
    FROM categories c
    JOIN category_tree t ON c.parent_id = t.id
    WHERE NOT c.id = ANY(t.visited)
)
SELECT
    p.id,
    p.group_id,
    p.name,
    p.vendor,
    p.vendor_code,
    p.category_id,
    p.price,
    p.url,
    p.picture,
    COALESCE(t.category_path, c.name, '') AS category_path,

    replace(lower(p.name), 'ё', 'е') AS normalized_name,

    setweight(
        to_tsvector('russian', COALESCE(p.name, '')),
        'A'
    ) ||
    setweight(
        to_tsvector(
            'russian',
            COALESCE(t.category_path, c.name, '')
        ),
        'A'
    ) ||
    setweight(
        to_tsvector(
            'russian',
            concat_ws(' ', p.vendor, p.vendor_code)
        ),
        'B'
    ) ||
    setweight(
        to_tsvector(
            'russian',
            left(regexp_replace(
                COALESCE(p.description, ''),
                '<[^>]*>', ' ', 'g'
            ), 3000)
        ),
        'C'
    ) AS search_vector

FROM products p
LEFT JOIN category_tree t ON p.category_id = t.id
LEFT JOIN categories c ON p.category_id = c.id
WHERE p.available = true;

CREATE UNIQUE INDEX IF NOT EXISTS idx_search_id
ON search_products(id);

CREATE INDEX IF NOT EXISTS idx_search_fts
ON search_products USING GIN(search_vector);

CREATE INDEX IF NOT EXISTS idx_search_trgm
ON search_products USING GIN(normalized_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_search_category
ON search_products(category_id);

ANALYZE search_products;
