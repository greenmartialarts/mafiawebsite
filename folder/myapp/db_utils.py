from django.conf import settings
from supabase import Client

def get_supabase() -> Client:
    """Get the Supabase client instance."""
    return settings.supabase

def sync_to_supabase(model_instance, table_name):
    """
    Sync a Django model instance to Supabase.
    Use this in model save/delete methods when needed.
    """
    supabase = get_supabase()
    data = {
        'id': model_instance.id,
        # Add other fields as needed
        'created_at': model_instance.created_at.isoformat() if hasattr(model_instance, 'created_at') else None,
        'updated_at': model_instance.updated_at.isoformat() if hasattr(model_instance, 'updated_at') else None,
    }
    
    try:
        supabase.table(table_name).upsert(data).execute()
    except Exception as e:
        print(f"Error syncing to Supabase: {e}") 