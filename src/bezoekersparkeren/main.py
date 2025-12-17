import asyncio
import click
import logging
import sys
from .client import ParkeerClient
from .config import Config

# Helper for unified logging and console output
def log_echo(message, nl=True):
    """Log message to file and echo to console"""
    logging.info(message.strip())
    click.echo(message, nl=nl)

def setup_logging(config):
    """
    Setup logging to file and console.
    File: INFO level, persistent
    Console: ERROR/WARNING only (to keep it clean), or let click handle standard output separately.
    """
    log_config = config.logging
    log_file = log_config.file or "bezoekersparkeren.log"
    log_level = getattr(logging, log_config.level.upper(), logging.INFO)
    
    # Root logger configuration
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # clear existing handlers
    logger.handlers = []
    
    # File Handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console Handler (Optional: if we want to see logs in console too, but usually we use click.echo for user output)
    # For now, we rely on log_echo for user facing info, and internal logs go to file only.
    # If debug mode was needed, we could add a console handler.

def run_async(func):
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper

@click.group()
@click.option('--visible', is_flag=True, help='Run browser in visible mode (not headless)')
@click.pass_context
def cli(ctx, visible):
    """Bezoekersparkeren automation tool"""
    ctx.ensure_object(dict)
    ctx.obj['visible'] = visible
    
    # Load config and setup logging early
    config = Config.load()
    setup_logging(config)
    
    # Log the command execution
    logging.info(f"Command executed: {' '.join(sys.argv)}")

def get_client(ctx):
    from .config import Config
    config = Config.load()
    if ctx.obj.get('visible'):
        config.browser.headless = False
    return ParkeerClient(config)

from datetime import datetime, timedelta
from .utils.time_utils import TimeUtils

@cli.command()
@click.option('--plate', required=True, help='License plate number')
@click.option('--hours', type=int, help='Duration in hours')
@click.option('--minutes', type=int, help='Duration in minutes')
@click.option('--until', help='End time (HH:MM)')
@click.option('--all-day', is_flag=True, help='Park all day (until end of paid period)')
@click.option('--date', help='Date to park (DD-MM-YYYY) or "tomorrow"')
@click.option('--days', type=int, default=1, help='Number of consecutive days')
@click.option('--start-time', help='Start time (HH:MM)')
@click.pass_context
def register(ctx, plate, hours, minutes, until, all_day, date, days, start_time):
    """Register a visitor with advanced scheduling"""
    async def _register():
        async with get_client(ctx) as client:
            if not await client.login():
                log_echo("Login failed")
                return

            # Determine start date
            base_date = datetime.now()
            if date:
                if date.lower() == 'tomorrow':
                    base_date = base_date + timedelta(days=1)
                else:
                    try:
                        base_date = datetime.strptime(date, "%d-%m-%Y")
                    except ValueError:
                        log_echo("Invalid date format. Use DD-MM-YYYY")
                        return

            # Loop for multiple days
            for i in range(days):
                current_date = base_date + timedelta(days=i)
                current_date_str = current_date.strftime("%d-%m-%Y")
                
                # Determine Zone (default to first one config)
                zone = client.config.zones[0] if client.config.zones else None
                
                # Determine Start Time
                s_time = start_time
                if not s_time:
                    if i == 0 and not date: 
                        # Today, no specific date: start now
                        s_time = datetime.now().strftime("%H:%M")
                    else:
                        # Future date: default to zone start time? or 00:00?
                        # User constraint: "outside paid time... select first possible moment"
                        # If we have a zone rule, use its start time.
                        if zone:
                            rule = TimeUtils.get_rule_for_day(zone, current_date)
                            if rule:
                                s_time = rule.start_time
                            else:
                                s_time = "00:00" # fallback
                        else:
                            s_time = "00:00"

                # Determine End Time / Duration
                e_time = until
                # If all-day, calculate based on zone
                if all_day and zone:
                    e_time = TimeUtils.get_end_time_for_all_day(zone, current_date)
                
                # If neither until nor all-day, maybe hours/minutes logic applies
                # We calculate 'until' explicitly to pass to client if possible, 
                # or pass hours/minutes if we want client to handle it (but client handling is weak now)
                # Better to calculate e_time here.
                if not e_time and not (hours or minutes):
                     # If nothing specified, maybe default duration? 
                     pass

                if hours or minutes:
                     # Calculate e_time from s_time
                     st_dt = datetime.strptime(s_time, "%H:%M")
                     delta = timedelta(hours=hours or 0, minutes=minutes or 0)
                     et_dt = st_dt + delta
                     e_time = et_dt.strftime("%H:%M")

                log_echo(f"Registering {plate} for {current_date_str} {s_time} - {e_time or '...'}")
                
                session = await client.register_visitor(
                    plate=plate,
                    start_date=current_date_str,
                    start_time=s_time,
                    end_date=current_date_str, # User said: "einddatum should always be the same as the startdatum"
                    end_time=e_time,
                    hours=hours,
                    minutes=minutes
                )
                
                # Generate ID for new session (consistent with client list parsing)
                if not session.id and session.start_time:
                     import hashlib
                     id_base = f"{session.plate}-{session.start_time.isoformat()}"
                     session.id = hashlib.md5(id_base.encode()).hexdigest()[:8]

                # Update local state
                from .utils.session_manager import SessionManager
                SessionManager().add_session(session)
                
                log_echo(f"  Success: {session.plate} (ID: {session.id})")

    asyncio.run(_register())

@cli.command()
@click.argument('session_id')
@click.pass_context
def stop(ctx, session_id):
    """Stop a parking session by ID"""
    
    from .utils.session_manager import SessionManager
    
    async def _stop():
        # Load session from local state
        manager = SessionManager()
        session = manager.get_session(session_id)
        
        if not session:
            log_echo(f"Session with ID {session_id} not found in local history. Run 'list' to refresh.")
            return

        async with get_client(ctx) as client:
            if await client.login():
                if await client.stop_session(session):
                    # Remove from local state
                    manager.remove_session(session_id)
                    log_echo(f"Stopped session {session_id} ({session.plate})")
                else:
                    log_echo(f"Failed to stop session {session_id}")
            else:
                log_echo("Login failed")

    asyncio.run(_stop())

@cli.command()
@click.pass_context
def list(ctx):
    """List active sessions"""
    async def _list():
        from .utils.session_manager import SessionManager
        
        async with get_client(ctx) as client:
            if await client.login():
                sessions = await client.get_active_sessions()
                
                # Save to local state
                manager = SessionManager()
                manager.save_sessions(sessions)
                
                if not sessions:
                    log_echo("No active sessions")
                    return
                
                # Print table
                # Header
                log_echo(f"{'ID':<10} {'PLATE':<10} {'START':<20} {'END':<20}")
                log_echo("-" * 60)
                
                for s in sessions:
                    start_str = s.start_time.strftime("%d-%m %H:%M") if s.start_time else "?"
                    end_str = s.end_time.strftime("%d-%m %H:%M") if s.end_time else "?"
                    log_echo(f"{s.id or '?':<10} {s.plate:<10} {start_str:<20} {end_str:<20}")
            else:
                log_echo("Login failed")

    asyncio.run(_list())

@cli.command()
@click.pass_context
def balance(ctx):
    """Check balance"""
    async def _balance():
        async with get_client(ctx) as client:
            if await client.login():
                bal = await client.get_balance()
                log_echo(f"Balance: {bal.amount} {bal.currency}")
            else:
                log_echo("Login failed")

    asyncio.run(_balance())

@cli.command()
def bot():
    """Start de Telegram bot."""
    from bezoekersparkeren.bot.telegram_bot import main as bot_main
    bot_main()

if __name__ == '__main__':
    cli()

