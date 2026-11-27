import os
import time

import psycopg

from app.embeddings import EmbeddingModel

BATCH_SIZE = 64
MODEL_BATCH_SIZE = 8

model = EmbeddingModel()
started = time.perf_counter()

with psycopg.connect(
    host="db",
    dbname=os.environ["POSTGRES_DB"],
    user=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"]
) as conn:

    total = conn.execute(
        "SELECT count(*) FROM search_products"
    ).fetchone()[0]

    done = conn.execute(
        "SELECT count(*) FROM product_embeddings"
    ).fetchone()[0]

    print(f"Starting: {done}/{total}", flush=True)

    last_id = ""

    while True:
        rows = conn.execute(
            """
            SELECT
                p.id,
                concat_ws(
                    ' ',
                    p.name,
                    c.name,
                    p.vendor,
                    p.category_path
                )
            FROM search_products p
            LEFT JOIN categories c ON c.id = p.group_id
            WHERE p.id > %s
              AND NOT EXISTS (
                  SELECT 1
                  FROM product_embeddings e
                  WHERE e.product_id = p.id
              )
            ORDER BY p.id
            LIMIT %s
            """,
            (last_id, BATCH_SIZE)
        ).fetchall()

        if not rows:
            break

        values = []

        for i in range(0, len(rows), MODEL_BATCH_SIZE):
            batch = rows[i:i + MODEL_BATCH_SIZE]

            vectors = model.encode(
                [row[1] for row in batch]
            )

            for row, vector in zip(batch, vectors):
                vector_text = "[" + ",".join(
                    str(float(x)) for x in vector
                ) + "]"

                values.append(
                    (row[0], vector_text)
                )

        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO product_embeddings
                    (product_id, embedding)
                VALUES (%s, %s::vector)
                ON CONFLICT (product_id) DO NOTHING
                """,
                values
            )

        conn.commit()

        done += len(rows)
        last_id = rows[-1][0]

        elapsed = time.perf_counter() - started

        print(
            f"Indexed: {done}/{total} "
            f"({done / total * 100:.2f}%) "
            f"Elapsed: {elapsed:.1f}s",
            flush=True
        )

    print("Indexing completed.", flush=True)
