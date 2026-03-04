<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'
import { AxiosError } from 'axios'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAppToast } from '@/core/ui/appToast'
import EntityRelationPicker from '../components/EntityRelationPicker.vue'
import { triggerService, type TriggerPayload } from '../services/triggerService'
import { entityDefinitions } from '../shared/entityModels'
import { isEntityLike, resolveEntityId } from '../shared/maintenanceEntityUtils'

const props = defineProps<{
  id: string
}>()

const definition = entityDefinitions.triggers
const router = useRouter()
const { t } = useI18n()
const { showError, showSuccess, showInfo } = useAppToast()
const isNewEntity = computed(() => props.id === t('common.newItem'))
const loading = ref(false)
const submitting = ref(false)
const deleting = ref(false)
const activationBusy = ref(false)
const name = ref('')
const editableId = ref('')
const triggerType = ref<'START_AT_POINT_IN_TIME' | 'STOP_AT_POINT_IN_TIME'>('START_AT_POINT_IN_TIME')
const recurranceType = ref<'TIMER' | 'ONE_TIME' | 'WEEKLY'>('TIMER')
const weekdayOptions = ['SU', 'MO', 'TU', 'WE', 'TH', 'FR', 'SA'] as const
const date = ref('')
const time = ref('00:00:00')
const weekdays = ref<string[]>([])
const fromDate = ref('')
const toDate = ref('')
const recurring = ref(true)
const activated = ref(true)
const sequenceIds = ref<string[]>([])

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
  triggerType.value = 'START_AT_POINT_IN_TIME'
  recurranceType.value = 'TIMER'
  date.value = ''
  time.value = '00:00:00'
  weekdays.value = []
  fromDate.value = ''
  toDate.value = ''
  recurring.value = true
  activated.value = true
  sequenceIds.value = []
}

async function loadEntity(): Promise<void> {
  loading.value = true
  try {
    const payload = await triggerService.getById(props.id)
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
  triggerType.value = payload.trigger_type === 'STOP_AT_POINT_IN_TIME' ? 'STOP_AT_POINT_IN_TIME' : 'START_AT_POINT_IN_TIME'
  recurranceType.value = payload.recurrance_type === 'ONE_TIME' || payload.recurrance_type === 'WEEKLY' ? payload.recurrance_type : 'TIMER'
  date.value = typeof payload.date === 'string' ? payload.date.slice(0, 10) : ''
  time.value = normalizeTimeValue(payload.time) ?? '00:00:00'
  weekdays.value = normalizeWeekdays(payload.weekdays)
  fromDate.value = typeof payload.from_date === 'string' ? payload.from_date.slice(0, 10) : ''
  toDate.value = typeof payload.to_date === 'string' ? payload.to_date.slice(0, 10) : ''
  recurring.value = Boolean(payload.recurring ?? true)
  activated.value = Boolean(payload.activated ?? true)
  sequenceIds.value = Array.isArray(payload.sequences)
    ? payload.sequences.filter((id): id is string => typeof id === 'string')
    : []
}

function createPayload(): TriggerPayload {
  const normalizedTime = normalizeTimeValue(time.value)
  return {
    id: editableId.value.trim(),
    name: name.value.trim(),
    trigger_type: triggerType.value,
    recurrance_type: recurranceType.value,
    date: date.value || null,
    time: normalizedTime ?? null,
    weekdays: weekdays.value,
    from_date: fromDate.value || null,
    to_date: toDate.value || null,
    recurring: recurring.value,
    sequence_ids: sequenceIds.value,
  }
}

function validatePayload(payload: TriggerPayload): boolean {
  if (!payload.id || !payload.name) {
    showError(t('entities.triggers.validationMessage'))
    return false
  }
  if (!payload.time || !isValidTime(payload.time)) {
    showError(t('entities.triggers.timeValidationMessage'))
    return false
  }
  if (payload.recurrance_type === 'ONE_TIME' && !payload.date) {
    showError(t('entities.triggers.oneTimeValidationMessage'))
    return false
  }
  if (payload.recurrance_type === 'WEEKLY' && payload.weekdays.length === 0) {
    showError(t('entities.triggers.weeklyValidationMessage'))
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
      const createdPayload = await triggerService.create(payload)
      applyEntityPayload(createdPayload)
      const createdId = resolveEntityId(createdPayload)
      if (createdId) {
        await router.replace({ name: definition.maintenanceRouteName, params: { id: createdId } })
      }
      showSuccess(t('entities.triggers.createSuccess'))
    } else {
      await triggerService.update(payload)
      await loadEntity()
      showSuccess(t('entities.triggers.updateSuccess'))
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
    await triggerService.remove(props.id)
    showSuccess(t('entities.triggers.deleteSuccess'))
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
    await triggerService.setActivation(props.id, action)
  } catch (error: unknown) {
    activated.value = !activated.value
    showError(extractError(error))
  } finally {
    activationBusy.value = false
  }
}

function cancel(): void {
  void router.push({ name: definition.overviewRouteName })
}

function normalizeWeekdays(value: unknown): string[] {
  if (Array.isArray(value)) {
    return weekdayOptions.filter((day) => value.includes(day))
  }
  if (typeof value === 'string') {
    const parsed = value.split(',').map((item) => item.trim().toUpperCase())
    return weekdayOptions.filter((day) => parsed.includes(day))
  }
  return []
}

function normalizeTimeInput(): void {
  const normalizedTime = normalizeTimeValue(time.value)
  if (normalizedTime) {
    time.value = normalizedTime
  }
}

function handleTimeKeydown(event: KeyboardEvent): void {
  const input = event.target as HTMLInputElement | null
  if (!input || event.ctrlKey || event.metaKey || event.altKey) {
    return
  }
  if (isNavigationKey(event.key)) {
    return
  }
  if (/^\d$/.test(event.key)) {
    event.preventDefault()
    overwriteTimeDigit(input, event.key)
    return
  }
  if (event.key === 'Backspace') {
    event.preventDefault()
    replacePreviousTimeDigitWithZero(input)
    return
  }
  if (event.key === 'Delete') {
    event.preventDefault()
    replaceNextTimeDigitWithZero(input)
    return
  }
  event.preventDefault()
}

function isNavigationKey(key: string): boolean {
  return ['Tab', 'ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(key)
}

function overwriteTimeDigit(input: HTMLInputElement, digit: string): void {
  const selectionStart = input.selectionStart ?? 0
  const position = getEditablePosition(selectionStart, 'forward')
  if (position === null) {
    return
  }
  setTimeDigit(position, digit)
  const nextPosition = getEditablePosition(position + 1, 'forward') ?? position
  setTimeCaret(input, nextPosition)
}

function replacePreviousTimeDigitWithZero(input: HTMLInputElement): void {
  const selectionStart = input.selectionStart ?? 0
  const position = getEditablePosition(selectionStart - 1, 'backward')
  if (position === null) {
    return
  }
  setTimeDigit(position, '0')
  setTimeCaret(input, position)
}

function replaceNextTimeDigitWithZero(input: HTMLInputElement): void {
  const selectionStart = input.selectionStart ?? 0
  const position = getEditablePosition(selectionStart, 'forward')
  if (position === null) {
    return
  }
  setTimeDigit(position, '0')
  setTimeCaret(input, position)
}

function setTimeDigit(position: number, digit: string): void {
  const chars = getMaskedTimeCharacters()
  chars[position] = digit
  time.value = chars.join('')
}

function getMaskedTimeCharacters(): string[] {
  const normalized = normalizeTimeValue(time.value) ?? '00:00:00'
  return normalized.split('')
}

function getEditablePosition(start: number, direction: 'forward' | 'backward'): number | null {
  const editablePositions = [0, 1, 3, 4, 6, 7]
  if (direction === 'forward') {
    return editablePositions.find((position) => position >= start) ?? null
  }
  return [...editablePositions].reverse().find((position) => position <= start) ?? null
}

function setTimeCaret(input: HTMLInputElement, position: number): void {
  requestAnimationFrame(() => {
    input.setSelectionRange(position, position)
  })
}

function normalizeTimeValue(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null
  }
  const parts = value.trim().split(':')
  if (parts.length < 2 || parts.length > 3) {
    return null
  }
  const hoursRaw = parts[0] ?? ''
  const minutesRaw = parts[1] ?? ''
  const secondsRaw = parts[2] ?? '00'
  if (![hoursRaw, minutesRaw, secondsRaw].every((part) => /^\d{1,2}$/.test(part))) {
    return null
  }
  const hours = Number(hoursRaw)
  const minutes = Number(minutesRaw)
  const seconds = Number(secondsRaw)
  if (hours > 23 || minutes > 59 || seconds > 59) {
    return null
  }
  const normalized = [hours, minutes, seconds].map((part) => String(part).padStart(2, '0')).join(':')
  return normalized
}

function isValidTime(value: string): boolean {
  return normalizeTimeValue(value) !== null
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
    <div class="entity-maintenance__row">
      <div class="entity-maintenance__field"><label class="entity-maintenance__label entity-maintenance__label--small" for="trigger-id">{{ t('entities.triggers.fields.id') }} <button type="button" class="entity-maintenance__info" :title="t('entities.triggers.info.id')" :aria-label="t('entities.triggers.info.id')" @click="showInfo(t('entities.triggers.info.id'))"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button></label><InputText id="trigger-id" v-model="editableId" :disabled="!isNewEntity || loading" /></div>
      <div class="entity-maintenance__field"><label class="entity-maintenance__label" for="trigger-activated">{{ t('entities.triggers.fields.activated') }} <button type="button" class="entity-maintenance__info" :title="t('entities.triggers.info.activated')" :aria-label="t('entities.triggers.info.activated')" @click="showInfo(t('entities.triggers.info.activated'))"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button></label><ToggleSwitch id="trigger-activated" v-model="activated" :disabled="isNewEntity || loading || activationBusy" @update:model-value="void toggleActivation()" /></div>
    </div>
    <div class="entity-maintenance__field"><label class="entity-maintenance__label" for="trigger-name">{{ t('entities.triggers.fields.name') }} <button type="button" class="entity-maintenance__info" :title="t('entities.triggers.info.name')" :aria-label="t('entities.triggers.info.name')" @click="showInfo(t('entities.triggers.info.name'))"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button></label><InputText id="trigger-name" v-model="name" :disabled="loading" /></div>
    <div class="entity-maintenance__row">
      <div class="entity-maintenance__field"><label class="entity-maintenance__label" for="trigger-type">{{ t('entities.triggers.fields.triggerType') }} <button type="button" class="entity-maintenance__info" :title="t('entities.triggers.info.triggerType')" :aria-label="t('entities.triggers.info.triggerType')" @click="showInfo(t('entities.triggers.info.triggerType'))"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button></label><select id="trigger-type" v-model="triggerType" class="entity-maintenance__native-select" :disabled="loading"><option value="START_AT_POINT_IN_TIME">{{ t('entities.triggers.triggerTypeStart') }}</option><option value="STOP_AT_POINT_IN_TIME">{{ t('entities.triggers.triggerTypeStop') }}</option></select></div>
      <div class="entity-maintenance__field"><label class="entity-maintenance__label" for="trigger-recurrance-type">{{ t('entities.triggers.fields.recurranceType') }} <button type="button" class="entity-maintenance__info" :title="t('entities.triggers.info.recurranceType')" :aria-label="t('entities.triggers.info.recurranceType')" @click="showInfo(t('entities.triggers.info.recurranceType'))"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button></label><select id="trigger-recurrance-type" v-model="recurranceType" class="entity-maintenance__native-select" :disabled="loading || !isNewEntity"><option value="TIMER">{{ t('entities.triggers.recurranceTypeTimer') }}</option><option value="ONE_TIME">{{ t('entities.triggers.recurranceTypeOneTime') }}</option><option value="WEEKLY">{{ t('entities.triggers.recurranceTypeWeekly') }}</option></select></div>
    </div>
    <div class="entity-maintenance__row">
      <div class="entity-maintenance__field"><label class="entity-maintenance__label" for="trigger-time">{{ t('entities.triggers.fields.time') }} <button type="button" class="entity-maintenance__info" :title="t('entities.triggers.info.time')" :aria-label="t('entities.triggers.info.time')" @click="showInfo(t('entities.triggers.info.time'))"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button></label><input id="trigger-time" v-model="time" class="entity-maintenance__native-input" type="text" inputmode="numeric" placeholder="HH:MM:SS" maxlength="8" :disabled="loading" @keydown="handleTimeKeydown" @blur="normalizeTimeInput" /></div>
      <div class="entity-maintenance__field" v-if="recurranceType === 'ONE_TIME'"><label class="entity-maintenance__label" for="trigger-date">{{ t('entities.triggers.fields.date') }} <button type="button" class="entity-maintenance__info" :title="t('entities.triggers.info.date')" :aria-label="t('entities.triggers.info.date')" @click="showInfo(t('entities.triggers.info.date'))"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button></label><input id="trigger-date" v-model="date" class="entity-maintenance__native-input" type="date" :disabled="loading" /></div>
    </div>
    <div class="entity-maintenance__field">
      <label class="entity-maintenance__label">{{ t('entities.triggers.fields.weekdays') }} <button type="button" class="entity-maintenance__info" :title="t('entities.triggers.info.weekdays')" :aria-label="t('entities.triggers.info.weekdays')" @click="showInfo(t('entities.triggers.info.weekdays'))"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button></label>
      <div class="entity-maintenance__checkbox-row">
        <label v-for="day in weekdayOptions" :key="day" class="entity-maintenance__checkbox-item">
          <input v-model="weekdays" type="checkbox" :value="day" :disabled="loading || recurranceType !== 'WEEKLY'" />
          <span>{{ day }}</span>
        </label>
      </div>
    </div>
    <div class="entity-maintenance__row">
      <div class="entity-maintenance__field"><label class="entity-maintenance__label" for="trigger-from-date">{{ t('entities.triggers.fields.fromDate') }} <button type="button" class="entity-maintenance__info" :title="t('entities.triggers.info.fromDate')" :aria-label="t('entities.triggers.info.fromDate')" @click="showInfo(t('entities.triggers.info.fromDate'))"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button></label><input id="trigger-from-date" v-model="fromDate" class="entity-maintenance__native-input" type="date" :disabled="loading || recurranceType === 'ONE_TIME'" /></div>
      <div class="entity-maintenance__field"><label class="entity-maintenance__label" for="trigger-to-date">{{ t('entities.triggers.fields.toDate') }} <button type="button" class="entity-maintenance__info" :title="t('entities.triggers.info.toDate')" :aria-label="t('entities.triggers.info.toDate')" @click="showInfo(t('entities.triggers.info.toDate'))"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button></label><input id="trigger-to-date" v-model="toDate" class="entity-maintenance__native-input" type="date" :disabled="loading || recurranceType === 'ONE_TIME'" /></div>
    </div>
    <div class="entity-maintenance__field"><label class="entity-maintenance__label" for="trigger-recurring">{{ t('entities.triggers.fields.recurring') }} <button type="button" class="entity-maintenance__info" :title="t('entities.triggers.info.recurring')" :aria-label="t('entities.triggers.info.recurring')" @click="showInfo(t('entities.triggers.info.recurring'))"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button></label><ToggleSwitch id="trigger-recurring" v-model="recurring" :disabled="loading" /></div>
    <div class="entity-maintenance__field">
      <label class="entity-maintenance__label">{{ t('entities.triggers.fields.sequences') }} <button type="button" class="entity-maintenance__info" :title="t('entities.triggers.info.sequences')" :aria-label="t('entities.triggers.info.sequences')" @click="showInfo(t('entities.triggers.info.sequences'))"><FontAwesomeIcon icon="fa-solid fa-circle-info" /></button></label>
      <EntityRelationPicker v-model="sequenceIds" endpoint-path="/sequences" find-path="/sequences/find" placeholder-key="entities.triggers.sequencesPlaceholder" />
    </div>
    <footer class="entity-maintenance__footer">
      <Button severity="secondary" :label="t('common.cancel')" @click="cancel"><template #icon><FontAwesomeIcon icon="fa-solid fa-xmark" /></template></Button>
      <Button severity="danger" :label="t('common.delete')" :disabled="isNewEntity" :loading="deleting" @click="void remove()"><template #icon><FontAwesomeIcon icon="fa-solid fa-trash" /></template></Button>
      <Button :label="t('common.save')" :loading="submitting" @click="void save()"><template #icon><FontAwesomeIcon icon="fa-solid fa-floppy-disk" /></template></Button>
    </footer>
  </section>
</template>

<style scoped>
.entity-maintenance__checkbox-row {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.entity-maintenance__checkbox-item {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}
</style>
