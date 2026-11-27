RULES = {
    "кибер бэкап": (
        r"кибер[ -]*б[эе]кап",
        "%киберпротект%"
    ),
    "кибербэкап": (
        r"кибер[ -]*б[эе]кап",
        "%киберпротект%"
    ),
    "сканер-вс": (
        r"сканер[-– ]*вс",
        ""
    ),
    "сканер вс": (
        r"сканер[-– ]*вс",
        ""
    ),
    "крипто про csp 5.0": (
        r"^криптопро csp.*5[.]0",
        ""
    ),
    "криптопро csp 5.0": (
        r"^криптопро csp.*5[.]0",
        ""
    ),
    "365": (
        r"^microsoft 365",
        ""
    ),
    "microsoft office для дома и бизнеса": (
        r"^microsoft office для дома и бизнеса",
        ""
    ),
    "anydesk": (
        r"^anydesk",
        ""
    )
}


def refine_products(conn, query, items, limit):
    q = " ".join(query.lower().strip().split())
    rule = RULES.get(q)

    if not rule:
        return None

    pattern, vendor = rule
    existing = {item["id"]: item for item in items}

    rows = conn.execute(
        """
        WITH candidates AS (
            SELECT DISTINCT ON (p.normalized_name)
                p.id,
                p.name,
                p.vendor,
                p.category_path,
                p.price,
                p.url,
                p.normalized_name
            FROM search_products p
            WHERE p.normalized_name ~ %s
              AND (
                  %s = ''
                  OR coalesce(p.vendor, '') ILIKE %s
              )
            ORDER BY p.normalized_name, p.id
        )
        SELECT id, name, vendor, category_path, price, url
        FROM candidates
        ORDER BY
            CASE
                WHEN %s AND normalized_name ~
                    '(для семьи|family)'
                THEN 0
                WHEN %s THEN 1
                ELSE 0
            END,
            CASE
                WHEN normalized_name ~
                    '(продлен|обновлен|расширен|сертификат|дополнительн|additional|cross.grade|дистрибутив)'
                THEN 1
                ELSE 0
            END,
            coalesce(
                array_position(%s::text[], id),
                1000
            ),
            id
        LIMIT %s
        """,
        (
            pattern,
            vendor,
            vendor,
            q == "365",
            q == "365",
            list(existing),
            limit
        )
    ).fetchall()

    result = []

    for row in rows:
        item = dict(row)
        previous = existing.get(item["id"], {})

        item["score"] = previous.get("score")
        item["semantic_similarity"] = previous.get(
            "semantic_similarity"
        )
        item["match_source"] = "catalog_family"

        result.append(item)

    return result
