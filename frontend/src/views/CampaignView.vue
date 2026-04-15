<template>
  <div class="ax-root">
    <!-- ── NAV ───────────────────────────────────────────────── -->
    <nav class="ax-nav">
      <div class="ax-logo">AX<span class="x-accent">◈</span>ONIC</div>
      <div class="ax-nav-right">
        <div class="credit-pill">
          <span class="credit-dot"></span>
          <span class="credit-label">{{ creditsDisplay }} credits</span>
        </div>
        <a href="https://razorpay.com" class="buy-link" target="_blank">Top up ↗</a>
      </div>
    </nav>

    <!-- ── MAIN ──────────────────────────────────────────────── -->
    <main class="ax-main">

      <!-- LEFT: Context -->
      <aside class="ax-sidebar">
        <div class="sidebar-tag">DECISION ENGINE v1.0</div>
        <h1 class="sidebar-headline">Will this<br>campaign<br><span class="headline-red">work?</span></h1>
        <p class="sidebar-sub">
          Define your campaign. AXonic simulates how the Indian market
          will react — before you spend a single rupee.
        </p>

        <div class="sidebar-metrics">
          <div class="sm-row">
            <span class="sm-key">Models</span>
            <span class="sm-val">Llama 3.3 · Gemini 2.5</span>
          </div>
          <div class="sm-row">
            <span class="sm-key">Market</span>
            <span class="sm-val">India — Tier 1 / 2 / 3</span>
          </div>
          <div class="sm-row">
            <span class="sm-key">Output</span>
            <span class="sm-val">Executive Brief</span>
          </div>
          <div class="sm-row">
            <span class="sm-key">Cost</span>
            <span class="sm-val">0.5 credits / run</span>
          </div>
        </div>

        <div class="step-track">
          <div class="st-item active"><span class="st-n">01</span><span class="st-label">Campaign Definition</span></div>
          <div class="st-item"><span class="st-n">02</span><span class="st-label">Simulation</span></div>
          <div class="st-item"><span class="st-n">03</span><span class="st-label">Decision Report</span></div>
        </div>
      </aside>

      <!-- RIGHT: Form -->
      <section class="ax-form-panel">
        <div class="form-header">
          <span class="form-tag">// CAMPAIGN DEFINITION</span>
          <span class="form-step">STEP 01 / 03</span>
        </div>

        <form @submit.prevent="launch" class="ax-form">

          <!-- Campaign Name -->
          <div class="field-block">
            <label class="field-label">CAMPAIGN NAME <span class="req">*</span></label>
            <input
              v-model="form.name"
              class="ax-input"
              placeholder="e.g. Diwali Collection 2026"
              maxlength="80"
              required
            />
          </div>

          <!-- Description -->
          <div class="field-block">
            <label class="field-label">CAMPAIGN BRIEF <span class="req">*</span></label>
            <textarea
              v-model="form.description"
              class="ax-input ax-textarea"
              placeholder="What is this campaign about? What message are you sending? (2-3 sentences)"
              rows="3"
              required
            ></textarea>
          </div>

          <!-- Row: Platform + Tone -->
          <div class="field-row">
            <div class="field-block">
              <label class="field-label">PLATFORM <span class="req">*</span></label>
              <div class="ax-select-wrap">
                <select v-model="form.platform" class="ax-select" required>
                  <option value="">Select platform</option>
                  <option value="Instagram">Instagram</option>
                  <option value="Twitter">Twitter / X</option>
                  <option value="YouTube">YouTube</option>
                  <option value="LinkedIn">LinkedIn</option>
                  <option value="WhatsApp">WhatsApp</option>
                </select>
                <span class="select-arrow">▾</span>
              </div>
            </div>

            <div class="field-block">
              <label class="field-label">CAMPAIGN TONE <span class="req">*</span></label>
              <div class="ax-select-wrap">
                <select v-model="form.tone" class="ax-select" required>
                  <option value="">Select tone</option>
                  <option value="Inspirational">Inspirational</option>
                  <option value="Emotional">Emotional</option>
                  <option value="Informational">Informational</option>
                  <option value="Humorous">Humorous</option>
                  <option value="Aggressive">Aggressive / Direct</option>
                </select>
                <span class="select-arrow">▾</span>
              </div>
            </div>
          </div>

          <!-- Audience -->
          <div class="field-block">
            <label class="field-label">TARGET AUDIENCE <span class="req">*</span></label>
            <input
              v-model="form.audience"
              class="ax-input"
              placeholder="e.g. Urban women 22–35, Tier 1 cities, SEC A-B"
              required
            />
            <div class="field-hint">Be specific. The more precise, the more accurate the simulation.</div>
          </div>

          <!-- Goal -->
          <div class="field-block">
            <label class="field-label">PRIMARY GOAL</label>
            <div class="goal-chips">
              <button
                v-for="g in goals"
                :key="g"
                type="button"
                class="goal-chip"
                :class="{ active: form.goal === g }"
                @click="form.goal = g"
              >{{ g }}</button>
            </div>
          </div>

          <!-- Budget Context -->
          <div class="field-block">
            <label class="field-label">BUDGET RANGE (OPTIONAL)</label>
            <div class="ax-select-wrap">
              <select v-model="form.budget" class="ax-select">
                <option value="">Not specified</option>
                <option value="Under ₹50K">Under ₹50,000</option>
                <option value="₹50K–₹2L">₹50,000 – ₹2,00,000</option>
                <option value="₹2L–₹10L">₹2,00,000 – ₹10,00,000</option>
                <option value="₹10L+">₹10,00,000+</option>
              </select>
              <span class="select-arrow">▾</span>
            </div>
          </div>

          <!-- Error -->
          <div v-if="error" class="ax-error">
            <span class="error-icon">⚠</span> {{ error }}
          </div>

          <!-- Submit -->
          <button
            type="submit"
            class="ax-launch-btn"
            :disabled="!canSubmit || submitting"
          >
            <span v-if="!submitting">
              RUN SIMULATION
              <span class="btn-arrow">→</span>
            </span>
            <span v-else class="btn-loading">
              <span class="pulse-dot"></span>
              Initializing engine...
            </span>
          </button>

          <div class="launch-meta">
            Uses 0.5 credits · {{ creditsDisplay }} credits remaining
          </div>

        </form>
      </section>

    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { saveCampaign, getBalance, getUserId } from '../api/mvp.js'

const router = useRouter()

const form = ref({
  name:        '',
  description: '',
  platform:    '',
  tone:        '',
  audience:    '',
  goal:        'Brand Awareness',
  budget:      '',
})

const goals      = ['Brand Awareness', 'Lead Generation', 'Sales / Conversions', 'App Downloads', 'Community Growth']
const submitting = ref(false)
const error      = ref('')
const creditsDisplay = ref('—')

const canSubmit = computed(() =>
  form.value.name.trim() &&
  form.value.description.trim() &&
  form.value.platform &&
  form.value.tone &&
  form.value.audience.trim()
)

onMounted(async () => {
  // Ensure user ID exists
  getUserId()
  try {
    const res = await getBalance()
    creditsDisplay.value = res.credits_display ?? '3.0'
  } catch {
    creditsDisplay.value = '3.0'
  }
})

async function launch() {
  if (!canSubmit.value || submitting.value) return
  error.value   = ''
  submitting.value = true

  try {
    saveCampaign({ ...form.value })
    router.push({ name: 'Run' })
  } catch (e) {
    error.value = e.message || 'Failed to start. Please try again.'
    submitting.value = false
  }
}
</script>

<style scoped>
/* ── Design tokens ─────────────────────────────────────────── */
:root {
  --bg:       #0A0A0A;
  --surface:  #111111;
  --border:   #1E1E1E;
  --red:      #FF1744;
  --cyan:     #00E5FF;
  --text:     #FFFFFF;
  --muted:    #555555;
  --faint:    #2A2A2A;
  --mono:     'JetBrains Mono', monospace;
  --sans:     'Space Grotesk', system-ui, sans-serif;
}

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
}

.ax-logo {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 800;
  font-size: 18px;
  letter-spacing: 3px;
  color: #FF1744;
}

.x-accent {
  color: #00E5FF;
  font-size: 14px;
  margin: 0 1px;
}

.ax-nav-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.credit-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #111111;
  border: 1px solid #1E1E1E;
  padding: 6px 14px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: #888888;
}

.credit-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #00E5FF;
  animation: pulse-dot 2s infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.buy-link {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #FF1744;
  text-decoration: none;
  letter-spacing: 1px;
  transition: opacity 0.2s;
}
.buy-link:hover { opacity: 0.7; }

/* MAIN LAYOUT */
.ax-main {
  flex: 1;
  display: flex;
  max-width: 1280px;
  margin: 0 auto;
  width: 100%;
  padding: 0;
}

/* SIDEBAR */
.ax-sidebar {
  width: 340px;
  min-width: 320px;
  padding: 48px 40px;
  border-right: 1px solid #1E1E1E;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.sidebar-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 2px;
  color: #FF1744;
  padding: 4px 8px;
  border: 1px solid #FF1744;
  display: inline-block;
  width: fit-content;
}

.sidebar-headline {
  font-size: 3.6rem;
  font-weight: 700;
  line-height: 1.05;
  margin: 0;
  letter-spacing: -2px;
  color: #FFFFFF;
}

.headline-red {
  color: #FF1744;
}

.sidebar-sub {
  font-size: 0.9rem;
  line-height: 1.7;
  color: #555555;
  margin: 0;
}

.sidebar-metrics {
  display: flex;
  flex-direction: column;
  gap: 0;
  border: 1px solid #1E1E1E;
}

.sm-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  border-bottom: 1px solid #1E1E1E;
  font-size: 12px;
}
.sm-row:last-child { border-bottom: none; }

.sm-key {
  font-family: 'JetBrains Mono', monospace;
  color: #444444;
  letter-spacing: 0.5px;
}

.sm-val {
  color: #CCCCCC;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
}

.step-track {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: auto;
}

.st-item {
  display: flex;
  align-items: center;
  gap: 12px;
  opacity: 0.3;
}
.st-item.active { opacity: 1; }

.st-n {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #FF1744;
  font-weight: 700;
}

.st-label {
  font-size: 13px;
  color: #CCCCCC;
  font-weight: 500;
}

/* FORM PANEL */
.ax-form-panel {
  flex: 1;
  padding: 48px 56px;
  overflow-y: auto;
}

.form-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 40px;
  padding-bottom: 16px;
  border-bottom: 1px solid #1E1E1E;
}

.form-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: #444444;
  letter-spacing: 1px;
}

.form-step {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #FF1744;
  letter-spacing: 2px;
}

.ax-form {
  display: flex;
  flex-direction: column;
  gap: 28px;
  max-width: 640px;
}

.field-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.field-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 2px;
  color: #555555;
}

.req { color: #FF1744; }

.ax-input {
  background: #111111;
  border: 1px solid #1E1E1E;
  color: #FFFFFF;
  padding: 14px 16px;
  font-family: 'Space Grotesk', system-ui, sans-serif;
  font-size: 14px;
  outline: none;
  border-radius: 0;
  transition: border-color 0.2s;
  width: 100%;
  box-sizing: border-box;
}

.ax-input:focus {
  border-color: #FF1744;
}

.ax-input::placeholder { color: #333333; }

.ax-textarea {
  resize: vertical;
  min-height: 80px;
}

.ax-select-wrap {
  position: relative;
}

.ax-select {
  width: 100%;
  background: #111111;
  border: 1px solid #1E1E1E;
  color: #FFFFFF;
  padding: 14px 40px 14px 16px;
  font-family: 'Space Grotesk', system-ui, sans-serif;
  font-size: 14px;
  outline: none;
  border-radius: 0;
  appearance: none;
  cursor: pointer;
  transition: border-color 0.2s;
}

.ax-select:focus { border-color: #FF1744; }
.ax-select option { background: #111111; }

.select-arrow {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: #444444;
  pointer-events: none;
  font-size: 12px;
}

.field-hint {
  font-size: 11px;
  color: #333333;
  font-family: 'JetBrains Mono', monospace;
}

/* GOAL CHIPS */
.goal-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.goal-chip {
  background: transparent;
  border: 1px solid #1E1E1E;
  color: #555555;
  padding: 8px 16px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.5px;
  cursor: pointer;
  border-radius: 0;
  transition: all 0.15s;
}

.goal-chip:hover {
  border-color: #FF1744;
  color: #FF1744;
}

.goal-chip.active {
  background: #FF1744;
  border-color: #FF1744;
  color: #FFFFFF;
}

/* ERROR */
.ax-error {
  background: rgba(255, 23, 68, 0.08);
  border: 1px solid #FF1744;
  padding: 12px 16px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: #FF1744;
  display: flex;
  align-items: center;
  gap: 10px;
}

/* LAUNCH BUTTON */
.ax-launch-btn {
  background: #FF1744;
  border: none;
  color: #FFFFFF;
  padding: 18px 32px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 2px;
  cursor: pointer;
  border-radius: 0;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  width: 100%;
  margin-top: 8px;
}

.ax-launch-btn:hover:not(:disabled) {
  background: #FF4569;
  transform: translateY(-1px);
}

.ax-launch-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
  transform: none;
}

.btn-arrow {
  font-size: 16px;
  transition: transform 0.2s;
}

.ax-launch-btn:hover .btn-arrow { transform: translateX(4px); }

.btn-loading {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #FFFFFF;
  animation: pulse-dot 0.8s infinite;
}

.launch-meta {
  text-align: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #333333;
  letter-spacing: 1px;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #0A0A0A; }
::-webkit-scrollbar-thumb { background: #1E1E1E; }
</style>
