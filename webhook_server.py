import os
import json
import hmac
import hashlib
import subprocess
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any
from pydantic import BaseModel
from fastapi import FastAPI, Request, HTTPException, Header, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn

BRANCH_NAME = os.environ.get('BRANCH', 'main') 
def get_secret(secret_name):
    try:
        # Docker secrets disimpan di /run/secrets/<secret_name>
        with open(f'/run/secrets/{secret_name}', 'r') as secret_file:
            return secret_file.read().strip()
    except IOError:
        # Fallback ke environment variable untuk pengembangan lokal
        return os.environ.get(secret_name)
    
# Konfigurasi
CONFIG = {
    "PORT": 8000,
    "HOST": "0.0.0.0",
    "SECRET_TOKEN": get_secret("webhook_secret") or "your-secret-token-here",
    "REPO_PATH": "./repository",  # Path ke repository lokal
    "BRANCH": BRANCH_NAME,
    "POST_DEPLOY_SCRIPT": None,  # Script yang dijalankan setelah pull (opsional)
}

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


# Pydantic models
class WebhookResponse(BaseModel):
    status: str
    message: str
    timestamp: str
    output: Optional[str] = None
    error: Optional[str] = None


class StatusResponse(BaseModel):
    status: str
    timestamp: str
    config: Dict[str, Any]


class ManualPullResponse(BaseModel):
    status: str
    message: str
    output: Optional[str] = None
    error: Optional[str] = None


# FastAPI app
app = FastAPI(title="Git Webhook Server", description="Aplikasi webhook untuk otomatis pull git repository", version="1.0.0")


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


async def pull_repository() -> tuple[bool, str]:
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


async def process_webhook_background(payload: dict, event_type: str):
    """Background task untuk memproses webhook"""
    logger.info(f"Background processing webhook: {event_type}")

    if event_type == "push":
        ref = payload.get("ref", "")
        target_ref = f"refs/heads/{CONFIG['BRANCH']}"

        if ref == target_ref:
            logger.info(f"Push ke branch {CONFIG['BRANCH']} terdeteksi")
            success, message = await pull_repository()

            if success:
                logger.info("Background webhook berhasil diproses")
            else:
                logger.error("Background webhook gagal diproses")


@app.post("/webhook", response_model=WebhookResponse)
async def webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
    x_gitlab_event: Optional[str] = Header(None),
    x_gitea_event: Optional[str] = Header(None),
):
    """Endpoint webhook untuk menerima notifikasi dari git service"""

    # Log request
    client_ip = request.client.host
    logger.info(f"Webhook diterima dari IP: {client_ip}")

    # Baca request body
    body = await request.body()

    # Verifikasi signature (untuk GitHub)
    if CONFIG["SECRET_TOKEN"] and x_hub_signature_256:
        if not verify_signature(body, x_hub_signature_256, CONFIG["SECRET_TOKEN"]):
            logger.warning("Signature verification gagal")
            raise HTTPException(status_code=401, detail="Unauthorized")

    # Parse payload
    try:
        payload = await request.json()
        if not payload:
            logger.error("Payload kosong atau invalid")
            raise HTTPException(status_code=400, detail="Invalid payload")

    except Exception as e:
        logger.error(f"Error parsing JSON: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Log event info
    event_type = x_github_event or x_gitlab_event or x_gitea_event or "unknown"
    logger.info(f"Event type: {event_type}")

    # Hanya proses push events
    if "push" in event_type.lower():
        ref = payload.get("ref", "")
        target_ref = f"refs/heads/{CONFIG['BRANCH']}"

        if ref == target_ref:
            logger.info(f"Push ke branch {CONFIG['BRANCH']} terdeteksi")

            # Informasi commit
            commits = payload.get("commits", [])
            if commits:
                latest_commit = commits[-1]
                logger.info(f"Latest commit: {latest_commit.get('id', '')[:8]} - {latest_commit.get('message', '')}")

            # Pull repository (sync untuk response cepat)
            success, message = await pull_repository()

            # Juga jalankan background task untuk processing tambahan
            background_tasks.add_task(process_webhook_background, payload, event_type)

            if success:
                return WebhookResponse(status="success", message="Repository berhasil diupdate", timestamp=datetime.now().isoformat(), output=message)
            else:
                logger.error("Webhook gagal diproses")
                raise HTTPException(
                    status_code=500,
                    detail=WebhookResponse(
                        status="error", message="Gagal update repository", error=message, timestamp=datetime.now().isoformat()
                    ).dict(),
                )
        else:
            logger.info(f"Push ke branch lain ({ref}), diabaikan")
            return WebhookResponse(status="ignored", message="Branch diabaikan", timestamp=datetime.now().isoformat())

    elif event_type == "ping":
        logger.info("Ping event diterima")
        return WebhookResponse(status="success", message="Pong! Webhook aktif", timestamp=datetime.now().isoformat())

    else:
        logger.info(f"Event {event_type} diabaikan")
        return WebhookResponse(status="ignored", message=f"Event {event_type} diabaikan", timestamp=datetime.now().isoformat())


@app.get("/status", response_model=StatusResponse)
async def status():
    """Endpoint untuk cek status aplikasi"""
    return StatusResponse(
        status="running",
        timestamp=datetime.now().isoformat(),
        config={"repo_path": CONFIG["REPO_PATH"], "branch": CONFIG["BRANCH"], "has_secret": bool(CONFIG["SECRET_TOKEN"]), "port": CONFIG["PORT"]},
    )


@app.post("/manual-pull", response_model=ManualPullResponse)
async def manual_pull():
    """Endpoint untuk manual pull (untuk testing)"""
    logger.info("Manual pull dipicu")

    success, message = await pull_repository()

    if success:
        return ManualPullResponse(status="success", message="Manual pull berhasil", output=message)
    else:
        raise HTTPException(status_code=500, detail=ManualPullResponse(status="error", message="Manual pull gagal", error=message).dict())


@app.get("/")
async def root():
    """Root endpoint dengan info dasar"""
    return {
        "app": "Git Webhook Server",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {"webhook": "/webhook (POST)", "status": "/status (GET)", "manual_pull": "/manual-pull (POST)", "docs": "/docs (GET)"},
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    repo_exists = os.path.exists(CONFIG["REPO_PATH"])

    return {
        "status": "healthy" if repo_exists else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {"repository_exists": repo_exists, "config_valid": bool(CONFIG["REPO_PATH"] and CONFIG["BRANCH"])},
    }


if __name__ == "__main__":
    # Validasi konfigurasi
    if not os.path.exists(CONFIG["REPO_PATH"]):
        logger.error(f"Repository path tidak ditemukan: {CONFIG['REPO_PATH']}")
        logger.error("Silakan sesuaikan CONFIG['REPO_PATH'] dengan path repository Anda")
        exit(1)

    logger.info("=== Git Webhook Server Starting ===")
    logger.info(f"Repository: {CONFIG['REPO_PATH']}")
    logger.info(f"Branch: {CONFIG['BRANCH']}")
    logger.info(f"Port: {CONFIG['PORT']}")
    logger.info("FastAPI Documentation: http://localhost:8000/docs")
    logger.info("========================================================")

    uvicorn.run("webhook_server:app", host=CONFIG["HOST"], port=CONFIG["PORT"], reload=False, log_level="info")
