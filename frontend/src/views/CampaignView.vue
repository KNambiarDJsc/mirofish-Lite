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
        <div class="sidebar-tag">DECISION ENGINE v1.1</div>
        <h1 class="sidebar-headline">Simulate<br>your<br><span class="headline-red">strategy.</span></h1>
        <p class="sidebar-sub">
          Stop guessing. Paste your strategy documents and run a simulation 
          to see how the Indian market will realistically react.
        </p>


        <div class="step-track">
          <div class="st-item active"><span class="st-n">01</span><span class="st-label">Strategy Definition</span></div>
          <div class="st-item"><span class="st-n">02</span><span class="st-label">Simulation</span></div>
          <div class="st-item"><span class="st-n">03</span><span class="st-label">Decision Report</span></div>
        </div>
      </aside>

      <!-- RIGHT: Form -->
      <section class="ax-form-panel">
        <div class="form-header">
          <span class="form-tag">// STRATEGY SIMULATION</span>
          <span class="form-step">STEP 01 / 03</span>
        </div>

        <form @submit.prevent="launch" class="ax-form">

          <!-- Upload Strategy Section -->
          <div class="field-block">
            <label class="field-label">
              STRATEGY DOCUMENTS / CONTEXT
              <span class="label-opt">(PDF, TXT, MD)</span>
            </label>
            
            <div 
              class="upload-zone"
              :class="{ 'drag-over': isDragOver, 'has-files': files.length > 0 }"
              @dragover.prevent="isDragOver = true"
              @dragleave.prevent="isDragOver = false"
              @drop.prevent="handleDrop"
              @click="triggerFile"
            >
              <input 
                ref="fileInput"
                type="file" 
                multiple 
                accept=".pdf,.txt,.md" 
                class="hidden-input"
                @change="handleSelect"
              />
              
              <div v-if="files.length === 0" class="upload-inner">
                <div class="upload-icon">↑</div>
                <div class="upload-text">Drag & Drop strategy files here</div>
                <div class="upload-sub">or click to browse from local storage</div>
              </div>
              
              <div v-else class="file-list">
                <div v-for="(f, i) in files" :key="i" class="file-item">
                  <span class="file-icon">📄</span>
                  <span class="file-name">{{ f.name }}</span>
                  <span class="file-size">{{ (f.size / 1024).toFixed(1) }} KB</span>
                  <button type="button" class="remove-file" @click.stop="removeFile(i)">×</button>
                </div>
                <div class="add-more">+ Add more documents</div>
              </div>
            </div>
            <div class="field-hint">Upload brand guidelines, product details, or research to ground the model.</div>
          </div>

          <!-- Simulation Prompt -->
          <div class="field-block">
            <label class="field-label">SIMULATION PROMPT <span class="req">*</span></label>
            <textarea
              v-model="form.prompt"
              class="ax-input ax-textarea"
              placeholder="What do you want to test? e.g. 'Launch of a premium organic tea brand targeting Gen Z in Bangalore via Instagram Reels with a humorous tone.'"
              rows="4"
              required
            ></textarea>
            <div class="field-hint">Describe the specific campaign or move you want to simulate.</div>
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
const fileInput = ref(null)
const isDragOver = ref(false)
const files = ref([])

const form = ref({
  prompt:        '',
})

const submitting = ref(false)
const error      = ref('')
const creditsDisplay = ref('—')

const canSubmit = computed(() =>
  form.value.prompt.trim().length > 10
)

const triggerFile = () => fileInput.value?.click()

const handleSelect = (e) => {
  const newFiles = Array.from(e.target.files)
  addFiles(newFiles)
}

const handleDrop = (e) => {
  isDragOver.value = false
  const newFiles = Array.from(e.dataTransfer.files)
  addFiles(newFiles)
}

const addFiles = (newFiles) => {
  const allowed = ['.pdf', '.txt', '.md']
  const filtered = newFiles.filter(f => {
    const ext = f.name.substring(f.name.lastIndexOf('.')).toLowerCase()
    return allowed.includes(ext)
  })
  files.value.push(...filtered)
}

const removeFile = (i) => files.value.splice(i, 1)

// Helper to read file as text
const readFile = (file) => {
  return new Promise((resolve) => {
    if (file.type === 'application/pdf') {
      // Basic placeholder for PDF as we don't have a parser library in browser here
      resolve(`[FILE: ${file.name} - ${file.size} bytes]`)
    } else {
      const reader = new FileReader()
      reader.onload = (e) => resolve(e.target.result)
      reader.readAsText(file)
    }
  })
}

onMounted(async () => {
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
    // Read all files context
    const fileContents = await Promise.all(files.value.map(f => readFile(f)))
    const strategyContext = fileContents.join('\n\n---\n\n')

    const name = form.value.prompt.substring(0, 40) + (form.value.prompt.length > 40 ? '...' : '')
    saveCampaign({ 
      ...form.value,
      name: name,
      strategy_docs: strategyContext,
      platform: 'Digital',
      tone: 'Variable',
      goal: 'Simulation'
    })
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
  font-size: 3.2rem;
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
  gap: 32px;
  max-width: 680px;
}

.field-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.field-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 2px;
  color: #555555;
  display: flex;
  align-items: center;
  gap: 8px;
}

.label-opt {
  color: #2A2A2A;
  font-weight: 400;
}

.req { color: #FF1744; }

/* UPLOAD ZONE */
.upload-zone {
  background: #0D0D0D;
  border: 1px dashed #1E1E1E;
  min-height: 140px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.23, 1, 0.32, 1);
  position: relative;
}

.upload-zone:hover {
  border-color: #FF1744;
  background: #111111;
  box-shadow: 0 0 40px rgba(255,23,68,0.03);
}

.upload-zone.drag-over {
  border-color: #00E5FF;
  background: rgba(0, 229, 255, 0.05);
  transform: scale(1.01);
}

.hidden-input { display: none; }

.upload-inner {
  text-align: center;
}

.upload-icon {
  font-size: 24px;
  color: #1E1E1E;
  margin-bottom: 12px;
  transition: color 0.2s;
}
.upload-zone:hover .upload-icon { color: #FF1744; }

.upload-text {
  font-size: 14px;
  color: #888888;
  font-weight: 500;
  margin-bottom: 4px;
}

.upload-sub {
  font-family: var(--font-mono);
  font-size: 10px;
  color: #333333;
  letter-spacing: 0.5px;
}

.file-list {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  background: #111111;
  border: 1px solid #1E1E1E;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  gap: 12px;
  animation: slide-in 0.3s ease both;
}

@keyframes slide-in {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.file-icon { font-size: 12px; opacity: 0.5; }
.file-name { font-size: 13px; color: #CCCCCC; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.file-size { font-family: var(--font-mono); font-size: 10px; color: #333333; }

.remove-file {
  background: none;
  border: none;
  color: #333333;
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
}
.remove-file:hover { color: #FF1744; }

.add-more {
  font-family: var(--font-mono);
  font-size: 10px;
  color: #555555;
  text-align: center;
  padding-top: 8px;
  letter-spacing: 1px;
}

.ax-input {
  background: #111111;
  border: 1px solid #1E1E1E;
  color: #FFFFFF;
  padding: 16px;
  font-family: 'Space Grotesk', system-ui, sans-serif;
  font-size: 15px;
  outline: none;
  border-radius: 0;
  transition: all 0.2s;
  width: 100%;
  box-sizing: border-box;
  line-height: 1.6;
}

.ax-input:focus {
  border-color: #FF1744;
  background: #141414;
  box-shadow: 0 0 20px rgba(255,23,68,0.05);
}

.ax-input::placeholder { color: #333333; }

.ax-textarea {
  resize: vertical;
  min-height: 120px;
}

.field-hint {
  font-size: 11px;
  color: #333333;
  font-family: 'JetBrains Mono', monospace;
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
  padding: 20px 32px;
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
  box-shadow: 0 10px 30px rgba(255,23,68,0.2);
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
