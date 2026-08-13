<template>
  <header class="bg-slate-900/90 backdrop-blur-xl border-b border-slate-800/90 sticky top-0 z-30 px-4 sm:px-6 py-3.5 flex items-center justify-between shadow-2xl">
    <!-- Left Section: Mobile Menu Button + Logo & Title -->
    <div class="flex items-center space-x-3">
      <!-- Mobile Sidebar Drawer Toggle Button (< md) -->
      <button 
        @click="$emit('toggle-mobile-sidebar')"
        class="md:hidden p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700/60 transition active:scale-95 cursor-pointer"
        title="打开导航菜单"
      >
        <Menu class="w-5 h-5" />
      </button>

      <div class="flex items-center space-x-3">
        <div class="w-9 h-9 sm:w-10 sm:h-10 rounded-2xl bg-gradient-to-tr from-indigo-500 via-purple-500 to-indigo-600 p-0.5 shadow-lg shadow-indigo-500/20 shrink-0">
          <div class="w-full h-full bg-slate-950 rounded-[14px] flex items-center justify-center">
            <Film class="w-4 h-4 sm:w-5 sm:h-5 text-indigo-400" />
          </div>
        </div>
        <div>
          <div class="flex items-center space-x-2">
            <h1 class="text-base sm:text-lg font-extrabold bg-gradient-to-r from-slate-100 via-indigo-200 to-purple-300 bg-clip-text text-transparent tracking-wide">
              JavDB-Pilot
            </h1>
            <span class="text-[10px] sm:text-[11px] px-2 py-0.5 rounded-xl bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-mono font-bold">JavDB v1.2</span>
          </div>
          <p class="hidden sm:block text-[11px] text-slate-400">智能 JavDB 抓取、离线推送与无人值守媒体库</p>
        </div>
      </div>
    </div>

    <!-- Center Status Badges (Shown on XL and larger screens for clear layout) -->
    <div class="hidden lg:flex items-center space-x-3">
      <!-- Backend Status -->
      <div class="flex items-center space-x-2 bg-slate-950/80 border border-slate-800 rounded-2xl px-3 py-1.5 text-xs shadow-inner">
        <span class="relative flex h-2 w-2">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
        </span>
        <span class="text-slate-300 font-medium">FastAPI 在线</span>
      </div>

      <!-- Cookie Status Badge (Click to open Auth / Cookie modal) -->
      <div 
        @click="$emit('open-auth')"
        title="点击打开模拟登录与 Cookie 管理弹窗"
        class="flex items-center space-x-2 bg-slate-950/80 border border-slate-800 hover:border-indigo-500/50 rounded-2xl px-3 py-1.5 text-xs cursor-pointer transition shadow-inner"
      >
        <Key class="w-3.5 h-3.5 text-amber-400" />
        <span v-if="hasCookie" class="text-emerald-400 font-medium">Cookie 已设置</span>
        <span v-else class="text-amber-400 font-medium">未配置 Cookie</span>
      </div>

      <!-- 115 Quota Preview -->
      <div v-if="quota" class="flex items-center space-x-2 bg-slate-950/80 border border-slate-800 rounded-2xl px-3 py-1.5 text-xs shadow-inner">
        <CloudDownload class="w-3.5 h-3.5 text-indigo-400" />
        <span class="text-slate-300">115离线: <strong class="text-indigo-400 font-bold font-mono">{{ quota.remaining !== undefined ? (quota.remaining + ' 次可用') : (quota.remain_str || '可调出') }}</strong></span>
      </div>
    </div>

    <!-- Right Quick Action: Test Cookie & System Logout -->
    <div class="flex items-center space-x-2 sm:space-x-3">
      <!-- Admin User Badge -->
      <div v-if="username" class="hidden md:flex items-center space-x-1.5 px-3 py-1.5 bg-slate-950/80 border border-slate-800 rounded-2xl text-xs text-slate-300">
        <User class="w-3.5 h-3.5 text-indigo-400" />
        <span class="font-bold font-mono">{{ username }}</span>
      </div>

      <button 
        @click="handleCheckCookie"
        :disabled="checking"
        title="检测 Cookie 有效性"
        class="flex items-center space-x-1.5 px-3 py-2 sm:px-3.5 bg-slate-800/80 hover:bg-slate-800 text-slate-200 border border-slate-700/60 rounded-2xl text-xs font-bold transition active:scale-95 disabled:opacity-50 cursor-pointer"
      >
        <RefreshCw v-if="checking" class="w-3.5 h-3.5 animate-spin" />
        <ShieldCheck v-else class="w-3.5 h-3.5 text-indigo-400" />
        <span class="hidden sm:inline">{{ checking ? '检测中...' : '检测 Cookie' }}</span>
      </button>

      <!-- Logout Button -->
      <button 
        @click="$emit('logout')"
        title="安全退出当前账号登录"
        class="flex items-center space-x-1.5 px-3 py-2 sm:px-3.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 rounded-2xl text-xs font-bold transition active:scale-95 cursor-pointer"
      >
        <LogOut class="w-3.5 h-3.5" />
        <span>退出</span>
      </button>
    </div>
  </header>
</template>

<script setup>
import { ref } from 'vue';
import { Film, Key, CloudDownload, RefreshCw, ShieldCheck, User, LogOut, Menu } from 'lucide-vue-next';
import api, { getSavedCookie, formatApiError } from '../api';

defineProps({
  hasCookie: Boolean,
  quota: Object,
  username: String
});

defineEmits(['open-auth', 'logout', 'toggle-mobile-sidebar']);

const checking = ref(false);

async function handleCheckCookie() {
  const currentCookie = getSavedCookie();
  checking.value = true;
  try {
    const res = await api.post('/user/check-login', { cookies: currentCookie });
    if (res.data?.code === 200 && res.data?.data) {
      if (res.data.data.is_login) {
        window.$toast?.('Cookie 验证有效！JavDB 鉴权通过', 'success', '鉴权有效');
      } else {
        window.$toast?.(res.data.data.message || 'Cookie 已失效 (重定向至登录页)', 'error', 'Cookie 无效');
      }
    }
  } catch (err) {
    window.$toast?.(formatApiError(err), 'error', '检测失败');
  } finally {
    checking.value = false;
  }
}
</script>
