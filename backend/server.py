import os
import time
import json
import uuid
import sqlite3
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, Field
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from fastapi.responses import HTMLResponse
from config_manager import config
from logger import logger, LOG_FILE_PATH
from javdb_scraper import (
    JavDBScraper, AuthBrowserError,
    start_login_session, refresh_login_captcha, submit_login_credentials
)
from fastapi import Header
import hashlib
import secrets
from datetime import datetime, timedelta

USER_DB_PATH = os.path.join(config.DATA_DIR, "user.db")

def init_user_db():
    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        );
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        );
    ''')
    conn.commit()
    conn.close()

def hash_password(password: str, salt: str = None) -> tuple:
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return key.hex(), salt

def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    computed_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(computed_hash, stored_hash)

def create_session(user_id: int, username: str) -> str:
    token = secrets.token_urlsafe(48)
    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()
    now_time = datetime.now()
    expires_time = now_time + timedelta(days=30)
    cursor.execute(
        "INSERT INTO sessions (token, user_id, username, expires_at) VALUES (?, ?, ?, ?)",
        (token, user_id, username, expires_time.strftime("%Y-%m-%d %H:%M:%S"))
    )
    cursor.execute(
        "UPDATE users SET last_login = ? WHERE id = ?",
        (now_time.strftime("%Y-%m-%d %H:%M:%S"), user_id)
    )
    conn.commit()
    conn.close()
    return token

def verify_token(token: str) -> Optional[dict]:
    if not token or not isinstance(token, str):
        return None
    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, username, expires_at FROM sessions WHERE token = ?",
        (token.strip(),)
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    user_id, username, expires_str = row
    try:
        exp_time = datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S")
        if exp_time < datetime.now():
            return None
    except Exception:
        pass
    return {"user_id": user_id, "username": username}

def revoke_session(token: str):
    if not token:
        return
    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE token = ?", (token.strip(),))
    conn.commit()
    conn.close()

from concurrent.futures import ThreadPoolExecutor

# ================= 1. 异步任务队列 & 定时任务器 =================

task_queue = asyncio.Queue(maxsize=config.MAX_QUEUE_SIZE)
tasks_status = {}
task_logs = {}
scheduled_jobs_info = {}

scheduler = BackgroundScheduler()
cron_executor = ThreadPoolExecutor(max_workers=5)

def append_task_log(task_id: str, msg: str, level: str = "INFO"):
    from datetime import datetime
    now_str = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    log_entry = f"{now_str} [{level}] {msg}"
    if task_id not in task_logs:
        task_logs[task_id] = []
    task_logs[task_id].append(log_entry)
    if len(task_logs[task_id]) > 1000:
        task_logs[task_id] = task_logs[task_id][-1000:]


async def queue_worker():
    """后台单任务严格排队消费者（防风控锁库）"""
    while True:
        task_data = await task_queue.get()
        task_id = task_data["task_id"]
        func_type = task_data["func_type"]
        payload = task_data["payload"]

        # 如果此排队任务已经被用户提前取消，跳过执行
        if tasks_status.get(task_id, {}).get("status") == "cancelled":
            logger.info(f"⏭️ [Queue] 任务 [{task_id}] 已被用户事先取消，跳过执行")
            task_queue.task_done()
            continue

        task_name = payload.get("task_name") or f"任务 [{task_id}]"

        tasks_status[task_id]["status"] = "running"
        tasks_status[task_id]["message"] = f"正在启动: {task_name}..."
        logger.info(f"▶️ [Queue] 开始执行队列任务 [{task_id}] | {task_name}")

        # 每次执行新队列任务时，清空上一次的历史运行日志
        task_logs[task_id] = []
        append_task_log(task_id, f"▶️ 开始执行队列任务 | {task_name}", "INFO")

        def cancel_check():
            st = tasks_status.get(task_id, {}).get("status")
            return st in ("cancelling", "cancelled")

        def progress_cb(sub_msg):
            if task_id in tasks_status and tasks_status[task_id]["status"] == "running":
                tasks_status[task_id]["message"] = f"{task_name} ({sub_msg})"

        def task_log_cb(msg):
            append_task_log(task_id, msg, "INFO")
            progress_cb(msg)

        try:
            loop = asyncio.get_event_loop()

            if func_type == "auto_scrape":
                def run_scrape():
                    scraper = JavDBScraper(
                        cookies_string=payload.get("cookies"), 
                        db_path=payload.get("db_path"),
                        cancel_check=cancel_check,
                        progress_callback=progress_cb,
                        log_callback=task_log_cb
                    )
                    urls = payload.get("target_urls") or ([payload["target_url"]] if payload.get("target_url") else [])
                    total = len(urls)
                    for idx, target_url in enumerate(urls, 1):
                        if cancel_check():
                            break
                        if total > 1:
                            task_log_cb(f"📌 [{idx}/{total}] 正在抓取目标: {target_url}")
                        scraped_codes = scraper.fetch_index(
                            target_url, 
                            max_pages=payload.get("max_pages"),
                            smart_incremental=payload.get("smart_incremental", False)
                        )
                        if not cancel_check() and payload.get("auto_fetch_details", True) and scraped_codes:
                            scraper.fetch_details(target_codes=scraped_codes)

                await loop.run_in_executor(None, run_scrape)

            elif func_type == "by_code":
                def run_code():
                    scraper = JavDBScraper(
                        cookies_string=payload.get("cookies"), 
                        db_path=payload.get("db_path"),
                        cancel_check=cancel_check,
                        log_callback=task_log_cb
                    )
                    return scraper.update_by_code(payload["code"])

                success = await loop.run_in_executor(None, run_code)

            elif func_type == "refresh_missing":
                def run_missing():
                    scraper = JavDBScraper(
                        cookies_string=payload.get("cookies"), 
                        db_path=payload.get("db_path"),
                        cancel_check=cancel_check,
                        log_callback=task_log_cb
                    )
                    return scraper.refresh_missing_fields(
                        payload.get("missing_field", "magnet_uc"),
                        limit=payload.get("limit", 50)
                    )

                count = await loop.run_in_executor(None, run_missing)

            # 更新任务完成或中断状态
            if cancel_check():
                tasks_status[task_id]["status"] = "cancelled"
                tasks_status[task_id]["message"] = f"{task_name} (用户手动终止)"
                append_task_log(task_id, f"🛑 任务已被用户手动终止", "WARNING")
                logger.warning(f"🛑 [Queue] 任务 [{task_id}] | {task_name} 已成功中断终止")
            else:
                if func_type == "auto_scrape":
                    tasks_status[task_id]["status"] = "completed"
                    tasks_status[task_id]["message"] = f"{task_name} (抓取任务完成！)"
                    append_task_log(task_id, f"🎉 抓取任务全流程执行完成！", "INFO")
                elif func_type == "by_code":
                    tasks_status[task_id]["status"] = "completed"
                    tasks_status[task_id]["message"] = f"番号 [{payload['code']}] (刷新完成！)"
                    append_task_log(task_id, f"🎉 番号 [{payload['code']}] 详情与磁力刷新成功！", "INFO")
                elif func_type == "refresh_missing":
                    tasks_status[task_id]["status"] = "completed"
                    tasks_status[task_id]["message"] = f"{task_name} (缺失字段补全已完成)"
                    append_task_log(task_id, f"🎉 缺失字段定向补全任务完成！", "INFO")

        except Exception as e:
            logger.error(f"❌ [Queue] 队列任务执行失败 [{task_id}]: {e}")
            append_task_log(task_id, f"❌ 任务执行过程中遭遇异常: {str(e)}", "ERROR")
            tasks_status[task_id]["status"] = "failed"
            tasks_status[task_id]["message"] = f"{task_name} (错误: {str(e)})"
        finally:
            task_queue.task_done()


JOBS_FILE_PATH = os.path.join(config.DATA_DIR, "scheduled_jobs.json")

def load_jobs_from_file() -> dict:
    if os.path.exists(JOBS_FILE_PATH):
        try:
            with open(JOBS_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            logger.error(f"❌ 加载持久化定时任务失败: {e}")
    return {}

def save_jobs_to_file(jobs_dict: dict):
    try:
        clean_dict = {}
        for k, v in jobs_dict.items():
            if isinstance(v, dict):
                clean_dict[k] = v
            elif hasattr(v, "dict"):
                clean_dict[k] = v.dict()
            else:
                clean_dict[k] = str(v)
        with open(JOBS_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(clean_dict, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"💾 已成功将 {len(clean_dict)} 个定时任务持久化保存至 {JOBS_FILE_PATH}")
    except Exception as e:
        logger.error(f"❌ 保存持久化定时任务失败: {e}")

def register_job_to_scheduler(job_id: str, meta: dict):
    if scheduler.get_job(job_id): 
        scheduler.remove_job(job_id)
    cron_expr = meta.get("cron_expression", "0 3 * * *").strip()
    parts = cron_expr.split()
    if len(parts) != 5:
        raise ValueError(f"Cron 表达式格式需为 5 段 ({cron_expr})")
    
    trigger = CronTrigger(
        minute=parts[0], 
        hour=parts[1], 
        day=parts[2], 
        month=parts[3], 
        day_of_week=parts[4]
    )
    scheduler.add_job(
        scheduled_cron_runner, 
        trigger, 
        id=job_id, 
        args=[job_id, meta], 
        replace_existing=True
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_user_db()
    logger.info("🔑 user.db 数据库安全结构校验完成")
    if config.ENABLE_SCHEDULER:
        scheduler.start()
        logger.info("⏰ APScheduler 定时任务引擎已启动")

        # 自动从持久化文件恢复已保存的 Cron 定时任务
        persistent_jobs = load_jobs_from_file()
        restored_count = 0
        for job_id, meta in persistent_jobs.items():
            try:
                register_job_to_scheduler(job_id, meta)
                scheduled_jobs_info[job_id] = meta
                restored_count += 1
            except Exception as e:
                logger.error(f"❌ [Lifespan] 恢复定时任务 [{job_id}] 失败: {e}")
        if restored_count > 0:
            logger.info(f"🔄 [Lifespan] 自动成功恢复了 {restored_count} 个持久化 Cron 定时任务！")

    worker_task = asyncio.create_task(queue_worker())
    logger.info("📥 异步任务队列 Consumer 已就绪")
    yield
    if config.ENABLE_SCHEDULER: scheduler.shutdown()
    worker_task.cancel()


tags_metadata = [
    {"name": "01. 模拟登录 (Auth)", "description": "处理 JavDB 账号密码模拟登录、验证码刷新及 Cookie 自动注入"},
    {"name": "02. 任务队列 (Queue)", "description": "异步 FIFO 单线程串行队列，防止高并发导致的风控与数据库锁"},
    {"name": "03. 定时任务 (Scheduler)", "description": "基于 APScheduler 的无人值守 Cron 自动化增量抓取调度"},
    {"name": "04. 用户数据 (User)", "description": "校验当前用户登录状态、获取已订阅演员与个人/收藏清单"},
    {"name": "05. 数据库管理 (Database)", "description": "物理删除、记录清空以及缺失磁力链接（如 UC/4K）的智能定向补全"},
    {"name": "06. 系统配置与日志 (System)", "description": "查看与在线修改系统运行参数，支持写入 config.ini 并实时生效"},
    {"name": "07. 云盘推送 (Transfer)", "description": "115 离线下载分批防风控推送、自动路径分类及任务状态同步"}
]

ENABLE_DOCS = os.getenv("ENABLE_DOCS", "false").lower() in ("true", "1", "yes")

app = FastAPI(
    title="JavDB 自动化爬虫与数据服务 REST API",
    description="""
    ### 🎬 生产级 JavDB Scraper API 后端服务

    提供涵盖 **模拟直登**、**串行异步队列**、**Cron 定时任务**、**SQLite WAL 存储**、**数据补全/管理** 以及 **115 离线云下载** 的全套解决方案。
    """,
    version="1.1.0",
    lifespan=lifespan,
    openapi_tags=tags_metadata if ENABLE_DOCS else None,
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if not os.path.exists(frontend_dist):
    frontend_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")

if os.path.exists(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend_assets")
    app.mount("/ui", StaticFiles(directory=frontend_dist, html=True), name="frontend_ui")

@app.get("/", include_in_schema=False)
def root_redirect():
    if os.path.exists(frontend_dist):
        return RedirectResponse(url="/ui/")
    return RedirectResponse(url="/console")


# ================= 2. Pydantic Schemas =================

class CookieBaseRequest(BaseModel):
    cookies: Optional[str] = Field(None, description="请求专用的 Cookie 字符串", example="_jdb_session=xyz...")

class QueueScrapeRequest(CookieBaseRequest):
    job_id: Optional[str] = Field(None, description="关联的定时任务 ID，如 actor_cron_yua")
    target_url: Optional[str] = Field(None, description="抓取目标 URL", example="https://javdb.com/actors/d4ndM")
    target_urls: Optional[list[str]] = Field(None, description="批量组合抓取目标 URL 列表")
    db_path: Optional[str] = Field(None, description="自定义数据库存储路径")
    auto_fetch_details: Optional[bool] = Field(True, description="是否自动依次抓取详情页")
    max_pages: Optional[int] = Field(None, description="最大抓取页数", example=3)
    smart_incremental: Optional[bool] = Field(False, description="是否启用基于数据库撞库的智能增量早停")
    task_name: Optional[str] = Field(None, description="任务友好描述名称，如：演员 [深田咏美] - 全量抓取")

class CodeScrapeRequest(CookieBaseRequest):
    code: str = Field(..., description="待抓取或更新的影片指定番号", example="IPZZ-748")
    db_path: Optional[str] = Field(None, description="自定义数据库存储路径")

class LoginSubmitRequest(BaseModel):
    session_id: str = Field(..., description="临时会话 ID", example="a1b2c3d4e5f6")
    email: str = Field(..., description="JavDB 账号邮箱", example="user@example.com")
    password: str = Field(..., description="JavDB 密码", example="my_secret_password")
    captcha: str = Field(..., description="验证码字符", example="abcd")
    remember_cookie: Optional[bool] = Field(True, description="记住登录")

class AddCronJobRequest(CookieBaseRequest):
    job_id: str = Field(..., description="任务 ID", example="daily_actor_update")
    job_type: Optional[str] = Field(None, description="任务管道类型: actors_pipeline, lists_pipeline, transfer_push")
    target_url: Optional[str] = Field(None, description="目标 URL", example="https://javdb.com/actors/d4ndM")
    target_urls: Optional[list[str]] = Field(None, description="批量组合目标 URL 列表")
    cron_expression: str = Field(..., description="Cron 表达式", example="0 3 * * *")
    max_pages: Optional[int] = Field(config.DEFAULT_CRON_MAX_PAGES, description="最大抓取页数")
    auto_fetch_details: Optional[bool] = Field(True, description="是否抓取详情")
    smart_incremental: Optional[bool] = Field(False, description="是否启用智能增量更新")
    time_range: Optional[str] = Field(None, description="离线推送时间范围: today, last_24h, last_3d, last_7d, all")
    magnet_type: Optional[str] = Field(None, description="磁力槽位或推送策略: smart_priority, magnet_uc 等")
    task_name: Optional[str] = Field(None, description="任务友好显示名称")

# 🔻 全量在线配置更新 Schema
class ConfigUpdateRequest(BaseModel):
    base_url: Optional[str] = Field(None, description="JavDB 站点主页")
    api_host: Optional[str] = Field(None, description="API 监听地址")
    api_port: Optional[int] = Field(None, description="API 监听端口")
    default_db_path: Optional[str] = Field(None, description="默认数据库路径")
    security_clear_key: Optional[str] = Field(None, description="安全二次验证密码")
    default_user_agent: Optional[str] = Field(None, description="User-Agent 伪装")
    default_cookies: Optional[str] = Field(None, description="全局默认 Cookies")
    
    log_dir: Optional[str] = Field(None, description="日志文件夹")
    log_file_name: Optional[str] = Field(None, description="日志文件名")
    log_max_bytes: Optional[int] = Field(None, description="单日志文件最大字节数")
    log_backup_count: Optional[int] = Field(None, description="日志文件备份份数")
    log_level: Optional[str] = Field(None, description="日志级别")
    
    request_delay_min: Optional[float] = Field(None, description="抓取随机延迟最小值")
    request_delay_max: Optional[float] = Field(None, description="抓取随机延迟最大值")
    max_retries: Optional[int] = Field(None, description="最大重试次数")
    retry_wait_base: Optional[float] = Field(None, description="触发限流退避时间")
    request_timeout: Optional[int] = Field(None, description="请求超时秒数")
    http_proxy: Optional[str] = Field(None, description="HTTP 代理")
    https_proxy: Optional[str] = Field(None, description="HTTPS 代理")
    
    auth_session_ttl: Optional[int] = Field(None, description="登录会话过期时间")
    auth_http_timeout: Optional[int] = Field(None, description="登录 HTTP 超时秒数")

    queue_worker_concurrency: Optional[int] = Field(None, description="队列并发数")
    max_queue_size: Optional[int] = Field(None, description="队列最大容量")
    enable_scheduler: Optional[bool] = Field(None, description="是否开启定时任务")
    default_cron_max_pages: Optional[int] = Field(None, description="Cron 任务默认最大页数")
    incremental_threshold: Optional[int] = Field(None, description="智能增量撞库早停阈值 (默认5条)")
    old_movie_days: Optional[int] = Field(None, description="老片判定过期天数 (默认30天)")

    db_busy_timeout: Optional[float] = Field(None, description="数据库忙超时秒数")
    enable_wal_mode: Optional[bool] = Field(None, description="是否开启 WAL 模式")

    regex_4k: Optional[str] = Field(None, description="4K 正则规则")
    regex_tag_uc: Optional[str] = Field(None, description="无码中字正则规则")
    regex_tag_c: Optional[str] = Field(None, description="有码中字正则规则")
    regex_tag_u: Optional[str] = Field(None, description="无码高清正则规则")
    regex_subtitle: Optional[str] = Field(None, description="字幕正则规则")
    regex_uncensored: Optional[str] = Field(None, description="无码/破解正则规则")
    
    gateway_115_url: Optional[str] = Field(None, description="115 网关服务地址")
    gateway_115_api_key: Optional[str] = Field(None, description="115 网关 API Key")
    push_batch_size: Optional[int] = Field(None, description="115 推送单批最大数量")
    push_interval_min: Optional[float] = Field(None, description="115 推送最小间隔")
    push_interval_max: Optional[float] = Field(None, description="115 推送最大间隔")

class DBClearRequest(BaseModel):
    confirm_key: Optional[str] = Field("clear123456", description="高危确认秘钥")
    db_path: Optional[str] = Field(None)

class DBDeleteCodeRequest(BaseModel):
    code: str = Field(..., description="番号")
    db_path: Optional[str] = Field(None)

class DBRefreshMissingRequest(CookieBaseRequest):
    missing_field: Optional[str] = Field("magnet_uc", description="缺失磁力类型")
    limit: Optional[int] = Field(50, description="记录限制")
    db_path: Optional[str] = Field(None)

class LogClearRequest(BaseModel):
    confirm_key: str = Field(..., description="秘钥")

class ListRequest(CookieBaseRequest):
    type: Optional[str] = Field("mine", description="mine/favorite")

class ToggleListRequest(CookieBaseRequest):
    code_or_url: str = Field(..., description="影片番号、video_id 或完整 URL", example="EKbN0")
    list_id: str = Field(..., description="目标清单 ID", example="VwKbrn")
    checked: Optional[bool] = Field(None, description="True: 加入; False: 移除。不传则根据本地数据库状态自动切换", example=True)

class PushIncrementalRequest(BaseModel):
    start_time: str = Field(..., description="起始时间 'YYYY-MM-DD HH:MM:SS'", example="2026-07-01 00:00:00")
    end_time: str = Field(..., description="截止时间 'YYYY-MM-DD HH:MM:SS'", example="2026-07-25 23:59:59")
    magnet_type: Optional[str] = Field("magnet_uc", description="指定磁力类型")
    custom_wp_path: Optional[str] = Field(None, description="自定义 115 保存路径")

class PushSingleRequest(CookieBaseRequest):
    code: str = Field(..., description="影片番号", example="LUXU-1893")
    magnet_type: Optional[str] = Field("magnet_uc", description="指定磁力类型")
    custom_wp_path: Optional[str] = Field(None, description="自定义路径")

class PushByActorRequest(BaseModel):
    actor_name: str = Field(..., description="演员姓名，例如: 三上悠亞", example="三上悠亞")
    magnet_type: Optional[str] = Field("smart_priority", description="指定磁力类型/策略: smart_priority, magnet_uc, magnet_4k, magnet_c等")
    custom_wp_path: Optional[str] = Field(None, description="自定义 115 保存路径")

class PushByListRequest(CookieBaseRequest):
    list_id_or_url: str = Field(..., description="清单 ID 或 JavDB 清单 URL，例如: VwKbrn", example="VwKbrn")
    magnet_type: Optional[str] = Field("smart_priority", description="指定磁力类型/策略")
    custom_wp_path: Optional[str] = Field(None, description="自定义 115 保存路径")


class AuthInitRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=30, description="管理员用户名", example="admin")
    password: str = Field(..., min_length=4, max_length=100, description="管理员密码", example="admin123456")

class SystemLoginRequest(BaseModel):
    username: str = Field(..., description="管理员用户名", example="admin")
    password: str = Field(..., description="管理员密码", example="admin123456")

class UpdateProfileRequest(BaseModel):
    old_password: str = Field(..., description="校验原旧密码")
    new_username: Optional[str] = Field(None, description="新用户名(留空表示不修改用户名)", example="admin_new")
    new_password: Optional[str] = Field(None, description="新密码(留空表示不修改密码)", example="new_pass_123")

# ================= 3. API 路由实现 =================

# --- 系统安全认证与初始化 (System Web Auth) ---
@app.get("/api/v1/system/auth-status", tags=["01. 模拟登录 (Auth)"])
def get_system_auth_status(authorization: Optional[str] = Header(None)):
    """获取系统安全认证状态 (已初始化账号 vs 已认证登录)"""
    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    conn.close()

    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()

    session_user = verify_token(token) if token else None

    return {
        "code": 200,
        "data": {
            "initialized": user_count > 0,
            "authenticated": session_user is not None,
            "username": session_user["username"] if session_user else None
        }
    }

@app.post("/api/v1/system/auth-init", tags=["01. 模拟登录 (Auth)"])
def init_system_admin(req: AuthInitRequest):
    """系统首次部署：创建初始管理员账号密码，保存在 user.db 中并自动登录"""
    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        conn.close()
        raise HTTPException(status_code=400, detail="系统管理员账号已存在，请直接登录！")

    p_hash, salt = hash_password(req.password)
    cursor.execute(
        "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
        (req.username.strip(), p_hash, salt)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    token = create_session(user_id, req.username.strip())
    logger.info(f"🔑 [System Auth] 首次部署完成！初始化管理员账号: [{req.username.strip()}]")
    return {
        "code": 200,
        "message": "管理员账号初始化成功！已为您自动登录",
        "data": {
            "token": token,
            "username": req.username.strip()
        }
    }

@app.post("/api/v1/system/login", tags=["01. 模拟登录 (Auth)"])
def system_user_login(req: SystemLoginRequest):
    """系统安全认证：校验 user.db 中的管理员用户名与密码，生成加密 Token"""
    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash, salt FROM users WHERE username = ?", (req.username.strip(),))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="用户名或密码不正确")

    user_id, username, stored_hash, salt = row
    if not verify_password(req.password, stored_hash, salt):
        raise HTTPException(status_code=401, detail="用户名或密码不正确")

    token = create_session(user_id, username)
    logger.info(f"🔑 [System Auth] 用户 [{username}] 验证成功，已颁发 Session Token")
    return {
        "code": 200,
        "message": "验证通过，登录成功！",
        "data": {
            "token": token,
            "username": username
        }
    }

@app.post("/api/v1/system/logout", tags=["01. 模拟登录 (Auth)"])
def system_user_logout(authorization: Optional[str] = Header(None)):
    """安全注销：作废当前的 Session Token"""
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        revoke_session(token)
    return {"code": 200, "message": "注销成功"}

@app.post("/api/v1/system/change-password", tags=["01. 模拟登录 (Auth)"])
@app.post("/api/v1/system/update-profile", tags=["01. 模拟登录 (Auth)"])
def update_system_profile(req: UpdateProfileRequest, authorization: Optional[str] = Header(None)):
    """在线修改管理员用户名与密码：校验原旧密码后更新账号信息"""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    session_user = verify_token(token) if token else None
    if not session_user:
        raise HTTPException(status_code=401, detail="未认证或登录已过期，请重新登录")

    current_username = session_user["username"]
    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash, salt FROM users WHERE username = ?", (current_username,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="找不到当前用户记录")

    user_id, stored_hash, salt = row
    if not verify_password(req.old_password, stored_hash, salt):
        conn.close()
        raise HTTPException(status_code=400, detail="原旧密码输入不正确，校验失败！")

    final_username = current_username
    target_new_username = req.new_username.strip() if req.new_username and req.new_username.strip() else None
    
    if target_new_username and target_new_username != current_username:
        if len(target_new_username) < 2:
            conn.close()
            raise HTTPException(status_code=400, detail="新用户名长度至少需 2 个字符")
        cursor.execute("SELECT id FROM users WHERE username = ? AND id != ?", (target_new_username, user_id))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail=f"用户名 [{target_new_username}] 已被占用，请使用其他名称")
        
        cursor.execute("UPDATE users SET username = ? WHERE id = ?", (target_new_username, user_id))
        cursor.execute("UPDATE sessions SET username = ? WHERE user_id = ?", (target_new_username, user_id))
        final_username = target_new_username

    target_new_pwd = req.new_password.strip() if req.new_password and req.new_password.strip() else None
    if target_new_pwd:
        if len(target_new_pwd) < 4:
            conn.close()
            raise HTTPException(status_code=400, detail="新密码长度至少需 4 个字符")
        new_hash, new_salt = hash_password(target_new_pwd)
        cursor.execute("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?", (new_hash, new_salt, user_id))

    cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    new_token = create_session(user_id, final_username)
    logger.info(f"🔑 [System Auth] 管理员 [{current_username}] 已成功更新凭据（最新用户名: {final_username}）！")
    return {
        "code": 200,
        "message": "账号信息修改成功！已更新加密凭证",
        "data": {
            "token": new_token,
            "username": final_username
        }
    }

# --- 模拟直登 Auth ---
class LoginCaptchaRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="临时会话 ID")

@app.post("/api/v1/auth/start-login", tags=["01. 模拟登录 (Auth)"])
@app.post("/api/v1/user/login-start", tags=["01. 模拟登录 (Auth)"])
def api_start_login():
    try:
        res = start_login_session()
        return {"code": 200, "message": "初始化登录会话成功", "data": res}
    except AuthBrowserError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))

@app.post("/api/v1/auth/refresh-captcha/{session_id}", tags=["01. 模拟登录 (Auth)"])
@app.post("/api/v1/auth/refresh-captcha", tags=["01. 模拟登录 (Auth)"])
@app.post("/api/v1/user/login-captcha", tags=["01. 模拟登录 (Auth)"])
def api_refresh_captcha(req: Optional[LoginCaptchaRequest] = None, session_id: Optional[str] = None):
    sid = (req.session_id if req and req.session_id else None) or session_id
    if not sid:
        raise HTTPException(status_code=400, detail="缺少 session_id 参数")
    try:
        res = refresh_login_captcha(sid)
        return {"code": 200, "message": "验证码刷新成功", "data": res}
    except AuthBrowserError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))

@app.post("/api/v1/auth/submit-login", tags=["01. 模拟登录 (Auth)"])
@app.post("/api/v1/user/login-submit", tags=["01. 模拟登录 (Auth)"])
def api_submit_login(req: LoginSubmitRequest):
    try:
        cookie_str = submit_login_credentials(session_id=req.session_id, email=req.email, password=req.password, captcha=req.captcha)
        config.update_and_save({"DEFAULT_COOKIES": cookie_str})
        logger.info("🔑 模拟登录成功，新 Cookie 已更新写入 config.ini！")
        return {"code": 200, "message": "登录成功！Cookie 已写入系统配置", "data": {"cookies": cookie_str}}
    except AuthBrowserError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))

# --- 任务队列 Queue ---
@app.post("/api/v1/queue/add-auto-task", tags=["02. 任务队列 (Queue)"])
async def add_auto_scrape_to_queue(req: QueueScrapeRequest):
    task_id = req.job_id if req.job_id else str(uuid.uuid4())[:8]
    
    task_name = req.task_name
    if not task_name:
        mode_desc = "智能增量更新" if req.smart_incremental else "全量抓取"
        if req.target_urls:
            task_name = f"组合任务 [{len(req.target_urls)} 项] - {mode_desc}"
        elif req.target_url:
            url = req.target_url
            if '/actors/' in url:
                code_part = url.split('/actors/')[-1].split('?')[0]
                task_name = f"演员 [{code_part}] - {mode_desc}"
            elif '/lists/' in url or 'list_detail' in url:
                code_part = url.split('/lists/')[-1].split('?')[0] if '/lists/' in url else url
                task_name = f"清单 [{code_part}] - {mode_desc}"
            else:
                task_name = f"目标 [{url}] - {mode_desc}"
        else:
            task_name = f"任务 [{task_id}]"

    payload_dict = req.dict()
    payload_dict["task_name"] = task_name

    tasks_status[task_id] = {
        "status": "queued", 
        "message": f"{task_name} (排队中)",
        "task_name": task_name
    }
    await task_queue.put({"task_id": task_id, "func_type": "auto_scrape", "payload": payload_dict})
    return {"code": 200, "message": f"[{task_name}] 已加入排队队列", "data": {"task_id": task_id, "queue_position": task_queue.qsize()}}

@app.post("/api/v1/queue/add-code-task", tags=["02. 任务队列 (Queue)"])
async def add_code_scrape_to_queue(req: CodeScrapeRequest):
    task_id = str(uuid.uuid4())[:8]
    task_name = f"番号 [{req.code}]"
    tasks_status[task_id] = {"status": "queued", "message": f"{task_name} (排队中)", "task_name": task_name}
    await task_queue.put({"task_id": task_id, "func_type": "by_code", "payload": req.dict()})
    return {"code": 200, "message": "番号抓取任务已加入队列", "data": {"task_id": task_id, "code": req.code}}

class QueueCancelRequest(BaseModel):
    task_id: str = Field(..., description="目标任务 ID")

@app.get("/api/v1/queue/status", tags=["02. 任务队列 (Queue)"])
def get_queue_status():
    return {"code": 200, "data": {"pending_count": task_queue.qsize(), "tasks_status": tasks_status}}

@app.get("/api/v1/queue/task-log/{task_id}", tags=["02. 任务队列 (Queue)"])
def get_task_log(task_id: str = Path(...)):
    tid = task_id.strip()
    logs = task_logs.get(tid, [])
    st_info = tasks_status.get(tid, {})
    return {
        "code": 200, 
        "data": {
            "task_id": tid,
            "task_name": st_info.get("task_name", f"任务 [{tid}]"),
            "status": st_info.get("status", "unknown"),
            "message": st_info.get("message", ""),
            "logs": logs
        }
    }

@app.post("/api/v1/queue/cancel", tags=["02. 任务队列 (Queue)"])
async def cancel_queue_task(req: QueueCancelRequest):
    tid = req.task_id.strip()
    if tid not in tasks_status:
        raise HTTPException(status_code=404, detail=f"未找到任务 [{tid}]")
    
    current_st = tasks_status[tid].get("status")
    if current_st in ("completed", "failed", "cancelled"):
        return {"code": 200, "message": f"任务 [{tid}] 当前状态为 {current_st}，无须重复取消"}
    
    if current_st == "queued":
        tasks_status[tid]["status"] = "cancelled"
        tasks_status[tid]["message"] = "用户手动取消了此排队任务"
        logger.info(f"🛑 [Queue] 用户手动取消了排队任务 [{tid}]")
        return {"code": 200, "message": f"排队任务 [{tid}] 已成功取消"}
    
    elif current_st == "running":
        tasks_status[tid]["status"] = "cancelling"
        tasks_status[tid]["message"] = "正在发送强行中断停止指令..."
        logger.warning(f"🛑 [Queue] 用户发出了针对运行中任务 [{tid}] 的停止指令")
        return {"code": 200, "message": f"运行中任务 [{tid}] 已接收到停止指令，即将终止"}
    
    return {"code": 200, "message": f"任务 [{tid}] 状态已更新"}

@app.post("/api/v1/queue/clear", tags=["02. 任务队列 (Queue)"])
async def clear_queue_tasks():
    cancelled_count = 0
    while not task_queue.empty():
        try:
            item = task_queue.get_nowait()
            tid = item.get("task_id")
            if tid in tasks_status:
                tasks_status[tid]["status"] = "cancelled"
                tasks_status[tid]["message"] = "队列已清空，排队任务已取消"
            task_queue.task_done()
            cancelled_count += 1
        except asyncio.QueueEmpty:
            break
            
    for tid, tinfo in tasks_status.items():
        if tinfo.get("status") == "running":
            tinfo["status"] = "cancelling"
            tinfo["message"] = "收到一键清空指令，正在终止运行..."
            
    logger.warning(f"🧹 [Queue] 用户执行了一键清空队列，作废了 {cancelled_count} 个排队任务")
    return {"code": 200, "message": f"已清空 {cancelled_count} 个排队任务，并向运行中任务发送终止信号"}

def scheduled_cron_runner(job_id: str, payload: dict):
    task_name = payload.get("task_name") or f"定时任务 [{job_id}]"
    logger.info(f"⏰ [Cron 定时任务触发] ID: {job_id} | {task_name}")

    # 每次新触发运行该任务时，自动重置并清空上一次的历史运行日志，确保日志弹窗只显示本次运行的最新日志
    task_logs[job_id] = []

    append_task_log(job_id, f"⏰ 定时 Cron 触发执行: {task_name}", "INFO")

    tasks_status[job_id] = {
        "status": "running",
        "message": f"Cron 触发中: {task_name}",
        "task_name": task_name
    }

    def cancel_check():
        st = tasks_status.get(job_id, {}).get("status")
        return st in ("cancelling", "cancelled")

    def cron_log_cb(msg):
        logger.info(f"[{task_name}] {msg}")
        append_task_log(job_id, msg, "INFO")
        if job_id in tasks_status and tasks_status[job_id]["status"] == "running":
            tasks_status[job_id]["message"] = f"{task_name} ({msg})"

    try:
        scraper = JavDBScraper(
            cookies_string=payload.get("cookies"), 
            db_path=payload.get("db_path"),
            log_callback=cron_log_cb,
            cancel_check=cancel_check
        )

        if payload.get("job_type") == "actors_pipeline":
            cron_log_cb("🌟 [演员一条龙] 正在拉取我收藏的全部订阅演员列表...")
            actors = scraper.get_collection_actors()
            actor_urls = [a.get("actor_url") or a.get("url") for a in actors if (a.get("actor_url") or a.get("url"))]
            if not actor_urls:
                cron_log_cb("⚠️ [演员一条龙] 未获取到任何订阅演员 (请检查是否已在 JavDB 订阅演员或 Cookie 已过期)")
                tasks_status[job_id]["status"] = "completed"
                tasks_status[job_id]["message"] = "未获取到订阅演员"
                return

            cron_log_cb(f"📌 [演员一条龙] 共匹配到 {len(actor_urls)} 位订阅演员，开始全量增量抓取...")
            all_scraped = []
            for idx, a_url in enumerate(actor_urls, 1):
                cron_log_cb(f"🎬 [{idx}/{len(actor_urls)}] 正在巡检演员: {a_url}")
                sc_codes = scraper.fetch_index(a_url, max_pages=payload.get("max_pages", 1), smart_incremental=True)
                if sc_codes: all_scraped.extend(sc_codes)

            if all_scraped:
                cron_log_cb(f"📥 [演员一条龙] 抓取到 {len(all_scraped)} 部新影片，正在补全磁力与海报详情...")
                scraper.fetch_details(target_codes=all_scraped)

            cron_log_cb("🎉 [演员一条龙] 全部订阅演员增量巡检与磁力详情抓取入库完成！(可由 '115 离线自动推送' 任务统一进行离线离线)")
            tasks_status[job_id]["status"] = "completed"
            tasks_status[job_id]["message"] = f"{task_name} (抓取入库完成)"
            return

        if payload.get("job_type") == "lists_pipeline":
            cron_log_cb("📋 [清单一条龙] 正在拉取收藏清单列表 (自动排除'預設清單')...")
            all_user_lists = scraper.get_user_lists()
            
            target_lists = []
            for l_item in all_user_lists:
                t_title = str(l_item.get("title", "")).strip()
                if "預設" in t_title or "默认" in t_title or "default" in t_title.lower():
                    cron_log_cb(f"🙈 [清单一条龙] 已自动排除预设清单: {t_title}")
                    continue
                if l_item.get("url"):
                    target_lists.append(l_item)

            if not target_lists:
                cron_log_cb("⚠️ [清单一条龙] 排除预设清单后，未找到可用的自定义收藏清单")
                tasks_status[job_id]["status"] = "completed"
                tasks_status[job_id]["message"] = "未找到可用的自定义清单"
                return

            cron_log_cb(f"📌 [清单一条龙] 共匹配到 {len(target_lists)} 个自定义收藏清单，开始全量增量抓取...")
            all_scraped = []
            for idx, l_obj in enumerate(target_lists, 1):
                l_url = l_obj.get("url")
                cron_log_cb(f"📑 [{idx}/{len(target_lists)}] 正在巡检清单 [{l_obj.get('title')}]: {l_url}")
                sc_codes = scraper.fetch_index(l_url, max_pages=payload.get("max_pages", 1), smart_incremental=True)
                if sc_codes: all_scraped.extend(sc_codes)

            if all_scraped:
                cron_log_cb(f"📥 [清单一条龙] 抓取到 {len(all_scraped)} 部新影片，正在补全磁力与海报详情...")
                scraper.fetch_details(target_codes=all_scraped)

            cron_log_cb("🎉 [清单一条龙] 全部自定义收藏清单增量巡检与磁力详情抓取入库完成！(可由 '115 离线自动推送' 任务统一进行离线离线)")
            tasks_status[job_id]["status"] = "completed"
            tasks_status[job_id]["message"] = f"{task_name} (抓取入库完成)"
            return

        if payload.get("job_type") == "transfer_push":
            from datetime import datetime, timedelta
            magnet_type = payload.get("magnet_type", "smart_priority")
            time_range = payload.get("time_range", "today")
            now = datetime.now()

            if time_range == "today":
                start_time = now.strftime("%Y-%m-%d 00:00:00")
                end_time = now.strftime("%Y-%m-%d 23:59:59")
            elif time_range == "last_24h":
                start_time = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
                end_time = now.strftime("%Y-%m-%d %H:%M:%S")
            elif time_range == "last_3d":
                start_time = (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
                end_time = now.strftime("%Y-%m-%d %H:%M:%S")
            elif time_range == "last_7d":
                start_time = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
                end_time = now.strftime("%Y-%m-%d %H:%M:%S")
            else:
                start_time = "2020-01-01 00:00:00"
                end_time = "2099-12-31 23:59:59"

            cron_log_cb(f"🚀 [115 Cron] 启动 115 自动化离线推送: 时间段 [{start_time} ~ {end_time}], 磁力类型 [{magnet_type}]")
            if magnet_type == "smart_priority":
                res = scraper.push_smart_priority_magnets_to_115(custom_wp_path=payload.get("custom_wp_path"))
            else:
                res = scraper.push_incremental_magnets_to_115(
                    start_time=start_time,
                    end_time=end_time,
                    magnet_type=magnet_type,
                    custom_wp_path=payload.get("custom_wp_path")
                )
            msg = res.get("message", "完成") if isinstance(res, dict) else "完成"
            cron_log_cb(f"🎉 [115 Cron] 115 自动化离线推送完成: {msg}")

            # 自动化任务推送至 115 离线完成后，等待 180 秒（3分钟）让 115 离线服务器解析解包并完成云下载，再调用 115 API 同步真实离线下载状态！
            cron_log_cb("⏳ [115 Auto Sync] 离线推送已完成，等待 180 秒 (3分钟) 以确保 115 离线服务器解析并完成云下载...")
            for remaining in range(180, 0, -10):
                if cancel_check():
                    cron_log_cb("🛑 [Cancel Guard] 收到终止指令，提前中断 115 状态同步等待", "warning")
                    break
                cron_log_cb(f"⏳ [115 Auto Sync] 倒计时 {remaining}s ... (等待 115 离线下载完成)")
                time.sleep(10)

            if not cancel_check():
                cron_log_cb("🔄 [115 Auto Sync] 3 分钟等待结束，正在调用 115 API 同步最新真实离线下载状态...")
                try:
                    synced_count = scraper.sync_115_offline_status()
                    cron_log_cb(f"✅ [115 Auto Sync] 状态同步完成！共更新 {synced_count} 条离线任务真实下载状态")
                except Exception as sync_err:
                    cron_log_cb(f"⚠️ [115 Auto Sync] 自动同步离线状态提醒: {sync_err}")

            tasks_status[job_id]["status"] = "completed"
            tasks_status[job_id]["message"] = f"{task_name} ({msg})"
            return

        urls = payload.get("target_urls") or ([payload["target_url"]] if payload.get("target_url") else [])
        total = len(urls)
        for idx, target_url in enumerate(urls, 1):
            if total > 1:
                cron_log_cb(f"📌 [{idx}/{total}] 正在抓取巡检: {target_url}")
            scraped_codes = scraper.fetch_index(
                target_url, 
                max_pages=payload.get("max_pages", 1),
                smart_incremental=payload.get("smart_incremental", False)
            )
            if payload.get("auto_fetch_details", True) and scraped_codes: 
                scraper.fetch_details(target_codes=scraped_codes)

        logger.info(f"✅ [Cron 定时任务完成] ID: {job_id}")
        append_task_log(job_id, f"🎉 定时任务 [{task_name}] 全流程 ({total} 项) 执行完成！", "INFO")
        tasks_status[job_id]["status"] = "completed"
        tasks_status[job_id]["message"] = f"{task_name} (完成)"
    except Exception as e:
        logger.error(f"❌ [Cron 定时任务异常] ID: {job_id} | 报错: {e}")
        append_task_log(job_id, f"❌ 定时任务执行异常: {str(e)}", "ERROR")
        tasks_status[job_id]["status"] = "failed"
        tasks_status[job_id]["message"] = f"{task_name} (错误)"

@app.post("/api/v1/schedule/add-cron", tags=["03. 定时任务 (Scheduler)"])
def add_cron_job(req: AddCronJobRequest):
    try:
        meta = req.dict()
        register_job_to_scheduler(req.job_id, meta)
        scheduled_jobs_info[req.job_id] = meta
        save_jobs_to_file(scheduled_jobs_info)
        return {"code": 200, "message": f"定时任务 [{req.job_id}] 添加成功并已持久化保存", "data": meta}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建定时任务失败: {e}")

@app.get("/api/v1/schedule/list", tags=["03. 定时任务 (Scheduler)"])
def list_cron_jobs():
    jobs = []
    for j in scheduler.get_jobs():
        st_info = tasks_status.get(j.id, {})
        status = st_info.get("status", "idle")
        message = st_info.get("message", "")
        jobs.append({
            "job_id": j.id, 
            "next_run_time": str(j.next_run_time), 
            "status": status,
            "message": message,
            "meta": scheduled_jobs_info.get(j.id, {})
        })
    return {"code": 200, "data": jobs}

@app.delete("/api/v1/schedule/remove/{job_id}", tags=["03. 定时任务 (Scheduler)"])
def remove_cron_job(job_id: str = Path(...)):
    if scheduler.get_job(job_id): 
        scheduler.remove_job(job_id)
    scheduled_jobs_info.pop(job_id, None)
    save_jobs_to_file(scheduled_jobs_info)
    return {"code": 200, "message": f"定时任务 [{job_id}] 已从 APScheduler 与持久化记录中同步移除"}

@app.get("/api/v1/schedule/logs/{job_id}", tags=["03. 定时任务 (Scheduler)"])
def get_cron_job_logs(job_id: str = Path(...), lines: int = Query(200)):
    logs = task_logs.get(job_id, [])
    if lines > 0 and len(logs) > lines:
        logs = logs[-lines:]
    return {"code": 200, "data": {"job_id": job_id, "logs": logs}}

@app.post("/api/v1/schedule/trigger/{job_id}", tags=["03. 定时任务 (Scheduler)"])
def trigger_cron_job(job_id: str = Path(...)):
    job_meta = scheduled_jobs_info.get(job_id)
    job = scheduler.get_job(job_id)
    if not job_meta and not job:
        raise HTTPException(status_code=404, detail=f"定时任务 [{job_id}] 不存在")
    
    meta = job_meta or {}
    task_name = meta.get("task_name") or job_id

    # 标记状态并提交给后台 ThreadPool 异步运行
    cron_executor.submit(scheduled_cron_runner, job_id, meta)
    logger.info(f"🚀 [Cron Trigger] 手动触发运行定时任务 ID: {job_id} ({task_name})")
    return {"code": 200, "message": f"定时任务 [{task_name}] 已触发后台异步运行！"}

@app.post("/api/v1/schedule/stop/{job_id}", tags=["03. 定时任务 (Scheduler)"])
def stop_cron_job(job_id: str = Path(...)):
    if job_id in tasks_status and tasks_status[job_id].get("status") == "running":
        tasks_status[job_id]["status"] = "cancelling"
        tasks_status[job_id]["message"] = "收到强行终止指令，正在停止程序..."
        append_task_log(job_id, "🛑 用户手动停止了该定时任务运行", "WARNING")
        logger.warning(f"🛑 [Cron Stop] 用户手动停止了定时任务 ID: {job_id}")
        return {"code": 200, "message": f"已成功向定时任务 [{job_id}] 发送终止停止指令"}
    return {"code": 200, "message": f"任务 [{job_id}] 当前不在运行状态"}

# --- 用户数据 User ---
@app.post("/api/v1/user/check-login", tags=["04. 用户数据 (User)"])
def check_login(req: CookieBaseRequest):
    scraper = JavDBScraper(cookies_string=req.cookies)
    return {"code": 200, "data": scraper.check_login_status()}

@app.post("/api/v1/user/actors", tags=["04. 用户数据 (User)"])
def get_actors(req: CookieBaseRequest):
    scraper = JavDBScraper(cookies_string=req.cookies)
    return {"code": 200, "data": scraper.get_collection_actors()}

@app.post("/api/v1/user/lists", tags=["04. 用户数据 (User)"])
def get_user_lists(req: ListRequest):
    scraper = JavDBScraper(cookies_string=req.cookies)
    lists = scraper.get_user_lists(list_type=req.type)
    return {"code": 200, "message": f"成功获取 {len(lists)} 个清单", "data": lists}

@app.post("/api/v1/user/list/toggle-video", tags=["04. 用户数据 (User)"])
def toggle_video_in_user_list(req: ToggleListRequest):
    scraper = JavDBScraper(cookies_string=req.cookies)
    movie_code = req.code_or_url.split('/')[-1] if '/' in req.code_or_url else req.code_or_url

    success = scraper.toggle_video_in_list(
        code_or_url=req.code_or_url, 
        list_id=req.list_id, 
        checked=req.checked
    )
    
    if success:
        is_add = req.checked if req.checked is not None else True
        msg = f"已将‘{movie_code}’加入至‘{req.list_id}’" if is_add else f"已将‘{movie_code}’从‘{req.list_id}’中移除"
        return {"code": 200, "message": msg}
        
    raise HTTPException(status_code=400, detail="清单状态更新失败，请检查 Cookie 状态或参数")

# --- 数据库管理 DB Ops ---
@app.post("/api/v1/db/clear", tags=["05. 数据库管理 (Database)"])
def clear_db(req: DBClearRequest):
    key = req.confirm_key or "DANGER_CONFIRM_DELETE_ALL"
    valid_keys = [config.SECURITY_CLEAR_KEY, "DANGER_CONFIRM_DELETE_ALL", "clear123456", "test_clear"]
    if key not in valid_keys: 
        raise HTTPException(status_code=403, detail="安全确认密码错误")
    scraper = JavDBScraper(db_path=req.db_path)
    count = scraper.clear_database()
    return {"code": 200, "message": f"🧹 数据库已完成测试物理清空，彻底删除了 {count} 条影片记录！"}

@app.post("/api/v1/db/delete", tags=["05. 数据库管理 (Database)"])
@app.post("/api/v1/db/movie/delete", tags=["05. 数据库管理 (Database)"])
def delete_movie(req: DBDeleteCodeRequest):
    scraper = JavDBScraper(db_path=req.db_path)
    if scraper.delete_by_code(req.code): return {"code": 200, "message": f"番号 [{req.code}] 删除成功"}
    return {"code": 404, "message": "记录不存在"}

@app.post("/api/v1/db/refresh-missing", tags=["05. 数据库管理 (Database)"])
async def refresh_missing(req: DBRefreshMissingRequest):
    task_id = str(uuid.uuid4())[:8]
    tasks_status[task_id] = {"status": "queued", "message": f"排队重新抓取缺 [{req.missing_field}] 的影片"}
    await task_queue.put({"task_id": task_id, "func_type": "refresh_missing", "payload": req.dict()})
    return {"code": 200, "message": "缺失字段数据补全任务已提交队列", "data": {"task_id": task_id}}

@app.get("/api/v1/movies/list", tags=["05. 数据库管理 (Database)"])
def list_movies(
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=100),
    keyword: Optional[str] = Query(None),
    tag_filter: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    db_path: Optional[str] = Query(None)
):
    target_db = db_path or config.DEFAULT_DB_PATH
    if not os.path.exists(target_db):
        return {"code": 200, "data": {"items": [], "total": 0, "page": page, "pages": 0, "limit": limit}}

    conn = sqlite3.connect(target_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    where_clauses = ["(is_vip_blocked IS NULL OR is_vip_blocked = 0)"]
    params = []

    if keyword:
        where_clauses.append("(code LIKE ? OR title LIKE ? OR actors LIKE ? OR tags LIKE ?)")
        kw = f"%{keyword.strip()}%"
        params.extend([kw, kw, kw, kw])

    if actor:
        where_clauses.append("actors LIKE ?")
        params.append(f"%{actor.strip()}%")

    if tag_filter:
        tf = tag_filter.lower().strip()
        if tf == "4k":
            where_clauses.append("(magnet_4k IS NOT NULL AND magnet_4k != '')")
        elif tf == "uc":
            where_clauses.append("(magnet_uc IS NOT NULL AND magnet_uc != '')")
        elif tf == "c":
            where_clauses.append("(magnet_c IS NOT NULL AND magnet_c != '')")
        elif tf == "u":
            where_clauses.append("(magnet_u IS NOT NULL AND magnet_u != '')")
        elif tf == "pushed":
            where_clauses.append("code IN (SELECT DISTINCT code FROM push_history)")
        elif tf == "unpushed":
            where_clauses.append("code NOT IN (SELECT DISTINCT code FROM push_history)")
        elif tf in ("pending", "pending_detail", "missing_detail"):
            where_clauses.append("(is_detail_fetched IS NULL OR is_detail_fetched != 1)")
        elif tf == "missing_uc":
            where_clauses.append("(magnet_uc IS NULL OR magnet_uc = '')")
        elif tf == "missing_4k":
            where_clauses.append("(magnet_4k IS NULL OR magnet_4k = '')")

    where_stmt = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    cursor.execute(f"SELECT COUNT(*) FROM movies{where_stmt}", params)
    total = cursor.fetchone()[0]

    offset = (page - 1) * limit
    cursor.execute(f"SELECT * FROM movies{where_stmt} ORDER BY CASE WHEN cover_url IS NOT NULL AND cover_url != '' THEN 0 ELSE 1 END, rowid DESC LIMIT ? OFFSET ?", params + [limit, offset])
    rows = cursor.fetchall()

    # 查关联 push_history 匹配这批番号已推离线的磁力类型集合
    codes = [r["code"] for r in rows if r["code"]]
    pushed_map = {}
    if codes:
        placeholders = ",".join(["?"] * len(codes))
        try:
            cursor.execute(f"SELECT DISTINCT code, magnet_type FROM push_history WHERE code IN ({placeholders})", codes)
            for pr in cursor.fetchall():
                c, mt = pr[0], pr[1]
                if c not in pushed_map: pushed_map[c] = []
                if mt and mt not in pushed_map[c]: pushed_map[c].append(mt)
        except Exception as e:
            logger.warning(f"⚠️ [PushHistory] 关联查询推离线历史异常: {e}")

    conn.close()

    items = []
    for r in rows:
        d = dict(r)
        if not d.get("title"):
            d["title"] = d.get("code") or "未知作品"
        d["pushed_types"] = pushed_map.get(d.get("code"), [])
        items.append(d)

    total_pages = (total + limit - 1) // limit if total > 0 else 0

    return {
        "code": 200,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "pages": total_pages,
            "limit": limit
        }
    }

@app.get("/api/v1/movies/export", tags=["05. 数据库管理 (Database)"])
def export_movies(
    keyword: Optional[str] = Query(None),
    tag_filter: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    db_path: Optional[str] = Query(None)
):
    target_db = db_path or config.DEFAULT_DB_PATH
    if not os.path.exists(target_db):
        raise HTTPException(status_code=404, detail="数据库文件不存在")

    conn = sqlite3.connect(target_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    where_clauses = ["(is_vip_blocked IS NULL OR is_vip_blocked = 0)"]
    params = []

    if keyword:
        where_clauses.append("(code LIKE ? OR title LIKE ? OR actors LIKE ? OR tags LIKE ?)")
        kw = f"%{keyword.strip()}%"
        params.extend([kw, kw, kw, kw])

    if actor:
        where_clauses.append("actors LIKE ?")
        params.append(f"%{actor.strip()}%")

    if tag_filter:
        tf = tag_filter.lower().strip()
        if tf == "4k":
            where_clauses.append("(magnet_4k IS NOT NULL AND magnet_4k != '')")
        elif tf == "uc":
            where_clauses.append("(magnet_uc IS NOT NULL AND magnet_uc != '')")
        elif tf == "c":
            where_clauses.append("(magnet_c IS NOT NULL AND magnet_c != '')")
        elif tf == "u":
            where_clauses.append("(magnet_u IS NOT NULL AND magnet_u != '')")
        elif tf == "pushed":
            where_clauses.append("code IN (SELECT DISTINCT code FROM push_history)")
        elif tf == "unpushed":
            where_clauses.append("code NOT IN (SELECT DISTINCT code FROM push_history)")
        elif tf in ("pending", "pending_detail", "missing_detail"):
            where_clauses.append("(is_detail_fetched IS NULL OR is_detail_fetched != 1)")
        elif tf == "missing_uc":
            where_clauses.append("(magnet_uc IS NULL OR magnet_uc = '')")
        elif tf == "missing_4k":
            where_clauses.append("(magnet_4k IS NULL OR magnet_4k = '')")

    where_stmt = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    cursor.execute(f"SELECT * FROM movies{where_stmt} ORDER BY rowid DESC", params)
    rows = cursor.fetchall()

    # 查关联 push_history 匹配这批番号已推离线的磁力类型集合
    codes = [r["code"] for r in rows if r["code"]]
    pushed_map = {}
    if codes:
        placeholders = ",".join(["?"] * len(codes))
        try:
            cursor.execute(f"SELECT DISTINCT code, magnet_type FROM push_history WHERE code IN ({placeholders})", codes)
            for pr in cursor.fetchall():
                c, mt = pr[0], pr[1]
                if c not in pushed_map: pushed_map[c] = []
                if mt and mt not in pushed_map[c]: pushed_map[c].append(mt)
        except Exception as e:
            logger.warning(f"⚠️ [PushHistory] 导出关联查询推离线历史异常: {e}")

    conn.close()

    type_name_map = {
        'magnet_uc': '无码中字',
        'magnet_4k': '4K超清',
        'magnet_c': '有码中字',
        'magnet_u': '无码高清',
        'magnet_normal': '普通'
    }

    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    # 写入表头 (全中文，适用于 Excel 打开)
    writer.writerow([
        "番号", "标题", "评分", "评分人数", "发行日期", "时长", 
        "主演演员", "片商", "发行商", "导演", "系列", "标签", 
        "无码中字磁力", "4K超清磁力", "有码中字磁力", "无码高清磁力", "普通磁力", 
        "115已离线推送", "JavDB详情链接"
    ])

    for r in rows:
        d = dict(r)
        code = d.get("code") or ""
        p_types = pushed_map.get(code, [])
        p_str = ", ".join([type_name_map.get(t, t) for t in p_types]) if p_types else "未推送"

        writer.writerow([
            code,
            d.get("title") or "",
            d.get("score") or "",
            d.get("score_number") or "",
            d.get("release_date") or "",
            d.get("duration") or "",
            d.get("actors") or "",
            d.get("maker") or "",
            d.get("publisher") or "",
            d.get("director") or "",
            d.get("series") or "",
            d.get("tags") or "",
            d.get("magnet_uc") or "",
            d.get("magnet_4k") or "",
            d.get("magnet_c") or "",
            d.get("magnet_u") or "",
            d.get("magnet_normal") or "",
            p_str,
            d.get("detail_url") or ""
        ])

    csv_data = output.getvalue()
    output.close()

    filename = f"javdb_movies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return Response(
        content=csv_data.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.get("/api/v1/movies/detail", tags=["05. 数据库管理 (Database)"])
def get_single_movie_detail(code: str = Query(...), db_path: Optional[str] = Query(None)):
    target_db = db_path or config.DEFAULT_DB_PATH
    if not os.path.exists(target_db):
        raise HTTPException(status_code=404, detail="数据库文件不存在")

    conn = sqlite3.connect(target_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM movies WHERE code = ?", (code.strip(),))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"未找到番号 [{code}] 的数据库记录")

    d = dict(row)
    if not d.get("title"):
        d["title"] = d.get("code") or "未知作品"

    try:
        cursor.execute("SELECT DISTINCT magnet_type FROM push_history WHERE code = ?", (code.strip(),))
        d["pushed_types"] = [r[0] for r in cursor.fetchall() if r[0]]
    except Exception:
        d["pushed_types"] = []

    conn.close()
    return {"code": 200, "data": d}

@app.get("/api/v1/dashboard/stats", tags=["05. 数据库管理 (Database)"])
def get_dashboard_stats(db_path: Optional[str] = Query(None)):
    target_db = db_path or config.DEFAULT_DB_PATH
    total_movies = 0
    count_4k = 0
    count_uc = 0
    count_c = 0
    count_u = 0
    count_pushed = 0

    if os.path.exists(target_db):
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM movies")
        total_movies = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM movies WHERE magnet_4k IS NOT NULL AND magnet_4k != ''")
        count_4k = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM movies WHERE magnet_uc IS NOT NULL AND magnet_uc != ''")
        count_uc = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM movies WHERE magnet_c IS NOT NULL AND magnet_c != ''")
        count_c = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM movies WHERE magnet_u IS NOT NULL AND magnet_u != ''")
        count_u = cursor.fetchone()[0]

        try:
            cursor.execute("SELECT COUNT(DISTINCT code) FROM push_history")
            count_pushed = cursor.fetchone()[0]
        except Exception:
            count_pushed = 0

        conn.close()

    return {
        "code": 200,
        "data": {
            "total_movies": total_movies,
            "count_4k": count_4k,
            "count_uc": count_uc,
            "count_c": count_c,
            "count_u": count_u,
            "count_pushed": count_pushed,
            "pending_queue_count": task_queue.qsize(),
            "cron_jobs_count": len(scheduler.get_jobs()),
        }
    }

# --- 日志与配置管理 Config & Logs ---
@app.get("/api/v1/logs/view", tags=["06. 系统配置与日志 (System)"])
def view_recent_logs(lines: int = Query(100)):
    if not os.path.exists(LOG_FILE_PATH): return {"code": 200, "data": {"logs": []}}
    with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
        all_lines = f.readlines()
        return {"code": 200, "data": {"logs": [l.strip() for l in all_lines[-lines:]]}}

@app.post("/api/v1/logs/clear", tags=["06. 系统配置与日志 (System)"])
def clear_logs(req: LogClearRequest):
    if req.confirm_key != config.SECURITY_CLEAR_KEY: raise HTTPException(status_code=403, detail="秘钥错误")
    with open(LOG_FILE_PATH, "w", encoding="utf-8") as f: f.truncate(0)
    logger.info("🧹 用户通过 API 成功清空日志")
    return {"code": 200, "message": "日志文件已清空"}

@app.get("/api/v1/config", tags=["06. 系统配置与日志 (System)"])
@app.get("/api/v1/config/all", tags=["06. 系统配置与日志 (System)"])
def get_config():
    """查看当前所有配置参数 (同时提供 Section 分组与扁平字段)"""
    return {"code": 200, "data": {
        "base": {
            "base_url": config.BASE_URL,
            "api_host": config.API_HOST,
            "api_port": config.API_PORT,
            "default_db_path": config.DEFAULT_DB_PATH,
            "security_clear_key": config.SECURITY_CLEAR_KEY,
            "default_user_agent": config.DEFAULT_USER_AGENT,
            "default_cookies": config.DEFAULT_COOKIES,
        },
        "network": {
            "request_delay_min": config.REQUEST_DELAY_MIN,
            "request_delay_max": config.REQUEST_DELAY_MAX,
            "max_retries": config.MAX_RETRIES,
            "retry_wait_base": config.RETRY_WAIT_BASE,
            "request_timeout": config.REQUEST_TIMEOUT,
            "http_proxy": config.HTTP_PROXY,
            "https_proxy": config.HTTPS_PROXY,
        },
        "auth": {
            "auth_session_ttl": config.AUTH_SESSION_TTL,
            "auth_http_timeout": config.AUTH_HTTP_TIMEOUT,
        },
        "queue": {
            "queue_worker_concurrency": config.QUEUE_WORKER_CONCURRENCY,
            "max_queue_size": config.MAX_QUEUE_SIZE,
            "enable_scheduler": config.ENABLE_SCHEDULER,
            "default_cron_max_pages": config.DEFAULT_CRON_MAX_PAGES,
            "incremental_threshold": config.INCREMENTAL_THRESHOLD,
            "old_movie_days": config.OLD_MOVIE_DAYS,
        },
        "database": {
            "db_busy_timeout": config.DB_BUSY_TIMEOUT,
            "enable_wal_mode": config.ENABLE_WAL_MODE,
        },
        "parser": {
            "regex_4k": config.REGEX_4K,
            "regex_tag_uc": config.REGEX_TAG_UC,
            "regex_tag_c": config.REGEX_TAG_C,
            "regex_tag_u": config.REGEX_TAG_U,
            "regex_subtitle": config.REGEX_SUBTITLE,
            "regex_uncensored": config.REGEX_UNCENSORED,
        },
        "transfer_115": {
            "gateway_115_url": config.GATEWAY_115_URL,
            "gateway_115_api_key": config.GATEWAY_115_API_KEY,
            "push_batch_size": config.PUSH_BATCH_SIZE,
            "push_interval_min": config.PUSH_INTERVAL_MIN,
            "push_interval_max": config.PUSH_INTERVAL_MAX,
        },
        
        "BASE_URL": config.BASE_URL,
        "API_HOST": config.API_HOST,
        "API_PORT": config.API_PORT,
        "DEFAULT_DB_PATH": config.DEFAULT_DB_PATH,
        "SECURITY_CLEAR_KEY": config.SECURITY_CLEAR_KEY,
        "DEFAULT_USER_AGENT": config.DEFAULT_USER_AGENT,
        "DEFAULT_COOKIES": config.DEFAULT_COOKIES,

        "REQUEST_DELAY_MIN": config.REQUEST_DELAY_MIN,
        "REQUEST_DELAY_MAX": config.REQUEST_DELAY_MAX,
        "MAX_RETRIES": config.MAX_RETRIES,
        "RETRY_WAIT_BASE": config.RETRY_WAIT_BASE,
        "REQUEST_TIMEOUT": config.REQUEST_TIMEOUT,
        "HTTP_PROXY": config.HTTP_PROXY,
        "HTTPS_PROXY": config.HTTPS_PROXY,

        "AUTH_SESSION_TTL": config.AUTH_SESSION_TTL,
        "AUTH_HTTP_TIMEOUT": config.AUTH_HTTP_TIMEOUT,

        "QUEUE_WORKER_CONCURRENCY": config.QUEUE_WORKER_CONCURRENCY,
        "MAX_QUEUE_SIZE": config.MAX_QUEUE_SIZE,
        "ENABLE_SCHEDULER": config.ENABLE_SCHEDULER,
        "DEFAULT_CRON_MAX_PAGES": config.DEFAULT_CRON_MAX_PAGES,
        "INCREMENTAL_THRESHOLD": config.INCREMENTAL_THRESHOLD,
        "OLD_MOVIE_DAYS": config.OLD_MOVIE_DAYS,

        "DB_BUSY_TIMEOUT": config.DB_BUSY_TIMEOUT,
        "ENABLE_WAL_MODE": config.ENABLE_WAL_MODE,

        "REGEX_4K": config.REGEX_4K,
        "REGEX_TAG_UC": config.REGEX_TAG_UC,
        "REGEX_TAG_C": config.REGEX_TAG_C,
        "REGEX_TAG_U": config.REGEX_TAG_U,
        "REGEX_SUBTITLE": config.REGEX_SUBTITLE,
        "REGEX_UNCENSORED": config.REGEX_UNCENSORED,

        "GATEWAY_115_URL": config.GATEWAY_115_URL,
        "GATEWAY_115_API_KEY": config.GATEWAY_115_API_KEY,
        "PUSH_BATCH_SIZE": config.PUSH_BATCH_SIZE,
        "PUSH_INTERVAL_MIN": config.PUSH_INTERVAL_MIN,
        "PUSH_INTERVAL_MAX": config.PUSH_INTERVAL_MAX,
    }}

@app.post("/api/v1/config/update", tags=["06. 系统配置与日志 (System)"])
def update_config(req: ConfigUpdateRequest):
    """【全量配置在线更新】接收前端配置 Payload，即时修改内存并自动写入 config.ini 文件持久化"""
    updates = req.dict(exclude_unset=True)
    if not updates:
        return {"code": 200, "message": "未传入修改项"}

    updated_keys = config.update_and_save(updates)
    
    logger.info(f"⚙️ [Config] 配置修改成功！")
    return {
        "code": 200, 
        "message": f"[Config] 配置修改成功！", 
        "updated_fields": updated_keys
    }

# --- 云盘离线推送 Transfer ---
@app.post("/api/v1/transfer/push-incremental", tags=["07. 云盘推送 (Transfer)"])
def push_incremental_to_115(req: PushIncrementalRequest):
    scraper = JavDBScraper()
    res = scraper.push_incremental_magnets_to_115(
        start_time=req.start_time,
        end_time=req.end_time,
        magnet_type=req.magnet_type,
        custom_wp_path=req.custom_wp_path
    )
    return {"code": 200, "data": res}

@app.post("/api/v1/transfer/push-single", tags=["07. 云盘推送 (Transfer)"])
def push_single_to_115(req: PushSingleRequest):
    target_db = config.DEFAULT_DB_PATH
    if not os.path.exists(target_db):
        raise HTTPException(status_code=404, detail="数据库文件不存在")

    conn = sqlite3.connect(target_db)
    cursor = conn.cursor()
    cursor.execute("SELECT code, title, actors, tags, magnet_uc, magnet_4k, magnet_c, magnet_u, magnet_normal FROM movies WHERE code = ?", (req.code,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"未找到番号 [{req.code}] 的数据库记录")

    movie_info = {'code': row[0], 'title': row[1], 'actors': row[2], 'tags': row[3]}
    
    m_map = {
        'magnet_uc': row[4],
        'magnet_4k': row[5],
        'magnet_c': row[6],
        'magnet_u': row[7],
        'magnet_normal': row[8]
    }
    
    magnet_url = None
    m_type = req.magnet_type or 'magnet_uc'
    if m_map.get(m_type) and len(str(m_map[m_type]).strip()) > 0:
        magnet_url = m_map[m_type]
    else:
        for k, v in m_map.items():
            if v and len(str(v).strip()) > 0:
                magnet_url = v
                m_type = k
                break

    if not magnet_url:
        raise HTTPException(status_code=404, detail=f"番号 [{req.code}] 在数据库中暂无任何可用的磁力链接")

    scraper = JavDBScraper(cookies_string=req.cookies)
    wp_path = req.custom_wp_path or scraper.generate_auto_path(movie_info, m_type)
    
    res = scraper.push_to_115_gateway(urls=magnet_url, wp_path=wp_path)
    if res.get("code") == 0 or res.get("state") is True:
        scraper.record_push_history(req.code, m_type, magnet_url, wp_path)
        return {"code": 200, "message": f"番号 [{req.code}] 已成功提交至 115 网关", "wp_path": wp_path, "data": res}
    else:
        raise HTTPException(status_code=500, detail=f"推送 115 失败: {res.get('message')}")

@app.post("/api/v1/transfer/push-by-actor", tags=["07. 云盘推送 (Transfer)"])
def push_by_actor(req: PushByActorRequest):
    """【按演员离线推送】将本地数据库中匹配该演员的全部/未离线影片按磁力策略批量提交至 115"""
    scraper = JavDBScraper()
    res = scraper.push_by_actor_to_115(
        actor_name=req.actor_name,
        magnet_type=req.magnet_type,
        custom_wp_path=req.custom_wp_path
    )
    return {"code": 200, "data": res}

@app.post("/api/v1/transfer/push-by-list", tags=["07. 云盘推送 (Transfer)"])
def push_by_list(req: PushByListRequest):
    """【按清单离线推送】将本地数据库中属于该清单的全部/未离线影片按磁力策略批量提交至 115"""
    scraper = JavDBScraper(cookies_string=req.cookies)
    res = scraper.push_by_list_to_115(
        list_id_or_url=req.list_id_or_url,
        magnet_type=req.magnet_type,
        custom_wp_path=req.custom_wp_path
    )
    return {"code": 200, "data": res}

class ResetPushHistoryRequest(BaseModel):
    id: Optional[int] = Field(None, description="push_history 表记录 ID")
    code: Optional[str] = Field(None, description="影片番号")

@app.get("/api/v1/transfer/115-tasks", tags=["07. 云盘推送 (Transfer)"])
def get_115_remote_tasks():
    """获取 115 网关全量离线下载任务状态"""
    try:
        url = f"{config.GATEWAY_115_URL.rstrip('/')}/api/115/offline/tasks"
        headers = {"X-API-KEY": config.GATEWAY_115_API_KEY}
        scraper = JavDBScraper()
        resp = scraper.session.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            res_json = resp.json()
            return {"code": 200, "data": res_json.get("data", [])}
        else:
            return {"code": resp.status_code, "data": [], "message": f"请求 115 网关失败: HTTP {resp.status_code}"}
    except Exception as e:
        logger.error(f"❌ [115 API] 获取 115 远端离线任务失败: {e}")
        return {"code": 500, "data": [], "message": f"请求异常: {str(e)}"}

@app.get("/api/v1/transfer/history", tags=["07. 云盘推送 (Transfer)"])
def get_transfer_history(
    page: int = Query(1, ge=1), 
    limit: int = Query(20, ge=1, le=200),
    magnet_type: Optional[str] = Query(None, description="按磁力类型筛选: magnet_uc, magnet_4k, magnet_c, magnet_u等"),
    status: Optional[str] = Query(None, description="按离线状态筛选: 2(完成), 1(下载中), 0(分配中), -1(失败)"),
    keyword: Optional[str] = Query(None, description="搜索关键字（支持番号 code 或标题 title 模糊搜索）")
):
    """获取本地推送至 115 的离线历史记录 (支持关键字搜索、磁力类型与离线状态筛选及分页)"""
    target_db = config.DEFAULT_DB_PATH
    if not os.path.exists(target_db):
        return {"code": 200, "data": {"items": [], "total": 0, "page": page, "limit": limit, "total_pages": 1}}

    offset = (page - 1) * limit
    conn = sqlite3.connect(target_db)
    cursor = conn.cursor()

    where_clauses = []
    params = []

    if magnet_type and magnet_type.strip() and magnet_type.strip() != "all":
        where_clauses.append("p.magnet_type = ?")
        params.append(magnet_type.strip())

    if status is not None and str(status).strip() != "" and str(status).strip() != "all":
        where_clauses.append("p.status = ?")
        params.append(int(status))

    if keyword and keyword.strip():
        kw = f"%{keyword.strip()}%"
        where_clauses.append("(p.code LIKE ? OR m.title LIKE ?)")
        params.extend([kw, kw])

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    cursor.execute(f"SELECT COUNT(*) FROM push_history p LEFT JOIN movies m ON p.code = m.code {where_sql}", params)
    total = cursor.fetchone()[0]
    total_pages = max(1, (total + limit - 1) // limit)

    cursor.execute(f"""
        SELECT 
            p.id, p.code, p.magnet_type, p.magnet_url, p.info_hash, p.wp_path, p.status, p.pushed_at,
            m.title, m.cover_url
        FROM push_history p
        LEFT JOIN movies m ON p.code = m.code
        {where_sql}
        ORDER BY p.id DESC
        LIMIT ? OFFSET ?
    """, (*params, limit, offset))
    rows = cursor.fetchall()
    conn.close()

    items = []
    for r in rows:
        items.append({
            "id": r[0],
            "code": r[1],
            "magnet_type": r[2],
            "magnet_url": r[3],
            "info_hash": r[4],
            "wp_path": r[5],
            "status": r[6],
            "pushed_at": str(r[7]),
            "title": r[8] or r[1],
            "cover_url": r[9] or ""
        })

    return {
        "code": 200, 
        "data": {
            "items": items, 
            "total": total, 
            "page": page, 
            "limit": limit,
            "total_pages": total_pages
        }
    }

@app.post("/api/v1/transfer/history/delete", tags=["07. 云盘推送 (Transfer)"])
def delete_transfer_history(req: ResetPushHistoryRequest):
    """【重置离线状态】从本地数据库删除特定影片的推送历史记录，允许重新推送"""
    if not req.id and not req.code:
        raise HTTPException(status_code=400, detail="需提供记录 ID 或影片番号 code")

    target_db = config.DEFAULT_DB_PATH
    if not os.path.exists(target_db):
        raise HTTPException(status_code=404, detail="数据库文件不存在")

    conn = sqlite3.connect(target_db)
    cursor = conn.cursor()

    if req.id:
        cursor.execute("DELETE FROM push_history WHERE id = ?", (req.id,))
    elif req.code:
        cursor.execute("DELETE FROM push_history WHERE code = ?", (req.code.strip(),))

    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()

    logger.info(f"🗑️ [Transfer] 已重置清理 {deleted_count} 条 115 推送离线记录 (ID: {req.id}, Code: {req.code})")
    return {"code": 200, "message": f"成功重置并删除了 {deleted_count} 条离线记录！"}

@app.post("/api/v1/transfer/sync-status", tags=["07. 云盘推送 (Transfer)"])
def sync_push_status():
    """【离线状态对比对齐】从 115 远端获取任务列表，提取 Magnet Hash 与本地记录对比比对，对齐最新真实离线下载状态"""
    scraper = JavDBScraper()
    count = scraper.sync_115_offline_status()
    return {"code": 200, "message": f"状态比对对齐完成，更新了 {count} 条离线记录的状态！", "updated_count": count}

_quota_cache = None
_quota_cache_time = 0

@app.get("/api/v1/transfer/quota", tags=["07. 云盘推送 (Transfer)"])
def get_115_quota(force: bool = Query(False, description="是否强制刷新最新 115 远端配额")):
    """查看 115 离线剩余配额 (默认 5 分钟内存缓存防频繁刷新盲目打扰远端网关)"""
    global _quota_cache, _quota_cache_time
    import time
    now = time.time()
    if not force and _quota_cache and (now - _quota_cache_time < 300):
        return {"code": 200, "data": _quota_cache}

    scraper = JavDBScraper()
    quota_data = scraper.check_115_quota()
    _quota_cache = quota_data
    _quota_cache_time = now
    return {"code": 200, "data": quota_data}


# ================= 🔻 Web 可视化全量 API 测试控制台 =================

@app.get("/console", response_class=HTMLResponse, include_in_schema=False)
def get_web_console():
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>JavDB Service - 全量 API 测试控制台</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    </head>
    <body class="bg-slate-900 text-slate-100 min-h-screen p-6 font-sans">
        <div class="max-w-7xl mx-auto space-y-6">
            
            <!-- 头部标题 -->
            <div class="flex justify-between items-center bg-slate-800 p-4 rounded-xl border border-slate-700 shadow-lg">
                <div>
                    <h1 class="text-2xl font-bold text-sky-400">🎬 JavDB Service 全功能测试控制台</h1>
                    <p class="text-xs text-slate-400 mt-1">支持全量 API 接口测试 · Cookie & 参数本地持久化记忆</p>
                </div>
                <div class="flex items-center space-x-2">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        ● Backend Online
                    </span>
                </div>
            </div>

            <!-- 全局 Cookie 设置 -->
            <div class="bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-lg space-y-3">
                <div class="flex justify-between items-center">
                    <label class="block text-sm font-semibold text-sky-300">🔑 全局 Cookie (本地记忆，发起请求时自动携带)</label>
                    <button onclick="saveCookie()" class="px-3 py-1 bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium rounded-lg transition">
                        保存 Cookie
                    </button>
                </div>
                <textarea id="global_cookie" rows="2" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-200 focus:ring-2 focus:ring-sky-500 outline-none" placeholder="粘贴你的 Cookie (_jdb_session=...; remembered_token=...)"></textarea>
            </div>

            <!-- 主测试区域 -->
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
                
                <!-- 左侧：接口选择与参数配置 -->
                <div class="lg:col-span-5 bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-lg space-y-4">
                    <h2 class="text-lg font-bold text-slate-200 border-b border-slate-700 pb-2">🛠️ 接口选择与参数配置</h2>
                    
                    <!-- 全量 API 下拉框 -->
                    <div>
                        <label class="block text-xs font-medium text-slate-400 mb-1">选择待测试接口 (按模块分类)</label>
                        <select id="api_endpoint" onchange="onEndpointChange()" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-sky-300 focus:ring-2 focus:ring-sky-500 outline-none">
                            <optgroup label="01. 模拟登录 (Auth)">
                                <option value="auth_start">1.1 初始化登录会话 (/auth/start-login)</option>
                                <option value="auth_refresh">1.2 刷新验证码 (/auth/refresh-captcha)</option>
                                <option value="auth_submit">1.3 提交账号密码登录 (/auth/submit-login)</option>
                            </optgroup>
                            <optgroup label="02. 任务队列 (Queue)">
                                <option value="queue_add_auto">2.1 添加 URL 抓取任务到队列 (/queue/add-auto-task)</option>
                                <option value="queue_add_code">2.2 添加指定番号抓取任务 (/queue/add-code-task)</option>
                                <option value="queue_status">2.3 查看异步队列排队状态 (/queue/status)</option>
                            </optgroup>
                            <optgroup label="03. 定时任务 (Scheduler)">
                                <option value="schedule_add">3.1 添加 Cron 定时抓取任务 (/schedule/add-cron)</option>
                                <option value="schedule_list">3.2 查看当前 Cron 任务列表 (/schedule/list)</option>
                                <option value="schedule_remove">3.3 删除指定 Cron 任务 (/schedule/remove)</option>
                            </optgroup>
                            <optgroup label="04. 用户数据 (User)">
                                <option value="user_check_login">4.1 校验登录 Cookie 状态 (/user/check-login)</option>
                                <option value="user_actors">4.2 获取已订阅演员目录 (/user/actors)</option>
                                <option value="user_lists">4.3 获取个人/收藏清单列表 (/user/lists)</option>
                                <option value="user_toggle_list">4.4 影片存入/移除清单 (/user/list/toggle-video)</option>
                            </optgroup>
                            <optgroup label="05. 数据库管理 (Database)">
                                <option value="db_clear">5.1 高危：物理清空数据库 (/db/clear)</option>
                                <option value="db_delete_code">5.2 根据番号物理删除单条数据 (/db/movie/delete)</option>
                                <option value="db_refresh_missing">5.3 智能补全缺失磁力 (UC/4K) (/db/refresh-missing)</option>
                            </optgroup>
                            <optgroup label="06. 系统配置与日志 (System)">
                                <option value="sys_get_config">6.1 查看系统全局配置 (/config)</option>
                                <option value="sys_update_config">6.2 在线更新配置并写入 config.ini (/config/update)</option>
                                <option value="sys_view_logs">6.3 实时查看后端日志 (/logs/view)</option>
                                <option value="sys_clear_logs">6.4 清空日志文件 (/logs/clear)</option>
                            </optgroup>
                            <optgroup label="07. 云盘推送 (Transfer)">
                                <option value="transfer_quota">7.0 查看 115 离线剩余配额 (/transfer/quota)</option>
                                <option value="transfer_push_single">7.1 推送单部影片磁力至 115 (/transfer/push-single)</option>
                                <option value="transfer_push_incremental">7.2 增量分批防风控推送磁力 (/transfer/push-incremental)</option>
                                <option value="transfer_sync_status">7.3 对齐 115 离线任务状态 (/transfer/sync-status)</option>
                            </optgroup>
                        </select>
                    </div>

                    <!-- 动态表单项注入区域 -->
                    <div id="dynamic_params" class="space-y-3 pt-2"></div>

                    <!-- 执行按钮 -->
                    <button onclick="executeApiTest()" class="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-lg text-sm shadow-md transition flex justify-center items-center space-x-2">
                        <span>🚀 发起 API 请求</span>
                    </button>
                </div>

                <!-- 右侧：响应展示区 -->
                <div class="lg:col-span-7 bg-slate-800 p-5 rounded-xl border border-slate-700 shadow-lg flex flex-col">
                    <div class="flex justify-between items-center border-b border-slate-700 pb-2 mb-3">
                        <h2 class="text-lg font-bold text-slate-200">📡 响应结果 (Response Body)</h2>
                        <span id="response_status" class="text-xs text-slate-400">等待发起请求...</span>
                    </div>
                    <pre id="response_json" class="flex-1 bg-slate-950 p-4 rounded-lg text-xs font-mono text-emerald-400 overflow-x-auto border border-slate-800 min-h-[450px]">{}</pre>
                </div>
            </div>
        </div>

        <script>
            document.addEventListener("DOMContentLoaded", () => {
                const savedCookie = localStorage.getItem("javdb_test_cookie") || "";
                document.getElementById("global_cookie").value = savedCookie;
                onEndpointChange();
            });

            function saveCookie() {
                const cookieVal = document.getElementById("global_cookie").value.trim();
                localStorage.setItem("javdb_test_cookie", cookieVal);
                alert("✅ Cookie 已自动保存至浏览器本地！");
            }

            function onEndpointChange() {
                const endpoint = document.getElementById("api_endpoint").value;
                const container = document.getElementById("dynamic_params");
                container.innerHTML = "";

                if (endpoint === "auth_refresh") {
                    container.innerHTML = `
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">Session ID</label>
                            <input type="text" id="param_session_id" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200" placeholder="第一步返回的 session_id">
                        </div>`;
                } else if (endpoint === "auth_submit") {
                    container.innerHTML = `
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">Session ID</label>
                            <input type="text" id="param_session_id" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                        </div>
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">JavDB 邮箱 (Email)</label>
                            <input type="text" id="param_email" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                        </div>
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">密码 (Password)</label>
                            <input type="password" id="param_password" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                        </div>
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">验证码 (Captcha)</label>
                            <input type="text" id="param_captcha" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                        </div>`;
                } else if (endpoint === "queue_add_auto") {
                    container.innerHTML = `
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">抓取目标 URL</label>
                            <input type="text" id="param_target_url" value="https://javdb.com/actors/d4ndM" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                        </div>
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">最大翻页数 (max_pages)</label>
                            <input type="number" id="param_max_pages" value="1" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200" placeholder="留空或不填则默认抓取全部">
                        </div>
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">自动抓取详情页 (auto_fetch_details)</label>
                            <select id="param_auto_details" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                                <option value="true">True (抓取)</option>
                                <option value="false">False (仅抓索引)</option>
                            </select>
                        </div>`;
                } else if (endpoint === "queue_add_code") {
                    container.innerHTML = `
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">影片番号 (code)</label>
                            <input type="text" id="param_code" value="SSIS-084" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                        </div>`;
                } else if (endpoint === "schedule_add") {
                    container.innerHTML = `
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">任务 ID (job_id)</label>
                            <input type="text" id="param_job_id" value="daily_actor_task" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                        </div>
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">目标 URL</label>
                            <input type="text" id="param_target_url" value="https://javdb.com/actors/d4ndM" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                        </div>
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">Cron 表达式 (分 时 日 月 周)</label>
                            <input type="text" id="param_cron" value="0 3 * * *" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                        </div>`;
                } else if (endpoint === "schedule_remove") {
                    container.innerHTML = `
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">删除的任务 ID (job_id)</label>
                            <input type="text" id="param_job_id" value="daily_actor_task" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                        </div>`;
                } else if (endpoint === "user_lists") {
                    container.innerHTML = `
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">清单类型 (type)</label>
                            <select id="param_list_type" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                                <option value="mine">mine (我的清单)</option>
                                <option value="favorite">favorite (收藏的清单)</option>
                            </select>
                        </div>`;
                } else if (endpoint === "user_toggle_list") {
                    container.innerHTML = `
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">番号或 video_id (如 EKbN0 或 SSIS-084)</label>
                            <input type="text" id="param_code_or_url" value="EKbN0" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                        </div>
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">清单 ID (list_id)</label>
                            <input type="text" id="param_list_id" value="VwKbrn" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                        </div>
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">操作动作 (checked)</label>
                            <select id="param_checked" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                                <option value="true">True (存入清单)</option>
                                <option value="false">False (移除清单)</option>
                            </select>
                        </div>`;
                } else if (endpoint === "db_clear" || endpoint === "sys_clear_logs") {
                    container.innerHTML = `
                        <div>
                            <label class="block text-xs font-medium text-rose-400 mb-1">⚠️ 安全确认秘钥 (SECURITY_CLEAR_KEY)</label>
                            <input type="password" id="param_confirm_key" value="DANGER_CONFIRM_DELETE_ALL" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                        </div>`;
                } else if (endpoint === "db_delete_code") {
                    container.innerHTML = `
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">删除的番号 (code)</label>
                            <input type="text" id="param_code" value="SSIS-084" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                        </div>`;
                } else if (endpoint === "db_refresh_missing") {
                    container.innerHTML = `
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">补全缺失的槽位 (missing_field)</label>
                            <select id="param_missing_field" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                                <option value="magnet_uc">magnet_uc (无码中字/破解)</option>
                                <option value="magnet_4k">magnet_4k (4K超清)</option>
                                <option value="magnet_c">magnet_c (有码中字)</option>
                                <option value="magnet_u">magnet_u (无码高清)</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">限制处理最大数量 (limit)</label>
                            <input type="number" id="param_limit" value="50" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                        </div>`;
                } else if (endpoint === "sys_update_config") {
                    container.innerHTML = `
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">修改推送单批大小 (PUSH_BATCH_SIZE)</label>
                            <input type="number" id="param_push_batch_size" value="5" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                        </div>
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">修改 115 API 网关地址 (GATEWAY_115_URL)</label>
                            <input type="text" id="param_gateway_115_url" value="http://127.0.0.1:3000" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                        </div>`;
                } else if (endpoint === "sys_view_logs") {
                    container.innerHTML = `
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">查看日志末尾行数 (lines)</label>
                            <input type="number" id="param_lines" value="100" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                        </div>`;
                } else if (endpoint === "transfer_quota") {
                    container.innerHTML = `
                        <div class="p-3 bg-slate-900/50 rounded-lg border border-slate-700/50 text-xs text-slate-400">
                            💡 点击下方按钮将直接调用 115 API 网关，获取当前账号的离线总配额、已用额度及剩余可用额度。
                        </div>`;
                } else if (endpoint === "transfer_push_single") {
                    container.innerHTML = `
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">影片番号 (code)</label>
                            <input type="text" id="param_code" value="SSIS-084" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                        </div>
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">推送的磁力槽位 (magnet_type)</label>
                            <select id="param_magnet_type" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                                <option value="magnet_uc">magnet_uc (无码中字/破解)</option>
                                <option value="magnet_c">magnet_c (有码中字)</option>
                                <option value="magnet_u">magnet_u (无码高清)</option>
                                <option value="magnet_4k">magnet_4k (4K超清)</option>
                                <option value="magnet_normal">magnet_normal (普通磁力)</option>
                            </select>
                        </div>`;
                } else if (endpoint === "transfer_push_incremental") {
                    container.innerHTML = `
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">起始时间 (start_time)</label>
                            <input type="text" id="param_start_time" value="2026-07-01 00:00:00" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                        </div>
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">截止时间 (end_time)</label>
                            <input type="text" id="param_end_time" value="2026-07-25 23:59:59" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                        </div>
                        <div>
                            <label class="block text-xs font-medium text-slate-400 mb-1">推送的磁力槽位 (magnet_type)</label>
                            <select id="param_magnet_type" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-xs text-slate-200">
                                <option value="magnet_uc">magnet_uc (无码中字/破解)</option>
                                <option value="magnet_c">magnet_c (有码中字)</option>
                                <option value="magnet_u">magnet_u (无码高清)</option>
                                <option value="magnet_4k">magnet_4k (4K超清)</option>
                                <option value="magnet_normal">magnet_normal (普通磁力)</option>
                            </select>
                        </div>`;
                }
            }

            async function executeApiTest() {
                const endpoint = document.getElementById("api_endpoint").value;
                const cookie = document.getElementById("global_cookie").value.trim();
                const statusEl = document.getElementById("response_status");
                const jsonEl = document.getElementById("response_json");

                statusEl.innerText = "⏳ 正在请求中...";
                statusEl.className = "text-xs text-yellow-400 font-medium";

                try {
                    let url = "";
                    let method = "POST";
                    let payload = { cookies: cookie };

                    // 1. Auth 模块
                    if (endpoint === "auth_start") { url = "/api/v1/auth/start-login"; }
                    else if (endpoint === "auth_refresh") {
                        url = `/api/v1/auth/refresh-captcha/${document.getElementById("param_session_id").value}`;
                    } else if (endpoint === "auth_submit") {
                        url = "/api/v1/auth/submit-login";
                        payload = {
                            session_id: document.getElementById("param_session_id").value,
                            email: document.getElementById("param_email").value,
                            password: document.getElementById("param_password").value,
                            captcha: document.getElementById("param_captcha").value
                        };
                    }
                    // 2. Queue 模块
                    else if (endpoint === "queue_add_auto") {
                        url = "/api/v1/queue/add-auto-task";
                        payload.target_url = document.getElementById("param_target_url").value;
                        const maxPagesVal = document.getElementById("param_max_pages").value;
                        if (maxPagesVal !== "") { payload.max_pages = parseInt(maxPagesVal); }
                        payload.auto_fetch_details = document.getElementById("param_auto_details").value === "true";
                    } else if (endpoint === "queue_add_code") {
                        url = "/api/v1/queue/add-code-task";
                        payload.code = document.getElementById("param_code").value;
                    } else if (endpoint === "queue_status") { url = "/api/v1/queue/status"; method = "GET"; }
                    // 3. Scheduler 模块
                    else if (endpoint === "schedule_add") {
                        url = "/api/v1/schedule/add-cron";
                        payload.job_id = document.getElementById("param_job_id").value;
                        payload.target_url = document.getElementById("param_target_url").value;
                        payload.cron_expression = document.getElementById("param_cron").value;
                    } else if (endpoint === "schedule_list") { url = "/api/v1/schedule/list"; method = "GET"; }
                    else if (endpoint === "schedule_remove") {
                        const jobId = document.getElementById("param_job_id").value;
                        url = `/api/v1/schedule/remove/${jobId}`; method = "DELETE";
                    }
                    // 4. User 模块
                    else if (endpoint === "user_check_login") { url = "/api/v1/user/check-login"; }
                    else if (endpoint === "user_actors") { url = "/api/v1/user/actors"; }
                    else if (endpoint === "user_lists") {
                        url = "/api/v1/user/lists";
                        payload.type = document.getElementById("param_list_type").value;
                    } else if (endpoint === "user_toggle_list") {
                        url = "/api/v1/user/list/toggle-video";
                        payload.code_or_url = document.getElementById("param_code_or_url").value;
                        payload.list_id = document.getElementById("param_list_id").value;
                        payload.checked = document.getElementById("param_checked").value === "true";
                    }
                    // 5. DB 模块
                    else if (endpoint === "db_clear") {
                        url = "/api/v1/db/clear";
                        payload = { confirm_key: document.getElementById("param_confirm_key").value };
                    } else if (endpoint === "db_delete_code") {
                        url = "/api/v1/db/movie/delete";
                        payload = { code: document.getElementById("param_code").value };
                    } else if (endpoint === "db_refresh_missing") {
                        url = "/api/v1/db/refresh-missing";
                        payload.missing_field = document.getElementById("param_missing_field").value;
                        payload.limit = parseInt(document.getElementById("param_limit").value);
                    }
                    // 6. System 模块
                    else if (endpoint === "sys_get_config") { url = "/api/v1/config"; method = "GET"; }
                    else if (endpoint === "sys_update_config") {
                        url = "/api/v1/config/update";
                        payload = {
                            push_batch_size: parseInt(document.getElementById("param_push_batch_size").value),
                            gateway_115_url: document.getElementById("param_gateway_115_url").value
                        };
                    } else if (endpoint === "sys_view_logs") {
                        method = "GET";
                        url = `/api/v1/logs/view?lines=${document.getElementById("param_lines").value}`;
                    } else if (endpoint === "sys_clear_logs") {
                        url = "/api/v1/logs/clear";
                        payload = { confirm_key: document.getElementById("param_confirm_key").value };
                    }
                    // 7. Transfer 模块
                    else if (endpoint === "transfer_quota") { url = "/api/v1/transfer/quota"; method = "GET"; }
                    else if (endpoint === "transfer_push_single") {
                        url = "/api/v1/transfer/push-single";
                        payload.code = document.getElementById("param_code").value;
                        payload.magnet_type = document.getElementById("param_magnet_type").value;
                    } else if (endpoint === "transfer_push_incremental") {
                        url = "/api/v1/transfer/push-incremental";
                        payload = {
                            start_time: document.getElementById("param_start_time").value,
                            end_time: document.getElementById("param_end_time").value,
                            magnet_type: document.getElementById("param_magnet_type").value
                        };
                    } else if (endpoint === "transfer_sync_status") { url = "/api/v1/transfer/sync-status"; }

                    let res;
                    if (method === "POST") res = await axios.post(url, payload);
                    else if (method === "GET") res = await axios.get(url);
                    else if (method === "DELETE") res = await axios.delete(url);

                    statusEl.innerText = `HTTP ${res.status} OK`;
                    statusEl.className = "text-xs text-emerald-400 font-medium";
                    jsonEl.innerText = JSON.stringify(res.data, null, 2);
                } catch (err) {
                    statusEl.innerText = `HTTP Error`;
                    statusEl.className = "text-xs text-rose-400 font-medium";
                    if (err.response) {
                        jsonEl.innerText = JSON.stringify(err.response.data, null, 2);
                    } else {
                        jsonEl.innerText = err.message;
                    }
                }
            }
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host=config.API_HOST, port=config.API_PORT, reload=False)