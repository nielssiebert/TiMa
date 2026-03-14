<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import ToggleButton from 'primevue/togglebutton'
import { AxiosError } from 'axios'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAppToast } from '@/core/ui/appToast'
import EntityRelationPicker from '../components/EntityRelationPicker.vue'
import { executionEventGroupService } from '../services/executionEventGroupService'
import { executionEventService } from '../services/executionEventService'
import { sequenceService, type SequencePayload } from '../services/sequenceService'
import { entityDefinitions } from '../shared/entityModels'
import { isEntityLike, resolveEntityId } from '../shared/maintenanceEntityUtils'

const props = defineProps<{
  id: string
}>()

const definition = entityDefinitions.sequences
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
const triggerIds = ref<string[]>([])
const sequenceExecutionEventIds = ref<string[]>([])
const sequenceExecutionEventGroupIds = ref<string[]>([])
type SequenceItemType = 'execution-event' | 'execution-event-group'

interface SequenceOrderItem {
  key: string
  signature: string
  itemType: SequenceItemType
  entityId: string
  order: number
}

interface SequenceOrderGroup {
  order: number
  items: SequenceOrderItem[]
}

const sequenceOrderItems = ref<SequenceOrderItem[]>([])
const draggedItemKey = ref<string | null>(null)
const dragOverZone = ref<string | null>(null)
const touchDragging = ref(false)
const touchPointX = ref(0)
const touchPointY = ref(0)
const isSyncingFromEntity = ref(false)
const sequenceItemNames = ref<Record<string, string>>({})
const status = ref(false)
const isAutomaticallyCreated = ref(false)
const isSequenceItemsLocked = computed(() => !isNewEntity.value && isAutomaticallyCreated.value)

const draggedTouchItem = computed<SequenceOrderItem | null>(() => {
  if (!touchDragging.value || !draggedItemKey.value) {
    return null
  }
  return sequenceOrderItems.value.find((item) => item.key === draggedItemKey.value) ?? null
})

const touchGhostStyle = computed(() => ({
  left: `${touchPointX.value}px`,
  top: `${touchPointY.value}px`,
}))

const sequenceOrderGroups = computed<SequenceOrderGroup[]>(() => {
  const grouped = new Map<number, SequenceOrderItem[]>()
  for (const item of sequenceOrderItems.value) {
    const items = grouped.get(item.order) ?? []
    items.push(item)
    grouped.set(item.order, items)
  }
  return [...grouped.entries()]
    .sort(([left], [right]) => left - right)
    .map(([order, items]) => ({ order, items }))
})

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

watch(
  [sequenceExecutionEventIds, sequenceExecutionEventGroupIds],
  () => {
    if (isSyncingFromEntity.value) {
      return
    }
    reconcileOrderItems()
  },
  { deep: true },
)

watch(
  sequenceOrderItems,
  async () => {
    await ensureSequenceItemNames()
  },
  { deep: true },
)

function resetForm(): void {
  name.value = ''
  editableId.value = ''
  isAutomaticallyCreated.value = false
  triggerIds.value = []
  sequenceExecutionEventIds.value = []
  sequenceExecutionEventGroupIds.value = []
  sequenceOrderItems.value = []
  sequenceItemNames.value = {}
  draggedItemKey.value = null
  dragOverZone.value = null
  status.value = false
}

async function loadEntity(): Promise<void> {
  loading.value = true
  try {
    const payload = await sequenceService.getById(props.id)
    await applyEntityPayload(payload)
  } catch (error: unknown) {
    showError(extractError(error))
  } finally {
    loading.value = false
  }
}

async function applyEntityPayload(payload: unknown): Promise<void> {
  if (!isEntityLike(payload)) {
    return
  }
  editableId.value = String(payload.id ?? '')
  name.value = String(payload.name ?? '')
  isAutomaticallyCreated.value = payload.automatically_created === true
  triggerIds.value = Array.isArray(payload.triggers)
    ? payload.triggers.filter((id): id is string => typeof id === 'string')
    : []

  const sequenceItems = Array.isArray(payload.sequence_items)
    ? payload.sequence_items.filter(isEntityLike)
    : []
  const mappedOrderItems = mapPayloadSequenceItems(sequenceItems)
  isSyncingFromEntity.value = true
  sequenceOrderItems.value = mappedOrderItems
  sequenceExecutionEventIds.value = mappedOrderItems
    .filter((item) => item.itemType === 'execution-event')
    .map((item) => item.entityId)
  sequenceExecutionEventGroupIds.value = mappedOrderItems
    .filter((item) => item.itemType === 'execution-event-group')
    .map((item) => item.entityId)
  await nextTick()
  isSyncingFromEntity.value = false

  const runtime = isEntityLike(payload.runtime) ? payload.runtime : null
  status.value = runtime?.is_running === true
}

function createPayload(): SequencePayload {
  const payload: SequencePayload = {
    id: editableId.value.trim(),
    name: name.value.trim(),
    trigger_ids: triggerIds.value,
  }
  if (!isSequenceItemsLocked.value) {
    payload.sequence_items = createSequenceItemsPayload()
  }
  return payload
}

function createSequenceItemsPayload(): SequencePayload['sequence_items'] {
  return sequenceOrderItems.value.map((item) => {
    if (item.itemType === 'execution-event') {
      return {
        order: item.order,
        execution_event_id: item.entityId,
      }
    }
    return {
      order: item.order,
      execution_event_group_id: item.entityId,
    }
  })
}

function mapPayloadSequenceItems(payloadItems: Record<string, unknown>[]): SequenceOrderItem[] {
  const items: SequenceOrderItem[] = []
  for (let index = 0; index < payloadItems.length; index += 1) {
    const item = payloadItems[index]
    if (!item) {
      continue
    }
    const eventId = item.execution_event_id
    const eventGroupId = item.execution_event_group_id
    const order = Number(item.order)
    const normalizedOrder = Number.isInteger(order) && order > 0 ? order : 1
    if (typeof eventId === 'string') {
      const sourceId = typeof item.id === 'string' ? item.id : `${eventId}`
      const payloadKey = `execution-event:${sourceId}:${index}`
      items.push(createOrderItem('execution-event', eventId, normalizedOrder, payloadKey))
      continue
    }
    if (typeof eventGroupId === 'string') {
      const sourceId = typeof item.id === 'string' ? item.id : `${eventGroupId}`
      const payloadKey = `execution-event-group:${sourceId}:${index}`
      items.push(createOrderItem('execution-event-group', eventGroupId, normalizedOrder, payloadKey))
    }
  }
  return items.sort((left, right) => left.order - right.order)
}

function createOrderItem(
  itemType: SequenceItemType,
  entityId: string,
  order: number,
  key?: string,
): SequenceOrderItem {
  const signature = `${itemType}:${entityId}`
  return {
    key: key ?? `${signature}:${Math.random().toString(36).slice(2, 10)}`,
    signature,
    itemType,
    entityId,
    order,
  }
}

function reconcileOrderItems(): void {
  const wantedItems = [
    ...sequenceExecutionEventIds.value.map((entityId) => createOrderItem('execution-event', entityId, 1)),
    ...sequenceExecutionEventGroupIds.value.map((entityId) =>
      createOrderItem('execution-event-group', entityId, 1),
    ),
  ]
  const wantedSignatures = new Set(wantedItems.map((item) => item.signature))
  const existingBySignature = new Map(sequenceOrderItems.value.map((item) => [item.signature, item]))
  const kept = sequenceOrderItems.value.filter((item, index, allItems) => {
    if (!wantedSignatures.has(item.signature)) {
      return false
    }
    return allItems.findIndex((candidate) => candidate.signature === item.signature) === index
  })
  const maxOrder = Math.max(0, ...kept.map((item) => item.order))
  let nextOrder = maxOrder

  for (const wanted of wantedItems) {
    if (existingBySignature.has(wanted.signature)) {
      continue
    }
    nextOrder += 1
    kept.push(createOrderItem(wanted.itemType, wanted.entityId, nextOrder))
  }
  sequenceOrderItems.value = kept
}

function onDragStart(itemKey: string): void {
  if (isSequenceItemsLocked.value) {
    return
  }
  draggedItemKey.value = itemKey
}

function onDragEnd(): void {
  detachTouchListeners()
  touchDragging.value = false
  draggedItemKey.value = null
  dragOverZone.value = null
}

function onDragOver(zoneKey: string, event: DragEvent): void {
  if (isSequenceItemsLocked.value) {
    return
  }
  if (!draggedItemKey.value) {
    return
  }
  event.preventDefault()
  dragOverZone.value = zoneKey
}

function onTouchHandleStart(itemKey: string, event: TouchEvent): void {
  if (isSequenceItemsLocked.value) {
    return
  }
  if (event.cancelable) {
    event.preventDefault()
  }
  draggedItemKey.value = itemKey
  touchDragging.value = true
  updateTouchPointFromTouchEvent(event)
  attachTouchListeners()
  updateDragOverZoneFromTouchEvent(event)
}

function onWindowTouchMove(event: TouchEvent): void {
  if (!touchDragging.value || !draggedItemKey.value) {
    return
  }
  if (event.cancelable) {
    event.preventDefault()
  }
  updateTouchPointFromTouchEvent(event)
  updateDragOverZoneFromTouchEvent(event)
}

function onWindowTouchEnd(event: TouchEvent): void {
  if (!touchDragging.value || !draggedItemKey.value) {
    onDragEnd()
    return
  }
  if (event.cancelable) {
    event.preventDefault()
  }
  updateTouchPointFromTouchEvent(event)
  const dropZone = resolveDropZoneFromTouchEvent(event)
  const dropped = dropDraggedItemOnZone(dropZone)
  if (!dropped) {
    onDragEnd()
  }
}

function onWindowTouchCancel(): void {
  onDragEnd()
}

function attachTouchListeners(): void {
  window.addEventListener('touchmove', onWindowTouchMove, { passive: false })
  window.addEventListener('touchend', onWindowTouchEnd, { passive: false })
  window.addEventListener('touchcancel', onWindowTouchCancel)
}

function detachTouchListeners(): void {
  window.removeEventListener('touchmove', onWindowTouchMove)
  window.removeEventListener('touchend', onWindowTouchEnd)
  window.removeEventListener('touchcancel', onWindowTouchCancel)
}

function updateDragOverZoneFromTouchEvent(event: TouchEvent): void {
  const dropZone = resolveDropZoneFromTouchEvent(event)
  dragOverZone.value = dropZone
}

function updateTouchPointFromTouchEvent(event: TouchEvent): void {
  const touch = event.touches[0] ?? event.changedTouches[0]
  if (!touch) {
    return
  }
  touchPointX.value = touch.clientX
  touchPointY.value = touch.clientY
}

function resolveDropZoneFromTouchEvent(event: TouchEvent): string | null {
  const touch = event.touches[0] ?? event.changedTouches[0]
  if (!touch) {
    return null
  }
  return resolveDropZoneFromPoint(touch.clientX, touch.clientY)
}

function resolveDropZoneFromPoint(clientX: number, clientY: number): string | null {
  const element = document.elementFromPoint(clientX, clientY)
  if (!(element instanceof HTMLElement)) {
    return null
  }
  const zone = element.closest<HTMLElement>('[data-drop-zone]')
  return zone?.dataset.dropZone ?? null
}

function dropDraggedItemOnZone(dropZone: string | null): boolean {
  if (!dropZone) {
    return false
  }
  if (dropZone.startsWith('match:')) {
    const itemKey = dropZone.slice('match:'.length)
    if (!itemKey) {
      return false
    }
    moveDraggedItem(itemKey, 'match')
    return true
  }
  if (dropZone.startsWith('position:')) {
    const position = Number.parseInt(dropZone.slice('position:'.length), 10)
    if (!Number.isFinite(position)) {
      return false
    }
    moveDraggedToPosition(position)
    return true
  }
  return false
}

function onDropMatchOrder(targetItemKey: string): void {
  if (isSequenceItemsLocked.value) {
    return
  }
  moveDraggedItem(targetItemKey, 'match')
}

function onDropAtPosition(position: number): void {
  if (isSequenceItemsLocked.value) {
    return
  }
  moveDraggedToPosition(position)
}

onBeforeUnmount(() => {
  detachTouchListeners()
})

function moveDraggedItem(targetItemKey: string, position: 'before' | 'after' | 'match'): void {
  const sourceKey = draggedItemKey.value
  if (!sourceKey || sourceKey === targetItemKey) {
    onDragEnd()
    return
  }

  const items = [...sequenceOrderItems.value]
  const sourceIndex = items.findIndex((item) => item.key === sourceKey)
  const targetIndex = items.findIndex((item) => item.key === targetItemKey)
  if (sourceIndex < 0 || targetIndex < 0) {
    onDragEnd()
    return
  }

  const dragged = items[sourceIndex]
  if (!dragged) {
    onDragEnd()
    return
  }
  items.splice(sourceIndex, 1)
  const adjustedTargetIndex = items.findIndex((item) => item.key === targetItemKey)
  const insertIndex = position === 'before' ? adjustedTargetIndex : adjustedTargetIndex + 1
  items.splice(insertIndex, 0, dragged)

  const target = items.find((item) => item.key === targetItemKey)
  if (!target) {
    onDragEnd()
    return
  }

  if (position === 'match') {
    dragged.order = target.order
  } else {
    const targetOrder = position === 'before' ? target.order : target.order + 1
    assignStandaloneOrder(items, dragged.key, targetOrder)
  }

  normalizeOrderBuckets(items)

  sequenceOrderItems.value = items
  onDragEnd()
}

function moveDraggedToPosition(position: number): void {
  const sourceKey = draggedItemKey.value
  if (!sourceKey) {
    onDragEnd()
    return
  }

  const items = [...sequenceOrderItems.value]
  const sourceIndex = items.findIndex((item) => item.key === sourceKey)
  if (sourceIndex < 0) {
    onDragEnd()
    return
  }

  const dragged = items[sourceIndex]
  if (!dragged) {
    onDragEnd()
    return
  }

  const maxPosition = items.length + 1
  const normalizedPosition = Math.min(Math.max(position, 1), maxPosition)

  items.splice(sourceIndex, 1)
  assignStandaloneOrder(items, dragged.key, normalizedPosition)
  dragged.order = normalizedPosition
  items.push(dragged)
  normalizeOrderBuckets(items)

  sequenceOrderItems.value = items
  onDragEnd()
}

function assignStandaloneOrder(items: SequenceOrderItem[], draggedKey: string, order: number): void {
  for (const item of items) {
    if (item.key === draggedKey) {
      continue
    }
    if (item.order >= order) {
      item.order += 1
    }
  }

  const draggedItem = items.find((item) => item.key === draggedKey)
  if (draggedItem) {
    draggedItem.order = order
  }
}

function normalizeOrderBuckets(items: SequenceOrderItem[]): void {
  const uniqueOrders = [...new Set(items.map((item) => item.order))].sort((left, right) => left - right)
  const orderMap = new Map(uniqueOrders.map((order, index) => [order, index + 1]))
  for (const item of items) {
    const mappedOrder = orderMap.get(item.order)
    if (mappedOrder) {
      item.order = mappedOrder
    }
  }
}

function sequenceItemLabel(item: SequenceOrderItem): string {
  return sequenceItemNames.value[item.signature] ?? item.entityId
}

function sequenceItemTypeLabel(item: SequenceOrderItem): string {
  if (item.itemType === 'execution-event') {
    return t('entities.sequences.orderMaintenance.executionEventPrefix')
  }
  return t('entities.sequences.orderMaintenance.executionEventGroupPrefix')
}

async function ensureSequenceItemNames(): Promise<void> {
  const uniqueItems = new Map<string, SequenceOrderItem>()
  for (const item of sequenceOrderItems.value) {
    if (!sequenceItemNames.value[item.signature]) {
      uniqueItems.set(item.signature, item)
    }
  }

  for (const item of uniqueItems.values()) {
    const resolvedName = await fetchSequenceItemName(item)
    sequenceItemNames.value = {
      ...sequenceItemNames.value,
      [item.signature]: resolvedName,
    }
  }
}

async function fetchSequenceItemName(item: SequenceOrderItem): Promise<string> {
  try {
    const payload = item.itemType === 'execution-event'
      ? await executionEventService.getById(item.entityId)
      : await executionEventGroupService.getById(item.entityId)
    if (isEntityLike(payload) && typeof payload.name === 'string' && payload.name.trim()) {
      return payload.name
    }
  } catch {
  }
  return item.entityId
}

function validatePayload(payload: SequencePayload): boolean {
  if (!payload.id || !payload.name) {
    showError(t('entities.sequences.validationMessage'))
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
      const createdPayload = await sequenceService.create(payload)
      applyEntityPayload(createdPayload)
      const createdId = resolveEntityId(createdPayload)
      if (createdId) {
        await router.replace({ name: definition.maintenanceRouteName, params: { id: createdId } })
      }
      showSuccess(t('entities.sequences.createSuccess'))
    } else {
      await sequenceService.update(payload)
      await loadEntity()
      showSuccess(t('entities.sequences.updateSuccess'))
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
    await sequenceService.remove(props.id)
    showSuccess(t('entities.sequences.deleteSuccess'))
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
    await sequenceService.toggleRuntime(props.id, status.value ? 'start' : 'stop')
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
    <p v-if="isSequenceItemsLocked" class="sequence-maintenance__readonly-note">
      {{ t('entities.sequences.notes.autoCreatedSequenceItemsReadonly') }}
    </p>
    <div class="entity-maintenance__top-row">
      <div class="entity-maintenance__field"><label class="entity-maintenance__label entity-maintenance__label--small"
          for="sequence-id">{{ t('entities.sequences.fields.id') }} <button type="button"
            class="entity-maintenance__info" :title="t('entities.sequences.info.id')"
            :aria-label="t('entities.sequences.info.id')" @click="showInfo(t('entities.sequences.info.id'))">
            <FontAwesomeIcon icon="fa-solid fa-circle-info" />
          </button></label>
        <InputText id="sequence-id" v-model="editableId" class="entity-maintenance__id-input"
          :disabled="!isNewEntity || loading" />
      </div>
      <div class="entity-maintenance__field entity-maintenance__status-field"><label class="entity-maintenance__label"
          for="sequence-status">{{ t('entities.sequences.fields.status') }} <button type="button"
            class="entity-maintenance__info" :title="t('entities.sequences.info.status')"
            :aria-label="t('entities.sequences.info.status')" @click="showInfo(t('entities.sequences.info.status'))">
            <FontAwesomeIcon icon="fa-solid fa-circle-info" />
          </button></label>
        <ToggleButton id="sequence-status" :model-value="status" :on-label="t('common.on')" :off-label="t('common.off')"
          :disabled="isNewEntity || runningBusy || loading" class="entity-maintenance__running-toggle"
          @update:model-value="status = $event; void toggleStatus()" />
      </div>
    </div>
    <div class="entity-maintenance__field"><label class="entity-maintenance__label" for="sequence-name">{{
      t('entities.sequences.fields.name') }} <button type="button" class="entity-maintenance__info"
          :title="t('entities.sequences.info.name')" :aria-label="t('entities.sequences.info.name')"
          @click="showInfo(t('entities.sequences.info.name'))">
          <FontAwesomeIcon icon="fa-solid fa-circle-info" />
        </button></label>
      <InputText id="sequence-name" v-model="name" :disabled="loading" />
    </div>
    <div class="entity-maintenance__field"><label class="entity-maintenance__label">{{
      t('entities.sequences.fields.triggers') }} <button type="button" class="entity-maintenance__info"
          :title="t('entities.sequences.info.triggers')" :aria-label="t('entities.sequences.info.triggers')"
          @click="showInfo(t('entities.sequences.info.triggers'))">
          <FontAwesomeIcon icon="fa-solid fa-circle-info" />
        </button></label>
      <EntityRelationPicker v-model="triggerIds" endpoint-path="/triggers" find-path="/triggers/find"
        placeholder-key="entities.sequences.triggersPlaceholder" />
    </div>
    <div class="entity-maintenance__field"><label class="entity-maintenance__label">{{
      t('entities.sequences.fields.executionEvents') }} <button type="button" class="entity-maintenance__info"
          :title="t('entities.sequences.info.executionEvents')"
          :aria-label="t('entities.sequences.info.executionEvents')"
          @click="showInfo(t('entities.sequences.info.executionEvents'))">
          <FontAwesomeIcon icon="fa-solid fa-circle-info" />
        </button></label>
      <EntityRelationPicker v-model="sequenceExecutionEventIds" endpoint-path="/execution-events"
        find-path="/execution-events/find" placeholder-key="entities.sequences.executionEventsPlaceholder"
        :disabled="isSequenceItemsLocked || loading" />
    </div>
    <div class="entity-maintenance__field"><label class="entity-maintenance__label">{{
      t('entities.sequences.fields.executionEventGroups') }} <button type="button" class="entity-maintenance__info"
          :title="t('entities.sequences.info.executionEventGroups')"
          :aria-label="t('entities.sequences.info.executionEventGroups')"
          @click="showInfo(t('entities.sequences.info.executionEventGroups'))">
          <FontAwesomeIcon icon="fa-solid fa-circle-info" />
        </button></label>
      <EntityRelationPicker v-model="sequenceExecutionEventGroupIds" endpoint-path="/execution-event-groups"
        find-path="/execution-event-groups/find" placeholder-key="entities.sequences.executionEventGroupsPlaceholder"
        :disabled="isSequenceItemsLocked || loading" />
    </div>
    <div class="entity-maintenance__field"><label class="entity-maintenance__label">{{
      t('entities.sequences.fields.orderMaintenance') }} <button type="button" class="entity-maintenance__info"
          :title="t('entities.sequences.info.orderMaintenance')"
          :aria-label="t('entities.sequences.info.orderMaintenance')"
          @click="showInfo(t('entities.sequences.info.orderMaintenance'))">
          <FontAwesomeIcon icon="fa-solid fa-circle-info" />
        </button></label>
      <div class="sequence-order-maintenance">
        <p class="sequence-order-maintenance__hint">{{ t('entities.sequences.orderMaintenance.hint') }}</p>
        <div v-if="sequenceOrderItems.length" class="sequence-order-maintenance__list">
          <div
            v-if="sequenceOrderGroups[0]"
            class="sequence-order-maintenance__gap"
            data-drop-zone="position:1"
            :class="{ 'sequence-order-maintenance__gap--active': dragOverZone === 'position:1' }"
            @dragover="onDragOver('position:1', $event)"
            @drop.prevent="onDropAtPosition(1)"
          >
            {{ t('entities.sequences.orderMaintenance.dropHere') }}
          </div>
          <template v-for="(group, groupIndex) in sequenceOrderGroups" :key="group.order">
            <section class="sequence-order-maintenance__group">
            <header class="sequence-order-maintenance__group-header">#{{ group.order }}</header>
            <div class="sequence-order-maintenance__group-items">
              <template v-for="item in group.items" :key="item.key">
                <article
                  class="sequence-order-maintenance__item"
                  :data-drop-zone="`match:${item.key}`"
                  :class="{
                    'sequence-order-maintenance__item--dragging': draggedItemKey === item.key,
                    'sequence-order-maintenance__item--match-active': dragOverZone === `match:${item.key}`,
                  }"
                  :draggable="!isSequenceItemsLocked"
                  @dragstart="onDragStart(item.key)"
                  @dragend="onDragEnd"
                  @dragover="onDragOver(`match:${item.key}`, $event)"
                  @drop.prevent="onDropMatchOrder(item.key)"
                >
                  <div class="sequence-order-maintenance__item-content">
                    <span class="sequence-order-maintenance__label">{{ sequenceItemLabel(item) }}
                      <small class="sequence-order-maintenance__type">({{ sequenceItemTypeLabel(item) }})</small>
                    </span>
                    <span class="sequence-order-maintenance__match-hint">
                      {{ t('entities.sequences.orderMaintenance.dropMatchOrder') }}
                    </span>
                  </div>
                  <button
                    type="button"
                    class="sequence-order-maintenance__handle"
                    :disabled="isSequenceItemsLocked"
                    aria-label="Drag handle"
                    title="Drag handle"
                    @touchstart.stop="onTouchHandleStart(item.key, $event)"
                  >
                    <FontAwesomeIcon icon="fa-solid fa-grip-lines" />
                  </button>
                </article>
              </template>
            </div>
            </section>
            <div
              v-if="groupIndex < sequenceOrderGroups.length - 1"
              class="sequence-order-maintenance__gap"
              :data-drop-zone="`position:${groupIndex + 2}`"
              :class="{
                'sequence-order-maintenance__gap--active':
                  dragOverZone === `position:${groupIndex + 2}`,
              }"
              @dragover="onDragOver(`position:${groupIndex + 2}`, $event)"
              @drop.prevent="onDropAtPosition(groupIndex + 2)"
            >
              {{ t('entities.sequences.orderMaintenance.dropHere') }}
            </div>
          </template>
          <div
            v-if="sequenceOrderGroups[sequenceOrderGroups.length - 1]"
            class="sequence-order-maintenance__gap"
            :data-drop-zone="`position:${sequenceOrderGroups.length + 1}`"
            :class="{
              'sequence-order-maintenance__gap--active':
                dragOverZone === `position:${sequenceOrderGroups.length + 1}`,
            }"
            @dragover="onDragOver(`position:${sequenceOrderGroups.length + 1}`, $event)"
            @drop.prevent="onDropAtPosition(sequenceOrderGroups.length + 1)"
          >
            {{ t('entities.sequences.orderMaintenance.dropHere') }}
          </div>
        </div>
        <p v-else class="sequence-order-maintenance__empty">{{ t('entities.sequences.orderMaintenance.empty') }}</p>
      </div>
    </div>
    <footer class="entity-maintenance__footer"><Button severity="secondary" :label="t('common.cancel')"
        @click="cancel"><template #icon>
          <FontAwesomeIcon icon="fa-solid fa-xmark" />
        </template></Button><Button severity="danger" :label="t('common.delete')" :disabled="isNewEntity"
        :loading="deleting" @click="void remove()"><template #icon>
          <FontAwesomeIcon icon="fa-solid fa-trash" />
        </template></Button><Button :label="t('common.save')" :loading="submitting" @click="void save()"><template
          #icon>
          <FontAwesomeIcon icon="fa-solid fa-floppy-disk" />
        </template></Button></footer>
    <div
      v-if="draggedTouchItem"
      class="sequence-order-maintenance__touch-ghost"
      :style="touchGhostStyle"
      aria-hidden="true"
    >
      <span class="sequence-order-maintenance__label">{{ sequenceItemLabel(draggedTouchItem) }}
        <small class="sequence-order-maintenance__type">({{ sequenceItemTypeLabel(draggedTouchItem) }})</small>
      </span>
      <span class="sequence-order-maintenance__ghost-icon">
        <FontAwesomeIcon icon="fa-solid fa-grip-lines" />
      </span>
    </div>
  </section>
</template>

<style scoped>
:deep(.entity-maintenance__running-toggle.p-togglebutton) {
  background: var(--app-status-off-bg, var(--p-red-100, var(--p-surface-200)));
  border-color: var(--app-status-off-border, var(--p-red-200, var(--p-surface-300)));
  color: var(--app-status-off-text, var(--p-red-900, var(--p-text-color)));
}

:deep(.entity-maintenance__running-toggle.p-togglebutton.p-togglebutton-checked) {
  background: var(--app-status-on-bg, var(--p-green-100, var(--p-surface-200)));
  border-color: var(--app-status-on-border, var(--p-green-200, var(--p-surface-300)));
  color: var(--app-status-on-text, var(--p-green-900, var(--p-text-color)));
}

.sequence-order-maintenance {
  border: 1px solid var(--p-surface-300, var(--p-surface-border));
  border-radius: 0.5rem;
  padding: 0.75rem;
}

.sequence-order-maintenance__hint,
.sequence-order-maintenance__empty {
  margin: 0;
  color: var(--p-text-muted-color, var(--p-text-color-secondary));
}

.sequence-order-maintenance__list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.sequence-order-maintenance__group {
  border: 1px solid var(--p-surface-300, var(--p-surface-border));
  border-radius: 0.5rem;
  padding: 0.5rem;
}

.sequence-order-maintenance__group-header {
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.sequence-order-maintenance__group-items {
  display: flex;
  flex-direction: column;
  margin: 0.5rem 0 0;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.sequence-order-maintenance__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  border: 1px solid var(--app-content-border);
  border-radius: 0.5rem;
  padding: 0.375rem 0.5rem;
  background: var(--app-content-item-bg);
}

.sequence-order-maintenance__item-content {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 0.3rem;
  min-width: 0;
}

.sequence-order-maintenance__item--dragging {
  opacity: 0.6;
}

.sequence-order-maintenance__item--match-active {
  border-color: var(--p-primary-color, var(--p-highlight-background));
  background: var(--app-content-bg);
}

.sequence-order-maintenance__label {
  font-weight: 500;
}

.sequence-order-maintenance__type {
  font-weight: 400;
  font-size: 0.75rem;
}

.sequence-order-maintenance__match-hint {
  font-size: 0.8rem;
  color: var(--p-text-muted-color, var(--p-text-color-secondary));
}

.sequence-order-maintenance__handle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  min-height: 2rem;
  border: 1px solid var(--app-content-border);
  border-radius: 0.375rem;
  background: var(--app-content-bg);
  color: var(--p-text-muted-color, var(--p-text-color-secondary));
  cursor: grab;
  touch-action: none;
}

.sequence-order-maintenance__handle:active {
  cursor: grabbing;
}

.sequence-order-maintenance__gap {
  border: 1px dashed var(--app-dropzone-border, var(--p-surface-400, var(--p-surface-border)));
  border-radius: 0.375rem;
  background: var(--app-dropzone-bg, var(--p-surface-50, var(--p-surface-100)));
  color: var(--p-text-muted-color, var(--p-text-color-secondary));
  padding: 0.25rem 0.5rem;
  font-size: 0.8rem;
  text-align: center;
}

.sequence-order-maintenance__gap--active {
  border-style: solid;
  border-color: var(--app-dropzone-active-border, var(--p-primary-color, var(--p-highlight-background)));
  background: var(--app-dropzone-active-bg, var(--app-dropzone-bg, var(--app-content-item-bg)));
  color: var(--p-text-color);
}

.sequence-order-maintenance__touch-ghost {
  position: fixed;
  z-index: 1500;
  transform: translate(-50%, -120%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  width: min(32rem, calc(100vw - 1.5rem));
  border: 1px solid var(--p-primary-color, var(--app-content-border));
  border-radius: 0.5rem;
  background: var(--app-content-item-bg);
  box-shadow: 0 6px 12px color-mix(in srgb, var(--p-text-color, #000) 12%, transparent);
  padding: 0.375rem 0.5rem;
  pointer-events: none;
  opacity: 0.95;
}

.sequence-maintenance__readonly-note {
  margin: 0 0 0.75rem;
  font-size: 0.8rem;
  color: var(--p-text-muted-color, var(--p-text-color-secondary));
}

.sequence-order-maintenance__ghost-icon {
  display: inline-flex;
  align-items: center;
  color: var(--p-text-muted-color, var(--p-text-color-secondary));
}
</style>
