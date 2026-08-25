<template>
  <div class="space-y-6 animate-fade-in">
    
    <!-- Top Modern Glassmorphism Header -->
    <div class="bg-gradient-to-r from-slate-900/95 via-indigo-950/40 to-slate-900/95 backdrop-blur-xl p-6 rounded-3xl border border-slate-800/80 shadow-2xl flex flex-col md:flex-row md:items-center justify-between gap-5 relative overflow-hidden">
      <!-- Ambient Backlight -->
      <div class="absolute -top-16 -left-16 w-56 h-56 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>
      <div class="absolute -bottom-16 -right-16 w-56 h-56 bg-purple-500/10 rounded-full blur-3xl pointer-events-none"></div>

      <div class="relative z-10 space-y-1.5">
        <h2 class="text-xl font-extrabold text-slate-100 flex items-center space-x-3 tracking-tight">
          <div class="p-2.5 rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shadow-inner">
            <Sliders class="w-5 h-5" />
          </div>
          <span>系统参数配置</span>
        </h2>
      </div>

      <div class="relative z-10 flex items-center space-x-3 shrink-0">
        <button 
          @click="fetchConfig" 
          class="p-2.5 bg-slate-800 hover:bg-slate-700 active:scale-95 text-slate-300 rounded-2xl border border-slate-700/60 transition"
          title="重载配置"
        >
          <RefreshCw :class="['w-4 h-4', loading ? 'animate-spin' : '']" />
        </button>

        <button 
          @click="saveConfig" 
          :disabled="saving"
          class="px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 active:scale-95 text-white font-extrabold rounded-2xl text-xs shadow-lg shadow-indigo-600/25 transition flex items-center space-x-2 disabled:opacity-50"
        >
          <Save class="w-4 h-4" />
          <span>{{ saving ? '正在写回 config.ini...' : '保存全量配置并持久化' }}</span>
        </button>
      </div>
    </div>

    <!-- Category Section Tabs -->
    <div class="flex flex-wrap gap-2 bg-slate-900/90 backdrop-blur-xl p-2 rounded-2xl border border-slate-800/90 text-xs font-semibold shadow-inner">
      <button 
        v-for="tab in categoryTabs" 
        :key="tab.id"
        @click="activeCategory = tab.id"
        :class="[
          'px-4 py-2 rounded-xl transition-all duration-200 flex items-center space-x-1.5',
          activeCategory === tab.id 
            ? 'bg-indigo-600 text-white font-bold shadow-lg shadow-indigo-600/30' 
            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
        ]"
      >
        <span>{{ tab.label }}</span>
      </button>
    </div>

    <!-- Category Panels -->

    <!-- Section 1: [base] 基础参数 -->
    <div v-show="activeCategory === 'all' || activeCategory === 'base'" class="bg-slate-900/90 backdrop-blur-xl p-6 rounded-3xl border border-slate-800/90 shadow-2xl space-y-4">
      <h3 class="text-sm font-extrabold text-indigo-400 flex items-center space-x-2 border-b border-slate-800/80 pb-3">
        <span>🌐 1. 基础配置 [base]</span>
      </h3>

      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 text-xs">
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">JavDB 站点主页 (base_url)</label>
          <input v-model="form.BASE_URL" type="text" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">API 监听地址 (api_host)</label>
          <input v-model="form.API_HOST" type="text" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">API 监听端口 (api_port)</label>
          <input v-model.number="form.API_PORT" type="number" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">默认 SQLite 数据库路径 (default_db_path)</label>
          <input v-model="form.DEFAULT_DB_PATH" type="text" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">安全二次验证密码 (security_clear_key)</label>
          <input v-model="form.SECURITY_CLEAR_KEY" type="password" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div class="xl:col-span-3 md:col-span-2">
          <label class="block text-slate-300 mb-1.5 font-bold">默认 User-Agent 伪装标头 (default_user_agent)</label>
          <input v-model="form.DEFAULT_USER_AGENT" type="text" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 font-mono text-[11px] focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div class="xl:col-span-3 md:col-span-2">
          <label class="block text-slate-300 mb-1.5 font-bold">全局默认 Cookies 保持 (default_cookies)</label>
          <textarea v-model="form.DEFAULT_COOKIES" rows="2" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 font-mono text-[11px] focus:border-indigo-500 outline-none shadow-inner"></textarea>
        </div>
      </div>

      <!-- Change Admin Profile Sub-Card -->
      <div class="mt-4 pt-4 border-t border-slate-800/80">
        <h4 class="text-xs font-bold text-slate-200 mb-3 flex items-center space-x-2">
          <span class="text-indigo-400">👤 修改管理员账号与密码</span>
        </h4>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          <div>
            <label class="block text-slate-400 mb-1 font-medium">当前旧密码 <span class="text-rose-400">*</span> (验证身份)</label>
            <input v-model="oldPassword" type="password" placeholder="输入当前旧密码" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:border-indigo-500 outline-none" />
          </div>
          <div>
            <label class="block text-slate-400 mb-1 font-medium">新用户名 (可选)</label>
            <input v-model="newUsername" type="text" placeholder="留空则保持当前用户名" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:border-indigo-500 outline-none" />
          </div>
          <div>
            <label class="block text-slate-400 mb-1 font-medium">新密码 (可选，至少4位)</label>
            <input v-model="newPassword" type="password" placeholder="留空则保持原密码" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:border-indigo-500 outline-none" />
          </div>
          <div>
            <label class="block text-slate-400 mb-1 font-medium">确认新密码</label>
            <input v-model="confirmPassword" type="password" placeholder="再次输入新密码" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-200 focus:border-indigo-500 outline-none" />
          </div>
        </div>
        <div class="mt-3 flex justify-end">
          <button 
            @click="handleUpdateProfile" 
            :disabled="changingPassword || !oldPassword || (!newUsername && !newPassword)"
            class="px-4 py-2 bg-indigo-600/80 hover:bg-indigo-600 disabled:opacity-50 text-white font-bold text-xs rounded-xl transition shadow-md cursor-pointer flex items-center space-x-1.5"
          >
            <Key class="w-3.5 h-3.5" />
            <span>{{ changingPassword ? '正在更新...' : '确认更新管理员账号信息' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Section 2: [network] 网络与代理 -->
    <div v-show="activeCategory === 'all' || activeCategory === 'network'" class="bg-slate-900/90 backdrop-blur-xl p-6 rounded-3xl border border-slate-800/90 shadow-2xl space-y-4">
      <h3 class="text-sm font-extrabold text-indigo-400 flex items-center space-x-2 border-b border-slate-800/80 pb-3">
        <span>📡 2. 网络与防风控代理 [network]</span>
      </h3>

      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 text-xs">
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">抓取随机延迟最小值 (request_delay_min)</label>
          <input v-model.number="form.REQUEST_DELAY_MIN" type="number" step="0.5" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">抓取随机延迟最大值 (request_delay_max)</label>
          <input v-model.number="form.REQUEST_DELAY_MAX" type="number" step="0.5" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">最大重试次数 (max_retries)</label>
          <input v-model.number="form.MAX_RETRIES" type="number" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">触发限流退避等待时间 (retry_wait_base)</label>
          <input v-model.number="form.RETRY_WAIT_BASE" type="number" step="1" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">请求超时秒数 (request_timeout)</label>
          <input v-model.number="form.REQUEST_TIMEOUT" type="number" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">HTTP 代理 (http_proxy)</label>
          <input v-model="form.HTTP_PROXY" type="text" placeholder="http://127.0.0.1:7890" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">HTTPS 代理 (https_proxy)</label>
          <input v-model="form.HTTPS_PROXY" type="text" placeholder="http://127.0.0.1:7890" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
      </div>
    </div>

    <!-- Section 3: [auth] 模拟登录与验证码 -->
    <div v-show="activeCategory === 'all' || activeCategory === 'auth'" class="bg-slate-900/90 backdrop-blur-xl p-6 rounded-3xl border border-slate-800/90 shadow-2xl space-y-4">
      <h3 class="text-sm font-extrabold text-indigo-400 flex items-center space-x-2 border-b border-slate-800/80 pb-3">
        <span>🔐 3. 模拟登录与会话 [auth]</span>
      </h3>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">临时验证码会话过期分钟 (auth_session_ttl)</label>
          <input v-model.number="form.AUTH_SESSION_TTL" type="number" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">登录 HTTP 超时秒数 (auth_http_timeout)</label>
          <input v-model.number="form.AUTH_HTTP_TIMEOUT" type="number" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
      </div>
    </div>

    <!-- Section 4: [queue] 任务队列与调度 -->
    <div v-show="activeCategory === 'all' || activeCategory === 'queue'" class="bg-slate-900/90 backdrop-blur-xl p-6 rounded-3xl border border-slate-800/90 shadow-2xl space-y-4">
      <h3 class="text-sm font-extrabold text-indigo-400 flex items-center space-x-2 border-b border-slate-800/80 pb-3">
        <span>⚡ 4. 智能增量、任务队列与调度 [queue]</span>
      </h3>

      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 text-xs">
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">撞库终止阈值 (incremental_threshold)</label>
          <input v-model.number="form.INCREMENTAL_THRESHOLD" type="number" placeholder="默认 5" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
          <span class="text-[10px] text-slate-500 mt-1 block">在单页遇到多少部历史完整影片时终止翻页 (默认 5 条)</span>
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">老片判定天数 (old_movie_days)</label>
          <input v-model.number="form.OLD_MOVIE_DAYS" type="number" placeholder="默认 30" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
          <span class="text-[10px] text-slate-500 mt-1 block">发行超过多少天的影片视为老片，不再重复死守无码中字 (默认 30 天)</span>
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">并行消费者线程数 (queue_worker_concurrency)</label>
          <input v-model.number="form.QUEUE_WORKER_CONCURRENCY" type="number" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">最大排队容量 (max_queue_size)</label>
          <input v-model.number="form.MAX_QUEUE_SIZE" type="number" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">Cron 定时触发器抓取最大页数 (default_cron_max_pages)</label>
          <input v-model.number="form.DEFAULT_CRON_MAX_PAGES" type="number" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">是否开启后台 APScheduler 引擎 (enable_scheduler)</label>
          <select v-model="form.ENABLE_SCHEDULER" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner">
            <option :value="true">True (开启)</option>
            <option :value="false">False (关闭)</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Section 5: [database] SQLite 存储 -->
    <div v-show="activeCategory === 'all' || activeCategory === 'database'" class="bg-slate-900/90 backdrop-blur-xl p-6 rounded-3xl border border-slate-800/90 shadow-2xl space-y-4">
      <h3 class="text-sm font-extrabold text-indigo-400 flex items-center space-x-2 border-b border-slate-800/80 pb-3">
        <span>💾 5. SQLite 数据库性能配置 [database]</span>
      </h3>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">数据库繁忙等待超时秒数 (db_busy_timeout)</label>
          <input v-model.number="form.DB_BUSY_TIMEOUT" type="number" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">是否启用 SQLite WAL 日志并发写入模式 (enable_wal_mode)</label>
          <select v-model="form.ENABLE_WAL_MODE" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner">
            <option :value="true">True (启用 WAL 高并发)</option>
            <option :value="false">False (普通模式)</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Section 6: [parser] 正则解析表达式 -->
    <div v-show="activeCategory === 'all' || activeCategory === 'parser'" class="bg-slate-900/90 backdrop-blur-xl p-6 rounded-3xl border border-slate-800/90 shadow-2xl space-y-4">
      <h3 class="text-sm font-extrabold text-indigo-400 flex items-center space-x-2 border-b border-slate-800/80 pb-3">
        <span>🔍 6. 标签与画质正则解析规则 [parser]</span>
      </h3>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">4K 超清画质正则 (regex_4k)</label>
          <input v-model="form.REGEX_4K" type="text" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">无码中字标签正则 (regex_tag_uc)</label>
          <input v-model="form.REGEX_TAG_UC" type="text" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">有码中字标签正则 (regex_tag_c)</label>
          <input v-model="form.REGEX_TAG_C" type="text" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">无码高清标签正则 (regex_tag_u)</label>
          <input v-model="form.REGEX_TAG_U" type="text" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">通用字幕关键词正则 (regex_subtitle)</label>
          <input v-model="form.REGEX_SUBTITLE" type="text" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">无码关键词正则 (regex_uncensored)</label>
          <input v-model="form.REGEX_UNCENSORED" type="text" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
      </div>
    </div>

    <!-- Section 7: [transfer_115] 115 离线 API 参数 -->
    <div v-show="activeCategory === 'all' || activeCategory === 'transfer'" class="bg-slate-900/90 backdrop-blur-xl p-6 rounded-3xl border border-slate-800/90 shadow-2xl space-y-4">
      <h3 class="text-sm font-extrabold text-indigo-400 flex items-center space-x-2 border-b border-slate-800/80 pb-3">
        <span>☁️ 7. 115 云盘 API 网关参数 [transfer_115]</span>
      </h3>

      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 text-xs">
        <div class="xl:col-span-2 md:col-span-2">
          <label class="block text-slate-300 mb-1.5 font-bold">115 API 网关接口根地址 (gateway_115_url)</label>
          <input v-model="form.GATEWAY_115_URL" type="text" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 font-mono focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">API 访问密钥 (gateway_115_api_key)</label>
          <input v-model="form.GATEWAY_115_API_KEY" type="password" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 font-mono focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">单次防风控批处理推送上限 (push_batch_size)</label>
          <input v-model.number="form.PUSH_BATCH_SIZE" type="number" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">分批随机防风控延时最小秒数 (push_interval_min)</label>
          <input v-model.number="form.PUSH_INTERVAL_MIN" type="number" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
        <div>
          <label class="block text-slate-300 mb-1.5 font-bold">分批随机防风控延时最大秒数 (push_interval_max)</label>
          <input v-model.number="form.PUSH_INTERVAL_MAX" type="number" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none shadow-inner" />
        </div>
      </div>
    </div>

    <!-- Section 8: Live Terminal Log Stream -->
    <div class="bg-slate-900/90 backdrop-blur-xl p-6 rounded-3xl border border-slate-800/90 shadow-2xl space-y-4">
      <div class="flex justify-between items-center border-b border-slate-800/80 pb-3">
        <h3 class="text-sm font-extrabold text-slate-100 flex items-center space-x-2">
          <Terminal class="w-4 h-4 text-indigo-400" />
          <span>后台运行日志实时流 (Real-time Live Log)</span>
        </h3>

        <div class="flex items-center space-x-3 text-xs">
          <select v-model.number="logLines" @change="fetchLogs" class="bg-slate-950 border border-slate-800 text-slate-300 rounded-xl px-3 py-1 font-mono focus:border-indigo-500 outline-none">
            <option :value="100">显示最近 100 行</option>
            <option :value="300">显示最近 300 行</option>
            <option :value="500">显示最近 500 行</option>
          </select>

          <button @click="fetchLogs" class="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-indigo-300 rounded-xl font-bold transition border border-slate-700/60">
            刷新日志
          </button>
          
          <button @click="clearLogs" class="px-3 py-1 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded-xl font-bold transition">
            清空日志
          </button>
        </div>
      </div>

      <div 
        ref="logTerminal" 
        class="bg-slate-950 p-4 rounded-2xl border border-slate-800/80 font-mono text-[11px] text-slate-300 leading-relaxed max-h-96 overflow-y-auto whitespace-pre-wrap shadow-inner"
      >
        {{ logContent || '正在拉取实时运行日志...' }}
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue';
import { Sliders, RefreshCw, Save, Terminal, Key } from '@lucide/vue';
import api, { formatApiError, setAuthToken } from '../api';

const loading = ref(false);
const saving = ref(false);
const activeCategory = ref('all');
const logContent = ref('');
const logLines = ref(300);
const logTerminal = ref(null);

// Admin Profile Change State
const oldPassword = ref('');
const newUsername = ref('');
const newPassword = ref('');
const confirmPassword = ref('');
const changingPassword = ref(false);

async function handleUpdateProfile() {
  if (!oldPassword.value) {
    window.$toast?.('请输入当前旧密码进行身份验证！', 'warning');
    return;
  }
  if (!newUsername.value && !newPassword.value) {
    window.$toast?.('请至少输入新用户名或新密码！', 'warning');
    return;
  }
  if (newUsername.value && newUsername.value.trim().length < 2) {
    window.$toast?.('新用户名长度不能少于 2 个字符！', 'warning');
    return;
  }
  if (newPassword.value) {
    if (newPassword.value.length < 4) {
      window.$toast?.('新密码长度不能少于 4 个字符！', 'warning');
      return;
    }
    if (newPassword.value !== confirmPassword.value) {
      window.$toast?.('两次输入的新密码不一致，请重试！', 'warning');
      return;
    }
  }

  changingPassword.value = true;
  try {
    const payload = {
      old_password: oldPassword.value,
      new_username: newUsername.value ? newUsername.value.trim() : null,
      new_password: newPassword.value ? newPassword.value.trim() : null
    };

    const res = await api.post('/system/update-profile', payload);
    if (res.data?.code === 200 && res.data?.data) {
      if (res.data.data.token) {
        setAuthToken(res.data.data.token);
      }
      if (res.data.data.username) {
        localStorage.setItem('sys_username', res.data.data.username);
      }
      window.$toast?.(res.data.message || '账号信息已成功更新！', 'success', '更新成功');
      oldPassword.value = '';
      newUsername.value = '';
      newPassword.value = '';
      confirmPassword.value = '';
      // Refresh page to update sidebar username display
      setTimeout(() => {
        window.location.reload();
      }, 800);
    }
  } catch (err) {
    window.$toast?.('更新账号失败: ' + formatApiError(err), 'error', '验证错误');
  } finally {
    changingPassword.value = false;
  }
}

const categoryTabs = [
  { id: 'all', label: '全部参数' },
  { id: 'base', label: '🌐 基础配置 [base]' },
  { id: 'network', label: '📡 网络与代理 [network]' },
  { id: 'auth', label: '🔐 模拟登录 [auth]' },
  { id: 'queue', label: '⚡ 任务队列 [queue]' },
  { id: 'database', label: '💾 SQLite 存储 [database]' },
  { id: 'parser', label: '🔍 正则解析 [parser]' },
  { id: 'transfer', label: '☁️ 115 API 网关 [transfer]' }
];

const form = ref({
  BASE_URL: 'https://javdb.com',
  API_HOST: '127.0.0.1',
  API_PORT: 8000,
  DEFAULT_DB_PATH: 'javdb_movies.db',
  SECURITY_CLEAR_KEY: 'DANGER_CONFIRM_DELETE_ALL',
  DEFAULT_USER_AGENT: 'Mozilla/5.0...',
  DEFAULT_COOKIES: '',

  REQUEST_DELAY_MIN: 1.5,
  REQUEST_DELAY_MAX: 3.5,
  MAX_RETRIES: 3,
  RETRY_WAIT_BASE: 5.0,
  REQUEST_TIMEOUT: 20,
  HTTP_PROXY: '',
  HTTPS_PROXY: '',

  AUTH_SESSION_TTL: 10,
  AUTH_HTTP_TIMEOUT: 15,

  QUEUE_WORKER_CONCURRENCY: 1,
  MAX_QUEUE_SIZE: 500,
  ENABLE_SCHEDULER: true,
  DEFAULT_CRON_MAX_PAGES: 3,
  INCREMENTAL_THRESHOLD: 5,
  OLD_MOVIE_DAYS: 30,

  DB_BUSY_TIMEOUT: 15,
  ENABLE_WAL_MODE: true,

  REGEX_4K: '4[kK]|2160[pP]',
  REGEX_TAG_UC: '無碼.*中字|中字.*無碼|UC',
  REGEX_TAG_C: '有碼.*中字|中字.*有碼|\\bC\\b',
  REGEX_TAG_U: '無碼|\\bU\\b',
  REGEX_SUBTITLE: '中字|字幕|字',
  REGEX_UNCENSORED: '無碼|素人',

  GATEWAY_115_URL: 'http://127.0.0.1:8000/api/v1/transfer',
  GATEWAY_115_API_KEY: 'secret_115_key',
  PUSH_BATCH_SIZE: 50,
  PUSH_INTERVAL_MIN: 2.0,
  PUSH_INTERVAL_MAX: 5.0,
});

onMounted(() => {
  fetchConfig();
  fetchLogs();
});

async function fetchConfig() {
  loading.value = true;
  try {
    const res = await api.get('/config/all');
    if (res.data?.code === 200 && res.data?.data) {
      const d = res.data.data;
      if (d.base) {
        form.value.BASE_URL = d.base.base_url || form.value.BASE_URL;
        form.value.API_HOST = d.base.api_host || form.value.API_HOST;
        form.value.API_PORT = d.base.api_port || form.value.API_PORT;
        form.value.DEFAULT_DB_PATH = d.base.default_db_path || form.value.DEFAULT_DB_PATH;
        form.value.SECURITY_CLEAR_KEY = d.base.security_clear_key || form.value.SECURITY_CLEAR_KEY;
        form.value.DEFAULT_USER_AGENT = d.base.default_user_agent || form.value.DEFAULT_USER_AGENT;
        form.value.DEFAULT_COOKIES = d.base.default_cookies || '';
      }
      if (d.network) {
        form.value.REQUEST_DELAY_MIN = d.network.request_delay_min;
        form.value.REQUEST_DELAY_MAX = d.network.request_delay_max;
        form.value.MAX_RETRIES = d.network.max_retries;
        form.value.RETRY_WAIT_BASE = d.network.retry_wait_base;
        form.value.REQUEST_TIMEOUT = d.network.request_timeout;
        form.value.HTTP_PROXY = d.network.http_proxy || '';
        form.value.HTTPS_PROXY = d.network.https_proxy || '';
      }
      if (d.auth) {
        form.value.AUTH_SESSION_TTL = d.auth.auth_session_ttl;
        form.value.AUTH_HTTP_TIMEOUT = d.auth.auth_http_timeout;
      }
      if (d.queue) {
        form.value.QUEUE_WORKER_CONCURRENCY = d.queue.queue_worker_concurrency;
        form.value.MAX_QUEUE_SIZE = d.queue.max_queue_size;
        form.value.ENABLE_SCHEDULER = d.queue.enable_scheduler;
        form.value.DEFAULT_CRON_MAX_PAGES = d.queue.default_cron_max_pages;
        form.value.INCREMENTAL_THRESHOLD = d.queue.incremental_threshold ?? form.value.INCREMENTAL_THRESHOLD;
        form.value.OLD_MOVIE_DAYS = d.queue.old_movie_days ?? form.value.OLD_MOVIE_DAYS;
      }
      if (d.database) {
        form.value.DB_BUSY_TIMEOUT = d.database.db_busy_timeout;
        form.value.ENABLE_WAL_MODE = d.database.enable_wal_mode;
      }
      if (d.parser) {
        form.value.REGEX_4K = d.parser.regex_4k || form.value.REGEX_4K;
        form.value.REGEX_TAG_UC = d.parser.regex_tag_uc || form.value.REGEX_TAG_UC;
        form.value.REGEX_TAG_C = d.parser.regex_tag_c || form.value.REGEX_TAG_C;
        form.value.REGEX_TAG_U = d.parser.regex_tag_u || form.value.REGEX_TAG_U;
        form.value.REGEX_SUBTITLE = d.parser.regex_subtitle || form.value.REGEX_SUBTITLE;
        form.value.REGEX_UNCENSORED = d.parser.regex_uncensored || form.value.REGEX_UNCENSORED;
      }
      if (d.transfer_115) {
        form.value.GATEWAY_115_URL = d.transfer_115.gateway_115_url;
        form.value.GATEWAY_115_API_KEY = d.transfer_115.gateway_115_api_key;
        form.value.PUSH_BATCH_SIZE = d.transfer_115.push_batch_size;
        form.value.PUSH_INTERVAL_MIN = d.transfer_115.push_interval_min;
        form.value.PUSH_INTERVAL_MAX = d.transfer_115.push_interval_max;
      }

      // 兼容直接从扁平 Key 兜底读取
      if (d.INCREMENTAL_THRESHOLD !== undefined) form.value.INCREMENTAL_THRESHOLD = d.INCREMENTAL_THRESHOLD;
      if (d.OLD_MOVIE_DAYS !== undefined) form.value.OLD_MOVIE_DAYS = d.OLD_MOVIE_DAYS;
      if (d.REGEX_4K) form.value.REGEX_4K = d.REGEX_4K;
      if (d.REGEX_TAG_UC) form.value.REGEX_TAG_UC = d.REGEX_TAG_UC;
      if (d.REGEX_TAG_C) form.value.REGEX_TAG_C = d.REGEX_TAG_C;
      if (d.REGEX_TAG_U) form.value.REGEX_TAG_U = d.REGEX_TAG_U;
      if (d.REGEX_SUBTITLE) form.value.REGEX_SUBTITLE = d.REGEX_SUBTITLE;
      if (d.REGEX_UNCENSORED) form.value.REGEX_UNCENSORED = d.REGEX_UNCENSORED;
    }
  } catch (err) {
    console.error('Fetch config error', err);
  } finally {
    loading.value = false;
  }
}

async function saveConfig() {
  saving.value = true;
  try {
    const payload = {
      base_url: form.value.BASE_URL,
      api_host: form.value.API_HOST,
      api_port: form.value.API_PORT,
      default_db_path: form.value.DEFAULT_DB_PATH,
      security_clear_key: form.value.SECURITY_CLEAR_KEY,
      default_user_agent: form.value.DEFAULT_USER_AGENT,
      default_cookies: form.value.DEFAULT_COOKIES,

      request_delay_min: form.value.REQUEST_DELAY_MIN,
      request_delay_max: form.value.REQUEST_DELAY_MAX,
      max_retries: form.value.MAX_RETRIES,
      retry_wait_base: form.value.RETRY_WAIT_BASE,
      request_timeout: form.value.REQUEST_TIMEOUT,
      http_proxy: form.value.HTTP_PROXY,
      https_proxy: form.value.HTTPS_PROXY,

      auth_session_ttl: form.value.AUTH_SESSION_TTL,
      auth_http_timeout: form.value.AUTH_HTTP_TIMEOUT,

      queue_worker_concurrency: form.value.QUEUE_WORKER_CONCURRENCY,
      max_queue_size: form.value.MAX_QUEUE_SIZE,
      enable_scheduler: form.value.ENABLE_SCHEDULER,
      default_cron_max_pages: form.value.DEFAULT_CRON_MAX_PAGES,
      incremental_threshold: form.value.INCREMENTAL_THRESHOLD,
      old_movie_days: form.value.OLD_MOVIE_DAYS,

      db_busy_timeout: form.value.DB_BUSY_TIMEOUT,
      enable_wal_mode: form.value.ENABLE_WAL_MODE,

      regex_4k: form.value.REGEX_4K,
      regex_tag_uc: form.value.REGEX_TAG_UC,
      regex_tag_c: form.value.REGEX_TAG_C,
      regex_tag_u: form.value.REGEX_TAG_U,
      regex_subtitle: form.value.REGEX_SUBTITLE,
      regex_uncensored: form.value.REGEX_UNCENSORED,

      gateway_115_url: form.value.GATEWAY_115_URL,
      gateway_115_api_key: form.value.GATEWAY_115_API_KEY,
      push_batch_size: form.value.PUSH_BATCH_SIZE,
      push_interval_min: form.value.PUSH_INTERVAL_MIN,
      push_interval_max: form.value.PUSH_INTERVAL_MAX,
    };

    const res = await api.post('/config/update', payload);
    window.$toast?.(res.data.message, 'success', '配置保存成功');
    fetchConfig();
  } catch (err) {
    window.$toast?.('保存配置失败: ' + formatApiError(err), 'error');
  } finally {
    saving.value = false;
  }
}

async function fetchLogs() {
  try {
    const res = await api.get(`/logs/view?lines=${logLines.value}`);
    if (res.data?.code === 200 && res.data?.data?.logs) {
      logContent.value = res.data.data.logs.join('\n');
      nextTick(() => {
        if (logTerminal.value) {
          logTerminal.value.scrollTop = logTerminal.value.scrollHeight;
        }
      });
    }
  } catch (err) {
    console.error('Fetch logs error', err);
  }
}

async function clearLogs() {
  if (!confirm('确定要物理清空日志文件吗？')) return;
  try {
    const res = await api.post('/logs/clear', { confirm_key: 'DANGER_CONFIRM_DELETE_ALL' });
    window.$toast?.(res.data.message, 'success', '清空成功');
    fetchLogs();
  } catch (err) {
    window.$toast?.('清空日志失败: ' + formatApiError(err), 'error');
  }
}
</script>
