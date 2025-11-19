import csv
import io
import os
import tempfile
from .celery_app import celery
import redis
import httpx
import json
from .database import engine

REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
redis_client = redis.from_url(REDIS_URL)

@celery.task(bind=True)
def import_products_task(self, file_bytes, default_active=True):
    """
    Efficiently import large CSV into PostgreSQL using COPY, skipping duplicates.
    Publishes progress to Redis for SSE.
    """
    channel = f"task:{self.request.id}"

    def publish(progress, status):
        redis_client.publish(channel, json.dumps({"progress": progress, "status": status}))

    publish(0, "Upload received. Preparing CSV...")

    # Decode CSV
    csv_file = io.StringIO(file_bytes.decode('utf-8', errors='replace'))
    reader = csv.DictReader(csv_file)
    rows = list(reader)
    total = len(rows)
    if total == 0:
        publish(100, "No rows found in CSV")
        return {"imported": 0}

    publish(5, f"CSV loaded: {total} rows")

    # Create temporary CSV for COPY
    temp_file_path = f"/tmp/import_{self.request.id}.csv"
    with open(temp_file_path, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["sku", "name", "description", "active"])
        for row in rows:
            sku = (row.get('sku') or row.get('SKU') or '').strip().lower()
            name = row.get('name') or sku
            description = row.get('description') or ''
            if not sku:
                continue
            writer.writerow([sku, name, description, str(default_active)])

    # Bulk insert with ON CONFLICT DO NOTHING
    try:
        conn = engine.raw_connection()
        cur = conn.cursor()

        # Step 1: Create a temporary staging table
        cur.execute("""
            CREATE TEMP TABLE tmp_products (
                sku TEXT,
                name TEXT,
                description TEXT,
                active BOOLEAN
            ) ON COMMIT DROP;
        """)

        # Step 2: COPY into temp table
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            cur.copy_expert(
                sql="COPY tmp_products (sku, name, description, active) FROM STDIN WITH CSV HEADER",
                file=f
            )

        # Step 3: Insert into real table, skip duplicates
        cur.execute("""
            INSERT INTO products (sku, name, description, active)
            SELECT sku, name, description, active FROM tmp_products
            ON CONFLICT (sku) DO NOTHING;
        """)

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        publish(100, f"Error during import: {e}")
        raise e

    publish(100, f"Import complete: {total} rows processed (duplicates skipped)")
    return {"processed": total}

@celery.task
def deliver_webhook(url, payload):
    try:
        with httpx.Client(timeout=10) as client:
            r = client.post(url, json=payload)
            return {'status_code': r.status_code, 'text': r.text[:1000]}
    except Exception as e:
        return {'error': str(e)}