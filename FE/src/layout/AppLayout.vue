<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import MainSidebar from './MainSidebar.vue'
import TopBar from './TopBar.vue'
import { mainMenuItems } from './menuItems'

const SMALL_WIDTH = 820

const isCompactWidth = ref(false)
const isPhone = ref(false)
const mobileMenuVisible = ref(false)

const showBurger = computed(() => isCompactWidth.value || isPhone.value)

function detectPhone(): boolean {
  const userAgent = navigator.userAgent || ''
  return /Mobi|Android|iPhone|iPod|Windows Phone/i.test(userAgent)
}

function applyResponsiveState(): void {
  isPhone.value = detectPhone()
  isCompactWidth.value = window.innerWidth <= SMALL_WIDTH

  if (!showBurger.value) {
    mobileMenuVisible.value = false
  }
}

function toggleMenu(): void {
  mobileMenuVisible.value = !mobileMenuVisible.value
}

onMounted(() => {
  applyResponsiveState()
  window.addEventListener('resize', applyResponsiveState)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', applyResponsiveState)
})
</script>

<template>
  <div class="app-shell">
    <MainSidebar
      :items="mainMenuItems"
      :compact="isCompactWidth"
      :phone="isPhone"
      :visible="mobileMenuVisible"
      @update:visible="mobileMenuVisible = $event"
    />

    <div class="app-content-wrap">
      <TopBar :show-burger="showBurger" @toggle-menu="toggleMenu" />
      <main class="app-content">
        <RouterView />
      </main>
    </div>
  </div>
</template>
