"""
db/client.py — Supabase client singleton with timeout configuration.
"""
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from config import settings

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        # Create client with timeout options (30 seconds)
        _client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY,
            options=ClientOptions(
                postgrest_client_timeout=30,
                persist_session=False,
                auto_refresh_token=False,
            ),
        )
    return _client
