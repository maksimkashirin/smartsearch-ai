import json
import statistics
import urllib.request
import urllib.parse
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

QUERIES = [
    "astra linux",
    "Microsoft Office для дома и бизнеса",
    "kaspersky small office security",
    "крипто про csp 5.0",
    "anydesk",
    "кибер бэкап",
    "сканер-вс",
    "мтс",
    "max patrol",
    "365"
]

MODES = {
    "baseline": "/api/baseline",
    "lexical": "/api/search",
    "agent": "/api/agent"
}


def run_search(query, mode):
    params = {
        "q": query,
        "limit": 10
    }

    if mode == "lexical":
        params["mode"] = "lexical"

    url = (
        BASE_URL + MODES[mode] + "?"
        + urllib.parse.urlencode(params)
    )

    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


results = []

# Warm up all algorithms before measurements.
for mode in MODES:
    run_search("astra linux", mode)

for query in QUERIES:
    print("\n" + "=" * 70, flush=True)
    print("QUERY:", query, flush=True)

    for mode in MODES:
        try:
            data = run_search(query, mode)

            results.append({
                "query": query,
                "algorithm": mode,
                "actual_mode": data["mode"],
                "duration_ms": data["duration_ms"],
                "total": data["total"],
                "items": data["items"]
            })

            print(
                mode,
                "| Products:", data["total"],
                "| Time:", data["duration_ms"], "ms",
                flush=True
            )

            for item in data["items"][:3]:
                print("-", item["name"], flush=True)

        except Exception as error:
            print("ERROR:", mode, error, flush=True)
            results.append({
                "query": query,
                "algorithm": mode,
                "error": str(error)
            })

output = Path("data/benchmark_results.json")
output.parent.mkdir(exist_ok=True)

output.write_text(
    json.dumps(results, ensure_ascii=False, indent=2)
)

print("\n" + "=" * 70)
print("SUMMARY")

for mode in MODES:
    rows = [
        r for r in results
        if r["algorithm"] == mode and "error" not in r
    ]

    if not rows:
        continue

    print("\nAlgorithm:", mode)
    print("Successful requests:", len(rows), "/ 10")
    print("Zero results:", sum(r["total"] == 0 for r in rows))
    print("Average time:",
          round(statistics.mean(
              r["duration_ms"] for r in rows
          ), 2), "ms")
    print("Average products:",
          round(statistics.mean(
              r["total"] for r in rows
          ), 2))

print("\nSaved:", output)
