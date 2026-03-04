<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Button from 'primevue/button'
import { AxiosError } from 'axios'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useAppToast } from '@/core/ui/appToast'
import { userService } from '../services/userService'

interface UserItem {
  id: string
  username: string
  confirmed: boolean
}

const { t } = useI18n()
const authStore = useAuthStore()

const users = ref<UserItem[]>([])
const busy = ref(false)
const errorMessage = ref('')
const { showError } = useAppToast()

onMounted(async () => {
  await loadUsers()
})

async function loadUsers(): Promise<void> {
  busy.value = true
  errorMessage.value = ''
  try {
    const payload = await userService.getAll()
    users.value = normalizeUsers(payload)
  } catch (error: unknown) {
    const msg = extractErrorMessage(error)
    errorMessage.value = msg
    showError(msg)
  } finally {
    busy.value = false
  }
}

async function confirmUser(userId: string): Promise<void> {
  busy.value = true
  errorMessage.value = ''
  try {
    await userService.confirm(userId)
    await loadUsers()
  } catch (error: unknown) {
    const msg = extractErrorMessage(error)
    errorMessage.value = msg
    showError(msg)
    busy.value = false
  }
}

function normalizeUsers(payload: unknown): UserItem[] {
  if (!Array.isArray(payload)) {
    return []
  }
  return payload.map((item) => ({
    id: String(item.id ?? ''),
    username: String(item.username ?? ''),
    confirmed: Boolean(item.confirmed),
  })).filter((item) => item.username !== authStore.username)
}

function extractErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    return error.response?.data?.message ?? t('users.loadError')
  }
  return t('users.loadError')
}
</script>

<template>
  <section class="entity-card">
    <header class="entity-card__header">
      <h2 class="entity-card__title">{{ t('users.title') }}</h2>
      <Button
        severity="secondary"
        outlined
        :label="t('users.refresh')"
        :loading="busy"
        @click="loadUsers"
      />
    </header>

    <p v-if="errorMessage" class="auth-card__error">{{ errorMessage }}</p>

    <div v-if="users.length > 0" class="entity-list">
      <div v-for="user in users" :key="user.id" class="user-list__item">
        <div>
          <strong>{{ user.username }}</strong>
          <p class="user-list__status">
            {{ user.confirmed ? t('users.confirmed') : t('users.notConfirmed') }}
          </p>
        </div>
        <Button
          v-if="!user.confirmed"
          :label="t('users.confirmButton')"
          :disabled="busy"
          @click="confirmUser(user.id)"
        />
      </div>
    </div>

    <p v-else>{{ t('common.noItems') }}</p>
  </section>
</template>
