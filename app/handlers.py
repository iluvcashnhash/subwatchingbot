from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

from .models import User, Subscription, SubscriptionCreate, SubscriptionStatus
from .nlu import NLUProcessor
from .db import db
from .config import settings

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SubscriptionBotHandlers:
    def __init__(self):
        self.nlu = NLUProcessor(settings.GIGACHAT_CREDENTIALS)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /start is issued."""
        user = update.effective_user
        await self._get_or_create_user(update, context)
        
        welcome_text = (
            f"👋 Hello {user.mention_html()}!\n\n"
            "I'm your Subscription Tracker Bot. I'll help you keep track of all your subscriptions.\n\n"
            "You can use these commands:\n"
            "/add - Add a new subscription\n"
            "/list - List all your subscriptions\n"
            "/help - Show help message"
        )
        
        await update.message.reply_html(welcome_text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /help is issued."""
        help_text = (
            "🤖 <b>Subscription Tracker Bot Help</b>\n\n"
            "<b>Available Commands:</b>\n"
            "/start - Start the bot and show welcome message\n"
            "/help - Show this help message\n"
            "/add - Add a new subscription\n"
            "/list - List all your subscriptions\n"
            "/delete - Delete a subscription\n"
            "/stats - Show your subscription statistics\n\n"
            "You can also just type what you want to do, like:\n"
            "• "Add Netflix subscription for $15.99 monthly"\n"
            "• "Show me my subscriptions"\n"
            "• "Delete my Spotify subscription"\n"
        )
        await update.message.reply_html(help_text)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle any message that's not a command."""
        if not update.message or not update.message.text:
            return
            
        user = update.effective_user
        text = update.message.text
        
        # Process the message with NLU
        nlu_result = await self.nlu.process(text, user.id)
        
        # Route based on detected intent
        intent = nlu_result.get('intent', 'unknown')
        
        if intent == 'add_subscription':
            await self._handle_add_subscription(update, context, nlu_result)
        elif intent == 'list_subscriptions':
            await self._handle_list_subscriptions(update, context)
        elif intent == 'delete_subscription':
            await self._handle_delete_subscription(update, context, nlu_result)
        else:
            await update.message.reply_text(
                "I'm not sure what you mean. Type /help to see what I can do."
            )
    
    async def _get_or_create_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> User:
        """Get user from DB or create if not exists."""
        user_data = update.effective_user
        users_collection = db.get_collection("users")
        
        # Check if user exists
        existing_user = await users_collection.find_one({"telegram_id": user_data.id})
        
        if existing_user:
            return User(**existing_user)
        
        # Create new user
        new_user = UserCreate(
            telegram_id=user_data.id,
            username=user_data.username,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            language_code=user_data.language_code
        )
        
        result = await users_collection.insert_one(new_user.dict())
        created_user = await users_collection.find_one({"_id": result.inserted_id})
        return User(**created_user)
    
    async def _handle_add_subscription(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE,
        nlu_result: Dict[str, Any]
    ) -> None:
        """Handle adding a new subscription."""
        # This is a simplified implementation
        await update.message.reply_text(
            "To add a new subscription, please use the /add command with details like:\n"
            "/add <name> <amount> <currency> <frequency>\n\n"
            "Example: /add Netflix 15.99 USD monthly"
        )
    
    async def _handle_list_subscriptions(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle listing user's subscriptions."""
        user = await self._get_or_create_user(update, context)
        subscriptions_collection = db.get_collection("subscriptions")
        
        cursor = subscriptions_collection.find({"user_id": user.telegram_id, "status": "active"})
        subscriptions = await cursor.to_list(length=100)
        
        if not subscriptions:
            await update.message.reply_text("You don't have any active subscriptions yet!")
            return
        
        response = ["📋 <b>Your Active Subscriptions:</b>\n"]
        total_monthly = 0.0
        
        for sub in subscriptions:
            subscription = Subscription(**sub)
            amount = subscription.amount
            
            # Convert all to monthly equivalent for total
            if subscription.frequency == "yearly":
                monthly = amount / 12
            elif subscription.frequency == "weekly":
                monthly = amount * 4.33
            else:
                monthly = amount
                
            total_monthly += monthly
            
            response.append(
                f"• {subscription.name}: {subscription.amount} {subscription.currency} "
                f"({subscription.frequency}, next: {subscription.next_billing_date.strftime('%Y-%m-%d')})"
            )
        
        response.append(f"\n💵 <b>Total Monthly:</b> {total_monthly:.2f} {subscriptions[0]['currency'] if subscriptions else 'USD'}")
        
        await update.message.reply_text("\n".join(response), parse_mode='HTML')
    
    async def _handle_delete_subscription(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE,
        nlu_result: Dict[str, Any]
    ) -> None:
        """Handle deleting a subscription."""
        await update.message.reply_text(
            "To delete a subscription, please use the /delete command with the subscription name.\n"
            "Example: /delete Netflix"
        )
    
    def get_handlers(self):
        """Return all command and message handlers."""
        return [
            CommandHandler("start", self.start),
            CommandHandler("help", self.help_command),
            CommandHandler("add", self._handle_add_subscription),
            CommandHandler("list", self._handle_list_subscriptions),
            CommandHandler("delete", self._handle_delete_subscription),
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        ]
