<script setup lang="ts">
import Button from 'primevue/button'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  titleKey: string
  entityId: string
  overviewRouteName: string
}>()

const router = useRouter()
const { t } = useI18n()

function cancel(): void {
  router.push({ name: props.overviewRouteName })
}

function save(): void {
  window.alert(t('common.emptySaveInfo'))
}
</script>

<template>
  <section class="entity-card entity-maintenance">
    <h2 class="entity-card__title">{{ t(titleKey) }}</h2>
    <p class="entity-maintenance__id">{{ t('common.idLabel') }}: {{ entityId }}</p>
    <p>{{ t('common.emptyMaintenance') }}</p>

    <footer class="entity-maintenance__footer">
      <Button severity="secondary" :label="t('common.cancel')" @click="cancel">
        <template #icon>
          <FontAwesomeIcon icon="fa-solid fa-xmark" />
        </template>
      </Button>
      <Button :label="t('common.save')" @click="save">
        <template #icon>
          <FontAwesomeIcon icon="fa-solid fa-floppy-disk" />
        </template>
      </Button>
    </footer>
  </section>
</template>
