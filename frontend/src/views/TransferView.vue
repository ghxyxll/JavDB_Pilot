<template>
  <div class="space-y-6 animate-fade-in">
    
    <!-- Top Modern Glassmorphism Header -->
    <div class="bg-gradient-to-r from-slate-900/95 via-indigo-950/40 to-slate-900/95 backdrop-blur-xl p-6 rounded-3xl border border-slate-800/80 shadow-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-5 relative overflow-hidden">
      <!-- Ambient Backlight -->
      <div class="absolute -top-16 -left-16 w-56 h-56 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>
      <div class="absolute -bottom-16 -right-16 w-56 h-56 bg-purple-500/10 rounded-full blur-3xl pointer-events-none"></div>

      <div class="relative z-10 space-y-1.5">
        <h2 class="text-xl font-extrabold text-slate-100 flex items-center space-x-3 tracking-tight">
          <div class="p-2.5 rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shadow-inner">
            <Cloud class="w-5 h-5" />
          </div>
          <span>115 云盘离线自动化与管理中心</span>
        </h2>
        <p class="text-xs text-slate-400 leading-relaxed">
          管理本地数据库已离线影片状态、一键对齐 115 远端真实离线进度与配置自动化离线推送
        </p>
      </div>

      <div class="relative z-10 flex items-center space-x-3 shrink-0 flex-wrap gap-2">
        <!-- 🔄 一键同步对比 115 离线状态 -->
        <button 
          @click="syncStatus" 
          :disabled="loadingSync"
          class="px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 active:scale-95 text-white font-bold rounded-2xl text-xs shadow-lg shadow-indigo-600/25 transition flex items-center space-x-2 disabled:opacity-50 cursor-pointer"
        >
          <RefreshCw :class="['w-4 h-4', loadingSync ? 'animate-spin' : '']" />
          <span>一键对比 115 离线状态</span>
        </button>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="flex items-center space-x-3 border-b border-slate-800/80 pb-2 text-xs font-bold">
      <button 
        @click="activeTab = 'local'"
        :class="[
          'px-4 py-2.5 rounded-2xl transition-all duration-300 flex items-center space-x-2 cursor-pointer',
          activeTab === 'local' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30 font-extrabold' : 'text-slate-400 hover:text-slate-200 bg-slate-900/60 border border-slate-800/80'
        ]"
      >
        <Database class="w-4 h-4" />
        <span>📦 本地已离线记录与真实状态管理</span>
        <span v-if="localTotal" class="px-1.5 py-0.5 rounded bg-indigo-400/20 text-[10px] font-mono">{{ localTotal }}</span>
      </button>

      <button 
        @click="activeTab = 'manual'"
        :class="[
          'px-4 py-2.5 rounded-2xl transition-all duration-300 flex items-center space-x-2 cursor-pointer',
          activeTab === 'manual' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30 font-extrabold' : 'text-slate-400 hover:text-slate-200 bg-slate-900/60 border border-slate-800/80'
        ]"
      >
        <Send class="w-4 h-4" />
        <span>🚀 手动增量推送</span>
      </button>
    </div>

    <!-- TAB 1: 本地离线纪录与删除重置管理 (Default Tab) -->
    <div v-if="activeTab === 'local'" class="space-y-4">
      
      <!-- 🎛️ 搜索与多维筛选控制工具栏 -->
      <div class="flex flex-wrap items-center justify-between gap-3 bg-slate-900/90 backdrop-blur-xl p-4 rounded-3xl border border-slate-800/90 shadow-xl">
        <div class="flex items-center space-x-3 flex-wrap gap-2 text-xs flex-1">
          
          <!-- 🔍 关键字搜索输入框 (支持番号 SNOS-258 / 标题搜索) -->
          <div class="relative w-64">
            <Search class="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input 
              v-model="searchKeyword" 
              @keyup.enter="handleSearch"
              type="text" 
              placeholder="搜索番号 / 标题 (如: SNOS-258)"
              class="w-full bg-slate-950 border border-slate-800 rounded-2xl pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:border-indigo-500 outline-none transition font-mono shadow-inner"
            />
            <button 
              v-if="searchKeyword" 
              @click="clearSearch" 
              class="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-xs font-bold"
            >
              ✕
            </button>
          </div>

          <!-- 🧲 磁力类型筛选 -->
          <div class="flex items-center space-x-1.5">
            <span class="font-bold text-slate-300 flex items-center space-x-1">
              <Filter class="w-3.5 h-3.5 text-indigo-400" />
              <span>磁力:</span>
            </span>
            <select 
              v-model="filterMagnetType" 
              @change="handleSearch" 
              class="bg-slate-950 border border-slate-800 rounded-2xl px-3 py-1.5 text-xs text-indigo-300 font-bold outline-none focus:border-indigo-500 transition cursor-pointer shadow-inner"
            >
              <option value="all">🌟 全部类型</option>
              <option value="magnet_uc">⚡ 无码中字 (magnet_uc)</option>
              <option value="magnet_4k">🔥 4K超清 (magnet_4k)</option>
              <option value="magnet_c">💬 有码中字 (magnet_c)</option>
              <option value="magnet_u">🎬 无码高清 (magnet_u)</option>
              <option value="magnet_normal">📼 普通磁力 (magnet_normal)</option>
            </select>
          </div>

          <!-- 🎯 离线状态筛选 -->
          <div class="flex items-center space-x-1.5">
            <span class="font-bold text-slate-300 flex items-center space-x-1">
              <CheckCircle2 class="w-3.5 h-3.5 text-emerald-400" />
              <span>状态:</span>
            </span>
            <select 
              v-model="filterStatus" 
              @change="handleSearch" 
              class="bg-slate-950 border border-slate-800 rounded-2xl px-3 py-1.5 text-xs text-emerald-300 font-bold outline-none focus:border-indigo-500 transition cursor-pointer shadow-inner"
            >
              <option value="all">🌐 全部状态</option>
              <option value="2">🎉 115 离线完成</option>
              <option value="1">📥 115 正在下载</option>
              <option value="0">⏳ 115 排队分配</option>
              <option value="-1">❌ 115 离线失败</option>
            </select>
          </div>
        </div>

        <div class="flex items-center space-x-2 shrink-0">
          <button 
            @click="handleSearch" 
            class="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white font-extrabold rounded-2xl text-xs shadow-md shadow-indigo-600/25 transition cursor-pointer flex items-center space-x-1"
          >
            <Search class="w-3.5 h-3.5" />
            <span>搜索检索</span>
          </button>
          <button 
            @click="fetchLocalHistory(1)" 
            :disabled="loadingLocal"
            class="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-300 rounded-2xl text-xs font-bold transition flex items-center space-x-1.5 cursor-pointer shadow-md"
          >
            <RefreshCw :class="['w-3.5 h-3.5', loadingLocal ? 'animate-spin text-indigo-400' : '']" />
            <span>刷新</span>
          </button>
        </div>
      </div>

      <div v-if="loadingLocal" class="py-16 text-center text-xs text-slate-400 space-y-3 bg-slate-900/60 rounded-3xl border border-slate-800/80">
        <RefreshCw class="w-6 h-6 text-indigo-400 animate-spin mx-auto" />
        <p>正在检索读取离线历史记录...</p>
      </div>

      <div v-else-if="!localHistory.length" class="bg-slate-900/60 p-12 rounded-3xl border border-slate-800/80 text-center space-y-2">
        <Database class="w-8 h-8 text-slate-500 mx-auto" />
        <p class="text-xs font-bold text-slate-300">未找到符合搜索/筛选条件的离线记录</p>
        <p class="text-[11px] text-slate-500">尝试输入其他番号（如: SNOS-258）或重置筛选条件</p>
      </div>

      <div v-else class="space-y-4">
        <div class="bg-slate-900/90 backdrop-blur-xl rounded-3xl border border-slate-800/90 shadow-2xl overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs border-collapse min-w-[800px]">
            <thead class="bg-slate-950/80 text-slate-400 uppercase border-b border-slate-800/80 font-mono">
              <tr>
                <th class="p-3 pl-4 font-bold w-28">番号</th>
                <th class="p-3 font-bold">影片名称</th>
                <th class="p-3 font-bold">推送磁力类型</th>
                <th class="p-3 font-bold">115 真实离线状态</th>
                <th class="p-3 font-bold">推送时间</th>
                <th class="p-3 pr-4 font-bold text-right">操作</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-800/80 text-slate-300">
              <tr v-for="item in localHistory" :key="item.id" class="hover:bg-slate-800/40 transition">
                <td class="p-3 pl-4 font-mono font-extrabold text-indigo-300 text-xs w-28 whitespace-nowrap">
                  {{ item.code }}
                </td>
                <td class="p-4 max-w-[220px]">
                  <div class="font-bold text-slate-100 truncate" :title="item.title">{{ item.title || item.code }}</div>
                  <div class="text-[10px] font-mono text-slate-500 truncate" :title="item.wp_path">路径: {{ item.wp_path || '-' }}</div>
                </td>
                <td class="p-4 font-mono">
                  <span :class="[
                    'px-2.5 py-1 rounded-xl border font-bold text-[10px]',
                    item.magnet_type === 'magnet_uc' ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30' :
                    item.magnet_type === 'magnet_4k' ? 'bg-amber-500/20 text-amber-300 border-amber-500/30' :
                    item.magnet_type === 'magnet_c' ? 'bg-purple-500/20 text-purple-300 border-purple-500/30' :
                    item.magnet_type === 'magnet_u' ? 'bg-teal-500/20 text-teal-300 border-teal-500/30' : 'bg-slate-800 text-slate-300 border-slate-700'
                  ]">
                    {{ formatMagnetTypeLabel(item.magnet_type) }}
                  </span>
                </td>
                <td class="p-4 font-mono">
                  <span :class="[
                    'px-2.5 py-1 rounded-xl text-[10px] font-extrabold border shadow-sm',
                    item.status === 2 ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' :
                    item.status === 1 ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30 animate-pulse' :
                    item.status === 0 ? 'bg-amber-500/20 text-amber-300 border-amber-500/30' : 'bg-rose-500/20 text-rose-300 border-rose-500/30'
                  ]">
                    {{ formatLocalStatus(item.status) }}
                  </span>
                </td>
                <td class="p-4 font-mono text-slate-400 text-[11px]">{{ item.pushed_at || '-' }}</td>
                <td class="p-4 text-right">
                  <!-- 手动重置/删除离线标记按钮 -->
                  <button 
                    @click="resetLocalPushRecord(item)"
                    title="清空此影片在数据库中的离线记录，重置后可重新离线推送"
                    class="px-3 py-1.5 bg-rose-500/10 hover:bg-rose-600/30 text-rose-400 border border-rose-500/30 rounded-xl font-bold transition active:scale-95 cursor-pointer flex items-center space-x-1 ml-auto"
                  >
                    <Trash2 class="w-3.5 h-3.5" />
                    <span>重置离线标记</span>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
          </div>
        </div>

        <!-- 📄 分页控制栏 (Pagination Bar) -->
        <div v-if="totalPages > 1" class="flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-900/90 backdrop-blur-xl p-4 rounded-3xl border border-slate-800/90 shadow-lg text-xs">
          <div class="text-slate-400 font-mono">
            显示第 <span class="text-indigo-400 font-extrabold">{{ (currentPage - 1) * pageSize + 1 }}</span> 至 <span class="text-indigo-400 font-extrabold">{{ Math.min(currentPage * pageSize, localTotal) }}</span> 条 ，共 <span class="text-slate-200 font-extrabold">{{ localTotal }}</span> 条记录
          </div>

          <div class="flex items-center space-x-2 font-mono">
            <button 
              @click="changePage(currentPage - 1)" 
              :disabled="currentPage <= 1"
              class="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:hover:bg-slate-800 text-slate-300 rounded-xl font-bold transition flex items-center space-x-1 cursor-pointer"
            >
              <ChevronLeft class="w-4 h-4" />
              <span>上一页</span>
            </button>

            <span class="px-3 py-1 bg-slate-950 rounded-xl border border-slate-800 text-indigo-300 font-extrabold">
              {{ currentPage }} / {{ totalPages }} 页
            </span>

            <button 
              @click="changePage(currentPage + 1)" 
              :disabled="currentPage >= totalPages"
              class="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:hover:bg-slate-800 text-slate-300 rounded-xl font-bold transition flex items-center space-x-1 cursor-pointer"
            >
              <span>下一页</span>
              <ChevronRight class="w-4 h-4" />
            </button>
          </div>
        </div>

      </div>
    </div>

    <!-- TAB 2: 手动增量与目标推送 (Manual Push Panel) -->
    <div v-else-if="activeTab === 'manual'" class="space-y-6">
      
      <!-- 1. 按时间区间增量离线推送 -->
      <div class="bg-slate-900/90 backdrop-blur-xl p-6 rounded-3xl border border-slate-800/90 shadow-2xl space-y-5">
        <h3 class="text-base font-extrabold text-slate-100 border-b border-slate-800/80 pb-3 flex items-center space-x-2.5">
          <div class="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-inner">
            <Send class="w-4 h-4" />
          </div>
          <span>时间区间磁力离线推送 (Incremental Push)</span>
        </h3>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div>
            <label class="block text-slate-300 mb-1.5 font-bold">起始时间 (start_time)</label>
            <input 
              v-model="startTime" 
              type="text" 
              placeholder="2026-07-01 00:00:00"
              class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 font-mono focus:border-indigo-500 outline-none shadow-inner"
            />
          </div>

          <div>
            <label class="block text-slate-300 mb-1.5 font-bold">截止时间 (end_time)</label>
            <input 
              v-model="endTime" 
              type="text" 
              placeholder="2026-07-25 23:59:59"
              class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 font-mono focus:border-indigo-500 outline-none shadow-inner"
            />
          </div>

          <div>
            <label class="block text-slate-300 mb-1.5 font-bold">磁力槽位</label>
            <select v-model="manualMagnetType" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 font-mono focus:border-indigo-500 outline-none shadow-inner">
              <option value="magnet_uc">magnet_uc (无码中字/破解 推荐)</option>
              <option value="magnet_4k">magnet_4k (4K超清)</option>
              <option value="magnet_c">magnet_c (有码中字)</option>
              <option value="magnet_u">magnet_u (无码高清)</option>
            </select>
          </div>
        </div>

        <div class="flex items-center justify-between pt-2">
          <p class="text-[11px] text-slate-400">
            * 批量推送受 115 剩余配额保护并自动分批间隔防风控
          </p>

          <button 
            @click="submitIncrementalPush"
            :disabled="loadingPush"
            class="px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 active:scale-95 text-white font-extrabold text-xs rounded-2xl shadow-lg shadow-indigo-600/25 transition disabled:opacity-50 cursor-pointer"
          >
            {{ loadingPush ? '正在提交推送...' : '🚀 开始按时间区间提交 115 离线' }}
          </button>
        </div>
      </div>

      <!-- 2. 按指定演员批量离线推送 -->
      <div class="bg-slate-900/90 backdrop-blur-xl p-6 rounded-3xl border border-slate-800/90 shadow-2xl space-y-4">
        <h3 class="text-base font-extrabold text-slate-100 border-b border-slate-800/80 pb-3 flex items-center space-x-2.5">
          <div class="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shadow-inner">
            <User class="w-4 h-4" />
          </div>
          <span>🎬 按指定订阅演员提交 115 离线任务</span>
        </h3>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div>
            <label class="block text-slate-300 mb-1.5 font-bold">演员姓名</label>
            <input 
              v-model="actorPushName" 
              type="text" 
              placeholder="输入或搜索演员姓名 (如: 三上悠亞)"
              class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 font-bold focus:border-indigo-500 outline-none shadow-inner"
            />
          </div>

          <div>
            <label class="block text-slate-300 mb-1.5 font-bold">磁力推送策略</label>
            <select v-model="actorMagnetType" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 font-mono focus:border-indigo-500 outline-none shadow-inner">
              <option value="smart_priority">🌟 智能升阶优先 (UC > 4K > C 自动择优与升级)</option>
              <option value="magnet_uc">⚡ 无码中字 (magnet_uc)</option>
              <option value="magnet_4k">🔥 4K超清 (magnet_4k)</option>
              <option value="magnet_c">💬 有码中字 (magnet_c)</option>
              <option value="magnet_u">🎬 无码高清 (magnet_u)</option>
            </select>
          </div>
        </div>

        <div class="flex justify-end pt-1">
          <button 
            @click="submitActorPush"
            :disabled="loadingPushActor || !actorPushName.trim()"
            class="px-6 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 active:scale-95 text-white font-extrabold text-xs rounded-2xl shadow-lg shadow-emerald-600/25 transition disabled:opacity-50 cursor-pointer flex items-center space-x-2"
          >
            <RefreshCw v-if="loadingPushActor" class="w-4 h-4 animate-spin" />
            <CloudDownload v-else class="w-4 h-4" />
            <span>{{ loadingPushActor ? '正在离线推送...' : '🚀 批量推送该演员作品到 115' }}</span>
          </button>
        </div>
      </div>

      <!-- 3. 按指定收藏清单批量离线推送 -->
      <div class="bg-slate-900/90 backdrop-blur-xl p-6 rounded-3xl border border-slate-800/90 shadow-2xl space-y-4">
        <h3 class="text-base font-extrabold text-slate-100 border-b border-slate-800/80 pb-3 flex items-center space-x-2.5">
          <div class="p-2 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20 shadow-inner">
            <Folder class="w-4 h-4" />
          </div>
          <span>📑 按指定收藏清单提交 115 离线任务</span>
        </h3>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div>
            <label class="block text-slate-300 mb-1.5 font-bold">清单 ID 或 URL</label>
            <input 
              v-model="listPushId" 
              type="text" 
              placeholder="输入清单 ID 或 URL (如: VwKbrn)"
              class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 font-mono focus:border-indigo-500 outline-none shadow-inner"
            />
          </div>

          <div>
            <label class="block text-slate-300 mb-1.5 font-bold">磁力推送策略</label>
            <select v-model="listMagnetType" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 font-mono focus:border-indigo-500 outline-none shadow-inner">
              <option value="smart_priority">🌟 智能升阶优先 (UC > 4K > C 自动择优与升级)</option>
              <option value="magnet_uc">⚡ 无码中字 (magnet_uc)</option>
              <option value="magnet_4k">🔥 4K超清 (magnet_4k)</option>
              <option value="magnet_c">💬 有码中字 (magnet_c)</option>
              <option value="magnet_u">🎬 无码高清 (magnet_u)</option>
            </select>
          </div>
        </div>

        <div class="flex justify-end pt-1">
          <button 
            @click="submitListPush"
            :disabled="loadingPushList || !listPushId.trim()"
            class="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 active:scale-95 text-white font-extrabold text-xs rounded-2xl shadow-lg shadow-purple-600/25 transition disabled:opacity-50 cursor-pointer flex items-center space-x-2"
          >
            <RefreshCw v-if="loadingPushList" class="w-4 h-4 animate-spin" />
            <CloudDownload v-else class="w-4 h-4" />
            <span>{{ loadingPushList ? '正在离线推送...' : '🚀 批量推送该清单作品到 115' }}</span>
          </button>
        </div>
      </div>

      <!-- 日志面板 -->
      <div v-if="pushLogs.length" class="space-y-2 border-t border-slate-800/80 pt-4 bg-slate-900/90 p-5 rounded-3xl">
        <h4 class="text-xs font-extrabold text-slate-200">最新批量提交日志</h4>
        <div class="bg-slate-950 p-4 rounded-2xl border border-slate-800/80 font-mono text-xs text-indigo-300 space-y-1 max-h-60 overflow-y-auto shadow-inner">
          <div v-for="(log, idx) in pushLogs" :key="idx">{{ log }}</div>
        </div>
      </div>

    </div>

    <!-- Modal: ⏰ 115 自动化离线任务配置 -->
    <div v-if="showAutoModal" class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 animate-fade-in">
      <div class="bg-slate-900 border border-slate-800/90 rounded-3xl p-6 w-full max-w-md shadow-2xl space-y-4 animate-scale-up">
        <h3 class="text-base font-extrabold text-slate-100 flex items-center space-x-2">
          <Clock class="w-5 h-5 text-emerald-400" />
          <span>添加 115 自动化离线推送任务</span>
        </h3>

        <div class="space-y-3.5 text-xs">
          <div>
            <label class="block text-slate-300 font-bold mb-1.5">离线推送影片范围</label>
            <select v-model="autoForm.time_range" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none font-bold">
              <option value="today">📅 当天抓取的影片 (推荐)</option>
              <option value="last_24h">⏳ 过去 24 小时抓取的影片</option>
              <option value="last_7d">📆 过去 7 天抓取的影片</option>
              <option value="all">📚 所有历史未离线影片</option>
            </select>
          </div>

          <div>
            <label class="block text-slate-300 font-bold mb-1.5">优先推送的磁力类型</label>
            <select v-model="autoForm.magnet_type" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none font-bold">
              <option value="magnet_uc">⚡ magnet_uc (无码中字/破解 - 推荐)</option>
              <option value="magnet_4k">🔥 magnet_4k (4K超清)</option>
              <option value="magnet_c">💬 magnet_c (有码中字)</option>
              <option value="magnet_u">🎬 magnet_u (无码高清)</option>
            </select>
          </div>

          <div>
            <label class="block text-slate-300 font-bold mb-1.5">定时触发时间规则</label>
            <div class="grid grid-cols-2 gap-2 mb-2">
              <button 
                v-for="preset in cronPresets" 
                :key="preset.expr"
                @click="autoForm.cron_expression = preset.expr"
                :class="[
                  'p-2 rounded-xl border text-xs font-mono font-bold transition text-center cursor-pointer',
                  autoForm.cron_expression === preset.expr ? 'bg-emerald-600/30 border-emerald-500 text-emerald-300' : 'bg-slate-950 border-slate-800 text-slate-400'
                ]"
              >
                {{ preset.label }}
              </button>
            </div>
            <input 
              v-model="autoForm.cron_expression" 
              type="text" 
              placeholder="Cron 表达式，如 0 4 * * *"
              class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none font-mono text-xs"
            />
          </div>
        </div>

        <div class="flex justify-end space-x-3 pt-3 border-t border-slate-800/80">
          <button 
            @click="showAutoModal = false" 
            class="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-2xl text-xs font-bold transition cursor-pointer"
          >
            取消
          </button>
          <button 
            @click="submitAutoTask" 
            :disabled="submittingAuto"
            class="px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-extrabold text-xs rounded-2xl shadow-lg shadow-emerald-600/25 transition disabled:opacity-50 cursor-pointer"
          >
            {{ submittingAuto ? '正在保存...' : '创建并加入【定时任务】' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { Cloud, Send, RefreshCw, Clock, Database, CheckCircle2, Trash2, Filter, Search, ChevronLeft, ChevronRight, User, Folder, CloudDownload } from '@lucide/vue';
import api, { formatApiError } from '../api';

const activeTab = ref('local');
const quota = ref({ count: 1500, used: 0, remaining: 1500 });
const localHistory = ref([]);
const localTotal = ref(0);

const searchKeyword = ref('');
const filterMagnetType = ref('all');
const filterStatus = ref('all');

// 分页状态
const currentPage = ref(1);
const pageSize = ref(20);
const totalPages = ref(1);

const loadingLocal = ref(false);
const loadingSync = ref(false);
const loadingPush = ref(false);

const startTime = ref('');
const endTime = ref('');
const manualMagnetType = ref('magnet_uc');
const limit = ref(50);
const pushLogs = ref([]);

const actorPushName = ref('');
const actorMagnetType = ref('smart_priority');
const loadingPushActor = ref(false);

const listPushId = ref('');
const listMagnetType = ref('smart_priority');
const loadingPushList = ref(false);

// 自动化定时模态框状态
const showAutoModal = ref(false);
const submittingAuto = ref(false);

const autoForm = ref({
  time_range: 'today',
  magnet_type: 'magnet_uc',
  cron_expression: '0 4 * * *'
});

const cronPresets = [
  { label: '每天 04:00 (推荐)', expr: '0 4 * * *' },
  { label: '每天 00:00', expr: '0 0 * * *' },
  { label: '每 12 小时', expr: '0 */12 * * *' },
  { label: '每 6 小时', expr: '0 */6 * * *' }
];

onMounted(() => {
  fetchLocalHistory(1);
});

function handleSearch() {
  fetchLocalHistory(1);
}

function clearSearch() {
  searchKeyword.value = '';
  fetchLocalHistory(1);
}

function changePage(page) {
  if (page < 1 || page > totalPages.value) return;
  fetchLocalHistory(page);
}

async function fetchLocalHistory(page = currentPage.value) {
  currentPage.value = page;
  loadingLocal.value = true;
  try {
    const params = new URLSearchParams();
    params.append('page', String(currentPage.value));
    params.append('limit', String(pageSize.value));

    if (searchKeyword.value.trim()) {
      params.append('keyword', searchKeyword.value.trim());
    }
    if (filterMagnetType.value && filterMagnetType.value !== 'all') {
      params.append('magnet_type', filterMagnetType.value);
    }
    if (filterStatus.value && filterStatus.value !== 'all') {
      params.append('status', filterStatus.value);
    }

    const res = await api.get(`/transfer/history?${params.toString()}`);
    if (res.data?.code === 200 && res.data.data) {
      localHistory.value = res.data.data.items || [];
      localTotal.value = res.data.data.total || 0;
      totalPages.value = res.data.data.total_pages || 1;
    }
  } catch (err) {
    console.error('Fetch local push history error', err);
  } finally {
    loadingLocal.value = false;
  }
}

async function resetLocalPushRecord(item) {
  if (!confirm(`确定要重置并清空番号 [${item.code}] 的离线推送记录吗？重置后可重新离线推送`)) return;
  try {
    const res = await api.post('/transfer/history/delete', { id: item.id, code: item.code });
    if (res.data?.code === 200) {
      window.$toast?.(`已成功重置番号 [${item.code}] 的离线状态！`, 'success', '重置成功');
      fetchLocalHistory();
    }
  } catch (err) {
    window.$toast?.('重置离线状态失败: ' + formatApiError(err), 'error');
  }
}

async function submitAutoTask() {
  submittingAuto.value = true;
  const rangeMap = { today: '当天新增', last_24h: '24小时内', last_7d: '7天内', all: '全量历史' };
  const magnetMap = { magnet_uc: '无码中字', magnet_4k: '4K超清', magnet_c: '有码中字', magnet_u: '无码高清' };
  
  const rangeLabel = rangeMap[autoForm.value.time_range] || '增量';
  const magnetLabel = magnetMap[autoForm.value.magnet_type] || '中字磁力';
  const taskName = `115 离线自动推送 [${rangeLabel} | ${magnetLabel}]`;
  const jobId = `transfer_cron_${Date.now().toString(36)}`;

  try {
    const res = await api.post('/schedule/add-cron', {
      job_id: jobId,
      job_type: 'transfer_push',
      time_range: autoForm.value.time_range,
      magnet_type: autoForm.value.magnet_type,
      cron_expression: autoForm.value.cron_expression,
      task_name: taskName
    });

    if (res.data?.code === 200) {
      window.$toast?.(`115 自动化推送任务 [${taskName}] 创建成功！可在【定时任务】中管理`, 'success', '定时推送已就绪');
      showAutoModal.value = false;
    }
  } catch (err) {
    window.$toast?.('创建 115 自动化推送失败: ' + formatApiError(err), 'error');
  } finally {
    submittingAuto.value = false;
  }
}

async function submitIncrementalPush() {
  loadingPush.value = true;
  pushLogs.value = [];
  try {
    const payload = {
      start_time: startTime.value.trim() || undefined,
      end_time: endTime.value.trim() || undefined,
      magnet_type: manualMagnetType.value,
      limit: limit.value || 50
    };
    const res = await api.post('/transfer/push-incremental', payload);
    if (res.data?.code === 200) {
      window.$toast?.(res.data.message || '增量离线任务提交完成', 'success');
      pushLogs.value = res.data.data?.logs || [res.data.message];
      fetchLocalHistory(1);
    }
  } catch (err) {
    window.$toast?.('推送离线失败: ' + formatApiError(err), 'error');
  } finally {
    loadingPush.value = false;
  }
}

async function submitActorPush() {
  if (!actorPushName.value.trim()) return;
  loadingPushActor.value = true;
  try {
    const res = await api.post('/transfer/push-by-actor', {
      actor_name: actorPushName.value.trim(),
      magnet_type: actorMagnetType.value
    });
    if (res.data?.code === 200) {
      const data = res.data.data;
      pushLogs.value.unshift(`[${new Date().toLocaleTimeString()}] 🎬 演员 [${actorPushName.value.trim()}] 离线推送: ${data.message}`);
      window.$toast?.(data.message || `演员 [${actorPushName.value.trim()}] 的离线任务推送成功！`, 'success', '115 演员离线成功');
      fetchLocalHistory();
    }
  } catch (err) {
    window.$toast?.(`推送失败: ${formatApiError(err)}`, 'error');
  } finally {
    loadingPushActor.value = false;
  }
}

async function submitListPush() {
  if (!listPushId.value.trim()) return;
  loadingPushList.value = true;
  try {
    const res = await api.post('/transfer/push-by-list', {
      list_id_or_url: listPushId.value.trim(),
      magnet_type: listMagnetType.value
    });
    if (res.data?.code === 200) {
      const data = res.data.data;
      pushLogs.value.unshift(`[${new Date().toLocaleTimeString()}] 📑 清单 [${listPushId.value.trim()}] 离线推送: ${data.message}`);
      window.$toast?.(data.message || `清单 [${listPushId.value.trim()}] 的离线任务推送成功！`, 'success', '115 清单离线成功');
      fetchLocalHistory();
    }
  } catch (err) {
    window.$toast?.(`推送失败: ${formatApiError(err)}`, 'error');
  } finally {
    loadingPushList.value = false;
  }
}

async function syncStatus() {
  loadingSync.value = true;
  try {
    const res = await api.post('/transfer/sync-status');
    if (res.data?.code === 200) {
      window.$toast?.(res.data.message || '已成功与 115 远端比对对齐真实离线状态！', 'success', '状态同步成功');
      fetchLocalHistory();
    }
  } catch (err) {
    window.$toast?.('同步 115 离线状态失败: ' + formatApiError(err), 'error');
  } finally {
    loadingSync.value = false;
  }
}

function formatMagnetTypeLabel(type) {
  if (type === 'magnet_uc') return '⚡ 无码中字';
  if (type === 'magnet_4k') return '🔥 4K超清';
  if (type === 'magnet_c') return '💬 有码中字';
  if (type === 'magnet_u') return '🎬 无码高清';
  if (type === 'magnet_normal') return '📼 普通磁力';
  return type || '默认';
}

function formatLocalStatus(status) {
  if (status === 2) return '🎉 115 离线完成';
  if (status === 1) return '📥 115 正在下载';
  if (status === 0) return '⏳ 115 已分配排队';
  if (status === -1) return '❌ 115 离线失败';
  return '❓ 待对比对齐';
}
</script>
