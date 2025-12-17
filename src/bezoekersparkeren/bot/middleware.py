"""Middleware voor user authenticatie via whitelist."""

from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

def authorized_only(allowed_users: list[int]):
    """
    Decorator die checkt of de user in de whitelist staat.
    
    Usage:
        @authorized_only(config.telegram.allowed_users)
        async def my_handler(update, context):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user = update.effective_user
            if user is None:
                return
            
            if user.id not in allowed_users:
                logger.warning(f"Unauthorized access attempt by user {user.id} ({user.username})")
                # Optioneel: stuur bericht of negeer volledig
                await update.message.reply_text(
                    "⛔ Je bent niet geautoriseerd om deze bot te gebruiken.\n"
                    f"Je user ID is: `{user.id}`",
                    parse_mode="Markdown"
                )
                return
            
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator


class AuthFilter:
    """Filter class voor gebruik met MessageHandler en CallbackQueryHandler."""
    
    def __init__(self, allowed_users: list[int]):
        self.allowed_users = allowed_users
    
    def __call__(self, update: Update) -> bool:
        user = update.effective_user
        return user is not None and user.id in self.allowed_users
