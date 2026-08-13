<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950 p-4 font-sans select-none overflow-hidden">
    <!-- Ambient Dynamic Glowing Background Shapes -->
    <div class="absolute -top-32 -left-32 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl animate-pulse"></div>
    <div class="absolute -bottom-32 -right-32 w-96 h-96 bg-purple-600/20 rounded-full blur-3xl animate-pulse delay-1000"></div>
    <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-cyan-600/10 rounded-full blur-3xl"></div>

    <!-- Main Glassmorphism Card Container -->
    <div class="relative z-10 w-full max-w-md bg-slate-900/90 border border-slate-800/80 backdrop-blur-2xl rounded-3xl shadow-2xl p-8 space-y-7">
      
      <!-- Brand Logo / Header Icon -->
      <div class="text-center space-y-3">
        <div class="inline-flex p-4 rounded-3xl bg-gradient-to-br from-indigo-500/20 via-purple-500/10 to-transparent border border-indigo-500/30 text-indigo-400 shadow-xl shadow-indigo-500/10">
          <ShieldCheck v-if="isInitialized" class="w-10 h-10 text-indigo-400" />
          <UserPlus v-else class="w-10 h-10 text-emerald-400" />
        </div>

        <h1 class="text-2xl font-black tracking-tight text-white flex items-center justify-center space-x-2">
          <span>JavDB-Pilot</span>
          <span class="text-xs px-2.5 py-1 rounded-xl bg-indigo-500/20 text-indigo-300 font-mono font-bold border border-indigo-500/30">V1.2</span>
        </h1>
        
        <p class="text-xs text-slate-400 leading-relaxed font-medium">
          <span v-if="isInitialized">系统受安全屏障防护，请输入管理员身份凭证登录</span>
          <span v-else class="text-emerald-400 font-bold">✨ 检测到系统首次部署，请创建首位管理员账号与密码</span>
        </p>
      </div>

      <!-- Error Alert Message -->
      <transition name="fade">
        <div v-if="errorMessage" class="p-3.5 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2.5 shadow-lg">
          <AlertCircle class="w-4 h-4 shrink-0 text-rose-400" />
          <span class="font-medium">{{ errorMessage }}</span>
        </div>
      </transition>

      <!-- Form Inputs -->
      <form @submit.prevent="handleSubmit" class="space-y-4">
        <!-- Username Input -->
        <div class="space-y-1.5">
          <label class="block text-xs font-bold text-slate-300 ml-1">管理员用户名</label>
          <div class="relative">
            <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
              <User class="w-4 h-4" />
            </div>
            <input 
              v-model.trim="form.username"
              type="text" 
              required
              placeholder="请输入用户名" 
              class="w-full pl-10 pr-4 py-3 bg-slate-950/80 border border-slate-800 rounded-2xl text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition font-medium"
            />
          </div>
        </div>

        <!-- Password Input -->
        <div class="space-y-1.5">
          <label class="block text-xs font-bold text-slate-300 ml-1">管理员密码</label>
          <div class="relative">
            <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
              <Lock class="w-4 h-4" />
            </div>
            <input 
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'" 
              required
              placeholder="请输入密码" 
              class="w-full pl-10 pr-10 py-3 bg-slate-950/80 border border-slate-800 rounded-2xl text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition font-medium"
            />
            <button 
              type="button"
              @click="showPassword = !showPassword"
              class="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-500 hover:text-slate-300 transition cursor-pointer"
            >
              <EyeOff v-if="showPassword" class="w-4 h-4" />
              <Eye v-else class="w-4 h-4" />
            </button>
          </div>
        </div>

        <!-- Confirm Password Input (Only for First Time Init) -->
        <div v-if="!isInitialized" class="space-y-1.5">
          <label class="block text-xs font-bold text-slate-300 ml-1">确认管理员密码</label>
          <div class="relative">
            <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
              <KeyRound class="w-4 h-4" />
            </div>
            <input 
              v-model="form.confirmPassword"
              :type="showPassword ? 'text' : 'password'" 
              required
              placeholder="请再次输入确认密码" 
              class="w-full pl-10 pr-4 py-3 bg-slate-950/80 border border-slate-800 rounded-2xl text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition font-medium"
            />
          </div>
        </div>

        <!-- Submit Button -->
        <button 
          type="submit" 
          :disabled="loading"
          :class="[
            'w-full py-3.5 px-4 font-extrabold rounded-2xl text-xs text-white shadow-xl transition-all duration-200 flex items-center justify-center space-x-2 mt-2 cursor-pointer active:scale-95 disabled:opacity-50',
            isInitialized 
              ? 'bg-gradient-to-r from-indigo-600 via-purple-600 to-indigo-600 hover:from-indigo-500 hover:to-purple-500 shadow-indigo-600/30'
              : 'bg-gradient-to-r from-emerald-600 via-teal-600 to-emerald-600 hover:from-emerald-500 hover:to-teal-500 shadow-emerald-600/30'
          ]"
        >
          <Loader2 v-if="loading" class="w-4 h-4 animate-spin" />
          <span v-else-if="isInitialized" class="flex items-center space-x-2">
            <span>安全认证登录</span>
            <LogIn class="w-4 h-4" />
          </span>
          <span v-else class="flex items-center space-x-2">
            <span>创建账号并登录系统</span>
            <Sparkles class="w-4 h-4" />
          </span>
        </button>
      </form>

      <!-- Footer Info -->
      <div class="pt-4 border-t border-slate-800/80 text-center text-[11px] text-slate-500 font-mono">
        SQLite user.db 安全加盐哈希防护中
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { User, Lock, Eye, EyeOff, KeyRound, ShieldCheck, UserPlus, LogIn, AlertCircle, Loader2, Sparkles } from 'lucide-vue-next';
import api, { setAuthToken, formatApiError } from '../api';

const props = defineProps({
  isInitialized: {
    type: Boolean,
    default: true
  }
});

const emit = defineEmits(['login-success']);

const form = reactive({
  username: '',
  password: '',
  confirmPassword: ''
});

const showPassword = ref(false);
const showForgotModal = ref(false);
const loading = ref(false);
const errorMessage = ref('');

async function handleSubmit() {
  errorMessage.value = '';

  if (!form.username || !form.password) {
    errorMessage.value = '请填写完整的用户名与密码';
    return;
  }

  if (!props.isInitialized) {
    if (form.password.length < 4) {
      errorMessage.value = '设置的密码长度需至少 4 个字符';
      return;
    }
    if (form.password !== form.confirmPassword) {
      errorMessage.value = '两次输入的密码不一致，请重新核对';
      return;
    }
  }

  loading.value = true;
  try {
    const endpoint = props.isInitialized ? '/system/login' : '/system/auth-init';
    const payload = {
      username: form.username,
      password: form.password
    };

    const res = await api.post(endpoint, payload);
    if (res.data?.code === 200 && res.data?.data?.token) {
      setAuthToken(res.data.data.token);
      emit('login-success', res.data.data);
    } else {
      errorMessage.value = res.data?.message || '认证失败，请重试';
    }
  } catch (err) {
    errorMessage.value = formatApiError(err);
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
