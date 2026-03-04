<script setup lang="ts">
import Drawer from 'primevue/drawer'
import { useI18n } from 'vue-i18n'
import type { MainMenuItem } from './menuItems'

const props = defineProps<{
  items: MainMenuItem[]
  compact: boolean
  phone: boolean
  visible: boolean
}>()

const emit = defineEmits<{
  (event: 'update:visible', value: boolean): void
}>()

const { t } = useI18n()

function handleRouteClick(): void {
  if (props.compact || props.phone) {
    emit('update:visible', false)
  }
}

function updateVisibility(value: boolean): void {
  emit('update:visible', value)
}
</script>

<template>
  <aside v-if="!compact && !phone" class="main-sidebar">
    <h2 class="main-sidebar__title">{{ t('app.title') }}</h2>
    <nav class="main-sidebar__nav" :aria-label="t('app.menu')">
      <RouterLink
        v-for="item in items"
        :key="item.key"
        :to="item.to"
        class="main-sidebar__link"
        active-class="main-sidebar__link--active"
      >
        {{ t(item.labelKey) }}
      </RouterLink>
    </nav>
  </aside>

  <Drawer
    v-else
    :visible="visible"
    position="left"
    modal
    :dismissable="true"
    @update:visible="updateVisibility"
  >
    <template #header>
      <h2 class="main-sidebar__title">{{ t('app.title') }}</h2>
    </template>
    <nav class="main-sidebar__nav" :aria-label="t('app.menu')">
      <RouterLink
        v-for="item in items"
        :key="item.key"
        :to="item.to"
        class="main-sidebar__link"
        active-class="main-sidebar__link--active"
        @click="handleRouteClick"
      >
        {{ t(item.labelKey) }}
      </RouterLink>
    </nav>
  </Drawer>
</template>
