RULES = {
    "microsoft office для дома и бизнеса": (
        r"мойофис|р7[- ]офис|onlyoffice|libreoffice",
        r"^офисные программы",
        "Альтернативный офисный пакет"
    ),
    "365": (
        r"мойофис|р7[- ]офис|onlyoffice|libreoffice",
        r"^офисные программы",
        "Альтернативное решение для работы с документами"
    ),
    "мтс": (
        r"trueconf|видеоконференц|вебинар|eclass",
        r"^(программ|сеть и интернет|облачные|офисные)",
        "Альтернативная платформа видеоконференций"
    ),
    "max patrol": (
        r"kaspersky endpoint security|dr.web.*enterprise",
        r"^антивирусы и безопасность",
        "Альтернативное средство защиты конечных устройств"
    )
}


def find_alternatives(conn, query, items):
    if len(items) >= 4:
        return []

    q = " ".join(query.lower().strip().split())
    rule = RULES.get(q)

    if not rule:
        return []

    pattern, category, purpose = rule

    rows = conn.execute(
        """
        WITH candidates AS (
            SELECT DISTINCT ON (
                coalesce(nullif(p.group_id, ''), p.normalized_name)
            )
                p.id,
                p.name,
                p.vendor,
                p.price,
                p.url,
                p.category_path,
                p.normalized_name
            FROM search_products p
            WHERE p.normalized_name ~ %s
              AND lower(p.category_path) ~ %s
              AND NOT (p.id = ANY(%s::text[]))
              AND p.normalized_name !~
                  '(продлен|обновлен|сертификат|дополнительн)'
            ORDER BY
                coalesce(nullif(p.group_id, ''), p.normalized_name),
                p.price IS NULL,
                p.id
        )
        SELECT id, name, vendor, price, url, category_path
        FROM candidates
        ORDER BY id
        LIMIT %s
        """,
        (
            pattern,
            category,
            [item["id"] for item in items],
            4 - len(items)
        )
    ).fetchall()

    result = []

    for row in rows:
        item = dict(row)
        item["purpose"] = purpose
        item["note"] = (
            "Альтернативный продукт из каталога. "
            "Проверьте функциональность и условия лицензии."
        )
        result.append(item)

    return result
