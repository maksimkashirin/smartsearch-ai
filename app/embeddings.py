import os
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer


class EmbeddingModel:
    def __init__(self):
        path = Path("/models/e5-small")

        self.tokenizer = Tokenizer.from_file(
            str(path / "tokenizer.json")
        )

        self.tokenizer.enable_truncation(max_length=128)
        self.tokenizer.enable_padding(
            pad_id=self.tokenizer.token_to_id("<pad>"),
            pad_token="<pad>"
        )

        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1

        self.session = ort.InferenceSession(
            str(path / "model_quantized.onnx"),
            sess_options=options,
            providers=["CPUExecutionProvider"]
        )

    def encode(self, texts, prefix="passage"):
        encoded = self.tokenizer.encode_batch([
            f"{prefix}: {text}" for text in texts
        ])

        ids = np.array(
            [x.ids for x in encoded],
            dtype=np.int64
        )

        mask = np.array(
            [x.attention_mask for x in encoded],
            dtype=np.int64
        )

        inputs = {
            "input_ids": ids,
            "attention_mask": mask,
            "token_type_ids": np.zeros_like(ids)
        }

        feed = {
            item.name: inputs[item.name]
            for item in self.session.get_inputs()
        }

        hidden = self.session.run(None, feed)[0]

        expanded_mask = mask[..., None]
        pooled = (
            hidden * expanded_mask
        ).sum(axis=1) / expanded_mask.sum(axis=1)

        norms = np.linalg.norm(
            pooled, axis=1, keepdims=True
        )

        return (
            pooled / np.maximum(norms, 1e-12)
        ).astype(np.float32)


if __name__ == "__main__":
    started = time.perf_counter()
    model = EmbeddingModel()

    print("Model loaded:", round(
        time.perf_counter() - started, 3
    ), "sec")

    documents = [
        "Антивирус для защиты компьютеров организации",
        "Серверное оборудование для центра обработки данных",
        "Офисный пакет для работы с документами"
    ]

    vectors = model.encode(documents)

    query = model.encode(
        ["защита компьютера от вирусов"],
        prefix="query"
    )[0]

    print("Embedding shape:", vectors.shape)

    for document, vector in zip(documents, vectors):
        print(round(float(query @ vector), 4), document)

    import psycopg

    with psycopg.connect(
        host="db",
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"]
    ) as conn:
        rows = conn.execute(
            """
            SELECT concat_ws(' ', name, category_path)
            FROM search_products
            ORDER BY id
            LIMIT 32
            """
        ).fetchall()

    texts = [row[0] for row in rows]

    started = time.perf_counter()

    for i in range(0, len(texts), 8):
        model.encode(texts[i:i + 8])

    elapsed = time.perf_counter() - started

    print("Catalog benchmark:", len(texts), "products")
    print("Elapsed:", round(elapsed, 3), "sec")
    print("Products/sec:", round(len(texts) / elapsed, 2))
    print("Semantic model test completed.")
