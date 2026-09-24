<template>
  <div class="flex flex-col min-h-screen bg-gray-100 font-sans antialiased select-none [-webkit-touch-callout:none] [-webkit-tap-highlight-color:transparent]">
    
    <!-- Global Toasts (Notifications) -->
    <TransitionGroup 
      name="toast" 
      tag="div" 
      class="fixed top-24 left-0 right-0 z-[110] flex flex-col items-center gap-2 pointer-events-none px-4"
      enter-active-class="transition duration-300 ease-out" enter-from-class="transform -translate-y-4 opacity-0" enter-to-class="transform translate-y-0 opacity-100"
      leave-active-class="transition duration-200 ease-in" leave-from-class="transform translate-y-0 opacity-100" leave-to-class="transform -translate-y-4 opacity-0"
    >
      <div v-for="t in toasts" :key="t.id" class="bg-gray-800/95 backdrop-blur text-white px-5 py-3 rounded-full shadow-2xl font-black tracking-widest uppercase text-[10px] flex items-center gap-3">
        <span v-if="t.type === 'error'" class="text-red-500 text-sm font-bold">✗</span>
        <span v-else-if="t.type === 'warning'" class="text-yellow-500 text-sm">⚠️</span>
        <span v-else-if="t.type === 'info'" class="text-sky-400 text-sm font-bold">ℹ</span>
        <span v-else class="text-green-400 text-sm">✓</span> 
        {{ t.msg }}
      </div>
    </TransitionGroup>

    <div v-if="!token" class="fixed inset-0 z-[100] bg-indigo-900 flex items-center justify-center p-8">
      <div class="bg-white w-full max-w-sm rounded-[2.5rem] p-10 space-y-6 shadow-2xl">
        <div class="text-center space-y-2">
          <h1 class="text-4xl font-black italic tracking-tighter text-indigo-600">TJSB Tabule</h1>
          <p class="text-xs font-black text-gray-400 uppercase tracking-widest">Přihlášení do administrace</p>
        </div>
        <input type="password" v-model="loginPass" placeholder="Heslo" class="w-full bg-gray-100 rounded-2xl px-6 py-5 text-center text-3xl font-black outline-none focus:ring-4 ring-indigo-100 transition-all placeholder:text-xl placeholder:font-bold placeholder:text-gray-300">
        <button @click="handleLogin" class="w-full bg-indigo-600 text-white font-black py-5 rounded-2xl shadow-xl active:scale-95 transition-all">VSTOUPIT</button>
        <p v-if="loginError" class="text-red-500 text-center font-bold animate-pulse">{{ loginError }}</p>
      </div>
    </div>

    <template v-else>
      <header class="bg-white/80 backdrop-blur-md border-b px-6 py-4 flex justify-between items-center sticky top-0 z-[60]">
        <div class="font-black italic text-xl text-indigo-600">TJSB Tabule</div>
        <button @click="showSystemModal = true" class="flex items-center gap-2 bg-gray-100 px-3 py-1.5 rounded-full hover:bg-gray-200 active:scale-95 transition-all shadow-sm border border-gray-200 cursor-pointer" title="Systém">
          <div :class="wsConnected ? 'bg-green-500' : 'bg-red-500'" class="w-2.5 h-2.5 rounded-full"></div>
          <span class="text-[10px] font-black uppercase text-gray-500">{{ wsConnected ? 'Live' : 'Offline' }}</span>
        </button>
      </header>

      <div v-if="!wsConnected" class="fixed inset-0 z-[55] bg-gray-100/80 backdrop-blur-sm flex flex-col items-center justify-center animate-in fade-in duration-300">
        <div class="bg-white p-8 rounded-[2.5rem] shadow-2xl flex flex-col items-center gap-5 text-center border border-gray-100 mt-16 max-w-[80%]">
          <svg class="w-12 h-12 text-indigo-600 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <div>
            <h2 class="text-xl font-black text-gray-800 tracking-tight">Připojování</h2>
            <p class="text-[10px] font-bold text-gray-400 uppercase tracking-widest mt-2 leading-relaxed">Čekám na spojení<br>se serverem...</p>
          </div>
        </div>
      </div>

      <div v-else-if="boardState.is_syncing" class="fixed inset-0 z-[55] bg-gray-100/80 backdrop-blur-sm flex flex-col items-center justify-center animate-in fade-in duration-300">
        <div class="bg-white p-8 rounded-[2.5rem] shadow-2xl flex flex-col items-center gap-5 text-center border border-gray-100 mt-16 w-full max-w-[80%]">
          <svg class="w-12 h-12 text-indigo-600 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <div class="w-full">
            <h2 class="text-xl font-black text-gray-800 tracking-tight">Synchronizace</h2>
            
            <div class="w-full bg-gray-100 rounded-full h-3 mt-4 overflow-hidden shadow-inner">
              <div class="bg-indigo-600 h-3 rounded-full transition-all duration-300 ease-out" :style="{ width: boardState.sync_progress + '%' }"></div>
            </div>
            <p class="text-xs font-black text-indigo-600 mt-1.5">{{ boardState.sync_progress }} %</p>

            <p class="text-[10px] font-bold text-gray-400 uppercase tracking-widest mt-3 leading-relaxed">Nahrávám data na panel...<br>Prosím čekejte.</p>
          </div>
        </div>
      </div>

      <main ref="mainContainer" class="flex-1 overflow-y-auto p-4 max-w-xl mx-auto w-full pb-[calc(7rem+env(safe-area-inset-bottom))]">
        <component :is="activeComp" :state="boardState" :processing="isProcessing" :api="apiCall" :toast="showToast" />
      </main>

      <nav class="fixed bottom-0 left-0 right-0 bg-white/90 backdrop-blur-xl border-t h-[calc(5rem+env(safe-area-inset-bottom))] flex shadow-2xl z-50 px-2 pb-[calc(0.5rem+env(safe-area-inset-bottom))] pt-1">
        <button v-for="t in tabs" :key="t.id" @click="currentTab = t.id" :class="currentTab === t.id ? 'text-indigo-600' : 'text-gray-400'" class="flex-1 flex flex-col items-center justify-center gap-1 active:bg-gray-50 transition-all">
          <div :class="currentTab === t.id ? 'bg-indigo-100 text-indigo-600 scale-110' : 'bg-transparent text-gray-500 scale-100'" class="px-5 py-1.5 rounded-[1.2rem] transition-all duration-300">
            <span class="text-2xl">{{ t.icon }}</span>
          </div>
          <span class="text-[10px] font-black uppercase tracking-widest mt-0.5">{{ t.label }}</span>
        </button>
      </nav>

      <!-- SYSTEM MODAL -->
      <div v-if="showSystemModal" class="fixed inset-0 z-[100] bg-indigo-900/80 backdrop-blur-sm flex items-center justify-center p-6" @click.self="showSystemModal = false">
        <div class="bg-white rounded-[2rem] p-6 w-full max-w-sm shadow-2xl animate-in zoom-in-95 duration-200">
          <div class="flex justify-between items-center mb-6">
             <h3 class="font-black text-indigo-900 uppercase tracking-widest text-sm">Systém</h3>
             <button @click="showSystemModal = false" class="text-gray-400 hover:text-red-500 text-3xl font-light leading-none">&times;</button>
          </div>
          
          <div class="flex flex-col gap-5">
             <div class="flex flex-col items-center text-center gap-2 bg-gray-50 p-5 rounded-2xl border-2 border-gray-100">
               <div class="text-4xl mb-1">
                 {{ wsConnected ? '📡' : '⚠️' }}
               </div>
               <div class="font-black text-lg" :class="wsConnected ? 'text-green-600' : 'text-red-600'">
                 {{ wsConnected ? 'PŘIPOJENO' : 'ODPOJENO' }}
               </div>
               <p class="text-xs font-bold text-gray-400 leading-relaxed">
                 {{ wsConnected ? 'Spojení se serverem je aktivní. Data se synchronizují.' : 'Ztratili jsme spojení se serverem. Zkontrolujte připojení k internetu.' }}
               </p>
             </div>

             <div class="space-y-3 mt-2">
               <h4 class="font-black text-[10px] uppercase text-gray-400 tracking-widest text-center">Řešení problémů</h4>
               <HoldButton :holdTime="1000" colorClass="bg-sky-600 hover:bg-sky-700 shadow-md" @confirm="hardRefresh" class="!h-14 !rounded-xl">
                  <div class="flex items-center gap-2 text-xs">
                    <span>🔄</span>
                    <span>AKTUALIZOVAT APLIKACI</span>
                  </div>
               </HoldButton>
               <p class="text-[10px] text-gray-400 font-bold text-center leading-tight">
                 Podržte tlačítko pro stažení nejnovějších úprav nebo pokud aplikace nereaguje.
               </p>
             </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import GameScreen from './components/GameScreen.vue'
import SetupScreen from './components/SetupScreen.vue'
import BoardScreen from './components/BoardScreen.vue'
import RosterScreen from './components/RosterScreen.vue'
import HoldButton from './components/HoldButton.vue'

const token = ref(localStorage.getItem('scoreboard_token') || '')
const loginPass = ref(''); const loginError = ref('')
const currentTab = ref('game'); const wsConnected = ref(false); const isProcessing = ref(false)
const boardState = reactive({ score_home: 0, score_away: 0, minutes: 0, seconds: 0, period: 1, is_running: false, team_home: 'DOMÁCÍ', team_away: 'HOSTÉ', halftime_length: 45, mode: 5, brightness: 8, active_roster_id: null, rosters_version: 0, is_syncing: false, sync_progress: 0 })
const mainContainer = ref(null)
const showSystemModal = ref(false)

const tabs = [
    {id:'game', icon:'⚽', label:'Zápas'},
    {id:'roster', icon: '📋', label:'Soupisky'},
    {id:'setup', icon:'⚙️', label:'Nastavení'},
    {id:'board', icon:'📺', label:'Panel'}
]

const activeComp = computed(() => ({ game: GameScreen, roster: RosterScreen, setup: SetupScreen, board: BoardScreen }[currentTab.value]))

// Toast System
const toasts = ref([])
const showToast = (msg, type = 'success') => {
  const id = Date.now() + Math.random()
  toasts.value.push({ id, msg, type })
  setTimeout(() => { toasts.value = toasts.value.filter(t => t.id !== id) }, 2500)
}

watch(currentTab, async () => {
  await nextTick()
  setTimeout(() => {
    if (mainContainer.value) {
      mainContainer.value.scrollTop = 0
    }
  }, 10)
})

const handleLogin = async () => {
  const res = await fetch('/api/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ password: loginPass.value }) })
  const data = await res.json()
  if (res.ok) { token.value = data.access_token; localStorage.setItem('scoreboard_token', data.access_token); initWS() }
  else loginError.value = data.detail
}

const verifyToken = async () => {
  if (!token.value) return true;
  try {
    const res = await fetch('/api/state', { headers: { 'Authorization': `Bearer ${token.value}` } })
    if (res.status === 401) {
      token.value = '';
      localStorage.removeItem('scoreboard_token');
      loginPass.value = '';
      showToast('Relace vypršela. Přihlaste se znovu.', 'error');
      return false;
    }
    return true;
  } catch (e) {
    return true; // If no internet connection, allow
  }
}

const hardRefresh = () => {
  showToast('Aktualizuji systém...', 'info')
  showSystemModal.value = false
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then((registrations) => {
      for (let registration of registrations) {
        registration.unregister()
      }
    })
  }
  setTimeout(() => { window.location.reload() }, 500)
}

const apiCall = async (url, body = null, method = 'POST') => {
  if (isProcessing.value) return null;
  isProcessing.value = true
  try {
    const headers = { 'Authorization': `Bearer ${token.value}` }
    if (body !== null) headers['Content-Type'] = 'application/json'

    const res = await fetch(url, { method, headers, body: body !== null ? JSON.stringify(body) : null })

    if (!res.ok) {
      let errText = await res.text()
      try {
         const json = JSON.parse(errText)
         if (json.detail) errText = json.detail
      } catch(e) {}
      
      console.error(`[API Error] ${res.status}: ${errText}`)
      if (res.status === 401) { 
          token.value = ''; localStorage.removeItem('scoreboard_token');
          showToast('Byl jsi odhlášen. Přihlas se znovu.', 'error')
      } else {
          showToast(`Chyba: ${errText}`, 'error')
      }
      return null
    }
    
    const text = await res.text()
    return text ? JSON.parse(text) : true
  } catch (e) {
    console.error('[API Fetch Failed]', e)
    showToast('Chyba spojení se serverem', 'error')
    return null
  } finally { isProcessing.value = false }
}

let wsInstance = null
let pingInterval = null
let disconnectTimer = null
let reconnectAttempts = 0

const initWS = () => {
  if (wsInstance && (wsInstance.readyState === WebSocket.CONNECTING || wsInstance.readyState === WebSocket.OPEN)) {
    return;
  }

  let lastPongAt = Date.now()

  wsInstance = new WebSocket(`${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws?token=${token.value}`)
  wsInstance.onopen = () => {
    if (disconnectTimer) {
      clearTimeout(disconnectTimer);
      disconnectTimer = null;
    }
    wsConnected.value = true
    reconnectAttempts = 0;

    // Connection ping
    if (pingInterval) clearInterval(pingInterval);
    lastPongAt = Date.now()
    pingInterval = setInterval(() => {
      if (wsInstance && wsInstance.readyState === WebSocket.OPEN) {
        if (Date.now() - lastPongAt > 60000) {
          wsInstance.close()
          return
        }
        wsInstance.send(JSON.stringify({ type: 'ping' }))
      }
    }, 25000)
  }
  wsInstance.onclose = (e) => {
    if (pingInterval) clearInterval(pingInterval);
    if (e.code === 1008) {
      wsConnected.value = false;
      token.value = '';
      localStorage.removeItem('scoreboard_token');
      loginPass.value = '';
    } else {
      // Offline mode grace period
      if (wsConnected.value && !disconnectTimer) {
        disconnectTimer = setTimeout(() => wsConnected.value = false, 1500);
      }
      
      // Exponential backoff
      const delay = Math.min(500 * Math.pow(2, reconnectAttempts), 10000);
      reconnectAttempts++;
      
      setTimeout(() => {
        if (!wsInstance || wsInstance.readyState === WebSocket.CLOSED) initWS();
      }, delay)
    }
  }
  wsInstance.onmessage = (e) => { 
    const d = JSON.parse(e.data); 
    if (d.type === 'state') Object.assign(boardState, d) 
    if (d.type === 'roster_update') boardState.rosters_version = Date.now()
  }
}

window.addEventListener('beforeunload', () => {
  if (wsInstance) {
    if (pingInterval) clearInterval(pingInterval);
    if (disconnectTimer) clearTimeout(disconnectTimer);
    wsInstance.onclose = null
    wsInstance.close()
  }
})

onUnmounted(() => {
  if (wsInstance) {
    if (pingInterval) clearInterval(pingInterval);
    if (disconnectTimer) clearTimeout(disconnectTimer);
    wsInstance.onclose = null
    wsInstance.close()
  }
})

// Handle app resume
document.addEventListener('visibilitychange', async () => {
  if (document.visibilityState === 'visible' && token.value) {
    if (!wsInstance || wsInstance.readyState === WebSocket.CLOSED) {
      initWS();
    }
    await verifyToken();
  }
})

onMounted(async () => { 
  if (token.value && await verifyToken()) initWS() 
})
</script>