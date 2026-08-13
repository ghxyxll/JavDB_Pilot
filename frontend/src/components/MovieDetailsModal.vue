<template>
  <Teleport to="body">
    <div 
      v-if="displayMovie" 
      class="fixed inset-0 z-[9999] flex items-center justify-center p-4 sm:p-6 md:p-8 bg-slate-950/80 backdrop-blur-md animate-fade-in"
      @keydown.left="prevLightbox"
      @keydown.right="nextLightbox"
      @keydown.esc="closeLightbox"
      tabindex="0"
    >
      <div class="bg-slate-900 border border-slate-800/90 rounded-3xl max-w-5xl w-full h-auto max-h-[85vh] shadow-2xl flex flex-col lg:flex-row overflow-hidden relative">
      
      <!-- Close Modal Button -->
      <button 
        @click="$emit('close')"
        class="absolute top-3 right-3 sm:top-4 sm:right-4 z-30 p-2 sm:p-2.5 rounded-full bg-slate-950/80 hover:bg-rose-600/90 text-slate-300 hover:text-white border border-slate-700/80 transition active:scale-95 cursor-pointer shadow-xl"
      >
        <X class="w-5 h-5" />
      </button>

      <!-- Left Column: Big Poster + Quick Actions + Paginated Sample Images (左列：大海报 + 快捷按钮 + 翻页剧照相册) -->
      <div class="w-full lg:w-1/2 bg-slate-950/90 p-5 sm:p-6 border-b lg:border-b-0 lg:border-r border-slate-800/80 flex flex-col space-y-4 overflow-y-auto flex-1 min-h-0">
        
        <!-- Big Cover Image Container with Skeleton Loading -->
        <div class="relative rounded-2xl overflow-hidden bg-slate-900 border border-slate-800/80 shadow-xl group shrink-0">
          <!-- Poster Skeleton Placeholder Animation -->
          <div v-if="!posterLoaded" class="absolute inset-0 bg-slate-900/90 animate-pulse flex flex-col items-center justify-center text-slate-600 p-6 min-h-[260px]">
            <Film class="w-10 h-10 animate-spin text-indigo-500/50 mb-2" />
            <span class="text-xs font-mono font-bold text-slate-500">正在加载大海报...</span>
          </div>

          <img 
            :src="displayMovie.cover_url" 
            :alt="displayMovie.title || displayMovie.code"
            referrerpolicy="no-referrer"
            @load="posterLoaded = true"
            @error="posterLoaded = true"
            class="w-full rounded-2xl object-cover shadow-lg group-hover:scale-102 transition duration-500 max-h-[320px]"
          />
        </div>

        <!-- Quick Action Buttons -->
        <div class="flex items-center space-x-2 shrink-0">
          <button 
            @click="handleFetchDetail"
            :disabled="fetchingDetail"
            class="flex-1 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-xl font-bold text-xs flex items-center justify-center space-x-2 shadow-lg shadow-indigo-600/20 transition active:scale-95 disabled:opacity-50 cursor-pointer"
          >
            <RefreshCw :class="['w-3.5 h-3.5', fetchingDetail ? 'animate-spin' : '']" />
            <span>{{ fetchingDetail ? '正在更新详情...' : '手动更新详情' }}</span>
          </button>
          
          <a 
            v-if="displayMovie.detail_url" 
            :href="displayMovie.detail_url" 
            target="_blank"
            class="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-bold flex items-center justify-center space-x-1.5 transition border border-slate-700/60 shadow-sm shrink-0"
          >
            <ExternalLink class="w-3.5 h-3.5" />
            <span>前往源站</span>
          </a>
        </div>

        <!-- Sample Images Section (带翻页移动控件，纯剧照展示) -->
        <div v-if="parsedPreviewImages.length > 0" class="space-y-3 pt-3 border-t border-slate-800/80">
          
          <!-- Gallery Header & Pagination Controls (翻页移动控件) -->
          <div class="flex items-center justify-between">
            <h4 class="text-xs font-bold text-slate-200 flex items-center space-x-1.5">
              <ImageIcon class="w-4 h-4 text-purple-400" />
              <span>📷 精彩剧照图集 (Gallery)</span>
            </h4>

            <!-- Pagination Arrows (翻页移动按钮) -->
            <div class="flex items-center space-x-2">
              <span class="text-[11px] font-mono text-slate-400">
                {{ galleryPage }} / {{ totalGalleryPages }} 页 (共 {{ parsedPreviewImages.length }} 张)
              </span>

              <div v-if="totalGalleryPages > 1" class="flex items-center space-x-1">
                <button 
                  @click="prevGalleryPage" 
                  :disabled="galleryPage <= 1"
                  title="上一页剧照"
                  class="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-30 disabled:hover:bg-slate-800 border border-slate-700/60 transition active:scale-95 cursor-pointer"
                >
                  <ChevronLeft class="w-3.5 h-3.5" />
                </button>
                <button 
                  @click="nextGalleryPage" 
                  :disabled="galleryPage >= totalGalleryPages"
                  title="下一页剧照"
                  class="p-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-30 disabled:hover:bg-slate-800 border border-slate-700/60 transition active:scale-95 cursor-pointer"
                >
                  <ChevronRight class="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>

          <!-- Paginated Gallery Grid (每页固定 6 张剧照) -->
          <div class="grid grid-cols-3 gap-2.5">
            <div 
              v-for="(img, idx) in currentGalleryImages" 
              :key="idx"
              @click="openLightbox((galleryPage - 1) * pageSize + idx)"
              class="group aspect-video rounded-xl overflow-hidden bg-slate-900 border border-slate-800/80 hover:border-indigo-500 cursor-pointer relative transition shadow-sm"
            >
              <!-- Skeleton Loading Animation -->
              <div v-if="!loadedImages.has(img)" class="absolute inset-0 bg-slate-950 animate-pulse flex items-center justify-center border border-slate-800">
                <ImageIcon class="w-4 h-4 text-slate-700 animate-pulse" />
              </div>

              <img 
                :src="img" 
                referrerpolicy="no-referrer" 
                loading="lazy" 
                @load="loadedImages.add(img)"
                @error="loadedImages.add(img)"
                class="w-full h-full object-cover group-hover:scale-105 transition duration-300" 
              />
              <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center">
                <Maximize2 class="w-4 h-4 text-white" />
              </div>
            </div>
          </div>

        </div>

      </div>

      <!-- Right Column: Metadata + Magnets (右列：元数据与下载区) -->
      <div class="w-full lg:w-1/2 p-5 sm:p-6 space-y-5 overflow-y-auto flex-1 min-h-0">
        <!-- Title & Code Header -->
        <div>
          <div class="flex items-center space-x-2 mb-2">
            <span class="px-2.5 py-0.5 rounded-lg bg-sky-500/20 text-sky-400 border border-sky-500/30 text-xs font-mono font-bold">
              {{ displayMovie.code }}
            </span>
            <span v-if="displayMovie.score" class="px-2.5 py-0.5 rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/30 text-xs font-bold">
              ★ {{ displayMovie.score }} ({{ displayMovie.score_number || '0' }}评分)
            </span>
          </div>
          <h2 class="text-base font-bold text-slate-100 leading-snug">{{ displayMovie.title }}</h2>
        </div>

        <!-- Metadata Info Grid -->
        <div class="grid grid-cols-2 gap-3 text-xs bg-slate-950/60 p-4 rounded-2xl border border-slate-800/80">
          <div><span class="text-slate-500">发行日期：</span><span class="text-slate-300 font-mono">{{ displayMovie.release_date || '-' }}</span></div>
          <div><span class="text-slate-500">影片时长：</span><span class="text-slate-300 font-mono">{{ displayMovie.duration || '-' }}</span></div>
          <div><span class="text-slate-500">片商 Maker：</span><span class="text-slate-300">{{ displayMovie.maker || '-' }}</span></div>
          <div><span class="text-slate-500">发行 Publisher：</span><span class="text-slate-300">{{ displayMovie.publisher || '-' }}</span></div>
          <div><span class="text-slate-500">导演 Director：</span><span class="text-slate-300">{{ displayMovie.director || '-' }}</span></div>
          <div><span class="text-slate-500">系列 Series：</span><span class="text-slate-300">{{ displayMovie.series || '-' }}</span></div>
        </div>

        <!-- Clickable Actors Chips -->
        <div>
          <h4 class="text-xs font-semibold text-slate-400 mb-1.5 flex items-center space-x-1">
            <User class="w-3.5 h-3.5 text-sky-400" />
            <span>主演演员 (点击可在数据库中检索)</span>
          </h4>
          <div class="flex flex-wrap gap-1.5">
            <button 
              v-for="act in actorsList" 
              :key="act"
              @click="$emit('search-keyword', act)"
              :title="`在数据库中检索演员 [${act}] 的所有影片`"
              class="px-2.5 py-1 rounded-xl bg-slate-800 hover:bg-sky-600/30 text-slate-300 hover:text-sky-300 border border-slate-700/60 hover:border-sky-500/50 text-[11px] font-bold transition active:scale-95 cursor-pointer flex items-center space-x-1 shadow-sm"
            >
              <span>{{ act }}</span>
            </button>
            <span v-if="!actorsList.length" class="text-slate-500 text-xs">未知</span>
          </div>
        </div>

        <!-- Clickable Tags Chips -->
        <div>
          <h4 class="text-xs font-semibold text-slate-400 mb-1.5 flex items-center space-x-1">
            <Tag class="w-3.5 h-3.5 text-purple-400" />
            <span>分类标签 (点击可在数据库中检索)</span>
          </h4>
          <div class="flex flex-wrap gap-1.5">
            <button 
              v-for="t in tagsList" 
              :key="t"
              @click="$emit('search-keyword', t)"
              :title="`在数据库中检索标签 [${t}] 的所有影片`"
              class="px-2 py-0.5 rounded-lg bg-purple-500/10 text-purple-300 border border-purple-500/20 hover:bg-purple-500/20 text-[10px] font-medium transition cursor-pointer"
            >
              <span>{{ t }}</span>
            </button>
            <span v-if="!tagsList.length" class="text-slate-500 text-xs">暂无标签</span>
          </div>
        </div>

        <!-- Magnet Downloads & 115 Offline Push Slots Panel -->
        <div class="space-y-2 pt-2 border-t border-slate-800/80">
          <h4 class="text-xs font-semibold text-slate-400 flex items-center space-x-1">
            <Link class="w-3.5 h-3.5 text-emerald-400" />
            <span>磁力下载槽位 (支持一键推送 115 离线)</span>
          </h4>

          <div v-if="magnetSlots.length > 0" class="space-y-2">
            <div 
              v-for="slot in magnetSlots" 
              :key="slot.key"
              class="p-3 rounded-2xl bg-slate-950/80 border border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-2 hover:border-slate-700 transition"
            >
              <div class="flex items-center space-x-2 min-w-0 flex-1">
                <span :class="['px-2.5 py-1 rounded-xl text-[10px] font-extrabold shrink-0 shadow-inner', slot.badgeClass]">
                  {{ slot.label }}
                </span>
                <span class="text-xs font-mono text-slate-400 truncate select-all">{{ slot.url }}</span>
              </div>

              <div class="flex items-center space-x-2 shrink-0">
                <button 
                  @click="copyToClipboard(slot.url)"
                  class="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 active:scale-95 text-slate-200 text-xs font-bold transition cursor-pointer"
                >
                  复制
                </button>
                <button 
                  @click="handlePush115Slot(slot.key, slot.url)"
                  :disabled="pushingSlot === slot.key"
                  class="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 active:scale-95 disabled:opacity-50 text-white text-xs font-extrabold shadow-md shadow-emerald-600/20 transition flex items-center space-x-1.5 cursor-pointer"
                >
                  <RefreshCw v-if="pushingSlot === slot.key" class="w-3.5 h-3.5 animate-spin" />
                  <CloudDownload v-else class="w-3.5 h-3.5" />
                  <span>{{ pushingSlot === slot.key ? '正在推送...' : '推送至115' }}</span>
                </button>
              </div>
            </div>
          </div>

          <div v-else class="p-4 rounded-2xl bg-slate-950/40 border border-slate-800/60 text-center">
            <span class="text-xs text-slate-500">该作品在数据库中暂未匹配到任何可用磁力链接</span>
          </div>
        </div>

      </div>
    </div>

    <!-- Fullscreen Lightbox Modal with Interactive Prev/Next Navigation (全屏大图轮播灯箱，带左右切换箭头) -->
    <div 
      v-if="activeLightboxIndex !== -1 && currentLightboxImg" 
      @click="closeLightbox" 
      class="fixed inset-0 z-50 bg-black/95 backdrop-blur-xl flex items-center justify-center p-4 animate-fade-in select-none"
    >
      <!-- Top Counter & Close Bar -->
      <div class="absolute top-6 left-6 right-6 flex justify-between items-center z-10 pointer-events-none">
        <span class="px-3 py-1.5 rounded-xl bg-slate-900/80 text-slate-300 font-mono text-xs border border-slate-800 backdrop-blur-md shadow-lg pointer-events-auto">
          🖼️ 剧照 {{ activeLightboxIndex + 1 }} / {{ parsedPreviewImages.length }}
        </span>
        <button 
          @click.stop="closeLightbox" 
          class="p-3 rounded-full bg-slate-900/80 hover:bg-rose-600 text-white border border-slate-700 transition cursor-pointer pointer-events-auto shadow-lg"
        >
          <X class="w-6 h-6" />
        </button>
      </div>

      <!-- Left Arrow Button (< 切换上一张) -->
      <button 
        v-if="parsedPreviewImages.length > 1"
        @click.stop="prevLightbox" 
        title="上一张 (按键盘左箭头 ←)"
        class="absolute left-6 top-1/2 -translate-y-1/2 p-4 rounded-2xl bg-slate-900/80 hover:bg-indigo-600 text-white border border-slate-700/80 hover:border-indigo-400 transition active:scale-95 cursor-pointer z-10 shadow-2xl backdrop-blur-md"
      >
        <ChevronLeft class="w-8 h-8" />
      </button>

      <!-- Center Lightbox High-Res Image -->
      <div class="max-w-5xl max-h-[85vh] flex items-center justify-center p-2" @click.stop>
        <img 
          :src="currentLightboxImg" 
          referrerpolicy="no-referrer" 
          class="max-w-full max-h-[85vh] rounded-2xl shadow-2xl border border-slate-800 object-contain transition duration-300" 
        />
      </div>

      <!-- Right Arrow Button (> 切换下一张) -->
      <button 
        v-if="parsedPreviewImages.length > 1"
        @click.stop="nextLightbox" 
        title="下一张 (按键盘右箭头 →)"
        class="absolute right-6 top-1/2 -translate-y-1/2 p-4 rounded-2xl bg-slate-900/80 hover:bg-indigo-600 text-white border border-slate-700/80 hover:border-indigo-400 transition active:scale-95 cursor-pointer z-10 shadow-2xl backdrop-blur-md"
      >
        <ChevronRight class="w-8 h-8" />
      </button>

    </div>

  </div>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue';
import { X, RefreshCw, CloudDownload, ExternalLink, User, Tag, Link, Film, Image as ImageIcon, Maximize2, ChevronLeft, ChevronRight } from '@lucide/vue';
import api, { formatApiError } from '../api';

const props = defineProps({
  movie: Object
});

const emit = defineEmits(['close', 'push-115', 'push115', 'search-keyword', 'update-movie']);

const localMovie = ref(null);
const fetchingDetail = ref(false);
const pushingSlot = ref('');
const posterLoaded = ref(false);
const loadedImages = reactive(new Set());

// 剧照图集翻页与大图轮播控件
const galleryPage = ref(1);
const pageSize = 6;
const activeLightboxIndex = ref(-1);

watch(() => props.movie, (newVal) => {
  if (newVal) {
    localMovie.value = { ...newVal };
    posterLoaded.value = false;
    loadedImages.clear();
    galleryPage.value = 1;
    activeLightboxIndex.value = -1;
  }
}, { immediate: true, deep: true });

const displayMovie = computed(() => localMovie.value || props.movie);

const parsedPreviewImages = computed(() => {
  if (!displayMovie.value?.preview_images) return [];
  try {
    const raw = displayMovie.value.preview_images;
    if (typeof raw === 'string') {
      const arr = JSON.parse(raw);
      return Array.isArray(arr) ? arr : [];
    }
    if (Array.isArray(raw)) return raw;
  } catch (e) {
    return [];
  }
  return [];
});

const totalGalleryPages = computed(() => Math.ceil(parsedPreviewImages.value.length / pageSize) || 1);

// 当前页显示的 6 张剧照
const currentGalleryImages = computed(() => {
  const start = (galleryPage.value - 1) * pageSize;
  return parsedPreviewImages.value.slice(start, start + pageSize);
});

function prevGalleryPage() {
  if (galleryPage.value > 1) galleryPage.value--;
}

function nextGalleryPage() {
  if (galleryPage.value < totalGalleryPages.value) galleryPage.value++;
}

// Lightbox 大图轮播
const currentLightboxImg = computed(() => {
  if (activeLightboxIndex.value >= 0 && activeLightboxIndex.value < parsedPreviewImages.value.length) {
    return parsedPreviewImages.value[activeLightboxIndex.value];
  }
  return null;
});

function openLightbox(index) {
  activeLightboxIndex.value = index;
}

function closeLightbox() {
  activeLightboxIndex.value = -1;
}

function prevLightbox() {
  if (parsedPreviewImages.value.length === 0) return;
  if (activeLightboxIndex.value > 0) {
    activeLightboxIndex.value--;
  } else {
    activeLightboxIndex.value = parsedPreviewImages.value.length - 1;
  }
}

function nextLightbox() {
  if (parsedPreviewImages.value.length === 0) return;
  if (activeLightboxIndex.value < parsedPreviewImages.value.length - 1) {
    activeLightboxIndex.value++;
  } else {
    activeLightboxIndex.value = 0;
  }
}

// 键盘事件支持
function handleKeydown(e) {
  if (activeLightboxIndex.value === -1) return;
  if (e.key === 'ArrowLeft') prevLightbox();
  else if (e.key === 'ArrowRight') nextLightbox();
  else if (e.key === 'Escape') closeLightbox();
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown);
});

async function handlePush115Slot(slotKey, magnetUrl) {
  if (!magnetUrl || !displayMovie.value?.code) return;
  pushingSlot.value = slotKey;
  try {
    const res = await api.post('/transfer/push-single', {
      code: displayMovie.value.code,
      magnet_url: magnetUrl,
      magnet_type: slotKey
    });
    if (res.data?.code === 200) {
      window.$toast?.(`番号 [${displayMovie.value.code}] 磁力任务已成功提交至 115 离线下载队列！`, 'success', '115 推送成功');
    }
  } catch (err) {
    window.$toast?.('推送至 115 离线任务失败: ' + formatApiError(err), 'error');
  } finally {
    pushingSlot.value = '';
  }
}

async function handleFetchDetail() {
  const m = displayMovie.value;
  if (!m || !m.code) return;
  
  fetchingDetail.value = true;
  try {
    const res = await api.post('/queue/add-code-task', { code: m.code });
    if (res.data?.code === 200) {
      window.$toast?.(`已为番号 [${m.code}] 提交抓取任务，正在实时获取最新数据...`, 'info', '任务已提交');

      for (let i = 0; i < 15; i++) {
        await new Promise(r => setTimeout(r, 1000));
        
        try {
          const detailRes = await api.get('/movies/detail', { params: { code: m.code } });
          if (detailRes.data?.code === 200 && detailRes.data?.data) {
            const freshData = detailRes.data.data;
            if (freshData.is_detail_fetched === 1 || (freshData.actors && freshData.actors.length > 0) || freshData.magnet_uc || freshData.magnet_normal) {
              localMovie.value = freshData;
              window.$toast?.(`🎉 番号 [${m.code}] 最新详情抓取成功，数据已实时同步！`, 'success', '抓取完成');
              emit('update-movie', freshData);
              break;
            }
          }
        } catch (e) {
          // ignore
        }
      }
    }
  } catch (err) {
    window.$toast?.('提交抓取任务失败: ' + formatApiError(err), 'error');
  } finally {
    fetchingDetail.value = false;
  }
}

const actorsList = computed(() => {
  if (!displayMovie.value?.actors) return [];
  return displayMovie.value.actors.split(',').map(s => s.trim()).filter(Boolean);
});

const tagsList = computed(() => {
  if (!displayMovie.value?.tags) return [];
  return displayMovie.value.tags.split(',').map(s => s.trim()).filter(Boolean);
});

const magnetSlots = computed(() => {
  const m = displayMovie.value;
  const all = [
    { key: 'magnet_uc', label: '无码中字 UC', url: m?.magnet_uc, badgeClass: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' },
    { key: 'magnet_4k', label: '4K 超清', url: m?.magnet_4k, badgeClass: 'bg-purple-500/20 text-purple-400 border border-purple-500/30' },
    { key: 'magnet_c', label: '有码中字 C', url: m?.magnet_c, badgeClass: 'bg-blue-500/20 text-blue-400 border border-blue-500/30' },
    { key: 'magnet_u', label: '无码高清 U', url: m?.magnet_u, badgeClass: 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30' },
    { key: 'magnet_normal', label: '普通磁力', url: m?.magnet_normal, badgeClass: 'bg-slate-500/20 text-slate-300 border border-slate-500/30' }
  ];
  return all.filter(s => s.url && s.url !== 'None' && s.url.trim().length > 0);
});

function copyToClipboard(text) {
  navigator.clipboard.writeText(text);
  window.$toast?.('磁力链接已成功复制到剪贴板！', 'success', '已复制磁力');
}
</script>
