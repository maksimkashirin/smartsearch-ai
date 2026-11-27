CREATE TABLE IF NOT EXISTS categories (
    id TEXT PRIMARY KEY,
    parent_id TEXT,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    group_id TEXT,
    name TEXT NOT NULL,
    vendor TEXT,
    vendor_code TEXT,
    category_id TEXT,
    description TEXT,
    price NUMERIC(18, 2),
    old_price NUMERIC(18, 2),
    currency TEXT,
    available BOOLEAN NOT NULL,
    url TEXT,
    picture TEXT,
    vendor_url TEXT,
    sales_notes TEXT,
    attributes JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_products_category
    ON products(category_id);

CREATE INDEX IF NOT EXISTS idx_products_group
    ON products(group_id);

CREATE INDEX IF NOT EXISTS idx_products_available
    ON products(available);
