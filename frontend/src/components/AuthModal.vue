<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in">
    <div class="bg-slate-900/95 border border-slate-800/90 rounded-3xl max-w-lg w-full p-6 space-y-5 shadow-2xl relative overflow-hidden max-h-[90vh] overflow-y-auto">
      <!-- Ambient Backlight -->
      <div class="absolute -top-16 -left-16 w-56 h-56 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>

      <!-- Close Button -->
      <button 
        @click="$emit('close')"
        class="absolute top-4 right-4 p-2 rounded-full bg-slate-950/60 hover:bg-slate-800 text-slate-400 hover:text-white transition z-20"
      >
        <X class="w-5 h-5" />
      </button>

      <!-- Title Header -->
      <div class="flex items-center space-x-3 border-b border-slate-800/80 pb-4 relative z-10">
        <div class="p-2.5 rounded-2xl bg-amber-500/10 text-amber-400 border border-amber-500/20 shadow-inner">
          <Key class="w-6 h-6" />
        </div>
        <div>
          <h3 class="text-base font-extrabold text-slate-100">JavDB 账号登录 & Cookie 管理</h3>
          <p class="text-xs text-slate-400">支持网页模拟直登获取 Cookie 或直接粘贴手动配置</p>
        </div>
      </div>

      <!-- Mode Selector Tabs -->
      <div class="flex bg-slate-950/80 p-1.5 rounded-2xl border border-slate-800/80 text-xs font-semibold shadow-inner relative z-10">
        <button 
          @click="mode = 'simulate'"
          :class="['flex-1 py-2 rounded-xl transition-all duration-200', mode === 'simulate' ? 'bg-indigo-600 text-white font-bold shadow-md shadow-indigo-600/30' : 'text-slate-400 hover:text-slate-200']"
        >
          🔑 模拟网页登录 (自动抓取)
        </button>
        <button 
          @click="mode = 'manual'"
          :class="['flex-1 py-2 rounded-xl transition-all duration-200', mode === 'manual' ? 'bg-indigo-600 text-white font-bold shadow-md shadow-indigo-600/30' : 'text-slate-400 hover:text-slate-200']"
        >
          📝 手动粘贴 & 连通检测
        </button>
      </div>

      <!-- Mode A: Simulate Login Step-by-Step -->
      <div v-if="mode === 'simulate'" class="space-y-4 text-xs relative z-10">
        <!-- Step 1: Start Session -->
        <div v-if="!sessionId" class="space-y-3">
          <p class="text-slate-400 leading-relaxed">
            点击下方按钮触发后台伪装请求，自动初始化 JavDB 登录会话并获取实时图形验证码：
          </p>
          <button 
            @click="startSession" 
            :disabled="loading"
            class="w-full py-3 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-extrabold rounded-2xl shadow-lg shadow-indigo-600/25 transition flex items-center justify-center space-x-2"
          >
            <RefreshCw v-if="loading" class="w-4 h-4 animate-spin" />
            <span>{{ loading ? '正在请求 JavDB 登录页面...' : '🚀 第一步：初始化登录会话' }}</span>
          </button>
        </div>

        <!-- Step 2: Form Input + Captcha Image -->
        <div v-else class="space-y-3">
          <div class="p-3 bg-slate-950 rounded-2xl border border-slate-800 flex items-center justify-between shadow-inner">
            <span class="text-slate-400 font-mono truncate max-w-[240px]">Session: {{ sessionId }}</span>
            <button @click="refreshCaptcha" :disabled="loading" class="text-indigo-400 hover:underline text-[11px] flex items-center space-x-1 font-semibold">
              <RotateCw :class="['w-3 h-3', loading ? 'animate-spin' : '']" />
              <span>刷新验证码</span>
            </button>
          </div>

          <!-- Captcha Image Preview -->
          <div v-if="captchaImage" class="flex flex-col items-center justify-center bg-white p-3 rounded-2xl border border-slate-700 space-y-1 shadow-md">
            <img :src="formatCaptchaSrc(captchaImage)" alt="JavDB 验证码" class="h-14 object-contain max-w-full" />
            <span class="text-[10px] text-slate-500 font-medium">点击右上角“刷新验证码”可更换图片</span>
          </div>
          <div v-else class="p-3 bg-slate-950 rounded-2xl border border-slate-800 text-center text-slate-500 italic shadow-inner">
            未检测到图形验证码（或站点当前免验证码）
          </div>

          <div>
            <label class="block text-slate-300 mb-1.5 font-bold">JavDB 账号邮箱 (Email)</label>
            <input 
              v-model="email" 
              type="text" 
              placeholder="user@example.com"
              class="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-2xl p-3 text-slate-200 outline-none shadow-inner"
            />
          </div>

          <div>
            <label class="block text-slate-300 mb-1.5 font-bold">账号密码 (Password)</label>
            <input 
              v-model="password" 
              type="password" 
              placeholder="••••••••"
              class="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-2xl p-3 text-slate-200 outline-none shadow-inner"
            />
          </div>

          <div>
            <label class="block text-slate-300 mb-1.5 font-bold">验证码 (Captcha Code)</label>
            <input 
              v-model="captcha" 
              type="text" 
              placeholder="输入上图中的验证码"
              class="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-2xl p-3 text-slate-200 outline-none shadow-inner"
            />
          </div>

          <div class="flex space-x-2.5 pt-1">
            <button 
              @click="sessionId = ''; captchaImage = '';"
              class="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-2xl font-bold transition"
            >
              重新初始化
            </button>

            <button 
              @click="submitLogin" 
              :disabled="loading"
              class="flex-1 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-extrabold rounded-2xl shadow-lg transition flex items-center justify-center space-x-2"
            >
              <CheckCircle v-if="!loading" class="w-4 h-4" />
              <RefreshCw v-else class="w-4 h-4 animate-spin" />
              <span>{{ loading ? '正在提交并抓取 Cookie...' : '第二步：提交登录' }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Mode B: Manual Cookie & Live Check -->
      <div v-else class="space-y-4 text-xs relative z-10">
        <div class="space-y-2">
          <div class="flex justify-between items-center">
            <label class="block text-slate-300 font-bold">全局 Cookie 字符串</label>
            <span class="text-[11px] text-slate-500 font-mono">长度: {{ cookieInput.length }} 字符</span>
          </div>

          <textarea 
            v-model="cookieInput" 
            rows="5" 
            placeholder="粘贴从浏览器复制的 JavDB Cookie (_jdb_session=...; remembered_token=...)"
            class="w-full bg-slate-950 border border-slate-800 focus:border-indigo-500 rounded-2xl p-3.5 text-slate-200 font-mono text-xs outline-none transition shadow-inner"
          ></textarea>
        </div>

        <div class="flex space-x-2.5">
          <button 
            @click="handleCheckCookie" 
            :disabled="checking"
            class="flex-1 py-2.5 bg-slate-800 hover:bg-slate-700 active:scale-95 text-indigo-300 font-bold rounded-2xl border border-slate-700/60 transition flex items-center justify-center space-x-1.5"
          >
            <ShieldCheck class="w-4 h-4" />
            <span>{{ checking ? '正在检测...' : '仅检测有效性' }}</span>
          </button>

          <button 
            @click="handleSaveCookie" 
            class="flex-1 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 active:scale-95 text-white font-extrabold rounded-2xl shadow-lg transition flex items-center justify-center space-x-1.5"
          >
            <Save class="w-4 h-4" />
            <span>保存并存储配置</span>
          </button>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { X, Key, RefreshCw, RotateCw, CheckCircle, ShieldCheck, Save } from '@lucide/vue';
import api, { getSavedCookie, saveCookieToStorage, formatApiError } from '../api';

const emit = defineEmits(['close', 'cookie-updated']);

const mode = ref('simulate'); // 'simulate' or 'manual'
const loading = ref(false);
const checking = ref(false);

const sessionId = ref('');
const captchaImage = ref('');
const email = ref('');
const password = ref('');
const captcha = ref('');
const cookieInput = ref('');

onMounted(() => {
  cookieInput.value = getSavedCookie();
});

function formatCaptchaSrc(base64Str) {
  if (!base64Str) return '';
  if (base64Str.startsWith('data:image')) return base64Str;
  return `data:image/png;base64,${base64Str}`;
}

async function startSession() {
  loading.value = true;
  try {
    const res = await api.post('/user/login-start');
    if (res.data?.code === 200 && res.data?.data) {
      sessionId.value = res.data.data.session_id;
      captchaImage.value = res.data.data.captcha_image || '';
      window.$toast?.('登录会话已成功建立！', 'success');
    }
  } catch (err) {
    window.$toast?.('获取登录页面失败: ' + formatApiError(err), 'error');
  } finally {
    loading.value = false;
  }
}

async function refreshCaptcha() {
  if (!sessionId.value) return;
  loading.value = true;
  try {
    const res = await api.post('/user/login-captcha', { session_id: sessionId.value });
    if (res.data?.code === 200 && res.data?.data) {
      captchaImage.value = res.data.data.captcha_image || '';
      window.$toast?.('验证码图片已刷新', 'info');
    }
  } catch (err) {
    window.$toast?.('刷新验证码失败: ' + formatApiError(err), 'error');
  } finally {
    loading.value = false;
  }
}

async function submitLogin() {
  if (!email.value || !password.value) {
    window.$toast?.('请填写账号邮箱与密码！', 'warning');
    return;
  }
  loading.value = true;
  try {
    const payload = {
      session_id: sessionId.value,
      email: email.value,
      password: password.value,
      captcha: captcha.value
    };
    const res = await api.post('/user/login-submit', payload);
    if (res.data?.code === 200 && res.data?.data) {
      const fetchedCookie = res.data.data.cookies;
      if (fetchedCookie) {
        saveCookieToStorage(fetchedCookie);
        cookieInput.value = fetchedCookie;
        window.$toast?.('JavDB 模拟登录成功！已自动保持 Cookie', 'success');
        emit('cookie-updated', fetchedCookie);
        emit('close');
      } else {
        window.$toast?.(res.data.data.message || '未获取到 Cookie，可能密码或验证码有误', 'error');
      }
    }
  } catch (err) {
    window.$toast?.('提交登录失败: ' + formatApiError(err), 'error');
  } finally {
    loading.value = false;
  }
}

async function handleCheckCookie() {
  if (!cookieInput.value.trim()) {
    window.$toast?.('请先输入 Cookie 字符串！', 'warning');
    return;
  }
  checking.value = true;
  try {
    const res = await api.post('/user/check-login', { cookies: cookieInput.value.trim() });
    if (res.data?.code === 200 && res.data?.data) {
      if (res.data.data.is_login) {
        window.$toast?.('Cookie 验证成功！JavDB 账号处于已登录状态', 'success');
      } else {
        window.$toast?.(res.data.data.message || 'Cookie 验证未通过，可能已过期', 'error');
      }
    }
  } catch (err) {
    window.$toast?.('验证 Cookie 失败: ' + formatApiError(err), 'error');
  } finally {
    checking.value = false;
  }
}

function handleSaveCookie() {
  const val = cookieInput.value.trim();
  saveCookieToStorage(val);
  window.$toast?.('Cookie 配置已成功写回前端存储与服务端持久化！', 'success');
  emit('cookie-updated', val);
  emit('close');
}
</script>
