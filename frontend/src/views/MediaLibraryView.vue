<template>
  <div class="space-y-6 animate-fade-in">
    
    <!-- Top Filter Header -->
    <div class="bg-gradient-to-r from-slate-900/95 via-indigo-950/40 to-slate-900/95 backdrop-blur-xl p-6 rounded-3xl border border-slate-800/80 shadow-2xl space-y-4 relative overflow-hidden">
      <!-- Ambient Backlight -->
      <div class="absolute -top-16 -left-16 w-56 h-56 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>
      <div class="absolute -bottom-16 -right-16 w-56 h-56 bg-purple-500/10 rounded-full blur-3xl pointer-events-none"></div>

      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
        
        <!-- Search Keyword Input -->
        <div class="relative flex-1">
          <Search class="w-4 h-4 text-indigo-400 absolute left-4 top-1/2 -translate-y-1/2 z-10" />
          <input 
            v-model="keyword" 
            @keyup.enter="onSearch"
            type="text" 
            placeholder="搜索番号 (如 SSIS-084)、影片标题、演员或标签关键词..."
            class="w-full bg-slate-950/80 border border-slate-800 rounded-2xl pl-11 pr-10 py-3 text-xs text-slate-200 focus:border-indigo-500 outline-none shadow-inner"
          />
          <!-- Clear Keyword 'X' Button -->
          <button 
            v-if="keyword" 
            type="button"
            @click.stop.prevent="clearKeyword" 
            title="清空关键词并恢复显示全部作品"
            class="absolute right-3.5 top-1/2 -translate-y-1/2 z-20 p-1.5 rounded-full bg-slate-800 hover:bg-rose-600/30 text-slate-400 hover:text-rose-300 border border-slate-700/60 hover:border-rose-500/50 transition active:scale-95 cursor-pointer flex items-center justify-center shadow-md"
          >
            <X class="w-3.5 h-3.5" />
          </button>
        </div>

        <button 
          @click="onSearch" 
          class="px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 active:scale-95 text-white font-bold rounded-2xl text-xs shadow-lg shadow-indigo-600/25 transition flex items-center justify-center space-x-1.5"
        >
          <span>检索媒体库</span>
        </button>
      </div>

      <!-- Tag Category Filter Chips & Clear DB Test Button -->
      <div class="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800/80 text-xs relative z-10">
        <div class="flex flex-wrap items-center gap-2">
          <span class="text-slate-400 text-xs font-semibold mr-1">快捷筛选:</span>
          <button 
            v-for="filter in filters" 
            :key="filter.id"
            @click="selectTagFilter(filter.id)"
            :class="[
              'px-3.5 py-1.5 rounded-xl font-bold transition text-xs border',
              activeTagFilter === filter.id 
                ? 'bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-600/30' 
                : 'bg-slate-950/80 text-slate-400 hover:text-slate-200 border-slate-800/80'
            ]"
          >
            {{ filter.label }}
          </button>
        </div>

        <!-- Action Buttons Right: Export Data -->
        <div class="flex items-center gap-2 shrink-0">
          <button 
            @click="onExportData"
            :disabled="exporting"
            title="导出当前搜索与筛选条件下的全部影片记录为 CSV Excel 文件"
            class="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 active:scale-95 text-white font-bold transition text-xs flex items-center space-x-1.5 shrink-0 shadow-md shadow-emerald-600/20 cursor-pointer disabled:opacity-50"
          >
            <RefreshCw v-if="exporting" class="w-3.5 h-3.5 animate-spin" />
            <Download v-else class="w-3.5 h-3.5" />
            <span>{{ exporting ? '正在导出...' : '导出筛选数据' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="py-20 text-center space-y-3">
      <div class="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mx-auto shadow-inner">
        <RefreshCw class="w-6 h-6 text-indigo-400 animate-spin" />
      </div>
      <p class="text-xs text-slate-400 font-mono">正在检索数据库...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="!movies.length" class="bg-slate-900/60 p-16 rounded-3xl border border-slate-800/80 text-center space-y-3 shadow-xl backdrop-blur-md">
      <div class="w-14 h-14 rounded-2xl bg-slate-800/60 border border-slate-700/50 flex items-center justify-center mx-auto text-slate-500">
        <Film class="w-7 h-7" />
      </div>
      <h3 class="text-base font-bold text-slate-200">未找到符合条件的影片数据</h3>
      <p class="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
        尝试更换搜索关键词，或在控制台中触发番号抓取任务
      </p>
    </div>

    <!-- Movie Card Grid Gallery (放大自适应满行满列 6 列布局，单卡片宽约 285px) -->
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 2xl:grid-cols-6 gap-5 sm:gap-6">
      <MovieCard 
        v-for="movie in movies" 
        :key="movie.code"
        :movie="movie"
        @view-detail="openDetailModal"
        @push-115="onPushSingle"
        @delete-movie="onDeleteMovie"
      />
    </div>

    <!-- Pagination Controls -->
    <div v-if="totalPages > 1" class="flex justify-between items-center bg-slate-900/90 backdrop-blur-xl p-4 rounded-3xl border border-slate-800/90 text-xs shadow-xl">
      <span class="text-slate-400 font-mono font-medium">
        显示第 <strong class="text-slate-200">{{ (page - 1) * limit + 1 }}</strong> - <strong class="text-slate-200">{{ Math.min(page * limit, total) }}</strong> 条 (共 <strong class="text-indigo-400">{{ total }}</strong> 条记录)
      </span>

      <div class="flex items-center space-x-2">
        <button 
          @click="changePage(page - 1)" 
          :disabled="page <= 1"
          class="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 font-bold transition text-xs"
        >
          上一页
        </button>

        <span class="px-3.5 py-1.5 rounded-xl bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-mono font-bold">
          {{ page }} / {{ totalPages }}
        </span>

        <button 
          @click="changePage(page + 1)" 
          :disabled="page >= totalPages"
          class="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 font-bold transition text-xs"
        >
          下一页
        </button>
      </div>
    </div>

    <!-- Movie Detail Modal -->
    <MovieDetailsModal 
      v-if="selectedMovie" 
      :movie="selectedMovie" 
      @close="selectedMovie = null"
      @push-115="onPushSingle"
      @search-keyword="onSearchFromModal"
      @update-movie="onMovieUpdated"
    />

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { Search, Film, RefreshCw, X, Trash2, Download } from '@lucide/vue';
import api, { formatApiError } from '../api';
import MovieCard from '../components/MovieCard.vue';
import MovieDetailsModal from '../components/MovieDetailsModal.vue';

const movies = ref([]);
const total = ref(0);
const page = ref(1);
const totalPages = ref(1);
const limit = ref(24);
const loading = ref(false);
const exporting = ref(false);
const keyword = ref('');
const activeTagFilter = ref('all');
const selectedMovie = ref(null);

const filters = [
  { id: 'all', label: '全部作品' },
  { id: 'pushed', label: '🚀 115已离线' },
  { id: 'unpushed', label: '📥 115未离线' },
  { id: 'pending_detail', label: '🔍 待补充详情' },
  { id: 'uc', label: '无码中字' },
  { id: '4k', label: '4K 超清' },
  { id: 'c', label: '有码中字' },
  { id: 'u', label: '无码高清' },
];

onMounted(() => {
  fetchMovies();
});

async function fetchMovies() {
  loading.value = true;
  try {
    const params = {
      page: page.value,
      limit: limit.value,
      keyword: keyword.value.trim() || undefined,
      tag_filter: activeTagFilter.value !== 'all' ? activeTagFilter.value : undefined
    };
    const res = await api.get('/movies/list', { params });
    if (res.data?.code === 200 && res.data?.data) {
      movies.value = res.data.data.items || [];
      total.value = res.data.data.total || 0;
      totalPages.value = res.data.data.pages || 1;
    }
  } catch (err) {
    console.error('Fetch movies error', err);
    window.$toast?.(formatApiError(err), 'error', '加载媒体库失败');
  } finally {
    loading.value = false;
  }
}

function onSearch() {
  page.value = 1;
  fetchMovies();
}

function clearKeyword() {
  keyword.value = '';
  page.value = 1;
  fetchMovies();
}

function selectTagFilter(filterId) {
  activeTagFilter.value = filterId;
  page.value = 1;
  fetchMovies();
}

function changePage(p) {
  if (p >= 1 && p <= totalPages.value) {
    page.value = p;
    fetchMovies();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

function openDetailModal(movie) {
  selectedMovie.value = movie;
}

function onMovieUpdated(updatedMovie) {
  const idx = movies.value.findIndex(m => m.code === updatedMovie.code);
  if (idx !== -1) {
    movies.value[idx] = updatedMovie;
  }
}

function onSearchFromModal(kw) {
  selectedMovie.value = null;
  keyword.value = kw;
  page.value = 1;
  fetchMovies();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function onPushSingle({ code, magnet_url }) {
  try {
    const res = await api.post('/transfer/push-single', { code, magnet_url });
    if (res.data?.code === 200) {
      window.$toast?.(`番号 [${code}] 已成功提交至 115 离线任务队列！`, 'success', '115 推送成功');
    }
  } catch (err) {
    window.$toast?.('推送至 115 离线任务失败: ' + formatApiError(err), 'error');
  }
}

async function onDeleteMovie(code) {
  try {
    const res = await api.post('/db/delete', { code });
    if (res.data?.code === 200) {
      window.$toast?.(`番号 [${code}] 的电影记录已删除`, 'success');
      fetchMovies();
    }
  } catch (err) {
    window.$toast?.('删除记录失败: ' + formatApiError(err), 'error');
  }
}

async function onExportData() {
  exporting.value = true;
  try {
    const params = {
      keyword: keyword.value.trim() || undefined,
      tag_filter: activeTagFilter.value !== 'all' ? activeTagFilter.value : undefined
    };
    
    const res = await api.get('/movies/export', { params, responseType: 'blob' });
    
    const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    
    const timeStr = new Date().toISOString().slice(0, 10);
    const filterText = activeTagFilter.value !== 'all' ? `_${activeTagFilter.value}` : '';
    const kwText = keyword.value.trim() ? `_${keyword.value.trim()}` : '';
    link.setAttribute('download', `javdb_movies${filterText}${kwText}_${timeStr}.csv`);
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);

    window.$toast?.(`已成功导出匹配条件的影片数据为 CSV 文件！`, 'success', '数据导出成功');
  } catch (err) {
    console.error('Export error', err);
    window.$toast?.(formatApiError(err), 'error', '导出数据失败');
  } finally {
    exporting.value = false;
  }
}
</script>
