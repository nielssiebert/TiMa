<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'
import { AxiosError } from 'axios'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAppToast } from '@/core/ui/appToast'
import { factorService, type FactorPayload } from '../services/factorService'
import { entityDefinitions } from '../shared/entityModels'
import { isEntityLike, resolveEntityId } from '../shared/maintenanceEntityUtils'

const props = defineProps<{
  id: string
}>()

const definition = entityDefinitions.factors
const router = useRouter()
const { t } = useI18n()
const { showError, showSuccess, showInfo } = useAppToast()
const isNewEntity = computed(() => props.id === t('common.newItem'))
const loading = ref(false)
const submitting = ref(false)
const deleting = ref(false)
const activationBusy = ref(false)
const factorBusy = ref(false)
const name = ref('')
const editableId = ref('')
const minVal = ref('')
const maxVal = ref('')
const factorValue = ref('1')
const factorEditMode = ref(false)
const activated = ref(true)

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
  minVal.value = ''
  maxVal.value = ''
  factorValue.value = '1'
  factorEditMode.value = false
  activated.value = true
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
    const payload = await factorService.getById(props.id)
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
  minVal.value = toNullableText(payload.min_val)
  maxVal.value = toNullableText(payload.max_val)
  factorValue.value = toFactorText(payload.factor)
  factorEditMode.value = false
  activated.value = Boolean(payload.activated ?? true)
}

function createPayload(): FactorPayload {
  return {
    id: editableId.value.trim(),
    name: name.value.trim(),
    min_val: parseOptionalFloat(minVal.value),
    max_val: parseOptionalFloat(maxVal.value),
  }
}

function validatePayload(payload: FactorPayload): boolean {
  if (!payload.id || !payload.name) {
    showError(t('entities.factors.validationMessage'))
    return false
  }
  if (payload.min_val !== null && payload.max_val !== null && payload.min_val > payload.max_val) {
    showError(t('entities.factors.minMaxValidationMessage'))
    return false
  }
  if (Number.isNaN(payload.min_val as number) || Number.isNaN(payload.max_val as number)) {
    showError(t('entities.factors.numberValidationMessage'))
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
      const createdPayload = await factorService.create(payload)
      applyEntityPayload(createdPayload)
      const createdId = resolveEntityId(createdPayload)
      if (createdId) {
        await router.replace({ name: definition.maintenanceRouteName, params: { id: createdId } })
      }
      showSuccess(t('entities.factors.createSuccess'))
    } else {
      await factorService.update(payload)
      await loadEntity()
      showSuccess(t('entities.factors.updateSuccess'))
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
    await factorService.remove(props.id)
    showSuccess(t('entities.factors.deleteSuccess'))
    await router.push({ name: definition.overviewRouteName })
  } catch (error: unknown) {
    showError(extractError(error))
  } finally {
    deleting.value = false
  }
}

async function toggleActivation(): Promise<void> {
  if (isNewEntity.value) {
    return
  }
  activationBusy.value = true
  try {
    const action = activated.value ? 'activate' : 'deactivate'
    await factorService.setActivation(props.id, action)
  } catch (error: unknown) {
    activated.value = !activated.value
    showError(extractError(error))
  } finally {
    activationBusy.value = false
  }
}

function beginFactorEdit(): void {
  if (isNewEntity.value || loading.value || factorBusy.value) {
    return
  }
  factorEditMode.value = true
}

async function saveFactorValue(): Promise<void> {
  if (isNewEntity.value) {
    return
  }
  const parsed = Number.parseFloat(factorValue.value.trim())
  if (Number.isNaN(parsed)) {
    showError(t('entities.factors.factorNumberValidationMessage'))
    return
  }

  factorBusy.value = true
  try {
    const payload = await factorService.updateFactorValue(props.id, parsed)
    applyEntityPayload(payload)
    showSuccess(t('entities.factors.factorUpdateSuccess'))
  } catch (error: unknown) {
    showError(extractError(error))
  } finally {
    factorBusy.value = false
    factorEditMode.value = false
  }
}

function cancel(): void {
  void router.push({ name: definition.overviewRouteName })
}

function parseOptionalFloat(value: string): number | null {
  const trimmed = value.trim()
  if (!trimmed) {
    return null
  }
  return Number.parseFloat(trimmed)
}

function toNullableText(value: unknown): string {
  if (typeof value === 'number') {
    return String(value)
  }
  return ''
}

function toFactorText(value: unknown): string {
  return typeof value === 'number' ? String(value) : '1'
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
    <div class="entity-maintenance__field"><label class="entity-maintenance__label entity-maintenance__label--small" for="factor-id">{{ t('entities.factors.fields.id') }} <button type="button" class="entity-maintenance__info" :title="infoTitle('entities.factors.info.id')" :aria-label="infoTitle('entities.factors.info.id')" @click="showFieldInfo('entities.factors.info.id')"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button></label><InputText id="factor-id" v-model="editableId" :disabled="!isNewEntity || loading" /></div>
    <div class="entity-maintenance__field"><label class="entity-maintenance__label" for="factor-name">{{ t('entities.factors.fields.name') }} <button type="button" class="entity-maintenance__info" :title="infoTitle('entities.factors.info.name')" :aria-label="infoTitle('entities.factors.info.name')" @click="showFieldInfo('entities.factors.info.name')"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button></label><InputText id="factor-name" v-model="name" :disabled="loading" /></div>
    <div class="entity-maintenance__row">
      <div class="entity-maintenance__field"><label class="entity-maintenance__label" for="factor-min-val">{{ t('entities.factors.fields.minVal') }} <button type="button" class="entity-maintenance__info" :title="infoTitle('entities.factors.info.minVal')" :aria-label="infoTitle('entities.factors.info.minVal')" @click="showFieldInfo('entities.factors.info.minVal')"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button></label><InputText id="factor-min-val" v-model="minVal" inputmode="decimal" :disabled="loading" /></div>
      <div class="entity-maintenance__field"><label class="entity-maintenance__label" for="factor-max-val">{{ t('entities.factors.fields.maxVal') }} <button type="button" class="entity-maintenance__info" :title="infoTitle('entities.factors.info.maxVal')" :aria-label="infoTitle('entities.factors.info.maxVal')" @click="showFieldInfo('entities.factors.info.maxVal')"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button></label><InputText id="factor-max-val" v-model="maxVal" inputmode="decimal" :disabled="loading" /></div>
    </div>
    <div class="entity-maintenance__field">
      <label class="entity-maintenance__label" for="factor-value">
        {{ t('entities.factors.fields.factor') }}
        <button type="button" class="entity-maintenance__info" :title="infoTitle('entities.factors.info.factor')" :aria-label="infoTitle('entities.factors.info.factor')" @click="showFieldInfo('entities.factors.info.factor')"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button>
      </label>
      <div class="entity-maintenance__inline-edit">
        <InputText id="factor-value" v-model="factorValue" inputmode="decimal" :disabled="!factorEditMode || loading || factorBusy || isNewEntity" />
        <Button v-if="!factorEditMode" text :aria-label="t('entities.factors.editFactorValue')" :disabled="isNewEntity || loading || factorBusy" @click="beginFactorEdit">
          <template #icon><FontAwesomeIcon icon="fa-solid fa-pen" /></template>
        </Button>
        <Button v-else text severity="success" :aria-label="t('entities.factors.saveFactorValue')" :loading="factorBusy" @click="void saveFactorValue()">
          <template #icon><FontAwesomeIcon icon="fa-solid fa-check" /></template>
        </Button>
      </div>
    </div>
    <div class="entity-maintenance__field"><label class="entity-maintenance__label" for="factor-activated">{{ t('entities.factors.fields.activated') }} <button type="button" class="entity-maintenance__info" :title="infoTitle('entities.factors.info.activated')" :aria-label="infoTitle('entities.factors.info.activated')" @click="showFieldInfo('entities.factors.info.activated')"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button></label><ToggleSwitch id="factor-activated" v-model="activated" :disabled="isNewEntity || loading || activationBusy" @update:model-value="void toggleActivation()" /></div>
    <footer class="entity-maintenance__footer"><Button severity="secondary" :label="t('common.cancel')" @click="cancel"><template #icon><FontAwesomeIcon icon="fa-solid fa-xmark" /></template></Button><Button severity="danger" :label="t('common.delete')" :disabled="isNewEntity" :loading="deleting" @click="void remove()"><template #icon><FontAwesomeIcon icon="fa-solid fa-trash" /></template></Button><Button :label="t('common.save')" :loading="submitting" @click="void save()"><template #icon><FontAwesomeIcon icon="fa-solid fa-floppy-disk" /></template></Button></footer>
  </section>
</template>

<style scoped>
.entity-maintenance__inline-edit {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.entity-maintenance__inline-edit :deep(.p-inputtext) {
  flex: 1;
}
</style>
