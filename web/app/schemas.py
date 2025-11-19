from pydantic import BaseModel, AnyUrl
from typing import Optional


class ProductBase(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    active: Optional[bool] = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    active: Optional[bool]


class ProductOut(ProductBase):
    id: int
    class Config:
        orm_mode = True


class WebhookCreate(BaseModel):
    url: AnyUrl
    event: str
    enabled: Optional[bool] = True


class WebhookOut(WebhookCreate):
    id: int
    class Config:
        orm_mode = True