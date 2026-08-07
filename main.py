import os
from dotenv import load_dotenv
from supabase import create_client, Client

# 1. Muat variabel lingkungan dari file .env
load_dotenv()

# 2. Ambil nilai dari file .env menggunakan os.environ
url: str = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
key: str = os.environ.get("NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY")

# Pastikan variabel tidak kosong sebelum membuat client
if not url or not key:
    raise ValueError("Pastikan NEXT_PUBLIC_SUPABASE_URL dan NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY sudah diisi di file .env")

# 3. Inisialisasi klien Supabase
supabase: Client = create_client(url, key)

# 4. Ambil data dari tabel
try:
    response = supabase.table("members").select("*").execute()
    data = response.data

    if not data:
        print("Tidak ada data pada tabel 'members'.")
    else:
        print(f"Total {len(data)} baris data dari tabel 'members':\n")
        for i, row in enumerate(data, start=1):
            print(f"---------- Data ke-{i} ----------")
            for key, value in row.items():
                print(f"  {key}: {value}")
            print()
except Exception as e:
    print(f"Terjadi kesalahan saat mengambil data: {e}")
