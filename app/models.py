from datetime import datetime, timezone
from typing import Optional, List, Union
from enum import Enum

from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic.functional_validators import BeforeValidator
from typing_extensions import Annotated

# Custom type for MongoDB ObjectId
PyObjectId = Annotated[str, BeforeValidator(str)]

def utcnow() -> datetime:
    """Get current UTC datetime with timezone info."""
    return datetime.now(timezone.utc)

def next_reminder_offsets() -> list[int]:
    """Return the default reminder offsets in days before payment is due.
    
    Returns:
        list[int]: List of days before payment when reminders should be sent.
    """
    return [7, 3, 1]  # 1 week, 3 days, and 1 day before payment

class Subscription(BaseModel):
    """Subscription model representing a recurring payment."""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    service: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0, description="Subscription amount in the specified currency")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    period_days: int = Field(..., gt=0, description="Billing period in days (e.g., 30 for monthly)")
    next_payment: datetime = Field(..., description="Next payment due date and time")
    created_at: datetime = Field(default_factory=utcnow)
    
    # Optional fields
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional description or notes about the subscription"
    )
    
    # Pydantic configuration
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "service": "Netflix",
                "amount": 15.99,
                "currency": "USD",
                "period_days": 30,
                "next_payment": "2023-12-31T23:59:59Z",
                "description": "Premium Plan"
            }
        }
    )
    
    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code is uppercase."""
        return v.upper()
    
    @field_validator('next_payment')
    @classmethod
    def validate_next_payment(cls, v: datetime) -> datetime:
        """Ensure next_payment is timezone-aware."""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

class User(BaseModel):
    """User model for the subscription tracking system."""
    tg_id: int = Field(..., description="Telegram user ID")
    username: Optional[str] = Field(
        default=None,
        max_length=32,
        description="Telegram username (without @)"
    )
    tz: str = Field(
        default="UTC",
        description="IANA timezone name (e.g., 'America/New_York', 'Europe/London')"
    )
    subs: List[Subscription] = Field(
        default_factory=list,
        description="List of user's subscriptions"
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        description="When the user was first registered"
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        description="When the user was last updated"
    )
    
    # Pydantic configuration
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "tg_id": 123456789,
                "username": "johndoe",
                "tz": "Asia/Jerusalem",
                "subs": []
            }
        }
    )
    
    def add_subscription(self, subscription: Subscription) -> None:
        """Add a new subscription to the user."""
        self.subs.append(subscription)
        self.updated_at = utcnow()
    
    def remove_subscription(self, subscription_id: str) -> bool:
        """Remove a subscription by ID."""
        initial_length = len(self.subs)
        self.subs = [sub for sub in self.subs if str(sub.id) != subscription_id]
        if len(self.subs) < initial_length:
            self.updated_at = utcnow()
            return True
        return False
    
    def get_upcoming_subscriptions(self, days: int = 30) -> List[Subscription]:
        """Get subscriptions with payments due in the next 'days' days."""
        now = utcnow()
        cutoff = now + datetime.timedelta(days=days)
        return [
            sub for sub in self.subs 
            if now <= sub.next_payment <= cutoff
        ]
