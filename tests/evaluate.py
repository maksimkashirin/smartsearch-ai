import json
import math
import re
import statistics
import urllib.request
import urllib.parse
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
LIMIT = 4

CUSTOMER = [
    ("astra linux", r"astra linux special edition"),
    ("Microsoft Office для дома и бизнеса",
     r"microsoft office для дома и бизнеса 2024"),
    ("kaspersky small office security",
     r"kaspersky small office security"),
    ("крипто про csp 5.0",
     r"^криптопро csp.*5[.]0"),
    ("anydesk", r"^anydesk"),
    ("кибер бэкап", r"киберпротект.*кибер бэкап"),
    ("сканер-вс", r"сканер[-– ]*вс"),
    ("мтс", r"мтс линк|webinar group"),
    ("max patrol", r"max\s*patrol.*endpoint protection"),
    ("365", r"microsoft 365.*(family|для семьи)")
]

FUNCTIONAL = [
    ("антивирь",
     r"category:.*антивирусы для"),
    ("сервер",
     r"^name:(?:(?:rack|tower|blade)[-– ]?)?сервер\s"),
    ("антивирус для сервера",
     r"name:.*(?:сервер|server).*category:.*антивирусы для"),
    ("редактор электронных таблиц",
     r"name:.*(?:microsoft office|microsoft 365|мойофис|р7-офис).*category:офисные программы"),
    ("сервис для онлайн-совещаний",
     r"name:.*(?:eclass|контур[. ]толк|мтс линк|trueconf)"),
    ("гарнитура для переговоров",
     r"name:.*гарнитур.*category:.*наушники и микрофоны"),
    ("удаленное управление ПК",
     r"category:программы для удаленного доступа"),
    ("программа для восстановления файлов на компьютере",
     r"name:.*(?:феникс|recuva|r-studio|disk drill)")
]

MODES = {
    "baseline": "/api/baseline",
    "lexical": "/api/search",
    "agent": "/api/agent"
}


def search(query, mode):
    params = {"q": query, "limit": LIMIT}

    if mode == "lexical":
        params["mode"] = "lexical"

    url = BASE_URL + MODES[mode] + "?"
    url += urllib.parse.urlencode(params)

    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def relevant(item, pattern, group):
    name = item["name"].lower()
    category = (item.get("category_path") or "").lower()

    if group == "customer":
        text = name
    else:
        text = "name:" + name + " category:" + category

    return bool(re.search(pattern, text, re.I))


def evaluate(query, pattern, mode, group):
    data = search(query, mode)
    items = data["items"]

    matches = [
        relevant(item, pattern, group)
        for item in items
    ]

    rank = next(
        (i + 1 for i, match in enumerate(matches) if match),
        None
    )

    return {
        "group": group,
        "query": query,
        "algorithm": mode,
        "actual_mode": data["mode"],
        "expected_pattern": pattern,
        "duration_ms": data["duration_ms"],
        "total": len(items),
        "first_relevant_rank": rank,
        "hit1": int(rank == 1),
        "hit4": int(rank is not None),
        "rr4": 1 / rank if rank else 0,
        "precision4": sum(matches) / LIMIT,
        "items": [
            {
                **item,
                "relevant_by_rule": match
            }
            for item, match in zip(items, matches)
        ]
    }


def summarize(rows):
    n = len(rows)
    times = sorted(r["duration_ms"] for r in rows)

    return {
        "queries": n,
        "hit1_percent": round(
            100 * statistics.mean(r["hit1"] for r in rows), 2
        ),
        "hit4_percent": round(
            100 * statistics.mean(r["hit4"] for r in rows), 2
        ),
        "mrr4": round(
            statistics.mean(r["rr4"] for r in rows), 4
        ),
        "precision4_percent": round(
            100 * statistics.mean(
                r["precision4"] for r in rows
            ), 2
        ),
        "zero_results_percent": round(
            100 * sum(r["total"] == 0 for r in rows) / n, 2
        ),
        "avg_duration_ms": round(
            statistics.mean(times), 2
        ),
        "p95_duration_ms": round(
            times[math.ceil(0.95 * n) - 1], 2
        )
    }


print("Warming up...", flush=True)

for mode in MODES:
    search("astra linux", mode)

results = []

for group, cases in [
    ("customer", CUSTOMER),
    ("functional", FUNCTIONAL)
]:
    for query, pattern in cases:
        for mode in MODES:
            row = evaluate(query, pattern, mode, group)
            results.append(row)

            print(
                group, "|", mode, "|", query,
                "| rank:", row["first_relevant_rank"],
                "| ms:", row["duration_ms"],
                flush=True
            )

summary = {}

for group in ("customer", "functional"):
    summary[group] = {}

    for mode in MODES:
        rows = [
            r for r in results
            if r["group"] == group
            and r["algorithm"] == mode
        ]

        summary[group][mode] = summarize(rows)

negative = {}

for mode in MODES:
    data = search("qzxv987654", mode)
    negative[mode] = data["total"]

output = {
    "evaluation_type": "rule_based_relevance",
    "limit": LIMIT,
    "summary": summary,
    "negative_query_results": negative,
    "details": results
}

Path("data/final_evaluation.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2)
)

print("\nFINAL EVALUATION")
print(json.dumps(summary, ensure_ascii=False, indent=2))

print("\nNEGATIVE QUERY")
print(json.dumps(negative, ensure_ascii=False, indent=2))

print("\nSaved: data/final_evaluation.json")
