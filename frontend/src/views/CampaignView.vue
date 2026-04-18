<template>
  <div class="cv-root">
    <!-- Gradient Background -->
    <div class="cv-bg"></div>

    <!-- NAV -->
    <nav class="cv-nav">
      <div class="cv-logo" @click="$router.push('/')">AX<span class="logo-dot">◈</span>ONIC</div>
      <div class="cv-nav-right">
        <div class="credit-badge">
          <span class="credit-dot"></span>
          {{ creditsDisplay }} credits
        </div>
        <a href="https://razorpay.com" class="topup-link" target="_blank">Top up ↗</a>
        <UserButton after-sign-out-url="/" />
      </div>
    </nav>

    <!-- MAIN CONTENT -->
    <main class="cv-main">
      <div class="cv-card" :class="{ 'card-ready': ready }">

        <!-- Header -->
        <div class="cv-header">
          <h1 class="cv-title">Simulate your strategy</h1>
          <p class="cv-subtitle">
            Upload your strategies and add a prompt then click generate report to<br>
            get your detailed report.
          </p>
        </div>

        <form @submit.prevent="launch" class="cv-form">

          <!-- Upload Zone -->
          <div class="form-field">
            <label class="field-label">Upload your files</label>
            <div
              class="upload-zone"
              :class="{ 'dz-hover': isDragOver, 'dz-filled': files.length > 0 }"
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
                class="file-input-hidden"
                @change="handleSelect"
              />

              <!-- Empty state -->
              <div v-if="files.length === 0" class="dz-empty">
                <div class="dz-icon">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14,2 14,8 20,8"/>
                    <line x1="12" y1="18" x2="12" y2="12"/>
                    <line x1="9" y1="15" x2="15" y2="15"/>
                  </svg>
                </div>
                <div class="dz-text">Drop file here or click to upload</div>
                <div class="dz-sub">TXT, PDF Supported</div>
              </div>

              <!-- Files list -->
              <div v-else class="dz-files">
                <div v-for="(f, i) in files" :key="i" class="dz-file-row">
                  <span class="dfr-icon">📄</span>
                  <span class="dfr-name">{{ f.name }}</span>
                  <span class="dfr-size">{{ (f.size / 1024).toFixed(1) }} KB</span>
                  <button type="button" class="dfr-remove" @click.stop="removeFile(i)">×</button>
                </div>
                <div class="dz-add">+ Add more files</div>
              </div>
            </div>
          </div>

          <!-- Prompt -->
          <div class="form-field">
            <label class="field-label">Enter your prompt</label>
            <textarea
              v-model="form.prompt"
              class="cv-textarea"
              placeholder="Simulate this strategy for the summer season."
              rows="5"
              required
            ></textarea>
          </div>

          <!-- Error -->
          <div v-if="error" class="cv-error">⚠ {{ error }}</div>

          <!-- Submit -->
          <div class="cv-submit-row">
            <button
              type="submit"
              class="cv-submit-btn"
              :class="{ 'btn-loading': submitting }"
              :disabled="!canSubmit || submitting"
            >
              <span v-if="!submitting">Generate your Report</span>
              <span v-else class="btn-spinner-wrap">
                <span class="btn-spinner"></span>
                Initializing engine...
              </span>
            </button>
          </div>

        </form>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { saveCampaign, getBalance, getUserId } from '../api/mvp.js'
import { UserButton } from '@clerk/vue'

const router     = useRouter()
const fileInput  = ref(null)
const isDragOver = ref(false)
const files      = ref([])
const ready      = ref(false)
const form       = ref({ prompt: '' })
const submitting = ref(false)
const error      = ref('')
const creditsDisplay = ref('—')

const canSubmit = computed(() => form.value.prompt.trim().length > 10)

const triggerFile = () => fileInput.value?.click()

const handleSelect = (e) => addFiles(Array.from(e.target.files))
const handleDrop   = (e) => { isDragOver.value = false; addFiles(Array.from(e.dataTransfer.files)) }

const addFiles = (newFiles) => {
  const allowed = ['.pdf', '.txt', '.md']
  files.value.push(...newFiles.filter(f => allowed.includes(f.name.slice(f.name.lastIndexOf('.')).toLowerCase())))
}
const removeFile = (i) => files.value.splice(i, 1)

const readFile = (file) => new Promise(resolve => {
  if (file.type === 'application/pdf') return resolve(`[FILE: ${file.name}]`)
  const r = new FileReader()
  r.onload = e => resolve(e.target.result)
  r.readAsText(file)
})

onMounted(async () => {
  getUserId()
  try {
    const res = await getBalance()
    creditsDisplay.value = res.credits_display ?? '3.0'
  } catch { creditsDisplay.value = '3.0' }
  setTimeout(() => { ready.value = true }, 80)
})

async function launch() {
  if (!canSubmit.value || submitting.value) return
  error.value = ''
  submitting.value = true
  try {
    const contents = await Promise.all(files.value.map(readFile))
    const name = form.value.prompt.substring(0, 40) + (form.value.prompt.length > 40 ? '...' : '')
    saveCampaign({
      ...form.value,
      name,
      strategy_docs: contents.join('\n\n---\n\n'),
      platform: 'Digital',
      tone: 'Variable',
      goal: 'Simulation',
    })
    router.push({ name: 'Run' })
  } catch (e) {
    error.value = e.message || 'Failed to start. Please try again.'
    submitting.value = false
  }
}
</script>

<style scoped>
/* ── Root & Background ─────────────────────────────────────── */
.cv-root {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
  font-family: 'Inter', system-ui, sans-serif;
  overflow: hidden;
}

.cv-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  background:
    radial-gradient(ellipse at 0% 40%,  rgba(232,121,58,0.22) 0%, transparent 55%),
    radial-gradient(ellipse at 100% 60%, rgba(255,200,120,0.18) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 100%, rgba(232,121,58,0.12) 0%, transparent 50%),
    #FDF6EC;
  animation: bg-shift 20s ease-in-out infinite alternate;
}
@keyframes bg-shift {
  0%   { background-position: 0% 40%, 100% 60%, 50% 100%; }
  100% { background-position: 5% 45%, 95% 55%, 45% 95%;  }
}

/* ── NAV ──────────────────────────────────────────────────── */
.cv-nav {
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
.cv-logo {
  font-weight: 800;
  font-size: 15px;
  letter-spacing: 3px;
  color: #3D1E0F;
  cursor: pointer;
  user-select: none;
}
.logo-dot { color: #E8793A; font-size: 12px; margin: 0 2px; }
.cv-nav-right { display: flex; align-items: center; gap: 16px; }
.credit-badge {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: #8A6A50;
  background: rgba(255,255,255,0.7);
  border: 1px solid rgba(61,30,15,0.1);
  padding: 5px 14px;
  border-radius: 20px;
}
.credit-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #E8793A;
  animation: dot-pulse 2s infinite;
}
@keyframes dot-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }
.topup-link {
  font-size: 12px;
  color: #E8793A;
  text-decoration: none;
  font-weight: 600;
  transition: opacity 0.2s;
}
.topup-link:hover { opacity: 0.7; }

/* ── MAIN ─────────────────────────────────────────────────── */
.cv-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 24px 64px;
  position: relative;
  z-index: 2;
}

/* ── CARD ─────────────────────────────────────────────────── */
.cv-card {
  width: 100%;
  max-width: 580px;
  opacity: 0;
  transform: translateY(24px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}
.cv-card.card-ready { opacity: 1; transform: none; }

/* ── HEADER ───────────────────────────────────────────────── */
.cv-header { text-align: center; margin-bottom: 36px; }
.cv-title {
  font-size: clamp(2rem, 4vw, 2.8rem);
  font-weight: 700;
  color: #2D1A0A;
  letter-spacing: -1px;
  line-height: 1.1;
  margin: 0 0 14px;
  font-family: 'Georgia', 'Times New Roman', serif;
}
.cv-subtitle {
  font-size: 0.9rem;
  color: #8A6A50;
  line-height: 1.7;
  margin: 0;
}

/* ── FORM ─────────────────────────────────────────────────── */
.cv-form { display: flex; flex-direction: column; gap: 20px; }

.form-field { display: flex; flex-direction: column; gap: 10px; }
.field-label {
  font-size: 13px;
  font-weight: 600;
  color: #3D1E0F;
}

/* UPLOAD ZONE */
.upload-zone {
  background: #FFFFFF;
  border: 1.5px dashed rgba(61,30,15,0.2);
  border-radius: 16px;
  min-height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: border-color 0.25s, background 0.25s, transform 0.15s;
  padding: 20px;
}
.upload-zone:hover { border-color: #E8793A; background: rgba(232,121,58,0.03); }
.upload-zone.dz-hover {
  border-color: #E8793A;
  background: rgba(232,121,58,0.06);
  transform: scale(1.01);
}
.upload-zone.dz-filled { border-style: solid; border-color: rgba(61,30,15,0.15); align-items: flex-start; }

.file-input-hidden { display: none; }

.dz-empty { text-align: center; }
.dz-icon { color: #C4A882; margin-bottom: 10px; display: flex; justify-content: center; }
.dz-text { font-size: 14px; font-weight: 600; color: #5A3E28; margin-bottom: 4px; }
.dz-sub  { font-size: 12px; color: #C4A882; }

.dz-files { width: 100%; display: flex; flex-direction: column; gap: 8px; }
.dz-file-row {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #FDF6EC;
  border: 1px solid rgba(61,30,15,0.08);
  border-radius: 10px;
  padding: 10px 14px;
  animation: row-in 0.25s ease both;
}
@keyframes row-in { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
.dfr-icon { font-size: 14px; }
.dfr-name { flex: 1; font-size: 13px; color: #3D1E0F; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dfr-size { font-size: 11px; color: #BBA890; font-family: monospace; }
.dfr-remove { background: none; border: none; color: #BBA890; font-size: 18px; cursor: pointer; padding: 0; line-height: 1; transition: color 0.2s; }
.dfr-remove:hover { color: #c0392b; }
.dz-add { font-size: 12px; color: #E8793A; text-align: center; padding-top: 4px; cursor: pointer; }

/* TEXTAREA */
.cv-textarea {
  background: #FFFFFF;
  border: 1.5px solid rgba(61,30,15,0.12);
  border-radius: 16px;
  padding: 18px 20px;
  font-size: 14px;
  color: #2D1A0A;
  font-family: 'Inter', system-ui, sans-serif;
  line-height: 1.65;
  outline: none;
  resize: none;
  width: 100%;
  box-sizing: border-box;
  transition: border-color 0.25s, box-shadow 0.25s;
  italic-like: italic;
}
.cv-textarea::placeholder { color: #C4A882; font-style: italic; }
.cv-textarea:focus {
  border-color: #E8793A;
  box-shadow: 0 0 0 4px rgba(232,121,58,0.1);
}

/* ERROR */
.cv-error {
  background: rgba(192,57,43,0.08);
  border: 1px solid rgba(192,57,43,0.25);
  border-radius: 10px;
  padding: 12px 16px;
  font-size: 13px;
  color: #c0392b;
}

/* SUBMIT */
.cv-submit-row { display: flex; justify-content: center; padding-top: 8px; }
.cv-submit-btn {
  background: #E8793A;
  border: none;
  color: #FFFFFF;
  font-size: 15px;
  font-weight: 700;
  padding: 16px 40px;
  border-radius: 50px;
  cursor: pointer;
  transition: background 0.2s, transform 0.15s, box-shadow 0.2s;
  min-width: 220px;
}
.cv-submit-btn:hover:not(:disabled) {
  background: #d4622a;
  transform: translateY(-2px);
  box-shadow: 0 6px 24px rgba(232,121,58,0.35);
}
.cv-submit-btn:active:not(:disabled) { transform: scale(0.97); }
.cv-submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.cv-submit-btn.btn-loading { opacity: 1; }

.btn-spinner-wrap { display: flex; align-items: center; gap: 10px; }
.btn-spinner {
  width: 16px; height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { 100% { transform: rotate(360deg); } }
</style>
