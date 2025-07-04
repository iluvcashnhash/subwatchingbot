"""Tests for SubWatch Bot models."""
import pytest
from datetime import datetime, timedelta
from app.models import Subscription, User, next_reminder_offsets

class TestSubscriptionModel:
    """Test Subscription model functionality."""
    
    def test_subscription_creation(self):
        """Test creating a subscription with required fields."""
        sub = Subscription(
            user_id=12345,
            service="Netflix",
            amount=9.99,
            currency="USD",
            period_days=30,
            start_date=datetime(2023, 1, 1),
            next_payment=datetime(2023, 2, 1)
        )
        assert sub.user_id == 12345
        assert sub.service == "Netflix"
        assert sub.amount == 9.99
        assert sub.currency == "USD"
        assert sub.period_days == 30
        assert sub.next_payment == datetime(2023, 2, 1)
    
    def test_subscription_defaults(self):
        """Test subscription with default values."""
        sub = Subscription(
            user_id=12345,
            service="Spotify",
            amount=9.99,
            currency="USD"
        )
        assert sub.period_days == 30
        assert sub.start_date.date() == datetime.utcnow().date()
        assert sub.next_payment > datetime.utcnow()
    
    def test_calculate_next_payment(self):
        """Test next payment date calculation."""
        start_date = datetime(2023, 1, 1)
        sub = Subscription(
            user_id=12345,
            service="Test",
            amount=10,
            currency="USD",
            period_days=7,
            start_date=start_date
        )
        assert sub.next_payment == start_date + timedelta(days=7)

class TestUserModel:
    """Test User model functionality."""
    
    def test_user_creation(self):
        """Test creating a user with required fields."""
        user = User(
            user_id=12345,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        assert user.user_id == 12345
        assert user.username == "testuser"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.subscriptions == []
    
    def test_user_defaults(self):
        """Test user with default values."""
        user = User(user_id=12345, first_name="Test")
        assert user.username is None
        assert user.last_name is None
        assert user.subscriptions == []

class TestNextReminderOffsets:
    """Test next_reminder_offsets function."""
    
    def test_reminder_offsets(self):
        """Test calculation of reminder offsets."""
        # Test with default offsets (7, 3, 1)
        offsets = next_reminder_offsets()
        assert offsets == [7, 3, 1]
        
        # Test with custom offsets
        custom_offsets = [14, 7, 3, 1]
        offsets = next_reminder_offsets(custom_offsets)
        assert offsets == custom_offsets
        
        # Test with empty list should return default
        assert next_reminder_offsets([]) == [7, 3, 1]
        
        # Test with None should return default
        assert next_reminder_offsets(None) == [7, 3, 1]
