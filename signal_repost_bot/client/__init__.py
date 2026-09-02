"""Signal client package factory."""

from signal_repost_bot.client.base import BaseSignalClient
from signal_repost_bot.client.jsonrpc_client import JsonRpcSignalClient
from signal_repost_bot.client.rest_client import RestApiSignalClient


def create_signal_client(client_mode: str, account: str, endpoint: str) -> BaseSignalClient:
    """
    Factory function to instantiate Signal client based on configuration.

    Args:
        client_mode: "jsonrpc_socket" or "rest_api"
        account: Phone number of the bot account
        endpoint: Socket address or HTTP URL

    Returns:
        BaseSignalClient instance
    """
    mode = client_mode.lower()
    if mode in ("jsonrpc_socket", "socket", "jsonrpc"):
        return JsonRpcSignalClient(account=account, endpoint=endpoint)
    elif mode in ("rest_api", "rest", "http"):
        return RestApiSignalClient(account=account, endpoint=endpoint)
    else:
        raise ValueError(f"Unsupported client_mode: {client_mode}. Supported: 'jsonrpc_socket', 'rest_api'")
