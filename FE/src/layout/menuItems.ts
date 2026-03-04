export interface MainMenuItem {
  key: string
  labelKey: string
  to: string
}

export const mainMenuItems: MainMenuItem[] = [
  {
    key: 'execution-events',
    labelKey: 'menu.executionEvents',
    to: '/execution-events',
  },
  {
    key: 'execution-event-groups',
    labelKey: 'menu.executionEventGroups',
    to: '/execution-event-groups',
  },
  {
    key: 'sequences',
    labelKey: 'menu.sequences',
    to: '/sequences',
  },
  {
    key: 'triggers',
    labelKey: 'menu.triggers',
    to: '/triggers',
  },
  {
    key: 'factors',
    labelKey: 'menu.factors',
    to: '/factors',
  },
  {
    key: 'user',
    labelKey: 'menu.user',
    to: '/user',
  },
]
