import os
import shutil
import stat

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Check if environment is serverless (such as Vercel or AWS Lambda) or read-only
IS_SERVERLESS = bool(
    os.getenv("VERCEL")
    or os.getenv("AWS_LAMBDA_FUNCTION_NAME")
    or not os.access(BASE_DIR, os.W_OK)
)

if IS_SERVERLESS:
    TMP_DIR = "/tmp"
    UPLOAD_DIR = os.path.join(TMP_DIR, "uploads")
    SEED_ASSETS_DIR = os.path.join(BASE_DIR, "seed_assets")
    
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
    except Exception as e:
        print(f"[config] Warning: could not make UPLOAD_DIR: {e}")

    DB_PATH = os.path.join(TMP_DIR, "envi_connect.db")
    ORIG_DB = os.path.join(BASE_DIR, "envi_connect.db")

    # Always ensure a writable copy of the seeded DB exists in /tmp
    if os.path.exists(ORIG_DB):
        if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
            try:
                shutil.copyfile(ORIG_DB, DB_PATH)
                os.chmod(DB_PATH, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
            except Exception as e:
                print(f"[config] Warning: Failed to copy SQLite db to {DB_PATH}: {e}")

    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
else:
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    SEED_ASSETS_DIR = os.path.join(BASE_DIR, "seed_assets")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(SEED_ASSETS_DIR, exist_ok=True)
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'envi_connect.db')}")

SECRET_KEY = os.getenv("SECRET_KEY", "envi-connect-super-secret-jwt-key-2026-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days for demo ease
