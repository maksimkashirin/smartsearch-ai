def record_event(conn, result, requested_mode):
    conn.execute(
        """
        INSERT INTO search_events (
            requested_mode,
            actual_mode,
            intent,
            result_count,
            duration_ms
        )
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            requested_mode,
            result["mode"],
            result.get("intent", {}).get("type"),
            result["total"],
            result["duration_ms"]
        )
    )


def get_metrics(conn):
    return conn.execute(
        """
        SELECT
            requested_mode,
            actual_mode,
            count(*) AS requests,
            count(*) FILTER (
                WHERE result_count = 0
            ) AS zero_results,
            round(
                100.0 * count(*) FILTER (
                    WHERE result_count = 0
                ) / count(*), 2
            ) AS zero_results_percent,
            round(avg(result_count), 2) AS avg_results,
            round(avg(duration_ms)::numeric, 2)
                AS avg_duration_ms,
            round(
                (percentile_cont(0.95)
                WITHIN GROUP (
                    ORDER BY duration_ms
                ))::numeric, 2
            ) AS p95_duration_ms
        FROM search_events
        GROUP BY requested_mode, actual_mode
        ORDER BY requested_mode, actual_mode
        """
    ).fetchall()
