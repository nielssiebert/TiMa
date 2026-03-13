<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import Button from 'primevue/button'
import ToggleButton from 'primevue/togglebutton'
import ToggleSwitch from 'primevue/toggleswitch'
import { AxiosError } from 'axios'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { httpClient } from '@/core/api/httpClient'
import { appConfig } from '@/core/config/appConfig'
import type { EntityListItem } from '../shared/entityModels'
import { useAppToast } from '@/core/ui/appToast'

const props = defineProps<{
  titleKey: string
  maintenanceRouteName: string
  apiPath: string
  showActivationToggle?: boolean
  activationDisabledEvaluator?: (item: Record<string, unknown>) => boolean
  showRunningToggle?: boolean
  runningStateEvaluator?: (item: Record<string, unknown>) => boolean
}>()

const router = useRouter()
const { t } = useI18n()
const items = ref<EntityListItem[]>([])
const busy = ref(false)
const activationBusyId = ref<string>('')
const errorMessage = ref('')
const { showError } = useAppToast()
let autoRefreshTimer: number | null = null

onMounted(async () => {
  await loadItems()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})

async function loadItems(): Promise<void> {
  if (busy.value) {
    return
  }
  busy.value = true
  errorMessage.value = ''
  try {
    const response = await httpClient.get(props.apiPath)
    items.value = normalizeEntityItems(response.data)
  } catch (error: unknown) {
    const msg = extractErrorMessage(error)
    errorMessage.value = msg
    showError(msg)
  } finally {
    busy.value = false
  }
}

function startAutoRefresh(): void {
  const intervalMs = resolveRefreshIntervalMs(props.apiPath)
  if (intervalMs < 1) {
    return
  }
  stopAutoRefresh()
  autoRefreshTimer = window.setInterval(() => {
    void loadItems()
  }, intervalMs)
}

function stopAutoRefresh(): void {
  if (autoRefreshTimer === null) {
    return
  }
  window.clearInterval(autoRefreshTimer)
  autoRefreshTimer = null
}

function resolveRefreshIntervalMs(apiPath: string): number {
  const configured = appConfig.overviewRefreshMs.byApiPath[apiPath]
  return typeof configured === 'number' ? configured : appConfig.overviewRefreshMs.default
}

function addItem(): void {
  router.push({
    name: props.maintenanceRouteName,
    params: { id: t('common.newItem') },
  })
}

function openItem(itemId: string): void {
  router.push({
    name: props.maintenanceRouteName,
    params: { id: itemId },
  })
}

async function toggleItemActivation(item: EntityListItem): Promise<void> {
  if (!props.showActivationToggle || typeof item.activated !== 'boolean' || isActivationToggleDisabled(item)) {
    return
  }

  activationBusyId.value = item.id
  try {
    const action = item.activated ? 'deactivate' : 'activate'
    await httpClient.post(`${props.apiPath}/${item.id}/${action}`)
    item.activated = !item.activated
  } catch (error: unknown) {
    showError(extractErrorMessage(error))
  } finally {
    activationBusyId.value = ''
  }
}

async function toggleItemRunning(item: EntityListItem): Promise<void> {
  if (!props.showRunningToggle || typeof item.isRunning !== 'boolean') {
    return
  }

  activationBusyId.value = item.id
  try {
    const action = item.isRunning ? 'stop' : 'start'
    await httpClient.post(`${props.apiPath}/${item.id}/${action}`)
    item.isRunning = !item.isRunning
  } catch (error: unknown) {
    showError(extractErrorMessage(error))
  } finally {
    activationBusyId.value = ''
  }
}

function normalizeEntityItems(payload: unknown): EntityListItem[] {
  if (!Array.isArray(payload)) {
    return []
  }

  return payload
    .map((item) => {
      if (!isEntityLike(item)) {
        return { id: '', name: '' }
      }
      return {
        id: String(item.id ?? ''),
        name: String(item.name ?? ''),
        activated: parseActivated(item.activated),
        activationDisabled: parseActivationDisabled(item),
        isRunning: parseRunningState(item),
      }
    })
    .filter((item) => item.id !== '' && item.name !== '')
}

function parseActivationDisabled(item: Record<string, unknown>): boolean {
  if (!props.showActivationToggle || !props.activationDisabledEvaluator) {
    return false
  }
  return props.activationDisabledEvaluator(item)
}

function isActivationToggleDisabled(item: EntityListItem): boolean {
  if (activationBusyId.value === item.id) {
    return true
  }
  return Boolean(item.activationDisabled)
}

function parseActivated(value: unknown): boolean | undefined {
  if (!props.showActivationToggle) {
    return undefined
  }
  return typeof value === 'boolean' ? value : false
}

function parseRunningState(item: Record<string, unknown>): boolean | undefined {
  if (!props.showRunningToggle || !props.runningStateEvaluator) {
    return undefined
  }
  return props.runningStateEvaluator(item)
}

function extractErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    return error.response?.data?.message ?? t('entities.loadError')
  }
  return t('entities.loadError')
}

function isEntityLike(item: unknown): item is {
  id?: unknown
  name?: unknown
  activated?: unknown
} {
  return typeof item === 'object' && item !== null
}
</script>

<template>
  <section class="entity-card">
    <header class="entity-card__header">
      <h2 class="entity-card__title">{{ t(titleKey) }}</h2>
      <div class="entity-card__actions">
        <Button severity="secondary" outlined :label="t('common.refresh')" :loading="busy" @click="loadItems" />
        <Button :label="t('common.add')" @click="addItem">
          <template #icon>
            <FontAwesomeIcon icon="fa-solid fa-plus" />
          </template>
        </Button>
      </div>
    </header>

    <p v-if="errorMessage" class="auth-card__error">{{ errorMessage }}</p>

    <div v-if="items.length > 0" class="entity-list">
      <div v-for="item in items" :key="item.id" class="entity-list__row">
        <Button
          class="entity-list__item"
          severity="secondary"
          outlined
          :label="item.name"
          @click="openItem(item.id)"
        />
        <ToggleSwitch
          v-if="showActivationToggle"
          :model-value="item.activated"
          :disabled="isActivationToggleDisabled(item)"
          :aria-label="t('entities.activationToggle')"
          @click.stop
          @update:model-value="void toggleItemActivation(item)"
        />
        <ToggleButton
          v-if="showRunningToggle"
          class="entity-list__running-toggle"
          :model-value="item.isRunning"
          :on-label="t('common.on')"
          :off-label="t('common.off')"
          :aria-label="t('entities.runningToggle')"
          :disabled="activationBusyId === item.id"
          @click.stop
          @update:model-value="void toggleItemRunning(item)"
        />
      </div>
    </div>

    <p v-else>{{ t('common.noItems') }}</p>
  </section>
</template>

<style scoped>
:deep(.entity-list__running-toggle.p-togglebutton) {
  background: var(--app-status-off-bg, var(--p-red-100, var(--p-surface-200)));
  border-color: var(--app-status-off-border, var(--p-red-200, var(--p-surface-300)));
  color: var(--app-status-off-text, var(--p-red-900, var(--p-text-color)));
}

:deep(.entity-list__running-toggle.p-togglebutton:not(.p-disabled):hover) {
  filter: brightness(1.06);
}

:deep(.entity-list__running-toggle.p-togglebutton.p-togglebutton-checked) {
  background: var(--app-status-on-bg, var(--p-green-100, var(--p-surface-200)));
  border-color: var(--app-status-on-border, var(--p-green-200, var(--p-surface-300)));
  color: var(--app-status-on-text, var(--p-green-900, var(--p-text-color)));
}

:deep(.entity-list__running-toggle.p-togglebutton.p-togglebutton-checked:not(.p-disabled):hover) {
  filter: brightness(1.06);
}
</style>
