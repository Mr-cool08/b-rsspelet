import os
import shutil
import subprocess
from pathlib import Path

from dotenv import dotenv_values


def main():
    project_dir = Path(__file__).resolve().parent
    config = dotenv_values(project_dir / ".env")
    authtoken = os.getenv("NGROK_AUTHTOKEN") or config.get("NGROK_AUTHTOKEN")
    if not authtoken:
        raise SystemExit("Fyll i NGROK_AUTHTOKEN i .env innan du startar tunneln.")

    ngrok = shutil.which("ngrok")
    if ngrok is None:
        local_ngrok = project_dir / ".cache" / "ngrok" / "ngrok.exe"
        if not local_ngrok.is_file():
            raise SystemExit("Installera ngrok från https://ngrok.com/download/windows.")
        ngrok = str(local_ngrok)

    port = os.getenv("STOCK_FIGHT_PORT", config.get("STOCK_FIGHT_PORT") or "8080")
    try:
        return subprocess.call(
            [ngrok, "http", f"http://127.0.0.1:{port}"],
            env={**os.environ, "NGROK_AUTHTOKEN": authtoken},
        )
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
