<template>
  <div class="fixed top-5 right-5 z-50 flex flex-col space-y-2.5 pointer-events-none max-w-md w-full px-4">
    <TransitionGroup name="toast">
      <div 
        v-for="t in toasts" 
        :key="t.id" 
        :class="[
          'pointer-events-auto p-4 rounded-2xl border shadow-2xl backdrop-blur-md text-xs flex items-start justify-between space-x-3 transition-all duration-300 transform',
          t.type === 'success' ? 'bg-slate-900/95 border-emerald-500/40 text-emerald-400 shadow-emerald-500/10' :
          t.type === 'error' ? 'bg-slate-900/95 border-rose-500/40 text-rose-400 shadow-rose-500/10' :
          t.type === 'warning' ? 'bg-slate-900/95 border-amber-500/40 text-amber-400 shadow-amber-500/10' :
          'bg-slate-900/95 border-sky-500/40 text-sky-400 shadow-sky-500/10'
        ]"
      >
        <div class="flex items-start space-x-2.5">
          <CheckCircle2 v-if="t.type === 'success'" class="w-5 h-5 shrink-0 mt-0.5 text-emerald-400" />
          <AlertCircle v-else-if="t.type === 'error'" class="w-5 h-5 shrink-0 mt-0.5 text-rose-400" />
          <AlertTriangle v-else-if="t.type === 'warning'" class="w-5 h-5 shrink-0 mt-0.5 text-amber-400" />
          <Info v-else class="w-5 h-5 shrink-0 mt-0.5 text-sky-400" />
          
          <div>
            <h4 class="font-bold text-slate-100 text-xs mb-0.5">
              {{ t.title || (t.type === 'success' ? '操作成功' : t.type === 'error' ? '提示信息' : t.type === 'warning' ? '系统警告' : '通知') }}
            </h4>
            <p class="text-slate-300 text-[11px] leading-relaxed whitespace-pre-line">{{ t.message }}</p>
          </div>
        </div>

        <button 
          @click="removeToast(t.id)" 
          class="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
        >
          <X class="w-4 h-4" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from '@lucide/vue';

const toasts = ref([]);

function addToast({ message, type = 'success', title = '', duration = 3500 }) {
  const id = Date.now() + Math.random().toString(36).substring(2, 9);
  toasts.value.unshift({ id, message, type, title });
  if (duration > 0) {
    setTimeout(() => {
      removeToast(id);
    }, duration);
  }
}

function removeToast(id) {
  toasts.value = toasts.value.filter(t => t.id !== id);
}

function handleToastEvent(e) {
  if (e.detail) {
    addToast(e.detail);
  }
}

onMounted(() => {
  window.addEventListener('app-toast', handleToastEvent);
  window.$toast = (message, type = 'success', title = '', duration = 3500) => {
    window.dispatchEvent(new CustomEvent('app-toast', { detail: { message, type, title, duration } }));
  };
});

onUnmounted(() => {
  window.removeEventListener('app-toast', handleToastEvent);
});
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.toast-enter-from {
  opacity: 0;
  transform: translateY(-20px) scale(0.95);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(100px);
}
</style>
