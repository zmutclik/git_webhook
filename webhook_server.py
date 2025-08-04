import os
from datetime import datetime, date
from typing import Optional, Dict, Any

from fastapi import FastAPI, Request, HTTPException, Header, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
from webhook_func import ensure_webhook_secret, logger, get_secret, verify_signature, pull_repository, process_webhook_background, execute_command
from webhook_models import WebhookResponse, StatusResponse, ManualPullResponse

BRANCH_NAME = os.environ.get("BRANCH", "main")
REPOSITORY_PATH = os.environ.get("REPO_PATH", "./repository")
GIT_URL_SSH = os.environ.get("GIT_URL_SSH", "git@gitlab.com:zmutclik/test-repo.git")

ensure_webhook_secret()

# Konfigurasi
CONFIG = {
    "PORT": 7000,
    "HOST": "0.0.0.0",
    "SECRET_TOKEN": get_secret("webhook_secret") or "your-secret-token-here",
    "REPO_PATH": REPOSITORY_PATH,
    "BRANCH": BRANCH_NAME,
    "POST_DEPLOY_SCRIPT": None,  # Script yang dijalankan setelah pull (opsional)
}


# FastAPI app
app = FastAPI(
    title="Git Webhook Server",
    description="Aplikasi webhook untuk otomatis pull git repository",
    version="1.0.0",
)


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
            success, message = await pull_repository(CONFIG)

            # Juga jalankan background task untuk processing tambahan
            background_tasks.add_task(process_webhook_background, CONFIG, payload, event_type)

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

    success, message = await pull_repository(CONFIG)

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


@app.post("/clone")
async def clone_repository():
    """Endpoint untuk clone repository (inisialisasi awal)"""
    logger.info("Clone repository dipicu")

    # Cek apakah direktori sudah ada
    if os.path.exists(CONFIG["REPO_PATH"]):
        # Cek apakah sudah ada .git folder
        git_path = os.path.join(CONFIG["REPO_PATH"], ".git")
        if os.path.exists(git_path):
            logger.warning(f"Repository sudah ada di {CONFIG['REPO_PATH']}")
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Repository sudah ada. Gunakan /manual-pull untuk update atau hapus folder terlebih dahulu",
                    "timestamp": datetime.now().isoformat(),
                },
            )
        else:
            # Direktory ada tapi bukan git repo, hapus isinya
            logger.info(f"Membersihkan direktori {CONFIG['REPO_PATH']}")
            success, output = await execute_command(f"rm -rf {CONFIG['REPO_PATH']}/*")
            if not success:
                logger.error(f"Gagal membersihkan direktori: {output}")
                raise HTTPException(
                    status_code=500,
                    detail={"status": "error", "message": "Gagal membersihkan direktori", "error": output, "timestamp": datetime.now().isoformat()},
                )
    else:
        # Buat direktori parent jika belum ada
        parent_dir = os.path.dirname(CONFIG["REPO_PATH"])
        if parent_dir and not os.path.exists(parent_dir):
            try:
                os.makedirs(parent_dir, exist_ok=True)
                logger.info(f"Direktori parent dibuat: {parent_dir}")
            except Exception as e:
                logger.error(f"Gagal membuat direktori parent: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail={"status": "error", "message": "Gagal membuat direktori parent", "error": str(e), "timestamp": datetime.now().isoformat()},
                )

    # Clone repository
    clone_command = f"git clone -b {CONFIG['BRANCH']} {GIT_URL_SSH} {CONFIG['REPO_PATH']}"
    logger.info(f"Menjalankan: {clone_command}")

    success, output = await execute_command(clone_command)

    if not success:
        logger.error(f"Git clone gagal: {output}")
        raise HTTPException(
            status_code=500, detail={"status": "error", "message": "Git clone gagal", "error": output, "timestamp": datetime.now().isoformat()}
        )

    logger.info("Repository berhasil di-clone")

    # Jalankan post-deploy script jika ada
    if CONFIG["POST_DEPLOY_SCRIPT"]:
        logger.info("Menjalankan post-deploy script setelah clone...")
        script_success, script_output = await execute_command(CONFIG["POST_DEPLOY_SCRIPT"], cwd=CONFIG["REPO_PATH"])

        if not script_success:
            logger.warning(f"Post-deploy script gagal: {script_output}")

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": f"Repository berhasil di-clone ke {CONFIG['REPO_PATH']}",
            "output": output,
            "timestamp": datetime.now().isoformat(),
        },
    )


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
    logger.info("FastAPI Documentation: http://localhost:7000/docs")
    logger.info("========================================================")

    uvicorn.run("webhook_server:app", host=CONFIG["HOST"], port=CONFIG["PORT"], reload=False, log_level="info")
