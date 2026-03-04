<script setup lang="ts">
import EntityOverviewShell from '../components/EntityOverviewShell.vue'
import { entityDefinitions } from '../shared/entityModels'

const definition = entityDefinitions.factors
</script>

<template>
  <EntityOverviewShell
    :title-key="definition.titleKey"
    :maintenance-route-name="definition.maintenanceRouteName"
    :api-path="definition.apiPath"
    show-activation-toggle
  />
</template>
