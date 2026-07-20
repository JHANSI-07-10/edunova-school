import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    print("Checking portal_exam_schedule columns...")
    try:
        cursor.execute("ALTER TABLE public.portal_exam_schedule ADD COLUMN IF NOT EXISTS status varchar(50) NOT NULL DEFAULT 'Draft' CHECK (status IN ('Draft','Submitted','Published','Returned'));")
        cursor.execute("ALTER TABLE public.portal_exam_schedule ADD COLUMN IF NOT EXISTS room varchar(50);")
        print("Columns added successfully.")
    except Exception as e:
        print(f"Error: {e}")
