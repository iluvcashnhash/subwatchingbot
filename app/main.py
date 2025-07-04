import logging
from telegram.ext import Application, ApplicationBuilder
from telegram import Update

from .config import settings
from .handlers import SubscriptionBotHandlers
from .scheduler import handle_payment_confirmation

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def create_application() -> Application:
    """Create and configure the Telegram application."""
    # Create application with token from settings
    application = (
        ApplicationBuilder()
        .token(settings.BOT_TOKEN)
        .build()
    )
    
    # Add handlers
    bot_handlers = SubscriptionBotHandlers(application)
    for handler in bot_handlers.get_handlers():
        application.add_handler(handler)
    
    # Add payment confirmation handler
    application.add_handler(handle_payment_confirmation)
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    return application

async def error_handler(update: object, context) -> None:
    """Log errors and send a message to the user."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    if update and hasattr(update, 'effective_message') and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Произошла ошибка при обработке вашего запроса. "
            "Попробуйте еще раз или свяжитесь с поддержкой."
        )

def main() -> None:
    """Run the bot until the user presses Ctrl-C."""
    logger.info("Starting bot...")
    
    # Create and configure application
    application = create_application()
    
    # Run the bot until the user presses Ctrl-C
    logger.info("Bot is running. Press Ctrl-C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
