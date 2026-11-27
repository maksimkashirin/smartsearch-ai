CREATE TABLE IF NOT EXISTS product_embeddings (
    product_id TEXT PRIMARY KEY,
    embedding vector(384) NOT NULL
);
