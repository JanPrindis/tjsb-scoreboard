<template>
  <button
    @mousedown="startHold"
    @mouseup="stopHold"
    @mouseleave="stopHold"
    @touchstart="startHold"
    @touchmove="handleTouchMove"
    @touchend="stopHold"
    @touchcancel="stopHold"
    @contextmenu.prevent
    :disabled="loading"
    class="group relative h-20 w-full overflow-hidden rounded-[2rem] font-black uppercase tracking-widest text-white shadow-xl transition-all active:scale-95 disabled:active:scale-100 disabled:opacity-90 select-none [-webkit-touch-callout:none] [-webkit-tap-highlight-color:transparent]"
    :class="[colorClass, loading ? 'cursor-wait' : 'cursor-pointer']"
  >
    <div
      class="absolute inset-0 z-0 bg-white/30 transition-none"
      :style="{ width: progress + '%' }"
    ></div>

    <div class="relative z-20 flex items-center justify-center gap-3">
      <svg v-if="loading" class="h-8 w-8 animate-spin text-white" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <slot v-else></slot>
    </div>
  </button>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  loading: Boolean,
  holdTime: { type: Number, default: 600 },
  colorClass: { type: String, default: 'bg-indigo-600' }
})

const emit = defineEmits(['confirm'])
const progress = ref(0)
let startTime = null
let animationFrame = null
let startX = 0
let startY = 0

const animate = (currentTime) => {
  if (!startTime) startTime = currentTime
  const elapsed = currentTime - startTime
  progress.value = Math.min((elapsed / props.holdTime) * 100, 100)

  if (progress.value < 100) {
    animationFrame = requestAnimationFrame(animate)
  } else {
    emit('confirm')
    // Reset startTime so next press starts from zero,
    // but keep progress at 100% until loading starts
  }
}

const startHold = (e) => {
  if (props.loading) return
  if (e && e.touches && e.touches.length > 0) {
    startX = e.touches[0].clientX
    startY = e.touches[0].clientY
  }
  progress.value = 0
  startTime = null
  animationFrame = requestAnimationFrame(animate)
}

const handleTouchMove = (e) => {
  if (!startTime || !e.touches || e.touches.length === 0) return
  const currentX = e.touches[0].clientX
  const currentY = e.touches[0].clientY
  
  // If finger moved more than 10px, user is scrolling - interrupt hold action
  if (Math.abs(currentX - startX) > 10 || Math.abs(currentY - startY) > 10) {
    stopHold()
  }
}

const stopHold = () => {
  cancelAnimationFrame(animationFrame)
  if (!props.loading) {
    progress.value = 0
  }
}

// Once loading finishes (backend replied), reset progress bar
watch(() => props.loading, (newVal) => {
  if (!newVal) progress.value = 0
})
</script>