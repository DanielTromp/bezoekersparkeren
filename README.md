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
