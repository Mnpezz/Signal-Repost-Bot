# Signal Repost Bot

A lightweight, asynchronous Python bot designed to solve the Signal group member limit issue. It monitors multiple source Signal chat groups, filters incoming messages for posts containing both a photo/media and text caption, formats the caption with group/sender headers, and reposts them to dedicated spectator groups.

---

## 🌟 Architecture & Highlights

```
                          SOURCE GROUPS
                 ┌──────────────┼──────────────┐
                 ▼              ▼              ▼
           Curb Source    Housing Source   Event Source
                 │              │              │
                 └──────────────┼──────────────┘
                                ▼
                       signal-cli daemon
                   (JSON-RPC Socket / REST API)
                                │
                                ▼
                     ┌─────────────────────┐
                     │  Signal Repost Bot  │
                     │  (Multi-Route Engine)│
                     └──────────┬──────────┘
                                │
                 • Multi-Route Syndication (Curb Alerts, Housing, etc.)
                 • DM Contact Info (Include phone numbers for rent-seekers)
                 • Deduplication (SQLite persistent store)
                 • Filter: Photo + Text requirement, replies, whitelists
                                │
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
       [Curb Spectator Feed]        [Housing Spectator Feed]
```

- **Multi-Route Syndication**: A single bot account and process can handle multiple independent feeds (e.g. Curb Alerts -> Curb Spectator Group, Housing & Rentals -> Housing Spectator Group).
- **Direct Messaging (DM) Support**: Optionally include the original poster's phone number/handle in the repost header (`include_sender_number: true`) so spectator readers can tap to DM the original sender directly.
- **Two Engine Modes Supported**:
  - `jsonrpc_socket`: Connects directly to `signal-cli daemon` via TCP or Unix domain sockets.
  - `rest_api`: Connects to Dockerized `signal-cli-rest-api` via HTTP & WebSockets.
- **Filtering Engine**:
  - Filter by source group IDs (or wildcard `*` for all joined groups).
  - Require photo/media and non-empty text caption.
  - Media support: photos (JPEG, PNG, WebP), videos, animated GIFs.
  - Skip quote replies or bot self-messages.
- **Deduplication Engine**: SQLite store maintains message hashes to prevent double-posting across bot restarts.
- **Docker Ready**: `Dockerfile` and `docker-compose.yml` included for one-command deployment.

---

## 🚀 Quick Start Guide

### 1. Requirements

- Python 3.10+
- `signal-cli` installed locally OR `docker` & `docker-compose`.

### 2. Installation

Clone repository and install dependencies:

```bash
git clone https://github.com/your-username/signal-repost-bot.git
cd signal-repost-bot

# Create virtual environment and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### 3. Multi-Route Configuration Setup

Copy the example configuration file:

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml`:

```yaml
signal_account: "+15045555045"
client_mode: "jsonrpc_socket"
endpoint: "127.0.0.1:7583"

# Define your routes (Curb Alerts, Housing, etc.)
routes:
  - name: "Curb Alerts Feed"
    spectator_group_id: "your-curb-spectator-group-id"
    source_group_ids:
      - "your-curb-source-group-id"
    filters:
      require_photo: true
      require_text: true

  - name: "Housing & Rentals Feed"
    spectator_group_id: "your-housing-spectator-group-id"
    source_group_ids:
      - "your-housing-source-group-id"
    filters:
      require_photo: true
      require_text: true
    formatting:
      header_template: "🏠 [{group_name}] {sender_name}:\n"
      include_sender_number: true # Allows rent seekers to DM original sender!

storage:
  db_path: "data/bot_state.db"
```

---

## 🛠️ CLI Usage & Helpers

### Validate Configuration

```bash
signal-repost-bot -c config.yaml test-config
```

### Discover Joined Signal Group IDs

```bash
signal-repost-bot -c config.yaml list-groups
```

Output:
```text
Joined Signal Groups:
============================================================
 Group Name: Curb Alerts Chat
 Group ID:   UrFJfd5Co...
------------------------------------------------------------
 Group Name: Housing & Rentals
 Group ID:   gX8sF92bL...
------------------------------------------------------------
```

### Run the Bot Daemon

```bash
signal-repost-bot -c config.yaml run
```

---

## ☁️ Hosting Guide (Namecheap / Cloud / VPS)

### Can I host this on Namecheap?

- **Shared Hosting (cPanel)**: ❌ **No**. Standard Namecheap shared web hosting (cPanel) does not support long-running background daemons, socket listeners, or Docker containers.
- **Namecheap VPS (Virtual Private Server)**: ✅ **Yes!** Any Linux VPS (Ubuntu/Debian) on Namecheap, DigitalOcean, Hetzner, AWS, or a home Raspberry Pi is ideal.

### Deployment on a VPS using Docker:

1. SSH into your VPS:
   ```bash
   ssh root@your-vps-ip
   ```
2. Clone the bot and copy your `config.yaml`:
   ```bash
   git clone https://github.com/your-username/signal-repost-bot.git
   cd signal-repost-bot
   cp config.example.yaml config.yaml
   ```
3. Start the bot and `signal-cli-rest-api` stack in background mode:
   ```bash
   docker-compose up -d
   ```
4. Check logs:
   ```bash
   docker-compose logs -f signal-repost-bot
   ```

---

## 🧪 Running Unit Tests

Execute the full test suite with `pytest`:

```bash
pytest -v
```

---

## 📄 License

MIT License.
