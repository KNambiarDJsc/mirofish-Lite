import { createRouter, createWebHistory } from 'vue-router'
import LandingView  from '../views/LandingView.vue'
import CampaignView from '../views/CampaignView.vue'
import RunView      from '../views/RunView.vue'
import ReportView   from '../views/ReportView.vue'

const routes = [
  { path: '/',         name: 'Landing',  component: LandingView  },
  { path: '/start',    name: 'Campaign', component: CampaignView },
  { path: '/run',      name: 'Run',      component: RunView      },
  { path: '/report',   name: 'Report',   component: ReportView   },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

export default router
