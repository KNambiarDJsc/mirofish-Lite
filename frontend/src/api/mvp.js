import service from './index.js'

const BASE = '/api/mvp'

/** Generate a stable user ID for this browser session */
export function getUserId() {
  let id = localStorage.getItem('axonic_uid')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('axonic_uid', id)
  }
  return id
}

/** Persist campaign data between screens */
export function saveCampaign(campaign) {
  localStorage.setItem('axonic_campaign', JSON.stringify(campaign))
}
export function loadCampaign() {
  try { return JSON.parse(localStorage.getItem('axonic_campaign')) } catch { return null }
}

/** Persist simulation results between screens */
export function saveSimResult(data) {
  localStorage.setItem('axonic_sim', JSON.stringify(data))
}
export function loadSimResult() {
  try { return JSON.parse(localStorage.getItem('axonic_sim')) } catch { return null }
}

/** POST /api/mvp/simulate */
export async function runSimulation(campaign) {
  return service.post(`${BASE}/simulate`, {
    user_id:  getUserId(),
    campaign,
  })
}

/** POST /api/mvp/report */
export async function generateReport(campaign, events) {
  return service.post(`${BASE}/report`, {
    user_id:       getUserId(),
    campaign,
    events,
    simulation_id: crypto.randomUUID(),
  })
}

/** GET /api/mvp/balance */
export async function getBalance() {
  return service.get(`${BASE}/balance`, { params: { user_id: getUserId() } })
}

/** POST /api/mvp/purchase */
export async function purchaseCredits(pack, paymentId) {
  return service.post(`${BASE}/purchase`, {
    user_id:    getUserId(),
    pack,
    payment_id: paymentId,
  })
}
