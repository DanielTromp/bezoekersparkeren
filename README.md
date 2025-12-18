# Bezoekersparkeren

Automate visitor parking registration on bezoek.parkeer.nl (Almere).

## ⚠️ Disclaimer

This tool is for personal use only. Use at your own risk. The author is not responsible for any misuse or violations of terms of service.

## Installation

```bash
# Clone repository
git clone https://github.com/danieltromp/bezoekersparkeren.git
cd bezoekersparkeren

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install package
pip install -e .

# Install Playwright browsers
playwright install chromium
playwright install-deps chromium
```

## Configuration

1. Copy the example config:
   ```bash
   cp config.example.yaml config.yaml
   cp .env.example .env
   ```

2. Edit `.env` with your credentials:
   ```
   PARKEER_EMAIL=your@email.com
   PARKEER_PASSWORD=your_password
   ```

## Running with Docker

You can run the application using Docker Compose without installing Python or dependencies locally.

1. Make sure you have configured `config.yaml` and `.env` as described above.

2. Build and run commands:

   ```bash
   # Show help
   docker compose run --rm app --help

   # List sessions
   docker compose run --rm app list

   # Register a visitor
   docker compose run --rm app register --plate AB-123-CD --hours 4
   ```

Note: The `sessions.json` file is mounted, so session data persists between runs.

### Running the Telegram Bot

To run the Telegram bot as a background service (daemon):

```bash
docker compose run -d --name parkeerbot --restart unless-stopped app bot
```

- `-d`: Run in detached mode (background)
- `--name parkeerbot`: Give the container a recognizable name
- `--restart unless-stopped`: Automatically restart if it crashes or Docker restarts
- `bot`: The command to start the bot

To stop the bot:
```bash
docker stop parkeerbot
docker rm parkeerbot
```

### Deploying with Portainer

You can deploy this application as a Stack in Portainer.

1.  **Go to Stacks** and click **"Add stack"**.
2.  Select **"Repository"**.
3.  **Name:** `bezoekersparkeren` (or your preferred name).
4.  **Repository URL:** `https://github.com/danieltromp/bezoekersparkeren.git`
5.  **Compose path:** `docker-compose.yml`
6.  **Environment variables:** Add the variables here (e.g., `PARKEER_EMAIL`, `PARKEER_PASSWORD`, `PARKEER_TELEGRAM_BOT_TOKEN`).

**Important Note on Volumes:**
The default `docker-compose.yml` expects `config.yaml` and `sessions.json` to be in the same directory. In Portainer, you likely need to modify the volume mappings to point to absolute paths on your server where these files reside, or use Docker volumes.

Example modification for Portainer (you can edit the Compose file in Portainer):
```yaml
volumes:
  - /path/to/host/config.yaml:/app/config.yaml
  - /path/to/host/sessions.json:/app/sessions.json
```

## Usage


The tool uses a browser automation engine. By default it runs in headless mode. 
Add `--visible` to any command to see the browser window (useful for debugging).

### Commands

#### 1. List Active Sessions
Shows current and future parking sessions with their unique IDs.

```bash
bezoekersparkeren list
# With visible browser
bezoekersparkeren --visible list
```

#### 2. Register Visitor
Register a parking session. You can specify duration, specific times, or all-day parking.

**Options:**
- `--plate` (Required): License plate number
- `--hours` / `--minutes`: Duration of parking
- `--until`: Specific end time (HH:MM)
- `--start-time`: Specific start time (HH:MM) - defaults to now
- `--date`: Date (DD-MM-YYYY) or "tomorrow" - defaults to today
- `--all-day`: Automatically calculate end time based on zone rules (e.g. 24:00)
- `--days`: Register for multiple consecutive days (default: 1)

**Examples:**
```bash
# Simple registration for 4 hours
bezoekersparkeren register --plate "AB-123-CD" --hours 4

# Park all day tomorrow
bezoekersparkeren register --plate "AB-123-CD" --date tomorrow --all-day

# Park for a specific time range
bezoekersparkeren register --plate "AB-123-CD" --start-time 14:00 --until 16:30
```

#### 3. Stop Session
Stop a specific parking session using the ID from the `list` command.

```bash
bezoekersparkeren stop <SESSION_ID>
```

#### 4. Check Balance
View current credit balance.

```bash
bezoekersparkeren balance
```

## License

MIT
