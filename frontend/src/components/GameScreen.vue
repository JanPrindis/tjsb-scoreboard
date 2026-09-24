<template>
  <div class="space-y-6 animate-in fade-in duration-300">
    <div class="bg-gray-900 rounded-[3rem] p-8 shadow-2xl flex flex-col items-center gap-6 border-4 border-gray-800">
      
      <div @dblclick="openPeriodModal" @contextmenu.prevent="openPeriodModal" title="Dvojklik pro změnu" class="text-indigo-400 font-black text-xs tracking-widest uppercase cursor-pointer hover:text-indigo-300 transition-colors px-4 py-1 bg-gray-800 rounded-full">
        {{ periodName(state.period) }}️
      </div>

      <div class="grid grid-cols-3 w-full items-center gap-2">
        <div class="flex flex-col items-center overflow-hidden">
          <div class="text-6xl font-black text-white tabular-nums cursor-pointer hover:text-gray-300 transition-colors" @dblclick="openScoreModal('home')" @contextmenu.prevent="openScoreModal('home')">
            {{ state.score_home }}
          </div>
          <div class="text-indigo-400 font-bold text-xs uppercase w-full break-words line-clamp-2 leading-tight text-center px-1">{{ state.team_home }}</div>
        </div>
        <div class="text-4xl font-black text-gray-700 text-center flex-shrink-0">:</div>
        <div class="flex flex-col items-center overflow-hidden">
          <div class="text-6xl font-black text-white tabular-nums cursor-pointer hover:text-gray-300 transition-colors" @dblclick="openScoreModal('away')" @contextmenu.prevent="openScoreModal('away')">
            {{ state.score_away }}
          </div>
          <div class="text-indigo-400 font-bold text-xs uppercase w-full break-words line-clamp-2 leading-tight text-center px-1">{{ state.team_away }}</div>
        </div>
      </div>

      <div class="bg-black/50 px-10 py-3 rounded-3xl font-mono text-5xl font-black text-yellow-400 border border-yellow-400/20 cursor-pointer hover:bg-black/70 transition-colors" @dblclick="openTimeModal" @contextmenu.prevent="openTimeModal">
        {{ String(state.minutes).padStart(2, '0') }}:{{ String(state.seconds).padStart(2, '0') }}
      </div>
    </div>

    <div class="grid grid-cols-2 gap-6">
      <div class="flex flex-col gap-2">
        <HoldButton :loading="processing" :holdTime="400" colorClass="bg-indigo-600 shadow-indigo-900/40" @confirm="quickGoal('home')">
          <span class="text-3xl font-black">+</span>
        </HoldButton>
        <HoldButton :loading="processing" :holdTime="400" colorClass="bg-indigo-900/50 text-indigo-300 hover:bg-indigo-900/70" class="!h-12 !rounded-xl !text-xs" @confirm="minusScore('home')">
          -1 GÓL
        </HoldButton>
      </div>
      <div class="flex flex-col gap-2">
        <HoldButton :loading="processing" :holdTime="400" colorClass="bg-rose-600 shadow-rose-900/40" @confirm="quickGoal('away')">
          <span class="text-3xl font-black">+</span>
        </HoldButton>
        <HoldButton :loading="processing" :holdTime="400" colorClass="bg-rose-900/50 text-rose-300 hover:bg-rose-900/70" class="!h-12 !rounded-xl !text-xs" @confirm="minusScore('away')">
          -1 GÓL
        </HoldButton>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <HoldButton :loading="processing" :colorClass="state.is_running ? 'bg-orange-500' : 'bg-emerald-600'" @confirm="toggleTime" class="!h-16 rounded-2xl">
        <div class="flex items-center gap-3">
          <span class="text-xl">{{ state.is_running ? '⏸️' : '▶️' }}</span>
          <span class="text-sm font-black uppercase">{{ state.is_running ? 'Stop' : 'Start' }}</span>
        </div>
      </HoldButton>
      <HoldButton :loading="processing" colorClass="bg-amber-500" @confirm="resetTime" class="!h-16 rounded-2xl">
        <div class="flex items-center gap-3">
          <span class="text-xl">🔄</span>
          <span class="text-sm font-black uppercase">Reset Času</span>
        </div>
      </HoldButton>
    </div>

    <div class="bg-white p-4 rounded-3xl shadow-sm space-y-3">
      <h3 class="font-black uppercase text-gray-400 text-[10px] tracking-widest text-center">Animace a Události na panelu</h3>
      <div class="flex flex-wrap gap-2">
        <HoldButton v-for="a in [
            {id: 'goal', label: 'GÓL'},
            {id: 'yellow', label: 'ŽK'},
            {id: 'red', label: 'ČK'},
            {id: 'sub', label: 'Střídání'}]" :key="a.id"
          :loading="processing"
          :holdTime="400"
          colorClass="bg-indigo-500 shadow-sm"
          class="!h-12 flex-1 min-w-[60px] !rounded-xl !text-[10px]"
          @confirm="triggerAction(a.id)"
        >
          {{ a.label }}
        </HoldButton>
      </div>
    </div>

    <div class="bg-white p-4 rounded-3xl shadow-sm space-y-3">
      <h3 class="font-black uppercase text-gray-400 text-[10px] tracking-widest text-center">Představení soupisek</h3>
      <div class="flex gap-2">
        <HoldButton :loading="processing" :holdTime="2000" colorClass="bg-indigo-600 shadow-sm" class="!h-12 flex-1 !rounded-xl !text-[10px]" @confirm="triggerShowRoster('home')">
          UKÁZAT DOMÁCÍ
        </HoldButton>
        <HoldButton :loading="processing" :holdTime="2000" colorClass="bg-rose-600 shadow-sm" class="!h-12 flex-1 !rounded-xl !text-[10px]" @confirm="triggerShowRoster('away')">
          UKÁZAT HOSTÉ
        </HoldButton>
      </div>
    </div>

    <div v-if="activeModal" class="fixed inset-0 z-[100] bg-indigo-900/80 backdrop-blur-sm flex items-center justify-center p-6" @click.self="closeModal">
      <div class="bg-white rounded-[2rem] p-6 w-full max-w-sm shadow-2xl animate-in zoom-in-95 duration-200">
        <div class="flex justify-between items-center mb-6">
           <h3 class="font-black text-indigo-900 uppercase tracking-widest text-sm">{{ modalTitle }}</h3>
           <button @click="closeModal" class="text-gray-400 hover:text-red-500 text-3xl font-light leading-none">&times;</button>
        </div>

        <div v-if="activeModal === 'period'" class="flex flex-col gap-3">
           <button v-for="(name, p) in periodOptions" :key="p" @click="savePeriod(Number(p))"
             class="p-4 rounded-xl font-bold transition-all border-2"
             :class="state.period === p ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-gray-50 text-gray-700 hover:border-indigo-200 hover:bg-indigo-50'">
             {{ name }}
           </button>
        </div>

        <div v-if="activeModal === 'score'" class="flex flex-col items-center gap-6">
           <input type="number" inputmode="numeric" min="0" max="99" v-model.number="tempScore" class="text-6xl font-black text-center bg-gray-100 w-32 py-4 rounded-2xl outline-none focus:ring-4 ring-indigo-100 transition-all">
           <button @click="saveScore" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-black py-4 rounded-xl transition-all shadow-lg shadow-indigo-200">ULOŽIT SKÓRE</button>
        </div>

        <div v-if="activeModal === 'time'" class="flex flex-col items-center gap-6">
           <div class="flex items-center gap-4 text-4xl font-black">
             <input type="number" inputmode="numeric" min="0" max="99" v-model.number="tempTimeM" class="text-center bg-gray-100 w-24 py-4 rounded-2xl outline-none focus:ring-4 ring-indigo-100 transition-all">
             <span class="text-gray-400">:</span>
             <input type="number" inputmode="numeric" min="0" max="59" v-model.number="tempTimeS" class="text-center bg-gray-100 w-24 py-4 rounded-2xl outline-none focus:ring-4 ring-indigo-100 transition-all">
           </div>
           <button @click="saveTime" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-black py-4 rounded-xl transition-all shadow-lg shadow-indigo-200">NASTAVIT ČAS</button>
        </div>

        <div v-if="activeModal === 'action'" class="flex flex-col gap-4">

           <div v-if="!pendingTeam" class="grid grid-cols-2 gap-4">
             <button @click="selectTeamForAction('home')" class="bg-indigo-600 text-white py-8 rounded-2xl font-black text-lg shadow-md hover:scale-105 transition-transform">DOMÁCÍ</button>
             <button @click="selectTeamForAction('away')" class="bg-rose-600 text-white py-8 rounded-2xl font-black text-lg shadow-md hover:scale-105 transition-transform">HOSTÉ</button>
           </div>

           <template v-else>
             <!-- SUBSTITUTION HELPER -->
             <div v-if="pendingAction === 'sub' && subStep === 1" class="bg-rose-100 text-rose-700 p-3 rounded-xl mb-3 text-center shadow-inner border border-rose-200">
               <div class="font-black text-xs uppercase tracking-widest">KROK 1/2</div>
               <div class="text-sm font-bold mt-1">Kdo jde DOLŮ? ⬇️</div>
             </div>
             <div v-if="pendingAction === 'sub' && subStep === 2" class="bg-emerald-100 text-emerald-700 p-3 rounded-xl mb-3 text-center shadow-inner border border-emerald-200">
               <div class="font-black text-xs uppercase tracking-widest">KROK 2/2</div>
               <div class="text-sm font-bold mt-1">
                 Za <span class="uppercase">{{ playerOff ? playerOff.last_name : 'Neznámého' }}</span> NA HŘIŠTĚ? ⬆️
               </div>
             </div>

             <div class="flex flex-col gap-2 max-h-[50vh] overflow-y-auto mb-2 p-1">
               <HoldButton v-for="p in actionPlayers" :key="p.id" :holdTime="400" @confirm="executeAction(p)"
                       :disabled="subStep === 2 && playerOff && p.id === playerOff.id"
                       :colorClass="(subStep === 2 && playerOff && p.id === playerOff.id) ? 'bg-rose-900 text-rose-300' : 'bg-indigo-600 text-white hover:bg-indigo-500'"
                       :class="['!p-0 !rounded-xl border-2 transition-all shadow-md shrink-0', (subStep === 2 && playerOff && p.id === playerOff.id) ? 'border-rose-950 opacity-50 pointer-events-none' : 'border-indigo-700']">
                 <div class="flex items-center justify-between w-full py-4 px-4">
                   <div class="flex items-center gap-4 text-left">
                     <span class="bg-black/20 text-white px-3 py-1.5 rounded-lg min-w-[3rem] text-center text-lg font-black shadow-inner">{{ p.number === 0 ? 'TR' : (p.number || '?') }}</span>
                     <span class="truncate leading-tight text-base font-black" :class="(subStep === 2 && playerOff && p.id === playerOff.id) ? 'line-through text-rose-200' : ''">{{ p.last_name || 'Neznámý' }}</span>
                   </div>
                   <div v-if="subStep === 2 && playerOff && p.id === playerOff.id" class="text-[10px] font-black bg-rose-700 px-2 py-1 rounded text-rose-100 uppercase tracking-widest shadow-inner whitespace-nowrap">
                     ⬇ DOLŮ
                   </div>
                 </div>
               </HoldButton>
             </div>
             <HoldButton :holdTime="400" @confirm="executeAction(null)" class="!w-full !p-0 !rounded-xl transition-all shadow-md" colorClass="bg-gray-700 text-white hover:bg-gray-600">
               <div class="w-full py-4 px-4 font-black uppercase tracking-widest text-center text-sm">
                 Neznámý / Bez hráče
               </div>
             </HoldButton>
           </template>

        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import HoldButton from './HoldButton.vue'
const props = defineProps(['state', 'processing', 'api', 'toast'])

const periodOptions = { 1: '1. Poločas', 2: '2. Poločas', 3: '1. Prodloužení', 4: '2. Prodloužení' }
const periodName = (p) => periodOptions[p] || `${p}. Perioda`

// --- MODAL STATE ---
const activeModal = ref(null)
const closeModal = () => { activeModal.value = null; pendingTeam.value = null; pendingAction.value = null; subStep.value = 0; playerOff.value = null }

const modalTitle = computed(() => {
  if (activeModal.value === 'period') return 'Vyberte periodu'
  if (activeModal.value === 'score') return `Skóre - ${scoreTeam.value === 'home' ? props.state.team_home : props.state.team_away}`
  if (activeModal.value === 'time') return 'Nastavit čas'
  if (activeModal.value === 'action') {
    if (pendingAction.value === 'sub' && pendingTeam.value) {
      return `STŘÍDÁNÍ - ${pendingTeam.value === 'home' ? props.state.team_home : props.state.team_away}`
    }
    const actionName = { goal: 'GÓL', yellow: 'ŽLUTÁ KARTA', red: 'ČERVENÁ KARTA' }[pendingAction.value] || 'UDÁLOST'
    if (!pendingTeam.value) return `Který tým? (${actionName})`
    return `Kdo to byl? (${pendingTeam.value === 'home' ? props.state.team_home : props.state.team_away})`
  }
  return ''
})

// --- PERIOD ---
const openPeriodModal = () => { activeModal.value = 'period' }
const savePeriod = async (p) => {
  if (!await props.api(`/api/settings/period/${p}`)) return
  props.toast('Perioda změněna')
  closeModal()
}

// --- SCORE (Manual Override) ---
const tempScore = ref(0)
const scoreTeam = ref('home')
const openScoreModal = (team) => {
  scoreTeam.value = team
  tempScore.value = team === 'home' ? props.state.score_home : props.state.score_away
  activeModal.value = 'score'
}
const saveScore = async () => {
  const num = Math.max(0, Math.min(99, parseInt(tempScore.value) || 0))
  const payload = {
    home: scoreTeam.value === 'home' ? num : props.state.score_home,
    away: scoreTeam.value === 'away' ? num : props.state.score_away
  }
  if (!await props.api('/api/score/set', payload)) return
  props.toast('Skóre uloženo')
  closeModal()
}

// --- SCORE (-1 Helper) ---
const minusScore = async (team) => {
  const payload = {
    home: team === 'home' ? Math.max(0, props.state.score_home - 1) : props.state.score_home,
    away: team === 'away' ? Math.max(0, props.state.score_away - 1) : props.state.score_away
  }
  if (!await props.api('/api/score/set', payload)) return
  props.toast('Gól odebrán!')
}

// --- TIME ---
const tempTimeM = ref(0)
const tempTimeS = ref(0)
const openTimeModal = () => {
  tempTimeM.value = props.state.minutes
  tempTimeS.value = props.state.seconds
  activeModal.value = 'time'
}
const saveTime = async () => {
  const m = Math.max(0, Math.min(99, parseInt(tempTimeM.value) || 0))
  const s = Math.max(0, Math.min(59, parseInt(tempTimeS.value) || 0))
  if (!await props.api('/api/time/set', { minutes: m, seconds: s })) return
  props.toast('Čas nastaven')
  closeModal()
}

const toggleTime = async () => {
  const isR = props.state.is_running
  if (!await props.api(isR ? '/api/time/stop' : '/api/time/start')) return
  props.toast(isR ? 'Časomíra zastavena' : 'Časomíra spuštěna')
}

const resetTime = async () => {
  if (!await props.api('/api/time/reset')) return
  props.toast('Čas vyresetován')
}

// --- ACTION / ROSTER FLOW ---
const pendingAction = ref(null)
const pendingTeam = ref(null)
const actionPlayers = ref([])
const subStep = ref(0) // 1 = player out, 2 = player in
const playerOff = ref(null)

const quickGoal = async (team) => {
  if (!await props.api(`/api/score/${team}`)) return
  props.toast('Gól přidán!')
}

const triggerShowRoster = async (team) => {
  if (!props.state.active_roster_id) {
    props.toast('Nemáš aktivní profil soupisky!', 'warning')
    return
  }
  if (!await props.api(`/api/anim/roster/${team}`)) return
  props.toast(`Soupiska odeslána na panel!`)
}

const triggerAction = async (actionType) => {
  if (!props.state.active_roster_id) {
    // Simple mode (just animation)
    if (!await props.api(`/api/anim/${actionType}`)) return
    props.toast('Odesláno na panel!')
    return
  }

  // With roster active
  pendingAction.value = actionType
  pendingTeam.value = null
  subStep.value = actionType === 'sub' ? 1 : 0
  activeModal.value = 'action'
}

const selectTeamForAction = async (team) => {
  pendingTeam.value = team
  await loadPlayersForTeam(team)
}

watch(() => props.state.rosters_version, () => {
  if (activeModal.value === 'action' && pendingTeam.value) {
    loadPlayersForTeam(pendingTeam.value)
  }
})

const loadPlayersForTeam = async (team) => {
  const res = await fetch('/api/rosters/active', { headers: { 'Authorization': `Bearer ${localStorage.getItem('scoreboard_token')}` }})
  if (res.ok) {
    const data = await res.json()
    let players = team === 'home' ? data.home : data.away
    
    // Do not show coaches as goalscorers
    if (pendingAction.value === 'goal') {
      players = players.filter(p => p.number !== 0)
    }

    // Order player by number, 0 (Coach) goes to the end
    players.sort((a, b) => {
      const numA = (!a.number || a.number === 0) ? 999 : a.number
      const numB = (!b.number || b.number === 0) ? 999 : b.number
      return numA - numB
    })

    actionPlayers.value = players
  }
}

const executeAction = async (player) => {
  // Intercept first step of substitution
  if (pendingAction.value === 'sub' && subStep.value === 1) {
    playerOff.value = player
    subStep.value = 2
    return
  }
  
  // Prevent same-player selection
  if (pendingAction.value === 'sub' && subStep.value === 2 && player && playerOff.value && player.id === playerOff.value.id) {
    props.toast('Tento hráč už ze hřiště odchází!', 'warning')
    return
  }

  const payload = {
    action: pendingAction.value,
    team: pendingTeam.value,
    player_id: player ? player.id : null,
    player_name: player ? player.last_name : null,
    player_number: player ? player.number : null,
    player_out_name: (pendingAction.value === 'sub' && playerOff.value) ? playerOff.value.last_name : null,
    player_out_number: (pendingAction.value === 'sub' && playerOff.value) ? playerOff.value.number : null
  }

  closeModal()

  if (!await props.api('/api/action/goal_player', payload)) return
  props.toast('Akce dokončena na panelu!')
}
</script>