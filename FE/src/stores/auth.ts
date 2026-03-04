import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { AxiosError } from 'axios'
import {
  createBasicAuthToken,
  httpClient,
  setBasicAuthToken,
} from '@/core/api/httpClient'

interface AuthSession {
  username: string
  token: string
  confirmed: boolean
}

const STORAGE_KEY = 'tima.auth.session'

function readSession(): AuthSession | null {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) {
    return null
  }
  try {
    return JSON.parse(raw) as AuthSession
  } catch {
    localStorage.removeItem(STORAGE_KEY)
    return null
  }
}

function writeSession(session: AuthSession | null): void {
  if (!session) {
    localStorage.removeItem(STORAGE_KEY)
    return
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
}

function isUnauthorizedError(error: unknown): boolean {
  return error instanceof AxiosError && error.response?.status === 401
}

export const useAuthStore = defineStore('auth', () => {
  const session = ref<AuthSession | null>(readSession())
  setBasicAuthToken(session.value?.token ?? null)

  const username = computed(() => session.value?.username ?? '')
  const isAuthenticated = computed(() => session.value !== null)
  const isConfirmed = computed(() => session.value?.confirmed === true)

  function applySession(nextSession: AuthSession | null): void {
    session.value = nextSession
    writeSession(nextSession)
    setBasicAuthToken(nextSession?.token ?? null)
  }

  async function login(usernameValue: string, password: string): Promise<void> {
    await httpClient.post('/login', {
      username: usernameValue,
      password,
    })
    const token = createBasicAuthToken(usernameValue, password)
    const confirmed = await fetchConfirmationState(token, usernameValue)
    applySession({
      username: usernameValue,
      token,
      confirmed,
    })
  }

  async function register(usernameValue: string, password: string): Promise<void> {
    await httpClient.post('/users', {
      id: usernameValue,
      username: usernameValue,
      password,
    })
  }

  async function refreshConfirmationState(): Promise<void> {
    if (!session.value) {
      return
    }
    const confirmed = await fetchConfirmationState(session.value.token, session.value.username)
    applySession({
      ...session.value,
      confirmed,
    })
  }

  function logout(): void {
    applySession(null)
  }

  function updateSessionPassword(newPassword: string): void {
    if (!session.value) {
      return
    }
    const nextToken = createBasicAuthToken(session.value.username, newPassword)
    applySession({
      ...session.value,
      token: nextToken,
    })
  }

  async function fetchConfirmationState(token: string, usernameValue: string): Promise<boolean> {
    try {
      const response = await httpClient.get('/users', {
        headers: {
          Authorization: `Basic ${token}`,
        },
      })
      const users = Array.isArray(response.data) ? response.data : []
      const current = users.find((user) => user.username === usernameValue)
      return current?.confirmed === true
    } catch (error: unknown) {
      if (isUnauthorizedError(error)) {
        return false
      }
      throw error
    }
  }

  return {
    username,
    isAuthenticated,
    isConfirmed,
    login,
    logout,
    updateSessionPassword,
    register,
    refreshConfirmationState,
  }
})
