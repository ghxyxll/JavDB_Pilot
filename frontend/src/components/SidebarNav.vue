<template>
  <div>
    <!-- Mobile Backdrop Drawer Overlay (< md screens) -->
    <div 
      v-if="isMobileOpen" 
      @click="$emit('close-mobile')"
      class="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-40 md:hidden animate-fade-in"
    ></div>

    <!-- Main Sidebar Container (Full Vertical Height h-screen) -->
    <aside 
      :class="[
        'bg-slate-900/95 backdrop-blur-2xl border-r border-slate-800/80 flex flex-col justify-between shrink-0 select-none transition-all duration-300 z-40 h-screen',
        // Mobile positioning
        'fixed inset-y-0 left-0 md:static',
        isMobileOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full md:translate-x-0',
        // Desktop collapse width (w-16 = 64px, sleek & compact)
        isCollapsed ? 'md:w-16' : 'md:w-64',
        'w-64' // Default width for mobile drawer & expanded state
      ]"
    >
      <!-- Top Brand Logo Header -->
      <div 
        :class="[
          'border-b border-slate-800/80 flex items-center shrink-0 transition-all duration-300',
          isCollapsed ? 'p-3 justify-center' : 'p-4 justify-between'
        ]"
      >
        <!-- Expanded Logo & App Name -->
        <div v-if="!isCollapsed" class="flex items-center space-x-3 min-w-0">
          <div class="w-9 h-9 rounded-2xl bg-gradient-to-tr from-indigo-500 via-purple-500 to-indigo-600 p-0.5 shadow-lg shadow-indigo-500/20 shrink-0">
            <div class="w-full h-full bg-slate-950 rounded-[14px] flex items-center justify-center">
              <Film class="w-4 h-4 text-indigo-400" />
            </div>
          </div>
          <div class="min-w-0">
            <div class="flex items-center space-x-1.5">
              <h1 class="text-base font-black bg-gradient-to-r from-slate-100 via-indigo-200 to-purple-300 bg-clip-text text-transparent tracking-wide truncate">
                JavDB-Pilot
              </h1>
              <span class="text-[10px] px-2 py-0.5 rounded-xl bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-mono font-bold shrink-0">v1.2</span>
            </div>
            <p class="text-[10px] text-slate-400 font-medium truncate">JavDB 媒体库管理</p>
          </div>
        </div>

        <!-- Collapsed Mini Icon Logo (Centered 32px) -->
        <div v-else class="flex items-center justify-center">
          <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-500 via-purple-500 to-indigo-600 p-0.5 shadow-md shadow-indigo-500/20 shrink-0">
            <div class="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
              <Film class="w-3.5 h-3.5 text-indigo-400" />
            </div>
          </div>
        </div>

        <!-- Mobile Close 'X' Button -->
        <button 
          @click="$emit('close-mobile')" 
          class="md:hidden p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- Navigation Menu Items -->
      <div :class="['space-y-1.5 overflow-y-auto flex-1 custom-scrollbar', isCollapsed ? 'p-2' : 'p-3']">
        <div v-if="!isCollapsed" class="text-[11px] font-bold text-slate-500 uppercase tracking-wider px-3 mb-2">
          主菜单 Navigation
        </div>

        <button
          v-for="item in navItems"
          :key="item.id"
          @click="handleSelect(item.id)"
          :class="[
            'w-full flex items-center py-3 rounded-2xl text-xs font-semibold transition-all duration-200 group relative cursor-pointer',
            isCollapsed ? 'justify-center px-0' : 'space-x-3 px-3.5',
            activeTab === item.id 
              ? 'bg-gradient-to-r from-indigo-600/25 via-purple-600/15 to-transparent text-white border border-indigo-500/35 shadow-lg shadow-indigo-600/10 font-bold'
              : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60 border border-transparent'
          ]"
        >
          <!-- Active Pill Indicator (Left Glowing Edge) -->
          <span 
            v-if="activeTab === item.id" 
            class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-gradient-to-b from-indigo-400 to-purple-500 rounded-r-full shadow-md shadow-indigo-500/50"
          ></span>

          <component 
            :is="item.icon" 
            :class="[
              'w-4 h-4 shrink-0 transition-transform duration-200 group-hover:scale-110', 
              activeTab === item.id ? 'text-indigo-400' : 'text-slate-400 group-hover:text-slate-200'
            ]" 
          />
          
          <!-- Expanded Menu Label -->
          <span v-if="!isCollapsed" class="truncate">{{ item.label }}</span>
          
          <!-- Expanded Menu Badge -->
          <span 
            v-if="!isCollapsed && item.badge" 
            :class="[
              'ml-auto text-[10px] px-2 py-0.5 rounded-xl font-mono font-bold shrink-0 shadow-inner',
              item.badgeColor || 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/20'
            ]"
          >
            {{ item.badge }}
          </span>

          <!-- Collapsed View: Floating Glassmorphism Popover Tooltip -->
          <div 
            v-if="isCollapsed" 
            class="absolute left-full ml-3 top-1/2 -translate-y-1/2 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-200 pointer-events-none z-50 bg-slate-900/95 border border-slate-700/80 rounded-2xl px-3.5 py-2 text-xs font-semibold text-slate-100 shadow-2xl backdrop-blur-xl whitespace-nowrap flex items-center space-x-2"
          >
            <span>{{ item.label }}</span>
            <span 
              v-if="item.badge" 
              :class="[
                'text-[10px] px-2 py-0.5 rounded-xl font-mono font-bold',
                item.badgeColor || 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/20'
              ]"
            >
              {{ item.badge }}
            </span>
          </div>

          <!-- Indicator Dot in Collapsed View when Badge Exists -->
          <span 
            v-if="isCollapsed && item.badge" 
            class="absolute top-2.5 right-2.5 w-1.5 h-1.5 rounded-full bg-indigo-400 shadow-sm"
          ></span>
        </button>
      </div>

      <!-- Bottom Status & System Controls (Above Collapse Toggle Button) -->
      <div :class="['border-t border-slate-800/80 space-y-2 shrink-0', isCollapsed ? 'p-2' : 'p-3']">
        
        <!-- Expanded Status Block -->
        <div v-if="!isCollapsed" class="bg-slate-950/80 rounded-2xl p-3 border border-slate-800/80 space-y-2 shadow-inner">
          <!-- 1. System Status & Cookie State -->
          <div class="flex items-center justify-between text-xs">
            <div 
              @click="$emit('open-auth')"
              class="flex items-center space-x-1.5 hover:text-indigo-300 cursor-pointer transition min-w-0"
              title="点击配置 Cookie"
            >
              <Key class="w-3.5 h-3.5 text-amber-400 shrink-0" />
              <span v-if="hasCookie" class="text-emerald-400 font-bold truncate">Cookie 已设置</span>
              <span v-else class="text-amber-400 font-bold truncate">未配置 Cookie</span>
            </div>

            <button 
              @click="handleCheckCookie"
              :disabled="checkingCookie"
              title="检测 Cookie 有效性"
              class="p-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 transition active:scale-95 disabled:opacity-50 cursor-pointer shrink-0"
            >
              <RefreshCw v-if="checkingCookie" class="w-3.5 h-3.5 animate-spin" />
              <ShieldCheck v-else class="w-3.5 h-3.5 text-indigo-400" />
            </button>
          </div>

          <!-- 2. 115 Quota Status -->
          <div v-if="quota" class="flex items-center justify-between text-[11px] border-t border-slate-800/60 pt-2 text-slate-400">
            <div class="flex items-center space-x-1.5 min-w-0">
              <CloudDownload class="w-3.5 h-3.5 text-indigo-400 shrink-0" />
              <span class="truncate">115 配额</span>
            </div>
            <span class="font-mono font-bold text-indigo-300 truncate">
              {{ quota.remaining !== undefined ? (quota.remaining + ' 次可用') : (quota.remain_str || '可调出') }}
            </span>
          </div>

          <!-- 3. User & Logout Bar -->
          <div class="flex items-center justify-between border-t border-slate-800/60 pt-2 text-xs">
            <div class="flex items-center space-x-1.5 min-w-0">
              <User class="w-3.5 h-3.5 text-indigo-400 shrink-0" />
              <span class="font-bold font-mono text-slate-200 truncate">{{ username || '管理员' }}</span>
            </div>

            <button 
              @click="$emit('logout')"
              title="安全退出当前账号登录"
              class="flex items-center space-x-1 px-2 py-1 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 rounded-xl text-[11px] font-bold transition active:scale-95 cursor-pointer shrink-0"
            >
              <LogOut class="w-3 h-3" />
              <span>退出</span>
            </button>
          </div>
        </div>

        <!-- Collapsed Mini Icon Control Bar -->
        <div v-else class="flex flex-col items-center space-y-2 py-1">
          <!-- Cookie Mini Button -->
          <button 
            @click="$emit('open-auth')" 
            title="配置/管理 Cookie"
            class="p-2 rounded-xl bg-slate-950/80 hover:bg-slate-800 border border-slate-800 text-amber-400 relative transition cursor-pointer"
          >
            <Key class="w-3.5 h-3.5" />
            <span :class="['absolute top-1 right-1 w-1.5 h-1.5 rounded-full', hasCookie ? 'bg-emerald-500' : 'bg-amber-500']"></span>
          </button>

          <!-- Check Cookie Mini Button -->
          <button 
            @click="handleCheckCookie" 
            :disabled="checkingCookie"
            title="检测 Cookie 有效性"
            class="p-2 rounded-xl bg-slate-950/80 hover:bg-slate-800 border border-slate-800 text-indigo-400 transition cursor-pointer"
          >
            <RefreshCw v-if="checkingCookie" class="w-3.5 h-3.5 animate-spin" />
            <ShieldCheck v-else class="w-3.5 h-3.5" />
          </button>

          <!-- Logout Mini Button -->
          <button 
            @click="$emit('logout')" 
            title="退出账号"
            class="p-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-300 transition cursor-pointer"
          >
            <LogOut class="w-3.5 h-3.5" />
          </button>
        </div>

        <!-- Desktop Collapse Toggle Button -->
        <button
          @click="$emit('toggle-collapse')"
          :title="isCollapsed ? '展开侧边导航栏' : '收起侧边导航栏'"
          :class="[
            'w-full hidden md:flex items-center justify-center py-2.5 rounded-2xl bg-slate-950/80 hover:bg-indigo-600/20 text-slate-400 hover:text-indigo-300 border border-slate-800 hover:border-indigo-500/40 text-xs font-bold transition-all duration-300 active:scale-95 cursor-pointer shadow-inner',
            isCollapsed ? 'px-0' : 'space-x-2 px-3'
          ]"
        >
          <ChevronRight v-if="isCollapsed" class="w-4 h-4 text-indigo-400 shrink-0" />
          <template v-else>
            <ChevronLeft class="w-4 h-4 text-indigo-400 shrink-0" />
            <span>收起侧栏菜单</span>
          </template>
        </button>

      </div>
    </aside>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { LayoutDashboard, Film, Users, Bookmark, Clock, Cloud, Settings, ChevronLeft, ChevronRight, X, Key, ShieldCheck, RefreshCw, CloudDownload, User, LogOut } from '@lucide/vue';
import api, { getSavedCookie, formatApiError } from '../api';

const props = defineProps({
  activeTab: String,
  stats: Object,
  actorCount: Number,
  listCount: Number,
  isCollapsed: Boolean,
  isMobileOpen: Boolean,
  hasCookie: Boolean,
  quota: Object,
  username: String
});

const emit = defineEmits(['select-tab', 'toggle-collapse', 'close-mobile', 'open-auth', 'logout']);

const checkingCookie = ref(false);

async function handleCheckCookie() {
  const currentCookie = getSavedCookie();
  checkingCookie.value = true;
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
    checkingCookie.value = false;
  }
}

function handleSelect(id) {
  emit('select-tab', id);
  emit('close-mobile');
}

const navItems = computed(() => [
  { id: 'dashboard', label: '控制台', icon: LayoutDashboard },
  { 
    id: 'library', 
    label: '媒体库', 
    icon: Film, 
    badge: props.stats?.total_movies !== undefined ? `${props.stats.total_movies} 部` : null,
    badgeColor: 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/20'
  },
  { 
    id: 'actors', 
    label: '订阅演员', 
    icon: Users, 
    badge: props.actorCount !== undefined && props.actorCount !== null ? `${props.actorCount} 位` : null,
    badgeColor: 'bg-purple-500/20 text-purple-300 border border-purple-500/20'
  },
  { 
    id: 'user-lists', 
    label: '收藏清单', 
    icon: Bookmark, 
    badge: props.listCount !== undefined && props.listCount !== null ? `${props.listCount} 个` : null,
    badgeColor: 'bg-amber-500/20 text-amber-300 border border-amber-500/20'
  },
  { 
    id: 'scheduler', 
    label: '定时任务', 
    icon: Clock, 
    badge: props.stats?.cron_jobs_count ? `${props.stats.cron_jobs_count} 项` : null,
    badgeColor: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/20'
  },
  { 
    id: 'transfer', 
    label: '离线记录', 
    icon: Cloud, 
    badge: props.stats?.count_pushed ? `${props.stats.count_pushed} 推` : null,
    badgeColor: 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/20'
  },
  { id: 'settings', label: '系统设置', icon: Settings },
]);
</script>
