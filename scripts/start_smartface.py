import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / ".smartface"
FRONTEND_DIR = ROOT / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist-app" / "index.html"
REQUIREMENTS = ROOT / "database_pdt" / "requirements.txt"
URL = "http://127.0.0.1:8000"


def file_hash(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path.relative_to(ROOT)).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def read_state() -> dict:
    state_file = STATE_DIR / "state.json"
    if not state_file.is_file():
        return {}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_state(state: dict) -> None:
    STATE_DIR.mkdir(exist_ok=True)
    (STATE_DIR / "state.json").write_text(
        json.dumps(state, indent=2),
        encoding="utf-8",
    )


def run(command: list[str], cwd: Path = ROOT) -> None:
    print(f"> {' '.join(command)}")
    subprocess.run(command, cwd=cwd, check=True)


def ensure_python_dependencies(state: dict) -> None:
    requirements_hash = file_hash([REQUIREMENTS])
    if state.get("requirements") == requirements_hash:
        return

    print("Dang cap nhat thu vien Python...")
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--cache-dir",
            str(ROOT / ".pip-cache"),
            "-r",
            str(REQUIREMENTS),
        ]
    )
    state["requirements"] = requirements_hash
    write_state(state)


def npm_command() -> str:
    npm = shutil.which("npm.cmd")
    if npm:
        return npm
    fallback = Path(r"D:\cuasu\npm.cmd")
    if fallback.is_file():
        return str(fallback)
    raise RuntimeError("Khong tim thay npm.cmd. Hay cai Node.js.")


def frontend_files() -> list[Path]:
    files = [
        FRONTEND_DIR / "package.json",
        FRONTEND_DIR / "package-lock.json",
        FRONTEND_DIR / "vite.config.js",
        FRONTEND_DIR / "index.html",
    ]
    files.extend((FRONTEND_DIR / "src").rglob("*"))
    return [path for path in files if path.is_file()]


def ensure_frontend(state: dict) -> None:
    npm = npm_command()
    package_hash = file_hash(
        [
            FRONTEND_DIR / "package.json",
            FRONTEND_DIR / "package-lock.json",
        ]
    )
    if (
        state.get("frontend_packages") != package_hash
        or not (FRONTEND_DIR / "node_modules").is_dir()
    ):
        print("Dang cap nhat thu vien frontend...")
        run(
            [
                npm,
                "install",
                "--cache",
                str(FRONTEND_DIR / ".npm-cache"),
            ],
            FRONTEND_DIR,
        )
        state["frontend_packages"] = package_hash
        write_state(state)

    source_hash = file_hash(frontend_files())
    if state.get("frontend_source") == source_hash and FRONTEND_DIST.is_file():
        return

    print("Dang build frontend...")
    run([npm, "run", "build"], FRONTEND_DIR)
    state["frontend_source"] = source_hash
    write_state(state)


def is_server_ready() -> bool:
    try:
        with urllib.request.urlopen(f"{URL}/health", timeout=1) as response:
            return response.status == 200
    except OSError:
        return False


def open_browser_when_ready() -> None:
    for _ in range(120):
        if is_server_ready():
            if os.getenv("SMARTFACE_NO_BROWSER") != "1":
                webbrowser.open(URL)
            return
        time.sleep(0.5)
    print(f"Server khoi dong qua lau. Hay mo thu cong: {URL}")


def main() -> int:
    os.chdir(ROOT)
    print("SmartFace dang khoi dong...")

    if is_server_ready():
        print("SmartFace da chay. Dang mo trinh duyet...")
        if os.getenv("SMARTFACE_NO_BROWSER") != "1":
            webbrowser.open(URL)
        return 0

    state = read_state()
    ensure_python_dependencies(state)
    ensure_frontend(state)

    print(f"Web: {URL}")
    print("Nhan Ctrl+C de dung server.")
    threading.Thread(target=open_browser_when_ready, daemon=True).start()

    backend = subprocess.Popen(
        [sys.executable, "-u", str(ROOT / "database_pdt" / "main.py")],
        cwd=ROOT,
    )
    try:
        return backend.wait()
    except KeyboardInterrupt:
        backend.terminate()
        try:
            return backend.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend.kill()
            return backend.wait()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print()
        print(f"KHONG THE KHOI DONG SMARTFACE: {exc}")
        input("Nhan Enter de thoat...")
        raise SystemExit(1)
