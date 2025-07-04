import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot

from .models import Subscription, User
from .db import db

logger = logging.getLogger(__name__)

class SubscriptionScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self._jobs: Dict[str, str] = {}  # subscription_id -> job_id
    
    async def start(self):
        """Start the scheduler and load existing subscriptions."""
        logger.info("Starting subscription scheduler...")
        await self._load_existing_subscriptions()
        self.scheduler.start()
        logger.info("Subscription scheduler started")
    
    async def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("Subscription scheduler stopped")
    
    async def _load_existing_subscriptions(self):
        """Load existing subscriptions from the database and schedule them."""
        subscriptions_collection = db.get_collection("subscriptions")
        cursor = subscriptions_collection.find({"status": "active"})
        
        async for sub_data in cursor:
            try:
                subscription = Subscription(**sub_data)
                await self.schedule_subscription_notification(subscription)
            except Exception as e:
                logger.error(f"Error loading subscription {sub_data.get('_id')}: {e}")
    
    async def schedule_subscription_notification(self, subscription: Subscription):
        """Schedule a notification for a subscription."""
        job_id = f"sub_{subscription.id}"
        
        # Remove existing job if it exists
        if job_id in self._jobs:
            self.scheduler.remove_job(self._jobs[job_id])
        
        # Calculate next run time
        now = datetime.utcnow()
        next_run = subscription.next_billing_date
        
        # If the next billing date is in the past, calculate the next occurrence
        if next_run < now:
            next_run = self._calculate_next_billing_date(subscription)
        
        # Schedule the job
        trigger = self._create_trigger(subscription)
        
        job = self.scheduler.add_job(
            self._send_notification,
            trigger=trigger,
            id=job_id,
            args=[subscription],
            next_run_time=next_run
        )
        
        self._jobs[subscription.id] = job_id
        logger.info(f"Scheduled notification for subscription {subscription.id} to run at {next_run}")
    
    def _create_trigger(self, subscription: Subscription):
        """Create an APScheduler trigger based on subscription frequency."""
        if subscription.frequency == "daily":
            return CronTrigger(hour=9, minute=0)  ##### 9 AM daily
        elif subscription.frequency == "weekly":
            return CronTrigger(day_of_week=subscription.next_billing_date.weekday(), hour=9, minute=0)
        elif subscription.frequency == "monthly":
            return CronTrigger(day=subscription.next_billing_date.day, hour=9, minute=0)
        elif subscription.frequency == "yearly":
            return CronTrigger(
                month=subscription.next_billing_date.month,
                day=subscription.next_billing_date.day,
                hour=9,
                minute=0
            )
        else:
            # Default to daily if frequency is not recognized
            return CronTrigger(hour=9, minute=0)
    
    def _calculate_next_billing_date(self, subscription: Subscription) -> datetime:
        """Calculate the next billing date based on subscription frequency."""
        now = datetime.utcnow()
        next_date = subscription.next_billing_date
        
        while next_date < now:
            if subscription.frequency == "daily":
                next_date += timedelta(days=1)
            elif subscription.frequency == "weekly":
                next_date += timedelta(weeks=1)
            elif subscription.frequency == "monthly":
                # Handle month overflow
                next_month = next_date.month + 1
                year = next_date.year
                if next_month > 12:
                    next_month = 1
                    year += 1
                next_date = next_date.replace(month=next_month, year=year)
            elif subscription.frequency == "yearly":
                next_date = next_date.replace(year=next_date.year + 1)
            else:
                # Default to daily if frequency is not recognized
                next_date += timedelta(days=1)
        
        return next_date
    
    async def _send_notification(self, subscription: Subscription):
        """Send notification about upcoming subscription renewal."""
        try:
            user_collection = db.get_collection("users")
            user_data = await user_collection.find_one({"telegram_id": subscription.user_id})
            
            if not user_data:
                logger.error(f"User {subscription.user_id} not found for subscription {subscription.id}")
                return
            
            user = User(**user_data)
            
            message = (
                f"🔔 <b>Upcoming Subscription Renewal</b>\n\n"
                f"<b>{subscription.name}</b>\n"
                f"Amount: {subscription.amount} {subscription.currency}\n"
                f"Next billing date: {subscription.next_billing_date.strftime('%Y-%m-%d')}\n"
                f"Frequency: {subscription.frequency.capitalize()}"
            )
            
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode='HTML'
            )
            
            # Update next billing date in the database
            subscriptions_collection = db.get_collection("subscriptions")
            next_billing_date = self._calculate_next_billing_date(subscription)
            
            await subscriptions_collection.update_one(
                {"_id": subscription.id},
                {"$set": {"next_billing_date": next_billing_date}}
            )
            
            # Reschedule the job for the next billing date
            await self.schedule_subscription_notification(
                Subscription(
                    **{
                        **subscription.dict(),
                        "next_billing_date": next_billing_date
                    }
                )
            )
            
        except Exception as e:
            logger.error(f"Error sending notification for subscription {subscription.id}: {e}")
    
    async def add_subscription(self, subscription: Subscription):
        """Add a new subscription to the scheduler."""
        await self.schedule_subscription_notification(subscription)
    
    async def update_subscription(self, subscription: Subscription):
        """Update an existing subscription in the scheduler."""
        await self.schedule_subscription_notification(subscription)
    
    async def remove_subscription(self, subscription_id: str):
        """Remove a subscription from the scheduler."""
        job_id = f"sub_{subscription_id}"
        if job_id in self._jobs:
            self.scheduler.remove_job(self._jobs[job_id])
            del self._jobs[subscription_id]
            logger.info(f"Removed subscription {subscription_id} from scheduler")
