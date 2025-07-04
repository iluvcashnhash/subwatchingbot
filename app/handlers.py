from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional, cast

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from . import db, nlu
from .config import settings
from .models import Subscription, SubscriptionIntent, User

if TYPE_CHECKING:
    from telegram import CallbackQuery

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Conversation states
(
    STATE_ADD_CONFIRM,
    STATE_DELETE_CONFIRM,
) = range(2)

# Context keys
CTX_USER = "user"
CTX_PENDING_SUB = "pending_sub"


class SubscriptionBotHandlers:
    def __init__(self, application: Application):
        self.application = application
        self.user_data = application.user_data
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up all command and message handlers."""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))

        # Message handler for all text messages that are not commands
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

        # Callback query handler for inline buttons
        self.application.add_handler(
            CallbackQueryHandler(self.button_callback, pattern=r"^(confirm|cancel)_(\w+)_(\w+)$")
        )

    async def _get_or_create_user(self, update: Update) -> User:
        """Get or create a user in the database."""
        tg_user = update.effective_user
        if not tg_user:
            raise ValueError("No user associated with this update")

        users_collection = db.get_collection("users")
        user_data = await users_collection.find_one({"tg_id": tg_user.id})

        if not user_data:
            # Create new user
            new_user = User(
                tg_id=tg_user.id,
                username=tg_user.username,
                tz=settings.TZ,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            result = await users_collection.insert_one(new_user.dict(exclude={"id"}))
            user_data = await users_collection.find_one({"_id": result.inserted_id})
            logger.info(f"Created new user: {tg_user.id} ({tg_user.username or 'no username'})")

        return User(**user_data)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command - show welcome message and help."""
        user = update.effective_user
        if not user:
            return

        await self._get_or_create_user(update)

        welcome_text = f"""
👋 Hello {user.mention_html()}!

I'm your Subscription Tracker Bot. I'll help you manage all your subscriptions.

<b>What can I do?</b>
• Add new subscriptions
• List your current subscriptions
• Get reminders before payments are due
• Track your monthly expenses

<b>Try these commands:</b>
/help - Show detailed help
/add - Add a new subscription
/list - Show your subscriptions

Or just type what you want to do, like:
"Add Netflix for $15.99 monthly"
"Show me my subscriptions"
"Delete my Spotify subscription"
"""
        await update.message.reply_html(welcome_text, disable_web_page_preview=True)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command - show help message."""
        help_text = """
🤖 <b>Subscription Tracker Bot</b>

<b>Commands:</b>
/start - Show welcome message
/help - Show this help
/add - Add a new subscription
/list - List your subscriptions
/delete - Remove a subscription

<b>Examples:</b>
• <i>"Add Netflix for $15.99 monthly"</i>
• <i>"Show my subscriptions"</i>
• <i>"Delete Spotify subscription"</i>
• <i>"How much do I spend monthly?"</i>

<b>Features:</b>
• Track all your subscriptions in one place
• Get reminders before payments are due
• Monitor your monthly expenses
• Natural language processing - just type what you want!
"""
        await update.message.reply_html(help_text, disable_web_page_preview=True)
    
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
        """Handle adding a new subscription based on NLU results."""
        user = await self._get_or_create_user(update)
        
        # Extract subscription data from NLU result
        service = nlu_result.get('service', '').strip()
        amount = float(nlu_result.get('amount', 0))
        currency = nlu_result.get('currency', 'USD').upper()
        period_days = int(nlu_result.get('period_days', 30))
        
        # Parse next payment date or default to today + period
        next_payment = datetime.now(timezone.utc) + timedelta(days=period_days)
        if 'next_payment' in nlu_result:
            try:
                next_payment = datetime.fromisoformat(nlu_result['next_payment'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
                
        # Create subscription object
        subscription = Subscription(
            service=service,
            amount=amount,
            currency=currency,
            period_days=period_days,
            next_payment=next_payment,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Store in context for confirmation
        context.user_data[CTX_PENDING_SUB] = subscription
        
        # Create confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_add_{subscription.id}"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_add")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send confirmation message
        await update.message.reply_text(
            f"📝 <b>Please confirm subscription details:</b>\n\n"
            f"• <b>Service:</b> {subscription.service}\n"
            f"• <b>Amount:</b> {subscription.amount} {subscription.currency}\n"
            f"• <b>Billing period:</b> {subscription.period_days} days\n"
            f"• <b>Next payment:</b> {subscription.next_payment.strftime('%Y-%m-%d')}",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def _handle_list_subscriptions(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """List all user's subscriptions."""
        user = await self._get_or_create_user(update)
        users_collection = db.get_collection("users")
        
        # Get user with subscriptions
        user_data = await users_collection.find_one(
            {"tg_id": user.tg_id},
            {"subs": 1}
        )
        
        if not user_data or 'subs' not in user_data or not user_data['subs']:
            await update.message.reply_text("You don't have any subscriptions yet!")
            return
        
        # Format subscriptions list
        response = ["📋 <b>Your Subscriptions:</b>\n"]
        total_monthly = 0.0
        currency = 'USD'
        
        for sub_data in user_data['subs']:
            try:
                sub = Subscription(**sub_data)
                # Calculate monthly equivalent
                monthly = (sub.amount * 30) / sub.period_days
                total_monthly += monthly
                currency = sub.currency
                
                # Format subscription info
                period_str = f"{sub.period_days} days"
                if sub.period_days == 7:
                    period_str = "weekly"
                elif sub.period_days == 30:
                    period_str = "monthly"
                elif sub.period_days == 365:
                    period_str = "yearly"
                
                response.append(
                    f"• <b>{sub.service}</b>: {sub.amount:.2f} {sub.currency} "
                    f"({period_str}, next: {sub.next_payment.strftime('%Y-%m-%d')})"
                )
            except Exception as e:
                logger.error(f"Error formatting subscription: {e}")
                continue
        
        # Add total
        response.append(
            f"\n💵 <b>Total Monthly:</b> {total_monthly:.2f} {currency}"
        )
        
        await update.message.reply_text(
            "\n".join(response),
            parse_mode=ParseMode.HTML
        )
    
    async def _handle_delete_subscription(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE,
        nlu_result: Dict[str, Any]
    ) -> None:
        """Handle deleting a subscription based on NLU results."""
        user = await self._get_or_create_user(update)
        service = nlu_result.get('service', '').strip().lower()
        
        if not service:
            await update.message.reply_text(
                "Please specify which subscription you want to delete.\n"
                "Example: \"Delete Netflix\" or \"Cancel Spotify subscription\""
            )
            return
        
        # Store in context for confirmation
        context.user_data['delete_service'] = service
        
        # Create confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, delete it", callback_data=f"confirm_delete_{service}"),
                InlineKeyboardButton("❌ No, keep it", callback_data="cancel_delete")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Are you sure you want to delete the subscription for <b>{service.title()}</b>?",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle button callbacks from inline keyboards."""
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        if not user:
            return
            
        callback_data = query.data
        
        # Handle subscription confirmation
        if callback_data.startswith("confirm_add_"):
            await self._handle_confirm_add(update, context, query)
        elif callback_data == "cancel_add":
            await self._handle_cancel_add(update, context, query)
        elif callback_data.startswith("confirm_delete_"):
            await self._handle_confirm_delete(update, context, query)
        elif callback_data == "cancel_delete":
            await self._handle_cancel_delete(update, context, query)
    
    async def _handle_confirm_add(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        query: CallbackQuery
    ) -> None:
        """Handle confirmation of adding a new subscription."""
        user = await self._get_or_create_user(update)
        subscription = context.user_data.get(CTX_PENDING_SUB)
        
        if not subscription:
            await query.edit_message_text("❌ Error: Subscription data not found. Please try again.")
            return
            
        users_collection = db.get_collection("users")
        
        try:
            # Add subscription to user's subscriptions
            result = await users_collection.update_one(
                {"tg_id": user.tg_id},
                {"$push": {"subs": subscription.model_dump(exclude={"id"})}},
                upsert=True
            )
            
            if result.modified_count > 0 or result.upserted_id:
                await query.edit_message_text(
                    f"✅ Successfully added subscription for <b>{subscription.service}</b>!",
                    parse_mode=ParseMode.HTML
                )
                
                # Clear pending subscription
                if CTX_PENDING_SUB in context.user_data:
                    del context.user_data[CTX_PENDING_SUB]
            else:
                await query.edit_message_text("❌ Failed to add subscription. Please try again.")
                
        except Exception as e:
            logger.error(f"Error adding subscription: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again later.")
    
    async def _handle_cancel_add(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        query: CallbackQuery
    ) -> None:
        """Handle cancellation of adding a new subscription."""
        # Clear pending subscription
        if CTX_PENDING_SUB in context.user_data:
            del context.user_data[CTX_PENDING_SUB]
            
        await query.edit_message_text("❌ Subscription addition cancelled.")
    
    async def _handle_confirm_delete(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        query: CallbackQuery
    ) -> None:
        """Handle confirmation of subscription deletion."""
        user = await self._get_or_create_user(update)
        service = context.user_data.get('delete_service')
        
        if not service:
            await query.edit_message_text("❌ Error: Subscription not found. Please try again.")
            return
            
        users_collection = db.get_collection("users")
        
        try:
            # Remove subscription from user's subscriptions
            result = await users_collection.update_one(
                {"tg_id": user.tg_id},
                {"$pull": {"subs": {"service": {"$regex": f"^{service}$", "$options": "i"}}}}
            )
            
            if result.modified_count > 0:
                await query.edit_message_text(
                    f"✅ Successfully deleted subscription for <b>{service.title()}</b>.",
                    parse_mode=ParseMode.HTML
                )
                
                # Clear delete service from context
                if 'delete_service' in context.user_data:
                    del context.user_data['delete_service']
            else:
                await query.edit_message_text("❌ Subscription not found or already deleted.")
                
        except Exception as e:
            logger.error(f"Error deleting subscription: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again later.")
    
    async def _handle_cancel_delete(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        query: CallbackQuery
    ) -> None:
        """Handle cancellation of subscription deletion."""
        # Clear delete service from context
        if 'delete_service' in context.user_data:
            del context.user_data['delete_service']
            
        await query.edit_message_text("❌ Subscription deletion cancelled.")
    
    def get_handlers(self):
        """Return all command and message handlers."""
        return [
            CommandHandler("start", self.start),
            CommandHandler("help", self.help_command),
            CommandHandler("add", self._handle_add_subscription),
            CommandHandler("list", self._handle_list_subscriptions),
            CommandHandler("delete", self._handle_delete_subscription),
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message),
            CallbackQueryHandler(self.button_callback)
        ]
