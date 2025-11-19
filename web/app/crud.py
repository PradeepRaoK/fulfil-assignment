from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models, schemas


# Upsert by case-insensitive SKU
def upsert_product(db: Session, sku: str, name: str, description: str = None, active: bool = True):
    sku_norm = sku.strip().lower()
    existing = db.query(models.Product).filter(func.lower(models.Product.sku) == sku_norm).one_or_none()
    if existing:
        existing.sku = sku
        existing.name = name
        existing.description = description
        existing.active = active
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        p = models.Product(sku=sku, name=name, description=description, active=active)
        db.add(p)
        db.commit()
        db.refresh(p)
        return p


def get_products(db: Session, skip: int = 0, limit: int = 10, filters: dict = None):
    q = db.query(models.Product)
    if filters:
        if 'sku' in filters:
            q = q.filter(models.Product.sku.ilike(f"%{filters['sku']}%"))
        if 'name' in filters:
            q = q.filter(models.Product.name.ilike(f"%{filters['name']}%"))
        if 'description' in filters:
            q = q.filter(models.Product.description.ilike(f"%{filters['description']}%"))
        if 'active' in filters:
            q = q.filter(models.Product.active == filters['active'])
    return q.order_by(models.Product.id.desc()).offset(skip).limit(limit).all()


def delete_all_products(db: Session):
    n = db.query(models.Product).delete()
    db.commit()
    return n


# CRUD for webhooks
def create_webhook(db: Session, webhook: schemas.WebhookCreate):
    w = models.Webhook(url=str(webhook.url), event=webhook.event, enabled=webhook.enabled if webhook.enabled is not None else True)
    db.add(w)
    db.commit()
    db.refresh(w)
    return w


def list_webhooks(db: Session):
    return db.query(models.Webhook).order_by(models.Webhook.id.desc()).all()


def get_webhook(db: Session, id: int):
    return db.query(models.Webhook).filter(models.Webhook.id == id).one_or_none()

def update_webhook(db: Session, id: int, fields: dict):
    """
    fields: dictionary of attributes to update, e.g. {'url': 'new', 'enabled': False}
    """
    w = get_webhook(db, id)
    if not w:
        return None
    for k, v in fields.items():
        if hasattr(w, k):
            setattr(w, k, v)
    db.add(w)
    db.commit()
    db.refresh(w)
    return w


def delete_webhook(db: Session, id: int):
    w = get_webhook(db, id)
    if w:
        db.delete(w)
        db.commit()
    return w