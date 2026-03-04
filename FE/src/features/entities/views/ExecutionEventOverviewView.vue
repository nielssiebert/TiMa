<script setup lang="ts">
import EntityOverviewShell from '../components/EntityOverviewShell.vue'
import { entityDefinitions } from '../shared/entityModels'

const definition = entityDefinitions.executionEvents

function isRunning(item: Record<string, unknown>): boolean {
  return item.status === 'ON'
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
