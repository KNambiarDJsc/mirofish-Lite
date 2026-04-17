<template>
  <div class="ax-root">
    <!-- NAV -->
    <nav class="ax-nav">
      <div class="ax-logo" @click="router.push('/')">AX<span class="x-accent">◈</span>ONIC</div>
      <div class="nav-center">
        <div class="phase-track">
          <span class="phase-item done">01 DEFINITION</span>
          <span class="phase-sep">──</span>
          <span class="phase-item done">02 SIMULATION</span>
          <span class="phase-sep">──</span>
          <span class="phase-item active">03 REPORT</span>
        </div>
      </div>
      <div class="nav-actions">
        <button class="nav-btn" @click="router.push('/')">← New Campaign</button>
      </div>
    </nav>

    <!-- REPORT BODY -->
    <main class="ax-main" v-if="result">

      <!-- ── VERDICT BLOCK ──────────────────────────────────── -->
      <section class="verdict-block" :class="`verdict-${verdictKey}`">
        <div class="verdict-left">
          <div class="verdict-tag">DECISION VERDICT</div>
          <div class="verdict-headline">{{ result.report.verdict }}</div>
          <div class="verdict-reason">{{ result.report.verdict_reason }}</div>
        </div>
        <div class="verdict-right">
          <div class="confidence-ring">
            <svg viewBox="0 0 80 80" class="ring-svg">
              <circle cx="40" cy="40" r="34" class="ring-track"/>
              <circle
                cx="40" cy="40" r="34"
                class="ring-fill"
                :stroke="verdictColor"
                :stroke-dasharray="`${(result.report.confidence_score / 100) * 213.6} 213.6`"
              />
            </svg>
            <div class="ring-center">
              <span class="ring-num">{{ result.report.confidence_score }}</span>
              <span class="ring-label">%</span>
            </div>
          </div>
          <div class="ring-sub">Confidence Score</div>
        </div>
      </section>

      <!-- ── STRATEGY META ──────────────────────────────────── -->
      <section class="meta-bar">
        <div class="meta-pill" v-if="result.campaign">
          <span class="mp-key">STRATEGY</span>
          <span class="mp-val">{{ result.campaign.name }}</span>
        </div>
        <div class="meta-pill" v-if="result.campaign?.strategy_docs">
          <span class="mp-key">DOCS</span>
          <span class="mp-val">Context Provided</span>
        </div>
        <div class="meta-pill">
          <span class="mp-key">MARKET</span>
          <span class="mp-val">India (Unified)</span>
        </div>
        <div class="meta-pill">
          <span class="mp-key">REGION</span>
          <span class="mp-val">India</span>
        </div>
      </section>

      <!-- ── CONTENT GRID ───────────────────────────────────── -->
      <div class="content-grid">

        <!-- LEFT COL -->
        <div class="col-left">

          <!-- SIMULATION REPLAY -->
          <div class="report-section" v-if="result.events?.length">
            <div class="rs-header">
              <span class="rs-tag">// SIMULATION REPLAY</span>
            </div>
            <div class="event-timeline">
              <div v-for="(ev, i) in result.events" :key="i" class="tl-item" :class="`sent-${ev.sentiment}`">
                <div class="tl-round">R{{ ev.round }}</div>
                <div class="tl-body">
                  <div class="tl-event">{{ ev.event }}</div>
                  <div class="tl-metric">{{ ev.metric }}</div>
                </div>
                <div class="tl-tag" :class="`tag-${ev.sentiment}`">{{ ev.sentiment?.toUpperCase() }}</div>
              </div>
            </div>
          </div>

          <!-- RISKS -->
          <div class="report-section" v-if="result.report.risks?.length">
            <div class="rs-header">
              <span class="rs-tag">// RISK FACTORS</span>
              <span class="rs-count">{{ result.report.risks.length }}</span>
            </div>
            <div class="item-list">
              <div
                v-for="(risk, i) in result.report.risks"
                :key="'r'+i"
                class="list-item risk-item"
                :style="{ animationDelay: `${i * 0.1}s` }"
              >
                <span class="li-icon risk-icon">▲</span>
                <span class="li-text">{{ risk }}</span>
              </div>
            </div>
          </div>

        </div>

        <!-- RIGHT COL -->
        <div class="col-right">

          <!-- OPPORTUNITIES -->
          <div class="report-section" v-if="result.report.opportunities?.length">
            <div class="rs-header">
              <span class="rs-tag">// OPPORTUNITIES</span>
              <span class="rs-count opp">{{ result.report.opportunities.length }}</span>
            </div>
            <div class="item-list">
              <div
                v-for="(opp, i) in result.report.opportunities"
                :key="'o'+i"
                class="list-item opp-item"
                :style="{ animationDelay: `${i * 0.1}s` }"
              >
                <span class="li-icon opp-icon">◆</span>
                <span class="li-text">{{ opp }}</span>
              </div>
            </div>
          </div>

          <!-- RECOMMENDATIONS -->
          <div class="report-section rec-section" v-if="result.report.recommendations?.length">
            <div class="rs-header">
              <span class="rs-tag">// RECOMMENDATIONS</span>
            </div>
            <div class="rec-list">
              <div
                v-for="(rec, i) in result.report.recommendations"
                :key="'rec'+i"
                class="rec-item"
                :style="{ animationDelay: `${i * 0.12}s` }"
              >
                <span class="rec-num">0{{ i + 1 }}</span>
                <span class="rec-text">{{ rec }}</span>
              </div>
            </div>
          </div>

          <!-- INDIAN MARKET INSIGHT -->
          <div class="report-section insight-section" v-if="result.report.indian_market_insight">
            <div class="rs-header">
              <span class="rs-tag">// INDIA INSIGHT</span>
              <span class="insight-badge">🇮🇳 LOCAL INTELLIGENCE</span>
            </div>
            <div class="insight-text">{{ result.report.indian_market_insight }}</div>
          </div>

          <!-- REGIONAL BREAKDOWN (paid tier) -->
          <div class="report-section" v-if="result.report.regional_breakdown">
            <div class="rs-header">
              <span class="rs-tag">// REGIONAL BREAKDOWN</span>
              <span class="rs-count opp">PRO</span>
            </div>
            <div class="regional-grid">
              <div class="rg-item">
                <div class="rg-tier">TIER 1 CITIES</div>
                <div class="rg-detail">{{ result.report.regional_breakdown.tier1_cities }}</div>
              </div>
              <div class="rg-item">
                <div class="rg-tier">TIER 2 CITIES</div>
                <div class="rg-detail">{{ result.report.regional_breakdown.tier2_cities }}</div>
              </div>
              <div class="rg-item">
                <div class="rg-tier">TIER 3 / RURAL</div>
                <div class="rg-detail">{{ result.report.regional_breakdown.tier3_rural }}</div>
              </div>
            </div>
          </div>

          <!-- BUDGET ESTIMATE (paid tier) -->
          <div class="report-section" v-if="result.report.budget_estimate">
            <div class="rs-header">
              <span class="rs-tag">// BUDGET ESTIMATE</span>
              <span class="rs-count opp">PRO</span>
            </div>
            <div class="budget-grid">
              <div class="bg-item" v-for="(val, key) in result.report.budget_estimate" :key="key">
                <div class="bg-key">{{ budgetLabel(key) }}</div>
                <div class="bg-val">{{ val }}</div>
              </div>
            </div>
          </div>

        </div>
      </div>

      <!-- ── CTA FOOTER ──────────────────────────────────────── -->
      <footer class="ax-footer">
        <div class="footer-left">
          <span class="footer-tag">AXonic Intelligence Report</span>
          <span class="footer-meta">{{ new Date().toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' }) }}</span>
        </div>
        <div class="footer-right">
          <button class="footer-btn secondary" @click="router.push('/')">
            ← New Campaign
          </button>
          <button class="footer-btn primary" @click="downloadReport">
            Export Report ↓
          </button>
        </div>
      </footer>

    </main>

    <!-- NO DATA STATE -->
    <div v-else class="no-data">
      <div class="nd-icon">◌</div>
      <div class="nd-text">No report data found.</div>
      <button class="ax-launch-btn" @click="router.push('/')">Start New Campaign →</button>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { loadSimResult } from '../api/mvp.js'

const router = useRouter()
const result = ref(null)

const verdictKey = computed(() => {
  const v = result.value?.report?.verdict || ''
  if (v.includes('Strong')) return 'success'
  if (v.includes('Weak'))   return 'fail'
  return 'risk'
})

const verdictColor = computed(() => ({
  success: '#00FF88',
  risk:    '#FFB300',
  fail:    '#FF1744',
}[verdictKey.value]))

const budgetLabel = (key) => ({
  minimum_budget_inr: 'MIN BUDGET',
  optimal_budget_inr: 'OPTIMAL BUDGET',
  expected_cpm_inr:   'EXPECTED CPM',
  roi_estimate:       'ROI ESTIMATE',
}[key] || key.toUpperCase())

const downloadReport = () => {
  if (!result.value) return
  const content = JSON.stringify(result.value, null, 2)
  const blob    = new Blob([content], { type: 'application/json' })
  const url     = URL.createObjectURL(blob)
  const a       = document.createElement('a')
  a.href        = url
  a.download    = `axonic-report-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(() => {
  result.value = loadSimResult()
})
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
  position: sticky;
  top: 0;
  z-index: 100;
  flex-shrink: 0;
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
.phase-item      { color: #2A2A2A; }
.phase-item.done { color: #555555; }
.phase-item.active { color: #FF1744; }
.phase-sep       { color: #1E1E1E; }

.nav-actions { display: flex; gap: 12px; }

.nav-btn {
  background: transparent;
  border: 1px solid #1E1E1E;
  color: #555555;
  padding: 7px 16px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  cursor: pointer;
  letter-spacing: 1px;
  transition: all 0.2s;
}
.nav-btn:hover { border-color: #FF1744; color: #FF1744; }

/* VERDICT BLOCK */
.verdict-block {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 40px 48px;
  border-bottom: 1px solid #1E1E1E;
  position: relative;
  overflow: hidden;
}

.verdict-block::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 4px;
}

.verdict-success::before { background: #00FF88; }
.verdict-risk::before    { background: #FFB300; }
.verdict-fail::before    { background: #FF1744; }

.verdict-left {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.verdict-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 3px;
  color: #444444;
}

.verdict-headline {
  font-size: 3rem;
  font-weight: 700;
  letter-spacing: -1px;
  line-height: 1;
  opacity: 0;
  animation: fade-in 0.5s ease 0.2s forwards;
}

.verdict-success .verdict-headline { color: #00FF88; }
.verdict-risk    .verdict-headline { color: #FFB300; }
.verdict-fail    .verdict-headline { color: #FF1744; }

.verdict-reason {
  font-size: 1rem;
  color: #888888;
  max-width: 600px;
  line-height: 1.6;
  opacity: 0;
  animation: fade-in 0.5s ease 0.4s forwards;
}

@keyframes fade-in {
  to { opacity: 1; }
}

/* CONFIDENCE RING */
.verdict-right {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.confidence-ring {
  width: 100px;
  height: 100px;
  position: relative;
}

.ring-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.ring-track {
  fill: none;
  stroke: #1E1E1E;
  stroke-width: 4;
}

.ring-fill {
  fill: none;
  stroke-width: 4;
  stroke-linecap: butt;
  transition: stroke-dasharray 1s ease;
}

.ring-center {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
}

.ring-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 22px;
  font-weight: 700;
  color: #FFFFFF;
}

.ring-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: #444444;
  margin-top: 6px;
}

.ring-sub {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #333333;
  letter-spacing: 1px;
}

/* META BAR */
.meta-bar {
  display: flex;
  gap: 0;
  border-bottom: 1px solid #1E1E1E;
  overflow-x: auto;
  flex-shrink: 0;
}

.meta-pill {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 12px 24px;
  border-right: 1px solid #1E1E1E;
  white-space: nowrap;
  flex-shrink: 0;
}

.mp-key {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  letter-spacing: 1.5px;
  color: #333333;
}

.mp-val {
  font-size: 12px;
  color: #CCCCCC;
  font-weight: 500;
}

/* CONTENT GRID */
.ax-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  flex: 1;
}

.col-left  { border-right: 1px solid #1E1E1E; }

.report-section {
  padding: 32px 40px;
  border-bottom: 1px solid #1E1E1E;
  animation: fade-in 0.5s ease both;
}

.rs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.rs-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 2px;
  color: #444444;
}

.rs-count {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #FF1744;
  border: 1px solid #FF1744;
  padding: 2px 8px;
}
.rs-count.opp { color: #00FF88; border-color: #00FF88; }

/* EVENT TIMELINE */
.event-timeline {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tl-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: #111111;
}

.tl-round {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #444444;
  padding: 3px 8px;
  border: 1px solid #1E1E1E;
  white-space: nowrap;
}

.tl-body { flex: 1; }

.tl-event {
  font-size: 13px;
  color: #CCCCCC;
  line-height: 1.5;
  margin-bottom: 4px;
}

.tl-metric {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #444444;
}

.tl-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  padding: 3px 8px;
  border: 1px solid currentColor;
  white-space: nowrap;
}

.tag-positive { color: #00FF88; }
.tag-negative { color: #FF1744; }
.tag-neutral  { color: #444444; }
.tag-mixed    { color: #FFB300; }

/* LISTS */
.item-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.list-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  animation: slide-up 0.4s ease both;
}

@keyframes slide-up {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.risk-item { background: rgba(255, 23, 68, 0.04); border-left: 2px solid #FF1744; }
.opp-item  { background: rgba(0, 255, 136, 0.04); border-left: 2px solid #00FF88; }

.li-icon { font-size: 10px; margin-top: 3px; flex-shrink: 0; }
.risk-icon { color: #FF1744; }
.opp-icon  { color: #00FF88; }

.li-text { font-size: 13px; color: #CCCCCC; line-height: 1.55; }

/* RECOMMENDATIONS */
.rec-list { display: flex; flex-direction: column; gap: 12px; }

.rec-item {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  background: #111111;
  border: 1px solid #1E1E1E;
  animation: slide-up 0.4s ease both;
  transition: border-color 0.2s;
}
.rec-item:hover { border-color: #FF1744; }

.rec-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 18px;
  font-weight: 700;
  color: #FF1744;
  min-width: 28px;
  opacity: 0.5;
}

.rec-text {
  font-size: 13px;
  color: #CCCCCC;
  line-height: 1.6;
}

/* INSIGHT */
.insight-section { background: rgba(0, 229, 255, 0.02); }

.insight-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  letter-spacing: 1px;
  color: #00E5FF;
  border: 1px solid rgba(0, 229, 255, 0.3);
  padding: 2px 8px;
}

.insight-text {
  font-size: 14px;
  color: #AAAAAA;
  line-height: 1.7;
  border-left: 2px solid #00E5FF;
  padding-left: 16px;
}

/* REGIONAL */
.regional-grid { display: flex; flex-direction: column; gap: 12px; }

.rg-item {
  padding: 12px 16px;
  background: #111111;
  border-left: 2px solid #FFB300;
}

.rg-tier {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  letter-spacing: 2px;
  color: #FFB300;
  margin-bottom: 6px;
}

.rg-detail { font-size: 12px; color: #888888; line-height: 1.5; }

/* BUDGET */
.budget-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

.bg-item {
  background: #111111;
  padding: 14px 16px;
  border-left: 2px solid #444444;
}

.bg-key {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  letter-spacing: 1px;
  color: #444444;
  margin-bottom: 6px;
}

.bg-val { font-size: 13px; color: #CCCCCC; font-weight: 600; }

/* FOOTER */
.ax-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 48px;
  border-top: 1px solid #1E1E1E;
  background: #0A0A0A;
  flex-shrink: 0;
}

.footer-left { display: flex; align-items: center; gap: 20px; }

.footer-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #FF1744;
  letter-spacing: 1px;
}

.footer-meta {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #333333;
}

.footer-right { display: flex; gap: 12px; }

.footer-btn {
  padding: 10px 24px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 1px;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.footer-btn.secondary {
  background: transparent;
  border: 1px solid #1E1E1E;
  color: #555555;
}
.footer-btn.secondary:hover { border-color: #FF1744; color: #FF1744; }

.footer-btn.primary {
  background: #FF1744;
  color: #FFFFFF;
}
.footer-btn.primary:hover { background: #FF4569; }

/* NO DATA */
.no-data {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
}

.nd-icon {
  font-size: 48px;
  color: #1E1E1E;
  animation: spin 3s linear infinite;
}
@keyframes spin { 100% { transform: rotate(360deg); } }

.nd-text {
  font-family: 'JetBrains Mono', monospace;
  color: #333333;
  font-size: 13px;
}

.ax-launch-btn {
  background: #FF1744;
  border: none;
  color: #FFFFFF;
  padding: 14px 28px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  letter-spacing: 2px;
  cursor: pointer;
}

::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #0A0A0A; }
::-webkit-scrollbar-thumb { background: #1E1E1E; }
</style>
