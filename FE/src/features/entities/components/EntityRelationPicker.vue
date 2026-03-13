<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import { AxiosError } from 'axios'
import { useI18n } from 'vue-i18n'
import { httpClient } from '@/core/api/httpClient'
import { useAppToast } from '@/core/ui/appToast'

interface RelationOption {
  id: string
  name: string
}

const props = defineProps<{
  modelValue: string[]
  endpointPath: string
  findPath: string
  placeholderKey: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

const { t } = useI18n()
const { showError } = useAppToast()
const query = ref('')
const suggestions = ref<RelationOption[]>([])
const selectedItems = ref<RelationOption[]>([])
const isSearching = ref(false)
const hasSearched = ref(false)
const searchFailed = ref(false)
let searchTimer: number | null = null
let blurTimer: number | null = null

const selectedIds = computed(() => selectedItems.value.map((item) => item.id))
const showNoResults = computed(
  () => hasSearched.value && !searchFailed.value && !isSearching.value && !suggestions.value.length,
)

watch(
  () => props.modelValue,
  async (ids) => {
    await syncSelectedItems(ids)
  },
  { immediate: true },
)

onUnmounted(() => {
  clearSearchTimer()
  clearBlurTimer()
})

function queueSearch(): void {
  clearSearchTimer()
  const normalizedTerm = normalizeSearchTerm(query.value)
  searchTimer = window.setTimeout(() => {
    void loadSuggestions(normalizedTerm)
  }, 250)
}

function handleInputBlur(): void {
  clearBlurTimer()
  blurTimer = window.setTimeout(() => {
    suggestions.value = []
    hasSearched.value = false
    searchFailed.value = false
  }, 150)
}

function clearBlurTimer(): void {
  if (blurTimer === null) {
    return
  }
  window.clearTimeout(blurTimer)
  blurTimer = null
}

function clearSearchTimer(): void {
  if (searchTimer === null) {
    return
  }
  window.clearTimeout(searchTimer)
  searchTimer = null
}

async function syncSelectedItems(ids: string[]): Promise<void> {
  const uniqueIds = [...new Set(ids.filter(Boolean))]
  if (arraysEqual(uniqueIds, selectedIds.value)) {
    return
  }
  if (!uniqueIds.length) {
    selectedItems.value = []
    return
  }
  try {
    const loaded = await Promise.all(uniqueIds.map((id) => fetchById(id)))
    selectedItems.value = loaded.filter((item): item is RelationOption => item !== null)
  } catch (error: unknown) {
    showError(extractError(error))
  }
}

async function fetchById(id: string): Promise<RelationOption | null> {
  try {
    const response = await httpClient.get(`${props.endpointPath}/${id}`)
    const data = response.data
    if (!isOptionLike(data)) {
      return null
    }
    return { id: String(data.id), name: String(data.name) }
  } catch {
    return null
  }
}

async function loadSuggestions(searchTerm: string): Promise<void> {
  isSearching.value = true
  hasSearched.value = false
  searchFailed.value = false
  try {
    const response = await httpClient.get(props.findPath, { params: { query: searchTerm } })
    suggestions.value = parseOptions(response.data).filter((item) => !selectedIds.value.includes(item.id))
    hasSearched.value = true
  } catch (error: unknown) {
    showError(extractError(error))
    suggestions.value = []
    hasSearched.value = true
    searchFailed.value = true
  } finally {
    isSearching.value = false
  }
}

function parseOptions(payload: unknown): RelationOption[] {
  if (!Array.isArray(payload)) {
    return []
  }
  return payload
    .filter(isOptionLike)
    .map((item) => ({ id: String(item.id), name: String(item.name) }))
    .filter((item) => item.id !== '' && item.name !== '')
}

function addItem(item: RelationOption): void {
  clearSearchTimer()
  clearBlurTimer()
  selectedItems.value = [...selectedItems.value, item]
  emit('update:modelValue', selectedItems.value.map((entry) => entry.id))
  query.value = ''
  suggestions.value = []
  hasSearched.value = false
  searchFailed.value = false
}

function handleSuggestionMouseDown(item: RelationOption): void {
  addItem(item)
}

function removeItem(id: string): void {
  selectedItems.value = selectedItems.value.filter((item) => item.id !== id)
  emit('update:modelValue', selectedItems.value.map((entry) => entry.id))
}

function isOptionLike(value: unknown): value is { id?: unknown; name?: unknown } {
  return typeof value === 'object' && value !== null
}

function arraysEqual(left: string[], right: string[]): boolean {
  if (left.length !== right.length) {
    return false
  }
  return left.every((id, index) => id === right[index])
}

function extractError(error: unknown): string {
  if (error instanceof AxiosError) {
    return error.response?.data?.message ?? t('entities.loadError')
  }
  return t('entities.loadError')
}

function normalizeSearchTerm(raw: string): string {
  const trimmed = raw.trim()
  if (trimmed === '') {
    return ''
  }
  if (/^[*%]+$/.test(trimmed)) {
    return ''
  }
  return trimmed
}
</script>

<template>
  <div class="relation-picker">
    <ul v-if="selectedItems.length" class="relation-picker__selected">
      <li v-for="item in selectedItems" :key="item.id" class="relation-picker__selected-item">
        <span>{{ item.name }}</span>
        <Button
          text
          rounded
          severity="danger"
          :aria-label="t('common.remove')"
          @click="removeItem(item.id)"
        >
          <template #icon>
            <FontAwesomeIcon icon="fa-solid fa-trash" />
          </template>
        </Button>
      </li>
    </ul>

    <InputText
      v-model="query"
      class="relation-picker__input"
      :placeholder="t(placeholderKey)"
      @input="queueSearch"
      @blur="handleInputBlur"
    />

    <ul v-if="suggestions.length" class="relation-picker__suggestions">
      <li v-for="item in suggestions" :key="item.id">
        <button
          type="button"
          class="relation-picker__suggestion-btn"
          @mousedown.prevent="handleSuggestionMouseDown(item)"
        >
          {{ item.name }}
        </button>
      </li>
    </ul>

    <p v-else-if="showNoResults" class="relation-picker__no-results">{{ t('common.noResults') }}</p>
  </div>
</template>

<style scoped>
.relation-picker {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.relation-picker__selected {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.relation-picker__selected-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1px solid var(--app-content-border);
  border-radius: 8px;
  background: var(--app-content-item-bg);
  padding: 0.375rem 0.5rem;
}

.relation-picker__input {
  width: 100%;
}

.relation-picker__suggestions {
  list-style: none;
  margin: 0;
  padding: 0;
  border: 1px solid var(--app-content-border);
  border-radius: 8px;
  background: var(--app-content-bg);
}

.relation-picker__suggestion-btn {
  width: 100%;
  border: 0;
  background: transparent;
  text-align: left;
  padding: 0.5rem 0.625rem;
  cursor: pointer;
  color: var(--app-text-color);
}

.relation-picker__suggestion-btn:hover {
  background: var(--app-content-item-bg);
}

.relation-picker__no-results {
  margin: 0;
  color: var(--app-text-color);
}
</style>