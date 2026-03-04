<script setup lang="ts">
import Button from 'primevue/button'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps<{
  showBurger: boolean
}>()

defineEmits<{
  (event: 'toggle-menu'): void
}>()
</script>

<template>
  <header class="app-topbar">
    <Button
      v-if="showBurger"
      text
      rounded
      severity="secondary"
      :aria-label="t('app.menu')"
      @click="$emit('toggle-menu')"
    >
      <template #icon>
        <FontAwesomeIcon icon="fa-solid fa-bars" />
      </template>
    </Button>
    <h1 class="app-topbar__title">{{ t('app.title') }}</h1>
  </header>
</template>
