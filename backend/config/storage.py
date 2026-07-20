from django.core.files.storage import Storage
from django.conf import settings
from supabase import create_client
import uuid
import os
from django.core.files.storage import FileSystemStorage

class SupabaseStorage(Storage):
    def __init__(self, bucket_name=None):
        self.bucket_name = bucket_name or getattr(settings, 'SUPABASE_BUCKET_CERTS', 'officialdocuments')
        self.supabase_url = getattr(settings, 'SUPABASE_URL', '')
        self.supabase_key = getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', '')
        self.fallback_storage = FileSystemStorage()
        if self.supabase_url and self.supabase_key:
            self.client = create_client(self.supabase_url, self.supabase_key)
        else:
            self.client = None

    def _save(self, name, content):
        if not self.client:
            return self.fallback_storage._save(name, content)
            
        ext = name.split('.')[-1] if '.' in name else 'bin'
        unique_name = f"uploads/{uuid.uuid4()}.{ext}"
        content_type = getattr(content, 'content_type', 'application/octet-stream')
        
        content.seek(0)
        file_bytes = content.read()
        
        try:
            self.client.storage.from_(self.bucket_name).upload(
                path=unique_name,
                file=file_bytes,
                file_options={"content-type": content_type}
            )
            return unique_name
        except Exception as e:
            print(f"SupabaseStorage: upload failed ({e}), falling back to local storage.")
            return self.fallback_storage._save(name, content)

    def exists(self, name):
        return False

    def url(self, name):
        if not self.client:
            return self.fallback_storage.url(name)
        return self.client.storage.from_(self.bucket_name).get_public_url(name)

    def size(self, name):
        return 0

    def _open(self, name, mode='rb'):
        # For simplicity, returning None, but standard behavior usually requires returning a File object.
        pass
