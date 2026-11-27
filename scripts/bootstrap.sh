#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
    echo "Create .env from .env.example first."
    exit 1
fi

if grep -q '^POSTGRES_PASSWORD=CHANGE_ME$' .env; then
    echo "Set a secure database password first."
    exit 1
fi

if [ ! -s data/Mindbox.yml.gz.xml ]; then
    echo "Missing data/Mindbox.yml.gz.xml"
    exit 1
fi

db() {
    docker compose exec -T db sh -c \
        'exec psql -v ON_ERROR_STOP=1 \
        -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$@"' \
        psql "$@"
}

echo "[1/7] Starting PostgreSQL"
docker compose up -d --wait db

db < database/init.sql
db < database/schema.sql

existing=$(db -Atc \
    "SELECT (SELECT count(*) FROM products) +
            (SELECT count(*) FROM categories);")

if [ "$existing" != "0" ]; then
    echo "Database already contains data."
    echo "Bootstrap is intended for a fresh database."
    exit 1
fi

echo "[2/7] Processing catalog"
python3 scripts/import_catalog.py

echo "[3/7] Importing catalog"

db -c "\copy categories FROM STDIN WITH (FORMAT csv)" \
    < data/categories.csv

db -c "\copy products FROM STDIN WITH (FORMAT csv)" \
    < data/products.csv

db -c "ANALYZE categories; ANALYZE products;"

echo "[4/7] Building search indexes"

for file in \
    search \
    normalize \
    search_function \
    embeddings \
    hybrid_search \
    baseline \
    analytics
do
    db < "database/$file.sql"
done

echo "[5/7] Downloading embedding model"

mkdir -p models/e5-small

MODEL_URL="https://huggingface.co/Xenova/multilingual-e5-small/resolve/main"

curl -fL --retry 3 \
    "$MODEL_URL/tokenizer.json" \
    -o models/e5-small/tokenizer.json

curl -fL --retry 3 \
    "$MODEL_URL/onnx/model_quantized.onnx" \
    -o models/e5-small/model_quantized.onnx

echo "f80102d3f2a1229f387d3c81909990d8945513e347b0eab049f7de3c6f98c193  models/e5-small/model_quantized.onnx" \
    | sha256sum -c -

chmod a+r models/e5-small/*

echo "[6/7] Building API and indexing products"

docker compose build api

docker compose run --rm --no-deps api \
    python -m app.index_embeddings

echo "[7/7] Starting application"

docker compose up -d --wait api
docker compose ps

curl -fsS http://127.0.0.1:8000/health

echo
echo "SmartSearch AI is ready."
echo "Open http://127.0.0.1:8000/"
