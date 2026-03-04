<script setup lang="ts">
import { ref } from 'vue'
import { AxiosError } from 'axios'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Password from 'primevue/password'
import UserOverviewView from './UserOverviewView.vue'
import { userService } from '../services/userService'
import { useAuthStore } from '@/stores/auth'
import { useAppToast } from '@/core/ui/appToast'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()
const { showError, showSuccess } = useAppToast()

const showPasswordForm = ref(false)
const busy = ref(false)
const oldPassword = ref('')
const newPassword = ref('')
const errorMessage = ref('')

function logout(): void {
  authStore.logout()
  router.push('/login')
}

function openChangePassword(): void {
  showPasswordForm.value = true
  errorMessage.value = ''
}

function cancelChangePassword(): void {
  showPasswordForm.value = false
  oldPassword.value = ''
  newPassword.value = ''
  errorMessage.value = ''
}

async function submitChangePassword(): Promise<void> {
  if (!oldPassword.value || !newPassword.value) {
    errorMessage.value = t('users.passwordRequired')
    return
  }

  busy.value = true
  errorMessage.value = ''
  try {
    await userService.changePassword(oldPassword.value, newPassword.value)
    authStore.updateSessionPassword(newPassword.value)
    showSuccess(t('users.passwordChanged'))
    cancelChangePassword()
  } catch (error: unknown) {
    const message = extractErrorMessage(error)
    errorMessage.value = message
    showError(message)
  } finally {
    busy.value = false
  }
}

function extractErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    return error.response?.data?.message ?? t('users.passwordChangeError')
  }
  return t('users.passwordChangeError')
}
</script>

<template>
  <section class="entity-card user-view__actions-card">
    <header class="entity-card__header">
      <h2 class="entity-card__title">{{ t('users.userActionsTitle') }}</h2>
      <div class="entity-card__actions">
        <Button
          severity="secondary"
          outlined
          :label="t('users.changePasswordButton')"
          :disabled="busy"
          @click="openChangePassword"
        />
        <Button severity="danger" :label="t('users.logoutButton')" :disabled="busy" @click="logout" />
      </div>
    </header>

    <div v-if="showPasswordForm" class="user-view__password-form">
      <label class="auth-card__label" for="old-password">{{ t('users.oldPassword') }}</label>
      <Password
        id="old-password"
        v-model="oldPassword"
        :feedback="false"
        toggle-mask
        :placeholder="t('users.oldPassword')"
        fluid
      />

      <label class="auth-card__label" for="new-password">{{ t('users.newPassword') }}</label>
      <Password
        id="new-password"
        v-model="newPassword"
        :feedback="false"
        toggle-mask
        :placeholder="t('users.newPassword')"
        fluid
      />

      <p v-if="errorMessage" class="auth-card__error">{{ errorMessage }}</p>

      <div class="entity-card__actions">
        <Button
          severity="secondary"
          outlined
          :label="t('common.cancel')"
          :disabled="busy"
          @click="cancelChangePassword"
        />
        <Button :label="t('common.save')" :loading="busy" @click="submitChangePassword" />
      </div>
    </div>
  </section>

  <UserOverviewView />
</template>
