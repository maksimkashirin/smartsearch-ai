def get_suggestions(conn, query, limit=8):
    q = " ".join(
        query.lower().replace("ё", "е").split()
    )

    if len(q) < 2:
        return []

    rows = conn.execute(
        """
        WITH term AS (
            SELECT %s::text AS q
        ),
        candidates AS (
            SELECT
                c.name AS suggestion,
                CASE
                    WHEN starts_with(
                        replace(lower(c.name), 'ё', 'е'),
                        t.q
                    ) THEN 0
                    ELSE 2
                END AS priority
            FROM categories c
            CROSS JOIN term t
            WHERE strpos(
                replace(lower(c.name), 'ё', 'е'),
                t.q
            ) > 0
              AND length(c.name) <= 250
              AND EXISTS (
                  SELECT 1
                  FROM search_products p
                  WHERE p.group_id = c.id
                     OR p.category_id = c.id
              )

            UNION ALL

            SELECT
                p.name AS suggestion,
                CASE
                    WHEN starts_with(
                        p.normalized_name, t.q
                    ) THEN 1
                    ELSE 3
                END AS priority
            FROM search_products p
            CROSS JOIN term t
            WHERE strpos(p.normalized_name, t.q) > 0
              AND length(p.name) <= 250
        )
        SELECT suggestion
        FROM candidates
        GROUP BY suggestion
        ORDER BY
            min(priority),
            length(suggestion),
            suggestion
        LIMIT %s
        """,
        (q, limit)
    ).fetchall()

    return [row["suggestion"] for row in rows]
