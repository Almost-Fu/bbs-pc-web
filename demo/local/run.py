#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BBS 本地部署启动器（有界实现）

用法（必须用后端虚拟环境的 Python 运行）：
    D:\\项目\\BBS\\bbs-app-backend\\.venv\\Scripts\\python.exe bbs-local\\run.py
    D:\\项目\\BBS\\bbs-app-backend\\.venv\\Scripts\\python.exe bbs-local\\run.py --check

做五件事：
  1. 只初始化/复用本机独立库 bbs_local_codex（绝不 DROP，绝不碰其他库）
  2. 启动后端 127.0.0.1:8001
  3. 启动移动 H5 静态服务 127.0.0.1:5183（只读发行包，运行时改写 JS 里的线上域名）
  4. 启动 PC Vite dev 127.0.0.1:5184
  5. 如已安装依赖，再启动管理后台 Vite dev 127.0.0.1:5185
     （后端代理在子进程环境里固定指向 8001，不改 admin-web 源码或 .env；
      未安装 node_modules 时只提示、不自动安装，其余服务照常启动）

不改 .env、不改后端源码、不改 H5 发行包；不杀任何外部进程。
"""

from __future__ import annotations

import argparse
import http.client
import json
import mimetypes
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pymysql
from dotenv import dotenv_values
from pymysql.constants import CLIENT

# =============================================================================
# 固定路径 / 端口 / 库名
# =============================================================================
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = PROJECT_ROOT / "bbs-app-backend"
PC_DIR = PROJECT_ROOT / "bbs-pc-web"
ADMIN_DIR = PROJECT_ROOT / "bbs-admin-web"
H5_DIR = PROJECT_ROOT / "bbs-app-frontend" / "unpackage" / "dist" / "build" / "web"

BACKEND_PYTHON = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
ENV_FILE = BACKEND_DIR / ".env"
SCHEMA_FILE = BACKEND_DIR / "sql" / "bbs_schema.sql"
VITE_BIN = PC_DIR / "node_modules" / "vite" / "bin" / "vite.js"
ADMIN_VITE_BIN = ADMIN_DIR / "node_modules" / "vite" / "bin" / "vite.js"

DEPLOY_DIR = Path(__file__).resolve().parent
LOGS_DIR = DEPLOY_DIR / "logs"
UPLOADS_DIR = DEPLOY_DIR / "uploads"
STATE_FILE = DEPLOY_DIR / "state.json"

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8001
MOBILE_PORT = 5183
PC_PORT = 5184
ADMIN_PORT = 5185
PORTS = {
    BACKEND_PORT: "后端 API",
    MOBILE_PORT: "移动 H5",
    PC_PORT: "PC 网页",
    ADMIN_PORT: "管理后台",
}

LOCAL_DB = "bbs_local_codex"
PRODUCTION_API = b"https://bbs-app-backend-zuzm.onrender.com"

# 建表脚本里的 10 张核心表。admin_audit_logs 由后端启动时 CREATE TABLE IF NOT EXISTS 自动补建。
REQUIRED_TABLES = (
    "users",
    "bars",
    "posts",
    "post_images",
    "comments",
    "likes",
    "favorites",
    "follows",
    "footprints",
    "notify_read",
)

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "proxy-connection",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}

DROP_TABLE_RE = re.compile(r"(?im)^[ \t]*DROP[ \t]+TABLE\b[^;]*;[ \t]*(?:\r?\n)?")
ANY_DROP_TABLE_RE = re.compile(r"(?i)\bDROP\s+TABLE\b")

log_lock = threading.Lock()


def log(message: str) -> None:
    with log_lock:
        print(message, flush=True)


# =============================================================================
# 基础检查
# =============================================================================
def port_is_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex((host, port)) == 0


def admin_available() -> bool:
    """管理后台依赖是否已安装。没有 node_modules 只提示，不自动安装。"""
    return ADMIN_DIR.is_dir() and ADMIN_VITE_BIN.is_file()


def db_error_text(exc: Exception) -> str:
    """只输出错误码/类型，不输出账号、密码、.env 内容。"""
    if isinstance(exc, pymysql.err.OperationalError) and exc.args:
        code = exc.args[0]
        hints = {
            1045: "账号或密码无效/无权限",
            2003: "无法连接 MySQL（服务未启动或端口不对）",
            1044: "数据库账号无权限",
        }
        return f"MySQL 错误 {code}：{hints.get(code, '连接失败')}"
    return f"{type(exc).__name__}"


def load_db_config() -> dict:
    """运行时读取 .env；值只保存在内存里，绝不打印。"""
    if not ENV_FILE.is_file():
        raise RuntimeError(f"缺少 .env：{ENV_FILE}")
    values = dotenv_values(str(ENV_FILE))
    missing = [key for key in ("DB_HOST", "DB_PORT", "DB_USER") if not values.get(key)]
    if missing:
        raise RuntimeError("本地 .env 缺少连接配置：" + ", ".join(missing))

    host = str(values["DB_HOST"]).strip()
    if host.lower() not in ("localhost", "127.0.0.1"):
        raise RuntimeError("本地 .env 的 DB_HOST 必须是 localhost 或 127.0.0.1")
    try:
        port = int(str(values["DB_PORT"]).strip())
    except ValueError as exc:
        raise RuntimeError("本地 .env 的 DB_PORT 不是有效端口") from exc

    return {
        "host": "127.0.0.1" if host.lower() == "localhost" else host,
        "port": port,
        "user": str(values["DB_USER"]).strip(),
        "password": str(values.get("DB_PASSWORD") or ""),
    }


def db_connect(config: dict, multi: bool = False) -> pymysql.connections.Connection:
    kwargs = {
        "host": config["host"],
        "port": config["port"],
        "user": config["user"],
        "password": config["password"],
        "charset": "utf8mb4",
        "autocommit": True,
        "connect_timeout": 8,
    }
    if multi:
        kwargs["client_flag"] = CLIENT.MULTI_STATEMENTS
    return pymysql.connect(**kwargs)


def database_exists(conn, name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s", (name,))
        return cur.fetchone() is not None


def missing_tables(conn, name: str) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s", (name,))
        existing = {row[0] for row in cur.fetchall()}
    return [table for table in REQUIRED_TABLES if table not in existing]


def inspect_database(config: dict) -> tuple[str, list[str]]:
    """返回 (missing|incomplete|ready, 缺少的10张表)。"""
    conn = db_connect(config)
    try:
        if not database_exists(conn, LOCAL_DB):
            return "missing", list(REQUIRED_TABLES)
        missing = missing_tables(conn, LOCAL_DB)
        return ("ready" if not missing else "incomplete"), missing
    finally:
        conn.close()


def check_all() -> tuple[bool, dict | None]:
    errors: list[str] = []

    log("[1/4] 检查文件")
    file_checks = [
        ("后端虚拟环境 Python", BACKEND_PYTHON),
        ("后端 main.py", BACKEND_DIR / "main.py"),
        ("后端 .env", ENV_FILE),
        ("建表脚本", SCHEMA_FILE),
        ("PC package.json", PC_DIR / "package.json"),
        ("PC Vite", VITE_BIN),
        ("移动 H5 index.html", H5_DIR / "index.html"),
    ]
    for label, path in file_checks:
        if path.is_file():
            log(f"  [ok] {label}: {path}")
        else:
            log(f"  [错误] 缺少{label}: {path}")
            errors.append(label)

    if ADMIN_DIR.is_dir() and ADMIN_VITE_BIN.is_file():
        log(f"  [ok] 管理后台 Vite: {ADMIN_VITE_BIN}")
    elif not ADMIN_DIR.is_dir():
        log(f"  [警告] 找不到管理后台目录 {ADMIN_DIR}；5185 不会启动（不会自动安装）")
    else:
        log(f"  [警告] 管理后台未安装依赖（缺少 {ADMIN_VITE_BIN}）；5185 不会启动（不会自动安装）")

    node = shutil.which("node")
    if node:
        log(f"  [ok] node: {node}")
    else:
        log("  [错误] PATH 中找不到 node")
        errors.append("node")

    log("[2/4] 检查 .env 数据库连接配置")
    config = None
    try:
        config = load_db_config()
        log(f"  [ok] 本机连接 {config['host']}:{config['port']}（凭据不显示）")
    except Exception as exc:
        log(f"  [错误] {exc}")
        errors.append("env")

    log("[3/4] 检查数据库初始化前置（只读检查，不创建、不导入）")
    db_state = "unknown"
    if config is not None:
        try:
            conn = db_connect(config)
            conn.close()
            log("  [ok] MySQL 连接成功")
            db_state, missing = inspect_database(config)
            if db_state == "missing":
                log(f"  [ok] 独立库 {LOCAL_DB} 不存在；启动时会创建并导入 schema")
            elif db_state == "ready":
                log(f"  [ok] 独立库 {LOCAL_DB} 已存在且 10 张核心表齐全；启动时直接复用")
            else:
                log(f"  [错误] 独立库 {LOCAL_DB} 已存在但表不完整，缺少：{', '.join(missing)}")
                log("         不会清库；请先手动处理该独立库后重试")
                errors.append("db-incomplete")
        except Exception as exc:
            log(f"  [错误] 数据库检查失败：{db_error_text(exc)}")
            errors.append("db")

    log("[4/4] 检查端口")
    active_ports = {
        port: label
        for port, label in PORTS.items()
        if port != ADMIN_PORT or admin_available()
    }
    if ADMIN_PORT not in active_ports:
        log(f"  [跳过] 管理后台端口 {ADMIN_PORT}（依赖未安装）")
    for port, label in active_ports.items():
        if port_is_open(port):
            log(f"  [错误] {label} 端口 {port} 已被占用；不会终止外部进程，请先释放")
            errors.append(f"port-{port}")
        else:
            log(f"  [ok] {label} 端口 {port} 空闲")

    if errors:
        log(f"[失败] 共 {len(errors)} 项检查未通过")
        return False, config
    log("[通过] 全部检查通过")
    return True, config


# =============================================================================
# 数据库：只初始化 bbs_local_codex
# =============================================================================
def import_schema(config: dict) -> None:
    sql = SCHEMA_FILE.read_text(encoding="utf-8-sig")
    sql = sql.replace("`bbs_app`", f"`{LOCAL_DB}`")
    if "`bbs_app`" in sql:
        raise RuntimeError("建表脚本仍包含 `bbs_app`，拒绝执行")

    sql = DROP_TABLE_RE.sub("", sql)
    if ANY_DROP_TABLE_RE.search(sql):
        raise RuntimeError("建表脚本仍包含 DROP TABLE，禁止执行")

    conn = db_connect(config, multi=True)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            while cur.nextset():
                pass
    finally:
        conn.close()


def initialize_database(config: dict) -> str:
    conn = db_connect(config)
    try:
        if database_exists(conn, LOCAL_DB):
            missing = missing_tables(conn, LOCAL_DB)
            if missing:
                raise RuntimeError(
                    f"独立库 {LOCAL_DB} 已存在但表不完整（缺少：{', '.join(missing)}）；"
                    "按约定拒绝清库，请手动处理"
                )
            log(f"[数据库] 复用已有独立库 {LOCAL_DB}（10 张核心表齐全，不导入、不清库）")
            return "reused"

        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{LOCAL_DB}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
            )
        log(f"[数据库] 已创建独立库 {LOCAL_DB}")
    finally:
        conn.close()

    log(f"[数据库] 导入 {SCHEMA_FILE.name} 到 {LOCAL_DB}（已去除 DROP TABLE）")
    import_schema(config)

    check = db_connect(config)
    try:
        missing = missing_tables(check, LOCAL_DB)
    finally:
        check.close()
    if missing:
        raise RuntimeError(f"导入后仍缺少表：{', '.join(missing)}")
    log("[数据库] 初始化完成（10 张核心表齐全；admin_audit_logs 由后端启动时自动补建）")
    return "created"


# =============================================================================
# JWT secret / 子进程环境
# =============================================================================
def load_or_create_jwt_secret() -> str:
    if STATE_FILE.is_file():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            secret = str(data.get("jwt_secret", ""))
            if len(secret) >= 32:
                return secret
        except Exception:
            pass
    secret = secrets.token_urlsafe(48)
    STATE_FILE.write_text(json.dumps({"jwt_secret": secret}, ensure_ascii=False, indent=2), encoding="utf-8")
    return secret


MINIMAL_ENV_KEYS = {
    "PATH",
    "SYSTEMROOT",
    "WINDIR",
    "TEMP",
    "TMP",
    "USERPROFILE",
    "HOMEDRIVE",
    "HOMEPATH",
    "APPDATA",
    "LOCALAPPDATA",
    "COMSPEC",
    "PATHEXT",
    "NUMBER_OF_PROCESSORS",
    "PROCESSOR_ARCHITECTURE",
    "PROCESSOR_IDENTIFIER",
    "OS",
    "PROGRAMDATA",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
    "COMMONPROGRAMFILES",
    "COMMONPROGRAMFILES(X86)",
}


def minimal_env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key.upper() in MINIMAL_ENV_KEYS}
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    return env


def creation_flags() -> int:
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0


def start_backend(config: dict, jwt_secret: str):
    log_path = LOGS_DIR / "backend.log"
    stream = open(log_path, "ab", buffering=0)
    env = minimal_env()
    env.update(
        {
            "APP_ENV": "development",
            "DB_HOST": "127.0.0.1",
            "DB_PORT": str(config["port"]),
            "DB_USER": config["user"],
            "DB_PASSWORD": config["password"],
            "DB_NAME": LOCAL_DB,
            "DB_SSL": "false",
            "SEED_DEMO_DATA": "0",
            "PORT": str(BACKEND_PORT),
            "JWT_SECRET": jwt_secret,
            "UPLOAD_DIR": str(UPLOADS_DIR),
            "CORS_ORIGINS": (
                f"http://127.0.0.1:{MOBILE_PORT},http://127.0.0.1:{PC_PORT},"
                f"http://127.0.0.1:{ADMIN_PORT}"
            ),
        }
    )
    cmd = [
        str(BACKEND_PYTHON),
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        BACKEND_HOST,
        "--port",
        str(BACKEND_PORT),
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(BACKEND_DIR),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=stream,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags(),
        )
    except Exception:
        stream.close()
        raise
    log(f"[启动] 后端 API 127.0.0.1:{BACKEND_PORT}  (pid {proc.pid}, 日志 logs/backend.log)")
    return proc, stream


def start_pc():
    node = shutil.which("node")
    if not node:
        raise RuntimeError("PATH 中找不到 node")
    log_path = LOGS_DIR / "pc.log"
    stream = open(log_path, "ab", buffering=0)
    env = minimal_env()
    env["VITE_DEV_PROXY_TARGET"] = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
    cmd = [
        node,
        str(VITE_BIN),
        "--host",
        BACKEND_HOST,
        "--port",
        str(PC_PORT),
        "--strictPort",
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(PC_DIR),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=stream,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags(),
        )
    except Exception:
        stream.close()
        raise
    log(f"[启动] PC 网页 127.0.0.1:{PC_PORT}  (pid {proc.pid}, 日志 logs/pc.log)")
    return proc, stream


def start_admin():
    """管理后台 Vite dev（5185）。

    不改 admin-web 的源码或 .env：只用子进程环境变量
    VITE_DEV_PROXY_TARGET 把 /api、/uploads、/static 代理固定到本机 8001。
    Vite 的 loadEnv 会优先读取进程环境里的 VITE_ 变量。
    """
    if not ADMIN_VITE_BIN.is_file():
        raise RuntimeError(f"管理后台依赖未安装：缺少 {ADMIN_VITE_BIN}（不会自动安装）")
    node = shutil.which("node")
    if not node:
        raise RuntimeError("PATH 中找不到 node")
    log_path = LOGS_DIR / "admin.log"
    stream = open(log_path, "ab", buffering=0)
    env = minimal_env()
    env["VITE_DEV_PROXY_TARGET"] = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
    cmd = [
        node,
        str(ADMIN_VITE_BIN),
        "--host",
        BACKEND_HOST,
        "--port",
        str(ADMIN_PORT),
        "--strictPort",
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(ADMIN_DIR),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=stream,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags(),
        )
    except Exception:
        stream.close()
        raise
    log(f"[启动] 管理后台 127.0.0.1:{ADMIN_PORT}  (pid {proc.pid}, 日志 logs/admin.log)")
    return proc, stream


def wait_for_port(proc: subprocess.Popen, port: int, timeout: float, label: str) -> tuple[bool, str]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False, f"{label} 进程已退出（code {proc.returncode}），请查看 logs 目录"
        if port_is_open(port):
            return True, ""
        time.sleep(0.25)
    return False, f"{label} 在 {int(timeout)} 秒内未监听 127.0.0.1:{port}"


# =============================================================================
# 移动 H5：ThreadingHTTPServer（只读静态 + 代理）
# =============================================================================
def is_proxy_path(path: str) -> bool:
    return (
        path == "/api"
        or path.startswith("/api/")
        or path == "/uploads"
        or path.startswith("/uploads/")
        or path == "/static/avatars"
        or path.startswith("/static/avatars/")
    )


def is_within(root: Path, target: Path) -> bool:
    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False


def is_asset_like(relative: str) -> bool:
    return (
        relative == "assets"
        or relative.startswith("assets/")
        or relative == "static"
        or relative.startswith("static/")
        or bool(Path(relative).suffix)
    )


class LocalHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = False
    daemon_threads = True

    def __init__(self, address, handler, log_stream):
        self.log_stream = log_stream
        self.log_lock = threading.Lock()
        super().__init__(address, handler)

    def write_log(self, message: str) -> None:
        line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}\n"
        with self.log_lock:
            try:
                self.log_stream.write(line)
                self.log_stream.flush()
            except Exception:
                pass

    def handle_error(self, request, client_address):
        self.write_log(f"请求处理异常 {client_address[0]}: {type(sys.exc_info()[1]).__name__}")


class MobileHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "BBSLocalMobile/1.0"

    # ---- 路由 ----
    def do_GET(self):
        self._dispatch("GET")

    def do_HEAD(self):
        self._dispatch("HEAD")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_PATCH(self):
        self._dispatch("PATCH")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def do_OPTIONS(self):
        self._dispatch("OPTIONS")

    def _dispatch(self, method: str) -> None:
        try:
            path = urlsplit(self.path).path
            if is_proxy_path(path):
                self._proxy(method)
            elif method in ("GET", "HEAD", "OPTIONS"):
                self._serve_local(method, path)
            else:
                self._send_plain(405, "Method Not Allowed", method)
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True
        except Exception as exc:
            self.server.write_log(f"{method} {self.path} 失败: {type(exc).__name__}")
            try:
                self._send_plain(500, "Internal Server Error", method)
            except Exception:
                pass

    # ---- 工具 ----
    def _send_plain(self, status: int, text: str, method: str = "GET", extra_headers=None) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if extra_headers:
            for key, value in extra_headers:
                self.send_header(key, value)
        self.end_headers()
        if method != "HEAD":
            self.wfile.write(body)

    def log_message(self, fmt, *args):
        try:
            message = fmt % args
        except Exception:
            message = fmt
        self.server.write_log(f"{self.client_address[0]} {message}")

    # ---- 本地静态 ----
    def _serve_local(self, method: str, path: str) -> None:
        if method == "OPTIONS":
            self._send_plain(204, "", method="OPTIONS", extra_headers=[("Allow", "GET, HEAD, OPTIONS")])
            return

        relative = path.lstrip("/")
        try:
            relative = unquote(relative)
        except Exception:
            self._send_plain(400, "Bad Request", method)
            return

        # 防遍历/防盘符跳转/防 ADS
        if "\x00" in relative or "\\" in relative or ":" in relative:
            self._send_plain(404, "Not Found", method)
            return
        if relative.startswith("/") or Path(relative).is_absolute():
            self._send_plain(404, "Not Found", method)
            return

        root = H5_DIR.resolve()
        target = (root / relative).resolve()
        if not is_within(root, target):
            self._send_plain(404, "Not Found", method)
            return

        if target.is_dir():
            target = (target / "index.html").resolve()
            if not is_within(root, target):
                self._send_plain(404, "Not Found", method)
                return

        if target.is_file():
            self._send_file(target, method)
            return

        if is_asset_like(relative):
            self._send_plain(404, "Not Found", method)
            return

        index = root / "index.html"
        if index.is_file():
            self._send_file(index, method)
        else:
            self._send_plain(404, "Not Found", method)

    def _send_file(self, target: Path, method: str) -> None:
        suffix = target.suffix.lower()
        ctype, _ = mimetypes.guess_type(str(target))
        if suffix in (".js", ".mjs") or (ctype and "javascript" in ctype):
            ctype = "text/javascript; charset=utf-8"
        if not ctype:
            ctype = "application/octet-stream"
        if (ctype.startswith("text/") or ctype in ("application/json", "application/xml", "image/svg+xml")) and "charset=" not in ctype:
            ctype += "; charset=utf-8"

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("X-Content-Type-Options", "nosniff")

        if suffix in (".js", ".mjs") or (ctype and "javascript" in ctype):
            # 只在内存里把线上 API 域名替换为空串，让请求走同源 /api；绝不改发行包。
            data = target.read_bytes().replace(PRODUCTION_API, b"")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if method != "HEAD":
                self.wfile.write(data)
            return

        size = target.stat().st_size
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "no-cache" if suffix in (".html", ".htm") else "public, max-age=3600")
        self.end_headers()
        if method == "HEAD":
            return
        with open(target, "rb") as fh:
            shutil.copyfileobj(fh, self.wfile, 64 * 1024)

    # ---- 反向代理到后端 ----
    def _read_body(self) -> bytes:
        transfer_encoding = self.headers.get("Transfer-Encoding", "").lower()
        if "chunked" in transfer_encoding:
            chunks = bytearray()
            while True:
                line = self.rfile.readline(65536).strip()
                if not line:
                    break
                size = int(line.split(b";")[0], 16)
                if size == 0:
                    while True:
                        trailer = self.rfile.readline(65536)
                        if trailer in (b"\r\n", b"\n", b""):
                            break
                    break
                chunks += self.rfile.read(size)
                self.rfile.read(2)
            return bytes(chunks)

        raw_length = self.headers.get("Content-Length")
        if not raw_length:
            return b""
        try:
            length = int(raw_length)
        except ValueError:
            return b""
        if length <= 0:
            return b""
        return self.rfile.read(length)

    def _proxy(self, method: str) -> None:
        body = self._read_body()
        connection_tokens = {
            token.strip().lower()
            for token in self.headers.get("Connection", "").split(",")
            if token.strip()
        }

        headers: list[tuple[str, str]] = []
        for key, value in self.headers.items():
            lower = key.lower()
            if lower in HOP_BY_HOP or lower in connection_tokens:
                continue
            if lower in ("host", "content-length"):
                continue
            headers.append((key, value))
        if body or method in ("POST", "PUT", "PATCH"):
            headers.append(("Content-Length", str(len(body))))

        upstream = http.client.HTTPConnection(BACKEND_HOST, BACKEND_PORT, timeout=120)
        try:
            upstream.putrequest(method, self.path, skip_accept_encoding=True)
            for key, value in headers:
                upstream.putheader(key, value)
            upstream.endheaders()
            if body:
                upstream.send(body)

            response = upstream.getresponse()
            data = response.read()

            response_tokens = {
                token.strip().lower()
                for token in response.getheader("Connection", "").split(",")
                if token.strip()
            }

            self.send_response(response.status)
            for key, value in response.getheaders():
                lower = key.lower()
                if lower in HOP_BY_HOP or lower in response_tokens:
                    continue
                if lower == "content-length":
                    continue
                self.send_header(key, value)

            if response.status in (204, 304):
                pass
            elif method == "HEAD":
                original_length = response.getheader("Content-Length")
                if original_length is not None:
                    self.send_header("Content-Length", original_length)
                else:
                    self.send_header("Content-Length", "0")
            else:
                self.send_header("Content-Length", str(len(data)))
            self.end_headers()

            if method != "HEAD" and response.status not in (204, 304) and data:
                self.wfile.write(data)
        except (ConnectionRefusedError, ConnectionResetError, socket.timeout, OSError) as exc:
            self.server.write_log(f"代理到后端失败 {method} {self.path}: {type(exc).__name__}")
            self._send_plain(502, "Backend Unavailable", method)
        finally:
            upstream.close()


def start_mobile():
    stream = open(LOGS_DIR / "mobile.log", "a", encoding="utf-8", buffering=1)
    try:
        server = LocalHTTPServer((BACKEND_HOST, MOBILE_PORT), MobileHandler, stream)
    except Exception:
        stream.close()
        raise
    thread = threading.Thread(target=server.serve_forever, name="mobile-h5", daemon=True)
    thread.start()
    server.write_log(f"移动 H5 已启动 http://127.0.0.1:{MOBILE_PORT} -> 后端 {BACKEND_HOST}:{BACKEND_PORT}")
    log(f"[启动] 移动 H5 127.0.0.1:{MOBILE_PORT}  (日志 logs/mobile.log)")
    return server, stream


# =============================================================================
# 停止：只结束自己创建的子进程树
# =============================================================================
def terminate_tree(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    pid = proc.pid

    try:
        import psutil  # type: ignore

        parent = psutil.Process(pid)
        processes = parent.children(recursive=True) + [parent]
        for item in processes:
            try:
                item.terminate()
            except psutil.Error:
                pass
        _, alive = psutil.wait_procs(processes, timeout=5)
        for item in alive:
            try:
                item.kill()
            except psutil.Error:
                pass
        try:
            proc.wait(timeout=3)
        except Exception:
            pass
        return
    except ImportError:
        pass
    except Exception:
        pass

    if os.name == "nt":
        terminated = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags(),
        )
        if terminated.returncode != 0:
            subprocess.run(
                ["pwsh.exe", "-NoProfile", "-NonInteractive", "-Command",
                 f"$p=[System.Diagnostics.Process]::GetProcessById({pid}); $p.Kill($true)"],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=creation_flags(), check=False,
            )
    else:
        proc.terminate()
    try:
        proc.wait(timeout=8)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def stop_services(backend, pc, admin, mobile, streams) -> None:
    log("[停止] 只结束本启动器创建的服务…")
    if mobile is not None:
        try:
            mobile.shutdown()
            mobile.server_close()
        except Exception:
            pass
    terminate_tree(admin)
    terminate_tree(pc)
    terminate_tree(backend)
    for stream in streams:
        if stream is None:
            continue
        try:
            stream.close()
        except Exception:
            pass
    log("[停止] 完成。数据库未删除。")


# =============================================================================
# 主流程
# =============================================================================
def run_services(config: dict) -> int:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    backend = None
    pc = None
    admin = None
    mobile = None
    backend_stream = None
    pc_stream = None
    admin_stream = None
    mobile_stream = None

    try:
        initialize_database(config)
        jwt_secret = load_or_create_jwt_secret()
        log("[状态] JWT_SECRET 已加载/生成（保存在 state.json，不打印）")

        backend, backend_stream = start_backend(config, jwt_secret)
        mobile, mobile_stream = start_mobile()

        ready, message = wait_for_port(backend, BACKEND_PORT, 60, "后端 API")
        if not ready:
            raise RuntimeError(message)

        pc, pc_stream = start_pc()
        ready, message = wait_for_port(pc, PC_PORT, 60, "PC 网页")
        if not ready:
            raise RuntimeError(message)

        # 管理后台是可选项：依赖没装只提示，不自动安装，也不影响其它服务。
        if admin_available():
            try:
                admin, admin_stream = start_admin()
                ready, message = wait_for_port(admin, ADMIN_PORT, 60, "管理后台")
                if not ready:
                    log(f"[警告] 管理后台未就绪：{message}；其余服务继续")
                    terminate_tree(admin)
                    admin = None
            except Exception as exc:
                log(f"[警告] 管理后台未启动：{exc}；其余服务继续")
                admin = None
        else:
            log(f"[警告] 管理后台依赖未安装，跳过 5185（不会自动安装）")

        log("=" * 64)
        log("BBS 本地部署已启动")
        log(f"  后端 API   http://127.0.0.1:{BACKEND_PORT}   (接口文档 /docs)")
        log(f"  移动 H5    http://127.0.0.1:{MOBILE_PORT}")
        log(f"  PC 网页    http://127.0.0.1:{PC_PORT}")
        if admin is not None:
            log(f"  管理后台   http://127.0.0.1:{ADMIN_PORT}")
        else:
            log(f"  管理后台   未启动（5185）；依赖或启动异常见上方提示")
        log(f"  本地独立库 {LOCAL_DB}（只由本启动器使用，不接触其他库）")
        log("  种子数据   sql/bbs_schema.sql 的示例数据；更多演示数据可另行运行 seed_demo.py")
        log("  演示说明   outputs/bbs-demo-guide.md")
        log("  日志       logs/backend.log、logs/pc.log、logs/admin.log、logs/mobile.log")
        log("  按 Ctrl+C 停止；只结束本启动器创建的服务")
        log("=" * 64)

        while True:
            if backend.poll() is not None:
                log(f"[错误] 后端进程已退出（code {backend.returncode}），请查看 logs/backend.log")
                return 1
            if pc.poll() is not None:
                log(f"[错误] PC 进程已退出（code {pc.returncode}），请查看 logs/pc.log")
                return 1
            if admin is not None and admin.poll() is not None:
                log(f"[警告] 管理后台进程已退出（code {admin.returncode}），请查看 logs/admin.log；其余服务继续")
                admin = None
            time.sleep(1)
    except KeyboardInterrupt:
        log("\n[停止] 收到 Ctrl+C")
        return 0
    except Exception as exc:
        if isinstance(exc, pymysql.err.MySQLError):
            log(f"[错误] 数据库操作失败：{db_error_text(exc)}")
        else:
            log(f"[错误] {exc}")
        return 1
    finally:
        stop_services(
            backend,
            pc,
            admin,
            mobile,
            [backend_stream, pc_stream, admin_stream, mobile_stream],
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="BBS 本地部署启动器")
    parser.add_argument("--check", action="store_true", help="只检查端口/连接/文件和初始化前置，不启动服务")
    args = parser.parse_args()

    log("BBS 本地部署启动器")
    log(f"部署目录：{DEPLOY_DIR}")
    ok, config = check_all()

    if args.check:
        log("")
        log("[--check] 仅检查，未创建数据库、未导入 SQL、未启动服务")
        return 0 if ok else 1

    if not ok or config is None:
        log("[失败] 前置检查未通过，未启动任何服务")
        return 1

    return run_services(config)


if __name__ == "__main__":
    sys.exit(main())
