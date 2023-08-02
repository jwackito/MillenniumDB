from __future__ import annotations

import socket
import subprocess
import sys
import time
from io import TextIOWrapper
from pathlib import Path
from subprocess import Popen

from .logging import Level, log
from .options import (
    CREATE_DB_EXECUTABLE,
    CWD,
    HOST,
    PORT,
    QUERY_EXECUTABLE,
    SERVER_EXECUTABLE,
    SERVER_LOGS_DIR,
    SLEEP_DELAY,
    TEST_SUITE_DIR,
    TESTING_DBS_DIR,
    TIMEOUT,
)
from .types import ExecutionStats, ServerCrashedException, Test


def create_db(qm_file: Path):
    if not qm_file.is_file():
        log(Level.ERROR, f"File not found {qm_file}")
        sys.exit(1)

    db_dir = TESTING_DBS_DIR / qm_file.with_suffix("").relative_to(TEST_SUITE_DIR)

    if db_dir.exists():
        log(Level.WARNING, f'Database "{db_dir.relative_to(TESTING_DBS_DIR)}" already exists')
    else:
        cmd: list[str] = [str(CREATE_DB_EXECUTABLE), str(qm_file), str(db_dir)]

        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log(Level.DEBUG, f'Database "{db_dir}" created')

    return db_dir


__log_file: TextIOWrapper | None = None


def start_server(db_dir: Path):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    address = (HOST, PORT)

    # Check if port is already in use
    if sock.connect_ex(address) == 0:
        log(Level.ERROR, f"Port {PORT} is already in use")
        sys.exit(1)

    global __log_file

    if __log_file is not None:
        __log_file.close()
        __log_file = None

    log_path = SERVER_LOGS_DIR / db_dir.with_suffix(".log").relative_to(TESTING_DBS_DIR)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.touch()

    __log_file = log_path.open(mode="a+", encoding="utf-8")

    cmd: list[str] = [str(SERVER_EXECUTABLE), str(db_dir), "--timeout", str(TIMEOUT), "--port", str(PORT)]

    server_process = subprocess.Popen(cmd, stdout=__log_file, stderr=__log_file)

    # Wait for server initialization
    while sock.connect_ex(address) != 0:
        time.sleep(SLEEP_DELAY)

    log(Level.BEGIN, f'SERVER STARTED: "{db_dir.relative_to(CWD)}"')
    return server_process, __log_file


def kill_server(server_process: Popen[bytes]):
    server_process.kill()
    server_process.wait()
    log(Level.END, "SERVER KILLED")


def execute_query(server: Popen[bytes] | None, test: Test, stats: ExecutionStats) -> str | None:
    with test.query.open(encoding="utf-8") as file:
        query_str = file.read()

    log(Level.DEBUG, f"query_string: {query_str}")

    result = subprocess.run(
        str(QUERY_EXECUTABLE),
        input=query_str,
        capture_output=True,
        encoding="utf-8",
    )

    if server and server.poll() is not None:
        stats.error += 1
        log(Level.ERROR, str(test), "Server crashed")
        raise ServerCrashedException

    if result.returncode != 0:
        stats.error += 1
        log(Level.ERROR, str(test), f"Server returned error: {result.returncode}")
        return None

    return result.stdout
