import re


def detect_task_intent(query):
    q = " ".join(query.lower().replace("ё", "е").split())

    hardware = re.search(
        r"гарнитур|наушник|микрофон|веб[- ]?камер|оборудован",
        q
    )

    if re.search(r"гарнитур|headset", q):
        kind = "headset"
        label = "Гарнитуры и оборудование для переговоров"

    elif re.search(
        r"видеоконференц|видеосовещан|видеозвон|вебинар|онлайн[- ]?встреч|онлайн[- ]?совещан",
        q
    ) and not hardware:
        kind = "video_conference"
        label = "Программы для видеоконференций"

    elif re.search(
        r"офисн\w*\s+(пакет|программ|редактор)|"
        r"аналог microsoft office|электронн\w*\s+таблиц|"
        r"редактор\w*\s+таблиц",
        q
    ):
        kind = "office_software"
        label = "Офисное программное обеспечение"

    elif (
        re.search(r"восстанов|recover", q)
        and re.search(r"файл|данн|data|file", q)
    ):
        kind = "data_recovery"
        label = "Восстановление файлов и данных"

    else:
        return None

    return {
        "type": kind,
        "label": label,
        "rewritten_query": query,
        "category": None
    }


TASK_RULES = {
    "headset": (
        r"наушники и микрофоны",
        r"гарнитур|headset",
        r"амбушюр|адаптер|запасн|коннектор"
    ),
    "video_conference": (
        r"^(программ|сеть и интернет|облачные|офисные|управление бизнесом)",
        r"trueconf|мтс линк|webinar|видеоконференц|вебинар|eclass|zoom|видеосвяз|контур[. ]толк",
        r"гарнитур|наушник|микрофон|веб.камер|коннектор"
    ),
    "office_software": (
        r"^офисные программы",
        r"microsoft office|microsoft 365|мой[ -]*офис|р7[- ]офис|onlyoffice|libreoffice|офисный пакет",
        r"антивирус|kaspersky|сквадус|squadus|mailion|мейлион|коннектор|техподдерж"
    ),
    "data_recovery": (
        r"программное обеспечение для восстановления данных",
        r"data recovery|file recovery|recover|восстановлен|r-studio|recuva|disk drill|ams software феникс",
        r"system repair|data eraser|удаление данных|стирание данных"
    )
}


def select_task_products(conn, intent, items, limit):
    kind = intent["type"]
    rule = TASK_RULES.get(kind)

    if not rule:
        return None

    category, include, exclude = rule

    existing = {
        item["id"]: item for item in items
    }

    q = intent["rewritten_query"].lower()

    desktop_recovery = (
        kind == "data_recovery"
        and bool(re.search(
            r"компьютер|ноутбук|windows|macos|\bпк\b", q
        ))
        and not bool(re.search(
            r"ios|android|iphone|ipad|телефон|смартфон", q
        ))
    )

    mobile_pattern = ""

    if kind == "data_recovery":
        if re.search(r"iphone|ipad|ios", q):
            mobile_pattern = "ios|iphone|ipad"
        elif "android" in q:
            mobile_pattern = "android"
        elif re.search(r"телефон|смартфон", q):
            mobile_pattern = "ios|android|iphone|ipad"

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
                p.normalized_name,
                CASE
                    WHEN %s THEN
                        CASE
                            WHEN p.normalized_name ~
                                '(модификатор|модул|вебинарных портов|дополнительн)'
                            THEN 2
                            WHEN p.category_path ~* 'ip-телефони'
                            THEN 1
                            ELSE 0
                        END
                    WHEN %s AND p.normalized_name ~
                        '(ios|android|iphone|ipad)'
                    THEN 1
                    ELSE 0
                END AS priority,
                coalesce(
                    array_position(%s::text[], p.id),
                    1000
                ) AS old_rank
            FROM search_products p
            WHERE p.category_path ~* %s
              AND p.normalized_name ~* %s
              AND p.normalized_name !~* %s
              AND NOT (
                  %s AND p.normalized_name ~
                      '(ios|android|iphone|ipad)'
              )
              AND (%s = '' OR p.normalized_name ~ %s)
              AND p.normalized_name !~
                  '(продлен|сертификат|дополнительн|cross.grade)'
            ORDER BY
                p.normalized_name,
                p.price IS NULL,
                p.id
        ),
        diversified AS (
            SELECT *,
                row_number() OVER (
                    PARTITION BY coalesce(
                        nullif(vendor, ''),
                        normalized_name
                    )
                    ORDER BY priority, old_rank, id
                ) AS vendor_rank
            FROM candidates
        )
        SELECT id, name, vendor, category_path, price, url
        FROM diversified
        ORDER BY
            priority,
            vendor_rank,
            old_rank,
            id
        LIMIT %s
        """,
        (
            kind == "video_conference",
            kind == "data_recovery",
            list(existing),
            category,
            include,
            exclude,
            desktop_recovery,
            mobile_pattern,
            mobile_pattern,
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
        item["match_source"] = "functional_category"

        if kind == "data_recovery" and re.search(
            r"ios|android|iphone|ipad",
            item["name"].lower()
        ):
            item["note"] = (
                "Средство восстановления данных мобильных "
                "устройств. Уточните поддерживаемую платформу."
            )

        result.append(item)

    return result
