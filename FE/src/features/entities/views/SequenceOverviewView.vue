<script setup lang="ts">
import EntityOverviewShell from '../components/EntityOverviewShell.vue'
import { entityDefinitions } from '../shared/entityModels'

const definition = entityDefinitions.sequences

function isRunning(item: Record<string, unknown>): boolean {
  const runtime = item.runtime
  if (typeof runtime !== 'object' || runtime === null) {
    return false
  }
  const running = (runtime as { is_running?: unknown }).is_running
  return running === true
}
</script>

<template>
  <EntityOverviewShell
    :title-key="definition.titleKey"
    :maintenance-route-name="definition.maintenanceRouteName"
    :api-path="definition.apiPath"
    show-running-toggle
    :running-state-evaluator="isRunning"
  />
</template>
