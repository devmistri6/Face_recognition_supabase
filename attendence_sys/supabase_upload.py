import uuid
import mimetypes
from supabase import create_client
from supabase.lib.client_options import ClientOptions

SUPABASE_URL = "https://lcygbuvqtahekoghnpmx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxjeWdidXZxdGFoZWtvZ2hucG14Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NDU0MDE0NiwiZXhwIjoyMDYwMTE2MTQ2fQ.S6DR83R-Uw4spJEXVpRnlG6dDGxeGF91PBha90S12Io"
SUPABASE_BUCKET = "userprofile"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY, options=ClientOptions())

def upload_to_supabase(file, folder: str, filename: str = None) -> str:
    """
    Uploads a file to Supabase Storage and returns the relative path to the file.
    If `filename` is not provided, a UUID-based filename is used.
    """

    original_name = file.name
    ext = original_name.split('.')[-1]
    final_filename = filename or f"{uuid.uuid4()}.{ext}"
    supabase_path = f"{folder}/{final_filename}"

    content_type, _ = mimetypes.guess_type(original_name)
    file_content = file.read()

    # Delete if it already exists to avoid conflict
    try:
        supabase.storage.from_(SUPABASE_BUCKET).remove([supabase_path])
    except Exception:
        pass  # Ignore if file does not exist

    try:
        supabase.storage.from_(SUPABASE_BUCKET).upload(
            supabase_path,
            file_content,
            {"content-type": content_type or "application/octet-stream"}
        )
        return supabase_path
    except Exception as e:
        print(f"Upload to Supabase failed: {e}")
        return ""
