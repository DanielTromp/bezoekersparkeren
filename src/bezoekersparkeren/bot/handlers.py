"""Telegram bot command en callback handlers."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from bezoekersparkeren.client import ParkeerClient
from bezoekersparkeren.config import Config
import logging

logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_PLATE = 1
WAITING_FOR_DURATION = 2
CONFIRM_STOP = 3

# Store client instance
_client: ParkeerClient | None = None
_config: Config | None = None

def init_handlers(config: Config):
    """Initialize handlers met config."""
    global _config
    _config = config


async def get_client() -> ParkeerClient:
    """Get or create ParkeerClient instance."""
    global _client
    if _client is None:
        _client = ParkeerClient(_config)
        await _client._init_browser()
        await _client.login()
    return _client


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler voor /start command - toont hoofdmenu."""
    keyboard = [
        [
            InlineKeyboardButton("🚗 Bezoek aanmelden", callback_data="menu_register"),
            InlineKeyboardButton("🛑 Stoppen", callback_data="menu_stop"),
        ],
        [
            InlineKeyboardButton("📋 Actieve sessies", callback_data="menu_list"),
            InlineKeyboardButton("💰 Saldo", callback_data="menu_balance"),
        ],
        [
            InlineKeyboardButton("⭐ Favorieten", callback_data="menu_favorites"),
        ],
    ]
    
    await update.message.reply_text(
        "🅿️ *Bezoekersparkeren Almere*\n\n"
        "Wat wil je doen?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler voor inline button callbacks."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "menu_register":
        # Toon favorieten als snelkeuze + optie voor nieuw kenteken
        favorites = _config.favorites if _config and _config.favorites else []
        
        keyboard = []
        for fav in favorites:
            keyboard.append([
                InlineKeyboardButton(
                    f"⭐ {fav.name} ({fav.plate})", 
                    callback_data=f"register_{fav.plate}"
                )
            ])
        keyboard.append([
            InlineKeyboardButton("✏️ Ander kenteken invoeren", callback_data="register_custom")
        ])
        keyboard.append([
            InlineKeyboardButton("⬅️ Terug", callback_data="menu_back")
        ])
        
        await query.edit_message_text(
            "🚗 *Bezoek aanmelden*\n\n"
            "Kies een favoriet of voer een kenteken in:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    
    elif data.startswith("register_") and data != "register_custom":
        # Direct registreren met favoriet kenteken
        plate = data.replace("register_", "")
        await query.edit_message_text(f"⏳ Bezig met aanmelden van {plate}...")
        
        try:
            client = await get_client()
            session = await client.register_visitor(plate)
            await query.edit_message_text(
                f"✅ *Kenteken aangemeld!*\n\n"
                f"🚗 `{plate}`\n"
                f"⏰ Gestart om: {session.start_time.strftime('%H:%M') if session.start_time else 'nu'}\n\n"
                f"Vergeet niet om af te melden!",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error registering plate: {e}")
            await query.edit_message_text(f"❌ Fout bij aanmelden: {str(e)}")
    
    elif data == "register_custom":
        await query.edit_message_text(
            "✏️ *Kenteken invoeren*\n\n"
            "Stuur het kenteken als bericht (bijv. `AB-123-CD`):",
            parse_mode="Markdown"
        )
        context.user_data["awaiting_plate"] = True
    
    elif data == "menu_stop":
        # Haal actieve sessies op en toon als buttons
        try:
            client = await get_client()
            sessions = await client.get_active_sessions()
            
            if not sessions:
                await query.edit_message_text(
                    "ℹ️ Er zijn geen actieve parkeersessies.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Terug", callback_data="menu_back")
                    ]])
                )
                return
            
            keyboard = []
            for session in sessions:
                keyboard.append([
                    InlineKeyboardButton(
                        f"🛑 Stop: {session.plate}", 
                        callback_data=f"stop_{session.plate}"
                    )
                ])
            keyboard.append([
                InlineKeyboardButton("⬅️ Terug", callback_data="menu_back")
            ])
            
            await query.edit_message_text(
                "🛑 *Welke sessie stoppen?*",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error getting sessions: {e}")
            await query.edit_message_text(f"❌ Fout: {str(e)}")
    
    elif data.startswith("stop_"):
        plate = data.replace("stop_", "")
        await query.edit_message_text(f"⏳ Bezig met afmelden van {plate}...")
        
        try:
            client = await get_client()
            sessions = await client.get_active_sessions()
            session = next((s for s in sessions if s.plate == plate), None)
            
            if session:
                await client.stop_session(session)
                await query.edit_message_text(f"✅ Sessie voor `{plate}` is gestopt!", parse_mode="Markdown")
            else:
                await query.edit_message_text(f"❌ Geen actieve sessie gevonden voor `{plate}`.")
        except Exception as e:
            logger.error(f"Error stopping session: {e}")
            await query.edit_message_text(f"❌ Fout bij stoppen: {str(e)}")
    
    elif data == "menu_list":
        try:
            client = await get_client()
            sessions = await client.get_active_sessions()
            
            if not sessions:
                text = "ℹ️ Geen actieve parkeersessies."
            else:
                text = "📋 *Actieve sessies:*\n\n"
                for s in sessions:
                    text += f"• `{s.plate}`"
                    if s.start_time:
                        text += f" - sinds {s.start_time.strftime('%H:%M')}"
                    if s.end_time:
                        text += f" (tot {s.end_time.strftime('%H:%M')})"
                    text += "\n"
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Terug", callback_data="menu_back")
                ]]),
                parse_mode="Markdown"
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Fout: {str(e)}")
    
    elif data == "menu_balance":
        try:
            client = await get_client()
            balance = await client.get_balance()
            await query.edit_message_text(
                f"💰 *Saldo*\n\n"
                f"Beschikbaar: €{balance.amount:.2f}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Terug", callback_data="menu_back")
                ]]),
                parse_mode="Markdown"
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Fout: {str(e)}")
    
    elif data == "menu_favorites":
        favorites = _config.favorites if _config and _config.favorites else []
        
        if not favorites:
            text = "ℹ️ Geen favorieten ingesteld.\n\nVoeg favorieten toe in `config.yaml`."
        else:
            text = "⭐ *Favorieten:*\n\n"
            for fav in favorites:
                text += f"• {fav.name}: `{fav.plate}`\n"
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Terug", callback_data="menu_back")
            ]]),
            parse_mode="Markdown"
        )
    
    elif data == "menu_back":
        # Terug naar hoofdmenu
        keyboard = [
            [
                InlineKeyboardButton("🚗 Bezoek aanmelden", callback_data="menu_register"),
                InlineKeyboardButton("🛑 Stoppen", callback_data="menu_stop"),
            ],
            [
                InlineKeyboardButton("📋 Actieve sessies", callback_data="menu_list"),
                InlineKeyboardButton("💰 Saldo", callback_data="menu_balance"),
            ],
            [
                InlineKeyboardButton("⭐ Favorieten", callback_data="menu_favorites"),
            ],
        ]
        await query.edit_message_text(
            "🅿️ *Bezoekersparkeren Almere*\n\nWat wil je doen?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler voor tekst berichten (bijv. kenteken invoer)."""
    if context.user_data.get("awaiting_plate"):
        plate = update.message.text.upper().strip()
        context.user_data["awaiting_plate"] = False
        
        # Valideer kenteken formaat (simpele check)
        if len(plate) < 4:
            await update.message.reply_text("❌ Ongeldig kenteken. Probeer opnieuw met /start")
            return
        
        await update.message.reply_text(f"⏳ Bezig met aanmelden van {plate}...")
        
        try:
            client = await get_client()
            session = await client.register_visitor(plate)
            await update.message.reply_text(
                f"✅ *Kenteken aangemeld!*\n\n"
                f"🚗 `{plate}`\n\n"
                f"Gebruik /start om terug te gaan naar het menu.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error registering plate: {e}")
            await update.message.reply_text(f"❌ Fout bij aanmelden: {str(e)}")
    else:
        # Onbekend bericht, toon help
        await update.message.reply_text(
            "Gebruik /start om het menu te openen."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler voor /help command."""
    await update.message.reply_text(
        "🅿️ *Bezoekersparkeren Bot*\n\n"
        "*Commando's:*\n"
        "/start - Open het hoofdmenu\n"
        "/register <kenteken> - Snel aanmelden\n"
        "/stop <kenteken> - Snel stoppen\n"
        "/list - Toon actieve sessies\n"
        "/balance - Toon saldo\n"
        "/help - Deze hulp\n"
        "/myid - Toon je Telegram user ID\n\n"
        "*Tip:* Gebruik de knoppen in /start voor makkelijke bediening!",
        parse_mode="Markdown"
    )


async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler voor /myid - toont user ID (handig voor whitelist setup)."""
    user = update.effective_user
    await update.message.reply_text(
        f"👤 *Jouw Telegram gegevens:*\n\n"
        f"User ID: `{user.id}`\n"
        f"Username: @{user.username or 'geen'}\n"
        f"Naam: {user.full_name}",
        parse_mode="Markdown"
    )


async def quick_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler voor /register <kenteken> - snelle registratie."""
    if not context.args:
        await update.message.reply_text(
            "Gebruik: `/register AB-123-CD`",
            parse_mode="Markdown"
        )
        return
    
    plate = context.args[0].upper()
    await update.message.reply_text(f"⏳ Bezig met aanmelden van {plate}...")
    
    try:
        client = await get_client()
        await client.register_visitor(plate)
        await update.message.reply_text(f"✅ `{plate}` aangemeld!", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Fout: {str(e)}")


async def quick_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler voor /stop <kenteken> - snel stoppen."""
    if not context.args:
        await update.message.reply_text(
            "Gebruik: `/stop AB-123-CD`",
            parse_mode="Markdown"
        )
        return
    
    plate = context.args[0].upper()
    await update.message.reply_text(f"⏳ Bezig met stoppen van {plate}...")
    
    try:
        client = await get_client()
        sessions = await client.get_active_sessions()
        session = next((s for s in sessions if s.plate == plate), None)
        
        if session:
            await client.stop_session(session)
            await update.message.reply_text(f"✅ `{plate}` gestopt!", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ Geen actieve sessie gevonden voor `{plate}`.")
    except Exception as e:
        await update.message.reply_text(f"❌ Fout: {str(e)}")
