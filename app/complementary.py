import re

BACKUP_SOURCE = (
    "https://cyberprotect.ru/buy-backup/"
)

RULES = {
    "server_backup": (
        r"киберпротект.*кибер бэкап.*для физического сервера",
        r"резервного копирования",
        "Резервное копирование физического сервера",
        BACKUP_SOURCE
    ),
    "workstation_backup": (
        r"киберпротект.*кибер бэкап.*для рабочей станции windows",
        r"резервного копирования",
        "Резервное копирование рабочей станции Windows",
        BACKUP_SOURCE
    ),
    "server_os": (
        r"^astra linux special edition.*[xх]86.*серверн",
        r"^операционные системы",
        "Операционная система для сервера x86-64",
        "https://astra.ru/software-services/os/"
    ),
    "home_security": (
        r"^kaspersky standard",
        r"антивирусы для дома",
        "Антивирусная защита домашнего компьютера",
        "https://www.kaspersky.ru/standard"
    ),
    "business_security": (
        r"^kaspersky small office security",
        r"антивирусы для организаций",
        "Защита компьютеров малого бизнеса",
        "https://www.kaspersky.ru/small-business-security/small-office-security"
    ),
    "logitech_headset": (
        r"гарнитура.*logitech zone wired",
        r"наушники и микрофоны",
        "Гарнитура для переговоров",
        "https://www.logitech.com/en-us/products/headsets/zone-wired-noise-canceling.html"
    ),
    "yealink_headset": (
        r"гарнитура.*yealink uh35",
        r"наушники и микрофоны",
        "Другой вариант гарнитуры для переговоров",
        "https://www.yealink.com/en/product-tech-specs/headset-uh35"
    )
}


def select_rules(query, items):
    if not items:
        return []

    q = query.lower().replace("ё", "е")
    first = items[0]

    name = first["name"].lower()
    path = (first.get("category_path") or "").lower()

    if path.startswith("серверы и опции"):
        if re.search(r"сервер", name):
            return ["server_os", "server_backup"]

    if path.startswith("офисные программы"):
        if re.search(r"бизнес|организац|коммерческ", q + " " + name):
            return ["business_security", "workstation_backup"]

        return ["home_security"]

    if "антивирусы для организаций" in path:
        if re.search(r"сервер|server", q):
            return ["server_backup"]

        return ["workstation_backup"]

    if path.startswith("программы для удаленного доступа"):
        return ["workstation_backup"]

    if re.search(
        r"видеоконференц|видеосовещан|вебинар|"
        r"онлайн[- ]?совещан|мтс линк|webinar|eclass",
        q + " " + name
    ):
        if not re.search(
            r"гарнитур|наушник|микрофон|камер",
            q
        ) and path.startswith(
            ("программ", "сеть и интернет", "офисные")
        ):
            return ["logitech_headset", "yealink_headset"]

    return []


def recommend_complementary(conn, query, items):
    excluded = [item["id"] for item in items]
    recommendations = []

    for key in select_rules(query, items):
        pattern, category, purpose, source = RULES[key]

        row = conn.execute(
            """
            SELECT id, name, vendor, price, url, category_path
            FROM search_products
            WHERE normalized_name ~* %s
              AND category_path ~* %s
              AND NOT (id = ANY(%s::text[]))
              AND normalized_name !~
                  '(продлен|обновлен|сертификат|техподдерж|дополнительн|cross.grade)'
            ORDER BY
                price IS NULL,
                length(name),
                id
            LIMIT 1
            """,
            (pattern, category, excluded)
        ).fetchone()

        if row:
            item = dict(row)
            item["purpose"] = purpose
            item["source"] = source
            item["source_type"] = "vendor_family"
            item["note"] = (
                "Сопутствующее решение по назначению. "
                "Перед покупкой уточните совместимость, "
                "операционную систему и условия лицензии."
            )

            recommendations.append(item)
            excluded.append(item["id"])

    return recommendations
