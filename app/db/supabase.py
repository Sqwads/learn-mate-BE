import os
from supabase import create_client, Client
from app.core.config import settings

def create_supabase_client() -> Client:
    """
    Create and validate Supabase client connection.

    Returns:
        Client: Configured Supabase client

    Raises:
        RuntimeError: If connection validation fails
    """
    try:
        # Use service role key for database operations to bypass RLS issues
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

        # Validate connection by attempting a simple query
        # This will raise an exception if the connection is invalid
        test_response = supabase.table('profiles').select('id').limit(1).execute()
        print("✅ Supabase connection validated successfully")

        return supabase

    except Exception as e:
        error_msg = f"Failed to connect to Supabase: {str(e)}"
        print(f"❌ {error_msg}")
        raise RuntimeError(error_msg)

# Create and validate the Supabase client
supabase: Client = create_supabase_client()
