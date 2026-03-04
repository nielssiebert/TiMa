export type EntityKey =
  | 'executionEvents'
  | 'executionEventGroups'
  | 'sequences'
  | 'triggers'
  | 'factors'

export interface EntityDefinition {
  key: EntityKey
  titleKey: string
  maintenanceTitleKey: string
  overviewRouteName: string
  maintenanceRouteName: string
  apiPath: string
}

export interface EntityListItem {
  id: string
  name: string
  activated?: boolean
  activationDisabled?: boolean
  isRunning?: boolean
}

export const entityDefinitions: Record<EntityKey, EntityDefinition> = {
  executionEvents: {
    key: 'executionEvents',
    titleKey: 'entities.executionEvents.title',
    maintenanceTitleKey: 'entities.executionEvents.maintenanceTitle',
    overviewRouteName: 'execution-events-overview',
    maintenanceRouteName: 'execution-events-maintenance',
    apiPath: '/execution-events',
  },
  executionEventGroups: {
    key: 'executionEventGroups',
    titleKey: 'entities.executionEventGroups.title',
    maintenanceTitleKey: 'entities.executionEventGroups.maintenanceTitle',
    overviewRouteName: 'execution-event-groups-overview',
    maintenanceRouteName: 'execution-event-groups-maintenance',
    apiPath: '/execution-event-groups',
  },
  sequences: {
    key: 'sequences',
    titleKey: 'entities.sequences.title',
    maintenanceTitleKey: 'entities.sequences.maintenanceTitle',
    overviewRouteName: 'sequences-overview',
    maintenanceRouteName: 'sequences-maintenance',
    apiPath: '/sequences',
  },
  triggers: {
    key: 'triggers',
    titleKey: 'entities.triggers.title',
    maintenanceTitleKey: 'entities.triggers.maintenanceTitle',
    overviewRouteName: 'triggers-overview',
    maintenanceRouteName: 'triggers-maintenance',
    apiPath: '/triggers',
  },
  factors: {
    key: 'factors',
    titleKey: 'entities.factors.title',
    maintenanceTitleKey: 'entities.factors.maintenanceTitle',
    overviewRouteName: 'factors-overview',
    maintenanceRouteName: 'factors-maintenance',
    apiPath: '/factors',
  },
}
