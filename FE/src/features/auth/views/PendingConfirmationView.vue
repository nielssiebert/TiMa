<script setup lang="ts">
import Button from 'primevue/button'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import TopBar from '@/layout/TopBar.vue'

const authStore = useAuthStore()
const router = useRouter()
const { t } = useI18n()

async function retryAccess(): Promise<void> {
  await authStore.refreshConfirmationState()
  if (authStore.isConfirmed) {
    await router.replace('/execution-events')
  }
}

async function backToLogin(): Promise<void> {
  authStore.logout()
  await router.replace('/login')
}
</script>

<template>
  <div class="auth-screen">
    <TopBar :show-burger="false" />
    <section class="auth-page auth-page--with-topbar">
      <div class="auth-card">
        <h2 class="auth-card__title">{{ t('auth.pendingTitle') }}</h2>
        <p>{{ t('auth.pendingText') }}</p>
        <div class="auth-card__actions">
          <Button :label="t('auth.retry')" @click="retryAccess" />
          <Button
            severity="secondary"
            outlined
            :label="t('auth.returnToLogin')"
            @click="backToLogin"
          />
        </div>
      </div>
    </section>
  </div>
</template>
