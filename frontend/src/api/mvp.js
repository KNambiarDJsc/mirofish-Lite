import service from './index.js'

const BASE = '/api/mvp'

/** Stable session ID as fallback */
export function getSessionId() {
  let id = localStorage.getItem('axonic_session_id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('axonic_session_id', id)
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
export async function runSimulation(user_id, campaign) {
  return service.post(`${BASE}/simulate`, {
    user_id,
    campaign,
    simulation_id: getSessionId()
  })
}

/** POST /api/mvp/report */
export async function generateReport(user_id, campaign, events) {
  return service.post(`${BASE}/report`, {
    user_id,
    campaign,
    events,
    simulation_id: getSessionId(),
  })
}

/** GET /api/mvp/balance */
export async function getBalance(user_id) {
  if (!user_id) return { compute_units: 0, credits_display: 0 }
  return service.get(`${BASE}/balance`, { params: { user_id } })
}

/** POST /api/mvp/purchase */
export async function purchaseCredits(user_id, pack, paymentId) {
  return service.post(`${BASE}/purchase`, {
    user_id,
    pack,
    payment_id: paymentId,
  })
}
