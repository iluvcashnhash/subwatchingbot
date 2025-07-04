import asyncio
import logging
import signal
from typing import Optional

from telegram import Update, Bot
from telegram.ext import Application, ContextTypes, ApplicationBuilder

from .config import settings
from .db import db
from .handlers import SubscriptionBotHandlers
from .scheduler import SubscriptionScheduler

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SubscriptionBot:
    def __init__(self):
        self.application: Optional[Application] = None
        self.scheduler: Optional[SubscriptionScheduler] = None
    
    async def initialize(self):
        """Initialize the bot and all its components."""
        logger.info("Initializing Subscription Bot...")
        
        # Initialize database connection
        await db.connect_db()
        
        # Create the Application
        self.application = (
            ApplicationBuilder()
            .token(settings.BOT_TOKEN)
            .post_init(self.on_startup)
            .post_shutdown(self.on_shutdown)
            .build()
        )
        
        # Initialize scheduler
        self.scheduler = SubscriptionScheduler(self.application.bot)
        
        # Add handlers
        handlers = SubscriptionBotHandlers()
        for handler in handlers.get_handlers():
            self.application.add_handler(handler)
        
        # Add error handler
        self.application.add_error_handler(self.error_handler)
        
        logger.info("Subscription Bot initialized")
    
    async def on_startup(self, application: Application) -> None:
        """Run this when the bot starts."""
        logger.info("Starting Subscription Bot...")
        await self.scheduler.start()
    
    async def on_shutdown(self, application: Application) -> None:
        """Run this when the bot stops."""
        logger.info("Shutting down Subscription Bot...")
        await self.scheduler.stop()
        await db.close_db()
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log errors caused by updates."""
        logger.error("Exception while handling an update:", exc_info=context.error)
        
        if update and hasattr(update, 'effective_message') and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ An error occurred while processing your request. "
                "The developers have been notified."
            )
    
    def run(self):
        """Run the bot until you press Ctrl-C."""
        if not self.application:
            raise RuntimeError("Bot not initialized. Call initialize() first.")
        
        # Enable graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown(sig)))
        
        # Start the Bot
        if settings.WEBHOOK_URL and settings.WEBHOOK_PATH:
            # Webhook mode
            self.application.run_webhook(
                listen="0.0.0.0",
                port=8443,
                url_path=settings.WEBHOOK_PATH,
                webhook_url=f"{settings.WEBHOOK_URL}{settings.WEBHOOK_PATH}",
                cert="cert.pem" if settings.WEBHOOK_SSL_CERT else None,
                key="key.pem" if settings.WEBHOOK_SSL_PRIV else None
            )
        else:
            # Polling mode
            self.application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    async def shutdown(self, signal):
        """Shut down the application gracefully."""
        logger.info(f"Received exit signal {signal.name}...")
        
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
        
        # Cancel all running tasks
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        
        await asyncio.gather(*tasks, return_exceptions=True)
        asyncio.get_event_loop().stop()

def main():
    """Run the bot."""
    bot = SubscriptionBot()
    
    try:
        # Initialize and run the bot
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.initialize())
        bot.run()
    except Exception as e:
        logger.error("Fatal error in main loop", exc_info=e)
    finally:
        logger.info("Bot has stopped.")

if __name__ == "__main__":
    main()
