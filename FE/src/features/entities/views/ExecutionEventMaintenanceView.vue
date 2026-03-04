<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import ToggleButton from 'primevue/togglebutton'
import ToggleSwitch from 'primevue/toggleswitch'
import { AxiosError } from 'axios'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAppToast } from '@/core/ui/appToast'
import EntityRelationPicker from '../components/EntityRelationPicker.vue'
import { executionEventService, type ExecutionEventPayload } from '../services/executionEventService'
import { entityDefinitions } from '../shared/entityModels'

const props = defineProps<{
  id: string
}>()
const definition = entityDefinitions.executionEvents
const router = useRouter()
const { t } = useI18n()
const { showError, showSuccess, showInfo } = useAppToast()
const isNewEntity = computed(() => props.id === t('common.newItem'))
const loading = ref(false)
const submitting = ref(false)
const deleting = ref(false)
const runningBusy = ref(false)
const name = ref('')
const editableId = ref('')
const durationMs = ref('600000')
const activated = ref(true)
const factorIds = ref<string[]>([])
const status = ref(false)
const startEventAttributes = ref<AttributeEntry[]>([])
const stopEventAttributes = ref<AttributeEntry[]>([])

interface AttributeEntry {
  key: string
  value: string
}

watch(
  () => props.id,
  async () => {
    if (isNewEntity.value) {
      resetForm()
      return
    }
    await loadEntity()
  },
  { immediate: true },
)

function resetForm(): void {
  name.value = ''
  editableId.value = ''
  durationMs.value = '600000'
  activated.value = true
  factorIds.value = []
  status.value = false
  startEventAttributes.value = []
  stopEventAttributes.value = []
}

function infoTitle(key: string): string {
  return t(key)
}

function showFieldInfo(key: string): void {
  showInfo(t(key))
}

async function loadEntity(): Promise<void> {
  loading.value = true
  try {
    const payload = await executionEventService.getById(props.id)
    applyEntityPayload(payload)
  } catch (error: unknown) {
    showError(extractError(error))
  } finally {
    loading.value = false
  }
}

function applyEntityPayload(payload: unknown): void {
  if (!isEntityLike(payload)) {
    return
  }
  editableId.value = String(payload.id ?? '')
  name.value = String(payload.name ?? '')
  durationMs.value = String(payload.duration_ms ?? '600000')
  activated.value = Boolean(payload.activated ?? true)
  status.value = String(payload.status ?? 'OFF') === 'ON'
  factorIds.value = Array.isArray(payload.factors)
    ? payload.factors.filter((id): id is string => typeof id === 'string')
    : []
  startEventAttributes.value = toAttributeEntries(payload.start_event_attributes)
  stopEventAttributes.value = toAttributeEntries(payload.stop_event_attributes)
}

function createPayload(): ExecutionEventPayload {
  return {
    id: editableId.value.trim(),
    name: name.value.trim(),
    duration_ms: Number.parseInt(durationMs.value, 10),
    activated: activated.value,
    factor_ids: factorIds.value,
    start_event_attributes: toAttributeMap(startEventAttributes.value),
    stop_event_attributes: toAttributeMap(stopEventAttributes.value),
  }
}

function validatePayload(payload: ExecutionEventPayload): boolean {
  if (!payload.id || !payload.name || Number.isNaN(payload.duration_ms) || payload.duration_ms <= 0) {
    showError(t('entities.executionEvents.validationMessage'))
    return false
  }
  if (!validateAttributeRows(startEventAttributes.value) || !validateAttributeRows(stopEventAttributes.value)) {
    showError(t('entities.executionEvents.customAttributesValidationMessage'))
    return false
  }
  return true
}

function addStartAttribute(): void {
  startEventAttributes.value = [...startEventAttributes.value, { key: '', value: '' }]
}

function addStopAttribute(): void {
  stopEventAttributes.value = [...stopEventAttributes.value, { key: '', value: '' }]
}

function removeStartAttribute(index: number): void {
  startEventAttributes.value = startEventAttributes.value.filter((_, itemIndex) => itemIndex !== index)
}

function removeStopAttribute(index: number): void {
  stopEventAttributes.value = stopEventAttributes.value.filter((_, itemIndex) => itemIndex !== index)
}

function toAttributeEntries(source: unknown): AttributeEntry[] {
  if (!isEntityLike(source)) {
    return []
  }
  return Object.entries(source)
    .filter(([key, value]) => typeof key === 'string' && key.trim() && value !== null && value !== undefined)
    .map(([key, value]) => ({ key: key.trim(), value: String(value) }))
}

function toAttributeMap(entries: AttributeEntry[]): Record<string, string> {
  const result: Record<string, string> = {}
  for (const item of entries) {
    const key = item.key.trim()
    const value = item.value.trim()
    if (!key || !value) {
      continue
    }
    result[key] = value
  }
  return result
}

function validateAttributeRows(entries: AttributeEntry[]): boolean {
  const keys = new Set<string>()
  for (const item of entries) {
    const key = item.key.trim()
    const value = item.value.trim()
    if (!key && !value) {
      continue
    }
    if (!key || !value || keys.has(key)) {
      return false
    }
    keys.add(key)
  }
  return true
}

async function save(): Promise<void> {
  const payload = createPayload()
  if (!validatePayload(payload)) {
    return
  }

  submitting.value = true
  try {
    if (isNewEntity.value) {
      const createdPayload = await executionEventService.create(payload)
      applyEntityPayload(createdPayload)
      const createdId = resolveEntityId(createdPayload)
      if (createdId) {
        await router.replace({ name: definition.maintenanceRouteName, params: { id: createdId } })
      }
      showSuccess(t('entities.executionEvents.createSuccess'))
    } else {
      await executionEventService.update(payload)
      await loadEntity()
      showSuccess(t('entities.executionEvents.updateSuccess'))
    }
  } catch (error: unknown) {
    showError(extractError(error))
  } finally {
    submitting.value = false
  }
}

async function remove(): Promise<void> {
  if (isNewEntity.value) {
    return
  }
  deleting.value = true
  try {
    await executionEventService.remove(props.id)
    showSuccess(t('entities.executionEvents.deleteSuccess'))
    await router.push({ name: definition.overviewRouteName })
  } catch (error: unknown) {
    showError(extractError(error))
  } finally {
    deleting.value = false
  }
}

async function toggleStatus(): Promise<void> {
  if (isNewEntity.value) {
    return
  }
  runningBusy.value = true
  try {
    const action = status.value ? 'start' : 'stop'
    await executionEventService.toggleStatus(props.id, action)
  } catch (error: unknown) {
    status.value = !status.value
    showError(extractError(error))
  } finally {
    runningBusy.value = false
  }
}

function cancel(): void {
  void router.push({ name: definition.overviewRouteName })
}

function isEntityLike(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function resolveEntityId(payload: unknown): string {
  if (!isEntityLike(payload)) {
    return ''
  }
  return typeof payload.id === 'string' ? payload.id : ''
}

function extractError(error: unknown): string {
  if (error instanceof AxiosError) {
    return error.response?.data?.message ?? t('entities.loadError')
  }
  return t('entities.loadError')
}
</script>

<template>
  <section class="entity-card entity-maintenance">
    <h2 class="entity-card__title">{{ t(definition.maintenanceTitleKey) }}</h2>

    <div class="entity-maintenance__top-row">
      <div class="entity-maintenance__field">
        <label class="entity-maintenance__label entity-maintenance__label--small" for="execution-event-id">
          {{ t('entities.executionEvents.fields.id') }}
          <button
            type="button"
            class="entity-maintenance__info"
            :title="infoTitle('entities.executionEvents.info.id')"
            :aria-label="infoTitle('entities.executionEvents.info.id')"
            @click="showFieldInfo('entities.executionEvents.info.id')"
          >
            <FontAwesomeIcon icon="fa-solid fa-circle-info" />
          </button>
        </label>
        <InputText
          id="execution-event-id"
          v-model="editableId"
          :disabled="!isNewEntity || loading"
          class="entity-maintenance__id-input"
        />
      </div>

      <div class="entity-maintenance__field entity-maintenance__status-field">
        <label class="entity-maintenance__label" for="execution-event-status">
          {{ t('entities.executionEvents.fields.status') }}
          <button
            type="button"
            class="entity-maintenance__info"
            :title="infoTitle('entities.executionEvents.info.status')"
            :aria-label="infoTitle('entities.executionEvents.info.status')"
            @click="showFieldInfo('entities.executionEvents.info.status')"
          >
            <FontAwesomeIcon icon="fa-solid fa-circle-info" />
          </button>
        </label>
        <ToggleButton
          id="execution-event-status"
          class="entity-maintenance__running-toggle"
          :model-value="status"
          :on-label="t('common.on')"
          :off-label="t('common.off')"
          :disabled="isNewEntity || runningBusy || loading"
          @update:model-value="status = $event; void toggleStatus()"
        />
      </div>
    </div>

    <div class="entity-maintenance__field">
      <label class="entity-maintenance__label" for="execution-event-name">
        {{ t('entities.executionEvents.fields.name') }}
        <button
          type="button"
          class="entity-maintenance__info"
          :title="infoTitle('entities.executionEvents.info.name')"
          :aria-label="infoTitle('entities.executionEvents.info.name')"
          @click="showFieldInfo('entities.executionEvents.info.name')"
        >
          <FontAwesomeIcon icon="fa-solid fa-circle-info" />
        </button>
      </label>
      <InputText id="execution-event-name" v-model="name" :disabled="loading" />
    </div>

    <div class="entity-maintenance__field">
      <label class="entity-maintenance__label" for="execution-event-duration">
        {{ t('entities.executionEvents.fields.duration') }}
        <button
          type="button"
          class="entity-maintenance__info"
          :title="infoTitle('entities.executionEvents.info.duration')"
          :aria-label="infoTitle('entities.executionEvents.info.duration')"
          @click="showFieldInfo('entities.executionEvents.info.duration')"
        >
          <FontAwesomeIcon icon="fa-solid fa-circle-info" />
        </button>
      </label>
      <InputText id="execution-event-duration" v-model="durationMs" inputmode="numeric" :disabled="loading" />
    </div>

    <div class="entity-maintenance__field">
      <label class="entity-maintenance__label">
        {{ t('entities.executionEvents.fields.factors') }}
        <button
          type="button"
          class="entity-maintenance__info"
          :title="infoTitle('entities.executionEvents.info.factors')"
          :aria-label="infoTitle('entities.executionEvents.info.factors')"
          @click="showFieldInfo('entities.executionEvents.info.factors')"
        >
          <FontAwesomeIcon icon="fa-solid fa-circle-info" />
        </button>
      </label>
      <EntityRelationPicker
        v-model="factorIds"
        endpoint-path="/factors"
        find-path="/factors/find"
        placeholder-key="entities.executionEvents.factorsPlaceholder"
      />
    </div>

    <div class="entity-maintenance__field">
      <label class="entity-maintenance__label" for="execution-event-activated">
        {{ t('entities.executionEvents.fields.activated') }}
        <button
          type="button"
          class="entity-maintenance__info"
          :title="infoTitle('entities.executionEvents.info.activated')"
          :aria-label="infoTitle('entities.executionEvents.info.activated')"
          @click="showFieldInfo('entities.executionEvents.info.activated')"
        >
          <FontAwesomeIcon icon="fa-solid fa-circle-info" />
        </button>
      </label>
      <ToggleSwitch id="execution-event-activated" v-model="activated" :disabled="loading" />
    </div>

    <div class="entity-maintenance__field">
      <label class="entity-maintenance__label">
        {{ t('entities.executionEvents.fields.customEventAttributes') }}
        <button
          type="button"
          class="entity-maintenance__info"
          :title="infoTitle('entities.executionEvents.info.customEventAttributes')"
          :aria-label="infoTitle('entities.executionEvents.info.customEventAttributes')"
          @click="showFieldInfo('entities.executionEvents.info.customEventAttributes')"
        >
          <FontAwesomeIcon icon="fa-solid fa-circle-info" />
        </button>
      </label>

      <div class="entity-maintenance__attributes-group">
        <div class="entity-maintenance__attributes-block">
          <div class="entity-maintenance__attributes-header">
            <span>{{ t('entities.executionEvents.fields.startEventAttributes') }}</span>
            <Button size="small" severity="secondary" :label="t('common.add')" :disabled="loading" @click="addStartAttribute" />
          </div>
          <div v-for="(item, index) in startEventAttributes" :key="`start-${index}`" class="entity-maintenance__attribute-row">
            <InputText v-model="item.key" :placeholder="t('entities.executionEvents.customAttributeKeyPlaceholder')" :disabled="loading" />
            <InputText v-model="item.value" :placeholder="t('entities.executionEvents.customAttributeValuePlaceholder')" :disabled="loading" />
            <Button
              size="small"
              severity="danger"
              :label="t('common.remove')"
              :disabled="loading"
              @click="removeStartAttribute(index)"
            />
          </div>
        </div>

        <div class="entity-maintenance__attributes-block">
          <div class="entity-maintenance__attributes-header">
            <span>{{ t('entities.executionEvents.fields.stopEventAttributes') }}</span>
            <Button size="small" severity="secondary" :label="t('common.add')" :disabled="loading" @click="addStopAttribute" />
          </div>
          <div v-for="(item, index) in stopEventAttributes" :key="`stop-${index}`" class="entity-maintenance__attribute-row">
            <InputText v-model="item.key" :placeholder="t('entities.executionEvents.customAttributeKeyPlaceholder')" :disabled="loading" />
            <InputText v-model="item.value" :placeholder="t('entities.executionEvents.customAttributeValuePlaceholder')" :disabled="loading" />
            <Button
              size="small"
              severity="danger"
              :label="t('common.remove')"
              :disabled="loading"
              @click="removeStopAttribute(index)"
            />
          </div>
        </div>
      </div>
    </div>

    <footer class="entity-maintenance__footer">
      <Button severity="secondary" :label="t('common.cancel')" @click="cancel">
        <template #icon>
          <FontAwesomeIcon icon="fa-solid fa-xmark" />
        </template>
      </Button>
      <Button severity="danger" :label="t('common.delete')" :disabled="isNewEntity" :loading="deleting" @click="void remove()">
        <template #icon>
          <FontAwesomeIcon icon="fa-solid fa-trash" />
        </template>
      </Button>
      <Button :label="t('common.save')" :loading="submitting" @click="void save()">
        <template #icon>
          <FontAwesomeIcon icon="fa-solid fa-floppy-disk" />
        </template>
      </Button>
    </footer>
  </section>
</template>

<style scoped>
.entity-maintenance {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.entity-maintenance__top-row {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 0.75rem;
}

.entity-maintenance__field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.entity-maintenance__status-field {
  align-items: flex-start;
}

.entity-maintenance__label {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.95rem;
  font-weight: 600;
}

.entity-maintenance__label--small {
  font-size: 0.75rem;
  text-transform: lowercase;
}

.entity-maintenance__info {
  border: 0;
  background: transparent;
  color: inherit;
  padding: 0;
  line-height: 1;
  cursor: help;
}

.entity-maintenance__id-input {
  width: 100%;
}

:deep(.entity-maintenance__running-toggle.p-togglebutton) {
  background: var(--p-red-100, var(--p-surface-200));
  border-color: var(--p-red-200, var(--p-surface-300));
  color: var(--p-red-900, var(--p-text-color));
}

:deep(.entity-maintenance__running-toggle.p-togglebutton.p-togglebutton-checked) {
  background: var(--p-green-100, var(--p-surface-200));
  border-color: var(--p-green-200, var(--p-surface-300));
  color: var(--p-green-900, var(--p-text-color));
}

.entity-maintenance__footer {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.entity-maintenance__attributes-group {
  display: grid;
  gap: 0.75rem;
}

.entity-maintenance__attributes-block {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.entity-maintenance__attributes-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.entity-maintenance__attribute-row {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 0.5rem;
  padding: 0.65rem;
  border: 1px solid var(--p-surface-300);
  border-radius: 0.5rem;
  background: var(--p-surface-100);
}

@media (max-width: 820px) {
  .entity-maintenance__top-row {
    grid-template-columns: 1fr;
  }

  .entity-maintenance__attribute-row {
    grid-template-columns: 1fr;
  }
}
</style>
