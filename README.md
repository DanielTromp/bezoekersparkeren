# Bezoekersparkeren

Automate visitor parking registration on bezoek.parkeer.nl (Almere).

## Disclaimer

This tool is for personal use only. Use at your own risk.

## Configuration

```bash
cp config.example.yaml config.yaml
cp .env.example .env
# Edit .env with your credentials
```

## Deployment Options

### Docker Compose

```bash
# Run commands
docker compose run --rm app list
docker compose run --rm app register --plate AB-123-CD --hours 4

# Run Telegram bot as daemon
docker compose run -d --name parkeerbot --restart unless-stopped app bot
```

### Incus (OCI Container)

Deploy using the provided scripts:

```bash
# Setup Incus (first time only)
./scripts/setup-incus.sh

# Deploy container
./scripts/deploy-incus.sh
```

Manage the container:

```bash
incus list                                    # Status
incus exec parkeerbot -- journalctl -u parkeerbot -f  # Logs
incus exec parkeerbot -- systemctl restart parkeerbot # Restart
```

Configuration files are stored in `/opt/bezoekersparkeren/`.

## CLI Usage

```bash
bezoekersparkeren list                        # List active sessions
bezoekersparkeren register --plate AB-123-CD --hours 4
bezoekersparkeren register --plate AB-123-CD --all-day
bezoekersparkeren stop <SESSION_ID>
bezoekersparkeren balance
```

Add `--visible` to see the browser window for debugging.

## License

MIT
