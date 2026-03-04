import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '../layout/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../features/auth/views/LoginView.vue'),
      meta: {
        guestOnly: true,
      },
    },
    {
      path: '/awaiting-confirmation',
      name: 'awaiting-confirmation',
      component: () => import('../features/auth/views/PendingConfirmationView.vue'),
      meta: {
        requiresAuth: true,
      },
    },
    {
      path: '/',
      component: AppLayout,
      meta: {
        requiresAuth: true,
        requiresConfirmed: true,
      },
      children: [
        {
          path: '',
          redirect: '/execution-events',
        },
        {
          path: 'execution-events',
          name: 'execution-events-overview',
          component: () => import('../features/entities/views/ExecutionEventOverviewView.vue'),
        },
        {
          path: 'execution-events/:id',
          name: 'execution-events-maintenance',
          component: () => import('../features/entities/views/ExecutionEventMaintenanceView.vue'),
          props: true,
        },
        {
          path: 'execution-event-groups',
          name: 'execution-event-groups-overview',
          component: () => import('../features/entities/views/ExecutionEventGroupOverviewView.vue'),
        },
        {
          path: 'execution-event-groups/:id',
          name: 'execution-event-groups-maintenance',
          component: () =>
            import('../features/entities/views/ExecutionEventGroupMaintenanceView.vue'),
          props: true,
        },
        {
          path: 'sequences',
          name: 'sequences-overview',
          component: () => import('../features/entities/views/SequenceOverviewView.vue'),
        },
        {
          path: 'sequences/:id',
          name: 'sequences-maintenance',
          component: () => import('../features/entities/views/SequenceMaintenanceView.vue'),
          props: true,
        },
        {
          path: 'triggers',
          name: 'triggers-overview',
          component: () => import('../features/entities/views/TriggerOverviewView.vue'),
        },
        {
          path: 'triggers/:id',
          name: 'triggers-maintenance',
          component: () => import('../features/entities/views/TriggerMaintenanceView.vue'),
          props: true,
        },
        {
          path: 'factors',
          name: 'factors-overview',
          component: () => import('../features/entities/views/FactorOverviewView.vue'),
        },
        {
          path: 'factors/:id',
          name: 'factors-maintenance',
          component: () => import('../features/entities/views/FactorMaintenanceView.vue'),
          props: true,
        },
        {
          path: 'user',
          name: 'user-overview',
          component: () => import('../features/users/views/UserView.vue'),
        },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const authStore = useAuthStore()

  if (to.meta.guestOnly) {
    if (authStore.isAuthenticated && authStore.isConfirmed) {
      return '/execution-events'
    }
    if (authStore.isAuthenticated) {
      return '/awaiting-confirmation'
    }
    return true
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return '/login'
  }

  if (to.meta.requiresConfirmed && !authStore.isConfirmed) {
    return '/awaiting-confirmation'
  }

  return true
})

export default router
