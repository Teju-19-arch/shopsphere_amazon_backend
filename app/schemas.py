from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, Any

class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    phone: Optional[str] = None

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class AddressIn(BaseModel):
    full_name: str
    phone: str
    line1: str
    line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = 'India'
    is_default: bool = False

class CategoryIn(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None

class SellerIn(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None

class ProductIn(BaseModel):
    name: str
    description: str = ''
    category_id: int
    seller_id: int
    price: float = Field(gt=0)
    mrp: Optional[float] = None
    sku: str
    brand: Optional[str] = None
    image_url: Optional[str] = None
    stock: int = Field(default=0, ge=0)
    active: bool = True
    metadata: dict[str, Any] = {}

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0)
    mrp: Optional[float] = Field(default=None, gt=0)
    stock: Optional[int] = Field(default=None, ge=0)
    active: Optional[bool] = None
    metadata: Optional[dict[str, Any]] = None

class CartItemIn(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=100)

class CouponIn(BaseModel):
    code: str
    discount_percent: float = Field(gt=0, le=100)
    min_order_value: float = Field(default=0, ge=0)
    max_uses: int = Field(default=100, ge=1)
    active: bool = True

class CheckoutIn(BaseModel):
    address_id: int
    coupon_code: Optional[str] = None
    payment_method: str = 'COD'

class PaymentIn(BaseModel):
    order_id: int
    method: str = 'UPI'

class ShipmentStatusIn(BaseModel):
    status: str
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None

class ReviewIn(BaseModel):
    product_id: int
    rating: int = Field(ge=1, le=5)
    title: str = ''
    comment: str = ''

class RecommendationIn(BaseModel):
    product_ids: list[int]
    reason: str = 'personalized'

class WishlistIn(BaseModel):
    product_id: int
