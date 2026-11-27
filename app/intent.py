import re
from app.task_search import detect_task_intent


RULES = [
    (
        r"сервер|серверы|серверное оборудование|физический сервер",
        "server_hardware",
        "Серверное оборудование",
        "сервер",
        "Серверы и опции"
    ),
    (
        r"антивирус для сервера|антивирус для серверов|защита сервера от вирусов",
        "server_security",
        "Антивирусная защита серверов",
        "антивирус сервер",
        "Антивирусы и безопасность"
    ),
    (
        r"антивирь|антивир|антивирус|защита компьютеров от вирусов",
        "antivirus",
        "Антивирусное программное обеспечение",
        "антивирус",
        "Антивирусы и безопасность"
    ),
    (
        r"чем защитить компьютеры фирмы|антивирус для организации|антивирус для бизнеса",
        "business_security",
        "Защита компьютеров организации",
        "антивирус для организаций",
        "Антивирусы и безопасность"
    ),
    (
        r"удал[её]нное управление пк|удал[её]нный доступ|удал[её]нное управление компьютером",
        "remote_access",
        "Программы удаленного доступа",
        "удаленный доступ",
        "Программы для удаленного доступа"
    ),
    (
        r"б[эе]кап|б[эе]кап данных|резервное копирование",
        "backup",
        "Резервное копирование данных",
        "резервное копирование",
        "Программное обеспечение для работы с файлами и дисками"
    ),
    (
        r"офисный пакет|офисные программы|аналог microsoft office",
        "office_software",
        "Офисное программное обеспечение",
        "офисный пакет",
        "Офисные программы"
    )
]


def detect_intent(query):
    task = detect_task_intent(query)

    if task is not None:
        return task

    normalized = " ".join(query.lower().strip().split())

    for pattern, intent, label, rewritten, category in RULES:
        if re.fullmatch(pattern, normalized):
            return {
                "type": intent,
                "label": label,
                "rewritten_query": rewritten,
                "category": category
            }

    return {
        "type": "general",
        "label": "Общий поиск по каталогу",
        "rewritten_query": query,
        "category": None
    }


def filter_by_intent(items, intent):
    category = intent["category"]

    if not category:
        return items

    filtered = []

    for item in items:
        path = (item.get("category_path") or "").lower()
        name = (item.get("name") or "").lower()

        if path.split(" / ")[0] != category.lower():
            continue

        if intent["type"] == "server_hardware":
            if not re.match(
                r"^серверы и опции / [^/]*сервер", path
            ):
                continue

        if intent["type"] == "server_security":
            if not re.search(r"сервер|server", name + " " + path):
                continue

        if intent["type"] == "backup":
            if "резервн" not in path:
                continue

        if intent["type"] in (
            "antivirus",
            "server_security",
            "business_security"
        ):
            if "антивирус" not in " / ".join(path.split(" / ")[1:]):
                continue

        if intent["type"] == "business_security":
            if "для организаций" not in path:
                continue

        if intent["type"] == "remote_access":
            if re.search(r"opc\s*ua|эликонт", name):
                continue

        if intent["type"] == "server_hardware":
            if not re.match(
                r"^(?:(?:rack|tower|blade)[-– ]?)?сервер(?:\s|$)",
                name
            ):
                continue

        filtered.append(item)

    return filtered
