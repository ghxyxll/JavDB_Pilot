<template>
  <div class="space-y-6 animate-fade-in">
    
    <!-- Top Row: Stat Cards Grid -->
    <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-5">
      <!-- Total Movies -->
      <div class="group bg-slate-900/90 hover:bg-slate-900 p-5 rounded-3xl border border-slate-800/90 hover:border-indigo-500/40 shadow-xl hover:shadow-2xl hover:shadow-indigo-500/10 transition-all duration-300 flex items-center justify-between relative overflow-hidden">
        <div class="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-indigo-500/10 via-purple-500/5 to-transparent rounded-tr-3xl pointer-events-none"></div>
        <div class="relative z-10 space-y-1">
          <p class="text-xs text-slate-400 font-semibold">数据库影片总数</p>
          <h3 class="text-2xl font-extrabold text-slate-100 font-mono tracking-tight">{{ stats?.total_movies || 0 }}</h3>
          <p class="text-[11px] text-indigo-400 font-medium">SQLite WAL 高效存库</p>
        </div>
        <div class="p-3 rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shadow-inner relative z-10">
          <Film class="w-7 h-7" />
        </div>
      </div>

      <!-- 4K Movies -->
      <div class="group bg-slate-900/90 hover:bg-slate-900 p-5 rounded-3xl border border-slate-800/90 hover:border-purple-500/40 shadow-xl hover:shadow-2xl hover:shadow-purple-500/10 transition-all duration-300 flex items-center justify-between relative overflow-hidden">
        <div class="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-purple-500/10 via-pink-500/5 to-transparent rounded-tr-3xl pointer-events-none"></div>
        <div class="relative z-10 space-y-1">
          <p class="text-xs text-slate-400 font-semibold">4K 超清作品</p>
          <h3 class="text-2xl font-extrabold text-purple-300 font-mono tracking-tight">{{ stats?.count_4k || 0 }}</h3>
          <p class="text-[11px] text-purple-400 font-medium">4K 原画高码率</p>
        </div>
        <div class="p-3 rounded-2xl bg-purple-500/10 text-purple-400 border border-purple-500/20 shadow-inner relative z-10">
          <Zap class="w-7 h-7" />
        </div>
      </div>

      <!-- Uncensored Sub (UC) -->
      <div class="group bg-slate-900/90 hover:bg-slate-900 p-5 rounded-3xl border border-slate-800/90 hover:border-emerald-500/40 shadow-xl hover:shadow-2xl hover:shadow-emerald-500/10 transition-all duration-300 flex items-center justify-between relative overflow-hidden">
        <div class="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-emerald-500/10 via-teal-500/5 to-transparent rounded-tr-3xl pointer-events-none"></div>
        <div class="relative z-10 space-y-1">
          <p class="text-xs text-slate-400 font-semibold">无码中字 (UC)</p>
          <h3 class="text-2xl font-extrabold text-emerald-300 font-mono tracking-tight">{{ stats?.count_uc || 0 }}</h3>
          <p class="text-[11px] text-emerald-400 font-medium">智能正则精准识别</p>
        </div>
        <div class="p-3 rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-inner relative z-10">
          <CheckCircle2 class="w-7 h-7" />
        </div>
      </div>

      <!-- 115 Pushed -->
      <div class="group bg-slate-900/90 hover:bg-slate-900 p-5 rounded-3xl border border-slate-800/90 hover:border-amber-500/40 shadow-xl hover:shadow-2xl hover:shadow-amber-500/10 transition-all duration-300 flex items-center justify-between relative overflow-hidden">
        <div class="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-amber-500/10 via-orange-500/5 to-transparent rounded-tr-3xl pointer-events-none"></div>
        <div class="relative z-10 space-y-1">
          <p class="text-xs text-slate-400 font-semibold">115 离线已推送</p>
          <h3 class="text-2xl font-extrabold text-amber-300 font-mono tracking-tight">{{ stats?.count_pushed || 0 }}</h3>
          <p class="text-[11px] text-amber-400 font-medium">API 自动化离线提交</p>
        </div>
        <div class="p-3 rounded-2xl bg-amber-500/10 text-amber-400 border border-amber-500/20 shadow-inner relative z-10">
          <CloudDownload class="w-7 h-7" />
        </div>
      </div>
    </div>

    <!-- Middle Row: 115 Storage & Quick Scrape -->
    <div class="grid grid-cols-1 xl:grid-cols-12 gap-6">
      
      <!-- 115 Quota Visual Card (7 Cols) -->
      <div class="xl:col-span-7 bg-slate-900/90 backdrop-blur-xl p-6 rounded-3xl border border-slate-800/90 shadow-2xl space-y-4 flex flex-col justify-between relative overflow-hidden">
        <div class="flex justify-between items-center relative z-10">
          <div class="flex items-center space-x-2.5">
            <div class="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shadow-inner">
              <Cloud class="w-5 h-5" />
            </div>
            <h3 class="text-base font-extrabold text-slate-100">115 云盘离线配额状态</h3>
          </div>
          <button 
            @click="fetchQuota" 
            :disabled="loadingQuota"
            class="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 active:scale-95 text-indigo-300 rounded-xl text-xs font-semibold transition flex items-center space-x-1.5 border border-slate-700/60"
          >
            <RefreshCw :class="['w-3.5 h-3.5', loadingQuota ? 'animate-spin' : '']" />
            <span>刷新配额</span>
          </button>
        </div>

        <div v-if="quotaData" class="space-y-3 bg-slate-950/80 p-4 rounded-2xl border border-slate-800/80 shadow-inner relative z-10">
          <div class="flex justify-between items-center text-xs">
            <span class="text-slate-400 font-medium">离线配额已用进度</span>
            <span class="font-mono text-indigo-400 font-bold">
              {{ quotaUsed }} / {{ quotaTotal }} 次 (可用剩余: {{ quotaRemaining }} 次)
            </span>
          </div>

          <!-- Progress Bar -->
          <div class="w-full bg-slate-900 rounded-full h-3.5 overflow-hidden p-0.5 border border-slate-800">
            <div 
              class="bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-400 h-full rounded-full transition-all duration-500 shadow-md" 
              :style="{ width: quotaPercentage + '%' }"
            ></div>
          </div>

          <div class="grid grid-cols-3 gap-2.5 pt-1 text-center text-xs">
            <div class="p-2.5 bg-slate-900 rounded-xl border border-slate-800/80">
              <p class="text-[10px] text-slate-500 font-medium">总配额</p>
              <p class="font-mono font-extrabold text-slate-200 mt-0.5">{{ quotaTotal }} 次</p>
            </div>
            <div class="p-2.5 bg-slate-900 rounded-xl border border-slate-800/80">
              <p class="text-[10px] text-slate-500 font-medium">已使用</p>
              <p class="font-mono font-extrabold text-amber-400 mt-0.5">{{ quotaUsed }} 次</p>
            </div>
            <div class="p-2.5 bg-slate-900 rounded-xl border border-slate-800/80">
              <p class="text-[10px] text-slate-500 font-medium">剩余可用</p>
              <p class="font-mono font-extrabold text-emerald-400 mt-0.5">{{ quotaRemaining }} 次</p>
            </div>
          </div>
        </div>

        <div v-else class="p-6 bg-slate-950/60 rounded-2xl border border-slate-800/60 text-center text-xs text-slate-400">
          点击上方按钮查询 115 离线配额状态
        </div>
      </div>

      <!-- Quick Action Panel (5 Cols) -->
      <div class="xl:col-span-5 bg-slate-900/90 backdrop-blur-xl p-6 rounded-3xl border border-slate-800/90 shadow-2xl space-y-4">
        <div class="flex items-center space-x-2.5 border-b border-slate-800/80 pb-3">
          <div class="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shadow-inner">
            <PlayCircle class="w-5 h-5" />
          </div>
          <h3 class="text-base font-extrabold text-slate-100">快捷触发中心</h3>
        </div>

        <!-- Single Code Scrape -->
        <div class="space-y-2">
          <label class="block text-xs font-bold text-slate-300">指定番号抓取 / 重新刷新</label>
          <div class="flex space-x-2">
            <input 
              v-model="quickCode" 
              type="text" 
              placeholder="输入番号 (如 SSIS-084)"
              class="flex-1 bg-slate-950 border border-slate-800 rounded-2xl px-3.5 py-2.5 text-xs font-mono text-slate-200 focus:border-indigo-500 outline-none shadow-inner"
            />
            <button 
              @click="submitQuickCode" 
              class="px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 active:scale-95 text-white font-bold text-xs rounded-2xl shadow-lg shadow-indigo-600/25 transition"
            >
              提交队列
            </button>
          </div>
        </div>

        <!-- Auto Scrape missing magnetic links -->
        <div class="space-y-2 pt-2 border-t border-slate-800/80">
          <label class="block text-xs font-bold text-slate-300">定向磁力数据补全 (防风控串行队列)</label>
          <div class="grid grid-cols-2 gap-2.5">
            <button 
              @click="triggerRefreshMissing('magnet_uc')" 
              class="py-2.5 bg-slate-950 hover:bg-slate-800 text-emerald-400 border border-emerald-500/30 rounded-2xl text-xs font-bold transition shadow-sm"
            >
              补全无码中字 (UC)
            </button>
            <button 
              @click="triggerRefreshMissing('magnet_4k')" 
              class="py-2.5 bg-slate-950 hover:bg-slate-800 text-purple-400 border border-purple-500/30 rounded-2xl text-xs font-bold transition shadow-sm"
            >
              补全 4K 超清
            </button>
          </div>
        </div>

      </div>

    </div>

    <!-- Bottom Row (并列双列): 左侧为后台运行日志实时流 (7 Cols), 右侧为异步 FIFO 串行任务队列 (5 Cols) -->
    <div class="grid grid-cols-1 xl:grid-cols-12 gap-6">
      
      <!-- Left Column: 后台运行日志实时流 (7 Cols) -->
      <div class="xl:col-span-7 bg-slate-900/90 backdrop-blur-xl p-6 rounded-3xl border border-slate-800/90 shadow-2xl space-y-4 flex flex-col justify-between">
        <div class="space-y-4">
          <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center border-b border-slate-800/80 pb-3 gap-3">
            <div class="flex items-center space-x-2.5">
              <div class="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shadow-inner">
                <Terminal class="w-5 h-5" />
              </div>
              <div>
                <h3 class="text-base font-extrabold text-slate-100 flex items-center space-x-2">
                  <span>后台运行日志实时流</span>
                  <span class="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 animate-pulse">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                    <span>实时流式输出</span>
                  </span>
                </h3>
                <p class="text-[11px] text-slate-400">全量运行与抓取实时终端卡片</p>
              </div>
            </div>

            <div class="flex items-center space-x-2 text-xs shrink-0">
              <select 
                v-model.number="logLines" 
                @change="fetchLogs" 
                class="bg-slate-950 border border-slate-800 text-slate-300 rounded-xl px-2.5 py-1.5 font-mono text-xs focus:border-indigo-500 outline-none shadow-inner cursor-pointer"
              >
                <option :value="100">100行</option>
                <option :value="300">300行</option>
                <option :value="500">500行</option>
              </select>

              <button 
                @click="clearScreen" 
                class="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-bold transition active:scale-95 border border-slate-700/60 cursor-pointer"
                title="清空当前窗口显示的日志 (前端清屏)"
              >
                <Eraser class="w-4 h-4" />
              </button>
            </div>
          </div>

          <div 
            ref="logTerminal" 
            class="bg-slate-950 p-4 rounded-2xl border border-slate-800/80 font-mono text-[11px] text-indigo-300/90 leading-relaxed h-80 overflow-y-auto whitespace-pre-wrap shadow-inner"
          >
            {{ logContent || '正在拉取后台实时日志...' }}
          </div>
        </div>
      </div>

      <!-- Right Column: 异步 FIFO 串行任务队列 (5 Cols) -->
      <div class="xl:col-span-5 bg-slate-900/90 backdrop-blur-xl p-6 rounded-3xl border border-slate-800/90 shadow-2xl space-y-4 flex flex-col justify-between">
        <div class="space-y-4">
          <div class="flex justify-between items-center border-b border-slate-800/80 pb-3">
            <div class="flex items-center space-x-2.5">
              <div class="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20 shadow-inner">
                <ListOrdered class="w-5 h-5" />
              </div>
              <div>
                <h3 class="text-base font-extrabold text-slate-100">异步 FIFO 串行任务队列</h3>
                <p class="text-[11px] text-slate-400">单线程防封锁排队执行</p>
              </div>
            </div>
            <div class="flex items-center space-x-1.5 shrink-0">
              <button 
                v-if="hasActiveTasks"
                @click="clearQueue" 
                title="一键清空全部排队任务并强行中断当前运行任务"
                class="px-2.5 py-1.5 bg-rose-600/20 hover:bg-rose-600 active:scale-95 text-rose-300 hover:text-white rounded-xl text-xs font-bold border border-rose-500/30 transition flex items-center space-x-1"
              >
                <Ban class="w-3.5 h-3.5" />
                <span>停止全部</span>
              </button>
              <button 
                @click="fetchQueueStatus" 
                class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 active:scale-95 text-slate-300 rounded-xl text-xs font-semibold border border-slate-700/60 transition shrink-0"
              >
                刷新队列
              </button>
            </div>
          </div>

          <!-- Queue Status Items -->
          <div v-if="queueTasks && Object.keys(queueTasks).length" class="space-y-2.5 h-80 overflow-y-auto pr-1">
            <div 
              v-for="(task, tid) in queueTasks" 
              :key="tid"
              class="p-3.5 bg-slate-950/80 rounded-2xl border border-slate-800/80 flex items-center justify-between text-xs shadow-inner gap-2"
            >
              <div class="flex items-center space-x-3 min-w-0 pr-1">
                <span class="font-mono text-slate-500 font-semibold shrink-0">[{{ tid }}]</span>
                <span class="text-slate-200 font-medium truncate" :title="task.message">{{ task.message }}</span>
              </div>

              <div class="flex items-center space-x-2 shrink-0">
                <!-- 📄 查看专属日志按钮 -->
                <button 
                  @click="openTaskLogModal(tid, task)" 
                  title="查看此任务的独立运行日志"
                  class="px-2 py-1 rounded-xl bg-indigo-500/20 hover:bg-indigo-600 active:scale-95 text-indigo-300 hover:text-white border border-indigo-500/40 text-[10px] font-bold transition flex items-center space-x-1 cursor-pointer"
                >
                  <FileText class="w-3.5 h-3.5" />
                  <span>日志</span>
                </button>

                <button 
                  v-if="task.status === 'queued' || task.status === 'running'"
                  @click="cancelTask(tid)" 
                  title="手动取消或中断此任务"
                  class="px-2 py-1 rounded-xl bg-rose-500/20 hover:bg-rose-600 active:scale-95 text-rose-300 hover:text-white border border-rose-500/40 text-[10px] font-bold transition flex items-center space-x-1 cursor-pointer"
                >
                  <Square class="w-3.5 h-3.5" />
                  <span>停止</span>
                </button>

                <span 
                  :class="[
                    'px-2.5 py-1 rounded-xl font-bold text-[10px] font-mono shrink-0',
                    task.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                    task.status === 'running' ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 animate-pulse' :
                    task.status === 'cancelling' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30 animate-pulse' :
                    task.status === 'cancelled' ? 'bg-slate-800 text-slate-400 border border-slate-700' :
                    task.status === 'failed' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
                    'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  ]"
                >
                  ● {{ task.status }}
                </span>
              </div>
            </div>
          </div>

          <div v-else class="h-80 bg-slate-950/40 rounded-2xl border border-slate-800/60 text-center text-xs text-slate-500 flex flex-col items-center justify-center space-y-2">
            <ListOrdered class="w-8 h-8 text-slate-600/50" />
            <p>当前任务队列空闲中，没有正在排队的任务</p>
          </div>
        </div>
      </div>

    </div>

    <!-- Modal: Task Specific Log Viewer -->
    <div v-if="activeLogTaskId" class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
      <div class="bg-slate-900 border border-slate-800/90 rounded-3xl p-6 w-full max-w-2xl shadow-2xl space-y-4 max-h-[90vh] flex flex-col">
        <div class="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <div class="flex items-center space-x-3 min-w-0">
            <div class="p-2.5 rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shrink-0">
              <Terminal class="w-5 h-5" />
            </div>
            <div class="min-w-0 flex-1">
              <h3 class="text-sm font-extrabold text-slate-100 flex items-center space-x-2 truncate">
                <span>{{ activeLogTaskName || activeLogTaskId }}</span>
              </h3>
              <p class="font-mono text-[10px] text-slate-400 mt-0.5">任务 ID: {{ activeLogTaskId }}</p>
            </div>
          </div>

          <div class="flex items-center space-x-2 shrink-0">
            <button 
              @click="fetchActiveTaskLog" 
              class="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition cursor-pointer"
              title="刷新实时日志"
            >
              <RefreshCw :class="['w-4 h-4', logLoading ? 'animate-spin' : '']" />
            </button>
            <button 
              @click="activeLogTaskId = null" 
              class="p-2 rounded-xl hover:bg-slate-800 text-slate-400 hover:text-white transition cursor-pointer"
            >
              <X class="w-5 h-5" />
            </button>
          </div>
        </div>

        <!-- Terminal Window -->
        <div class="bg-slate-950 rounded-2xl p-4 border border-slate-800/80 font-mono text-xs text-slate-300 h-96 overflow-y-auto space-y-1.5 shadow-inner select-text">
          <div v-if="!activeTaskLogs.length" class="text-slate-500 italic py-16 text-center">
            暂无该任务的专属日志输出...
          </div>
          <div 
            v-for="(line, idx) in activeTaskLogs" 
            :key="idx" 
            :class="[
              'leading-relaxed break-all',
              line.includes('[ERROR]') || line.includes('❌') ? 'text-rose-400 font-bold' :
              line.includes('[WARNING]') || line.includes('⚠️') || line.includes('🛑') ? 'text-amber-300' :
              line.includes('🎉') || line.includes('✅') || line.includes('💾') ? 'text-emerald-300 font-semibold' : 'text-slate-300'
            ]"
          >
            {{ line }}
          </div>
        </div>

        <!-- Modal Footer Actions -->
        <div class="flex items-center justify-between pt-2 border-t border-slate-800/80">
          <span class="text-[11px] text-slate-400 font-mono">已记录 {{ activeTaskLogs.length }} 条独占日志</span>
          <div class="flex items-center space-x-2">
            <button 
              @click="copyTaskLogs" 
              class="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-2xl text-xs font-bold transition flex items-center space-x-1.5 cursor-pointer"
            >
              <Copy class="w-3.5 h-3.5" />
              <span>复制日志</span>
            </button>
            <button 
              @click="activeLogTaskId = null" 
              class="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-2xl text-xs font-extrabold shadow-lg shadow-indigo-600/20 transition cursor-pointer"
            >
              关闭
            </button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { Film, Zap, CheckCircle2, CloudDownload, Cloud, RefreshCw, PlayCircle, ListOrdered, Terminal, Eraser, Square, Ban, FileText, X, Copy } from '@lucide/vue';
import api, { formatApiError } from '../api';

const props = defineProps({
  stats: Object
});

const emit = defineEmits(['refresh-stats']);

const quotaData = ref(null);
const loadingQuota = ref(false);
const quickCode = ref('');
const queueTasks = ref({});

// Log Stream States
const logContent = ref('');
const logLines = ref(100);
const logTerminal = ref(null);
const autoRefreshLog = ref(true);
const fetchingLog = ref(false);
let logTimer = null;
let modalLogTimer = null;

const quotaTotal = computed(() => {
  if (!quotaData.value) return 0;
  return quotaData.value.count || quotaData.value.total || 0;
});

const quotaUsed = computed(() => {
  if (!quotaData.value) return 0;
  if (quotaData.value.used !== undefined) return quotaData.value.used;
  return 0;
});

const quotaRemaining = computed(() => {
  if (!quotaData.value) return 0;
  if (quotaData.value.remaining !== undefined) return quotaData.value.remaining;
  if (quotaData.value.remain !== undefined) return quotaData.value.remain;
  return Math.max(0, quotaTotal.value - quotaUsed.value);
});

const quotaPercentage = computed(() => {
  if (!quotaTotal.value || quotaTotal.value === 0) return 0;
  return Math.min(100, Math.round((quotaUsed.value / quotaTotal.value) * 100));
});

onMounted(() => {
  fetchQuota();
  fetchQueueStatus();
  fetchLogs();
  
  // 800 毫秒超高频极速实时刷新日志流与任务队列状态
  logTimer = setInterval(() => {
    if (autoRefreshLog.value) {
      fetchLogs(true);
      fetchQueueStatus();
    }
  }, 800);
});

onUnmounted(() => {
  if (logTimer) {
    clearInterval(logTimer);
    logTimer = null;
  }
  if (modalLogTimer) {
    clearInterval(modalLogTimer);
    modalLogTimer = null;
  }
});

function toggleAutoRefresh() {
  autoRefreshLog.value = !autoRefreshLog.value;
}

const clearedTimeStr = ref('');

function clearScreen() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  clearedTimeStr.value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
  logContent.value = '';
  window.$toast?.('控制台窗口已清屏（新发生的日志将继续实时显示）', 'info');
}

async function fetchLogs(silent = false) {
  if (!silent) fetchingLog.value = true;
  try {
    const res = await api.get(`/logs/view?lines=${logLines.value}`);
    if (res.data?.code === 200 && res.data?.data?.logs) {
      let logs = res.data.data.logs;
      if (clearedTimeStr.value) {
        logs = logs.filter(line => {
          const match = line.match(/^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]/);
          if (!match) return true;
          return match[1] >= clearedTimeStr.value;
        });
      }
      logContent.value = logs.join('\n');
      nextTick(() => {
        if (logTerminal.value) {
          logTerminal.value.scrollTop = logTerminal.value.scrollHeight + 9999;
        }
      });
      setTimeout(() => {
        if (logTerminal.value) {
          logTerminal.value.scrollTop = logTerminal.value.scrollHeight + 9999;
        }
      }, 50);
    }
  } catch (err) {
    console.error('Fetch logs error', err);
  } finally {
    if (!silent) fetchingLog.value = false;
  }
}

async function fetchQuota() {
  loadingQuota.value = true;
  try {
    const res = await api.get('/transfer/quota');
    if (res.data?.code === 200) {
      quotaData.value = res.data.data;
    }
  } catch (err) {
    console.error('Fetch quota error', err);
  } finally {
    loadingQuota.value = false;
  }
}

async function submitQuickCode() {
  if (!quickCode.value.trim()) return;
  try {
    const res = await api.post('/queue/add-code-task', { code: quickCode.value.trim() });
    window.$toast?.(res.data.message, 'success', '任务已提交');
    quickCode.value = '';
    fetchQueueStatus();
    fetchLogs(true);
  } catch (err) {
    window.$toast?.('提交任务失败: ' + (err.response?.data?.detail || err.message), 'error');
  }
}

async function triggerRefreshMissing(field) {
  try {
    const res = await api.post('/db/refresh-missing', { missing_field: field, limit: 50 });
    window.$toast?.(res.data.message, 'success', '补全任务已提交');
    fetchQueueStatus();
    fetchLogs(true);
  } catch (err) {
    window.$toast?.('提交补全任务失败: ' + (err.response?.data?.detail || err.message), 'error');
  }
}

const hasActiveTasks = computed(() => {
  if (!queueTasks.value) return false;
  return Object.values(queueTasks.value).some(t => t.status === 'queued' || t.status === 'running');
});

async function cancelTask(tid) {
  try {
    const res = await api.post('/queue/cancel', { task_id: tid });
    window.$toast?.(res.data.message, 'warning', '中断任务');
    fetchQueueStatus();
    fetchLogs(true);
  } catch (err) {
    window.$toast?.('取消任务失败: ' + (err.response?.data?.detail || err.message), 'error');
  }
}

async function clearQueue() {
  try {
    const res = await api.post('/queue/clear');
    window.$toast?.(res.data.message, 'warning', '清空队列');
    fetchQueueStatus();
    fetchLogs(true);
  } catch (err) {
    window.$toast?.('清空队列失败: ' + (err.response?.data?.detail || err.message), 'error');
  }
}

async function fetchQueueStatus() {
  try {
    const res = await api.get('/queue/status');
    if (res.data?.code === 200 && res.data?.data) {
      queueTasks.value = res.data.data.tasks_status || {};
    }
  } catch (err) {
    console.error('Fetch queue error', err);
  }
}

// 独立任务专属日志 Viewer 逻辑 (支持 1.5s 实时高频轮询)
const activeLogTaskId = ref(null);
const activeLogTaskName = ref('');
const activeTaskLogs = ref([]);
const logLoading = ref(false);

async function openTaskLogModal(tid, task) {
  activeLogTaskId.value = tid;
  activeLogTaskName.value = task.task_name || task.message || `任务 [${tid}]`;
  fetchActiveTaskLog(false);

  if (modalLogTimer) clearInterval(modalLogTimer);
  modalLogTimer = setInterval(() => {
    if (activeLogTaskId.value) {
      fetchActiveTaskLog(true);
    } else {
      clearInterval(modalLogTimer);
      modalLogTimer = null;
    }
  }, 1500);
}

function closeTaskLogModal() {
  activeLogTaskId.value = null;
  if (modalLogTimer) {
    clearInterval(modalLogTimer);
    modalLogTimer = null;
  }
}

async function fetchActiveTaskLog(silent = false) {
  if (!activeLogTaskId.value) return;
  if (!silent) logLoading.value = true;
  try {
    const res = await api.get(`/queue/task-log/${activeLogTaskId.value}`);
    if (res.data?.code === 200 && res.data.data) {
      activeTaskLogs.value = res.data.data.logs || [];
      if (res.data.data.task_name) {
        activeLogTaskName.value = res.data.data.task_name;
      }
    }
  } catch (err) {
    console.error('Fetch task log error', err);
  } finally {
    if (!silent) logLoading.value = false;
  }
}

function copyTaskLogs() {
  if (!activeTaskLogs.value.length) return;
  const text = activeTaskLogs.value.join('\n');
  navigator.clipboard.writeText(text).then(() => {
    window.$toast?.('该任务日志已成功复制到剪贴板！', 'success', '已复制日志');
  }).catch(() => {
    window.$toast?.('复制日志失败', 'error');
  });
}
</script>
