# Bezoekersparkeren

Telegram bot for automated visitor parking registration on bezoek.parkeer.nl.

## Container Image

```
ghcr.io/danieltromp/bezoekersparkeren:latest
```

Multi-platform: `linux/amd64`, `linux/arm64`

## Configuration

Create configuration files:

```bash
# config.yaml - see config.example.yaml
cp config.example.yaml config.yaml

# .env - credentials
cat > .env << 'EOF'
PARKEER_EMAIL=your@email.com
PARKEER_PASSWORD=your_password
PARKEER_TELEGRAM_BOT_TOKEN=your_bot_token
PARKEER_TELEGRAM_ALLOWED_USERS=123456789
PARKEER_OPENROUTER_API_KEY=optional_api_key
EOF
```

## Deployment

### Docker Compose (recommended)

```bash
# Start bot as daemon
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

### Docker

```bash
# Run bot
docker run -d --name parkeerbot \
  --env-file .env \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/sessions.json:/app/sessions.json \
  ghcr.io/danieltromp/bezoekersparkeren:latest bot

# Run CLI commands
docker run --rm \
  --env-file .env \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  ghcr.io/danieltromp/bezoekersparkeren:latest list
```

### Podman

```bash
# Run bot
podman run -d --name parkeerbot \
  --env-file .env \
  -v ./config.yaml:/app/config.yaml:ro \
  -v ./sessions.json:/app/sessions.json \
  ghcr.io/danieltromp/bezoekersparkeren:latest bot

# With systemd auto-start
podman generate systemd --name parkeerbot --new --files
sudo mv container-parkeerbot.service /etc/systemd/system/parkeerbot.service
sudo systemctl daemon-reload
sudo systemctl enable --now parkeerbot
```

## CLI Commands

```bash
bezoekersparkeren list                        # List active sessions
bezoekersparkeren register --plate AB-123-CD --hours 4
bezoekersparkeren register --plate AB-123-CD --all-day
bezoekersparkeren stop <SESSION_ID>
bezoekersparkeren balance
bezoekersparkeren bot                         # Start Telegram bot
```

## Development

```bash
# Build locally
docker build -t bezoekersparkeren .

# Or with compose
docker compose build
```

## License

MIT
