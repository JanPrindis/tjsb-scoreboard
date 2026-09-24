<template>
  <div class="space-y-6 animate-in fade-in duration-300 pb-10">
    <div class="bg-white p-6 rounded-3xl shadow-sm space-y-4">
      <h3 class="font-black uppercase text-gray-400 text-xs tracking-widest">Režim Panelu</h3>
      <div class="grid grid-cols-2 gap-3">
        <HoldButton v-for="m in modes" :key="m.id"
          :loading="processing"
          :holdTime="600"
          :colorClass="localMode === m.id ? 'bg-indigo-600 shadow-indigo-900/40' : 'bg-gray-800 shadow-xl'"
          class="!h-14 !rounded-2xl !text-xs"
          @confirm="setMode(m.id, m.name)">
          {{ m.name }}
        </HoldButton>
      </div>
    </div>

    <div class="bg-white p-6 rounded-3xl shadow-sm space-y-4">
      <div class="flex justify-between items-center">
        <h3 class="font-black uppercase text-gray-400 text-xs tracking-widest">Board Brightness</h3>
        <label class="flex items-center gap-2 cursor-pointer">
          <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Auto</span>
          <input type="checkbox" v-model="isAutoBrightness" class="w-5 h-5 accent-indigo-600 rounded cursor-pointer">
        </label>
      </div>
      <div class="flex items-center gap-4 transition-opacity duration-300" :class="{'opacity-40 pointer-events-none': isAutoBrightness}">
        <input type="range" min="0" max="15" v-model="localBrightness" class="flex-1 accent-indigo-600" :disabled="isAutoBrightness">
        <span class="font-black w-10 text-center" :class="isAutoBrightness ? 'text-gray-400 text-xs' : 'text-indigo-600 text-base'">{{ isAutoBrightness ? 'AUTO' : localBrightness }}</span>
      </div>
      <HoldButton :loading="processing" :holdTime="1000" colorClass="bg-indigo-600" @confirm="saveBrightness" class="!h-14 !rounded-2xl shadow-lg mt-2">
        ULOŽIT JAS
      </HoldButton>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import HoldButton from './HoldButton.vue'
const props = defineProps(['api', 'processing', 'toast', 'state'])

const modes = [
  { id: 1, name: 'VYPNUTO' },
  { id: 2, name: 'HODINY' },
  { id: 5, name: 'ZÁPAS' },
  { id: 6, name: 'SPONZOŘI' }
]

// Local state for mode kept purely for bulletproof UI reactivity
const localMode = ref(Number(props.state.mode) || 5)

watch(() => props.state.mode, (newVal) => {
  // Ignore old state from server if request is running (prevents flickering)
  if (newVal !== undefined && !props.processing) {
    localMode.value = Number(newVal)
  }
}, { immediate: true })

// Same for brightness - but handling the magic '255' value for auto brightness
const initB = Number(props.state.brightness);
const localBrightness = ref(initB === 255 ? 8 : (initB || 8))
const isAutoBrightness = ref(initB === 255)

watch(() => props.state.brightness, (newVal) => {
  if (newVal !== undefined && !props.processing) {
    const val = Number(newVal)
    isAutoBrightness.value = (val === 255)
    if (val !== 255) {
      localBrightness.value = val
    }
  }
}, { immediate: true })

const setMode = async (id, name) => {
  localMode.value = id
  await props.api(`/api/settings/mode/${id}`)
  props.toast(`Režim tabule: ${name}`)
}

const saveBrightness = async () => {
  const val = isAutoBrightness.value ? 255 : localBrightness.value
  if (!await props.api(`/api/settings/brightness/${val}`)) return
  props.toast(isAutoBrightness.value ? `Automatický jas zapnut` : `Jas nastaven na úroveň ${val}`)
}
</script>