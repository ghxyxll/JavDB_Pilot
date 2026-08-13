<template>
  <div class="space-y-6 animate-fade-in">
    
    <!-- Top Modern Glassmorphism Header -->
    <div class="bg-gradient-to-r from-slate-900/95 via-indigo-950/40 to-slate-900/95 backdrop-blur-xl p-5 sm:p-6 rounded-3xl border border-slate-800/80 shadow-2xl flex flex-col xl:flex-row xl:items-center justify-between gap-5 relative overflow-hidden">
      <!-- Ambient Backlight -->
      <div class="absolute -top-16 -left-16 w-56 h-56 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>
      <div class="absolute -bottom-16 -right-16 w-56 h-56 bg-purple-500/10 rounded-full blur-3xl pointer-events-none"></div>

      <div class="relative z-10 space-y-1.5">
        <div class="flex flex-wrap items-center gap-3">
          <h2 class="text-xl font-extrabold text-slate-100 flex items-center space-x-3 tracking-tight">
            <div class="p-2.5 rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shadow-inner">
              <Bookmark class="w-5 h-5" />
            </div>
            <span>JavDB 个人与收藏清单</span>
          </h2>

          <!-- Last Sync Time Badge -->
          <span 
            v-if="lastSyncTime" 
            class="px-3 py-1 rounded-xl bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-mono text-xs font-semibold shadow-sm flex items-center space-x-1.5 shrink-0"
          >
            <Clock class="w-3.5 h-3.5 text-indigo-400" />
            <span>上次同步: {{ lastSyncTime }}</span>
          </span>
        </div>

        <p class="text-xs text-slate-400 leading-relaxed">
          实时同步自您的 JavDB 账号，支持对每个清单灵活设置 <span class="text-indigo-300 font-semibold">加入时间 (?lst=0)</span> 或 <span class="text-purple-300 font-semibold">发布日期 (?lst=1)</span> 抓取
        </p>
      </div>

      <!-- Controls Right -->
      <div class="relative z-10 flex flex-wrap items-center gap-3 shrink-0">
        <!-- Segmented Tab Switcher -->
        <div class="flex bg-slate-950/80 p-1.5 rounded-2xl border border-slate-800/80 text-xs font-semibold shadow-inner">
          <button 
            @click="switchType('mine')"
            :class="[
              'px-4 py-2 rounded-xl transition-all duration-300 flex items-center space-x-2 cursor-pointer', 
              currentType === 'mine' ? 'bg-indigo-600 text-white font-bold shadow-lg shadow-indigo-600/30' : 'text-slate-400 hover:text-slate-200'
            ]"
          >
            <span>我的清单</span>
            <span v-if="currentType === 'mine' && userLists.length" class="px-1.5 py-0.5 rounded-md bg-indigo-400/20 text-[10px]">
              {{ userLists.length }}
            </span>
          </button>
          <button 
            @click="switchType('favorite')"
            :class="[
              'px-4 py-2 rounded-xl transition-all duration-300 flex items-center space-x-2 cursor-pointer', 
              currentType === 'favorite' ? 'bg-indigo-600 text-white font-bold shadow-lg shadow-indigo-600/30' : 'text-slate-400 hover:text-slate-200'
            ]"
          >
            <span>收藏的清单</span>
            <span v-if="currentType === 'favorite' && userLists.length" class="px-1.5 py-0.5 rounded-md bg-indigo-400/20 text-[10px]">
              {{ userLists.length }}
            </span>
          </button>
        </div>

        <!-- ⏰ 添加勾选清单自动化任务按钮 -->
        <button 
          @click="openAutoTaskModal" 
          :disabled="!userLists.length"
          class="px-4 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 active:scale-95 text-white font-extrabold rounded-2xl text-xs shadow-lg shadow-emerald-600/25 transition flex items-center space-x-2 disabled:opacity-50 cursor-pointer"
        >
          <Clock class="w-4 h-4" />
          <span>配置定时抓取任务</span>
        </button>

        <button 
          @click="showPushModal = true" 
          class="px-4 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 active:scale-95 text-white font-extrabold rounded-2xl text-xs shadow-lg shadow-emerald-600/25 transition flex items-center space-x-2 cursor-pointer"
        >
          <CloudDownload class="w-4 h-4" />
          <span>配置定时离线任务</span>
        </button>

        <!-- Refresh Button -->
        <button 
          @click="fetchLists" 
          :disabled="loading"
          class="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 active:scale-95 disabled:opacity-50 text-white font-bold rounded-2xl text-xs shadow-lg shadow-indigo-600/25 transition flex items-center space-x-2 cursor-pointer"
        >
          <RefreshCw :class="['w-4 h-4', loading ? 'animate-spin' : '']" />
          <span>同步清单</span>
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="py-20 text-center text-xs text-slate-400 space-y-3">
      <div class="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mx-auto shadow-inner">
        <RefreshCw class="w-6 h-6 text-indigo-400 animate-spin" />
      </div>
      <p class="font-medium text-slate-300">正在从 JavDB 拉取最新清单目录...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="!userLists.length" class="bg-slate-900/60 p-16 rounded-3xl border border-slate-800/80 text-center space-y-3 shadow-xl backdrop-blur-md">
      <div class="w-14 h-14 rounded-2xl bg-slate-800/60 border border-slate-700/50 flex items-center justify-center mx-auto text-slate-500">
        <FolderX class="w-7 h-7" />
      </div>
      <h3 class="text-base font-bold text-slate-200">暂未获取到清单数据</h3>
      <p class="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
        请检查您的 JavDB 登录 Cookie 是否有效，或在右上方切换 [我的清单 / 收藏的清单] 后重新同步
      </p>
    </div>

    <!-- Lists Cards Grid Layout -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
      <div 
        v-for="item in userLists" 
        :key="item.list_id + (item.url || '')"
        class="group bg-slate-900/90 hover:bg-slate-900 p-5 rounded-3xl border border-slate-800/90 hover:border-indigo-500/40 shadow-xl hover:shadow-2xl hover:shadow-indigo-500/10 transition-all duration-300 flex flex-col justify-between space-y-4 relative overflow-hidden"
      >
        <!-- Top Decorative Corner Glow -->
        <div class="absolute top-0 right-0 w-28 h-28 bg-gradient-to-bl from-indigo-500/10 via-purple-500/5 to-transparent rounded-tr-3xl pointer-events-none"></div>

        <div class="space-y-4 relative z-10">
          
          <!-- Card Header: Folder Icon & Enlarge Aligned Title -->
          <div class="flex items-center justify-between gap-3">
            <div class="flex items-center space-x-3 min-w-0">
              <!-- Folder Icon Aligned with Title -->
              <div class="p-2.5 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 shrink-0 flex items-center justify-center shadow-inner">
                <FolderHeart v-if="item.is_default" class="w-5 h-5 text-amber-400" />
                <Folder v-else class="w-5 h-5 text-indigo-400" />
              </div>

              <div class="min-w-0 flex-1">
                <h3 
                  @click="openListUrl(item)" 
                  title="点击在浏览器中打开此清单"
                  class="text-base font-extrabold text-slate-100 group-hover:text-indigo-400 cursor-pointer line-clamp-1 transition leading-tight flex items-center gap-1.5"
                >
                  <span>{{ item.list_name || item.title || '未命名清单' }}</span>
                  <ExternalLink class="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 text-indigo-400 transition shrink-0" />
                </h3>

                <div class="flex items-center space-x-2 mt-1 font-mono text-[11px] text-slate-400">
                  <span>ID: <strong class="text-indigo-300 font-bold">{{ item.list_id || '-' }}</strong></span>
                  <span v-if="item.is_default" class="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-sans text-[10px] font-bold">默认</span>
                </div>
              </div>
            </div>

            <!-- Total Movies Badge -->
            <div class="text-right shrink-0">
              <span class="px-2.5 py-1 rounded-xl bg-purple-500/10 text-purple-300 border border-purple-500/20 font-mono text-xs font-bold">
                {{ item.total_count ?? item.video_count ?? item.count ?? 0 }} 部
              </span>
            </div>
          </div>

          <!-- Sort Selector Radio Pills (?lst=0 加入时间 vs ?lst=1 发布日期) -->
          <div class="bg-slate-950/80 p-2.5 rounded-2xl border border-slate-800/80 space-y-1.5 shadow-inner">
            <div class="flex items-center justify-between text-[11px] text-slate-400 font-semibold px-1">
              <span class="flex items-center space-x-1">
                <ArrowUpDown class="w-3 h-3 text-indigo-400" />
                <span>抓取排序规则</span>
              </span>
              <span class="font-mono text-[10px] text-indigo-400">?lst={{ getSort(itemKey(item)) }}</span>
            </div>

            <div class="grid grid-cols-2 gap-1.5 text-xs font-semibold">
              <button 
                @click="setSort(itemKey(item), 0)"
                :class="[
                  'py-1.5 rounded-xl transition text-center flex items-center justify-center space-x-1 cursor-pointer',
                  getSort(itemKey(item)) === 0 
                    ? 'bg-indigo-600 text-white font-bold shadow-md shadow-indigo-600/30' 
                    : 'bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800/80'
                ]"
              >
                <span>按加入时间</span>
              </button>
              
              <button 
                @click="setSort(itemKey(item), 1)"
                :class="[
                  'py-1.5 rounded-xl transition text-center flex items-center justify-center space-x-1 cursor-pointer',
                  getSort(itemKey(item)) === 1 
                    ? 'bg-purple-600 text-white font-bold shadow-md shadow-purple-600/30' 
                    : 'bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800/80'
                ]"
              >
                <span>按发布日期</span>
              </button>
            </div>
          </div>

        </div>

        <!-- Card Footer Actions Panel -->
        <div class="w-full space-y-2 pt-3 border-t border-slate-800/80 relative z-10 mt-3">
          <!-- 智能增量更新 -->
          <button 
            @click="scrapeListUpdate(item)"
            class="w-full py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 active:scale-95 text-white font-extrabold rounded-xl text-xs shadow-lg shadow-indigo-600/20 transition flex items-center justify-center space-x-1.5 cursor-pointer"
          >
            <Sparkles class="w-3.5 h-3.5" />
            <span>智能增量更新</span>
          </button>

          <!-- 📚 全量抓取所有影片 -->
          <button 
            @click="scrapeListFull(item)"
            class="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white active:scale-95 rounded-xl text-xs font-semibold border border-slate-700/60 transition flex items-center justify-center space-x-1 cursor-pointer"
          >
            <Layers class="w-3.5 h-3.5 text-purple-400" />
            <span>全量抓取</span>
          </button>

          <!-- Extra Utility Buttons -->
          <div class="grid grid-cols-2 gap-2 pt-1">
            <button 
              @click="copyListUrl(item)" 
              class="py-1.5 bg-slate-950 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded-xl text-[11px] font-mono transition border border-slate-800 flex items-center justify-center space-x-1 cursor-pointer"
              title="复制完整带 lst=x 参数的网页链接"
            >
              <Copy class="w-3 h-3" />
              <span>复制链接</span>
            </button>

            <button 
              @click="openListUrl(item)" 
              class="py-1.5 bg-slate-950 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded-xl text-[11px] font-mono transition border border-slate-800 flex items-center justify-center space-x-1 cursor-pointer"
              title="前往 JavDB 浏览此清单"
            >
              <ExternalLink class="w-3 h-3 text-sky-400" />
              <span>源站浏览</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal: Batch Add Automation Task for User Lists -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="showAutoTaskModal" class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 animate-fade-in select-none">
          <div class="bg-slate-900 border border-slate-800/90 rounded-3xl p-6 w-full max-w-xl shadow-2xl space-y-5 max-h-[90vh] flex flex-col relative overflow-hidden animate-scale-up">
            <!-- Ambient Backlight -->
            <div class="absolute -top-16 -left-16 w-56 h-56 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>
            <div class="absolute -bottom-16 -right-16 w-56 h-56 bg-purple-500/10 rounded-full blur-3xl pointer-events-none"></div>

            <!-- Top Header -->
            <div class="flex items-center justify-between border-b border-slate-800/80 pb-3 relative z-10">
              <h3 class="text-base font-extrabold text-slate-100 flex items-center space-x-2.5">
                <div class="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-inner">
                  <Clock class="w-4 h-4" />
                </div>
                <span>添加清单定时自动化增量抓取任务</span>
              </h3>
              <button @click="showAutoTaskModal = false" class="p-1.5 rounded-full hover:bg-slate-800 text-slate-400 hover:text-white transition cursor-pointer">
                <X class="w-5 h-5" />
              </button>
            </div>

            <!-- Form Body Container -->
            <div class="space-y-4 text-xs overflow-y-auto pr-1 flex-1 relative z-10">
              <!-- List Selection Grid -->
              <div class="bg-slate-950/80 p-3.5 rounded-2xl border border-slate-800/80 space-y-2">
                <div class="flex items-center justify-between">
                  <label class="font-bold text-slate-200">选择要添加定时任务的清单 (已选 {{ selectedListKeys.size }}/{{ userLists.length }} 个)</label>
                  <button @click="toggleSelectAllLists" class="text-indigo-400 hover:underline font-bold text-[11px] cursor-pointer">
                    {{ selectedListKeys.size === userLists.length ? '取消全选' : '全选列表' }}
                  </button>
                </div>
                <div class="space-y-1.5 max-h-40 overflow-y-auto bg-slate-900 p-2.5 rounded-xl border border-slate-800/80">
                  <label 
                    v-for="listObj in userLists" 
                    :key="itemKey(listObj)"
                    class="flex items-center justify-between p-2 rounded-lg hover:bg-slate-800/60 cursor-pointer text-slate-300 text-xs"
                  >
                    <div class="flex items-center space-x-2 truncate pr-2">
                      <input 
                        type="checkbox" 
                        :checked="selectedListKeys.has(itemKey(listObj))"
                        @change="toggleListSelect(itemKey(listObj))"
                        class="rounded accent-indigo-600 cursor-pointer"
                      />
                      <span class="font-bold text-slate-100 truncate">{{ listObj.list_name || listObj.title || '自定义清单' }}</span>
                    </div>
                    <span class="text-[10px] font-mono text-indigo-400 shrink-0 font-bold">{{ listObj.total_count ?? listObj.video_count ?? listObj.count ?? 0 }} 部</span>
                  </label>
                </div>
              </div>

              <!-- Update Mode -->
              <div>
                <label class="block font-bold text-slate-200 mb-1.5">抓取更新模式 (Scrape Mode)</label>
                <div class="p-3 bg-indigo-600/25 border border-indigo-500 rounded-2xl text-indigo-200 font-bold text-xs shadow-sm shadow-indigo-600/10">
                  ⚡ 智能增量更新 (自动撞库早停，仅巡检补全新增影片)
                </div>
              </div>

              <!-- Cron Rule Preset Selector -->
              <div>
                <label class="block font-bold text-slate-200 mb-1.5">定时调度规则 (Cron Schedule)</label>
                <div class="grid grid-cols-2 gap-2 mb-2">
                  <button 
                    v-for="preset in cronPresets" 
                    :key="preset.expr"
                    @click="selectedCronExpr = preset.expr"
                    :class="[
                      'p-2 rounded-xl border text-xs font-mono font-bold transition text-center cursor-pointer',
                      selectedCronExpr === preset.expr ? 'bg-emerald-600/30 border-emerald-500 text-emerald-300' : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                    ]"
                  >
                    {{ preset.label }}
                  </button>
                </div>
                <input 
                  v-model="selectedCronExpr" 
                  type="text" 
                  placeholder="Cron 表达式，如 0 3 * * *"
                  class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none font-mono text-xs"
                />
              </div>
            </div>

            <!-- Footer Actions -->
            <div class="flex items-center justify-between border-t border-slate-800/80 pt-3 relative z-10">
              <button 
                @click="showAutoTaskModal = false" 
                class="px-4 py-2.5 rounded-2xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold transition text-xs cursor-pointer"
              >
                取消
              </button>
              <button 
                @click="submitBatchListCronTasks" 
                :disabled="submittingCron || !selectedListKeys.size"
                class="px-6 py-2.5 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 active:scale-95 text-white font-extrabold transition text-xs shadow-lg shadow-emerald-600/25 flex items-center space-x-2 disabled:opacity-50 cursor-pointer"
              >
                <RefreshCw v-if="submittingCron" class="w-4 h-4 animate-spin" />
                <Clock v-else class="w-4 h-4" />
                <span>{{ submittingCron ? '正在提交...' : `为 ${selectedListKeys.size} 个清单创建定时任务` }}</span>
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- Push Task Rule & Cron Modal -->
    <PushTaskModal 
      v-if="showPushModal"
      :initial-target-mode="'list'"
      :lock-target-mode="true"
      @close="showPushModal = false"
      @created="onPushTaskCreated"
    />

  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { Bookmark, RefreshCw, Sparkles, Layers, ExternalLink, Copy, Folder, FolderHeart, FolderX, ArrowUpDown, Clock, X, CloudDownload } from '@lucide/vue';
import api, { formatApiError } from '../api';
import PushTaskModal from '../components/PushTaskModal.vue';

const currentType = ref('mine'); // 'mine' or 'favorite'
const userLists = ref([]);
const loading = ref(false);
const lastSyncTime = ref('');

// 推送弹窗状态
const showPushModal = ref(false);
const pushListTargetId = ref('');

// Sort Modes dictionary keyed by itemKey
const sortModes = reactive({});

// 自动化任务弹窗状态
const showAutoTaskModal = ref(false);
const selectedListKeys = reactive(new Set());
const selectedCronExpr = ref('0 3 * * *');
const submittingCron = ref(false);

const cronPresets = [
  { label: '每天 03:00 (推荐)', expr: '0 3 * * *' },
  { label: '每 12 小时执行', expr: '0 */12 * * *' },
  { label: '每周一 04:00', expr: '0 4 * * 1' },
  { label: '每 6 小时执行', expr: '0 */6 * * *' }
];

function loadLocalData(type) {
  const cached = localStorage.getItem(`user_lists_cache_${type}`);
  const cachedTime = localStorage.getItem(`user_lists_${type}_time`);
  if (cachedTime) lastSyncTime.value = cachedTime;
  else lastSyncTime.value = '';

  if (cached) {
    try {
      userLists.value = JSON.parse(cached);
      localStorage.setItem('user_lists', JSON.stringify(userLists.value));
    } catch (e) {
      userLists.value = [];
    }
  } else {
    userLists.value = [];
  }
}

onMounted(() => {
  loadLocalData(currentType.value);
});

function switchType(type) {
  currentType.value = type;
  loadLocalData(type);
}

function itemKey(listObj) {
  return listObj.list_id || listObj.url || 'default';
}

function getSort(key) {
  return sortModes[key] !== undefined ? sortModes[key] : 0;
}

function setSort(key, sortVal) {
  sortModes[key] = sortVal;
}

function openAutoTaskModal() {
  selectedListKeys.clear();
  userLists.value.forEach(item => {
    selectedListKeys.add(itemKey(item));
  });
  showAutoTaskModal.value = true;
}

function toggleListSelect(key) {
  if (!key) return;
  if (selectedListKeys.has(key)) {
    selectedListKeys.delete(key);
  } else {
    selectedListKeys.add(key);
  }
}

function toggleSelectAllLists() {
  if (selectedListKeys.size === userLists.value.length) {
    selectedListKeys.clear();
  } else {
    userLists.value.forEach(item => {
      selectedListKeys.add(itemKey(item));
    });
  }
}

async function submitBatchListCronTasks() {
  if (!selectedListKeys.size) return;
  submittingCron.value = true;

  const selectedItems = userLists.value.filter(item => selectedListKeys.has(itemKey(item)));
  const urls = selectedItems.map(item => getTargetUrlWithSort(item));
  const count = selectedItems.length;
  const namesStr = selectedItems.slice(0, 3).map(i => i.list_name || i.title || '清单').join('、');
  const suffix = count > 3 ? ` 等 ${count} 个清单` : '';
  const taskName = `批量清单巡检 [${namesStr}${suffix}] - 智能增量更新`;
  const batchId = `batch_lists_cron_${Date.now().toString(36)}`;

  try {
    const res = await api.post('/schedule/add-cron', {
      job_id: batchId,
      target_url: urls[0],
      target_urls: urls,
      cron_expression: selectedCronExpr.value,
      max_pages: 3,
      auto_fetch_details: true,
      smart_incremental: true,
      task_name: taskName
    });
    if (res.data?.code === 200) {
      window.$toast?.(`已为 ${count} 个清单成功创建 1 个组合自动化任务！可在【定时任务】中统一管理`, 'success', '组合任务创建成功');
    }
  } catch (err) {
    console.error('Failed to add batch cron for lists', err);
    window.$toast?.('创建组合定时任务失败: ' + formatApiError(err), 'error');
  } finally {
    submittingCron.value = false;
    showAutoTaskModal.value = false;
  }
}

async function submitListsPipelineCron() {
  submittingCron.value = true;
  const taskName = "全量收藏清单一条龙 [排除预设清单+自动抓取+补全详情+智能UC>4K>C离线推送115]";
  const jobId = `lists_pipeline_${Date.now().toString(36)}`;

  try {
    const res = await api.post('/schedule/add-cron', {
      job_id: jobId,
      job_type: 'lists_pipeline',
      cron_expression: selectedCronExpr.value || '0 3 * * *',
      max_pages: 1,
      task_name: taskName
    });
    if (res.data?.code === 200) {
      window.$toast?.(`【${taskName}】自动化任务创建成功！将在每日 03:00 自动排除預設清單抓取并按优先级推送 115`, 'success', '一条龙任务已创建');
    }
  } catch (err) {
    window.$toast?.('创建清单一条龙自动化任务失败: ' + formatApiError(err), 'error');
  } finally {
    submittingCron.value = false;
  }
}

async function fetchLists() {
  loading.value = true;
  try {
    const res = await api.post('/user/lists', { type: currentType.value });
    if (res.data?.code === 200 && Array.isArray(res.data?.data)) {
      userLists.value = res.data.data;
      localStorage.setItem(`user_lists_cache_${currentType.value}`, JSON.stringify(res.data.data));
      localStorage.setItem('user_lists', JSON.stringify(res.data.data));
      if (res.data.data.length > 0) {
        const nowStr = new Date().toLocaleString('zh-CN');
        lastSyncTime.value = nowStr;
        localStorage.setItem(`user_lists_${currentType.value}_time`, nowStr);
        window.$toast?.(`成功从 JavDB 同步 [${currentType.value === 'mine' ? '我的' : '收藏的'}] 清单目录！`, 'success', '同步成功');
      } else {
        window.$toast?.(`未拉取到 [${currentType.value === 'mine' ? '我的' : '收藏的'}] 清单，请检查 JavDB 登录 Cookie 是否过期！`, 'warning', '清单提示');
      }
    }
  } catch (err) {
    window.$toast?.('同步清单目录失败: ' + formatApiError(err), 'error');
  } finally {
    loading.value = false;
  }
}

function getTargetUrlWithSort(listObj) {
  let baseUrl = listObj.url || listObj.detail_url || '';
  if (!baseUrl && listObj.list_id) {
    baseUrl = `https://javdb.com/lists/${listObj.list_id}`;
  }
  if (!baseUrl) return '';

  const sortVal = getSort(itemKey(listObj));
  baseUrl = baseUrl.replace(/([?&])lst=\d+/, '');
  const sep = baseUrl.includes('?') ? '&' : '?';
  return `${baseUrl}${sep}lst=${sortVal}`;
}

function openListUrl(listObj) {
  const url = getTargetUrlWithSort(listObj);
  if (url) window.open(url, '_blank');
}

function copyListUrl(listObj) {
  const url = getTargetUrlWithSort(listObj);
  if (!url) return;
  navigator.clipboard.writeText(url).then(() => {
    window.$toast?.(`清单链接已复制到剪贴板:\n${url}`, 'success', '已复制链接');
  }).catch(() => {
    window.$toast?.(`链接: ${url}`, 'info');
  });
}

async function scrapeListUpdate(listObj) {
  const targetUrl = getTargetUrlWithSort(listObj);
  if (!targetUrl) return;
  const listName = listObj.list_name || listObj.title || '自定义清单';
  const taskName = `清单 [${listName}] - 智能增量更新`;
  try {
    await api.post('/queue/add-auto-task', {
      target_url: targetUrl,
      smart_incremental: true,
      auto_fetch_details: true,
      task_name: taskName
    });
    window.$toast?.(`[${taskName}] 已加入排队队列！`, 'success', '智能更新');
  } catch (err) {
    window.$toast?.('提交任务失败: ' + formatApiError(err), 'error');
  }
}

async function scrapeListFull(listObj) {
  const targetUrl = getTargetUrlWithSort(listObj);
  if (!targetUrl) return;
  const listName = listObj.list_name || listObj.title || '自定义清单';
  const taskName = `清单 [${listName}] - 全量抓取`;
  try {
    await api.post('/queue/add-auto-task', {
      target_url: targetUrl,
      max_pages: null,
      auto_fetch_details: true,
      task_name: taskName
    });
    window.$toast?.(`[${taskName}] 已加入排队队列！`, 'success', '全量入列');
  } catch (err) {
    window.$toast?.('提交任务失败: ' + formatApiError(err), 'error');
  }
}

function pushListTo115(item) {
  const listId = item.list_id || item.id || (item.url ? item.url.split('/').pop() : '');
  pushListTargetId.value = listId;
  showPushModal.value = true;
}

function onPushTaskCreated() {
  window.$toast?.('关联的清单 115 离线任务已成功创建并提交系统！', 'success');
}
</script>
