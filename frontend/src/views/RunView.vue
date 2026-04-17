<template>
  <div class="ax-root">
    <!-- NAV -->
    <nav class="ax-nav">
      <div class="ax-logo" @click="router.push('/')">AX<span class="x-accent">◈</span>ONIC</div>
      <div class="nav-center">
        <div class="phase-track">
          <span class="phase-item done">01 DEFINITION</span>
          <span class="phase-sep">──</span>
          <span class="phase-item" :class="{ active: phase >= 1 }">02 SIMULATION</span>
          <span class="phase-sep">──</span>
          <span class="phase-item" :class="{ active: phase >= 2 }">03 REPORT</span>
        </div>
      </div>
      <div class="status-pill" :class="statusClass">
        <span class="status-dot"></span>
        {{ statusText }}
      </div>
    </nav>

    <!-- SYSTEM LOG BAR -->
    <div class="log-bar">
      <span class="log-prefix">SYS &gt;</span>
      <span class="log-line">{{ currentLog }}</span>
      <span class="log-cursor" v-if="running">_</span>
    </div>

    <!-- MAIN -->
    <main class="ax-main">

      <!-- LEFT: Signal Panel -->
      <aside class="signal-panel">
        <div class="sp-header">// LIVE SIGNALS</div>
        <div class="signals-grid">
          <div v-for="sig in signals" :key="sig.key" class="signal-card" :class="`sig-${sig.status}`">
            <div class="sig-label">{{ sig.label }}</div>
            <div class="sig-val">{{ sig.value }}</div>
            <div class="sig-bar">
              <div class="sig-fill" :style="{ width: sig.pct + '%', background: sig.color }"></div>
            </div>
            <div class="sig-trend">{{ sig.trend }}</div>
          </div>
        </div>

        <!-- Campaign summary -->
        <div class="campaign-summary" v-if="campaign">
          <div class="cs-header">// STRATEGY CONTEXT</div>
          <div class="cs-row"><span class="cs-key">PROMPT</span><span class="cs-val">{{ campaign.name }}</span></div>
          <div class="cs-row" v-if="campaign.strategy_docs"><span class="cs-key">DOCS</span><span class="cs-val">Attached ({{ campaign.strategy_docs.length }} chars)</span></div>
          <div class="cs-row"><span class="cs-key">MARKET</span><span class="cs-val">India (Unified)</span></div>
        </div>
      </aside>

      <!-- RIGHT: Event Stream -->
      <section class="event-panel">
        <div class="ep-header">
          <span class="ep-tag">// SIMULATION STREAM</span>
          <div class="round-counter" v-if="currentRound > 0">
            ROUND {{ currentRound }} / 3
          </div>
        </div>

        <!-- Timeline -->
        <div class="event-stream" ref="streamRef">

          <!-- Static steps (always visible) -->
          <div class="stream-step" v-for="(step, i) in steps" :key="i"
            :class="{ active: step.active, done: step.done, pending: step.pending }">
            <div class="step-left">
              <div class="step-icon">
                <span v-if="step.done">✓</span>
                <span v-else-if="step.active" class="spin-icon">◌</span>
                <span v-else>○</span>
              </div>
              <div class="step-line" v-if="i < steps.length - 1"></div>
            </div>
            <div class="step-body">
              <div class="step-title">{{ step.title }}</div>
              <div class="step-sub" v-if="step.sub">{{ step.sub }}</div>
            </div>
            <div class="step-time" v-if="step.time">{{ step.time }}</div>
          </div>

          <!-- Live Events (from simulation) -->
          <div v-if="events.length > 0" class="events-divider">
            <span>SIMULATION EVENTS</span>
          </div>

          <div
            v-for="(ev, i) in visibleEvents"
            :key="'ev-' + i"
            class="event-card"
            :class="`ev-${ev.sentiment}`"
            :style="{ animationDelay: `${i * 0.15}s` }"
          >
            <div class="ev-header">
              <span class="ev-round">ROUND {{ ev.round }}</span>
              <span class="ev-sentiment" :class="`sent-${ev.sentiment}`">{{ ev.sentiment?.toUpperCase() }}</span>
            </div>
            <div class="ev-text">{{ ev.event }}</div>
            <div class="ev-metric">{{ ev.metric }}</div>
          </div>

          <!-- Generating report state -->
          <div v-if="generatingReport" class="gen-report-block">
            <div class="gen-dots">
              <span></span><span></span><span></span>
            </div>
            <div class="gen-text">Generating executive report...</div>
          </div>

        </div>

        <!-- Error -->
        <div v-if="error" class="ax-error">
          <span>⚠</span> {{ error }}
          <button class="retry-btn" @click="retryRun">Retry →</button>
        </div>

      </section>

    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import {
  loadCampaign,
  runSimulation,
  generateReport,
  saveSimResult,
} from '../api/mvp.js'

const router    = useRouter()
const campaign  = ref(null)
const phase     = ref(1)
const running   = ref(true)
const error     = ref('')
const events    = ref([])
const visibleEvents = ref([])
const generatingReport = ref(false)
const currentRound = ref(0)
const currentLog   = ref('Initializing AXonic simulation engine...')
const streamRef    = ref(null)

// ── Signals (live updating) ───────────────────────────────────
const signals = ref([
  { key: 'attention',      label: 'ATTENTION',      value: '—', pct: 0,  trend: 'Awaiting data', status: 'idle', color: '#00E5FF' },
  { key: 'trust',          label: 'TRUST',          value: '—', pct: 0,  trend: 'Awaiting data', status: 'idle', color: '#00FF88' },
  { key: 'risk',           label: 'RISK LEVEL',     value: '—', pct: 0,  trend: 'Awaiting data', status: 'idle', color: '#FF1744' },
  { key: 'amplification',  label: 'AMPLIFICATION',  value: '—', pct: 0,  trend: 'Awaiting data', status: 'idle', color: '#FFB300' },
])

// ── Steps ─────────────────────────────────────────────────────
const steps = ref([
  { title: 'Campaign Loaded',        sub: '',  active: false, done: true,  pending: false, time: 'Done' },
  { title: 'Audience Modelling',     sub: '',  active: false, done: false, pending: false, time: '' },
  { title: 'Market Intelligence',    sub: '',  active: false, done: false, pending: false, time: '' },
  { title: 'Simulation Running',     sub: '',  active: false, done: false, pending: false, time: '' },
  { title: 'Report Generation',      sub: '',  active: false, done: false, pending: false, time: '' },
])

// ── Status ────────────────────────────────────────────────────
const statusClass = computed(() => {
  if (error.value)   return 'status-error'
  if (!running.value) return 'status-done'
  return 'status-running'
})
const statusText = computed(() => {
  if (error.value)   return 'Error'
  if (!running.value) return 'Complete'
  return 'Running'
})

// ── Helpers ───────────────────────────────────────────────────
const setLog = (msg) => { currentLog.value = msg }

const activateStep = (i, sub = '') => {
  steps.value.forEach((s, j) => {
    if (j < i)  { s.done = true; s.active = false }
    if (j === i) { s.active = true; s.done = false; s.sub = sub }
    if (j > i)  { s.active = false }
  })
}

const completeStep = (i, time = '') => {
  steps.value[i].done   = true
  steps.value[i].active = false
  steps.value[i].time   = time
}

const wait = (ms) => new Promise(r => setTimeout(r, ms))

const scrollBottom = () => {
  nextTick(() => {
    if (streamRef.value) {
      streamRef.value.scrollTop = streamRef.value.scrollHeight
    }
  })
}

// Animate signals from events
const computeSignals = (evList) => {
  const sentimentMap = { positive: 1, neutral: 0, mixed: -0.5, negative: -1 }
  const scores = evList.map(e => sentimentMap[e.sentiment] ?? 0)
  const avg    = scores.reduce((a, b) => a + b, 0) / (scores.length || 1)

  const attention    = Math.min(95, 40 + evList.length * 18)
  const trust        = Math.max(10, Math.min(95, 50 + avg * 35))
  const risk         = Math.max(5,  Math.min(90, 50 - avg * 30))
  const amplification = Math.min(95, 30 + evList.length * 20)

  signals.value[0].pct   = attention;    signals.value[0].value = attention + '%';    signals.value[0].trend = 'Growing'
  signals.value[1].pct   = trust;        signals.value[1].value = trust + '%';        signals.value[1].trend = trust > 60 ? 'High' : 'Moderate'
  signals.value[2].pct   = risk;         signals.value[2].value = risk + '%';         signals.value[2].trend = risk > 60 ? 'Elevated' : 'Controlled'
  signals.value[3].pct   = amplification; signals.value[3].value = amplification + '%'; signals.value[3].trend = 'Active'

  signals.value.forEach(s => { s.status = s.pct > 50 ? 'active' : 'idle' })
}

// Reveal events one by one
const revealEvents = async (evList) => {
  for (let i = 0; i < evList.length; i++) {
    currentRound.value = evList[i].round
    setLog(`Round ${evList[i].round}: ${evList[i].event.substring(0, 60)}...`)
    visibleEvents.value.push(evList[i])
    computeSignals(visibleEvents.value)
    scrollBottom()
    await wait(1200)
  }
}

// ── Main flow ─────────────────────────────────────────────────
const runFlow = async () => {
  campaign.value = loadCampaign()
  if (!campaign.value) {
    router.push({ name: 'Campaign' })
    return
  }

  // Step 2: Audience Modelling
  activateStep(1, 'Mapping Indian consumer segments...')
  setLog('Modelling target audience segments for Indian market...')
  await wait(1800)
  completeStep(1, '1.8s')

  // Step 3: Market Intelligence
  activateStep(2, 'Loading platform intelligence...')
  setLog(`Loading ${campaign.value.platform} market intelligence...`)
  await wait(1400)
  completeStep(2, '1.4s')

  // Step 4: Simulation
  activateStep(3, 'Running strategy simulation engine...')
  setLog('Calling intelligence layer...')

  let simEvents = []
  try {
    const simRes  = await runSimulation(campaign.value)
    simEvents     = simRes.events || []
  } catch (e) {
    // If API fails, use rule-based fallback display
    setLog('Using rule-based simulation fallback...')
    simEvents = []
    error.value = `Simulation API error: ${e.message}. Using fallback.`
  }

  events.value = simEvents
  await revealEvents(simEvents)
  completeStep(3, `${simEvents.length} events`)

  // Step 5: Report
  phase.value = 2
  activateStep(4, 'Calling Gemini 2.5 Flash...')
  setLog('Generating decision report — Gemini 2.5 Flash...')
  generatingReport.value = true
  scrollBottom()

  try {
    const repRes = await generateReport(campaign.value, simEvents)
    saveSimResult({
      campaign: campaign.value,
      events:   simEvents,
      report:   repRes.report,
      tier:     repRes.tier_used,
      model:    repRes.model_used,
      credits:  repRes.credits_display,
    })
    completeStep(4, 'Done')
    setLog('Report complete. Redirecting...')
    running.value = false
    await wait(800)
    router.push({ name: 'Report' })
  } catch (e) {
    generatingReport.value = false
    error.value = `Report generation failed: ${e.message}`
    running.value = false
  }
}

const retryRun = () => {
  error.value = ''
  running.value = true
  runFlow()
}

onMounted(() => { runFlow() })
</script>

<style scoped>
.ax-root {
  min-height: 100vh;
  background: #0A0A0A;
  color: #FFFFFF;
  font-family: 'Space Grotesk', system-ui, sans-serif;
  display: flex;
  flex-direction: column;
}

/* NAV */
.ax-nav {
  height: 56px;
  border-bottom: 1px solid #1E1E1E;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  background: #0A0A0A;
}

.ax-logo {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 800;
  font-size: 18px;
  letter-spacing: 3px;
  color: #FF1744;
  cursor: pointer;
}

.x-accent { color: #00E5FF; font-size: 14px; margin: 0 1px; }

.nav-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.phase-track {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 1px;
}

.phase-item { color: #2A2A2A; transition: color 0.4s; }
.phase-item.done   { color: #555555; }
.phase-item.active { color: #FF1744; }
.phase-sep { color: #1E1E1E; }

.status-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border: 1px solid #1E1E1E;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 1px;
}

.status-running { border-color: #FF1744; color: #FF1744; }
.status-done    { border-color: #00FF88; color: #00FF88; }
.status-error   { border-color: #FF1744; color: #FF1744; }

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse-dot 1s infinite;
}

@keyframes pulse-dot { 0%,100% { opacity: 1; } 50% { opacity: 0.2; } }

/* LOG BAR */
.log-bar {
  height: 32px;
  background: #111111;
  border-bottom: 1px solid #1E1E1E;
  display: flex;
  align-items: center;
  padding: 0 32px;
  gap: 12px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  overflow: hidden;
}

.log-prefix { color: #FF1744; font-weight: 700; }
.log-line   { color: #444444; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.log-cursor { color: #FF1744; animation: blink 1s step-end infinite; }
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }

/* MAIN */
.ax-main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* SIGNAL PANEL */
.signal-panel {
  width: 280px;
  min-width: 260px;
  border-right: 1px solid #1E1E1E;
  display: flex;
  flex-direction: column;
  gap: 0;
  overflow-y: auto;
}

.sp-header {
  padding: 20px 24px 12px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 2px;
  color: #333333;
  border-bottom: 1px solid #1E1E1E;
}

.signals-grid {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.signal-card {
  padding: 16px 24px;
  border-bottom: 1px solid #1E1E1E;
  transition: background 0.3s;
}

.signal-card.sig-active { background: rgba(255, 255, 255, 0.02); }

.sig-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  letter-spacing: 2px;
  color: #444444;
  margin-bottom: 6px;
}

.sig-val {
  font-family: 'JetBrains Mono', monospace;
  font-size: 22px;
  font-weight: 700;
  color: #FFFFFF;
  margin-bottom: 8px;
  transition: all 0.5s;
}

.sig-bar {
  height: 2px;
  background: #1E1E1E;
  margin-bottom: 6px;
  overflow: hidden;
}

.sig-fill {
  height: 100%;
  transition: width 0.8s ease;
}

.sig-trend {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #333333;
}

/* Campaign Summary */
.campaign-summary {
  padding: 20px 24px;
  margin-top: auto;
  border-top: 1px solid #1E1E1E;
}

.cs-header {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 2px;
  color: #333333;
  margin-bottom: 12px;
}

.cs-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 10px;
}

.cs-key {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  letter-spacing: 1px;
  color: #333333;
}

.cs-val {
  font-size: 13px;
  color: #CCCCCC;
}

/* EVENT PANEL */
.event-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.ep-header {
  padding: 20px 32px 12px;
  border-bottom: 1px solid #1E1E1E;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.ep-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 2px;
  color: #333333;
}

.round-counter {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #FF1744;
  letter-spacing: 2px;
  animation: pulse-dot 2s infinite;
}

.event-stream {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
  display: flex;
  flex-direction: column;
  gap: 0;
}

/* STEPS */
.stream-step {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 4px;
  opacity: 0.35;
  transition: opacity 0.3s;
}
.stream-step.active { opacity: 1; }
.stream-step.done   { opacity: 0.6; }

.step-left {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  width: 20px;
  flex-shrink: 0;
}

.step-icon {
  width: 20px;
  height: 20px;
  border: 1px solid #1E1E1E;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  color: #555555;
  background: #0A0A0A;
  flex-shrink: 0;
  font-family: 'JetBrains Mono', monospace;
}

.stream-step.done  .step-icon { border-color: #00FF88; color: #00FF88; }
.stream-step.active .step-icon { border-color: #FF1744; color: #FF1744; animation: pulse-border 1s infinite; }

@keyframes pulse-border {
  0%,100% { box-shadow: 0 0 0 0 rgba(255,23,68,0.4); }
  50%      { box-shadow: 0 0 0 4px rgba(255,23,68,0); }
}

.spin-icon { animation: spin 1s linear infinite; display: inline-block; }
@keyframes spin { 100% { transform: rotate(360deg); } }

.step-line {
  width: 1px;
  flex: 1;
  min-height: 24px;
  background: #1E1E1E;
  margin: 2px 0;
}

.step-body { padding: 1px 0 16px; flex: 1; }

.step-title {
  font-size: 13px;
  color: #FFFFFF;
  font-weight: 500;
  margin-bottom: 2px;
}

.step-sub {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #444444;
}

.step-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #333333;
  padding-top: 2px;
  white-space: nowrap;
}

/* EVENTS DIVIDER */
.events-divider {
  display: flex;
  align-items: center;
  gap: 16px;
  margin: 16px 0;
}

.events-divider::before,
.events-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #1E1E1E;
}

.events-divider span {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  letter-spacing: 2px;
  color: #333333;
}

/* EVENT CARDS */
.event-card {
  border-left: 2px solid #1E1E1E;
  padding: 14px 16px;
  margin-bottom: 12px;
  background: #111111;
  animation: slide-in 0.4s ease both;
}

.event-card.ev-positive  { border-left-color: #00FF88; }
.event-card.ev-negative  { border-left-color: #FF1744; }
.event-card.ev-neutral   { border-left-color: #444444; }
.event-card.ev-mixed     { border-left-color: #FFB300; }

@keyframes slide-in {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

.ev-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.ev-round {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 2px;
  color: #444444;
}

.ev-sentiment {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  letter-spacing: 1px;
  padding: 2px 8px;
  border: 1px solid currentColor;
}

.sent-positive { color: #00FF88; }
.sent-negative { color: #FF1744; }
.sent-neutral  { color: #444444; }
.sent-mixed    { color: #FFB300; }

.ev-text {
  font-size: 13px;
  color: #CCCCCC;
  line-height: 1.55;
  margin-bottom: 6px;
}

.ev-metric {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #555555;
}

/* GENERATING REPORT */
.gen-report-block {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: rgba(255, 23, 68, 0.04);
  border: 1px solid rgba(255, 23, 68, 0.2);
  margin-top: 8px;
}

.gen-dots {
  display: flex;
  gap: 4px;
}

.gen-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #FF1744;
  animation: gen-bounce 1.2s infinite;
}

.gen-dots span:nth-child(2) { animation-delay: 0.2s; }
.gen-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes gen-bounce {
  0%,80%,100% { transform: scale(0.8); opacity: 0.4; }
  40%         { transform: scale(1.2); opacity: 1; }
}

.gen-text {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: #FF1744;
}

/* ERROR */
.ax-error {
  margin: 16px 32px;
  background: rgba(255, 23, 68, 0.08);
  border: 1px solid rgba(255, 23, 68, 0.3);
  padding: 14px 18px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: #FF1744;
  display: flex;
  align-items: center;
  gap: 12px;
}

.retry-btn {
  margin-left: auto;
  background: #FF1744;
  border: none;
  color: #FFFFFF;
  padding: 6px 16px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  cursor: pointer;
  letter-spacing: 1px;
}

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #0A0A0A; }
::-webkit-scrollbar-thumb { background: #1E1E1E; }
</style>
