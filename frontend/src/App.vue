<template>
  <div class="h-screen bg-slate-950 text-slate-100 flex overflow-hidden font-sans selection:bg-sky-500 selection:text-white">
    <!-- Auth Guard: Login / Admin Init Screen -->
    <LoginView 
      v-if="!isAuthenticated" 
      :is-initialized="isInitialized" 
      @login-success="handleLoginSuccess" 
    />

    <template v-else>
      <!-- Left Full-Height Sidebar (Stretch from top 0 to bottom 0) -->
      <SidebarNav 
        :active-tab="activeTab" 
        :stats="stats"
        :actor-count="actorCount"
        :list-count="listCount"
        :is-collapsed="isSidebarCollapsed"
        :is-mobile-open="isMobileSidebarOpen"
        :has-cookie="hasCookie"
        :quota="quotaInfo"
        :username="username"
        @select-tab="activeTab = $event" 
        @toggle-collapse="toggleSidebarCollapse"
        @close-mobile="isMobileSidebarOpen = false"
        @open-auth="showAuthModal = true"
        @logout="handleLogout"
      />

      <!-- Right Content Area (100% Full Height Main Area, Zero Top Header) -->
      <div class="flex-1 flex flex-col min-w-0 h-screen overflow-hidden relative">
        <!-- Floating Mobile Sidebar Drawer Button (< md screens) -->
        <button 
          @click="isMobileSidebarOpen = true"
          class="md:hidden fixed top-3 left-3 z-30 p-2.5 rounded-2xl bg-slate-900/90 border border-slate-800 text-slate-200 shadow-xl backdrop-blur-md active:scale-95 cursor-pointer"
          title="打开导航菜单"
        >
          <Menu class="w-5 h-5" />
        </button>

        <!-- Main View Area with Modern Page Transition -->
        <main class="flex-1 p-4 sm:p-6 overflow-y-auto bg-slate-950/90 relative min-w-0">
          <transition name="page-fade-slide" mode="out-in">
            <KeepAlive>
              <component 
                :is="activeViewComponent" 
                :stats="stats"
                @refresh-stats="fetchStats"
              />
            </KeepAlive>
          </transition>
        </main>
      </div>

      <!-- Auth Modal -->
      <AuthModal 
        v-if="showAuthModal" 
        @close="showAuthModal = false"
        @cookie-updated="onCookieUpdated"
      />
    </template>

    <!-- Global Toast Container -->
    <ToastContainer />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { Menu } from '@lucide/vue';
import { getSavedCookie, removeAuthToken } from './api';
import api from './api';

import SidebarNav from './components/SidebarNav.vue';
import AuthModal from './components/AuthModal.vue';
import ToastContainer from './components/ToastContainer.vue';
import LoginView from './views/LoginView.vue';

import DashboardView from './views/DashboardView.vue';
import MediaLibraryView from './views/MediaLibraryView.vue';
import ActorsView from './views/ActorsView.vue';
import UserListsView from './views/UserListsView.vue';
import SchedulerView from './views/SchedulerView.vue';
import TransferView from './views/TransferView.vue';
import SettingsView from './views/SettingsView.vue';

const VALID_TABS = ['dashboard', 'library', 'actors', 'user-lists', 'scheduler', 'transfer', 'settings'];

function getInitialTab() {
  const hash = window.location.hash ? window.location.hash.replace('#', '').trim() : '';
  if (VALID_TABS.includes(hash)) return hash;
  const saved = localStorage.getItem('javdb_active_tab');
  if (saved && VALID_TABS.includes(saved)) return saved;
  return 'dashboard';
}

const activeTab = ref(getInitialTab());
const showAuthModal = ref(false);
const hasCookie = ref(false);
const stats = ref(null);
const quotaInfo = ref(null);

// Responsive sidebar collapse state
const isSidebarCollapsed = ref(localStorage.getItem('sidebar_collapsed') === 'true');
const isMobileSidebarOpen = ref(false);

function toggleSidebarCollapse() {
  isSidebarCollapsed.value = !isSidebarCollapsed.value;
  localStorage.setItem('sidebar_collapsed', String(isSidebarCollapsed.value));
}

// Auth state
const isInitialized = ref(true);
const isAuthenticated = ref(false);
const username = ref('');

watch(activeTab, (newTab) => {
  if (VALID_TABS.includes(newTab)) {
    localStorage.setItem('javdb_active_tab', newTab);
    if (window.location.hash !== `#${newTab}`) {
      window.location.hash = newTab;
    }
  }
}, { immediate: true });

const actorCount = computed(() => {
  try {
    const raw = localStorage.getItem('subscribed_actors');
    if (!raw) return null;
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr.length : null;
  } catch (e) {
    return null;
  }
});

const listCount = computed(() => {
  try {
    const rawMine = localStorage.getItem('user_lists_cache_mine');
    const rawFav = localStorage.getItem('user_lists_cache_favorite');
    const mineArr = rawMine ? JSON.parse(rawMine) : [];
    const favArr = rawFav ? JSON.parse(rawFav) : [];
    const set = new Set();
    if (Array.isArray(mineArr)) mineArr.forEach(item => set.add(item.list_id || item.url || item.detail_url));
    if (Array.isArray(favArr)) favArr.forEach(item => set.add(item.list_id || item.url || item.detail_url));
    return set.size > 0 ? set.size : null;
  } catch (e) {
    return null;
  }
});

const activeViewComponent = computed(() => {
  switch (activeTab.value) {
    case 'dashboard': return DashboardView;
    case 'library': return MediaLibraryView;
    case 'actors': return ActorsView;
    case 'user-lists': return UserListsView;
    case 'scheduler': return SchedulerView;
    case 'transfer': return TransferView;
    case 'settings': return SettingsView;
    default: return DashboardView;
  }
});

onMounted(() => {
  window.addEventListener('hashchange', () => {
    const hash = window.location.hash ? window.location.hash.replace('#', '').trim() : '';
    if (VALID_TABS.includes(hash)) {
      activeTab.value = hash;
    }
  });

  // Auto-collapse sidebar if screen is initially narrow (e.g. tablet width)
  if (window.innerWidth < 1024 && localStorage.getItem('sidebar_collapsed') === null) {
    isSidebarCollapsed.value = true;
  }

  checkAuthStatus();
});

async function checkAuthStatus() {
  try {
    const res = await api.get('/system/auth-status');
    if (res.data?.code === 200 && res.data?.data) {
      isInitialized.value = res.data.data.initialized;
      isAuthenticated.value = res.data.data.authenticated;
      username.value = res.data.data.username || '';
      
      if (isAuthenticated.value) {
        checkCookieState();
        fetchStats();
      }
    }
  } catch (err) {
    console.error('Check system auth status error', err);
  }
}

function handleLoginSuccess(data) {
  isInitialized.value = true;
  isAuthenticated.value = true;
  username.value = data.username || '';
  checkCookieState();
  fetchStats();
  window.$toast?.(`欢迎回来，${username.value}！`, 'success', '安全认证成功');
}

async function handleLogout() {
  try {
    await api.post('/system/logout');
  } catch (e) {
    // Ignore error
  } finally {
    removeAuthToken();
    isAuthenticated.value = false;
    username.value = '';
    window.$toast?.('您已成功安全注销退出', 'info', '安全提示');
  }
}

function checkCookieState() {
  const c = getSavedCookie();
  hasCookie.value = Boolean(c && c.trim().length > 0);
}

function onCookieUpdated(newCookie) {
  hasCookie.value = Boolean(newCookie && newCookie.trim().length > 0);
  fetchStats();
}

async function fetchStats() {
  try {
    const res = await api.get('/dashboard/stats');
    if (res.data?.code === 200 && res.data?.data) {
      stats.value = res.data.data;
    }
  } catch (err) {
    console.error('Fetch dashboard stats error', err);
  }

  try {
    const res = await api.get('/transfer/quota');
    if (res.data?.code === 200 && res.data?.data) {
      quotaInfo.value = res.data.data;
    }
  } catch (err) {
    console.error('Fetch quota error', err);
  }
}
</script>
