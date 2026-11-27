import os
import time
import logging

from threading import Lock
from typing import Literal

import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, Query, HTTPException

from app.embeddings import EmbeddingModel

app = FastAPI(
    title="SmartSearch AI",
    description="Intelligent search for Softline Store",
    version="0.2.0"
)

logger = logging.getLogger(__name__)

model = None
model_lock = Lock()


def get_connection():
    return psycopg.connect(
        host="db",
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        connect_timeout=5,
        options="-c statement_timeout=15000",
        row_factory=dict_row
    )


def encode_query(query):
    global model

    with model_lock:
        if model is None:
            model = EmbeddingModel()

        vector = model.encode(
            [query], prefix="query"
        )[0]

    return "[" + ",".join(
        str(float(x)) for x in vector
    ) + "]"


@app.get("/health")
def health():
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")

        return {
            "status": "ok",
            "database": "connected"
        }

    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable"
        )


def search(
    q: str = Query(min_length=1, max_length=250),
    limit: int = Query(default=8, ge=4, le=50),
    mode: Literal["lexical", "hybrid"] = "hybrid"
):
    q = q.strip()

    if not q:
        raise HTTPException(
            status_code=422,
            detail="Empty search query"
        )

    started = time.perf_counter()
    actual_mode = "lexical"
    fallback_reason = None
    vector = None

    try:
        with get_connection() as conn:
            status = conn.execute(
                """
                SELECT
                    normalize_query(%s) AS normalized,
                    (SELECT count(*) FROM search_products) AS total,
                    (SELECT count(*) FROM product_embeddings) AS indexed
                """,
                (q,)
            ).fetchone()

            normalized = status["normalized"]

            if mode == "hybrid":
                if status["total"] > 0 and (
                    status["indexed"] == status["total"]
                ):
                    try:
                        vector = encode_query(normalized)
                    except Exception:
                        logger.exception("Embedding failed")
                        fallback_reason = "model_unavailable"
                else:
                    fallback_reason = "indexing_in_progress"

            if vector is not None:
                rows = conn.execute(
                    """
                    SELECT *
                    FROM hybrid_search(%s, %s::vector, %s)
                    """,
                    (normalized, vector, limit)
                ).fetchall()

                actual_mode = "hybrid"

            else:
                rows = conn.execute(
                    "SELECT * FROM smart_search(%s, %s)",
                    (normalized, limit)
                ).fetchall()

    except psycopg.Error:
        logger.exception("Search failed")

        raise HTTPException(
            status_code=503,
            detail="Search unavailable"
        )

    return {
        "query": q,
        "normalized_query": normalized,
        "mode": actual_mode,
        "fallback_reason": fallback_reason,
        "indexed_products": status["indexed"],
        "index_total": status["total"],
        "total": len(rows),
        "duration_ms": round(
            (time.perf_counter() - started) * 1000, 2
        ),
        "items": rows
    }


from app.recommendations import recommend
from app.product_matching import refine_products
from app.task_search import select_task_products
from app.alternatives import find_alternatives
from app.unavailable import find_unavailable_office
from app.intent import detect_intent, filter_by_intent


@app.get("/api/agent")
def agent_search(
    q: str = Query(min_length=1, max_length=250),
    limit: int = Query(default=8, ge=4, le=50)
):
    started = time.perf_counter()
    intent = detect_intent(q)

    result = search(
        q=intent["rewritten_query"],
        limit=50 if intent["category"] else limit,
        mode="hybrid"
    )

    result["items"] = filter_by_intent(
        result["items"], intent
    )[:limit]

    result["total"] = len(result["items"])
    result["query"] = q
    result["intent"] = intent
    result["alternatives"] = []
    result["unavailable_alternatives"] = []


    try:
        with get_connection() as conn:
            refined = refine_products(
                conn, q, result["items"], limit
            )

            if refined is not None:
                result["items"] = refined
                result["total"] = len(refined)
                result["match_strategy"] = "catalog_family"
                result["intent"]["label"] = (
                    "Поиск конкретного семейства продуктов"
                )

            task_products = select_task_products(
                conn, intent, result["items"], limit
            )

            if task_products is not None:
                result["items"] = task_products
                result["total"] = len(task_products)
                result["match_strategy"] = "functional_category"

            result["alternatives"] = find_alternatives(
                conn, q, result["items"]
            )

            result["unavailable_alternatives"] = (
                find_unavailable_office(
                    conn,
                    q,
                    result["items"],
                    result["alternatives"]
                )
            )

            recommendations = recommend(
                conn,
                result["normalized_query"],
                result["items"]
            )

        result["recommendation_status"] = "ok"

    except psycopg.Error:
        logger.exception("Recommendations failed")
        recommendations = []
        result["recommendation_status"] = "unavailable"

    result["recommendations"] = recommendations

    result["agent"] = {
        "name": "SmartSearch AI",
        "strategy": "intent_search_and_recommend",
        "catalog_grounded": True,
        "embedding_model": "multilingual-e5-small"
    }

    result["duration_ms"] = round(
        (time.perf_counter() - started) * 1000, 2
    )
    save_metrics(result, "agent")
    return result


from pathlib import Path
from fastapi.responses import FileResponse


@app.get("/", include_in_schema=False)
def homepage():
    return FileResponse(
        Path(__file__).parent / "static" / "index.html"
    )


from app.analytics import record_event, get_metrics


def save_metrics(result, requested_mode):
    try:
        with get_connection() as conn:
            record_event(conn, result, requested_mode)
    except psycopg.Error:
        logger.exception("Analytics unavailable")


@app.get("/api/search")
def measured_search(
    q: str = Query(min_length=1, max_length=250),
    limit: int = Query(default=8, ge=4, le=50),
    mode: Literal["lexical", "hybrid"] = "hybrid"
):
    result = search(q=q, limit=limit, mode=mode)
    save_metrics(result, mode)
    return result


@app.get("/api/baseline")
def baseline(
    q: str = Query(min_length=1, max_length=250),
    limit: int = Query(default=8, ge=4, le=50)
):
    q = q.strip()

    if not q:
        raise HTTPException(
            status_code=422,
            detail="Empty search query"
        )

    started = time.perf_counter()

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM baseline_search(%s, %s)",
            (q, limit)
        ).fetchall()

    result = {
        "query": q,
        "normalized_query": q,
        "mode": "baseline",
        "total": len(rows),
        "duration_ms": round(
            (time.perf_counter() - started) * 1000, 2
        ),
        "items": rows
    }

    save_metrics(result, "baseline")
    return result


@app.get("/api/metrics")
def metrics():
    with get_connection() as conn:
        rows = get_metrics(conn)

    return {"metrics": rows}


from app.suggestions import get_suggestions


@app.get("/api/suggest")
def suggest(
    q: str = Query(min_length=2, max_length=80),
    limit: int = Query(default=8, ge=1, le=10)
):
    try:
        with get_connection() as conn:
            suggestions = get_suggestions(
                conn, q, limit
            )

        return {
            "query": q,
            "suggestions": suggestions
        }

    except psycopg.Error:
        logger.exception("Suggestion query failed")
        raise HTTPException(
            status_code=503,
            detail="Suggestions unavailable"
        )
