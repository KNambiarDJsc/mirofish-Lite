import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '@clerk/vue'

import LandingView  from '../views/LandingView.vue'
import CampaignView from '../views/CampaignView.vue'
import RunView      from '../views/RunView.vue'
import ReportView   from '../views/ReportView.vue'
import SignInView   from '../views/SignInView.vue'
import SignUpView   from '../views/SignUpView.vue'

const routes = [
  // ── Public ──────────────────────────────────────────────────
  { path: '/',         name: 'Landing',  component: LandingView,  meta: { public: true } },
  { path: '/sign-in',  name: 'SignIn',   component: SignInView,    meta: { public: true, authPage: true } },
  { path: '/sign-up',  name: 'SignUp',   component: SignUpView,    meta: { public: true, authPage: true } },

  // ── Protected ────────────────────────────────────────────────
  { path: '/start',    name: 'Campaign', component: CampaignView, meta: { requiresAuth: true } },
  { path: '/run',      name: 'Run',      component: RunView,      meta: { requiresAuth: true } },
  { path: '/report',   name: 'Report',   component: ReportView,   meta: { requiresAuth: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

// ── Auth guard ────────────────────────────────────────────────
router.beforeEach(async (to) => {
  // If the route doesn't need auth, always allow
  if (to.meta.public) return true

  // Check if the route requires auth
  if (to.meta.requiresAuth) {
    // useAuth works outside components in Vue 3 when clerk is initialised
    const { isSignedIn, isLoaded } = useAuth()

    // Wait for Clerk to finish loading
    if (!isLoaded.value) {
      // Clerk not ready yet — allow through and let the component handle it
      return true
    }

    if (!isSignedIn.value) {
      // Redirect to sign-in, remember where they were going
      return { name: 'SignIn', query: { redirect: to.fullPath } }
    }
  }

  return true
})

export default router
