<template>
  <div class="space-y-6 animate-in fade-in duration-300">

    <div class="bg-white p-6 rounded-3xl shadow-sm space-y-4">
      <h3 class="font-black uppercase text-gray-400 text-xs tracking-widest">Týmy</h3>
      <div class="space-y-3">
        <input v-model="localTeams.home" placeholder="Domácí" maxlength="30" class="w-full bg-gray-50 border-2 border-gray-100 rounded-2xl px-5 py-3 font-bold focus:border-indigo-500 outline-none transition-all">
        <input v-model="localTeams.away" placeholder="Hosté" maxlength="30" class="w-full bg-gray-50 border-2 border-gray-100 rounded-2xl px-5 py-3 font-bold focus:border-indigo-500 outline-none transition-all">
      </div>
      <HoldButton :loading="processing" :holdTime="1000" colorClass="bg-indigo-600" @confirm="saveTeams" class="!h-14 !rounded-2xl shadow-lg">
        ULOŽIT TÝMY
      </HoldButton>
    </div>

    <div class="bg-white p-6 rounded-3xl shadow-sm space-y-4">
      <h3 class="font-black uppercase text-gray-400 text-xs tracking-widest">Aktivní profil soupisky</h3>
      <select v-model="localRosterId" @change="saveActiveRoster" class="w-full bg-gray-50 border-2 border-gray-100 p-3 rounded-2xl font-bold focus:border-indigo-500 outline-none">
        <option :value="null">Bez soupisky</option>
        <option v-for="r in allProfiles" :key="r.id" :value="r.id">{{ r.name }}</option>
      </select>
    </div>

    <div class="bg-white p-6 rounded-3xl shadow-sm space-y-4">
      <h3 class="font-black uppercase text-gray-400 text-xs tracking-widest">Délka poločasu</h3>
      <div class="flex items-center gap-3">
        <input type="number" inputmode="numeric" min="1" max="99" v-model.number="localHalftime" class="w-full bg-gray-50 border-2 border-gray-100 rounded-2xl px-5 py-3 text-center text-xl font-black focus:border-indigo-500 outline-none transition-all">
        <span class="font-black text-gray-400 shrink-0">MIN</span>
      </div>
      <HoldButton :loading="processing" :holdTime="1000" colorClass="bg-indigo-600" @confirm="saveHalftime" class="!h-14 !rounded-2xl shadow-lg">
        ULOŽIT ČAS
      </HoldButton>
    </div>

    <div class="bg-white p-6 rounded-3xl shadow-sm space-y-4">
      <h3 class="font-black uppercase text-gray-400 text-xs tracking-widest">Nebezpečná zóna</h3>
      <HoldButton :loading="processing" :holdTime="2000" colorClass="bg-gray-800" @confirm="hardReset">
        RESET ZÁPASU (Skóre i Čas)
      </HoldButton>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, watch, onMounted } from 'vue'
import HoldButton from './HoldButton.vue'
const props = defineProps(['state', 'processing', 'api', 'toast'])

const localTeams = reactive({ home: props.state.team_home, away: props.state.team_away })
const localHalftime = ref(props.state.halftime_length || 45)

const localRosterId = ref(props.state.active_roster_id)
const allProfiles = ref([])

const fetchProfiles = async () => {
  const res = await fetch('/api/rosters', { headers: { 'Authorization': `Bearer ${localStorage.getItem('scoreboard_token')}` }})
  if (res.ok) {
    allProfiles.value = await res.json()
  }
}

// Load roster from DB
onMounted(fetchProfiles)
watch(() => props.state.rosters_version, fetchProfiles)

watch(() => props.state.team_home, (val) => { if (val) localTeams.home = val }, { immediate: true })
watch(() => props.state.team_away, (val) => { if (val) localTeams.away = val }, { immediate: true })
watch(() => props.state.halftime_length, (val) => { if (val) localHalftime.value = val }, { immediate: true })
watch(() => props.state.active_roster_id, (val) => { localRosterId.value = val })

const saveTeams = async () => {
  const h = String(localTeams.home || '').substring(0, 30)
  const a = String(localTeams.away || '').substring(0, 30)
  if (!await props.api('/api/teams/set', { is_away: false, name: h })) return
  if (!await props.api('/api/teams/set', { is_away: true, name: a })) return
  props.toast('Týmy uloženy')
}

const saveHalftime = async () => {
  const val = Number(localHalftime.value) || 45
  if (!await props.api(`/api/settings/halftime/${val}`)) return
  props.toast('Délka poločasu uložena')
}

const saveActiveRoster = async () => {
  props.toast('Aktivuji profil a posílám na panel... čekejte', 'info')
  if (!await props.api('/api/settings/active_roster', { roster_id: localRosterId.value })) return
  props.toast('Aktivní profil soupisky změněn a synchronizován')
}

const hardReset = async () => {
  if (!await props.api('/api/score/reset')) return
  if (!await props.api('/api/settings/period/1')) return
  if (!await props.api('/api/time/reset')) return
  props.toast('Zápas resetován')
}
</script>