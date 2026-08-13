import sqlite3
import re
import time
import random
import json
import base64
import uuid
from datetime import datetime, timedelta
from urllib.parse import urljoin, quote, parse_qs, urlparse
from typing import Optional
from bs4 import BeautifulSoup
import requests

from config_manager import config
from logger import logger

# ================= 模拟登录独立模块 (curl_cffi) =================

LOGIN_URL = f"{config.BASE_URL}/login"
LOGIN_POST_PATH = "/user_sessions"
CAPTCHA_PATH = "/rucaptcha/"

_auth_sessions: dict[str, dict] = {}

class AuthBrowserError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code

def _new_curl_session():
    from curl_cffi import requests as curl_requests
    proxies = {}
    if config.HTTP_PROXY: proxies['http'] = config.HTTP_PROXY
    if config.HTTPS_PROXY: proxies['https'] = config.HTTPS_PROXY

    session = curl_requests.Session(impersonate="chrome", timeout=config.AUTH_HTTP_TIMEOUT)
    if proxies: session.proxies = proxies
    return session

def _cleanup_expired_auth_sessions():
    now = time.time()
    for sid in list(_auth_sessions.keys()):
        if _auth_sessions[sid].get("expires_at", 0) <= now:
            _auth_sessions.pop(sid, None)

def start_login_session() -> dict:
    _cleanup_expired_auth_sessions()
    session = _new_curl_session()
    logger.info(f"🔑 [Auth] 正在请求 JavDB 登录页面获取 CSRF Token: {LOGIN_URL}")
    try:
        resp = session.get(LOGIN_URL)
    except Exception as exc:
        logger.error(f"❌ [Auth] 无法打开 JavDB 登录页: {exc}")
        raise AuthBrowserError(f"无法打开 JavDB 登录页：{exc}")
    
    if resp.status_code != 200:
        logger.error(f"❌ [Auth] 打开登录页失败，HTTP 状态码: {resp.status_code}")
        raise AuthBrowserError(f"打开登录页失败 (HTTP {resp.status_code})", 502)

    soup = BeautifulSoup(resp.text or "", "html.parser")
    form = soup.find("form", attrs={"action": LOGIN_POST_PATH})
    if not form:
        logger.error("❌ [Auth] 未能提取到登录表单，HTML 结构可能已被修改")
        raise AuthBrowserError("未找到登录表单，站点结构可能已变更", 502)

    token_input = form.find("input", attrs={"name": "authenticity_token"})
    token = token_input.get("value") if token_input else ""
    has_captcha = form.find("input", attrs={"name": "_rucaptcha"}) is not None

    captcha_image = ""
    if has_captcha:
        try:
            logger.info("🧩 [Auth] 识别到图形验证码，正在获取验证码图片...")
            c_resp = session.get(urljoin(config.BASE_URL, CAPTCHA_PATH) + f"?t={int(time.time() * 1000)}")
            if c_resp.status_code == 200 and c_resp.content:
                encoded = base64.b64encode(c_resp.content).decode("ascii")
                captcha_image = f"data:image/gif;base64,{encoded}"
                logger.info("✅ [Auth] 验证码图片 Base64 解析成功")
        except Exception as e:
            logger.warning(f"⚠️ [Auth] 获取验证码图片失败: {e}")

    session_id = uuid.uuid4().hex
    now = time.time()
    _auth_sessions[session_id] = {
        "curl_session": session,
        "token": token,
        "created_at": now,
        "expires_at": now + config.AUTH_SESSION_TTL,
    }
    logger.info(f"💡 [Auth] 成功创建登录临时会话, Session ID: {session_id}")
    return {
        "session_id": session_id,
        "needs_captcha": has_captcha,
        "captcha_image": captcha_image
    }

def refresh_login_captcha(session_id: str) -> dict:
    _cleanup_expired_auth_sessions()
    sess_data = _auth_sessions.get(session_id)
    if not sess_data:
        logger.error(f"❌ [Auth] 刷新验证码失败: 会话 [{session_id}] 不存在或已过期")
        raise AuthBrowserError("登录会话不存在或已过期，请重新初始化", 404)

    captcha_image = ""
    try:
        logger.info(f"🔄 [Auth] 正在为会话 [{session_id}] 重新获取验证码...")
        c_resp = sess_data["curl_session"].get(urljoin(config.BASE_URL, CAPTCHA_PATH) + f"?t={int(time.time() * 1000)}")
        if c_resp.status_code == 200 and c_resp.content:
            encoded = base64.b64encode(c_resp.content).decode("ascii")
            captcha_image = f"data:image/gif;base64,{encoded}"
            logger.info("✅ [Auth] 验证码刷新成功")
    except Exception as e:
        logger.warning(f"⚠️ [Auth] 刷新验证码失败: {e}")

    return {"session_id": session_id, "captcha_image": captcha_image}

def submit_login_credentials(session_id: str, email: str, password: str, captcha: str) -> str:
    _cleanup_expired_auth_sessions()
    sess_data = _auth_sessions.get(session_id)
    if not sess_data:
        logger.error(f"❌ [Auth] 提交登录失败: 会话 [{session_id}] 已过期")
        raise AuthBrowserError("登录会话不存在或已过期", 404)

    curl_session = sess_data["curl_session"]
    payload = {
        "authenticity_token": sess_data["token"],
        "email": email,
        "password": password,
        "_rucaptcha": captcha or "",
        "remember": "1",
        "commit": "Sign in",
    }

    try:
        logger.info(f"🚀 [Auth] 正在提交登录表单 (账号: {email})...")
        resp = curl_session.post(urljoin(config.BASE_URL, LOGIN_POST_PATH), data=payload, allow_redirects=True)
    except Exception as exc:
        logger.error(f"❌ [Auth] 提交登录表单网络错误: {exc}")
        raise AuthBrowserError(f"提交登录请求异常: {exc}")

    soup = BeautifulSoup(resp.text or "", "html.parser")
    still_on_login = soup.find("form", attrs={"action": LOGIN_POST_PATH}) is not None
    if still_on_login or "/login" in str(getattr(resp, "url", "")):
        logger.error("❌ [Auth] 登录失败，可能验证码错误或密码不正确")
        raise AuthBrowserError("登录失败，请检查账号密码或验证码是否正确。", 422)

    jar = curl_session.cookies
    pairs = [f"{k}={v}" for k, v in dict(jar).items()]
    cookie_str = "; ".join(pairs)

    if "_jdb_session" not in cookie_str:
        logger.error("❌ [Auth] 登录响应中未捕获到关键凭证 _jdb_session Cookie")
        raise AuthBrowserError("未成功捕获到核心 _jdb_session Cookie", 502)

    _auth_sessions.pop(session_id, None)
    logger.info("🎉 [Auth] JavDB 模拟直登成功！Cookie 凭证提取完毕")
    return cookie_str


# ================= JavDB 抓取 SDK =================

class JavDBScraper:
    def __init__(self, cookies_string: str = None, db_path: str = None, user_agent: str = None, cancel_check=None, progress_callback=None, log_callback=None):
        self.cancel_check = cancel_check
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.db_path = db_path or config.DEFAULT_DB_PATH
        raw_cookie = cookies_string if cookies_string is not None else config.DEFAULT_COOKIES
        if raw_cookie:
            if 'locale=' in raw_cookie:
                raw_cookie = re.sub(r'locale=[a-zA-Z\-]+', 'locale=zh', raw_cookie)
            else:
                raw_cookie = f"locale=zh; {raw_cookie}"
        self.cookies_string = raw_cookie or "locale=zh"
        self.user_agent = user_agent or config.DEFAULT_USER_AGENT
        
        self.session = requests.Session()
        
        if config.HTTP_PROXY or config.HTTPS_PROXY:
            proxies = {}
            if config.HTTP_PROXY: proxies['http'] = config.HTTP_PROXY
            if config.HTTPS_PROXY: proxies['https'] = config.HTTPS_PROXY
            self.session.proxies.update(proxies)

        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Cookie': self.cookies_string,
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        
        self._init_db()

    def safe_log(self, msg: str, level: str = "info"):
        if level == "error": logger.error(msg)
        elif level == "warning": logger.warning(msg)
        else: logger.info(msg)
        if self.log_callback:
            try: self.log_callback(msg)
            except Exception: pass

    def _get_db_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=config.DB_BUSY_TIMEOUT)
        if config.ENABLE_WAL_MODE:
            conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self):
        conn = self._get_db_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS movies (
                code TEXT PRIMARY KEY,
                title TEXT,
                detail_url TEXT,
                cover_url TEXT,
                score TEXT,
                score_number TEXT,
                release_date TEXT,
                duration TEXT,
                director TEXT,
                maker TEXT,
                publisher TEXT,
                series TEXT,
                tags TEXT,
                actors TEXT,
                magnets TEXT,
                magnet_normal TEXT,
                magnet_normal_fetched_at TEXT,
                magnet_u TEXT,
                magnet_u_fetched_at TEXT,
                magnet_c TEXT,
                magnet_c_fetched_at TEXT,
                magnet_uc TEXT,
                magnet_uc_fetched_at TEXT,
                magnet_4k TEXT,
                magnet_4k_fetched_at TEXT,
                is_detail_fetched INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute("PRAGMA table_info(movies)")
        existing_columns = [row[1] for row in cursor.fetchall()]

        for col_name in ['magnet_4k', 'magnet_4k_fetched_at', 'is_detail_fetched', 'preview_video_url', 'preview_images']:
            if col_name not in existing_columns:
                try: 
                    cursor.execute(f"ALTER TABLE movies ADD COLUMN {col_name} TEXT;")
                    logger.info(f"🛠️ [DB Schema] 自动追加数据库新字段: {col_name}")
                except sqlite3.OperationalError: pass

        if 'is_vip_blocked' not in existing_columns:
            try:
                cursor.execute("ALTER TABLE movies ADD COLUMN is_vip_blocked INTEGER DEFAULT 0;")
                logger.info("🛠️ [DB Schema] 自动追加数据库新字段: is_vip_blocked")
            except sqlite3.OperationalError: pass

        if 'in_lists' not in existing_columns:
            try: 
                cursor.execute("ALTER TABLE movies ADD COLUMN in_lists TEXT DEFAULT '[]';")
                logger.info("🛠️ [DB Schema] 自动追加数据库新字段: in_lists")
            except sqlite3.OperationalError: pass

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS push_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT,
                magnet_type TEXT,
                magnet_url TEXT,
                info_hash TEXT,
                wp_path TEXT,
                status INTEGER DEFAULT 0,
                pushed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def _safe_fetch_url(self, url: str, method: str = "GET", data: dict = None, headers: dict = None):
        req_headers = {
            "User-Agent": config.DEFAULT_USER_AGENT,
            "Cookie": self.cookies_string or config.DEFAULT_COOKIES,
        }
        if headers:
            req_headers.update(headers)

        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                delay = random.uniform(config.REQUEST_DELAY_MIN, config.REQUEST_DELAY_MAX)
                time.sleep(delay)
                
                http_method = method.upper()
                logger.debug(f"🌐 [{http_method}] 请求 URL: {url} (第 {attempt} 次, 休眠 {delay:.2f}s)")

                if http_method == "POST":
                    response = self.session.post(url, data=data, headers=req_headers, timeout=config.REQUEST_TIMEOUT)
                else:
                    response = self.session.get(url, headers=req_headers, timeout=config.REQUEST_TIMEOUT)

                if response.status_code in [200, 201, 204]:
                    return response
                elif response.status_code in [429, 503]:
                    wait_time = attempt * config.RETRY_WAIT_BASE + random.uniform(2, 5)
                    logger.warning(f"⚠️ 触发反爬限流 (HTTP {response.status_code})，主动休眠 {wait_time:.1f} 秒...")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"⚠️ HTTP 请求返回状态码: {response.status_code} | URL: {url}")
                    return response

            except Exception as e:
                logger.warning(f"⚠️ 网络请求异常 (第 {attempt}/{config.MAX_RETRIES} 次): {e}")
                if attempt < config.MAX_RETRIES:
                    time.sleep(config.RETRY_WAIT_BASE)
                else:
                    logger.error(f"❌ 超过最大重试次数，放弃请求: {url}")
                    return None

    def clear_database(self) -> int:
        conn = self._get_db_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM movies")
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        logger.info(f"🧹 [DB] 物理清空数据库完成，删除了 {deleted_count} 条记录")
        return deleted_count

    def delete_by_code(self, code: str) -> bool:
        conn = self._get_db_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM movies WHERE code = ?", (code.strip(),))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        if deleted: logger.info(f"🗑️ [DB] 已从数据库物理删除番号 [{code}]")
        return deleted

    def refresh_missing_fields(self, missing_field: str = "magnet_uc", limit: int = None):
        valid_fields = ['magnet_normal', 'magnet_u', 'magnet_c', 'magnet_uc', 'magnet_4k']
        if missing_field not in valid_fields:
            raise ValueError(f"无效的槽位字段，支持: {valid_fields}")

        conn = self._get_db_conn()
        cursor = conn.cursor()
        query = f"SELECT code, detail_url FROM movies WHERE detail_url IS NOT NULL AND ({missing_field} IS NULL OR {missing_field} = '')"
        if limit: cursor.execute(query + " LIMIT ?", (limit,))
        else: cursor.execute(query)
        pending_list = cursor.fetchall()
        conn.close()

        refreshed_count = 0
        logger.info(f"🔍 [补全] 扫描到 {len(pending_list)} 部影片缺失 [{missing_field}]，开始抓取...")
        for idx, (code, url) in enumerate(pending_list, start=1):
            logger.info(f"🔄 [{idx}/{len(pending_list)}] 正在补全番号: {code}")
            resp = self._safe_fetch_url(url)
            if resp and resp.status_code == 200:
                details, all_magnets_str, magnets = self._parse_detail_page(resp.text)
                self._update_movie_detail(code, details, all_magnets_str, magnets)
                refreshed_count += 1
        logger.info(f"✅ [补全] 任务结束，成功补全 {refreshed_count} 部影片")
        return refreshed_count

    def check_login_status(self) -> dict:
        profile_url = f"{config.BASE_URL}/users/profile"
        logger.info("🔍 [User] 正在请求个人中心校验 Cookie 权限...")
        resp = self._safe_fetch_url(profile_url)
        if not resp:
            return {"is_login": False, "message": "网络请求失败"}
        if "/login" in resp.url or "<title> 登录" in resp.text or "<title> 登入" in resp.text or "user_sessions" in resp.url:
            logger.warning("⚠️ [User] Cookie 已失效 (重定向至登录页)")
            return {"is_login": False, "message": "Cookie 已失效 (重定向至登录页)"}
        if resp.status_code == 200 and ("navbar-menu-user" in resp.text or "collection_actors" in resp.text or "favorite_lists" in resp.text):
            logger.info("✅ [User] Cookie 验证有效！")
            return {"is_login": True, "message": "Cookie 验证有效！"}
        return {"is_login": False, "message": "Cookie 无效或已过期"}

    def get_collection_actors(self) -> list:
        logger.info("🎭 [User] 正在拉取用户订阅演员...")
        resp = self._safe_fetch_url(f"{config.BASE_URL}/users/collection_actors")
        if not resp or resp.status_code != 200 or "/login" in resp.url or "<title> 登录" in resp.text:
            logger.warning("⚠️ [User] 拉取订阅演员失败：Cookie 已失效，需重新登录或设置 Cookie")
            return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        actors_list = []
        for box in soup.select('#actors .actor-box'):
            a_tag = box.select_one('a[href*="/actors/"]')
            if not a_tag: continue
            actor_url = urljoin(config.BASE_URL, a_tag.get('href', ''))
            img_tag = box.select_one('img.avatar')
            avatar_url = img_tag.get('src', '') if img_tag else ""
            if avatar_url.startswith('//'): avatar_url = 'https:' + avatar_url
            name_tag = box.select_one('strong')
            actor_name = name_tag.get_text(strip=True) if name_tag else ""
            if actor_name and actor_url:
                actors_list.append({"name": actor_name, "avatar_url": avatar_url, "actor_url": actor_url})
        logger.info(f"✅ [User] 成功拉取到 {len(actors_list)} 位已订阅演员")
        return actors_list

    def get_user_lists(self, list_type: str = "mine") -> list:
        target_url = f"{config.BASE_URL}/users/favorite_lists" if list_type == "favorite" else f"{config.BASE_URL}/users/lists"
        logger.info(f"📋 [User] 正在拉取用户清单目录 (类型: {list_type})...")
        resp = self._safe_fetch_url(target_url)
        if not resp or resp.status_code != 200 or "/login" in resp.url or "<title> 登录" in resp.text:
            logger.warning(f"⚠️ [User] 拉取 [{list_type}] 清单失败：Cookie 已失效，需重新登录或设置 Cookie")
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')
        lists_data = []

        for item in soup.select('#lists .list-item, .lists .list-item, .list-item'):
            a_tag = item.select_one('a')
            if not a_tag: continue
            href = a_tag.get('href', '')
            raw_url = urljoin(config.BASE_URL, href)
            
            li_id = item.get('id', '')
            list_id = li_id.replace('list-', '') if li_id.startswith('list-') else ''
            
            if not list_id and href:
                id_match = re.search(r'id=([a-zA-Z0-9]+)', href) or re.search(r'/lists/([a-zA-Z0-9]+)', href)
                if id_match:
                    list_id = id_match.group(1)

            name_tag = item.select_one('.list-name, .title, strong')
            list_name = name_tag.get_text(strip=True) if name_tag else ""

            video_count = 0
            meta_tag = item.select_one('.meta, .extra, .value, .number, .list-meta, small, .count, .subtitle')
            if meta_tag:
                m_meta = re.search(r'(\d+)', meta_tag.get_text(strip=True))
                if m_meta:
                    video_count = int(m_meta.group(1))
            else:
                # 剔除标题文本节点，防止标题名称中的纯数字与数量黏连
                item_copy = BeautifulSoup(str(item), 'html.parser')
                for title_elem in item_copy.select('.list-name, .title, strong, font, b, h1, h2, h3, h4, h5, a'):
                    title_elem.decompose()
                remain_text = item_copy.get_text(strip=True)
                match = re.search(r'(\d+)\s*(?:部影片|部作品|影片|條|部)', remain_text) or re.search(r'(\d+)', remain_text)
                if match:
                    video_count = int(match.group(1))

            # 判断是否为预设清单 (預設清單 / 预设清单 / Default)，预设清单保留原始链接避免 302 重定向
            is_default = any(k in list_name for k in ['預設清單', '预设清单', 'Default', '预设', '預設'])
            if is_default or not list_id:
                final_url = raw_url
            else:
                final_url = f"{config.BASE_URL}/lists/{list_id}"

            lists_data.append({
                "list_id": list_id or "default",
                "list_name": list_name,
                "title": list_name,
                "video_count": video_count,
                "total_count": video_count,
                "count": video_count,
                "detail_url": final_url,
                "url": final_url,
                "is_default": is_default
            })

        logger.info(f"✅ [User] 成功拉取到 {len(lists_data)} 个 [{list_type}] 清单")
        return lists_data

    def _classify_and_extract_magnets(self, soup):
        magnet_items = soup.select('#magnets-content .item, .magnet-name')
        all_magnets_list = []
        categorized = {'normal': None, 'u': None, 'c': None, 'uc': None, '4k': None}
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for item in magnet_items:
            a_tag = item.select_one('a[href^="magnet:"]')
            if not a_tag: continue
            magnet_link = a_tag.get('href', '').strip()
            name = a_tag.get_text(strip=True)
            tags_text = " ".join([t.get_text(strip=True) for t in item.select('.tag, .meta')]) + " " + name
            all_magnets_list.append(magnet_link)

            is_4k = bool(re.search(config.REGEX_4K, tags_text, re.I))
            if is_4k and not categorized['4k']: categorized['4k'] = (magnet_link, now_str)

            has_uc = bool(re.search(config.REGEX_TAG_UC, tags_text, re.I))
            has_c  = bool(re.search(config.REGEX_TAG_C, tags_text, re.I))
            has_u  = bool(re.search(config.REGEX_TAG_U, tags_text, re.I))
            has_sub = bool(re.search(config.REGEX_SUBTITLE, tags_text, re.I))
            has_unc = bool(re.search(config.REGEX_UNCENSORED, tags_text, re.I))

            is_uc_flag = has_uc or (has_unc and has_sub)
            is_c_flag  = not is_uc_flag and (has_c or has_sub)
            is_u_flag  = not is_uc_flag and (has_u or has_unc)

            if is_uc_flag:
                if not categorized['uc']: categorized['uc'] = (magnet_link, now_str)
            elif is_c_flag:
                if not categorized['c']: categorized['c'] = (magnet_link, now_str)
            elif is_u_flag:
                if not categorized['u']: categorized['u'] = (magnet_link, now_str)
            else:
                if not categorized['normal']: categorized['normal'] = (magnet_link, now_str)

        all_magnets_json = json.dumps(all_magnets_list, ensure_ascii=False) if all_magnets_list else ""
        return all_magnets_json, categorized

    def _is_valid_image_url(self, url: str) -> bool:
        if not url or not isinstance(url, str): return False
        u = url.lower().strip()
        if u.startswith('#') or u.startswith('data:image') or u.startswith('blob:') or 'javascript:' in u:
            return False
        # 排除网页 HTML 页面链接
        if '/v/' in u or '/actors/' in u or '/lists/' in u or '/users/' in u or '/search' in u or '/plans/' in u:
            return False
        # 匹配已知图片扩展名或 CDN 路径标识
        img_exts = ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.avif')
        if any(u.endswith(ext) or f'{ext}?' in u for ext in img_exts):
            return True
        if 'jdbstatic.com' in u or '/samples/' in u or '/covers/' in u or '/sample' in u:
            return True
        return False

    def _parse_detail_page(self, html: str):
        soup = BeautifulSoup(html, 'html.parser')
        details = {'duration': '', 'director': '', 'maker': '', 'publisher': '', 'series': '', 'tags': '', 'actors': ''}
        for block in soup.select('.movie-panel-info .panel-block'):
            text = block.get_text(strip=True)
            val = block.select_one('.value')
            val_text = val.get_text(strip=True) if val else ""
            if '時長' in text or '时长' in text: details['duration'] = val_text
            elif '導演' in text or '导演' in text: details['director'] = val_text
            elif '片商' in text: details['maker'] = val_text
            elif '發行' in text or '发行' in text: details['publisher'] = val_text
            elif '系列' in text: details['series'] = val_text
            elif '類別' in text or '类别' in text: details['tags'] = ",".join([a.get_text(strip=True) for a in block.select('a')])
            elif '演員' in text or '演员' in text:
                female_actors = []
                male_actors = []
                if val:
                    for a_tag in val.select('a'):
                        name = a_tag.get_text(strip=True)
                        if not name: continue
                        
                        is_male = False
                        # 检查紧跟在 <a> 标签后面的性别标识符号标签 <strong class="symbol female">♀</strong>
                        next_sib = a_tag.find_next_sibling()
                        if next_sib:
                            sib_text = next_sib.get_text(strip=True)
                            sib_class = next_sib.get('class', [])
                            if 'male' in sib_class or '♂' in sib_text:
                                is_male = True
                        
                        if is_male:
                            male_actors.append(name)
                        else:
                            female_actors.append(name)
                
                ordered_actors = female_actors + male_actors
                details['actors'] = ",".join(ordered_actors) if ordered_actors else val_text

        # 1. 提取高清封面图 (优先匹配 .preview-video-container 内的 video-cover 或 bigImage)
        cover_url = ""
        cover_img = soup.select_one('.preview-video-container img.video-cover, img.video-cover, img.movie-cover, .column-video-cover img, a.bigImage img')
        if cover_img:
            c_url = cover_img.get('src') or cover_img.get('data-src') or cover_img.get('data-original') or ""
            if c_url and self._is_valid_image_url(c_url):
                if c_url.startswith('//'): c_url = 'https:' + c_url
                elif c_url.startswith('/'): c_url = urljoin(config.BASE_URL, c_url)
                cover_url = c_url
        details['cover_url'] = cover_url

        # 2. 停用预告片视频抓取
        details['preview_video_url'] = ""

        # 3. 提取预览剧照图集 Preview Sample Images (严格特征校验：必须包含 /samples/ 节点，100% 隔离封面 /covers/)
        preview_images = []
        sample_container = soup.select_one('.tile-images.preview-images, .preview-images, .tile-images')
        if sample_container:
            for a_item in sample_container.select('a.tile-item'):
                classes = a_item.get('class', [])
                if 'preview-video-container' in classes:
                    continue

                img_url = ""
                # 1. 优先提取 a 标签 href (JavDB 剧照原图: https://c0.jdbstatic.com/samples/xx/xxxx_l_x.jpg)
                href_candidate = a_item.get('href', '').strip()
                if href_candidate and '/samples/' in href_candidate and self._is_valid_image_url(href_candidate):
                    img_url = href_candidate

                # 2. 备选提取内部 img 标签 (JavDB 剧照缩略图: https://c0.jdbstatic.com/samples/xx/xxxx_s_x.jpg)
                if not img_url:
                    img_tag = a_item.select_one('img')
                    if img_tag:
                        for candidate in [img_tag.get('data-src'), img_tag.get('data-original'), img_tag.get('data-lazy-src'), img_tag.get('src')]:
                            if candidate and '/samples/' in candidate and self._is_valid_image_url(candidate):
                                img_url = candidate
                                break

                if img_url:
                    if img_url.startswith('//'): img_url = 'https:' + img_url
                    elif img_url.startswith('/'): img_url = urljoin(config.BASE_URL, img_url)

                    if '/samples/' in img_url and self._is_valid_image_url(img_url) and img_url not in preview_images:
                        preview_images.append(img_url)

        details['preview_images'] = json.dumps(preview_images, ensure_ascii=False)

        all_magnets_str, categorized = self._classify_and_extract_magnets(soup)
        return details, all_magnets_str, categorized

    def _update_movie_detail(self, code: str, details: dict, all_magnets_str: str, magnets: dict):
        conn = self._get_db_conn()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE movies SET
                duration = ?, director = ?, maker = ?, publisher = ?, series = ?, tags = ?, actors = ?,
                preview_video_url = ?, preview_images = ?,
                cover_url = CASE WHEN ? != '' THEN ? ELSE cover_url END,
                magnets = CASE WHEN ? != '' THEN ? ELSE magnets END, 
                magnet_normal = COALESCE(?, magnet_normal), 
                magnet_normal_fetched_at = CASE WHEN ? IS NOT NULL THEN ? ELSE magnet_normal_fetched_at END, 
                magnet_u = COALESCE(?, magnet_u), 
                magnet_u_fetched_at = CASE WHEN ? IS NOT NULL THEN ? ELSE magnet_u_fetched_at END,
                magnet_c = COALESCE(?, magnet_c), 
                magnet_c_fetched_at = CASE WHEN ? IS NOT NULL THEN ? ELSE magnet_c_fetched_at END, 
                magnet_uc = COALESCE(?, magnet_uc), 
                magnet_uc_fetched_at = CASE WHEN ? IS NOT NULL THEN ? ELSE magnet_uc_fetched_at END, 
                magnet_4k = COALESCE(?, magnet_4k), 
                magnet_4k_fetched_at = CASE WHEN ? IS NOT NULL THEN ? ELSE magnet_4k_fetched_at END,
                is_detail_fetched = 1,
                is_vip_blocked = 0
            WHERE code = ?
        ''', (
            details['duration'], details['director'], details['maker'], details['publisher'],
            details['series'], details['tags'], details['actors'],
            details.get('preview_video_url', ''), details.get('preview_images', '[]'),
            details.get('cover_url', ''), details.get('cover_url', ''),
            all_magnets_str, all_magnets_str,
            magnets['normal'][0] if magnets['normal'] else None, magnets['normal'][1] if magnets['normal'] else None, magnets['normal'][1] if magnets['normal'] else None,
            magnets['u'][0] if magnets['u'] else None, magnets['u'][1] if magnets['u'] else None, magnets['u'][1] if magnets['u'] else None,
            magnets['c'][0] if magnets['c'] else None, magnets['c'][1] if magnets['c'] else None, magnets['c'][1] if magnets['c'] else None,
            magnets['uc'][0] if magnets['uc'] else None, magnets['uc'][1] if magnets['uc'] else None, magnets['uc'][1] if magnets['uc'] else None,
            magnets['4k'][0] if magnets['4k'] else None, magnets['4k'][1] if magnets['4k'] else None, magnets['4k'][1] if magnets['4k'] else None,
            code
        ))
        conn.commit()
        conn.close()
        logger.debug(f"💾 [DB] 番号 [{code}] 详情、磁力与预告图库更新完成")

    def _mark_detail_fetched_only(self, code: str):
        """将因 VIP 权限限制 (如跳转至 /plans/ypay) 或无权限访问的影片标记为 is_detail_fetched = 1 与 is_vip_blocked = 1，自动隐匿在海报墙外并避免以后无休止重复抓取"""
        conn = self._get_db_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE movies SET is_detail_fetched = 1, is_vip_blocked = 1 WHERE code = ?", (code,))
        conn.commit()
        conn.close()
        logger.info(f"🔒 [DB] 番号 [{code}] 已标记为 is_vip_blocked = 1 (自动在前端海报墙隐匿，且防止重复探寻)")

    def _parse_list_page(self, html: str, base_url: str):
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.select('.movie-list .item, .grid-view .item')
        movies = []
        for item in items:
            a_tag = item.select_one('a.box') or item.select_one('a')
            if not a_tag: continue
            detail_url = urljoin(base_url, a_tag.get('href', ''))
            title = a_tag.get('title', '').strip()
            code_el = item.select_one('strong')
            code = code_el.get_text(strip=True) if code_el else ""
            if not title:
                title_el = item.select_one('.video-title') or item.select_one('.title')
                if title_el:
                    for strong_tag in title_el.find_all('strong'): strong_tag.decompose()
                    title = title_el.get_text(strip=True)
            img_el = item.select_one('img')
            cover_url = ""
            if img_el:
                src_candidates = [
                    img_el.get('data-src'),
                    img_el.get('data-original'),
                    img_el.get('data-lazy-src'),
                    img_el.get('src')
                ]
                for candidate in src_candidates:
                    if candidate and not candidate.startswith('data:image') and not candidate.startswith('blob:'):
                        cover_url = candidate
                        break
                if cover_url.startswith('//'): cover_url = 'https:' + cover_url
                elif cover_url.startswith('/'): cover_url = urljoin(base_url, cover_url)

            date_el = item.select_one('.meta')
            release_date = date_el.get_text(strip=True) if date_el else ""
            score_el = item.select_one('.value')
            raw_score = score_el.get_text(strip=True) if score_el else ""
            score, score_number = "", ""
            if raw_score:
                parts = re.split(r'[,，]', raw_score)
                score = parts[0].strip() if len(parts) >= 1 else ""
                score_number = parts[1].strip() if len(parts) >= 2 else ""

            if code:
                movies.append({
                    'code': code, 'title': title, 'detail_url': detail_url,
                    'cover_url': cover_url, 'score': score,
                    'score_number': score_number, 'release_date': release_date
                })

        pagination = soup.select_one('.pagination, .pagination-list')
        has_next = False
        if pagination:
            next_btn = pagination.select_one('a.pagination-next, a[rel="next"]')
            if next_btn and 'is-disabled' not in next_btn.get('class', []):
                has_next = True
        return movies, has_next

    def _save_movies_index(self, movies: list, list_id: str = None):
        conn = self._get_db_conn()
        cursor = conn.cursor()
        for m in movies:
            cursor.execute('''
                INSERT INTO movies (code, title, detail_url, cover_url, score, score_number, release_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    title = excluded.title, detail_url = excluded.detail_url, 
                    cover_url = CASE WHEN excluded.cover_url != '' THEN excluded.cover_url ELSE movies.cover_url END,
                    score = excluded.score, score_number = excluded.score_number, release_date = excluded.release_date
            ''', (m['code'], m['title'], m['detail_url'], m['cover_url'], m['score'], m['score_number'], m['release_date']))

            if list_id:
                cursor.execute('SELECT in_lists FROM movies WHERE code = ?', (m['code'],))
                row = cursor.fetchone()
                current_lists = []
                if row and row[0]:
                    try:
                        current_lists = json.loads(row[0])
                        if not isinstance(current_lists, list): current_lists = []
                    except Exception:
                        current_lists = []
                if list_id not in current_lists:
                    current_lists.append(list_id)
                    cursor.execute('UPDATE movies SET in_lists = ? WHERE code = ?', (json.dumps(current_lists, ensure_ascii=False), m['code']))

        conn.commit()
        conn.close()
        logger.info(f"📥 [DB] 索引记录批量存库成功 ({len(movies)} 条)")

    def fetch_index(self, target_url: str, max_pages: int = None, smart_incremental: bool = False) -> list:
        current_url = target_url
        page = 1
        scraped_codes = []

        # 解析抓取上下文类型与代号 (清单 vs 演员)
        list_id = None
        actor_id = None
        if '/lists/' in target_url or 'list_detail' in target_url:
            match = re.search(r'id=([a-zA-Z0-9]+)', target_url) or re.search(r'/lists/([a-zA-Z0-9]+)', target_url)
            if match: list_id = match.group(1)
        elif '/actors/' in target_url:
            match = re.search(r'/actors/([a-zA-Z0-9]+)', target_url)
            if match: actor_id = match.group(1)

        while current_url:
            if self.cancel_check and self.cancel_check():
                self.safe_log(f"🛑 [Cancel Guard] 收到用户取消任务指令，终止抓取 [{current_url}]", "warning")
                break

            self.safe_log(f"📄 [Scrape] 正在抓取索引页 [{page}]: {current_url}")
            resp = self._safe_fetch_url(current_url)
            if not resp or resp.status_code != 200: 
                self.safe_log("❌ [Scrape] 索引页响应异常，结束翻页", "error")
                break

            movies, has_next = self._parse_list_page(resp.text, current_url)
            if movies:
                self._save_movies_index(movies, list_id=list_id)
                self.safe_log(f"📥 [DB] 索引记录批量存库成功 ({len(movies)} 条)")
                for m in movies:
                    if m['code'] not in scraped_codes:
                        scraped_codes.append(m['code'])

                if smart_incremental:
                    conn = self._get_db_conn()
                    cursor = conn.cursor()
                    exist_count = 0
                    for m in movies:
                        cursor.execute("SELECT is_detail_fetched, in_lists, actors, magnet_uc, release_date FROM movies WHERE code = ?", (m['code'],))
                        row = cursor.fetchone()
                        if row and row[0] == 1:
                            has_uc = row[3] and len(str(row[3]).strip()) > 0
                            r_date_str = str(row[4]).strip() if row[4] else ""
                            is_old_release = False
                            date_match = re.search(r'\d{4}-\d{2}-\d{2}', r_date_str)
                            if date_match:
                                cutoff_date = (datetime.now() - timedelta(days=config.OLD_MOVIE_DAYS)).strftime('%Y-%m-%d')
                                is_old_release = date_match.group(0) < cutoff_date

                            is_complete = has_uc or is_old_release
                            if is_complete:
                                if list_id:
                                    try:
                                        in_lists = json.loads(row[1]) if row[1] else []
                                        if isinstance(in_lists, list) and list_id in in_lists:
                                            exist_count += 1
                                    except Exception: pass
                                elif actor_id:
                                    if row[2] and len(row[2].strip()) > 0:
                                        exist_count += 1
                                else:
                                    exist_count += 1
                    conn.close()

                    if exist_count >= config.INCREMENTAL_THRESHOLD:
                        ctx_desc = f"清单 [{list_id}]" if list_id else (f"演员 [{actor_id}]" if actor_id else "目标")
                        self.safe_log(f"🛑 [Smart Incremental] 检测到本页有 {exist_count} 部影片在 {ctx_desc} 的历史记录中已存在且详情完整，智能判定已接轨历史，终止后续翻页！")
                        break

            if max_pages and page >= max_pages:
                self.safe_log(f"✅ [Scrape] 达到最大指定抓取页数 ({max_pages} 页)，停止翻页。")
                break

            if has_next:
                page += 1
                if 'page=' in current_url: current_url = re.sub(r'page=\d+', f'page={page}', current_url)
                else: current_url = f"{current_url}{'&' if '?' in current_url else '?'}page={page}"
            else: 
                self.safe_log("🔚 [Scrape] 抓取至末页")
                break

        return scraped_codes

    def fetch_details(self, limit: int = None, target_codes: list = None):
        conn = self._get_db_conn()
        cursor = conn.cursor()

        where_clauses = [
            "detail_url IS NOT NULL",
            "(is_vip_blocked IS NULL OR is_vip_blocked = 0)"
        ]
        params = []

        if target_codes and len(target_codes) > 0:
            placeholders = ','.join(['?'] * len(target_codes))
            where_clauses.append(f"code IN ({placeholders})")
            params.extend(target_codes)

        condition_sql = f'''(
            is_detail_fetched IS NULL 
            OR is_detail_fetched != 1 
            OR (
              (magnet_uc IS NULL OR magnet_uc = '') 
              AND (magnet_c IS NULL OR magnet_c = '') 
              AND (magnet_4k IS NULL OR magnet_4k = '') 
              AND (magnet_u IS NULL OR magnet_u = '') 
              AND (magnet_normal IS NULL OR magnet_normal = '')
            )
            OR (
              release_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
              AND release_date >= date('now', '-{config.OLD_MOVIE_DAYS} days')
              AND (magnet_uc IS NULL OR magnet_uc = '')
            )
        )'''
        where_clauses.append(condition_sql)

        query = "SELECT code, detail_url FROM movies WHERE " + " AND ".join(where_clauses)
        if limit:
            query += ' LIMIT ?'
            params.append(limit)

        cursor.execute(query, params)
        pending = cursor.fetchall()
        conn.close()

        self.safe_log(f"🚀 [Scrape] 筛选出 {len(pending)} 部待更新/追踪巡检影片")
        for idx, (code, url) in enumerate(pending, start=1):
            if self.cancel_check and self.cancel_check():
                self.safe_log(f"🛑 [Cancel Guard] 收到用户取消任务指令，中断详情抓取过程。", "warning")
                break

            self.safe_log(f"🔎 [{idx}/{len(pending)}] 抓取详情: {code} ({url})")
            resp = self._safe_fetch_url(url)
            if resp and resp.status_code == 200:
                resp_url = str(getattr(resp, 'url', ''))
                is_ypay_redirect = 'plans/ypay' in resp_url or 'plans/ypay' in resp.text or 'ypay' in resp_url
                details, all_magnets, magnets = self._parse_detail_page(resp.text)
                
                is_empty_info = not details.get('actors') and not details.get('duration') and not details.get('maker')

                if is_ypay_redirect or is_empty_info:
                    if is_ypay_redirect:
                        self.safe_log(f"🔒 [Paywall Guard] 番号 [{code}] 触发 VIP 权限限制重定向 ({resp_url})，标记为已尝试，以后不再重复抓取。", "warning")
                    else:
                        self.safe_log(f"⚠️ [Parse Guard] 番号 [{code}] 详情页未匹配到有效信息，标记为已处理。", "warning")
                    self._mark_detail_fetched_only(code)
                else:
                    has_uc = bool(magnets.get('uc'))
                    try:
                        all_m_list = json.loads(all_magnets) if all_magnets else []
                        total_m = len(all_m_list)
                    except Exception:
                        total_m = 0

                    if total_m > 0:
                        self.safe_log(f"💾 [DB] 番号 [{code}] 详情与磁力存库成功 (已获取 {total_m} 条磁力 | 无码中字: {'✅' if has_uc else '❌'})")
                    else:
                        self.safe_log(f"🔍 [DB] 番号 [{code}] 详情已存库 (网页暂无可用磁力，已开启 30 天新片追查模式)")

    def search_exact_movie_url(self, code: str) -> str:
        search_url = f"{config.BASE_URL}/search?q={quote(code)}&sb=0"
        logger.info(f"🔍 [Search] 精准搜索番号 [{code}] -> URL: {search_url}")
        resp = self._safe_fetch_url(search_url)
        if not resp or resp.status_code != 200: return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        for item in soup.select('.movie-list .item'):
            strong_tag = item.select_one('.video-title strong')
            if strong_tag and strong_tag.get_text(strip=True).upper() == code.upper():
                a_tag = item.select_one('a.box')
                if a_tag and a_tag.get('href'): return urljoin(config.BASE_URL, a_tag.get('href'))
        return None

    def update_by_code(self, code: str) -> bool:
        code = code.strip()
        detail_url = self.search_exact_movie_url(code)
        if not detail_url: 
            logger.warning(f"⚠️ [Search] 未找到番号 [{code}]")
            return False
            
        logger.info(f"🔗 [Search] 匹配到番号 [{code}] 目标链接: {detail_url}")
        resp = self._safe_fetch_url(detail_url)
        if not resp or resp.status_code != 200: return False

        details, all_magnets_str, magnets = self._parse_detail_page(resp.text)
        conn = self._get_db_conn()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO movies (code, detail_url) VALUES (?, ?)", (code, detail_url))
        cursor.execute("UPDATE movies SET detail_url = ? WHERE code = ?", (detail_url, code))
        conn.commit()
        conn.close()
        logger.info(f"📥 [DB] 番号 [{code}] 存库成功")
        self._update_movie_detail(code, details, all_magnets_str, magnets)
        return True

    # ================= 🔻 JavDB 清单管理 =================

    def toggle_video_in_list(
        self, 
        code_or_url: str, 
        list_id: str, 
        checked: Optional[bool] = None
    ) -> bool:
        """
        【存入 / 移除 清单】
        1. 从传入参数中提取唯一 video_id (如 EKbN0)
        2. 向 JavDB 发送 Content-Type: application/json 的 Payload: {"video_id": "...", "list_id": "...", "checked": true/false}
        3. 成功后更新 SQLite 中该影片记录的 in_lists 字段
        """
        clean_input = code_or_url.strip()
        
        # 提取 video_id (处理 /v/EKbN0、完整 URL 或纯 ID)
        match = re.search(r'/v/([A-Za-z0-9]+)', clean_input)
        video_id = match.group(1) if match else clean_input.split('/')[-1]

        # 查库获取该影片的展示番号(code)以及当前已存清单列表
        conn = self._get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT code, in_lists, detail_url FROM movies WHERE code = ? OR detail_url LIKE ?", 
            (clean_input, f"%{video_id}%")
        )
        row = cursor.fetchone()
        conn.close()

        movie_code = clean_input
        current_lists = []
        
        if row:
            movie_code = row[0]
            try:
                current_lists = json.loads(row[1]) if row[1] else []
            except:
                current_lists = []

        # 若调用时未显式指定 checked 参数，则根据当前是否存在于清单中自动取反
        if checked is None:
            checked = list_id not in current_lists

        url = f"{config.BASE_URL}/users/save_video_to_list"
        payload = {
            "video_id": video_id,
            "list_id": list_id,
            "checked": checked
        }
        
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/json",
            "Referer": f"{config.BASE_URL}/v/{video_id}"
        }

        try:
            req_headers = {
                "User-Agent": self.user_agent,
                "Cookie": self.cookies_string or config.DEFAULT_COOKIES,
            }
            req_headers.update(headers)

            logger.info(f"📤 [List API] 正在发送网络请求 -> video_id: {video_id}, list_id: {list_id}, checked: {checked}")
            
            # 使用 json=payload，requests 会自动序列化为小写 true/false 的标准 JSON
            resp = self.session.post(url, json=payload, headers=req_headers, timeout=config.REQUEST_TIMEOUT)

            if resp and resp.status_code in [200, 201, 204]:
                # 1. 网络请求成功后，同步更新本地 SQLite 数据库中的 in_lists 字段
                self._sync_local_list_status(movie_code, video_id, list_id, is_checked=checked)
                
                # 2. 打印精准规范日志
                if checked:
                    logger.info(f"已将‘{movie_code}’加入至‘{list_id}’")
                else:
                    logger.info(f"已将‘{movie_code}’从‘{list_id}’中移除")
                return True
            else:
                logger.error(f"❌ [List API] 更新清单失败，HTTP 状态码: {resp.status_code if resp else 'None'}")
                return False
        except Exception as e:
            logger.error(f"❌ [List API] 网络异常: {e}")
            return False

    def _sync_local_list_status(self, movie_code: str, video_id: str, list_id: str, is_checked: bool):
        """私有辅助方法：精准维护 SQLite 中 in_lists 的 JSON 数组"""
        conn = self._get_db_conn()
        cursor = conn.cursor()
        
        # 查找记录
        cursor.execute(
            "SELECT code, in_lists FROM movies WHERE code = ? OR detail_url LIKE ?",
            (movie_code, f"%{video_id}%")
        )
        row = cursor.fetchone()
        
        if row:
            target_code, in_lists_json = row[0], row[1]
            try:
                current_lists = json.loads(in_lists_json) if in_lists_json else []
            except:
                current_lists = []

            if is_checked:
                if list_id not in current_lists:
                    current_lists.append(list_id)
            else:
                if list_id in current_lists:
                    current_lists.remove(list_id)

            updated_json = json.dumps(current_lists, ensure_ascii=False)
            cursor.execute("UPDATE movies SET in_lists = ? WHERE code = ?", (updated_json, target_code))
            conn.commit()
            logger.info(f"💾 [DB Synced] 番号 [{target_code}] 的 in_lists 字段已同步更新为: {updated_json}")
        else:
            logger.warning(f"⚠️ [DB Synced] 未在数据库中找到 [{movie_code}] 的记录，跳过本地 in_lists 字段更新")
            
        conn.close()
    # ================= 🔻 115 离线推送与状态同步 =================

    @staticmethod
    def generate_auto_path(movie_info: dict, magnet_type: str) -> str:
        category_dir = "有码"
        
        actors_raw = movie_info.get('actors', '')
        primary_actor = "未知演员"
        if actors_raw and actors_raw.strip():
            actor_list = [a.strip() for a in re.split(r'[,，]', actors_raw) if a.strip()]
            if actor_list: primary_actor = actor_list[0]
                
        primary_actor = re.sub(r'[\\/:*?"<>|]', '_', primary_actor)
                
        type_map = {
            'magnet_uc': '中字破解',
            'magnet_c': '中字有码',
            'magnet_u': '高清破解',
            'magnet_4k': '4K超清',
            'magnet_normal': '普通磁力'
        }
        type_dir = type_map.get(magnet_type, '其他磁力')
        date_dir = datetime.now().strftime("%Y-%m-%d")
        
        return f"/{category_dir}/{primary_actor}/{type_dir}/{date_dir}"

    def push_to_115_gateway(self, urls: str, wp_path: str) -> dict:
        endpoint = f"{config.GATEWAY_115_URL.rstrip('/')}/api/115/offline/external"
        headers = {"X-API-KEY": config.GATEWAY_115_API_KEY}
        payload = {"wp_path": wp_path, "urls": urls}
        self.safe_log(f"🚀 [115 Gateway] 提交离线任务到 115 网关 | 保存路径: {wp_path}")
        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                self.safe_log(f"✅ [115 Gateway] 网关返回结果: {resp.text}")
                return resp.json()
            else:
                self.safe_log(f"❌ [115 Gateway] 网关返回错误 (HTTP {resp.status_code}): {resp.text}", "error")
                return {"code": -1, "message": f"115 网关报错: {resp.text}"}
        except Exception as e:
            self.safe_log(f"❌ [115 Gateway] 网络异常: {e}", "error")
            return {"code": -1, "message": str(e)}

    def record_push_history(self, code: str, magnet_type: str, magnet_url: str, wp_path: str):
        info_hash = ""
        hash_match = re.search(r'btih:([a-fA-F0-9]{40}|[2-7a-zA-Z]{32})', magnet_url, re.I)
        if hash_match:
            info_hash = hash_match.group(1).lower()

        conn = self._get_db_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO push_history (code, magnet_type, magnet_url, info_hash, wp_path, status)
            VALUES (?, ?, ?, ?, ?, 0)
        ''', (code, magnet_type, magnet_url, info_hash, wp_path))
        conn.commit()
        conn.close()
        self.safe_log(f"📝 [Push History] 记录番号 [{code}] 离线任务 (Hash: {info_hash})")

    def delete_by_code(self, code: str) -> bool:
        """从数据库中精准删除指定番号的影片记录"""
        conn = self._get_db_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM movies WHERE code = ?", (code,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        if affected > 0:
            self.safe_log(f"🗑️ [DB] 成功从数据库删除番号 [{code}] 的影片记录")
            return True
        return False

    def clear_database(self) -> int:
        """清空 movies 数据库表中的所有记录"""
        conn = self._get_db_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM movies")
        count = cursor.rowcount
        conn.commit()
        conn.close()
        self.safe_log(f"🧹 [DB] 成功清空数据库，共删除 {count} 条影片记录")
        return count

    def push_incremental_magnets_to_115(
            self, 
            start_time: str, 
            end_time: str, 
            magnet_type: str = "magnet_uc",
            custom_wp_path: str = None
        ) -> dict:
            valid_fields = ['magnet_normal', 'magnet_u', 'magnet_c', 'magnet_uc', 'magnet_4k']
            if magnet_type not in valid_fields:
                raise ValueError(f"无效的磁力槽位，支持: {valid_fields}")

            time_field = f"{magnet_type}_fetched_at"
            
            conn = self._get_db_conn()
            cursor = conn.cursor()
            query = f"""
                SELECT code, title, actors, tags, {magnet_type}, {time_field}
                FROM movies
                WHERE {time_field} BETWEEN ? AND ?
                  AND {magnet_type} IS NOT NULL AND {magnet_type} != ''
                  AND code NOT IN (SELECT code FROM push_history WHERE magnet_type = ?)
            """
            cursor.execute(query, (start_time, end_time, magnet_type))
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                self.safe_log(f"ℹ️ [115 Push] 时间范围内无待推送的 [{magnet_type}] 磁力")
                return {"total": 0, "success": 0, "failed": 0, "message": "无新磁力需要推送"}

            # ================= 🔻 1. 检查 115 剩余离线配额 🔻 =================
            quota_info = self.check_115_quota()
            if not quota_info.get("allow_push"):
                self.safe_log("⛔ [115 Guard] 115 离线配额已耗尽，中断推送任务！", "warning")
                return {
                    "total": len(rows),
                    "success": 0,
                    "failed": len(rows),
                    "message": "115 离线配额已用尽，中断推送",
                    "quota": quota_info
                }

            remaining_quota = quota_info.get("remaining", 0)
            total_matched = len(rows)

            # 🎯 配额防爆截断：如果待推送条数超出了剩余配额，仅处理前 remaining_quota 条
            if total_matched > remaining_quota:
                self.safe_log(
                    f"⚠️ [115 Guard] 检索到 {total_matched} 条待推送，但 115 剩余配额仅 {remaining_quota} 条。"
                    f"本次将按配额上限截断，只推送前 {remaining_quota} 条！", "warning"
                )
                rows = rows[:remaining_quota]
            # ===================================================================

            self.safe_log(f"📦 [115 Push] 实际准备推送 {len(rows)} 条记录 (匹配总数: {total_matched}, 剩余配额: {remaining_quota})，开始分批提交...")
            
            items = []
            for r in rows:
                movie_info = {'code': r[0], 'title': r[1], 'actors': r[2], 'tags': r[3]}
                wp_path = custom_wp_path or self.generate_auto_path(movie_info, magnet_type)
                items.append({'code': r[0], 'magnet_url': r[4], 'wp_path': wp_path})

            path_groups = {}
            for item in items:
                p = item['wp_path']
                if p not in path_groups: path_groups[p] = []
                path_groups[p].append(item)

            batch_size = config.PUSH_BATCH_SIZE
            total_pushed = 0
            failed_count = 0
            quota_exhausted = False  # 熔断标记

            for path, item_list in path_groups.items():
                if quota_exhausted:
                    break

                for i in range(0, len(item_list), batch_size):
                    # 🔻 2. 批次级别配额二次防护 🔻
                    if total_pushed >= remaining_quota:
                        self.safe_log(f"⛔ [115 Guard] 批次推送已达到本次允许的配额上限 ({remaining_quota})，彻底终止后续任务！", "warning")
                        quota_exhausted = True
                        break

                    batch = item_list[i : i + batch_size]
                    urls_payload = "\n".join([it['magnet_url'] for it in batch])
                    
                    self.safe_log(f"⏳ [115 Push] 推送批次 ({i+1}~{min(i+batch_size, len(item_list))}/{len(item_list)}) -> 路径: {path}")
                    res = self.push_to_115_gateway(urls=urls_payload, wp_path=path)
                    
                    if res.get('code') == 0 or res.get('state') is True:
                        for it in batch:
                            self.record_push_history(it['code'], magnet_type, it['magnet_url'], path)
                            total_pushed += 1
                    else:
                        failed_count += len(batch)

                    if i + batch_size < len(item_list):
                        sleep_time = random.uniform(config.PUSH_INTERVAL_MIN, config.PUSH_INTERVAL_MAX)
                        self.safe_log(f"🛡️ [115 防风控保护] 批次间随机休眠 {sleep_time:.1f} 秒...")
                        time.sleep(sleep_time)

            # 最终计算未成功或未推送的总失败/跳过数
            skipped_count = len(items) - total_pushed - failed_count
            final_failed_or_skipped = failed_count + max(0, skipped_count)

            self.safe_log(f"🎉 [115 Push] 增量推送结束: 成功 {total_pushed} 条，失败/未推送 {final_failed_or_skipped} 条")
            return {
                "total": total_matched,
                "pushed_limit": len(rows),
                "success": total_pushed,
                "failed": final_failed_or_skipped,
                "remaining_quota": max(0, remaining_quota - total_pushed),
                "message": f"增量推送完成：成功 {total_pushed} 条，失败/截断 {final_failed_or_skipped} 条"
            }


    def push_smart_priority_magnets_to_115(self, target_codes: list = None, custom_wp_path: str = None) -> dict:
        """
        【智能优先级一条龙推送】
        优先级顺序: UC (无码中字/破解) > 4K (4K超清) > C (有码中字)
        升级逻辑: 若数据库中历史已推送 C 磁力，但后来探寻到了更高的 UC/4K 磁力，则触发【升阶推送】，仅推送更高的 UC/4K 磁力！ (自动忽略无中字原版 U / Normal 磁力)
        """
        PRIORITY_MAP = {'magnet_uc': 1, 'magnet_4k': 2, 'magnet_c': 3}
        
        conn = self._get_db_conn()
        cursor = conn.cursor()
        
        # 1. 查出 push_history 中每部影片已推送的最高优先级 rank
        cursor.execute("SELECT code, magnet_type FROM push_history")
        pushed_rows = cursor.fetchall()
        pushed_best_rank = {}
        pushed_best_type = {}
        for c, m_type in pushed_rows:
            r = PRIORITY_MAP.get(m_type, 99)
            if c not in pushed_best_rank or r < pushed_best_rank[c]:
                pushed_best_rank[c] = r
                pushed_best_type[c] = m_type

        # 2. 查出待检测的影片
        if target_codes and len(target_codes) > 0:
            placeholders = ','.join(['?'] * len(target_codes))
            cursor.execute(f"SELECT code, title, actors, tags, magnet_uc, magnet_4k, magnet_c FROM movies WHERE code IN ({placeholders})", target_codes)
        else:
            cursor.execute("SELECT code, title, actors, tags, magnet_uc, magnet_4k, magnet_c FROM movies WHERE is_detail_fetched = 1")
        
        movie_rows = cursor.fetchall()
        conn.close()

        items_to_push = []
        for r in movie_rows:
            code, title, actors, tags = r[0], r[1], r[2], r[3]
            m_uc, m_4k, m_c = r[4], r[5], r[6]

            m_candidates = [
                ('magnet_uc', m_uc, 1),
                ('magnet_4k', m_4k, 2),
                ('magnet_c', m_c, 3),
            ]

            best_available_type = None
            best_available_url = None
            best_available_rank = 99

            for m_type, m_url, rank in m_candidates:
                if m_url and len(str(m_url).strip()) > 0:
                    best_available_type = m_type
                    best_available_url = str(m_url).strip()
                    best_available_rank = rank
                    break

            if not best_available_type:
                continue

            prev_rank = pushed_best_rank.get(code, 99)
            prev_type = pushed_best_type.get(code, "未推送")

            # 新影片未推送过，或者探寻到了比此前推送过的磁力更高优先级的磁力 (如此前推送 C (3)，现在发现了 UC (1))
            if prev_rank == 99 or best_available_rank < prev_rank:
                movie_info = {'code': code, 'title': title, 'actors': actors, 'tags': tags}
                wp_path = custom_wp_path or self.generate_auto_path(movie_info, best_available_type)
                
                upgrade_tag = f"(智能升阶推送: {prev_type} -> {best_available_type})" if prev_rank != 99 else "(首次离线)"
                items_to_push.append({
                    'code': code,
                    'magnet_type': best_available_type,
                    'magnet_url': best_available_url,
                    'wp_path': wp_path,
                    'upgrade_tag': upgrade_tag
                })

        if not items_to_push:
            self.safe_log("ℹ️ [115 Smart Push] 当前无待推送或待升阶的高质量磁力")
            return {"total": 0, "success": 0, "failed": 0, "message": "当前所有影片磁力均已是最高优先级离线状态"}

        # 3. 检查 115 配额
        quota_info = self.check_115_quota()
        if not quota_info.get("allow_push"):
            self.safe_log("⛔ [115 Guard] 115 离线配额已用尽，中断智能一条龙推送！", "warning")
            return {"total": len(items_to_push), "success": 0, "failed": len(items_to_push), "message": "115 离线配额已用尽"}

        remaining_quota = quota_info.get("remaining", 0)
        if len(items_to_push) > remaining_quota:
            self.safe_log(f"⚠️ [115 Guard] 待推送 {len(items_to_push)} 条，剩余配额 {remaining_quota} 条，将按上限截断！", "warning")
            items_to_push = items_to_push[:remaining_quota]

        self.safe_log(f"🚀 [115 Smart Push] 开始批量提交 {len(items_to_push)} 条高优先级/升阶磁力推送...")

        # 4. 按路径分组分批提交
        path_groups = {}
        for item in items_to_push:
            p = item['wp_path']
            if p not in path_groups: path_groups[p] = []
            path_groups[p].append(item)

        batch_size = config.PUSH_BATCH_SIZE
        total_pushed = 0
        failed_count = 0

        for path, item_list in path_groups.items():
            for i in range(0, len(item_list), batch_size):
                batch = item_list[i:i + batch_size]
                urls = "\n".join([it['magnet_url'] for it in batch])
                res = self.push_to_115_gateway(urls=urls, wp_path=path)

                if res.get("code") == 0 or res.get("state") is True:
                    for it in batch:
                        self.record_push_history(it['code'], it['magnet_type'], it['magnet_url'], path)
                        total_pushed += 1
                        self.safe_log(f"✅ [115 Smart Push] 番号 [{it['code']}] 推送成功 {it['upgrade_tag']} -> [{path}]")
                else:
                    failed_count += len(batch)
                    self.safe_log(f"❌ [115 Smart Push] 批次推送失败: {res.get('message')}", "error")

                if i + batch_size < len(item_list):
                    sleep_time = random.uniform(config.PUSH_INTERVAL_MIN, config.PUSH_INTERVAL_MAX)
                    time.sleep(sleep_time)

        self.safe_log(f"🎉 [115 Smart Push] 智能一条龙推送结束: 成功 {total_pushed} 条，失败 {failed_count} 条")
        return {
            "total": len(items_to_push),
            "success": total_pushed,
            "failed": failed_count,
            "message": f"智能一条龙推送完成：成功离线/升阶 {total_pushed} 条！"
        }

    def push_by_actor_to_115(
        self, 
        actor_name: str, 
        magnet_type: str = "smart_priority", 
        custom_wp_path: str = None
    ) -> dict:
        """【按演员批量推送 115 离线】检索本地库中包含该演员的影片，按策略提交 115 离线"""
        actor_name = actor_name.strip()
        conn = self._get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT code FROM movies WHERE actors LIKE ? AND (is_vip_blocked IS NULL OR is_vip_blocked = 0)", (f"%{actor_name}%",))
        rows = cursor.fetchall()
        conn.close()

        codes = [r[0] for r in rows if r[0]]
        if not codes:
            self.safe_log(f"⚠️ [115 Actor Push] 本地数据库中暂无演员 [{actor_name}] 的影片记录")
            return {"total": 0, "success": 0, "failed": 0, "message": f"本地库中未找到演员 [{actor_name}] 的影片记录"}

        self.safe_log(f"🎬 [115 Actor Push] 匹配到演员 [{actor_name}] 共 {len(codes)} 部影片，开始智能推送...")
        if magnet_type == "smart_priority":
            return self.push_smart_priority_magnets_to_115(target_codes=codes, custom_wp_path=custom_wp_path)
        else:
            return self._push_target_codes_with_type(codes, magnet_type, custom_wp_path)

    def push_by_list_to_115(
        self, 
        list_id_or_url: str, 
        magnet_type: str = "smart_priority", 
        custom_wp_path: str = None
    ) -> dict:
        """【按清单批量推送 115 离线】检索本地库中属于该清单的影片，按策略提交 115 离线"""
        list_id = list_id_or_url.split('/')[-1] if '/' in list_id_or_url else list_id_or_url
        list_id = list_id.strip()

        conn = self._get_db_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT code, in_lists FROM movies WHERE is_vip_blocked IS NULL OR is_vip_blocked = 0")
        rows = cursor.fetchall()
        conn.close()

        codes = []
        for r in rows:
            c, in_lists = r[0], r[1]
            if in_lists and c:
                try:
                    l_arr = json.loads(in_lists) if isinstance(in_lists, str) else (in_lists if isinstance(in_lists, list) else [])
                    if list_id in l_arr:
                        codes.append(c)
                except Exception:
                    pass

        if not codes:
            self.safe_log(f"⚠️ [115 List Push] 本地数据库中暂无清单 [{list_id}] 的关联影片记录")
            return {"total": 0, "success": 0, "failed": 0, "message": f"本地库中未找到清单 [{list_id}] 的关联影片"}

        self.safe_log(f"📑 [115 List Push] 匹配到清单 [{list_id}] 共 {len(codes)} 部影片，开始智能推送...")
        if magnet_type == "smart_priority":
            return self.push_smart_priority_magnets_to_115(target_codes=codes, custom_wp_path=custom_wp_path)
        else:
            return self._push_target_codes_with_type(codes, magnet_type, custom_wp_path)

    def _push_target_codes_with_type(self, target_codes: list, magnet_type: str, custom_wp_path: str = None) -> dict:
        valid_fields = ['magnet_normal', 'magnet_u', 'magnet_c', 'magnet_uc', 'magnet_4k']
        if magnet_type not in valid_fields:
            magnet_type = 'magnet_uc'

        conn = self._get_db_conn()
        cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(target_codes))
        query = f"""
            SELECT code, title, actors, tags, {magnet_type}
            FROM movies
            WHERE code IN ({placeholders})
              AND {magnet_type} IS NOT NULL AND {magnet_type} != ''
              AND code NOT IN (SELECT code FROM push_history WHERE magnet_type = ?)
        """
        cursor.execute(query, target_codes + [magnet_type])
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            self.safe_log(f"ℹ️ [115 Push] 目标影片中无新待推送的 [{magnet_type}] 磁力")
            return {"total": 0, "success": 0, "failed": 0, "message": "无新磁力需要推送"}

        quota_info = self.check_115_quota()
        if not quota_info.get("allow_push"):
            return {"total": len(rows), "success": 0, "failed": len(rows), "message": "115 离线配额已用尽"}

        remaining_quota = quota_info.get("remaining", 0)
        if len(rows) > remaining_quota:
            rows = rows[:remaining_quota]

        items = []
        for r in rows:
            movie_info = {'code': r[0], 'title': r[1], 'actors': r[2], 'tags': r[3]}
            wp_path = custom_wp_path or self.generate_auto_path(movie_info, magnet_type)
            items.append({'code': r[0], 'magnet_url': r[4], 'wp_path': wp_path})

        path_groups = {}
        for item in items:
            p = item['wp_path']
            if p not in path_groups: path_groups[p] = []
            path_groups[p].append(item)

        batch_size = config.PUSH_BATCH_SIZE
        total_pushed = 0
        failed_count = 0

        for path, item_list in path_groups.items():
            for i in range(0, len(item_list), batch_size):
                batch = item_list[i : i + batch_size]
                urls_payload = "\n".join([it['magnet_url'] for it in batch])
                res = self.push_to_115_gateway(urls=urls_payload, wp_path=path)
                
                if res.get('code') == 0 or res.get('state') is True:
                    for it in batch:
                        self.record_push_history(it['code'], magnet_type, it['magnet_url'], path)
                        total_pushed += 1
                else:
                    failed_count += len(batch)

                if i + batch_size < len(item_list):
                    time.sleep(random.uniform(config.PUSH_INTERVAL_MIN, config.PUSH_INTERVAL_MAX))

        return {
            "total": len(items),
            "success": total_pushed,
            "failed": failed_count,
            "message": f"推送完成：成功 {total_pushed} 条，失败 {failed_count} 条"
        }


    def sync_115_offline_status(self) -> int:
        try:
            endpoint = f"{config.GATEWAY_115_URL.rstrip('/')}/api/115/offline/tasks"
            self.safe_log("🔄 [115 Sync] 正在单次请求拉取 115 网关全量离线任务 (不带 URL Query)...")
            
            remote_tasks = []
            try:
                resp = self.session.get(endpoint, headers={"X-API-KEY": config.GATEWAY_115_API_KEY}, timeout=30)
                if resp.status_code == 200:
                    res_json = resp.json()
                    raw_data = res_json.get("data")
                    if isinstance(raw_data, list):
                        remote_tasks = raw_data
                    elif isinstance(raw_data, dict):
                        remote_tasks = raw_data.get("tasks") or raw_data.get("list") or raw_data.get("items") or []
            except Exception as req_err:
                self.safe_log(f"⚠️ [115 Sync] 无 Query 请求遇到异常: {req_err}，准备降级为 page=1 重试...", "warning")

            if not remote_tasks:
                try:
                    resp2 = self.session.get(f"{endpoint}?page=1", headers={"X-API-KEY": config.GATEWAY_115_API_KEY}, timeout=20)
                    if resp2.status_code == 200:
                        raw_data2 = resp2.json().get("data")
                        if isinstance(raw_data2, list):
                            remote_tasks = raw_data2
                        elif isinstance(raw_data2, dict):
                            remote_tasks = raw_data2.get("tasks") or raw_data2.get("list") or []
                except Exception:
                    pass

            self.safe_log(f"📊 [115 Sync] 成功获取到 115 网关 {len(remote_tasks)} 条远端全量离线任务")
            
            hash_map = {}
            for t in remote_tasks:
                h = t.get('info_hash') or t.get('hash')
                if h:
                    hash_map[str(h).strip().lower()] = t.get('status', 0)
            
            conn = self._get_db_conn()
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, code, info_hash, status, magnet_url FROM push_history")
            all_rows = cursor.fetchall()
            
            updated_count = 0
            for p_id, code, raw_info_hash, old_status, magnet_url in all_rows:
                info_hash_clean = str(raw_info_hash).strip().lower() if raw_info_hash else ""
                
                # 如果数据库没有存 info_hash，从 magnet_url 提取 BTIH
                if not info_hash_clean and magnet_url:
                    match = re.search(r'btih:([a-fA-F0-9]{40}|[a-zA-Z2-7]{32})', str(magnet_url), re.IGNORECASE)
                    if match:
                        info_hash_clean = match.group(1).lower()

                if info_hash_clean in hash_map:
                    new_status = hash_map[info_hash_clean]
                    if new_status != old_status or not raw_info_hash:
                        cursor.execute("UPDATE push_history SET status = ?, info_hash = ? WHERE id = ?", (new_status, info_hash_clean, p_id))
                        status_msg_map = {-1: "离线失败 ❌", 0: "分配中 ⏳", 1: "下载中 📥", 2: "离线成功 🎉"}
                        status_str = status_msg_map.get(new_status, f"状态({new_status})")
                        self.safe_log(f"🔄 [115 Sync] 番号 [{code}] 状态对齐: {old_status} -> {new_status} ({status_str})")
                        updated_count += 1

            conn.commit()
            conn.close()
            self.safe_log(f"✅ [115 Sync] 任务状态比对对齐完成，更新了 {updated_count} 条离线记录")
            return updated_count

        except Exception as e:
            logger.error(f"❌ [115 Sync] 离线任务状态同步比对异常: {e}")
            return 0

    def check_115_quota(self) -> dict:
        """获取 115 离线配额并计算剩余额度"""
        url = f"{config.GATEWAY_115_URL}/api/115/user/quota"
        headers = {"X-API-KEY": config.GATEWAY_115_API_KEY}

        try:
            resp = self.session.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                res_json = resp.json()
                if res_json.get("code") == 0:
                    data = res_json.get("data", {})
                    count = data.get("count") or data.get("limit", 0)
                    used = data.get("used", 0)
                    remaining = max(0, count - used)

                    logger.info(f"📊 [115 Quota] 配额 -> 总量: {count}, 已用: {used}, 剩余可用: {remaining}")
                    return {
                        "count": count,
                        "used": used,
                        "remaining": remaining,
                        "allow_push": remaining > 0
                    }
            logger.error(f"❌ [115 Quota] 获取配额失败: HTTP {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"💥 [115 Quota] 请求异常: {str(e)}")

        return {"count": 0, "used": 0, "remaining": 0, "allow_push": False}

    def check_115_quota(self) -> dict:
            """
            请求 115 网关 API 获取当前账号离线下载配额信息
            """
            url = f"{config.GATEWAY_115_URL}/api/115/user/quota"
            headers = {"X-API-KEY": config.GATEWAY_115_API_KEY}

            try:
                resp = self.session.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    res_json = resp.json()
                    if res_json.get("code") == 0:
                        data = res_json.get("data", {})
                        # 兼容 limit 或 count 字段
                        count = data.get("count") if data.get("count") is not None else data.get("limit", 0)
                        used = data.get("used", 0)
                        remaining = max(0, count - used)

                        logger.info(f"📊 [115 Quota] 离线配额 -> 总量: {count}, 已用: {used}, 剩余可用: {remaining}")
                        return {
                            "count": count,
                            "used": used,
                            "remaining": remaining,
                            "allow_push": remaining > 0
                        }
                logger.error(f"❌ [115 Quota] 获取配额失败: HTTP {resp.status_code} - {resp.text}")
            except Exception as e:
                logger.error(f"💥 [115 Quota] 请求配额接口异常: {str(e)}")

            # 异常兜底，防止崩溃
            return {"count": 0, "used": 0, "remaining": 0, "allow_push": False}