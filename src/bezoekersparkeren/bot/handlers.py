"""Telegram bot command en callback handlers."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import ContextTypes, ConversationHandler
from bezoekersparkeren.client import ParkeerClient
from bezoekersparkeren.config import Config
import logging

import logging
import io
from bezoekersparkeren.license_plate_recognition import recognize_plate

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


async def _safe_edit_message(query, text: str, **kwargs):
    """Edit message text safely, picking up 'Message is not modified' errors."""
    try:
        await query.edit_message_text(text, **kwargs)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            logger.debug("Message not modified, suppressing error")
        else:
            raise e


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
        
        await _safe_edit_message(
            query,
            "🚗 *Bezoek aanmelden*\n\n"
            "Kies een favoriet of voer een kenteken in:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    
    elif data.startswith("register_") and not any(x in data for x in ["register_custom", "register_now_", "register_multi_", "regmulti_"]) :
        # Kies tussen direct of meerdaags
        plate = data.replace("register_", "")
        keyboard = [
            [
                InlineKeyboardButton("🚀 Direct starten", callback_data=f"register_now_{plate}"),
                InlineKeyboardButton("📅 Meerdaags", callback_data=f"register_multi_{plate}"),
            ],
            [InlineKeyboardButton("⬅️ Terug", callback_data="menu_register")]
        ]
        await _safe_edit_message(
            query,
            f"🚗 *Kenteken: {plate}*\n\nWat wil je doen?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data.startswith("register_now_"):
        # Direct registreren
        plate = data.replace("register_now_", "")
        await _safe_edit_message(query, f"⏳ Bezig met aanmelden van {plate}...")
        
        try:
            client = await get_client()
            # Gebruik register_multiple_days met 1 dag voor consistentie
            sessions = await client.register_multiple_days(plate, days=1)
            session = sessions[0]
            
            end_str = ""
            if session.end_time:
                end_str = f"⏰ Gepland tot: {session.end_time.strftime('%H:%M')}, of meld je eerder af."
            else:
                end_str = "Vergeet niet om af te melden!"

            await _safe_edit_message(
                query,
                f"✅ *Kenteken aangemeld!*\n\n"
                f"🚗 `{plate}`\n"
                f"{end_str}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error registering plate: {e}")
            await _safe_edit_message(query, f"❌ Fout bij aanmelden: {str(e)}")

    elif data.startswith("register_multi_"):
        plate = data.replace("register_multi_", "")
        # Toon keyboard voor aantal dagen
        keyboard = []
        row = []
        for i in range(2, 8):
            row.append(InlineKeyboardButton(f"{i} dgn", callback_data=f"regmulti_{i}_{plate}"))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        keyboard.append([InlineKeyboardButton("⬅️ Terug", callback_data=f"register_{plate}")])
        
        await _safe_edit_message(
            query,
            f"📅 *Meerdaags parkeren: {plate}*\n\nHoeveel dagen wil je aanmelden?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data.startswith("regmulti_"):
        # regmulti_{days}_{plate}
        parts = data.split("_")
        days = int(parts[1])
        plate = parts[2]
        
        await _safe_edit_message(query, f"⏳ Bezig met aanmelden van {plate} voor {days} dagen...")
        
        try:
            client = await get_client()
            sessions = await client.register_multiple_days(plate, days=days)
            last_session = sessions[-1]
            
            until_date = last_session.end_time.strftime('%d-%m %H:%M') if last_session.end_time else "onbekend"
            
            await _safe_edit_message(
                query,
                f"✅ *Kenteken aangemeld voor {days} dagen!*\n\n"
                f"🚗 `{plate}`\n"
                f"⏰ Gepland tot: {until_date}, of meld je eerder af.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error registering multi-day plate: {e}")
            await _safe_edit_message(query, f"❌ Fout bij aanmelden: {str(e)}")
    
    elif data == "register_custom":
        await _safe_edit_message(
            query,
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
                await _safe_edit_message(
                    query,
                    "ℹ️ Er zijn geen actieve parkeersessies.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Terug", callback_data="menu_back")
                    ]])
                )
                return
            
            keyboard = []
            seen_plates = set()
            for session in sessions:
                if session.plate not in seen_plates:
                    keyboard.append([
                        InlineKeyboardButton(
                            f"🛑 Stop: {session.plate}", 
                            callback_data=f"stop_{session.plate}"
                        )
                    ])
                    seen_plates.add(session.plate)
            keyboard.append([
                InlineKeyboardButton("⬅️ Terug", callback_data="menu_back")
            ])
            
            await _safe_edit_message(
                query,
                "🛑 *Welke sessie stoppen?*",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error getting sessions: {e}")
            await _safe_edit_message(query, f"❌ Fout: {str(e)}")
    
    elif data.startswith("stop_"):
        plate = data.replace("stop_", "")
        await _safe_edit_message(query, f"⏳ Bezig met afmelden van alle sessies voor {plate}...")
        
        try:
            client = await get_client()
            count = await client.stop_all_sessions(plate)
            
            if count > 0:
                await _safe_edit_message(query, f"✅ {count} sessie(s) voor `{plate}` zijn gestopt!", parse_mode="Markdown")
            else:
                await _safe_edit_message(query, f"❌ Geen actieve sessies gevonden voor `{plate}`.")
        except Exception as e:
            logger.error(f"Error stopping sessions: {e}")
            await _safe_edit_message(query, f"❌ Fout bij stoppen: {str(e)}")
    
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
            
            await _safe_edit_message(
                query,
                text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Terug", callback_data="menu_back")
                ]]),
                parse_mode="Markdown"
            )
        except Exception as e:
            await _safe_edit_message(query, f"❌ Fout: {str(e)}")
    
    elif data == "menu_balance":
        try:
            client = await get_client()
            balance = await client.get_balance()
            await _safe_edit_message(
                query,
                f"💰 *Saldo*\n\n"
                f"Beschikbaar: €{balance.amount:.2f}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Terug", callback_data="menu_back")
                ]]),
                parse_mode="Markdown"
            )
        except Exception as e:
            await _safe_edit_message(query, f"❌ Fout: {str(e)}")
    
    elif data == "menu_favorites":
        favorites = _config.favorites if _config and _config.favorites else []
        
        if not favorites:
            text = "ℹ️ Geen favorieten ingesteld.\n\nVoeg favorieten toe in `config.yaml`."
        else:
            text = "⭐ *Favorieten:*\n\n"
            for fav in favorites:
                text += f"• {fav.name}: `{fav.plate}`\n"
        
        await _safe_edit_message(
            query,
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
        await _safe_edit_message(
            query,
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
            sessions = await client.register_multiple_days(plate, days=1)
            session = sessions[0]
            
            end_str = ""
            if session.end_time:
                end_str = f"⏰ Gepland tot: {session.end_time.strftime('%H:%M')}, of meld je eerder af."
            else:
                end_str = "Gebruik /start om terug te gaan naar het menu."

            await update.message.reply_text(
                f"✅ *Kenteken aangemeld!*\n\n"
                f"🚗 `{plate}`\n\n"
                f"{end_str}",
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


async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler voor foto's (nummerplaatherkenning)."""
    if not update.message.photo:
        return

    # Feedback geven
    status_msg = await update.message.reply_text("Even kijken naar de nummerplaat... 🔍")
    
    try:
        # Pak de grootste foto
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # Download naar memory
        f = io.BytesIO()
        await file.download_to_memory(out=f)
        image_bytes = f.getvalue()
        
        # Roep vision API aan
        if not _config:
            await status_msg.edit_text("❌ Interne fout: config niet geladen.")
            return

        plate = await recognize_plate(image_bytes, _config)
        
        if plate:
            # Succes! Vraag om bevestiging via inline keyboard
            keyboard = [
                [
                    InlineKeyboardButton(f"✅ Start: {plate}", callback_data=f"register_{plate}"),
                    InlineKeyboardButton("❌ Nee", callback_data="menu_back") # Of delete
                ]
            ]
            
            await status_msg.edit_text(
                f"Nummerplaat gevonden: `{plate}`\n\nWil je een parkeersessie starten?",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        else:
            # Geen plaat gevonden
            await status_msg.edit_text(
                "Kon de nummerplaat niet goed lezen 😕\n\n"
                "Voer deze handmatig in met `/register <kenteken>` of gebruik het menu.",
                parse_mode="Markdown"
            )
            
    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        await status_msg.edit_text(f"❌ Er ging iets mis bij het verwerken van de foto: {str(e)}")



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
