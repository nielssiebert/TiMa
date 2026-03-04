import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/aura'

import App from './App.vue'
import router from './router'
import { i18n } from './core/i18n'
import { registerFontAwesome } from './core/ui/fontawesome'
import { setUnauthorizedHandler } from './core/api/httpClient'
import { useAuthStore } from './stores/auth'
import ToastService from 'primevue/toastservice'
import PrimeToast from 'primevue/toast'
import './styles/main.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(i18n)
app.use(PrimeVue, {
	theme: {
		preset: Aura,
	},
})
app.use(ToastService)

setUnauthorizedHandler(() => {
	const authStore = useAuthStore(pinia)
	authStore.logout()
	if (router.currentRoute.value.path !== '/login') {
		void router.push('/login')
	}
})

registerFontAwesome(app)

app.component('AppToast', PrimeToast)

app.mount('#app')
