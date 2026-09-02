"""CLI entry point for signal-repost-bot."""

import sys
import asyncio
import argparse
import logging
from signal_repost_bot.config import AppConfig
from signal_repost_bot.bot import SignalRepostBot
from signal_repost_bot.client import create_signal_client


def setup_logging(log_level: str):
    """Configure logging format and level."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def run_bot(config_path: str):
    """Run the main bot process."""
    config = AppConfig.load(config_path)
    setup_logging(config.log_level)

    bot = SignalRepostBot(config)
    try:
        await bot.start()
    except ConnectionError as e:
        print(f"\n❌ Connection Error:\n{e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        logger = logging.getLogger(__name__)
        logger.info("Received exit signal. Shutting down...")
    finally:
        await bot.stop()


async def list_groups(config_path: str):
    """Utility command to list joined Signal groups and their IDs."""
    config = AppConfig.load(config_path)
    setup_logging(config.log_level)
    print(f"Connecting to Signal via {config.client_mode} at {config.endpoint}...")

    client = create_signal_client(
        client_mode=config.client_mode,
        account=config.signal_account,
        endpoint=config.endpoint,
    )
    try:
        await client.connect()
        groups = await client.list_groups()
        print("\nJoined Signal Groups:")
        print("=" * 60)
        for g in groups:
            name = g.get("name") or g.get("title") or "Unnamed Group"
            gid = g.get("id") or g.get("groupId") or "Unknown ID"
            print(f" Group Name: {name}")
            print(f" Group ID:   {gid}")
            print("-" * 60)
    except ConnectionError as e:
        print(f"\n❌ Connection Error:\n{e}", file=sys.stderr)
        sys.exit(1)
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass


def test_config(config_path: str):
    """Utility command to validate and print config settings."""
    try:
        config = AppConfig.load(config_path)
        print("Configuration successfully loaded!")
        print("=" * 60)
        print(f" Signal Account:     {config.signal_account}")
        print(f" Client Mode:        {config.client_mode}")
        print(f" Endpoint:           {config.endpoint}")
        print(f" Database Path:      {config.storage.db_path}")
        print(f" Active Routes:      {len(config.routes)} route(s) configured")
        print("=" * 60)
        for idx, route in enumerate(config.routes, 1):
            print(f" • Route {idx}: '{route.name}'")
            print(f"   Monitored Sources: {route.source_group_ids}")
            print(f"   Target Spectator:  {route.spectator_group_id}")
            print(f"   Require Photo:     {route.filters.require_photo}")
            print(f"   Require Text:      {route.filters.require_text}")
            print(f"   Include DM Info:   {route.formatting.include_sender_number}")
            print("-" * 60)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)


def cli_entrypoint():
    """Main CLI command parser."""
    parser = argparse.ArgumentParser(
        prog="signal-repost-bot",
        description="Signal Repost Bot - Syndicate media+text posts to a spectator group.",
    )
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="Path to YAML configuration file (default: config.yaml)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: run
    subparsers.add_parser("run", help="Start the Signal Repost Bot daemon")

    # Command: list-groups
    subparsers.add_parser("list-groups", help="List all joined Signal groups and their IDs")

    # Command: test-config
    subparsers.add_parser("test-config", help="Validate configuration settings")

    args = parser.parse_args()

    # Default command is 'run' if not specified
    cmd = args.command or "run"

    if cmd == "test-config":
        test_config(args.config)
    elif cmd == "list-groups":
        asyncio.run(list_groups(args.config))
    elif cmd == "run":
        asyncio.run(run_bot(args.config))


if __name__ == "__main__":
    cli_entrypoint()
