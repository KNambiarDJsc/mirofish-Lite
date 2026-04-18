<template>
  <div class="rv-root">
    <!-- Gradient Background -->
    <div class="rv-bg"></div>

    <!-- NAV -->
    <nav class="rv-nav">
      <div class="rv-logo" @click="router.push('/')">AX<span class="logo-dot">◈</span>ONIC</div>
      <div class="nav-phases">
        <span class="phase done">01 Definition</span>
        <span class="phase-sep">——</span>
        <span class="phase" :class="{ active: phase >= 1 }">02 Simulation</span>
        <span class="phase-sep">——</span>
        <span class="phase" :class="{ active: phase >= 2 }">03 Report</span>
      </div>
      <div class="nav-right-group">
        <div class="nav-status" :class="statusClass">
          <span class="status-dot"></span>
          {{ statusText }}
        </div>
        <UserButton after-sign-out-url="/" />
      </div>
    </nav>

    <!-- MAIN -->
    <main class="rv-main">
      <div class="rv-content" :class="{ 'content-ready': ready }">

        <!-- Title -->
        <div class="rv-header">
          <h1 class="rv-title">Running your Simulation</h1>
          <p class="rv-subtitle">Your simulation is running. Your detailed report will be ready soon.</p>
        </div>

        <!-- STEP CARD (matches screenshot exactly) -->
        <div class="step-card">

          <!-- Card Header (collapsed / expanded state) -->
          <div class="sc-header">
            <div class="sc-header-left">
              <span class="sc-current-title">{{ activeStep ? activeStep.title : 'Campaign Loading' }}</span>
              <span class="sc-step-badge" v-if="activeStepIndex >= 0">
                STEP {{ activeStepIndex + 1 }} OF {{ steps.length }}
              </span>
            </div>
            <div class="sc-header-right">
              <span class="sc-pct" v-if="activeStep">{{ activeStep.pct }}%</span>
              <button class="sc-toggle" @click="expanded = !expanded">
                {{ expanded ? '∧' : '∨' }}
              </button>
            </div>
          </div>

          <!-- Steps List -->
          <div class="sc-steps" v-show="expanded">
            <div
              v-for="(step, i) in steps"
              :key="i"
              class="sc-step-row"
              :class="{
                'scr-done':    step.done,
                'scr-active':  step.active,
                'scr-pending': !step.done && !step.active
              }"
            >
              <!-- Number -->
              <div class="scr-num">{{ String(i + 1).padStart(2, '0') }}</div>

              <!-- Title + sub -->
              <div class="scr-body">
                <div class="scr-title">{{ step.title }}</div>
                <div class="scr-sub" v-if="step.active && step.sub">{{ step.sub }}</div>
              </div>

              <!-- Right state -->
              <div class="scr-right">
                <span v-if="step.done" class="scr-check">
                  <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                    <circle cx="9" cy="9" r="9" fill="#28C840"/>
                    <path d="M5 9l3 3 5-5" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </span>
                <span v-else-if="step.active" class="scr-pct-active">{{ step.pct }}%</span>
                <span v-else class="scr-zero">0%</span>
              </div>
            </div>
          </div>

        </div>

        <!-- Log ticker below card -->
        <div class="rv-log" v-if="running">
          <span class="log-dot"></span>
          <span class="log-text">{{ currentLog }}</span>
          <span class="log-cursor">_</span>
        </div>

        <!-- Error -->
        <div class="rv-error" v-if="error">
          <span>⚠ {{ error }}</span>
          <button class="retry-btn" @click="retryRun">Retry →</button>
        </div>

      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { loadCampaign, runSimulation, generateReport, saveSimResult } from '../api/mvp.js'
import { UserButton } from '@clerk/vue'

const router   = useRouter()
const phase    = ref(1)
const running  = ref(true)
const error    = ref('')
const ready    = ref(false)
const expanded = ref(true)
const currentLog = ref('Initializing AXonic simulation engine...')
const campaign = ref(null)

const steps = ref([
  { title: 'Campaign Loading',   sub: '',                         active: false, done: false, pct: 0 },
  { title: 'Audience Modelling', sub: 'Applying different models...', active: false, done: false, pct: 0 },
  { title: 'Market Intelligence',sub: 'Scanning market data...',  active: false, done: false, pct: 0 },
  { title: 'Run Simulations',    sub: 'Running simulation rounds...', active: false, done: false, pct: 0 },
  { title: 'Report Generation',  sub: 'Generating decision report...', active: false, done: false, pct: 0 },
])

const activeStepIndex = computed(() => steps.value.findIndex(s => s.active))
const activeStep      = computed(() => steps.value[activeStepIndex.value] || null)

const statusClass = computed(() => {
  if (error.value)    return 'status-error'
  if (!running.value) return 'status-done'
  return 'status-running'
})
const statusText = computed(() => {
  if (error.value)    return 'Error'
  if (!running.value) return 'Complete'
  return 'Running'
})

const setLog = (msg) => { currentLog.value = msg }
const wait   = (ms) => new Promise(r => setTimeout(r, ms))

const activateStep = (i, sub = '') => {
  steps.value.forEach((s, j) => {
    if (j < i)  { s.done = true; s.active = false; s.pct = 100 }
    if (j === i) { s.active = true; s.done = false; s.sub = sub; s.pct = 0 }
    if (j > i)  { s.active = false; s.done = false; s.pct = 0 }
  })
}

const animateStepPct = async (stepIdx, target = 100, durationMs = 1400) => {
  const s = steps.value[stepIdx]
  const interval = 50
  const steps_n  = durationMs / interval
  const increment = target / steps_n
  for (let p = 0; p <= target; p += increment) {
    if (!steps.value[stepIdx].active) break
    s.pct = Math.min(target, Math.round(p))
    await wait(interval)
  }
  s.pct = target
}

const completeStep = (i) => {
  steps.value[i].done   = true
  steps.value[i].active = false
  steps.value[i].pct    = 100
}

const runFlow = async () => {
  campaign.value = loadCampaign()
  if (!campaign.value) { router.push({ name: 'Campaign' }); return }

  setLog('Campaign loaded successfully.')

  // Step 0: Campaign Loading
  activateStep(0, 'Loading campaign files...')
  await animateStepPct(0, 100, 800)
  completeStep(0)
  await wait(200)

  // Step 1: Audience Modelling
  activateStep(1, 'Applying different models...')
  setLog('Modelling target audience segments for Indian market...')
  const audienceAnim = animateStepPct(1, 48, 1600)
  await wait(1000)
  setLog('Segmenting Tier 1, 2, 3 Indian consumer archetypes...')
  await audienceAnim
  await wait(300)
  completeStep(1)

  // Step 2: Market Intelligence
  activateStep(2, 'Scanning market data...')
  setLog(`Loading ${campaign.value.platform || 'Digital'} market intelligence...`)
  await animateStepPct(2, 100, 1200)
  completeStep(2)
  await wait(200)

  // Step 3: Run Simulations
  activateStep(3, 'Running simulation rounds...')
  setLog('Calling simulation intelligence layer...')
  let simEvents = []
  try {
    const simPctAnim = animateStepPct(3, 80, 3000)
    const simRes = await runSimulation(campaign.value)
    simEvents    = simRes.events || []
    await simPctAnim
    await animateStepPct(3, 100, 400)
  } catch (e) {
    setLog('Using rule-based simulation fallback...')
    simEvents = []
    await animateStepPct(3, 100, 600)
  }
  completeStep(3)
  await wait(200)

  // Step 4: Report Generation
  phase.value = 2
  activateStep(4, 'Generating decision report...')
  setLog('Generating decision report — Gemini 2.5 Flash...')

  try {
    const repPctAnim = animateStepPct(4, 80, 4000)
    const repRes = await generateReport(campaign.value, simEvents)
    saveSimResult({
      campaign: campaign.value,
      events: simEvents,
      report: repRes.report,
      tier:   repRes.tier_used,
      model:  repRes.model_used,
      credits: repRes.credits_display,
    })
    await repPctAnim
    await animateStepPct(4, 100, 300)
    completeStep(4)
    setLog('Report complete. Redirecting...')
    running.value = false
    await wait(700)
    router.push({ name: 'Report' })
  } catch (e) {
    error.value = `Report generation failed: ${e.message}`
    running.value = false
  }
}

const retryRun = () => { error.value = ''; running.value = true; runFlow() }

onMounted(() => {
  setTimeout(() => { ready.value = true }, 80)
  runFlow()
})
</script>

<style scoped>
/* ── Root & Background ─────────────────────────────────────── */
.rv-root {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
  font-family: 'Inter', system-ui, sans-serif;
}

.rv-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  background:
    radial-gradient(ellipse at 0% 50%,   rgba(232,121,58,0.20) 0%, transparent 55%),
    radial-gradient(ellipse at 100% 50%,  rgba(255,200,120,0.20) 0%, transparent 55%),
    radial-gradient(ellipse at 50% 100%, rgba(232,121,58,0.10) 0%, transparent 50%),
    #FDF6EC;
  animation: bg-drift 22s ease-in-out infinite alternate;
}
@keyframes bg-drift {
  0%   { opacity: 1; }
  50%  { opacity: 0.9; }
  100% { opacity: 1; }
}

/* ── NAV ──────────────────────────────────────────────────── */
.rv-nav {
  position: relative;
  z-index: 10;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 40px;
  border-bottom: 1px solid rgba(61,30,15,0.08);
  background: rgba(253,246,236,0.7);
  backdrop-filter: blur(12px);
}
.rv-logo {
  font-weight: 800;
  font-size: 15px;
  letter-spacing: 3px;
  color: #3D1E0F;
  cursor: pointer;
  user-select: none;
}
.logo-dot { color: #E8793A; font-size: 12px; margin: 0 2px; }

.nav-phases {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  letter-spacing: 0.5px;
}
.phase { color: rgba(61,30,15,0.3); font-weight: 500; transition: color 0.3s; }
.phase.done   { color: rgba(61,30,15,0.5); }
.phase.active { color: #E8793A; font-weight: 700; }
.phase-sep    { color: rgba(61,30,15,0.2); font-size: 10px; }

.nav-right-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.nav-status {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  font-weight: 600;
  padding: 5px 14px;
  border-radius: 20px;
  border: 1.5px solid;
  transition: all 0.3s;
}
.status-running { border-color: rgba(232,121,58,0.4); color: #E8793A; background: rgba(232,121,58,0.07); }
.status-done    { border-color: rgba(40,200,64,0.4);  color: #28C840; background: rgba(40,200,64,0.07); }
.status-error   { border-color: rgba(192,57,43,0.4);  color: #c0392b; background: rgba(192,57,43,0.07); }
.status-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: currentColor;
  animation: dot-pulse 1.2s infinite;
}
@keyframes dot-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.2; } }

/* ── MAIN ─────────────────────────────────────────────────── */
.rv-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 24px 80px;
  position: relative;
  z-index: 2;
}

/* ── CONTENT ──────────────────────────────────────────────── */
.rv-content {
  width: 100%;
  max-width: 540px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 28px;
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}
.rv-content.content-ready { opacity: 1; transform: none; }

/* ── HEADER ───────────────────────────────────────────────── */
.rv-header { text-align: center; }
.rv-title {
  font-size: clamp(2rem, 5vw, 3rem);
  font-weight: 800;
  color: #2D1A0A;
  letter-spacing: -1.5px;
  line-height: 1.1;
  margin: 0 0 14px;
  font-family: 'Georgia', 'Times New Roman', serif;
}
.rv-subtitle {
  font-size: 0.95rem;
  color: #8A6A50;
  line-height: 1.6;
  margin: 0;
}

/* ── STEP CARD ────────────────────────────────────────────── */
.step-card {
  width: 100%;
  background: #FFFFFF;
  border-radius: 18px;
  border: 1px solid rgba(61,30,15,0.09);
  box-shadow: 0 8px 40px rgba(61,30,15,0.1);
  overflow: hidden;
}

/* Card Header */
.sc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  cursor: pointer;
  user-select: none;
}
.sc-header-left { display: flex; align-items: center; gap: 10px; }
.sc-current-title {
  font-size: 15px;
  font-weight: 700;
  color: #2D1A0A;
}
.sc-step-badge {
  font-size: 10px;
  color: #BBA890;
  letter-spacing: 0.5px;
  font-weight: 500;
}
.sc-header-right { display: flex; align-items: center; gap: 10px; }
.sc-pct {
  font-size: 15px;
  font-weight: 700;
  color: #2D1A0A;
}
.sc-toggle {
  background: none;
  border: none;
  color: #BBA890;
  font-size: 14px;
  cursor: pointer;
  padding: 4px 8px;
  transition: color 0.2s;
}
.sc-toggle:hover { color: #3D1E0F; }

/* Steps list */
.sc-steps {
  border-top: 1px solid rgba(61,30,15,0.07);
}

.sc-step-row {
  display: flex;
  align-items: center;
  padding: 14px 22px;
  gap: 16px;
  border-bottom: 1px solid rgba(61,30,15,0.05);
  transition: background 0.2s;
}
.sc-step-row:last-child { border-bottom: none; }

/* States */
.scr-done    { opacity: 0.85; }
.scr-active  { background: rgba(232,121,58,0.03); }
.scr-pending { opacity: 0.5; }

/* Number */
.scr-num {
  font-size: 12px;
  font-weight: 700;
  color: #C4A882;
  width: 22px;
  flex-shrink: 0;
  font-family: monospace;
}
.scr-active .scr-num { color: #E8793A; }
.scr-done   .scr-num { color: #C4A882; }

/* Body */
.scr-body { flex: 1; min-width: 0; }
.scr-title {
  font-size: 14px;
  font-weight: 600;
  color: #5A3E28;
  transition: color 0.3s;
}
.scr-active .scr-title { color: #E8793A; }
.scr-done   .scr-title { color: #5A3E28; }
.scr-sub {
  font-size: 11px;
  color: #BBA890;
  margin-top: 2px;
}

/* Right state */
.scr-right { flex-shrink: 0; display: flex; align-items: center; }
.scr-check { color: #28C840; }
.scr-pct-active {
  font-size: 13px;
  font-weight: 700;
  color: #2D1A0A;
  font-family: monospace;
  min-width: 36px;
  text-align: right;
}
.scr-zero {
  font-size: 13px;
  color: #D4C0AA;
  font-family: monospace;
  min-width: 36px;
  text-align: right;
}

/* ── LOG TICKER ───────────────────────────────────────────── */
.rv-log {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #8A6A50;
  font-family: monospace;
}
.log-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #E8793A;
  flex-shrink: 0;
  animation: dot-pulse 1.2s infinite;
}
.log-text { flex: 1; }
.log-cursor { animation: blink 1s step-end infinite; color: #E8793A; }
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }

/* ── ERROR ────────────────────────────────────────────────── */
.rv-error {
  width: 100%;
  background: rgba(192,57,43,0.08);
  border: 1px solid rgba(192,57,43,0.25);
  border-radius: 12px;
  padding: 14px 18px;
  font-size: 13px;
  color: #c0392b;
  display: flex;
  align-items: center;
  gap: 12px;
}
.retry-btn {
  margin-left: auto;
  background: #E8793A;
  border: none;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  padding: 7px 18px;
  border-radius: 20px;
  cursor: pointer;
  transition: background 0.2s;
}
.retry-btn:hover { background: #d4622a; }
</style>
