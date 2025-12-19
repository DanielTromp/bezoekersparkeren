"""Telegram bot voor bezoekersparkeren."""

import asyncio
import logging
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from bezoekersparkeren.config import Config
from bezoekersparkeren.bot.handlers import (
    init_handlers,
    start,
    help_command,
    myid_command,
    button_callback,
    handle_text_message,
    quick_register,
    quick_stop,
    handle_photo_message,
)
from bezoekersparkeren.bot.middleware import authorized_only, AuthFilter

logger = logging.getLogger(__name__)


class ParkeerBot:
    """Telegram bot voor bezoekersparkeren."""
    
    def __init__(self, config: Config):
        self.config = config
        self.allowed_users = self._parse_allowed_users()
        self.application: Application | None = None
    
    def _parse_allowed_users(self) -> list[int]:
        """Parse allowed users from config (comma-separated string to list of ints)."""
        users_str = self.config.telegram.allowed_users
        if not users_str:
            logger.warning("No allowed users configured! Bot will reject everyone.")
            return []
        
        if isinstance(users_str, list):
            return [int(u) for u in users_str]
        
        if isinstance(users_str, str):
            return [int(u.strip()) for u in users_str.split(",") if u.strip()]
            
        return []
    
    async def start(self):
        """Start de bot."""
        logger.info(f"Starting Telegram bot with {len(self.allowed_users)} allowed users")
        
        # Initialize handlers met config
        init_handlers(self.config)
        
        # Build application
        self.application = (
            Application.builder()
            .token(self.config.telegram.bot_token)
            .build()
        )
        
        # Auth filter
        auth_filter = filters.User(self.allowed_users)
        
        # Command handlers (alleen voor geautoriseerde users)
        self.application.add_handler(
            CommandHandler("start", start, filters=auth_filter)
        )
        self.application.add_handler(
            CommandHandler("help", help_command, filters=auth_filter)
        )
        self.application.add_handler(
            CommandHandler("register", quick_register, filters=auth_filter)
        )
        self.application.add_handler(
            CommandHandler("stop", quick_stop, filters=auth_filter)
        )
        
        # /myid is voor iedereen toegankelijk (om je ID te kunnen vinden)
        self.application.add_handler(CommandHandler("myid", myid_command))
        
        # Callback query handler voor inline buttons
        self.application.add_handler(
            CallbackQueryHandler(button_callback)
        )
        
        # Text message handler
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & auth_filter,
                handle_text_message
            )
        )
        
        # Photo handler
        self.application.add_handler(
            MessageHandler(
                filters.PHOTO & auth_filter,
                handle_photo_message
            )
        )
        
        # Handler voor niet-geautoriseerde users
        async def unauthorized_handler(update, context):
            user = update.effective_user
            logger.warning(f"Unauthorized access: {user.id} ({user.username})")
            await update.message.reply_text(
                f"⛔ Niet geautoriseerd.\n\nJe user ID: `{user.id}`",
                parse_mode="Markdown"
            )
        
        self.application.add_handler(
            MessageHandler(~auth_filter, unauthorized_handler)
        )
        
        # Start polling
        logger.info("Bot started, polling for updates...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)
    
    async def stop(self):
        """Stop de bot."""
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()


async def run_bot():
    """Run de bot (standalone)."""
    config = Config.load()
    if not config.telegram:
        print("Error: No telegram config found in config.yaml or environment variables")
        return
        
    bot = ParkeerBot(config)
    
    try:
        await bot.start()
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await bot.stop()


def main():
    """Entry point voor telegram bot."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
