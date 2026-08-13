import os
import shutil
import configparser
from typing import Dict, Any

# 1. 配置文件路径解析：优先使用环境变量 CONFIG_PATH 或 Docker /config 挂载路径
DEFAULT_CONFIG_PATH = os.environ.get("CONFIG_PATH", "")
if not DEFAULT_CONFIG_PATH:
    if os.path.exists("/config"):
        DEFAULT_CONFIG_PATH = "/config/config.ini"
    else:
        DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.ini")

# 2. 数据与持久化文件目录解析：优先使用环境变量 DATA_DIR 或 Docker /data 挂载路径
DATA_DIR = os.environ.get("DATA_DIR", "")
if not DATA_DIR:
    if os.path.exists("/data"):
        DATA_DIR = "/data"
    else:
        DATA_DIR = os.path.dirname(__file__)

class ConfigManager:
    def __init__(self, ini_path: str = DEFAULT_CONFIG_PATH):
        self.ini_path = ini_path
        self.DATA_DIR = DATA_DIR
        # 🔻 核心修正：关闭插值解析 (interpolation=None)，防止 Cookie 中的 % 符号报错
        self.parser = configparser.ConfigParser(interpolation=None)
        self.ensure_config_exists()
        self.reload()

    def ensure_config_exists(self):
        """确保配置文件存在：若不存在则自动从模板/本地拷贝初始化"""
        if not os.path.exists(self.ini_path):
            dir_name = os.path.dirname(self.ini_path)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)
            
            local_default = os.path.join(os.path.dirname(__file__), "config.ini")
            if os.path.exists(local_default) and self.ini_path != local_default:
                shutil.copy(local_default, self.ini_path)

    def reload(self):
        """从 config.ini 读取配置并载入内存"""
        self.ensure_config_exists()
        self.parser.read(self.ini_path, encoding="utf-8")

        # 1. Base
        self.BASE_URL = self.parser.get("base", "base_url", fallback="https://javdb.com").rstrip('/')
        self.API_HOST = self.parser.get("base", "api_host", fallback="0.0.0.0")
        self.API_PORT = self.parser.getint("base", "api_port", fallback=8000)
        
        raw_db_path = self.parser.get("base", "default_db_path", fallback="javdb_standalone.db")
        if not os.path.isabs(raw_db_path):
            self.DEFAULT_DB_PATH = os.path.join(self.DATA_DIR, raw_db_path)
        else:
            self.DEFAULT_DB_PATH = raw_db_path

        self.SECURITY_CLEAR_KEY = self.parser.get("base", "security_clear_key", fallback="DANGER_CONFIRM_DELETE_ALL")
        self.DEFAULT_USER_AGENT = self.parser.get("base", "default_user_agent", fallback="")
        self.DEFAULT_COOKIES = self.parser.get("base", "default_cookies", fallback="")

        # 2. Log
        raw_log_dir = self.parser.get("log", "log_dir", fallback="logs")
        if not os.path.isabs(raw_log_dir):
            self.LOG_DIR = os.path.join(self.DATA_DIR, raw_log_dir)
        else:
            self.LOG_DIR = raw_log_dir

        self.LOG_FILE_NAME = self.parser.get("log", "log_file_name", fallback="javdb_service.log")
        self.LOG_MAX_BYTES = self.parser.getint("log", "log_max_bytes", fallback=10485760)
        self.LOG_BACKUP_COUNT = self.parser.getint("log", "log_backup_count", fallback=5)
        self.LOG_LEVEL = self.parser.get("log", "log_level", fallback="INFO")

        # 3. Network
        self.REQUEST_DELAY_MIN = self.parser.getfloat("network", "request_delay_min", fallback=1.5)
        self.REQUEST_DELAY_MAX = self.parser.getfloat("network", "request_delay_max", fallback=3.0)
        self.MAX_RETRIES = self.parser.getint("network", "max_retries", fallback=3)
        self.RETRY_WAIT_BASE = self.parser.getfloat("network", "retry_wait_base", fallback=15.0)
        self.REQUEST_TIMEOUT = self.parser.getint("network", "request_timeout", fallback=20)
        self.HTTP_PROXY = self.parser.get("network", "http_proxy", fallback="").strip() or None
        self.HTTPS_PROXY = self.parser.get("network", "https_proxy", fallback="").strip() or None

        # 4. Auth
        self.AUTH_SESSION_TTL = self.parser.getint("auth", "auth_session_ttl", fallback=600)
        self.AUTH_HTTP_TIMEOUT = self.parser.getint("auth", "auth_http_timeout", fallback=25)

        # 5. Queue & Schedule
        self.QUEUE_WORKER_CONCURRENCY = self.parser.getint("queue", "queue_worker_concurrency", fallback=1)
        self.MAX_QUEUE_SIZE = self.parser.getint("queue", "max_queue_size", fallback=100)
        self.ENABLE_SCHEDULER = self.parser.getboolean("queue", "enable_scheduler", fallback=True)
        self.DEFAULT_CRON_MAX_PAGES = self.parser.getint("queue", "default_cron_max_pages", fallback=1)
        self.INCREMENTAL_THRESHOLD = self.parser.getint("queue", "incremental_threshold", fallback=5)
        self.OLD_MOVIE_DAYS = self.parser.getint("queue", "old_movie_days", fallback=30)

        # 6. DB
        self.DB_BUSY_TIMEOUT = self.parser.getfloat("db", "db_busy_timeout", fallback=30.0)
        self.ENABLE_WAL_MODE = self.parser.getboolean("db", "enable_wal_mode", fallback=True)

        # 7. Regex
        self.REGEX_4K = self.parser.get("regex", "regex_4k", fallback=r'(?:[^\w]|^|[._\-\[])4K(?:[^\w]|$|[._\-\]])|2160p')
        self.REGEX_TAG_UC = self.parser.get("regex", "regex_tag_uc", fallback=r'(?:[^\w]|^)-?UC(?:[^\w]|$)|uncensored[-_\s]*sub')
        self.REGEX_TAG_C = self.parser.get("regex", "regex_tag_c", fallback=r'(?:[^\w]|^)-?C(?:[^\w]|$)')
        self.REGEX_TAG_U = self.parser.get("regex", "regex_tag_u", fallback=r'(?:[^\w]|^)-?U(?:[^\w]|$)')
        self.REGEX_SUBTITLE = self.parser.get("regex", "regex_subtitle", fallback=r'字幕|中字|中文|caption|sub|chs|cht|zh-cn|zh-tw')
        self.REGEX_UNCENSORED = self.parser.get("regex", "regex_uncensored", fallback=r'無碼|无码|破解|流出|泄露|uncensored|leak|mosaic-removed')

        # 8. Gateway 115
        self.GATEWAY_115_URL = self.parser.get("gateway115", "gateway_115_url", fallback="http://127.0.0.1:3000")
        self.GATEWAY_115_API_KEY = self.parser.get("gateway115", "gateway_115_api_key", fallback="115_api_key_default")
        self.PUSH_BATCH_SIZE = self.parser.getint("gateway115", "push_batch_size", fallback=5)
        self.PUSH_INTERVAL_MIN = self.parser.getfloat("gateway115", "push_interval_min", fallback=3.0)
        self.PUSH_INTERVAL_MAX = self.parser.getfloat("gateway115", "push_interval_max", fallback=8.0)

    def update_and_save(self, updates: Dict[str, Any]) -> list:
        """更新内存并同步保存至 config.ini"""
        attr_to_ini = {
            "BASE_URL": ("base", "base_url"),
            "API_HOST": ("base", "api_host"),
            "API_PORT": ("base", "api_port"),
            "DEFAULT_DB_PATH": ("base", "default_db_path"),
            "SECURITY_CLEAR_KEY": ("base", "security_clear_key"),
            "DEFAULT_USER_AGENT": ("base", "default_user_agent"),
            "DEFAULT_COOKIES": ("base", "default_cookies"),
            "LOG_DIR": ("log", "log_dir"),
            "LOG_FILE_NAME": ("log", "log_file_name"),
            "LOG_MAX_BYTES": ("log", "log_max_bytes"),
            "LOG_BACKUP_COUNT": ("log", "log_backup_count"),
            "LOG_LEVEL": ("log", "log_level"),
            "REQUEST_DELAY_MIN": ("network", "request_delay_min"),
            "REQUEST_DELAY_MAX": ("network", "request_delay_max"),
            "MAX_RETRIES": ("network", "max_retries"),
            "RETRY_WAIT_BASE": ("network", "retry_wait_base"),
            "REQUEST_TIMEOUT": ("network", "request_timeout"),
            "HTTP_PROXY": ("network", "http_proxy"),
            "HTTPS_PROXY": ("network", "https_proxy"),
            "AUTH_SESSION_TTL": ("auth", "auth_session_ttl"),
            "AUTH_HTTP_TIMEOUT": ("auth", "auth_http_timeout"),
            "QUEUE_WORKER_CONCURRENCY": ("queue", "queue_worker_concurrency"),
            "MAX_QUEUE_SIZE": ("queue", "max_queue_size"),
            "ENABLE_SCHEDULER": ("queue", "enable_scheduler"),
            "DEFAULT_CRON_MAX_PAGES": ("queue", "default_cron_max_pages"),
            "INCREMENTAL_THRESHOLD": ("queue", "incremental_threshold"),
            "OLD_MOVIE_DAYS": ("queue", "old_movie_days"),
            "DB_BUSY_TIMEOUT": ("db", "db_busy_timeout"),
            "ENABLE_WAL_MODE": ("db", "enable_wal_mode"),
            "REGEX_4K": ("regex", "regex_4k"),
            "REGEX_TAG_UC": ("regex", "regex_tag_uc"),
            "REGEX_TAG_C": ("regex", "regex_tag_c"),
            "REGEX_TAG_U": ("regex", "regex_tag_u"),
            "REGEX_SUBTITLE": ("regex", "regex_subtitle"),
            "REGEX_UNCENSORED": ("regex", "regex_uncensored"),
            "GATEWAY_115_URL": ("gateway115", "gateway_115_url"),
            "GATEWAY_115_API_KEY": ("gateway115", "gateway_115_api_key"),
            "PUSH_BATCH_SIZE": ("gateway115", "push_batch_size"),
            "PUSH_INTERVAL_MIN": ("gateway115", "push_interval_min"),
            "PUSH_INTERVAL_MAX": ("gateway115", "push_interval_max"),
        }

        updated_keys = []
        for key, val in updates.items():
            attr_key = key.upper()
            if val is not None and attr_key in attr_to_ini:
                section, option = attr_to_ini[attr_key]
                setattr(self, attr_key, val)
                self.parser.set(section, option, str(val if val is not None else ""))
                updated_keys.append(attr_key)

        with open(self.ini_path, "w", encoding="utf-8") as f:
            self.parser.write(f)

        return updated_keys

config = ConfigManager()