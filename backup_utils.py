# backup_utils.py  – robust weekly backups (HARD-CODED pg-bin path)
import os, shutil, subprocess, datetime as dt, sys
from pathlib import Path
from typing import List

# ─────────────────────── configuration ────────────────────────────
BACKUP_DIR   = Path(os.getenv("BACKUP_DIR", "./db_backups"))
DB_URL       = os.getenv("DATABASE_URL")               # MUST be set
RETENTION    = 4                                       # keep n newest
ADMIN_TOKEN  = os.getenv("BACKUP_ADMIN_TOKEN", "supersecret")

if not DB_URL:
    raise RuntimeError("Environment variable DATABASE_URL is missing")

BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# → ❶ ***HARD-CODE exact location of the PostgreSQL binaries***
PG_BIN = Path(r"C:\Program Files\PostgreSQL\17\bin")   # <-- adjust once!
if not PG_BIN.exists():
    raise RuntimeError(f"PostgreSQL bin folder not found: {PG_BIN}")

def _pg(exe: str) -> str:
    """
    Build absolute path to pg_dump / psql / pg_restore.
    Falls back to the short name if the .exe does not exist,
    so the script still works on Linux/Mac (where exe suffix is absent).
    """
    win_path = PG_BIN / f"{exe}.exe"
    return str(win_path) if win_path.exists() else exe


# ─────────────────────── helpers ──────────────────────────────────
def _timestamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d_%H-%M")

def _dump_path(stamp: str) -> Path:
    """…/<stamp>/dump.dump – single source of truth"""
    return BACKUP_DIR / stamp / "dump.dump"

def _call(cmd: List[str | os.PathLike]) -> None:
    """Run command and raise with stderr if it fails."""
    res = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if res.returncode:
        raise RuntimeError(
            f"command failed ({res.returncode}): {' '.join(map(str, cmd))}\n"
            f"{res.stderr.strip()}"
        )

# ─────────────────────── public API ───────────────────────────────
def create_backup() -> str:
    """
    Create a compressed pg_dump (custom format).
    Returns the timestamp (folder name) on success.
    Empty folders are removed on failure.
    """
    stamp      = _timestamp()
    folder     = _dump_path(stamp).parent
    dump_file  = _dump_path(stamp)

    folder.mkdir(parents=True, exist_ok=True)

    try:
        _call([_pg("pg_dump"), "-d", DB_URL, "-Fc", "-f", dump_file])
    except Exception:
        # remove empty folder to avoid “phantom” backups
        shutil.rmtree(folder, ignore_errors=True)
        raise

    # — retention — keep only the newest RETENTION backup folders
    valid = sorted(
        (p for p in BACKUP_DIR.iterdir() if _dump_path(p.name).exists()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in valid[RETENTION:]:
        shutil.rmtree(old, ignore_errors=True)

    return stamp


def list_backups() -> List[str]:
    """Newest → oldest list of real dumps."""
    return sorted(
        (p.name for p in BACKUP_DIR.iterdir() if _dump_path(p.name).exists()),
        reverse=True,
    )


def restore_backup(stamp: str) -> None:
    """***Destructive***: drop schema public and restore selected dump."""
    dump_file = _dump_path(stamp)
    if not dump_file.exists():
        raise FileNotFoundError(f"Backup {stamp!r} not found")

    # 1 – terminate connections & recreate schema
    _call([
        _pg("psql"), "-d", DB_URL, "-c",
        "SELECT pg_terminate_backend(pid)"
        " FROM pg_stat_activity WHERE pid <> pg_backend_pid();"
    ])
    _call([_pg("psql"), "-d", DB_URL, "-c", "DROP SCHEMA public CASCADE"])
    _call([_pg("psql"), "-d", DB_URL, "-c", "CREATE SCHEMA public"])

    # 2 – restore custom format
    _call([_pg("pg_restore"), "-d", DB_URL, "-Fc", dump_file])
