<template>
  <div class="space-y-6 animate-fade-in">
    
    <!-- Top Modern Glassmorphism Header -->
    <div class="bg-gradient-to-r from-slate-900/95 via-indigo-950/40 to-slate-900/95 backdrop-blur-xl p-5 sm:p-6 rounded-3xl border border-slate-800/80 shadow-2xl flex flex-col xl:flex-row xl:items-center justify-between gap-5 relative overflow-hidden">
      <!-- Ambient Backlight -->
      <div class="absolute -top-16 -left-16 w-56 h-56 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>
      <div class="absolute -bottom-16 -right-16 w-56 h-56 bg-purple-500/10 rounded-full blur-3xl pointer-events-none"></div>

      <div class="relative z-10 space-y-1.5 min-w-0">
        <h2 class="text-lg sm:text-xl font-extrabold text-slate-100 flex items-center space-x-3 tracking-tight">
          <div class="p-2.5 rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shadow-inner shrink-0">
            <Clock class="w-5 h-5" />
          </div>
          <span>JavDB 定时任务</span>
        </h2>
        <p class="text-xs text-slate-400 leading-relaxed">
          后台 Cron 表达式自动化巡检与增量抓取调度器，支持实时运行状态显示、独立执行日志与手动触发
        </p>
      </div>

      <div class="relative z-10 flex items-center space-x-3 shrink-0 flex-wrap gap-2">
        <!-- 演员一条龙预设按钮 -->
        <button 
          @click="openPipelineModal('actors')" 
          class="px-3.5 py-2 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 active:scale-95 text-white font-extrabold rounded-2xl text-xs shadow-lg shadow-orange-500/25 transition-all duration-300 flex items-center space-x-1.5 cursor-pointer"
        >
          <Sparkles class="w-4 h-4" />
          <span>演员一条龙</span>
        </button>

        <!-- 📋 清单一条龙预设按钮 -->
        <button 
          @click="openPipelineModal('lists')" 
          class="px-3.5 py-2 bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 active:scale-95 text-white font-extrabold rounded-2xl text-xs shadow-lg shadow-emerald-600/25 transition-all duration-300 flex items-center space-x-1.5 cursor-pointer"
        >
          <Sparkles class="w-4 h-4" />
          <span>清单一条龙 (排除预设)</span>
        </button>

        <!-- 📦 115 离线自动推送预设按钮 -->
        <button 
          @click="openPipelineModal('transfer_push')" 
          class="px-3.5 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 active:scale-95 text-white font-extrabold rounded-2xl text-xs shadow-lg shadow-blue-600/25 transition-all duration-300 flex items-center space-x-1.5 cursor-pointer"
        >
          <CloudDownload class="w-4 h-4" />
          <span>115 离线自动推送</span>
        </button>

        <button 
          @click="openAddModal" 
          class="px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 active:scale-95 text-white font-bold rounded-2xl text-xs shadow-lg shadow-indigo-600/25 transition-all duration-300 flex items-center space-x-1.5 cursor-pointer"
        >
          <Plus class="w-4 h-4" />
          <span>新建定时任务</span>
        </button>

        <button 
          @click="showPushModal = true" 
          class="px-4 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 active:scale-95 text-white font-extrabold rounded-2xl text-xs shadow-lg shadow-emerald-600/25 transition-all duration-300 flex items-center space-x-1.5 cursor-pointer"
        >
          <CloudDownload class="w-4 h-4" />
          <span>配置 115 离线规则任务</span>
        </button>

        <button 
          @click="fetchJobs(false)" 
          :disabled="loading"
          title="刷新定时任务列表"
          class="p-2.5 bg-slate-800 hover:bg-slate-700 active:scale-95 disabled:opacity-50 text-slate-300 rounded-2xl border border-slate-700/60 transition-all duration-300 cursor-pointer flex items-center justify-center shadow-md"
        >
          <RefreshCw :class="['w-4 h-4 transition-transform duration-300', loading ? 'animate-spin text-indigo-400' : '']" />
        </button>
      </div>
    </div>

    <!-- Loading State with Spinner & Skeleton Placeholders -->
    <div v-if="loading && !jobs.length" class="space-y-4 animate-fade-in">
      <div class="bg-slate-900/60 p-12 rounded-3xl border border-slate-800/80 text-center space-y-3 shadow-xl backdrop-blur-md">
        <div class="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mx-auto shadow-inner">
          <RefreshCw class="w-6 h-6 text-indigo-400 animate-spin" />
        </div>
        <p class="text-xs font-bold text-slate-300">正在获取 Cron 定时调度任务列表...</p>
      </div>
      
      <!-- Skeleton Rows -->
      <div class="bg-slate-900/90 rounded-3xl border border-slate-800/90 shadow-2xl p-4 space-y-3">
        <div v-for="n in 3" :key="n" class="h-16 bg-slate-800/40 rounded-2xl animate-pulse"></div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="!jobs.length" class="bg-slate-900/60 p-12 rounded-3xl border border-slate-800/80 text-center space-y-3 shadow-xl backdrop-blur-md">
      <Clock class="w-10 h-10 text-slate-500 mx-auto" />
      <p class="text-xs font-bold text-slate-300">目前暂无持久化的 Cron 定时任务</p>
      <p class="text-[11px] text-slate-400">可以点击上方快捷按钮创建【演员一条龙】、【清单一条龙】、【115 离线自动推送】或【新建定时任务】</p>
    </div>

    <!-- Job Table -->
    <div v-else class="bg-slate-900/90 backdrop-blur-xl rounded-3xl border border-slate-800/90 shadow-2xl overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs border-collapse min-w-[700px]">
        <thead class="bg-slate-950/80 text-slate-400 uppercase border-b border-slate-800/80 font-mono">
          <tr>
            <th class="p-4 font-bold">任务 ID / 名称</th>
            <th class="p-4 font-bold">Cron 表达式</th>
            <th class="p-4 font-bold">下次执行时间</th>
            <th class="p-4 font-bold">运行状态</th>
            <th class="p-4 font-bold">关联配置</th>
            <th class="p-4 font-bold text-right">操作</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-800/80 text-slate-300 font-mono">
          <tr v-for="job in jobs" :key="job.job_id" class="hover:bg-slate-800/40 transition-colors">
            <td class="p-4">
              <div class="font-extrabold text-slate-100 font-sans text-xs flex items-center space-x-2">
                <span>{{ job.meta?.task_name || job.job_id }}</span>
                <span v-if="job.meta?.job_type === 'actors_pipeline'" class="px-2 py-0.5 rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] font-bold">演员一条龙</span>
                <span v-if="job.meta?.job_type === 'lists_pipeline'" class="px-2 py-0.5 rounded-lg bg-teal-500/20 text-teal-300 border border-teal-500/30 text-[10px] font-bold">清单一条龙</span>
                <span v-if="job.meta?.job_type === 'transfer_push'" class="px-2 py-0.5 rounded-lg bg-blue-500/20 text-blue-300 border border-blue-500/30 text-[10px] font-bold">115自动推送+同步</span>
              </div>
              <div class="text-[10px] text-slate-500 font-mono mt-0.5">{{ job.job_id }}</div>
            </td>
            <td class="p-4 text-indigo-400 font-bold font-mono">{{ job.meta?.cron_expression || '-' }}</td>
            <td class="p-4 text-slate-400 text-[11px]">{{ formatTime(job.next_run_time) }}</td>
            <td class="p-4">
              <!-- 运行状态：正在运行 vs 未运行 -->
              <span v-if="job.status === 'running'" class="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-extrabold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm animate-pulse">
                <Loader2 class="w-3.5 h-3.5 animate-spin text-emerald-400 shrink-0" />
                <span>正在运行</span>
              </span>
              <span v-else-if="job.status === 'cancelling'" class="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40 opacity-80">
                <Loader2 class="w-3.5 h-3.5 animate-spin text-rose-400 shrink-0" />
                <span>正在停止</span>
              </span>
              <span v-else class="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-800/80 text-slate-400 border border-slate-700/60">
                <span class="w-2 h-2 rounded-full bg-slate-500 shrink-0"></span>
                <span>未运行</span>
              </span>
            </td>
            <td class="p-4 text-slate-400 text-[11px]">
              <div v-if="job.meta?.job_type === 'transfer_push'" class="text-sky-300 font-bold">
                范围: {{ timeRangeLabel(job.meta?.time_range) }} | 自动同步真实状态
              </div>
              <div v-else-if="job.meta?.target_urls?.length" class="text-indigo-300 font-bold">
                📦 组合 (含 {{ job.meta.target_urls.length }} 项)
              </div>
              <div v-else-if="job.meta?.job_type" class="text-emerald-400 font-bold">
                抓取更新元数据入库
              </div>
              <div v-else class="truncate max-w-xs" :title="job.meta?.target_url">
                {{ job.meta?.target_url || '-' }}
              </div>
            </td>
            <td class="p-4 text-right shrink-0 whitespace-nowrap">
              <div class="inline-flex items-center space-x-1.5">
                <!-- 查看独立控制台日志 -->
                <button 
                  @click="openJobLogs(job)"
                  class="w-8 h-8 p-0 bg-slate-800 hover:bg-slate-700 active:scale-95 text-indigo-300 hover:text-white border border-slate-700/80 rounded-xl transition-all duration-200 inline-flex items-center justify-center cursor-pointer shrink-0 shadow-sm"
                  title="查看此任务独占运行日志"
                >
                  <FileText class="w-4 h-4" />
                </button>

                <!-- 动态运行/停止按钮 -->
                <button 
                  v-if="job.status === 'running'"
                  @click="stopJob(job.job_id)" 
                  class="w-8 h-8 p-0 bg-rose-500/20 hover:bg-rose-600 text-rose-300 hover:text-white border border-rose-500/40 rounded-xl transition-all duration-200 inline-flex items-center justify-center cursor-pointer animate-pulse shrink-0 shadow-sm"
                  title="点击立刻终止此正在运行中的任务"
                >
                  <Square class="w-3.5 h-3.5 fill-current" />
                </button>

                <button 
                  v-else-if="job.status === 'cancelling'"
                  disabled
                  class="w-8 h-8 p-0 bg-rose-500/10 text-rose-400/60 border border-rose-500/20 rounded-xl inline-flex items-center justify-center opacity-60 cursor-not-allowed shrink-0"
                  title="正在强行终止中..."
                >
                  <Loader2 class="w-4 h-4 animate-spin text-rose-400" />
                </button>

                <button 
                  v-else
                  @click="triggerJob(job.job_id)" 
                  :disabled="runningJobId === job.job_id"
                  class="w-8 h-8 p-0 bg-emerald-500/10 hover:bg-emerald-600 text-emerald-300 hover:text-white border border-emerald-500/30 rounded-xl transition-all duration-200 inline-flex items-center justify-center cursor-pointer shrink-0 disabled:opacity-50 shadow-sm"
                  title="手动触发立即运行此任务"
                >
                  <Play :class="['w-4 h-4 ml-0.5', runningJobId === job.job_id ? 'animate-spin' : '']" />
                </button>

                <!-- 编辑按钮 -->
                <button 
                  @click="editJob(job)" 
                  class="w-8 h-8 p-0 bg-amber-500/10 hover:bg-amber-600 text-amber-300 hover:text-white border border-amber-500/30 rounded-xl transition-all duration-200 inline-flex items-center justify-center cursor-pointer shrink-0 shadow-sm"
                  title="编辑此定时任务参数配置"
                >
                  <Pencil class="w-4 h-4" />
                </button>

                <!-- 删除按钮 -->
                <button 
                  @click="deleteJob(job.job_id)" 
                  class="w-8 h-8 p-0 bg-rose-500/10 hover:bg-rose-600 text-rose-400 hover:text-white border border-rose-500/30 rounded-xl transition-all duration-200 inline-flex items-center justify-center cursor-pointer shrink-0 shadow-sm"
                  title="删除此定时任务"
                >
                  <Trash2 class="w-4 h-4" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      </div>
    </div>

    <!-- 独占任务日志 Modal (Teleport to Body) -->
    <Teleport to="body">
      <div v-if="activeLogJobId" class="fixed inset-0 z-[9999] bg-slate-950/85 backdrop-blur-md flex items-center justify-center p-4 sm:p-6 animate-fade-in">
        <div class="bg-slate-900 border border-slate-800/90 rounded-3xl p-6 w-full max-w-3xl max-h-[85vh] shadow-2xl flex flex-col space-y-4 animate-scale-up relative">
          
          <!-- Modal Header -->
          <div class="flex items-center justify-between border-b border-slate-800/80 pb-3 shrink-0">
            <div class="flex items-center space-x-2.5">
              <div class="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                <Terminal class="w-4 h-4" />
              </div>
              <div>
                <h3 class="text-sm font-extrabold text-slate-100 flex items-center space-x-2">
                  <span>{{ activeLogJobName }}</span>
                </h3>
                <p class="text-[10px] font-mono text-slate-400">ID: {{ activeLogJobId }}</p>
              </div>
            </div>

            <div class="flex items-center space-x-2">
              <button 
                @click="fetchTaskLogs(activeLogJobId)" 
                :disabled="logLoading"
                class="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-300 transition-all duration-300 cursor-pointer"
                title="刷新实时日志"
              >
                <RefreshCw :class="['w-4 h-4', logLoading ? 'animate-spin text-indigo-400' : '']" />
              </button>
              <button 
                @click="closeJobLogs" 
                class="p-2 rounded-xl hover:bg-slate-800 text-slate-400 hover:text-white transition-all duration-300 cursor-pointer"
              >
                <X class="w-5 h-5" />
              </button>
            </div>
          </div>

          <!-- Terminal Window -->
          <div ref="taskLogTerminalRef" class="bg-slate-950 rounded-2xl p-4 border border-slate-800/80 font-mono text-xs text-slate-300 flex-1 min-h-0 overflow-y-auto space-y-1.5 shadow-inner select-text">
            <div v-if="!activeJobLogs.length" class="text-slate-500 italic py-16 text-center">
              暂无此定时任务的执行日志记录...
            </div>
            <div 
              v-for="(line, idx) in activeJobLogs" 
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
          <div class="flex items-center justify-between pt-2 border-t border-slate-800/80 shrink-0">
            <span class="text-[11px] text-slate-400 font-mono">已记录 {{ activeJobLogs.length }} 条独占日志</span>
            <div class="flex items-center space-x-2">
              <button 
                @click="copyTaskLogs" 
                class="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-2xl text-xs font-bold transition-all duration-300 flex items-center space-x-1.5 cursor-pointer"
              >
                <Copy class="w-3.5 h-3.5 text-indigo-400" />
                <span>复制日志</span>
              </button>
              <button 
                @click="closeJobLogs" 
                class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-2xl text-xs font-extrabold shadow-md transition-all duration-300 cursor-pointer"
              >
                关闭
              </button>
            </div>
          </div>

        </div>
      </div>
    </Teleport>

    <!-- Modal: 🚀 一条龙 / 115 离线自动化配置 Modal (Teleport to Body) -->
    <Teleport to="body">
      <div v-if="showPipelineModal" class="fixed inset-0 z-[9999] bg-slate-950/85 backdrop-blur-md flex items-center justify-center p-4 sm:p-6 animate-fade-in">
        <div class="bg-slate-900 border border-slate-800/90 rounded-3xl p-6 w-full max-w-md max-h-[85vh] overflow-y-auto shadow-2xl space-y-4 animate-scale-up relative my-auto">
          <h3 class="text-base font-extrabold text-slate-100 flex items-center space-x-2">
            <Sparkles v-if="pipelineType !== 'transfer_push'" class="w-5 h-5 text-amber-400" />
            <CloudDownload v-else class="w-5 h-5 text-blue-400" />
            <span>配置【{{ pipelineTitle }}】自动化任务</span>
          </h3>

          <div class="space-y-3.5 text-xs">
            
            <!-- 115 离线推送专属配置: 时间范围手动选择 -->
            <template v-if="pipelineType === 'transfer_push'">
              <div>
                <label class="block text-slate-300 font-bold mb-1.5">离线推送的时间范围 (可手动选择)</label>
                <select v-model="pipelineForm.time_range" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none font-bold">
                  <option value="today">今天抓取的影片 (推荐)</option>
                  <option value="last_24h">最近 24 小时内抓取</option>
                  <option value="last_3d">最近 3 天内抓取</option>
                  <option value="last_7d">最近 7 天内抓取</option>
                  <option value="all">数据库历史全量记录</option>
                </select>
              </div>

              <div>
                <label class="block text-slate-300 font-bold mb-1.5">磁力下载类型 / 推送策略</label>
                <select v-model="pipelineForm.magnet_type" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none font-bold">
                  <option value="smart_priority">⚡ UC > 4K > C 智能升阶推送 (推荐)</option>
                  <option value="magnet_uc">仅推送无码中字/破解 (UC)</option>
                  <option value="magnet_4k">仅推送 4K 超清</option>
                  <option value="magnet_c">仅推送有码中字 (C)</option>
                </select>
              </div>

              <div class="p-3 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-[11px] text-blue-300 leading-relaxed">
                💡 <strong>自动同步保障</strong>：推送至 115 离线完毕后，系统将<strong>自动调用 115 API</strong> 对齐本地与 115 的真实下载状态！
              </div>
            </template>

            <!-- 演员 / 清单一条龙抓取配置 -->
            <template v-else>
              <div>
                <label class="block text-slate-300 font-bold mb-1.5">抓取更新模式 (可根据需求选择)</label>
                <div class="space-y-2">
                  <label class="flex items-center space-x-2 p-2.5 rounded-2xl bg-slate-950 border border-slate-800 hover:border-indigo-500/50 cursor-pointer transition">
                    <input type="radio" v-model="pipelineForm.mode" value="smart" class="accent-indigo-500" />
                    <div>
                      <span class="font-bold text-indigo-300">⚡ 智能增量更新 (推荐)</span>
                      <p class="text-[10px] text-slate-400">仅探寻最新页，遇到已抓取的历史记录自动停止，高效省资源</p>
                    </div>
                  </label>
                  
                  <label class="flex items-center space-x-2 p-2.5 rounded-2xl bg-slate-950 border border-slate-800 hover:border-indigo-500/50 cursor-pointer transition">
                    <input type="radio" v-model="pipelineForm.mode" value="full" class="accent-indigo-500" />
                    <div>
                      <span class="font-bold text-emerald-300">🌐 全量翻页扫盘</span>
                      <p class="text-[10px] text-slate-400">强制遍历历史翻页，适合首次全量建立本地数据库与补齐遗漏影片</p>
                    </div>
                  </label>
                </div>
              </div>

              <div>
                <label class="block text-slate-300 font-bold mb-1.5">最大翻页上限 (max_pages)</label>
                <select v-model.number="pipelineForm.max_pages" class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none font-bold">
                  <option :value="1">1 页 (快速巡检 推荐)</option>
                  <option :value="3">3 页 (深度巡检)</option>
                  <option :value="5">5 页</option>
                  <option :value="999">999 页 (全量翻页不限)</option>
                </select>
              </div>
            </template>

            <!-- 定时触发时间规则 -->
            <div>
              <label class="block text-slate-300 font-bold mb-1.5">定时触发时间规则 (Cron)</label>
              <div class="grid grid-cols-2 gap-2 mb-2">
                <button 
                  v-for="preset in cronPresets" 
                  :key="preset.expr"
                  @click="pipelineForm.cron_expression = preset.expr"
                  :class="[
                    'p-2 rounded-xl border text-xs font-mono font-bold transition text-center cursor-pointer',
                    pipelineForm.cron_expression === preset.expr ? 'bg-amber-600/30 border-amber-500 text-amber-300' : 'bg-slate-950 border-slate-800 text-slate-400'
                  ]"
                >
                  {{ preset.label }}
                </button>
              </div>
              <input 
                v-model="pipelineForm.cron_expression" 
                type="text" 
                placeholder="Cron 表达式，如 0 3 * * *"
                class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none font-mono text-xs"
              />
            </div>
          </div>

          <div class="flex justify-end space-x-3 pt-3 border-t border-slate-800/80">
            <button 
              @click="showPipelineModal = false" 
              class="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-2xl text-xs font-bold transition cursor-pointer"
            >
              取消
            </button>
            <button 
              @click="submitPipelineTask" 
              :disabled="submittingPipeline"
              class="px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-extrabold text-xs rounded-2xl shadow-lg shadow-indigo-600/25 transition disabled:opacity-50 cursor-pointer flex items-center space-x-1.5"
            >
              <RefreshCw v-if="submittingPipeline" class="w-4 h-4 animate-spin" />
              <span>{{ submittingPipeline ? (editingJobId ? '正在保存...' : '正在创建...') : (editingJobId ? '更新保存配置' : '保存并启动自动化任务') }}</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Normal Create / Edit Modal (Teleport to Body) -->
    <Teleport to="body">
      <div v-if="showAddModal" class="fixed inset-0 z-[9999] bg-slate-950/85 backdrop-blur-md flex items-center justify-center p-4 sm:p-6 animate-fade-in">
        <div class="bg-slate-900 border border-slate-800/90 rounded-3xl p-6 w-full max-w-md max-h-[85vh] overflow-y-auto shadow-2xl space-y-4 animate-scale-up relative my-auto">
          <h3 class="text-base font-extrabold text-slate-100 flex items-center space-x-2">
            <Clock class="w-5 h-5 text-indigo-400" />
            <span>{{ editingJobId ? '编辑 Cron 定时任务' : '新建 Cron 定时任务' }}</span>
          </h3>

          <div class="space-y-3 text-xs">
            <div>
              <label class="block text-slate-300 font-bold mb-1">任务友好名称</label>
              <input 
                v-model="newJob.task_name" 
                type="text" 
                placeholder="如：演员 [三上悠亚] - 定时智能增量"
                class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none transition-all duration-200"
              />
            </div>
            <div>
              <label class="block text-slate-300 font-bold mb-1">
                <span>任务 ID (唯一标识)</span>
                <span v-if="editingJobId" class="text-amber-400 font-normal text-[10px] ml-1.5">(编辑状态下不可修改)</span>
              </label>
              <input 
                v-model="newJob.job_id" 
                :disabled="!!editingJobId"
                type="text" 
                placeholder="如 scrape_yua_daily"
                class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none font-mono transition-all duration-200 disabled:opacity-60 disabled:bg-slate-900"
              />
            </div>
            <div>
              <label class="block text-slate-300 font-bold mb-1">抓取目标 URL</label>
              <input 
                v-model="newJob.target_url" 
                type="text" 
                placeholder="https://javdb.com/actors/d4ndM"
                class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none font-mono transition-all duration-200"
              />
            </div>
            <div>
              <label class="block text-slate-300 font-bold mb-1">Cron 表达式 (分 时 日 月 周)</label>
              <input 
                v-model="newJob.cron_expression" 
                type="text" 
                placeholder="0 3 * * * (每天凌晨3点)"
                class="w-full bg-slate-950 border border-slate-800 rounded-2xl p-3 text-slate-200 focus:border-indigo-500 outline-none font-mono transition-all duration-200"
              />
            </div>
          </div>

          <div class="flex justify-end space-x-3 pt-2">
            <button 
              @click="showAddModal = false" 
              class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-2xl text-xs font-bold transition-all duration-300 cursor-pointer"
            >
              取消
            </button>
            <button 
              @click="createJob" 
              class="px-5 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-2xl text-xs font-extrabold shadow-lg shadow-indigo-600/25 transition-all duration-300 cursor-pointer"
            >
              {{ editingJobId ? '更新保存配置' : '保存并启动' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Push Task Rule & Cron Modal -->
    <PushTaskModal 
      v-if="showPushModal"
      :initial-target-mode="'actor'"
      @close="showPushModal = false"
      @created="fetchJobs(false)"
    />

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { Clock, Plus, RefreshCw, Play, Square, Pencil, Trash2, FileText, Terminal, X, Copy, Loader2, CheckCircle2, Sparkles, CloudDownload } from '@lucide/vue';
import api, { formatApiError } from '../api';
import PushTaskModal from '../components/PushTaskModal.vue';

const jobs = ref([]);
const loading = ref(false);
const showAddModal = ref(false);
const showPushModal = ref(false);
const runningJobId = ref('');
let pollTimer = null;

// 自动化任务配置模态框状态
const showPipelineModal = ref(false);
const pipelineType = ref('actors'); // 'actors', 'lists', or 'transfer_push'
const pipelineTitle = ref('');
const submittingPipeline = ref(false);

const pipelineForm = ref({
  mode: 'smart', // 'smart' or 'full'
  max_pages: 1,
  time_range: 'today', // 'today', 'last_24h', 'last_3d', 'last_7d', 'all'
  magnet_type: 'smart_priority', // 'smart_priority', 'magnet_uc', 'magnet_4k', 'magnet_c'
  cron_expression: '0 3 * * *'
});

// 独占任务日志 Modal 状态
const activeLogJobId = ref(null);
const activeLogJobName = ref('');
const activeJobLogs = ref([]);
const logLoading = ref(false);

const cronPresets = [
  { label: '每天 03:00 (推荐)', expr: '0 3 * * *' },
  { label: '每天 00:00', expr: '0 0 * * *' },
  { label: '每 12 小时', expr: '0 */12 * * *' },
  { label: '每 6 小时', expr: '0 */6 * * *' }
];

const editingJobId = ref(null);

const newJob = ref({
  job_id: '',
  task_name: '',
  target_url: '',
  cron_expression: '0 3 * * *',
  smart_incremental: true
});

onMounted(() => {
  fetchJobs();
  pollTimer = setInterval(() => {
    fetchJobs(true);
  }, 3000);
});

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer);
});

function timeRangeLabel(val) {
  const map = {
    today: '今天抓取',
    last_24h: '最近 24 小时',
    last_3d: '最近 3 天',
    last_7d: '最近 7 天',
    all: '数据库全量历史'
  };
  return map[val] || val || '今天抓取';
}

function openPipelineModal(type) {
  editingJobId.value = null;
  pipelineType.value = type;
  if (type === 'actors') pipelineTitle.value = '订阅演员一条龙';
  else if (type === 'lists') pipelineTitle.value = '收藏清单一条龙 (排除预设)';
  else if (type === 'transfer_push') pipelineTitle.value = '115 离线自动推送';

  pipelineForm.value = {
    mode: 'smart',
    max_pages: 1,
    time_range: 'today',
    magnet_type: 'smart_priority',
    cron_expression: '0 3 * * *'
  };
  
  showPipelineModal.value = true;
}

function openAddModal() {
  editingJobId.value = null;
  newJob.value = {
    job_id: '',
    task_name: '',
    target_url: '',
    cron_expression: '0 3 * * *',
    smart_incremental: true
  };
  showAddModal.value = true;
}

function editJob(job) {
  const meta = job.meta || {};
  const jobType = meta.job_type;
  editingJobId.value = job.job_id;

  if (jobType === 'actors_pipeline' || jobType === 'lists_pipeline' || jobType === 'transfer_push') {
    pipelineType.value = jobType === 'transfer_push' ? 'transfer_push' : (jobType === 'actors_pipeline' ? 'actors' : 'lists');
    if (pipelineType.value === 'actors') pipelineTitle.value = '编辑订阅演员一条龙';
    else if (pipelineType.value === 'lists') pipelineTitle.value = '编辑收藏清单一条龙 (排除预设)';
    else if (pipelineType.value === 'transfer_push') pipelineTitle.value = '编辑 115 离线自动推送';

    pipelineForm.value = {
      mode: meta.smart_incremental ? 'smart' : 'full',
      max_pages: meta.max_pages || 1,
      time_range: meta.time_range || 'today',
      magnet_type: meta.magnet_type || 'smart_priority',
      cron_expression: meta.cron_expression || '0 3 * * *'
    };
    showPipelineModal.value = true;
  } else {
    newJob.value = {
      job_id: job.job_id,
      task_name: meta.task_name || job.job_id,
      target_url: meta.target_url || '',
      cron_expression: meta.cron_expression || '0 3 * * *',
      smart_incremental: meta.smart_incremental !== false
    };
    showAddModal.value = true;
  }
}

async function submitPipelineTask() {
  submittingPipeline.value = true;
  const type = pipelineType.value;
  const isSmart = pipelineForm.value.mode === 'smart';
  const modeStr = isSmart ? '智能增量' : '全量翻页';
  
  let taskName = '';
  let jobId = editingJobId.value;

  if (type === 'transfer_push') {
    const rangeText = timeRangeLabel(pipelineForm.value.time_range);
    taskName = `115 离线自动推送 [时间段: ${rangeText} | 自动对齐115真实状态]`;
    if (!jobId) jobId = `transfer_push_cron_${Date.now().toString(36)}`;
  } else {
    const titleMap = {
      actors: `全量订阅演员一条龙 [${modeStr} | 抓取元数据入库]`,
      lists: `全量收藏清单一条龙 [${modeStr} | 排除预设 | 抓取元数据入库]`
    };
    taskName = titleMap[type] || `一条龙任务`;
    if (!jobId) jobId = `${type}_pipeline_${Date.now().toString(36)}`;
  }

  try {
    const res = await api.post('/schedule/add-cron', {
      job_id: jobId,
      job_type: type === 'transfer_push' ? 'transfer_push' : `${type}_pipeline`,
      cron_expression: pipelineForm.value.cron_expression,
      smart_incremental: isSmart,
      max_pages: pipelineForm.value.max_pages,
      time_range: pipelineForm.value.time_range,
      magnet_type: pipelineForm.value.magnet_type,
      task_name: taskName
    });

    if (res.data?.code === 200) {
      const msg = editingJobId.value ? `【${taskName}】更新保存成功！` : `【${taskName}】创建成功！`;
      window.$toast?.(msg, 'success', '任务保存成功');
      showPipelineModal.value = false;
      editingJobId.value = null;
      fetchJobs(false);
    }
  } catch (err) {
    window.$toast?.('保存自动化任务失败: ' + formatApiError(err), 'error');
  } finally {
    submittingPipeline.value = false;
  }
}

async function fetchJobs(isSilent = false) {
  if (!isSilent) loading.value = true;
  const startTime = Date.now();
  try {
    const res = await api.get('/schedule/list');
    if (res.data?.code === 200 && Array.isArray(res.data?.data)) {
      jobs.value = res.data.data;
    }
  } catch (err) {
    console.error('Fetch jobs error', err);
  } finally {
    if (!isSilent) {
      const elapsed = Date.now() - startTime;
      const delay = Math.max(0, 450 - elapsed);
      setTimeout(() => {
        loading.value = false;
      }, delay);
    }
  }
}

async function triggerJob(jobId) {
  runningJobId.value = jobId;
  try {
    const jobObj = jobs.value.find(j => j.job_id === jobId);
    if (jobObj) {
      jobObj.status = 'running';
      jobObj.message = '手动触发运行中...';
    }
    const res = await api.post(`/schedule/trigger/${jobId}`);
    if (res.data?.code === 200) {
      window.$toast?.(`定时任务 [${jobId}] 已触发后台运行！`, 'success', '已触发运行');
    }
  } catch (err) {
    window.$toast?.('触发任务失败: ' + formatApiError(err), 'error');
  } finally {
    setTimeout(() => {
      runningJobId.value = '';
    }, 1200);
  }
}

async function stopJob(jobId) {
  try {
    const res = await api.post(`/schedule/stop/${jobId}`);
    if (res.data?.code === 200) {
      window.$toast?.(`已发送强行终止指令，正在退出...`, 'info', '停止指令已发送');
      const jobObj = jobs.value.find(j => j.job_id === jobId);
      if (jobObj) {
        jobObj.status = 'cancelling';
        jobObj.message = '正在终止程序...';
      }
    }
  } catch (err) {
    window.$toast?.('停止任务失败: ' + formatApiError(err), 'error');
  }
}

let cronModalLogTimer = null;
const taskLogTerminalRef = ref(null);

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer);
  if (cronModalLogTimer) {
    clearInterval(cronModalLogTimer);
    cronModalLogTimer = null;
  }
});

async function openJobLogs(job) {
  activeLogJobId.value = job.job_id;
  activeLogJobName.value = job.meta?.task_name || job.job_id;
  fetchTaskLogs(job.job_id, false);

  if (cronModalLogTimer) clearInterval(cronModalLogTimer);
  cronModalLogTimer = setInterval(() => {
    if (activeLogJobId.value) {
      fetchTaskLogs(activeLogJobId.value, true);
    } else {
      clearInterval(cronModalLogTimer);
      cronModalLogTimer = null;
    }
  }, 1500);
}

function closeJobLogs() {
  activeLogJobId.value = null;
  if (cronModalLogTimer) {
    clearInterval(cronModalLogTimer);
    cronModalLogTimer = null;
  }
}

async function fetchTaskLogs(jobId, silent = false) {
  if (!silent) logLoading.value = true;
  try {
    const res = await api.get(`/schedule/logs/${jobId}?lines=300`);
    if (res.data?.code === 200) {
      activeJobLogs.value = res.data.data?.logs || [];
      nextTick(() => {
        if (taskLogTerminalRef.value) {
          taskLogTerminalRef.value.scrollTop = taskLogTerminalRef.value.scrollHeight;
        }
      });
    }
  } catch (err) {
    console.error('Fetch task logs error', err);
  } finally {
    if (!silent) logLoading.value = false;
  }
}

function copyTaskLogs() {
  if (!activeJobLogs.value.length) return;
  const logText = activeJobLogs.value.join('\n');
  navigator.clipboard.writeText(logText).then(() => {
    window.$toast?.('独占任务日志已复制到剪贴板', 'success');
  }).catch(() => {
    window.$toast?.('复制失败，请手动选取', 'warning');
  });
}

async function createJob() {
  if (!newJob.value.job_id.trim() || !newJob.value.target_url.trim()) {
    window.$toast?.('请填写任务 ID 和目标 URL！', 'warning', '参数不完整');
    return;
  }

  try {
    const res = await api.post('/schedule/add-cron', {
      job_id: newJob.value.job_id.trim(),
      target_url: newJob.value.target_url.trim(),
      cron_expression: newJob.value.cron_expression.trim() || '0 3 * * *',
      task_name: newJob.value.task_name.trim() || undefined
    });

    if (res.data?.code === 200) {
      const msg = editingJobId.value ? '定时任务更新成功！' : '定时任务创建成功！';
      window.$toast?.(msg, 'success');
      showAddModal.value = false;
      editingJobId.value = null;
      newJob.value = { job_id: '', task_name: '', target_url: '', cron_expression: '0 3 * * *', smart_incremental: true };
      fetchJobs(false);
    }
  } catch (err) {
    window.$toast?.('保存定时任务失败: ' + formatApiError(err), 'error');
  }
}

async function deleteJob(jobId) {
  if (!confirm(`确定要删除定时任务 [${jobId}] 吗？`)) return;

  try {
    const res = await api.delete(`/schedule/remove/${jobId}`);
    if (res.data?.code === 200) {
      window.$toast?.('定时任务已删除', 'success');
      fetchJobs(false);
    }
  } catch (err) {
    window.$toast?.('删除任务失败: ' + formatApiError(err), 'error');
  }
}

function formatTime(val) {
  if (!val || val === 'None') return '未调度';
  return String(val).replace('T', ' ').substring(0, 19);
}
</script>
