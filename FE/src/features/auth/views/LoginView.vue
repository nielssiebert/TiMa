<script setup lang="ts">
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import { useRouter } from 'vue-router'
import { AxiosError } from 'axios'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import TopBar from '@/layout/TopBar.vue'
import { useAppToast } from '@/core/ui/appToast'

const authStore = useAuthStore()
const router = useRouter()
const { t } = useI18n()

const username = ref('')
const password = ref('')
const registerMode = ref(false)
const busy = ref(false)
const successMessage = ref('')
const errorMessage = ref('')
const { showError } = useAppToast()

const submitLabel = computed(() => {
  if (registerMode.value) {
    return t('auth.createAccount')
  }
  return t('auth.loginButton')
})

function openRegisterMode(): void {
  registerMode.value = true
  successMessage.value = ''
  errorMessage.value = ''
}

function returnToLogin(): void {
  registerMode.value = false
  successMessage.value = ''
  errorMessage.value = ''
}

async function submit(): Promise<void> {
  if (busy.value) {
    return
  }
  busy.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    if (registerMode.value) {
      await authStore.register(username.value, password.value)
      successMessage.value = t('auth.registrationSuccess')
      registerMode.value = false
      return
    }

    await authStore.login(username.value, password.value)
    if (authStore.isConfirmed) {
      await router.replace('/execution-events')
      return
    }
    await router.replace('/awaiting-confirmation')
  } catch (error: unknown) {
    const msg = extractErrorMessage(error, registerMode.value)
    errorMessage.value = msg
    showError(msg)
  } finally {
    busy.value = false
  }
}

function extractErrorMessage(error: unknown, registrationMode: boolean): string {
  if (error instanceof AxiosError) {
    if (error.response?.data?.message) {
      return error.response.data.message as string
    }
    if (registrationMode) {
      return t('auth.registrationFailed')
    }
    return t('auth.invalidCredentials')
  }
  return t('auth.unexpectedError')
}
</script>

<template>
  <div class="auth-screen">
    <TopBar :show-burger="false" />
    <section class="auth-page auth-page--with-topbar">
      <form class="auth-card" @submit.prevent="submit">
        <h2 class="auth-card__title">{{ t('auth.title') }}</h2>

        <div class="auth-card__fields">
          <label class="auth-card__label" for="username">{{ t('auth.username') }}</label>
          <InputText id="username" v-model="username" autocomplete="username" />

          <label class="auth-card__label" for="password">{{ t('auth.password') }}</label>
          <Password
            id="password"
            v-model="password"
            :feedback="false"
            toggle-mask
            autocomplete="current-password"
          />
        </div>

        <p v-if="successMessage" class="auth-card__success">{{ successMessage }}</p>
        <p v-if="errorMessage" class="auth-card__error">{{ errorMessage }}</p>

        <div class="auth-card__actions">
          <Button type="submit" :label="submitLabel" :loading="busy" />
          <Button
            v-if="!registerMode"
            type="button"
            severity="secondary"
            outlined
            :label="t('auth.registerButton')"
            @click="openRegisterMode"
          />
          <Button
            v-else
            type="button"
            severity="secondary"
            outlined
            :label="t('auth.returnToLogin')"
            @click="returnToLogin"
          />
        </div>
      </form>
    </section>
  </div>
</template>
