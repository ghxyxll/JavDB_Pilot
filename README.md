# 🎬 JavDB AutoSpider V1.2 - 智能自动化抓取与 115 离线云推送系统

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/FastAPI-1.1.0-emerald.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/Vue-3.x-brightgreen.svg" alt="Vue 3">
  <img src="https://img.shields.io/badge/Vite-6.x-purple.svg" alt="Vite 6">
  <img src="https://img.shields.io/badge/TailwindCSS-v4-38bdf8.svg" alt="TailwindCSS">
  <img src="https://img.shields.io/badge/Docker-Ready-blue?logo=docker" alt="Docker">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License MIT">
</p>

> **JavDB AutoSpider** 是一款面向个人私有化部署的生产级 JavDB 自动化爬虫、数据整理、智能磁力择优及 115 云盘离线自动推送系统。搭配极具现代极简风（Glassmorphism 暗黑流光）的 Vue 3 可视化管理控制台，提供从**影片数据抓取 ➔ 磁力智能升阶 ➔ 订阅演员巡检 ➔ 115 批量离线推送 ➔ CSV 数据导出** 的无人值守全流程解决方案。

---

## ✨ 核心特性

### 🎬 1. 智能爬虫引擎与 6 级风控防护
- **单线程异步 FIFO 队列**：基于 Python `asyncio.Queue` 构建严格排队机制，防止高并发高频抓取导致的 IP 限流风控或 SQLite 锁库异常。
- **6 级防封安全保护**：包含随机 Jitter 抖动延迟、429/503 指数退避重试、Paywall 屏障感知、模拟请求头/Cookie 自动注入、Cancel Guard 优雅中断机制。
- **智能撞库早停（Smart Incremental Skip）**：抓取列表页时自动与本地 SQLite 数据库对比，遇到连续已入库记录时触发智能早停，节省 90% 以上的无用网络请求。

### 🌟 2. 磁力槽位分类与智能升阶（UC > 4K > C > U）
- **多维度磁力提取**：自动识别并分类存储 `magnet_uc`（无码中字/破解）、`magnet_4k`（4K超清）、`magnet_c`（有码中字）、`magnet_u`（无码高清）及普通磁力。
- **非破坏性增量更新**：采用 SQL `COALESCE` 保护算法，二次补全或重新抓取时切不覆盖已存在的稀缺磁力槽位。

### 📦 3. 115 云盘离线自动化与状态对齐
- **批次推送与路径归类**：按演员/路径分批（单批 5 条）自动提交至 115 离线网关，防止触发 115 离线频率风控。
- **离线 Hash 去重与状态同步**：自动提取 Magnet Hash 校验，定时拉取 115 远端真实离线下载状态进行双向对比与实时状态对齐。
- **离线解析 180s 缓冲倒计时**：推送完成后自动进行 3 分钟解析等待缓冲，避免刚提交即同步导致的“状态未更新”延迟。
- **配额 5 分钟智能缓存**：配额查询使用 300 秒内存缓存，避免频繁按 `F5` 刷新页面打扰 115 远端网关。

### ⏰ 4. 无人值守 Cron 定时任务调度
- **APScheduler 后台调度**：支持针对**订阅演员批量巡检**、**个人/收藏清单增量更新**、**115 离线定时推送** 配置灵活的 Cron 表达式。
- **持久化恢复**：定时任务自动写盘保存（`scheduled_jobs.json`），服务重启后自动缝合恢复运行。

### 🛡️ 5. 安全认证与权限拦截 (`user.db`)
- **PBKDF2-HMAC-SHA256 加密**：管理员密码结合 16 字节随机盐值 (Salt) 经过 100,000 次深度哈希存储在 `backend/user.db` 中。
- **首次部署引导与会话拦截**：无账号时自动引导创建管理员；登录后颁发 64 位加密 Token，未授权请求全量阻断。
- **命令行救急工具**：内置零依赖 `python reset_password.py` 脚本，防止管理员忘记密码。
- **生产安全防泄漏**：通过 `ENABLE_DOCS=false` 彻底屏蔽 Swagger `/docs` 接口文档。

### 📊 6. 数据导出与全量库管理
- **标准 CSV 导出**：支持按关键词、标签（如 `4K` / `UC` / `已推送`）条件导出全量电影 CSV（带 `UTF-8-SIG` BOM 字节，完全兼容 Excel 直接打开无乱码）。
- **海报墙与详情弹窗**：支持视图无缝切换、多维度搜索、高清海报预检与一键离线推送。

---

## 🏗️ 系统架构图

```
+-------------------------------------------------------------------------+
|                        Vue 3 SPA Web Frontend                           |
|      (Dashboard / Media Library / Actors / Lists / Scheduler / Transfer)|
+------------------------------------+------------------------------------+
                                     | Axios (Bearer Token)
                                     v
+-------------------------------------------------------------------------+
|                       FastAPI REST API Service                          |
|  - Auth Middleware (user.db)          - Task Queue Worker (FIFO)        |
|  - System & Config API                - APScheduler Cron Engine         |
+------------------+-----------------------------------+------------------+
                   |                                   |
                   v                                   v
+----------------------------------+   +----------------------------------+
|        SQLite Databases          |   |        External Services         |
|  - javdb_spider.db (Movies/Pushes)|   |  - JavDB Source Site             |
|  - user.db (Users/Sessions)      |   |  - 115 Offline Gateway API       |
+----------------------------------+   +----------------------------------+
```

---

## 🚀 快速开始

### 方式一：Docker Compose 一键部署（推荐 🌟）

项目已针对 Docker 进行多阶段（Multi-stage）自动打包优化，前端编译与 Python 环境均集成于单个容器中。

1. **克隆项目到本地**：
   ```bash
   git clone https://github.com/your-username/JAVDB_AutoSpider.git
   cd JAVDB_AutoSpider
   ```

2. **启动 Docker 容器**：
   ```bash
   docker compose up -d
   ```

3. **访问系统**：
   打开浏览器访问 `http://<服务器IP>:8000/`，系统会自动重定向至 `http://<服务器IP>:8000/ui/`：
   - 首次打开将自动展示 **“系统首次部署 - 创建管理员账号”** 页面，设置用户名与密码后即可开始使用。

4. **停止与日志查看**：
   ```bash
   # 查看实时运行日志
   docker compose logs -f
   
   # 停止容器
   docker compose down
   ```

---

### 方式二：本地开发部署 (Python + Node.js)

如需进行二次开发或本地调试，可分别启动后端与前端服务。

#### 1. 后端服务启动 (Python 3.11+)

```bash
# 进入后端目录
cd backend

# 创建并激活虚拟环境 (可选)
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动 FastAPI 后端服务
python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload
```

#### 2. 前端服务启动 (Node.js 20+)

```bash
# 进入前端目录
cd frontend

# 安装 npm 依赖
npm install

# 启动 Vite 开发服务器
npm run dev

# 编译生成生产包 (输出至 dist 目录)
npm run build
```

访问 `http://localhost:3000/` 即可启动带热重载的开发界面。

---

## 🔐 忘记密码与安全救急

由于系统运行于私有化环境中，如果管理员忘记了登录密码，**无需重装系统**，可通过终端运行交互式脚本重置：

在项目根目录或 `backend` 目录下执行：
```bash
python reset_password.py
```

终端将弹出命令行控制菜单：
```text
=======================================================
 [Key] JavDB AutoSpider 管理员密码重置与安全救急工具
=======================================================

请选择您需要的救急操作:
  [1] 直接修改已有管理员账号的密码
  [2] 重置清空数据库用户表 (恢复为网页首次部署初始化状态)
  [3] 退出

[>] 请输入选项编号 (1/2/3):
```
根据提示输入 `1` 即可输入新密码完成秒级重置。

---

## ⚙️ 配置文件参数说明 (`config.ini`)

系统参数保存在 `config/config.ini` 中，也可以直接在前端网页的【系统设置】中在线修改：

| 配置项 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `BASE_URL` | `https://javdb.com` | JavDB 站点镜像主页地址 |
| `DEFAULT_DB_PATH` | `data/javdb_spider.db` | 主业务 SQLite 数据库存储路径 |
| `DEFAULT_COOKIES` | `""` | 用于绕过防爬过盾与拉取订阅的 JavDB 登录 Cookie |
| `REQUEST_DELAY_MIN` | `1.5` | 抓取请求随机等待延迟最小值（秒） |
| `REQUEST_DELAY_MAX` | `3.5` | 抓取请求随机等待延迟最大值（秒） |
| `MAX_RETRIES` | `3` | 触发 HTTP 429/503 时的最大重试次数 |
| `GATEWAY_115_URL` | `http://127.0.0.1:5000` | 115 离线下载网关 API 地址 |
| `GATEWAY_115_API_KEY` | `""` | 115 网关鉴权 API Key |
| `PUSH_BATCH_SIZE` | `5` | 115 推送单批次最大磁力链接数量 |
| `ENABLE_SCHEDULER` | `True` | 是否在启动时开启 APScheduler 定时任务引擎 |

---

## 📂 项目目录结构

```text
JAVDB_AutoSpider_V1.2/
├── backend/                  # Python FastAPI 后端服务
│   ├── javdb_scraper.py      # 爬虫核心引擎、数据解析、SQLite CRUD 与 115 推送
│   ├── server.py             # FastAPI App 入口、REST API 路由、Auth 鉴权
│   ├── config_manager.py     # 动态 config.ini 读写配置管理器
│   ├── logger.py             # 规范日志切片与控制台格式化输出
│   ├── reset_password.py     # 命令行密码重置与安全救急工具
│   └── requirements.txt      # 后端依赖包清单
├── frontend/                 # Vue 3 + Vite + TailwindCSS 前端工程
│   ├── src/
│   │   ├── components/       # 通用组件 (HeaderNav, SidebarNav, AuthModal, PushTaskModal 等)
│   │   ├── views/            # 页面视图 (Dashboard, MediaLibrary, Actors, UserLists, Scheduler, Transfer)
│   │   ├── api.js            # Axios 封装与 Auth Token 拦截器
│   │   ├── App.vue           # 根组件、鉴权拦截与 page-fade-slide 页面过渡
│   │   └── style.css         # Tailwind 全局样式与自定义动画 keyframes
│   └── package.json          # 前端依赖配置
├── config/                   # 宿主机配置持久化映射目录 (config.ini)
├── data/                     # 宿主机 SQLite 数据库与持久化数据映射目录
├── docker-compose.yml        # Docker Compose 一键编排文件
├── Dockerfile                # 多阶段自动构建 Dockerfile
├── reset_password.py         # 根目录救急重置快捷入口
└── README.md                 # 项目详细中文说明文档
```

---

## 📄 开源许可证与免责声明

- 本项目采用 **MIT License** 开源许可证。
- **免责声明**：本项目仅供个人技术研究、代码学习及个人媒体库自动化管理使用。请使用者严格遵守当地法律法规及目标网站的使用条款，切勿用于商业用途或高频恶意爬取。作者不对任何因不当使用而引发的纠纷承担责任。
