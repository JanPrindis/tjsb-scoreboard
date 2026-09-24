<template>
  <div class="space-y-6 animate-in fade-in duration-300">

    <div class="bg-white p-4 sm:p-6 rounded-2xl sm:rounded-3xl shadow-sm space-y-4">
      <div class="flex justify-between items-center px-1 sm:px-0">
        <h3 class="font-black uppercase text-gray-400 text-xs tracking-widest">Editace Profilu</h3>
        <button @click="createNewProfile" class="text-indigo-600 font-bold text-xs bg-indigo-50 px-3 py-1 rounded-lg hover:bg-indigo-100">+ Nový</button>
      </div>

      <select v-model="selectedProfileId" @change="loadProfile" class="w-full bg-gray-50 border-2 border-gray-100 rounded-xl sm:rounded-2xl px-3 sm:px-5 py-3 font-bold text-sm sm:text-base focus:border-indigo-500 outline-none">
        <option :value="null" disabled>Vyberte profil</option>
        <option v-for="r in allProfiles" :key="r.id" :value="r.id">{{ r.name }}</option>
      </select>
    </div>

    <template v-if="selectedProfileId">
      
      <!-- FLOATING ELEMENT FOR UNSAVED CHANGES -->
      <Teleport to="body">
        <div v-if="hasUnsavedChanges" class="fixed bottom-[calc(5.5rem+env(safe-area-inset-bottom))] left-1/2 -translate-x-1/2 w-[calc(100%-1rem)] sm:w-[calc(100%-2rem)] max-w-xl z-[60] bg-gray-900 border-2 border-yellow-500 p-2 sm:p-3 rounded-2xl sm:rounded-3xl flex justify-between items-center gap-2 shadow-2xl animate-in slide-in-from-bottom-8">
          <div class="flex items-center gap-2 sm:gap-3 px-2 min-w-0">
            <span class="text-xl sm:text-2xl animate-pulse shrink-0">⚠️</span>
            <div class="flex flex-col min-w-0">
              <span class="text-yellow-500 font-black text-[9px] sm:text-[10px] uppercase tracking-widest truncate">Pozor</span>
              <span class="text-white font-bold text-xs sm:text-sm leading-none truncate">Neuložené změny</span>
            </div>
          </div>
          <button @click="saveProfile" :disabled="processing" class="bg-yellow-500 hover:bg-yellow-600 text-yellow-950 h-10 sm:h-12 px-4 sm:px-5 w-auto shrink-0 rounded-xl sm:rounded-2xl text-[10px] sm:text-xs font-black shadow-lg flex items-center justify-center transition-all active:scale-95 disabled:opacity-80">
            <svg v-if="processing" class="h-4 w-4 sm:h-5 sm:w-5 animate-spin text-yellow-950" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span v-else>ULOŽIT</span>
          </button>
        </div>
      </Teleport>

      <HoldButton v-if="state.active_roster_id === selectedProfileId && !hasUnsavedChanges" :loading="processing" :holdTime="1000" colorClass="bg-indigo-600" @confirm="syncToBoard" class="!h-14 !rounded-2xl shadow-lg">
        <div class="flex items-center gap-2">
          <span class="text-lg">📡</span>
          <span>RUČNÍ SYNCHRONIZACE</span>
        </div>
      </HoldButton>

      <div v-for="team in ['home', 'away']" :key="team" class="bg-white p-3 sm:p-6 rounded-2xl sm:rounded-3xl shadow-sm space-y-4">
        <div class="flex justify-between items-center gap-2 sm:gap-4 px-1 sm:px-0">
          <h3 class="font-black uppercase text-gray-400 text-xs tracking-widest">
            {{ team === 'home' ? 'Domácí' : 'Hosté' }}
          </h3>
          <HoldButton v-if="team === 'away'" :holdTime="1500" colorClass="bg-red-600 text-white hover:bg-red-700 shadow-sm" class="!h-8 !px-4 !w-auto shrink-0 !rounded-lg !text-[11px] font-bold" @confirm="clearTeam(team)">
            Vymazat
          </HoldButton>
        </div>

        <div class="space-y-2">
          <div v-for="(p, idx) in editableRoster[team]" :key="idx" class="flex items-center gap-1.5 sm:gap-2" :class="{'opacity-50': !p.is_active}">
            <div class="flex flex-col items-center justify-center bg-gray-50 rounded-lg px-1 py-0.5 border border-gray-200 shadow-sm shrink-0">
              <button @click="movePlayer(team, idx, -1)" :disabled="idx === 0" class="text-gray-400 hover:text-indigo-600 disabled:opacity-20 text-[10px] sm:text-xs leading-none p-1">▲</button>
              <button @click="movePlayer(team, idx, 1)" :disabled="idx === editableRoster[team].length - 1" class="text-gray-400 hover:text-indigo-600 disabled:opacity-20 text-[10px] sm:text-xs leading-none p-1">▼</button>
            </div>
            <input type="checkbox" v-model="p.is_active" class="w-5 h-5 sm:w-6 sm:h-6 rounded text-indigo-600 focus:ring-indigo-500 shrink-0 cursor-pointer">
            <input type="number" min="0" max="99" v-model="p.number" @input="p.number = (p.number === 0 || p.number === '0') ? '' : p.number" placeholder="TR" title="Nula nebo prázdné = Trenér na tabuli" 
                   class="w-12 sm:w-16 shrink-0 rounded-xl px-1 sm:px-2 py-2 text-center font-bold text-sm sm:text-base outline-none border transition-all placeholder:text-gray-800 placeholder:text-xs sm:placeholder:text-sm"
                   :class="errorFields[team][idx + '-number'] ? 'bg-red-50 border-red-500 ring-2 ring-red-200 text-red-700' : 'bg-gray-50 border-gray-200 focus:border-indigo-500'">
            <input type="text" v-model="p.last_name" placeholder="Jméno Příjmení" maxlength="51"
                   class="flex-1 min-w-0 rounded-xl px-2 sm:px-3 py-2 font-bold text-sm sm:text-base outline-none border transition-all"
                   :class="errorFields[team][idx + '-name-err'] ? 'bg-red-50 border-red-500 ring-2 ring-red-200 text-red-700' : errorFields[team][idx + '-name'] ? 'bg-sky-50 border-sky-400 ring-2 ring-sky-200 text-sky-800' : 'bg-gray-50 border-gray-200 focus:border-indigo-500'">
            <button @click="editableRoster[team].splice(idx, 1)" class="text-red-300 hover:text-red-500 px-1 sm:px-2 text-xl font-black shrink-0">&times;</button>
          </div>
        </div>

        <button @click="editableRoster[team].push({ number: '', last_name: '', first_name: '', is_active: true })" class="w-full py-3 border-2 border-dashed border-gray-200 rounded-xl text-gray-400 font-bold hover:bg-gray-50 transition-colors">
          + Přidat hráče
        </button>
      </div>

      <div class="pt-4">
        <HoldButton :loading="processing" :holdTime="2000" colorClass="bg-red-600" @confirm="deleteProfile" class="!h-12 !rounded-xl !text-xs shadow">
          Smazat celý tento profil
        </HoldButton>
      </div>
    </template>

    <!-- MODALS -->
    <div v-if="activeModal" class="fixed inset-0 z-[100] bg-indigo-900/80 backdrop-blur-sm flex items-center justify-center p-6" @click.self="closeModal">
      <div class="bg-white rounded-[2rem] p-6 w-full max-w-sm shadow-2xl animate-in zoom-in-95 duration-200">
        
        <!-- Create profile -->
        <div v-if="activeModal === 'create'" class="flex flex-col gap-4">
          <h3 class="font-black text-indigo-900 uppercase tracking-widest text-sm mb-2">Nový profil</h3>
          <input v-model="newProfileName" placeholder="Zadejte název (např. Muži A)" class="w-full bg-gray-50 border-2 border-gray-200 rounded-xl px-4 py-4 font-bold focus:border-indigo-500 outline-none text-lg">
          <div class="flex gap-3 mt-2">
            <button @click="closeModal" class="flex-1 bg-gray-100 text-gray-600 font-bold py-3 rounded-xl hover:bg-gray-200 transition-all uppercase text-sm tracking-wider">Zrušit</button>
            <button @click="confirmCreateProfile" class="flex-1 bg-indigo-600 text-white font-bold py-3 rounded-xl hover:bg-indigo-700 transition-all shadow-md uppercase text-sm tracking-wider">Vytvořit</button>
          </div>
        </div>

        <!-- WARNING (Duplicate names) -->
        <div v-if="activeModal === 'warning'" class="flex flex-col gap-4 text-center">
          <div class="text-5xl">👀</div>
          <h3 class="font-black text-sky-600 uppercase tracking-widest text-lg">Opravdu stejná jména?</h3>
          <p class="text-gray-600 font-medium whitespace-pre-wrap text-sm leading-relaxed">{{ modalMessage }}</p>
          <div class="flex gap-3 mt-2">
            <button @click="closeModal" class="flex-1 bg-gray-100 text-gray-600 font-bold py-3 rounded-xl hover:bg-gray-200 transition-all uppercase tracking-widest text-xs">Upravit</button>
            <button @click="forceSaveProfile" class="flex-1 bg-sky-500 text-white font-bold py-3 rounded-xl hover:bg-sky-600 transition-all shadow-md uppercase tracking-widest text-xs">Je to OK</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import HoldButton from './HoldButton.vue'
const props = defineProps(['state', 'processing', 'api', 'toast'])

const allProfiles = ref([])
const selectedProfileId = ref(null)
const originalRosterStr = ref('')
const editableRoster = ref({ name: '', home: [], away: [] })

// MODAL STATE
const activeModal = ref(null)
const newProfileName = ref('')
const modalMessage = ref('')
const errorFields = ref({ home: {}, away: {} })
const isInternalUpdate = ref(false)

const closeModal = () => {
  activeModal.value = null
  newProfileName.value = ''
  modalMessage.value = ''
}

const fetchProfiles = async () => {
  const res = await fetch('/api/rosters', { headers: { 'Authorization': `Bearer ${localStorage.getItem('scoreboard_token')}` }})
  if (res.ok) allProfiles.value = await res.json()
}

watch(() => props.state.rosters_version, async () => {
  if (isInternalUpdate.value) return

  await fetchProfiles()
  if (!hasUnsavedChanges.value) {
    loadProfile()
  } else {
    props.toast('Někdo jiný zrovna upravil databázi! Tvé neuložené změny nebyly přepsány.', 'warning')
  }
})

onMounted(async () => {
  await fetchProfiles()
  if (props.state.active_roster_id) {
    selectedProfileId.value = props.state.active_roster_id
    loadProfile()
  }
})

const loadProfile = () => {
  if (!selectedProfileId.value) return
  const prof = allProfiles.value.find(r => r.id === selectedProfileId.value)
  if (prof) {
    const cloned = JSON.parse(JSON.stringify(prof)) // Deep copy
    for (const t of ['home', 'away']) {
      cloned[t].forEach(p => {
        if (p.number === 0 || p.number === '0' || p.number === null) p.number = ''
      })
    }
    editableRoster.value = cloned
    originalRosterStr.value = JSON.stringify(cloned)
  }
}

const hasUnsavedChanges = computed(() => {
  if (!selectedProfileId.value) return false
  return JSON.stringify(editableRoster.value) !== originalRosterStr.value
})

const clearTeam = (team) => {
  editableRoster.value[team] = []
  props.toast(`Seznam vymazán (nezapomeň uložit do DB)`)
}

const createNewProfile = () => {
  newProfileName.value = ''
  activeModal.value = 'create'
}

const confirmCreateProfile = async () => {
  if (!newProfileName.value.trim()) return
  
  isInternalUpdate.value = true
  const payload = { name: newProfileName.value.trim(), home: [], away: [] }
  const data = await props.api('/api/rosters', payload, 'POST')

  if (data) {
    await fetchProfiles()
    selectedProfileId.value = data.id
    loadProfile()
    props.toast('Profil vytvořen')
    closeModal()
  }
  setTimeout(() => { isInternalUpdate.value = false }, 1000)
}

const movePlayer = (team, idx, direction) => {
  const arr = editableRoster.value[team]
  if (direction === -1 && idx > 0) {
    const temp = arr[idx]; arr[idx] = arr[idx - 1]; arr[idx - 1] = temp;
  } else if (direction === 1 && idx < arr.length - 1) {
    const temp = arr[idx]; arr[idx] = arr[idx + 1]; arr[idx + 1] = temp;
  }
}

const saveProfile = async () => {
  await performSave(false)
}

const forceSaveProfile = async () => {
  closeModal()
  await performSave(true)
}

const performSave = async (ignoreWarnings = false) => {
  errorFields.value = { home: {}, away: {} }
  let hasError = false
  let hasNameError = false
  let hasLengthError = false
  let hasWarning = false
  let errMsg = ''
  let warnMsg = ''

  for (const team of ['home', 'away']) {
    const numbers = new Map()
    const names = new Map()
    
    editableRoster.value[team].forEach((p, idx) => {
      if ((p.number === null || p.number === '') && (!p.last_name || p.last_name.trim() === '')) return

      const num = parseInt(p.number, 10)
      const name = (p.last_name || '').trim().toLowerCase()
      const rawName = (p.last_name || '').trim()
      
      if (!name) {
        hasNameError = true
        errorFields.value[team][`${idx}-name-err`] = true
      } else {
        // Simulate backend split for validation
        let fName = ''
        let lName = rawName
        const spaceIdx = rawName.indexOf(' ')
        if (spaceIdx !== -1) {
          fName = rawName.substring(0, spaceIdx)
          lName = rawName.substring(spaceIdx + 1)
        }
        if (fName.length > 20 || lName.length > 30) {
          hasLengthError = true
          errorFields.value[team][`${idx}-name-err`] = true
        }
      }

      if (num > 0 && p.is_active) {
        if (numbers.has(num)) {
          hasError = true
          errorFields.value[team][`${idx}-number`] = true
          errorFields.value[team][`${numbers.get(num)}-number`] = true
          if (!errMsg.includes(`s číslem ${num}`)) {
            errMsg += `Hráč s číslem ${num} je v týmu (${team === 'home' ? 'Domácí' : 'Hosté'}) zadán vícekrát!\n`
          }
        } else {
          numbers.set(num, idx)
        }
      }
      
      if (name) {
        if (names.has(name)) {
          if (!ignoreWarnings) {
            hasWarning = true
            errorFields.value[team][`${idx}-name`] = true
            errorFields.value[team][`${names.get(name)}-name`] = true
            if (!warnMsg.includes(`"${p.last_name}"`)) {
              warnMsg += `Jméno "${p.last_name}" se v týmu (${team === 'home' ? 'Domácí' : 'Hosté'}) opakuje.\n`
            }
          }
        } else {
          names.set(name, idx)
        }
      }
    })
  }

  if (hasNameError) {
    props.toast('Všichni hráči musí mít vyplněné jméno', 'error')
    return
  }

  if (hasLengthError) {
    props.toast('Jméno je moc dlouhé', 'error')
    return
  }

  if (hasError) {
    props.toast('Dva aktivní hráči nemůžou mít stejné číslo', 'error')
    return
  }

  if (hasWarning && !ignoreWarnings) {
    modalMessage.value = warnMsg
    activeModal.value = 'warning'
    return
  }

  isInternalUpdate.value = true
  props.toast('Ukládám a synchronizuji profil... čekejte', 'info')

  const cleanTeam = (team) => team.filter(p => (p.number !== null && p.number !== '') || (p.last_name && p.last_name.trim() !== ''))
    .map(p => ({
      ...p,
      number: (p.number !== null && p.number !== '') ? Math.max(0, Math.min(99, parseInt(p.number, 10))) : 0,
      first_name: p.first_name ? p.first_name.trim() : '',
      last_name: p.last_name ? p.last_name.trim() : ''
    }))

  const payload = {
    name: editableRoster.value.name,
    home: cleanTeam(editableRoster.value.home),
    away: cleanTeam(editableRoster.value.away)
  }

  if (!await props.api(`/api/rosters/${selectedProfileId.value}`, payload, 'PUT')) {
    setTimeout(() => { isInternalUpdate.value = false }, 1000)
    return
  }

  await fetchProfiles()
  loadProfile()
  errorFields.value = { home: {}, away: {} }
  props.toast('Profil uložen a synchronizován')

  setTimeout(() => { isInternalUpdate.value = false }, 1000)
}

const deleteProfile = async () => {
  isInternalUpdate.value = true
  if (await props.api(`/api/rosters/${selectedProfileId.value}`, null, 'DELETE')) {
    await fetchProfiles()
    selectedProfileId.value = null
    props.toast('Profil smazán')
  }
  setTimeout(() => { isInternalUpdate.value = false }, 1000)
}

const syncToBoard = async () => {
  if (hasUnsavedChanges.value) {
    props.toast('Nejdříve ulož změny do DB!')
    return
  }
  if (!await props.api('/api/rosters/sync')) return
}
</script>