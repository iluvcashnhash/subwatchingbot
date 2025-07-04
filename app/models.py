from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class SubscriptionFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class SubscriptionBase(BaseModel):
    name: str
    amount: float
    currency: str
    frequency: SubscriptionFrequency
    next_billing_date: datetime
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    notes: Optional[str] = None
    category: Optional[str] = None

class SubscriptionCreate(SubscriptionBase):
    pass

class Subscription(SubscriptionBase):
    id: str = Field(..., alias="_id")
    user_id: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        from_attributes = True

class UserBase(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = "en"
    is_admin: bool = False

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    subscriptions: List[Subscription] = []

    class Config:
        populate_by_name = True
        from_attributes = True
