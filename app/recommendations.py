RULES = [
    {
        "patterns": ["%кибер бэкап%", "%cyber backup%"],
        "purpose": "Резервное копирование и восстановление",
        "source": "https://cyberprotect.ru/podderzhivaemyie-texnologii/cyber-backup-astra-linux-specialedition/"
    },
    {
        "patterns": ["%kaspersky endpoint security%linux%"],
        "purpose": "Защита рабочих станций и серверов Linux",
        "source": "https://astra.ru/ready-for-astra/compatible-software/"
    },
    {
        "patterns": ["КриптоПро CSP 5.0:%серверная лицензия%"],
        "purpose": "Криптографическая защита сервера",
        "source": "https://astra.ru/ready-for-astra/compatible-software/versions/50336/"
    }
]


def recommend_astra(conn, query, items):
    normalized = query.lower()

    is_astra = any(
        term in normalized
        for term in ("astra linux", "астра линукс", "alse")
    )

    if not is_astra:
        is_astra = any(
            "операционные системы" in
            (item.get("category_path") or "").lower()
            and "astra linux" in item["name"].lower()
            for item in items[:1]
        )

    if not is_astra:
        return []

    excluded = [item["id"] for item in items]
    recommendations = []

    for rule in RULES:
        row = conn.execute(
            """
            SELECT
                p.id,
                p.name,
                p.vendor,
                p.price,
                p.url,
                p.category_path
            FROM search_products p
            LEFT JOIN categories c ON c.id = p.group_id
            WHERE (
                p.name ILIKE ANY(%s)
                OR coalesce(c.name, '') ILIKE ANY(%s)
            )
              AND NOT (p.id = ANY(%s::text[]))
            ORDER BY
                CASE WHEN p.name ILIKE ANY(%s)
                     THEN 0 ELSE 1 END,
                CASE WHEN p.normalized_name ~
                    '(продлен|техподдерж|сертификат)'
                     THEN 1 ELSE 0 END,
                p.price IS NULL,
                p.id
            LIMIT 1
            """,
            (
                rule["patterns"],
                rule["patterns"],
                excluded,
                rule["patterns"]
            )
        ).fetchone()

        if row:
            row = dict(row)
            row["purpose"] = rule["purpose"]
            row["source"] = rule["source"]
            row["source_type"] = "vendor_family"
            row["note"] = (
                "Проверьте совместимость конкретной "
                "версии, лицензии и платформы."
            )

            recommendations.append(row)
            excluded.append(row["id"])

    return recommendations


from app.complementary import recommend_complementary


def recommend(conn, query, items):
    if not items:
        return []

    first = items[0]

    if (
        "astra linux" in first["name"].lower()
        and (first.get("category_path") or "").lower()
            .startswith("операционные системы")
    ):
        return recommend_astra(conn, query, items)

    return recommend_complementary(
        conn, query, items
    )
