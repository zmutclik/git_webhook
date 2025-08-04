import os
import secrets
import string
import logging
import hmac
import hashlib
import subprocess
from datetime import datetime
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"./logs/{datetime.now().strftime('%Y-%m')}_webhook.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def get_secret(secret_name):
    try:
        with open(f"/app/secrets/{secret_name}", "r") as secret_file:
            return secret_file.read().strip()
    except IOError:
        return os.environ.get(secret_name)


def ensure_webhook_secret():
    """Buat file webhook secret jika belum ada"""

    secret_dir = "./secrets"
    secret_file = os.path.join(secret_dir, "webhook_secret")

    # Buat direktori secrets jika belum ada
    if not os.path.exists(secret_dir):
        try:
            os.makedirs(secret_dir, exist_ok=True)
            logger.info(f"Direktori secrets dibuat: {secret_dir}")
        except Exception as e:
            logger.warning(f"Gagal membuat direktori secrets: {str(e)}")
            return

    # Cek apakah file webhook_secret sudah ada
    if not os.path.exists(secret_file):
        try:
            # Generate random string (32 karakter)
            alphabet = string.ascii_letters + string.digits
            random_secret = "".join(secrets.choice(alphabet) for _ in range(32))

            # Tulis ke file
            with open(secret_file, "w") as f:
                f.write(random_secret)

            # Set permission file (readonly untuk user)
            os.chmod(secret_file, 0o600)

            logger.info(f"File webhook secret dibuat: {secret_file}")
        except Exception as e:
            logger.warning(f"Gagal membuat file webhook secret: {str(e)}")
    else:
        logger.info(f"File webhook secret sudah ada: {secret_file}")


def verify_signature(payload_body: bytes, signature_header: str, secret: str) -> bool:
    """Verifikasi signature dari GitHub webhook"""
    if not signature_header:
        return False

    hash_object = hmac.new(secret.encode("utf-8"), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()

    return hmac.compare_digest(expected_signature, signature_header)


async def execute_command(command: str, cwd: Optional[str] = None) -> tuple[bool, str]:
    """Eksekusi command dengan error handling"""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True, timeout=300)  # 5 menit timeout

        if result.returncode == 0:
            logger.info(f"Command berhasil: {command}")
            logger.info(f"Output: {result.stdout}")
            return True, result.stdout
        else:
            logger.error(f"Command gagal: {command}")
            logger.error(f"Error: {result.stderr}")
            return False, result.stderr

    except subprocess.TimeoutExpired:
        logger.error(f"Command timeout: {command}")
        return False, "Command timeout"
    except Exception as e:
        logger.error(f"Exception saat eksekusi command: {str(e)}")
        return False, str(e)


async def pull_repository(CONFIG) -> tuple[bool, str]:
    """Pull perubahan terbaru dari repository"""
    logger.info("Memulai git pull...")

    # Cek apakah direktori repository ada
    if not os.path.exists(CONFIG["REPO_PATH"]):
        logger.error(f"Repository path tidak ditemukan: {CONFIG['REPO_PATH']}")
        return False, "Repository path tidak ditemukan"

    # Git pull
    pull_command = f"git pull origin {CONFIG['BRANCH']}"
    success, output = await execute_command(pull_command, cwd=CONFIG["REPO_PATH"])

    if not success:
        return False, f"Git pull gagal: {output}"

    # Jalankan post-deploy script jika ada
    if CONFIG["POST_DEPLOY_SCRIPT"]:
        logger.info("Menjalankan post-deploy script...")
        script_success, script_output = await execute_command(CONFIG["POST_DEPLOY_SCRIPT"], cwd=CONFIG["REPO_PATH"])

        if not script_success:
            logger.warning(f"Post-deploy script gagal: {script_output}")

    return True, output


async def process_webhook_background(CONFIG, payload: dict, event_type: str):
    """Background task untuk memproses webhook"""
    logger.info(f"Background processing webhook: {event_type}")

    if event_type == "push":
        ref = payload.get("ref", "")
        target_ref = f"refs/heads/{CONFIG['BRANCH']}"

        if ref == target_ref:
            logger.info(f"Push ke branch {CONFIG['BRANCH']} terdeteksi")
            success, message = await pull_repository(CONFIG)

            if success:
                logger.info("Background webhook berhasil diproses")
            else:
                logger.error("Background webhook gagal diproses")
