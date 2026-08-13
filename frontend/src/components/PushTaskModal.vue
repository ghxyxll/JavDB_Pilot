<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 animate-fade-in select-none">
      <div class="bg-slate-900 border border-slate-800/90 rounded-3xl p-6 w-full max-w-xl shadow-2xl space-y-5 max-h-[90vh] flex flex-col relative overflow-hidden animate-scale-up">
        
        <!-- Ambient Backlight -->
        <div class="absolute -top-16 -left-16 w-56 h-56 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>
        <div class="absolute -bottom-16 -right-16 w-56 h-56 bg-purple-500/10 rounded-full blur-3xl pointer-events-none"></div>

        <!-- Top Header -->
        <div class="flex items-center justify-between border-b border-slate-800/80 pb-3 relative z-10">
          <h3 class="text-base font-extrabold text-slate-100 flex items-center space-x-2.5">
            <div class="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shadow-inner">
              <Clock class="w-4 h-4" />
            </div>
            <span>{{ modalTitle }}</span>
          </h3>
          <button @click="$emit('close')" class="p-1.5 rounded-full hover:bg-slate-800 text-slate-400 hover:text-white transition cursor-pointer">
            <X class="w-5 h-5" />
          </button>
        </div>

        <!-- Form Fields Container -->
        <div class="space-y-4 text-xs overflow-y-auto pr-1 flex-1 relative z-10">

          <!-- Target Mode Selector Pills (Shown only if not locked) -->
          <div v-if="!lockTargetMode">
            <label class="block font-bold text-slate-200 mb-1.5">1. 选择离线目标类型 (Push Target)</label>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <button 
                v-for="mode in targetModes" 
                :key="mode.id"
                @click="selectTargetMode(mode.id)"
                :class="[
                  'p-2.5 rounded-2xl border text-xs font-bold transition flex flex-col items-center justify-center space-y-1 cursor-pointer',
                  form.targetMode === mode.id ? 'bg-indigo-600/30 border-indigo-500 text-indigo-300 shadow-md shadow-indigo-600/20' : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                ]"
              >
                <component :is="mode.icon" class="w-4 h-4" />
                <span>{{ mode.label }}</span>
              </button>
            </div>
          </div>

          <!-- Mode 1: ACTOR Target Selection -->
          <div v-if="form.targetMode === 'actor'" class="bg-slate-950/80 p-3.5 rounded-2xl border border-slate-800/80 space-y-2.5">
            <div class="flex items-center justify-between">
              <label class="block font-bold text-slate-200">选择要离线推送的演员 (已选 {{ effectiveActorNames.length }} 位)</label>
              <button v-if="subscribedActors.length" @click="toggleSelectAllActors" class="text-indigo-400 hover:underline font-bold text-[11px] cursor-pointer">
                {{ selectedActorNames.size === subscribedActors.length ? '取消全选' : '全选订阅演员' }}
              </button>
            </div>

            <!-- Subscribed Actors Checkbox Grid -->
            <div v-if="subscribedActors.length" class="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-40 overflow-y-auto bg-slate-900 p-2.5 rounded-xl border border-slate-800/80">
              <label 
                v-for="act in subscribedActors" 
                :key="act.name || act.actor_name"
                class="flex items-center space-x-2 p-1.5 rounded-lg hover:bg-slate-800/60 cursor-pointer text-slate-300 text-xs truncate"
              >
                <input 
                  type="checkbox" 
                  :checked="selectedActorNames.has(act.name || act.actor_name)"
                  @change="toggleActorSelect(act.name || act.actor_name)"
                  class="rounded accent-indigo-600 cursor-pointer"
                />
                <span class="truncate">{{ act.name || act.actor_name }}</span>
              </label>
            </div>

            <!-- Manual Custom Actor Name Input -->
            <div class="pt-1">
              <label class="block font-bold text-slate-400 text-[11px] mb-1">自定义输入单演员姓名 (未在上表勾选时有效)</label>
              <input 
                v-model="customActorName" 
                type="text" 
                placeholder="手动输入演员姓名 (如: 明里つむぎ)"
                class="w-full bg-slate-900 border border-slate-800 rounded-xl p-2.5 text-slate-200 font-bold outline-none focus:border-indigo-500 transition"
              />
            </div>
          </div>

          <!-- Mode 2: LIST Target Selection -->
          <div v-else-if="form.targetMode === 'list'" class="bg-slate-950/80 p-3.5 rounded-2xl border border-slate-800/80 space-y-2.5">
            <div class="flex items-center justify-between">
              <label class="block font-bold text-slate-200">选择要离线推送的收藏清单 (已选 {{ effectiveListIds.length }} 个)</label>
              <button v-if="userLists.length" @click="toggleSelectAllLists" class="text-indigo-400 hover:underline font-bold text-[11px] cursor-pointer">
                {{ selectedListIds.size === userLists.length ? '取消全选' : '全选清单' }}
              </button>
            </div>

            <!-- User Lists Checkbox Grid -->
            <div v-if="userLists.length" class="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-40 overflow-y-auto bg-slate-900 p-2.5 rounded-xl border border-slate-800/80">
              <label 
                v-for="item in userLists" 
                :key="item.list_id || item.id || item.title"
                class="flex items-center space-x-2 p-1.5 rounded-lg hover:bg-slate-800/60 cursor-pointer text-slate-300 text-xs truncate"
              >
                <input 
                  type="checkbox" 
                  :checked="selectedListIds.has(item.list_id || item.id || (item.url ? item.url.split('/').pop() : ''))"
                  @change="toggleListSelect(item.list_id || item.id || (item.url ? item.url.split('/').pop() : ''))"
                  class="rounded accent-indigo-600 cursor-pointer"
                />
                <span class="truncate font-bold">{{ item.title || item.list_name }}</span>
              </label>
            </div>

            <!-- Manual Custom List Input -->
            <div class="pt-1">
              <label class="block font-bold text-slate-400 text-[11px] mb-1">自定义输入清单 ID 或 URL (未在上表勾选时有效)</label>
              <input 
                v-model="customListIdOrUrl" 
                type="text" 
                placeholder="手动输入清单 ID 或 URL (如: VwKbrn)"
                class="w-full bg-slate-900 border border-slate-800 rounded-xl p-2.5 text-slate-200 font-mono outline-none focus:border-indigo-500 transition"
              />
            </div>
          </div>

          <!-- Mode 3: TIME RANGE Selection -->
          <div v-else-if="form.targetMode === 'time_range'" class="bg-slate-950/80 p-3.5 rounded-2xl border border-slate-800/80 space-y-1.5">
            <label class="block font-bold text-slate-300">时间增量筛选范围</label>
            <select v-model="form.timeRange" class="w-full bg-slate-900 border border-slate-800 rounded-xl p-2.5 text-slate-200 font-bold outline-none focus:border-indigo-500 transition">
              <option value="today">📅 今天新增的磁力 (00:00 - 23:59)</option>
              <option value="last_24h">⏱️ 最近 24 小时内抓取的磁力</option>
              <option value="last_3d">🗓️ 最近 3 天内抓取的磁力</option>
              <option value="last_7d">📆 最近 7 天内抓取的磁力</option>
              <option value="all">♾️ 库中全量未离线磁力</option>
            </select>
          </div>

          <!-- 磁力匹配与升阶规则 -->
          <div>
            <label class="block font-bold text-slate-200 mb-1.5">磁力匹配与升阶规则 (Magnet Selection Rule)</label>
            <select v-model="form.magnetType" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 font-mono font-bold outline-none focus:border-indigo-500 transition">
              <option value="smart_priority">🌟 智能升阶优先 (UC无码中字 > 4K超清 > C有码中字 自动择优与升级)</option>
              <option value="magnet_uc">⚡ 仅无码中字 / 破解中字 (magnet_uc)</option>
              <option value="magnet_4k">🔥 仅 4K 超清画质 (magnet_4k)</option>
              <option value="magnet_c">💬 仅有码中字 (magnet_c)</option>
              <option value="magnet_u">🎬 仅无码高清 (magnet_u)</option>
              <option value="magnet_normal">📼 仅普通磁力 (magnet_normal)</option>
            </select>
          </div>

          <!-- 定时 Cron 触发规则 -->
          <div>
            <label class="block font-bold text-slate-200 mb-1.5">定时调度规则 (Cron Schedule)</label>
            <div class="grid grid-cols-2 gap-2 mb-2">
              <button 
                v-for="preset in cronPresets" 
                :key="preset.expr"
                @click="form.cronExpression = preset.expr"
                :class="[
                  'p-2 rounded-xl border text-xs font-mono font-bold transition text-center cursor-pointer',
                  form.cronExpression === preset.expr ? 'bg-emerald-600/30 border-emerald-500 text-emerald-300' : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                ]"
              >
                {{ preset.label }}
              </button>
            </div>
            <input 
              v-model="form.cronExpression" 
              type="text" 
              placeholder="Cron 表达式，如 0 4 * * *"
              class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none font-mono text-xs"
            />
          </div>

          <!-- 触发控制与任务提交选项 -->
          <div class="space-y-3 pt-1">
            <label class="flex items-center space-x-2.5 p-3 rounded-2xl bg-slate-950/80 border border-slate-800/80 cursor-pointer">
              <input 
                v-model="form.runNow" 
                type="checkbox" 
                class="rounded accent-emerald-500 w-4 h-4 cursor-pointer"
              />
              <span class="font-bold text-slate-200">创建定时任务后，立即在后台手动触发运行一次 (Run Now)</span>
            </label>
          </div>

        </div>

        <!-- Footer Actions -->
        <div class="flex items-center justify-between border-t border-slate-800/80 pt-3 relative z-10">
          <button 
            @click="$emit('close')" 
            class="px-4 py-2.5 rounded-2xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold transition text-xs cursor-pointer"
          >
            取消
          </button>

          <button 
            @click="submitForm"
            :disabled="submitting || isSubmitDisabled"
            class="px-6 py-2.5 rounded-2xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 active:scale-95 text-white font-extrabold transition text-xs shadow-lg shadow-indigo-600/25 flex items-center space-x-2 disabled:opacity-50 cursor-pointer"
          >
            <RefreshCw v-if="submitting" class="w-4 h-4 animate-spin" />
            <CloudDownload v-else class="w-4 h-4" />
            <span>{{ submitting ? '正在创建...' : submitButtonText }}</span>
          </button>
        </div>

      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { Clock, X, User, Folder, Calendar, Sparkles, CloudDownload, RefreshCw } from '@lucide/vue';
import api, { formatApiError } from '../api';

const props = defineProps({
  initialTargetMode: { type: String, default: 'actor' }, // 'actor', 'list', 'time_range', 'smart_all'
  lockTargetMode: { type: Boolean, default: false }
});

const emit = defineEmits(['close', 'created']);

const submitting = ref(false);

const targetModes = [
  { id: 'actor', label: '🎬 指定演员', icon: User },
  { id: 'list', label: '📑 指定清单', icon: Folder },
  { id: 'time_range', label: '🕒 时间增量', icon: Calendar },
  { id: 'smart_all', label: '🌟 全库智能', icon: Sparkles }
];

const cronPresets = [
  { label: '每天 04:00 (推荐)', expr: '0 4 * * *' },
  { label: '每 12 小时执行', expr: '0 */12 * * *' },
  { label: '每周一 03:00', expr: '0 3 * * 1' },
  { label: '每 6 小时执行', expr: '0 */6 * * *' }
];

const form = reactive({
  targetMode: props.initialTargetMode,
  timeRange: 'today',
  magnetType: 'smart_priority',
  cronExpression: '0 4 * * *',
  runNow: true
});

const subscribedActors = ref([]);
const selectedActorNames = reactive(new Set());
const customActorName = ref('');

const userLists = ref([]);
const selectedListIds = reactive(new Set());
const customListIdOrUrl = ref('');

onMounted(() => {
  try {
    const cachedActors = localStorage.getItem('subscribed_actors');
    if (cachedActors) {
      subscribedActors.value = JSON.parse(cachedActors);
    }
  } catch (e) {}

  try {
    const cachedLists = localStorage.getItem('user_lists');
    if (cachedLists) {
      userLists.value = JSON.parse(cachedLists);
    }
  } catch (e) {}
});

const modalTitle = computed(() => {
  if (form.targetMode === 'actor') return '🎬 演员 115 离线任务规则与 Cron 定时配置';
  if (form.targetMode === 'list') return '📑 清单 115 离线任务规则与 Cron 定时配置';
  if (form.targetMode === 'time_range') return '🕒 时间增量 115 离线任务规则配置';
  return '🌟 115 离线任务规则与 Cron 定时配置';
});

// Effective selected actor names
const effectiveActorNames = computed(() => {
  const list = Array.from(selectedActorNames);
  if (!list.length && customActorName.value.trim()) {
    list.push(customActorName.value.trim());
  }
  return list;
});

// Effective selected list IDs
const effectiveListIds = computed(() => {
  const list = Array.from(selectedListIds);
  if (!list.length && customListIdOrUrl.value.trim()) {
    list.push(customListIdOrUrl.value.trim());
  }
  return list;
});

function toggleActorSelect(name) {
  if (selectedActorNames.has(name)) selectedActorNames.delete(name);
  else selectedActorNames.add(name);
}

function toggleSelectAllActors() {
  if (selectedActorNames.size === subscribedActors.value.length) {
    selectedActorNames.clear();
  } else {
    subscribedActors.value.forEach(a => {
      const name = a.name || a.actor_name;
      if (name) selectedActorNames.add(name);
    });
  }
}

function toggleListSelect(id) {
  if (selectedListIds.has(id)) selectedListIds.delete(id);
  else selectedListIds.add(id);
}

function toggleSelectAllLists() {
  if (selectedListIds.size === userLists.value.length) {
    selectedListIds.clear();
  } else {
    userLists.value.forEach(l => {
      const id = l.list_id || l.id || (l.url ? l.url.split('/').pop() : null);
      if (id) selectedListIds.add(id);
    });
  }
}

const isSubmitDisabled = computed(() => {
  if (form.targetMode === 'actor' && !effectiveActorNames.value.length) return true;
  if (form.targetMode === 'list' && !effectiveListIds.value.length) return true;
  return false;
});

const submitButtonText = computed(() => {
  if (form.targetMode === 'actor') {
    const count = effectiveActorNames.value.length;
    return count > 1 ? `🚀 为 ${count} 位演员创建 115 离线定时任务` : '🚀 保存并创建【演员 115 离线定时任务】';
  }
  if (form.targetMode === 'list') {
    const count = effectiveListIds.value.length;
    return count > 1 ? `🚀 为 ${count} 个清单创建 115 离线定时任务` : '🚀 保存并创建【清单 115 离线定时任务】';
  }
  return '🚀 保存并创建 115 离线定时任务';
});

function getMagnetTypeName(type) {
  const map = {
    'smart_priority': '智能升阶优先',
    'magnet_uc': '无码中字',
    'magnet_4k': '4K超清',
    'magnet_c': '有码中字',
    'magnet_u': '无码高清',
    'magnet_normal': '普通磁力'
  };
  return map[type] || type;
}

function selectTargetMode(modeId) {
  if (props.lockTargetMode) return;
  form.targetMode = modeId;
}

async function submitForm() {
  submitting.value = true;
  try {
    if (form.targetMode === 'actor') {
      const actorList = effectiveActorNames.value;
      let createdCount = 0;
      for (const actorName of actorList) {
        const jobId = `cron_push_actor_${Date.now()}_${Math.floor(Math.random()*1000)}`;
        const taskName = `115 离线 - 演员 [${actorName}] (${getMagnetTypeName(form.magnetType)})`;
        const payload = {
          job_id: jobId,
          job_type: 'transfer_push_actor',
          cron_expression: form.cronExpression,
          magnet_type: form.magnetType,
          actor_name: actorName,
          task_name: taskName,
          run_now: form.runNow
        };
        await api.post('/schedule/add-cron', payload);
        createdCount++;
      }
      window.$toast?.(`成功为 ${createdCount} 位演员创建 115 离线定时任务！`, 'success', '定时任务已创建');
    } else if (form.targetMode === 'list') {
      const listList = effectiveListIds.value;
      let createdCount = 0;
      for (const listId of listList) {
        const jobId = `cron_push_list_${Date.now()}_${Math.floor(Math.random()*1000)}`;
        const taskName = `115 离线 - 清单 [${listId}] (${getMagnetTypeName(form.magnetType)})`;
        const payload = {
          job_id: jobId,
          job_type: 'transfer_push_list',
          cron_expression: form.cronExpression,
          magnet_type: form.magnetType,
          list_id_or_url: listId,
          task_name: taskName,
          run_now: form.runNow
        };
        await api.post('/schedule/add-cron', payload);
        createdCount++;
      }
      window.$toast?.(`成功为 ${createdCount} 个清单创建 115 离线定时任务！`, 'success', '定时任务已创建');
    } else {
      const jobId = `cron_push_${form.targetMode}_${Date.now()}`;
      const taskName = form.targetMode === 'time_range' ? `115 离线 - 时间增量 [${form.timeRange}]` : `115 离线 - 全库智能离线`;
      const payload = {
        job_id: jobId,
        job_type: 'transfer_push',
        cron_expression: form.cronExpression,
        magnet_type: form.magnetType,
        time_range: form.targetMode === 'time_range' ? form.timeRange : undefined,
        task_name: taskName,
        run_now: form.runNow
      };
      await api.post('/schedule/add-cron', payload);
      window.$toast?.(`定时任务 [${taskName}] 创建成功！`, 'success');
    }

    emit('created');
    emit('close');
  } catch (err) {
    window.$toast?.('创建定时任务失败: ' + formatApiError(err), 'error');
  } finally {
    submitting.value = false;
  }
}
</script>
