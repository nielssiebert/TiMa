<script setup lang="ts">
import EntityOverviewShell from '../components/EntityOverviewShell.vue'
import { entityDefinitions } from '../shared/entityModels'

const definition = entityDefinitions.triggers

function isActivationDisabled(item: Record<string, unknown>): boolean {
  if (item.recurrance_type !== 'ONE_TIME') {
    return false
  }

  const dateValue = toStringValue(item.date)
  const timeValue = toStringValue(item.time)
  const scheduleAt = parseTriggerDateTime(dateValue, timeValue)
  return scheduleAt !== null && scheduleAt.getTime() < Date.now()
}

function toStringValue(value: unknown): string | undefined {
  return typeof value === 'string' ? value : undefined
}

function parseTriggerDateTime(dateValue?: string, timeValue?: string): Date | null {
  if (!dateValue || !timeValue) {
    return null
  }
  const timePart = timeValue.slice(0, 8)
  if (timePart.length !== 8) {
    return null
  }
  const parsed = new Date(`${dateValue}T${timePart}`)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}
</script>

<template>
  <EntityOverviewShell
    :title-key="definition.titleKey"
    :maintenance-route-name="definition.maintenanceRouteName"
    :api-path="definition.apiPath"
    show-activation-toggle
    :activation-disabled-evaluator="isActivationDisabled"
  />
</template>
