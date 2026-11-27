def find_unavailable_office(
    conn, query, items, alternatives
):
    q = " ".join(query.lower().strip().split())

    is_office = (
        q == "365"
        or q.startswith("microsoft office")
        or q.startswith("microsoft 365")
        or q.startswith("офисный пакет")
        or q.startswith("офисные программы")
    )

    remaining = 4 - len(items) - len(alternatives)

    if not is_office or remaining <= 0:
        return []

    rows = conn.execute(
        """
        WITH candidates AS (
            SELECT DISTINCT ON (p.vendor)
                p.id,
                p.name,
                p.vendor,
                p.url,
                c.name AS category_path
            FROM products p
            JOIN categories c ON c.id = p.category_id
            WHERE p.available = FALSE
              AND p.vendor IN ('АО «Р7»', 'МойОфис')
              AND c.name ~* 'офис'
              AND (
                  (
                      p.vendor = 'МойОфис'
                      AND lower(p.name) ~
                          '(стандартный|профессиональный|для дома|документы настольные|настольный офис|редакторы360)'
                  )
                  OR
                  (
                      p.vendor = 'АО «Р7»'
                      AND lower(p.name) ~
                          '(р7[-– ]*офис|р7» для бизнеса)'
                  )
              )
              AND lower(p.name) !~
                  '(сквадус|squadus|мейлион|mailion|почта|коннектор|серверная|серверный)'
              AND p.url LIKE 'https://%%'
              AND lower(p.name) !~
                  '(образоват|учебн|академ|школ|вуз|продлен|обновлен|расширен|дополнительн|сертификат|техподдерж)'
            ORDER BY
                p.vendor,
                CASE
                    WHEN lower(p.name) ~
                        '(для бизнеса|коммерческ)'
                    THEN 0
                    ELSE 1
                END,
                length(p.name),
                p.id
        )
        SELECT *
        FROM candidates
        ORDER BY vendor
        LIMIT %s
        """,
        (remaining,)
    ).fetchall()

    result = []

    for row in rows:
        item = dict(row)
        item["available"] = False
        item["price"] = None
        item["purpose"] = "Возможная альтернатива"
        item["note"] = (
            "Недоступен по данным исходного каталога. "
            "Актуальная цена и возможность покупки "
            "не подтверждены. Проверьте состав лицензии."
        )
        result.append(item)

    return result
