<template>
  <div class="group bg-slate-900/90 rounded-3xl border border-slate-800/90 hover:border-indigo-500/40 shadow-xl hover:shadow-2xl hover:shadow-indigo-500/10 overflow-hidden flex flex-col transition-all duration-300 transform hover:-translate-y-1 relative">
    <!-- Full Card Delete Confirmation Centered Overlay (全卡片居中删除确认遮罩) -->
    <div 
      v-if="showConfirmDelete"
      @click.stop
      class="absolute inset-0 bg-slate-950/95 backdrop-blur-md z-40 p-4 flex flex-col items-center justify-center text-center space-y-3 animate-fade-in border-2 border-rose-500/40 rounded-3xl"
    >
      <div class="p-2.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/30">
        <Trash2 class="w-6 h-6" />
      </div>
      <div>
        <h4 class="text-xs font-bold text-rose-300">确认物理删除此记录？</h4>
        <span class="text-[10px] font-mono text-slate-400 mt-0.5 block">番号: {{ movie.code }}</span>
      </div>

      <div class="flex items-center space-x-2 w-full pt-1">
        <button 
          @click.stop="confirmDelete"
          class="flex-1 py-1.5 rounded-xl bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500 text-white font-extrabold text-xs shadow-lg shadow-rose-600/30 transition active:scale-95 cursor-pointer"
        >
          确定物理删除
        </button>
        <button 
          @click.stop="showConfirmDelete = false"
          class="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs transition active:scale-95 cursor-pointer border border-slate-700"
        >
          取消
        </button>
      </div>
    </div>

    <!-- Top Corner Glow -->
    <div class="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-indigo-500/10 via-purple-500/5 to-transparent rounded-tr-3xl pointer-events-none z-10"></div>

    <!-- Image Poster Container (16:10 Horizontal Landscape Aspect Ratio) -->
    <div class="relative aspect-[16/10] w-full bg-slate-950 overflow-hidden cursor-pointer flex items-center justify-center" @click="$emit('view-detail', movie)">
      <!-- Real Cover Image with no-referrer -->
      <img
        v-if="movie.cover_url && !imgFailed"
        :src="movie.cover_url"
        :alt="movie.title || movie.code"
        referrerpolicy="no-referrer"
        class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
        @error="imgFailed = true"
      />

      <!-- Fallback Horizontal Dark Banner if Image is missing/broken -->
      <div v-else class="w-full h-full bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 flex flex-col items-center justify-center p-4 text-center border border-slate-800">
        <Film class="w-8 h-8 text-indigo-400/40 mb-2" />
        <span class="font-mono font-bold text-slate-300 text-sm tracking-wider">{{ movie.code }}</span>
        <span class="text-[10px] text-slate-500 mt-1 line-clamp-1 max-w-[90%]">{{ movie.title || '数据库待抓取详情' }}</span>
      </div>


      <!-- Top Left Floating "🚀 已离线" Badge -->
      <span v-if="pushedLabel" class="absolute top-2 left-2 px-2.5 py-1 rounded-xl bg-emerald-600/90 text-white font-extrabold text-[10px] flex items-center gap-1 shadow-lg z-20 backdrop-blur-md border border-emerald-400/30 animate-fade-in">
        🚀 已离线: {{ pushedLabel }}
      </span>

      <!-- Bottom Magnet Quality Badges -->
      <div class="absolute bottom-2.5 left-2.5 right-2.5 flex flex-wrap gap-1 pointer-events-none z-20">
        <span v-if="hasMagnet(movie.magnet_4k)" class="px-2 py-0.5 rounded-lg bg-purple-600/90 backdrop-blur-md text-white text-[9px] font-bold shadow flex items-center gap-0.5">
          4K <span v-if="isTypePushed('magnet_4k')">🚀</span>
        </span>
        <span v-if="hasMagnet(movie.magnet_uc)" class="px-2 py-0.5 rounded-lg bg-emerald-600/90 backdrop-blur-md text-white text-[9px] font-bold shadow flex items-center gap-0.5">
          无码中字 <span v-if="isTypePushed('magnet_uc')">🚀</span>
        </span>
        <span v-if="hasMagnet(movie.magnet_c)" class="px-2 py-0.5 rounded-lg bg-indigo-600/90 backdrop-blur-md text-white text-[9px] font-bold shadow flex items-center gap-0.5">
          有码中字 <span v-if="isTypePushed('magnet_c')">🚀</span>
        </span>
        <span v-if="hasMagnet(movie.magnet_u)" class="px-2 py-0.5 rounded-lg bg-cyan-600/90 backdrop-blur-md text-white text-[9px] font-bold shadow flex items-center gap-0.5">
          无码高清 <span v-if="isTypePushed('magnet_u')">🚀</span>
        </span>
      </div>
    </div>

    <!-- Info Section -->
    <div class="p-4 flex-1 flex flex-col justify-between space-y-3 relative z-10">
      <div>
        <h3 
          @click="$emit('view-detail', movie)"
          class="text-xs font-bold text-slate-200 line-clamp-2 hover:text-indigo-400 cursor-pointer transition leading-snug"
          :title="movie.title || movie.code"
        >
          {{ movie.title || movie.code }}
        </h3>

        <div class="flex items-center justify-between text-[11px] text-slate-400 mt-2">
          <span class="truncate pr-2 font-medium">{{ movie.actors || '未知演员' }}</span>
          <span class="font-mono text-slate-500 text-[10px] shrink-0">{{ movie.release_date || '' }}</span>
        </div>
      </div>

      <!-- Bottom Row: 番号与评分状态 -->
      <div class="flex items-center justify-between pt-2.5 border-t border-slate-800/80 gap-1.5 relative">
        <div class="flex items-center space-x-1.5 min-w-0 pr-1 shrink-0">
          <!-- 番号 Badge -->
          <span class="px-2.5 py-1 rounded-xl bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-mono text-xs font-extrabold shrink-0 shadow-inner">
            {{ movie.code }}
          </span>

          <!-- 评分状态 Badge (仅显示评分，如 3.96分) -->
          <div v-if="movie.score" class="flex items-center space-x-1 px-2.5 py-1 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs font-bold shrink-0">
            <Star class="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
            <span>{{ formatScore(movie.score) }}</span>
          </div>
          <span v-else class="text-[10px] text-slate-500 font-medium">暂无评分</span>
        </div>

        <!-- Delete Button -->
        <button 
          @click.stop="showConfirmDelete = true"
          title="从本地数据库中删除此记录"
          class="p-1.5 rounded-xl bg-slate-800/80 hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 border border-slate-700/60 transition active:scale-95 cursor-pointer shadow shrink-0"
        >
          <Trash2 class="w-3.5 h-3.5" />
        </button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { Film, Trash2, Star } from '@lucide/vue';

const props = defineProps({
  movie: Object
});

const emit = defineEmits(['view-detail', 'delete-movie']);

const imgFailed = ref(false);
const showConfirmDelete = ref(false);

const typeMap = {
  magnet_uc: '无码中字',
  magnet_4k: '4K超清',
  magnet_c: '有码中字',
  magnet_u: '无码高清',
  magnet_normal: '普通'
};

const pushedLabel = computed(() => {
  if (!props.movie?.pushed_types || props.movie.pushed_types.length === 0) return '';
  return props.movie.pushed_types.map(t => typeMap[t] || t).join(', ');
});

function isTypePushed(typeKey) {
  return props.movie?.pushed_types && props.movie.pushed_types.includes(typeKey);
}

function confirmDelete() {
  showConfirmDelete.value = false;
  emit('delete-movie', props.movie.code);
}

function hasMagnet(val) {
  return val && val !== 'None' && val.trim().length > 0;
}

function formatScore(val) {
  if (!val) return '';
  const s = String(val).trim();
  return s.endsWith('分') ? s : `${s}分`;
}
</script>
