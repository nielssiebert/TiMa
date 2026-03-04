<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import ToggleButton from 'primevue/togglebutton'
import { AxiosError } from 'axios'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAppToast } from '@/core/ui/appToast'
import EntityRelationPicker from '../components/EntityRelationPicker.vue'
import {
  executionEventGroupService,
  type ExecutionEventGroupPayload,
} from '../services/executionEventGroupService'
import { entityDefinitions } from '../shared/entityModels'
import { isEntityLike, resolveEntityId } from '../shared/maintenanceEntityUtils'

const props = defineProps<{
  id: string
}>()

const definition = entityDefinitions.executionEventGroups
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
const executionEventIds = ref<string[]>([])
const status = ref(false)

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
  executionEventIds.value = []
  status.value = false
}

async function loadEntity(): Promise<void> {
  loading.value = true
  try {
    const payload = await executionEventGroupService.getById(props.id)
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
  executionEventIds.value = Array.isArray(payload.execution_events)
    ? payload.execution_events.filter((id): id is string => typeof id === 'string')
    : []
  status.value = String(payload.status ?? 'OFF') === 'ON'
}

function createPayload(): ExecutionEventGroupPayload {
  return {
    id: editableId.value.trim(),
    name: name.value.trim(),
    execution_event_ids: executionEventIds.value,
  }
}

function validatePayload(payload: ExecutionEventGroupPayload): boolean {
  if (!payload.id || !payload.name) {
    showError(t('entities.executionEventGroups.validationMessage'))
    return false
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
      const createdPayload = await executionEventGroupService.create(payload)
      applyEntityPayload(createdPayload)
      const createdId = resolveEntityId(createdPayload)
      if (createdId) {
        await router.replace({ name: definition.maintenanceRouteName, params: { id: createdId } })
      }
      showSuccess(t('entities.executionEventGroups.createSuccess'))
    } else {
      await executionEventGroupService.update(payload)
      await loadEntity()
      showSuccess(t('entities.executionEventGroups.updateSuccess'))
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
    await executionEventGroupService.remove(props.id)
    showSuccess(t('entities.executionEventGroups.deleteSuccess'))
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
    await executionEventGroupService.toggleRuntime(props.id, status.value ? 'start' : 'stop')
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
      <div class="entity-maintenance__field"><label class="entity-maintenance__label entity-maintenance__label--small" for="execution-event-group-id">{{ t('entities.executionEventGroups.fields.id') }} <button type="button" class="entity-maintenance__info" :title="t('entities.executionEventGroups.info.id')" :aria-label="t('entities.executionEventGroups.info.id')" @click="showInfo(t('entities.executionEventGroups.info.id'))"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button></label><InputText id="execution-event-group-id" v-model="editableId" class="entity-maintenance__id-input" :disabled="!isNewEntity || loading" /></div>
      <div class="entity-maintenance__field entity-maintenance__status-field"><label class="entity-maintenance__label" for="execution-event-group-status">{{ t('entities.executionEventGroups.fields.status') }} <button type="button" class="entity-maintenance__info" :title="t('entities.executionEventGroups.info.status')" :aria-label="t('entities.executionEventGroups.info.status')" @click="showInfo(t('entities.executionEventGroups.info.status'))"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button></label><ToggleButton id="execution-event-group-status" :model-value="status" :on-label="t('common.on')" :off-label="t('common.off')" :disabled="isNewEntity || runningBusy || loading" class="entity-maintenance__running-toggle" @update:model-value="status = $event; void toggleStatus()" /></div>
    </div>
    <div class="entity-maintenance__field"><label class="entity-maintenance__label" for="execution-event-group-name">{{ t('entities.executionEventGroups.fields.name') }} <button type="button" class="entity-maintenance__info" :title="t('entities.executionEventGroups.info.name')" :aria-label="t('entities.executionEventGroups.info.name')" @click="showInfo(t('entities.executionEventGroups.info.name'))"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button></label><InputText id="execution-event-group-name" v-model="name" :disabled="loading" /></div>
    <div class="entity-maintenance__field"><label class="entity-maintenance__label">{{ t('entities.executionEventGroups.fields.executionEvents') }} <button type="button" class="entity-maintenance__info" :title="t('entities.executionEventGroups.info.executionEvents')" :aria-label="t('entities.executionEventGroups.info.executionEvents')" @click="showInfo(t('entities.executionEventGroups.info.executionEvents'))"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button></label><EntityRelationPicker v-model="executionEventIds" endpoint-path="/execution-events" find-path="/execution-events/find" placeholder-key="entities.executionEventGroups.executionEventsPlaceholder" /></div>
    <footer class="entity-maintenance__footer"><Button severity="secondary" :label="t('common.cancel')" @click="cancel"><template #icon><FontAwesomeIcon icon="fa-solid fa-xmark" /></template></Button><Button severity="danger" :label="t('common.delete')" :disabled="isNewEntity" :loading="deleting" @click="void remove()"><template #icon><FontAwesomeIcon icon="fa-solid fa-trash" /></template></Button><Button :label="t('common.save')" :loading="submitting" @click="void save()"><template #icon><FontAwesomeIcon icon="fa-solid fa-floppy-disk" /></template></Button></footer>
  </section>
</template>

<style scoped>
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
</style>
