import os
from typing import Optional, List
import time

from fastapi import Body, FastAPI, UploadFile, File, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import models, crud, schemas
from .database import engine, get_db
from .tasks import import_products_task, redis_client
from app.routes import products_ui, webhooks_ui

# Create database tables (for simple demo; in production use migrations)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Product Importer")

# mount static folder (index.html + assets)
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.include_router(products_ui.router, prefix="/products_ui", tags=["Product UI"])
app.include_router(webhooks_ui.router, prefix="/webhooks_ui", tags=["Webhooks UI"])

@app.get("/", response_class=HTMLResponse)
def index():
    """
    Serve the static index.html page.
    """
    index_path = os.path.join(static_dir, "index.html")
    if not os.path.exists(index_path):
        return HTMLResponse("<html><body><h1>Index not found</h1></body></html>", status_code=404)
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    """
    Accept a CSV upload and start an asynchronous import task.
    Returns the Celery task id so the UI can subscribe to progress events.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    # Start the Celery task (file content is sent as bytes)
    task = import_products_task.delay(content)
    print(f"Task ID:",task.id)
    return {"task_id": task.id}


@app.get("/events/{task_id}")
def sse_events(task_id: str):
    """
    SSE endpoint that streams progress messages published to Redis for a given task.
    The tasks publish to channel: task:{task_id}
    """
    pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
    channel = f"task:{task_id}"
    pubsub.subscribe(channel)

    def event_stream():
        try:
            while True:
                message = pubsub.get_message(timeout=1)  # Non-blocking
                if message and message["type"] == "message":
                    yield f"data: {message['data'].decode('utf-8')}\n\n"
                time.sleep(0.1)
        finally:
            pubsub.unsubscribe(channel)
            pubsub.close()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# -----------------------
# Product CRUD endpoints
# -----------------------
@app.get("/products", response_model=list[schemas.ProductOut])
def list_products(
    skip: int = 0,
    limit: int = 10,
    sku: Optional[str] = None,
    name: Optional[str] = None,
    active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """
    List products with optional filtering and pagination.
    """
    filters = {}
    if sku:
        filters["sku"] = sku
    if name:
        filters["name"] = name
    if active is not None:
        filters["active"] = active
    items = crud.get_products(db, skip=skip, limit=limit, filters=filters)
    return items


@app.post("/products", response_model=schemas.ProductOut)
def create_product(p: schemas.ProductCreate, db: Session = Depends(get_db)):
    """
    Create or upsert a product (upsert uses case-insensitive SKU).
    """
    product = crud.upsert_product(
        db,
        sku=p.sku,
        name=p.name,
        description=p.description,
        active=p.active if p.active is not None else True,
    )
    return product


@app.patch("/products/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, p: schemas.ProductUpdate, db: Session = Depends(get_db)):
    """
    Partially update a product by ID.
    """
    prod = db.query(models.Product).filter(models.Product.id == product_id).one_or_none()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    for k, v in p.dict(exclude_unset=True).items():
        setattr(prod, k, v)
    db.add(prod)
    db.commit()
    db.refresh(prod)
    return prod


@app.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """
    Delete a single product by ID.
    """
    prod = db.query(models.Product).filter(models.Product.id == product_id).one_or_none()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(prod)
    db.commit()
    return {"status": "deleted"}


@app.post("/products/bulk_delete")
def bulk_delete(confirm: bool = Query(False), db: Session = Depends(get_db)):
    """
    Delete all products. Must be called with confirm=true to proceed.
    """
    if not confirm:
        raise HTTPException(status_code=400, detail="Please confirm by sending confirm=true")
    deleted_count = crud.delete_all_products(db)
    return {"deleted": deleted_count}


@app.get("/webhooks", response_model=List[schemas.WebhookOut])
def list_webhooks(
    skip: int = 0,
    limit: int = 10,
    active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    List webhooks with optional active filter and pagination.
    """
    query = db.query(models.Webhook)
    if active is not None:
        query = query.filter(models.Webhook.enabled == active)
    return query.order_by(models.Webhook.id.desc()).offset(skip).limit(limit).all()


@app.post("/webhooks", response_model=schemas.WebhookOut)
def create_webhook(w: schemas.WebhookCreate, db: Session = Depends(get_db)):
    """
    Create a new webhook.
    """
    return crud.create_webhook(db, w)


@app.patch("/webhooks/{id}", response_model=schemas.WebhookOut)
def update_webhook(id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    """
    Partially update an existing webhook.
    Accepts any subset of fields: url, event, enabled
    """
    webhook = crud.get_webhook(db, id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    for k, v in payload.items():
        if k in ['url', 'event', 'enabled']:
            setattr(webhook, k, v)

    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook


@app.delete("/webhooks/{id}")
def delete_webhook(id: int, db: Session = Depends(get_db)):
    """
    Delete a webhook by ID.
    """
    webhook = crud.get_webhook(db, id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    db.delete(webhook)
    db.commit()
    return {"status": "deleted"}


@app.post("/webhooks/{id}/test")
def test_webhook(id: int, db: Session = Depends(get_db)):
    """
    Trigger a test delivery to the webhook asynchronously.
    Returns a Celery task ID.
    """
    webhook = crud.get_webhook(db, id)
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    payload = {"event": webhook.event, "test": True}
    task = import_products_task.app.send_task("app.tasks.deliver_webhook", args=(webhook.url, payload))
    return {"task_id": task.id, "status": "Test triggered"}