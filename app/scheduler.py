import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackContext
from .models import Subscription
from .db import db

logger = logging.getLogger(__name__)

# Reminder offsets in days
REMINDER_OFFSETS = [7, 3, 1]

# Callback data prefix for payment confirmation
PAYMENT_CONFIRM_PREFIX = "confirm_payment_"


def schedule_reminders(sub: Subscription, chat_id: int, app: Application) -> None:
    """
    Schedule reminder jobs for a subscription.
    
    Args:
        sub: The subscription to schedule reminders for
        chat_id: The chat ID to send reminders to
        app: The application instance for job queue access
    """
    if not sub.next_payment:
        logger.warning(f"No next_payment date for subscription {sub.id}, skipping reminders")
        return
        
    job_queue = app.job_queue
    if not job_queue:
        logger.error("No job queue available in application")
        return
    
    # Clear any existing jobs for this subscription
    for job in job_queue.jobs():
        if job.data and job.data.get('sub_id') == str(sub.id):
            job.schedule_removal()
    
    # Schedule new reminder jobs
    for offset_days in REMINDER_OFFSETS:
        trigger_date = sub.next_payment - timedelta(days=offset_days)
        
        # Skip if the reminder would be in the past
        if trigger_date < datetime.now(timezone.utc):
            continue
            
        job_queue.run_once(
            callback=reminder_callback,
            when=trigger_date,
            data={
                'chat_id': chat_id,
                'sub_id': str(sub.id),
                'offset_days': offset_days
            },
            name=f"reminder_{sub.id}_{offset_days}d"
        )
        
        logger.info(
            f"Scheduled {offset_days} day reminder for subscription {sub.id} "
            f"(service: {sub.service}) to trigger on {trigger_date}"
        )


async def reminder_callback(context: CallbackContext) -> None:
    """
    Callback for sending reminder messages and handling payment confirmation.
    """
    job = context.job
    if not job or not job.data:
        logger.error("Reminder job called without valid data")
        return
        
    chat_id = job.data.get('chat_id')
    sub_id = job.data.get('sub_id')
    offset_days = job.data.get('offset_days')
    
    if not all([chat_id, sub_id, offset_days is not None]):
        logger.error(f"Incomplete job data: {job.data}")
        return
    
    # Get subscription from database
    users_collection = db.get_collection("users")
    user_data = await users_collection.find_one(
        {"subs._id": sub_id},
        {"subs.$": 1}
    )
    
    if not user_data or not user_data.get('subs'):
        logger.error(f"Subscription {sub_id} not found or error accessing database")
        return
        
    sub_data = user_data['subs'][0]
    sub = Subscription(**sub_data)
    
    # Create inline keyboard for payment confirmation
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Отметить оплаченной",
                callback_data=f"{PAYMENT_CONFIRM_PREFIX}{sub_id}"
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Format amount with 2 decimal places if it's a whole number
    amount = int(sub.amount) if sub.amount == int(sub.amount) else sub.amount
    
    # Send reminder message
    message = (
        f"🔔 Через {offset_days} дн спишется "
        f"{amount}{sub.currency} за {sub.service}"
    )
    
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Failed to send reminder for subscription {sub_id}: {e}")


async def handle_payment_confirmation(update: Update, context: CallbackContext) -> None:
    """
    Handle payment confirmation button press.
    Updates next_payment date and reschedules reminders.
    """
    query = update.callback_query
    await query.answer()
    
    if not query.data or not query.data.startswith(PAYMENT_CONFIRM_PREFIX):
        return
    
    sub_id = query.data[len(PAYMENT_CONFIRM_PREFIX):]
    chat_id = query.message.chat_id
    
    # Get subscription from database
    users_collection = db.get_collection("users")
    user_data = await users_collection.find_one(
        {"subs._id": sub_id},
        {"subs.$": 1}
    )
    
    if not user_data or not user_data.get('subs'):
        logger.error(f"Subscription {sub_id} not found")
        await query.edit_message_text("❌ Ошибка: подписка не найдена")
        return
    
    # Update subscription's next_payment date
    sub_data = user_data['subs'][0]
    sub = Subscription(**sub_data)
    
    new_next_payment = sub.next_payment + timedelta(days=sub.period_days)
    
    # Update in database
    result = await users_collection.update_one(
        {"tg_id": user_data['tg_id'], "subs._id": sub_id},
        {"$set": {"subs.$.next_payment": new_next_payment}}
    )
    
    if result.modified_count > 0:
        # Reschedule reminders for the new payment date
        schedule_reminders(
            Subscription(**{**sub_data, "next_payment": new_next_payment}),
            chat_id,
            context.application
        )
        
        # Update message to show confirmation
        amount = int(sub.amount) if sub.amount == int(sub.amount) else sub.amount
        await query.edit_message_text(
            f"✅ Оплата за {sub.service} ({amount}{sub.currency}) отмечена. "
            f"Следующее списание: {new_next_payment.strftime('%Y-%m-%d')}",
            reply_markup=None
        )
    else:
        await query.edit_message_text("❌ Не удалось обновить дату следующего платежа")
