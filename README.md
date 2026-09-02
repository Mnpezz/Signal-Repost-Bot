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
                 • Smart Tap-to-DM Links (https://signal.me/#u/username or #p/+1...)
                 • Clean Header Sanitization (replaces raw base64 hashes with route names)
                 • Deduplication (SQLite persistent store)
                 • Filter: Photo + Text requirement, replies, whitelists
                                │
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
       [Curb Spectator Feed]        [Housing Spectator Feed]
```

- **Multi-Route Syndication**: A single bot account and process can handle multiple independent feeds (e.g. Curb Alerts -> Curb Spectator Group, Housing & Rentals -> Housing Spectator Group).
- **Smart Tap-to-DM Direct Messaging**: Automatically generates clickable Signal deep links (`https://signal.me/#u/username` or `https://signal.me/#p/+15551234567`) so spectators in the group can tap to DM original senders directly.
- **Friendly Group Header Sanitization**: Replaces raw base64 group ID strings (e.g. `UrFJfd5Co...`) with your clean, custom route names (e.g. `[Curb Alerts Feed]`).
- **Multi-Attachment Resolver**: Automatically resolves and packages multi-photo posts, GIFs, and videos directly from `signal-cli` data directories with a 64MB stream buffer limit.
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
git clone https://github.com/Mnpezz/Signal-Repost-Bot.git
cd Signal-Repost-Bot

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
signal_account: "+16094121314"
client_mode: "jsonrpc_socket"
endpoint: "127.0.0.1:7583"

# Define your routes (Curb Alerts, Housing, etc.)
routes:
  - name: "Curb Alerts Feed"
    spectator_group_id: "ugFqM3PNsm05ljZalNzInz36s4FOTJIxqts1SLtMkuE="
    source_group_ids:
      - "UrFJfd5CoAF5I/SRDj7X0usO0fd10b3khu8mNisDwW8="
    filters:
      require_photo: true
      require_text: true
    formatting:
      header_template: "📸 [{group_name}] {sender_name}:\n"
      include_sender_number: true
      include_dm_link: true

  - name: "Housing & Rentals Feed"
    spectator_group_id: "GOGt/D8P2Uqlg2KFxlQSbruo5uoa14bu6NYrbH68R+o="
    source_group_ids:
      - "dgabYJYlDvQonZ+kHYGQS8eIAbRDEel0teU3Bz0Ft9U="
    filters:
      require_photo: true
      require_text: true
    formatting:
      header_template: "🏠 [{group_name}] {sender_name}:\n"
      include_sender_number: true
      include_dm_link: true # Tap-to-DM links for rent seekers!

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
 Group ID:   dgabYJYlD...
------------------------------------------------------------
```

### Run the Bot Daemon

```bash
signal-repost-bot -c config.yaml run
```

---

## 💬 Tap-to-DM Link Details

When `include_dm_link: true` is enabled, the bot generates clickable Signal direct message links for spectators:

- **Username Links**: If the sender has a Signal Username (e.g. `@alice.01`), the link is formatted as `https://signal.me/#u/alice.01`.
- **Phone Links**: If the sender shares their phone number, the link is formatted as `https://signal.me/#p/+15551234567`.
- **Privacy Protection**: If the sender hides their phone number and has no username, raw invalid UUID links (`sgnl://`) are safely omitted to keep the post header clean.

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
   git clone https://github.com/Mnpezz/Signal-Repost-Bot.git
   cd Signal-Repost-Bot
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
