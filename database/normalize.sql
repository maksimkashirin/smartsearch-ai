CREATE OR REPLACE FUNCTION normalize_query(q TEXT)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    q := replace(lower(trim(coalesce(q, ''))), 'ё', 'е');

    q := regexp_replace(q, '\mантивирь\M', 'антивирус', 'g');
    q := regexp_replace(q, '\mантивир\M', 'антивирус', 'g');
    q := regexp_replace(q, '\mвинда\M', 'windows', 'g');
    q := regexp_replace(q, '\mвинду\M', 'windows', 'g');
    q := regexp_replace(q, '\mбэкапы?\M', 'резервное копирование', 'g');
    q := regexp_replace(q, '\mбекапы?\M', 'резервное копирование', 'g');
    q := regexp_replace(q, '\mпдф\M', 'pdf', 'g');
    q := regexp_replace(q, '\s+', ' ', 'g');

    RETURN trim(q);
END;
$$;
