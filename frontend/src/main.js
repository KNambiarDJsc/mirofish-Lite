import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { clerkPlugin } from '@clerk/vue'

const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

if (!PUBLISHABLE_KEY) {
  console.error(
    '[AXonic] Clerk publishable key is missing.\n' +
    'Add VITE_CLERK_PUBLISHABLE_KEY to frontend/.env\n' +
    'Get your key at: https://dashboard.clerk.com'
  )
}

const app = createApp(App)

app.use(clerkPlugin, { publishableKey: PUBLISHABLE_KEY || 'pk_test_placeholder' })
app.use(router)

app.mount('#app')
