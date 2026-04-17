<template>
  <div class="land-root">

    <!-- ══════════════════════════════════════════════════════
         NAV
    ══════════════════════════════════════════════════════ -->
    <nav class="land-nav" :class="{ 'nav-scrolled': scrolled }">
      <div class="nav-logo">AX<span class="logo-x">◈</span>ONIC</div>
      <div class="nav-links">
        <a href="#how" class="nav-link" @click.prevent="scrollTo('how')">How it works</a>
        <a href="#cases" class="nav-link" @click.prevent="scrollTo('cases')">Use cases</a>
        <a href="#output" class="nav-link" @click.prevent="scrollTo('output')">Output</a>
      </div>
      <button class="nav-cta" @click="$router.push('/start')">
        Run Simulation →
      </button>
    </nav>

    <!-- ══════════════════════════════════════════════════════
         SECTION 1 — HERO
    ══════════════════════════════════════════════════════ -->
    <section class="hero-section">
      <div class="hero-body">

        <!-- LEFT: Copy -->
        <div class="hero-left" :class="{ 'hero-revealed': heroReady }">
          <div class="hero-tag">
            <span class="tag-dot"></span>
            MARKETING DECISION ENGINE · INDIA 2026
          </div>

          <h1 class="hero-h1">
            Will this<br>
            campaign<br>
            <span class="h1-red">actually work?</span>
          </h1>

          <p class="hero-sub">
            Stop guessing. AXonic simulates how real Indian consumers
            will react to your campaign — before you spend a single rupee.
          </p>

          <div class="hero-ctas">
            <button class="cta-primary" @click="$router.push('/start')">
              Run First Simulation
              <span class="cta-arrow">→</span>
            </button>
            <div class="cta-note">
              3 free simulations · No credit card
            </div>
          </div>

          <div class="hero-trust">
            <span class="trust-text">Trusted by early-stage D2C brands & performance marketers</span>
          </div>
        </div>

        <!-- RIGHT: Live Simulation Feed -->
        <div class="hero-right" :class="{ 'hero-revealed': heroReady }">
          <div class="feed-window">
            <div class="feed-titlebar">
              <span class="feed-dot red"></span>
              <span class="feed-dot amber"></span>
              <span class="feed-dot green"></span>
              <span class="feed-title">axonic · live simulation</span>
              <span class="feed-live">
                <span class="live-blink"></span> LIVE
              </span>
            </div>

            <div class="feed-meta">
              <span class="fm-item">Campaign: <strong>Diwali Collection 2026</strong></span>
              <span class="fm-item">Platform: <strong>Instagram</strong></span>
              <span class="fm-item">Round <strong>{{ feedRound }}</strong>/3</span>
            </div>

            <div class="feed-stream" ref="feedStreamRef">
              <div
                v-for="(entry, i) in visibleFeed"
                :key="i"
                class="feed-entry"
                :class="`fe-${entry.type}`"
              >
                <span class="fe-time">{{ entry.time }}</span>
                <span class="fe-agent">{{ entry.agent }}</span>
                <span class="fe-action">{{ entry.action }}</span>
                <span class="fe-badge" :class="`badge-${entry.sentiment}`">{{ entry.sentiment }}</span>
              </div>
              <div class="feed-cursor" v-if="feedRunning">
                <span class="cursor-blink">_</span>
                <span class="cursor-label">agents processing...</span>
              </div>
            </div>

            <div class="feed-footer">
              <div class="ff-signals">
                <div class="ffs-item" v-for="sig in feedSignals" :key="sig.label">
                  <span class="ffs-label">{{ sig.label }}</span>
                  <div class="ffs-bar">
                    <div class="ffs-fill" :style="{ width: sig.pct + '%', background: sig.color }"></div>
                  </div>
                  <span class="ffs-val">{{ sig.pct }}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- Background noise texture -->
      <div class="hero-noise"></div>
    </section>

    <!-- ══════════════════════════════════════════════════════
         SECTION 2 — HOW IT WORKS
    ══════════════════════════════════════════════════════ -->
    <section id="how" class="how-section" ref="howRef">
      <div class="section-inner">
        <div class="section-label">// HOW IT WORKS</div>
        <h2 class="section-h2" :class="{ revealed: howReady }">
          From campaign idea<br>to decision — in minutes.
        </h2>

        <div class="pipeline" :class="{ revealed: howReady }">

          <div class="pipe-step" :class="{ 'pipe-active': pipeStep >= 1 }">
            <div class="ps-number">01</div>
            <div class="ps-body">
              <div class="ps-icon">⌨</div>
              <div class="ps-title">Define Strategy</div>
              <div class="ps-desc">Paste your strategy documents and a specific simulation prompt. Takes 60 seconds.</div>
            </div>
            <div class="ps-state" v-if="pipeStep >= 1">
              <span class="pss-dot done"></span> Ready
            </div>
          </div>

          <div class="pipe-arrow" :class="{ 'arrow-active': pipeStep >= 2 }">
            <div class="pa-line"></div>
            <div class="pa-head">▶</div>
          </div>

          <div class="pipe-step" :class="{ 'pipe-active': pipeStep >= 2 }">
            <div class="ps-number">02</div>
            <div class="ps-body">
              <div class="ps-icon">⚙</div>
              <div class="ps-title">Simulate Reactions</div>
              <div class="ps-desc">AI agents behave like real Indian consumers across Tier 1, 2 & 3 cities.</div>
            </div>
            <div class="ps-state running" v-if="pipeStep === 2">
              <span class="pss-dot pulsing"></span> Simulating...
            </div>
            <div class="ps-state" v-if="pipeStep > 2">
              <span class="pss-dot done"></span> Complete
            </div>
          </div>

          <div class="pipe-arrow" :class="{ 'arrow-active': pipeStep >= 3 }">
            <div class="pa-line"></div>
            <div class="pa-head">▶</div>
          </div>

          <div class="pipe-step" :class="{ 'pipe-active': pipeStep >= 3 }">
            <div class="ps-number">03</div>
            <div class="ps-body">
              <div class="ps-icon">◈</div>
              <div class="ps-title">Get Decision Report</div>
              <div class="ps-desc">Know what works, what risks exist, and what to change — before spending.</div>
            </div>
            <div class="ps-state" v-if="pipeStep >= 3">
              <span class="pss-dot done"></span> Report ready
            </div>
          </div>

        </div>

        <!-- Progress bar under pipeline -->
        <div class="pipe-progress">
          <div class="pp-fill" :style="{ width: pipeProgressWidth }"></div>
        </div>

      </div>
    </section>

    <!-- ══════════════════════════════════════════════════════
         SECTION 3 — USE CASES
    ══════════════════════════════════════════════════════ -->
    <section id="cases" class="cases-section" ref="casesRef">
      <div class="section-inner">
        <div class="section-label">// BUILT FOR REAL DECISIONS</div>
        <h2 class="section-h2" :class="{ revealed: casesReady }">
          Not a research tool.<br>A decision engine.
        </h2>

        <div class="cases-grid" :class="{ revealed: casesReady }">
          <div
            v-for="(c, i) in useCases"
            :key="i"
            class="case-card"
            :style="{ animationDelay: `${i * 0.1}s` }"
          >
            <div class="cc-icon">{{ c.icon }}</div>
            <div class="cc-title">{{ c.title }}</div>
            <div class="cc-desc">{{ c.desc }}</div>
            <div class="cc-outcome">
              <span class="outcome-label">OUTCOME</span>
              {{ c.outcome }}
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ══════════════════════════════════════════════════════
         SECTION 4 — DECISION REPORT PREVIEW
    ══════════════════════════════════════════════════════ -->
    <section id="output" class="output-section" ref="outputRef">
      <div class="section-inner">
        <div class="section-label">// WHAT YOU GET</div>
        <h2 class="section-h2" :class="{ revealed: outputReady }">
          An executive brief —<br>not a data dump.
        </h2>

        <div class="report-preview" :class="{ revealed: outputReady }">

          <!-- Fake Report Card -->
          <div class="rp-card">
            <div class="rp-topbar">
              <span class="rp-label">AXONIC DECISION REPORT</span>
              <span class="rp-date">{{ todayDate }}</span>
            </div>

            <!-- Verdict -->
            <div class="rp-verdict" :class="{ 'verdict-in': reportRevealed >= 1 }">
              <div class="rv-left">
                <div class="rv-tag">VERDICT</div>
                <div class="rv-headline">Strong Campaign</div>
                <div class="rv-reason">High emotional resonance with urban millennials in Tier 1 cities.</div>
              </div>
              <div class="rv-score">
                <div class="score-ring">
                  <svg viewBox="0 0 60 60">
                    <circle cx="30" cy="30" r="24" class="sr-track"/>
                    <circle
                      cx="30" cy="30" r="24"
                      class="sr-fill"
                      :stroke-dasharray="`${reportRevealed >= 1 ? 131 : 0} 151`"
                    />
                  </svg>
                  <span class="score-num">{{ reportRevealed >= 1 ? '87' : '—' }}</span>
                </div>
                <div class="score-label">CONFIDENCE</div>
              </div>
            </div>

            <!-- Risks -->
            <div class="rp-section" :class="{ 'section-in': reportRevealed >= 2 }">
              <div class="rps-header">▲ RISK FACTORS</div>
              <div class="rps-items">
                <div class="rps-item risk">Negative sentiment risk in Tier 2 cities — 34% likelihood</div>
                <div class="rps-item risk">Aggressive tone may alienate 35+ audience segment</div>
                <div class="rps-item risk">Instagram saturation risk after 72-hour peak window</div>
              </div>
            </div>

            <!-- Recommendations -->
            <div class="rp-section" :class="{ 'section-in': reportRevealed >= 3 }">
              <div class="rps-header">◆ RECOMMENDATIONS</div>
              <div class="rps-items">
                <div class="rps-item rec"><span class="rec-n">01</span> Launch at 8–10 PM IST when Delhi NCR engagement peaks</div>
                <div class="rps-item rec"><span class="rec-n">02</span> Switch tone to Emotional for Tier 2 audience segments</div>
                <div class="rps-item rec"><span class="rec-n">03</span> Activate micro-influencers (50K–200K) for amplification</div>
              </div>
            </div>

            <!-- India Insight -->
            <div class="rp-insight" :class="{ 'section-in': reportRevealed >= 4 }">
              <div class="ri-flag">🇮🇳 INDIA INSIGHT</div>
              <div class="ri-text">
                WhatsApp forward potential is high — family groups in Tier 2 cities are the primary amplification vector for this category.
              </div>
            </div>

          </div>

          <!-- Side caption -->
          <div class="rp-captions">
            <div
              v-for="(cap, i) in reportCaptions"
              :key="i"
              class="rp-cap"
              :class="{ 'cap-active': reportRevealed >= i + 1 }"
            >
              <div class="cap-line"></div>
              <div class="cap-body">
                <div class="cap-label">{{ cap.label }}</div>
                <div class="cap-text">{{ cap.text }}</div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </section>

    <!-- ══════════════════════════════════════════════════════
         SECTION 5 — FINAL CTA
    ══════════════════════════════════════════════════════ -->
    <section class="cta-section">
      <div class="section-inner cta-inner">
        <div class="cta-tag">// START NOW</div>
        <h2 class="cta-h2">
          Stop guessing.<br>Start simulating.
        </h2>
        <p class="cta-sub">
          Make better marketing decisions before spending money.
        </p>
        <button class="cta-big" @click="$router.push('/start')">
          Run Your First Simulation
          <span class="cta-arrow">→</span>
        </button>
        <div class="cta-meta">
          AXonic Decision Engine · Built for Strategic Excellence
        </div>
      </div>
    </section>

    <!-- FOOTER -->
    <footer class="land-footer">
      <div class="lf-logo">AX<span class="logo-x">◈</span>ONIC</div>
      <div class="lf-right">
        <span class="lf-copy">© 2026 AXonic. Marketing intelligence for India.</span>
      </div>
    </footer>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

// ── Scroll state ──────────────────────────────────────────────
const scrolled   = ref(false)
const heroReady  = ref(false)
const howReady   = ref(false)
const casesReady = ref(false)
const outputReady = ref(false)

const howRef    = ref(null)
const casesRef  = ref(null)
const outputRef = ref(null)

const scrollTo = (id) => {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
}

// ── Hero animation ────────────────────────────────────────────
const feedStreamRef = ref(null)
const feedRound     = ref(1)
const feedRunning   = ref(true)
const visibleFeed   = ref([])
const pipeStep      = ref(0)
const feedSignals   = ref([
  { label: 'ATTENTION',     pct: 0,  color: '#00E5FF' },
  { label: 'TRUST',         pct: 0,  color: '#00FF88' },
  { label: 'RISK',          pct: 0,  color: '#FF1744' },
  { label: 'AMPLIFICATION', pct: 0,  color: '#FFB300' },
])

const allFeedEntries = [
  { time: '09:01', agent: 'Priya M.',         action: 'Saved post to wishlist collection',          sentiment: 'positive', round: 1 },
  { time: '09:03', agent: 'Rahul K.',         action: 'Shared to family WhatsApp group',            sentiment: 'positive', round: 1 },
  { time: '09:07', agent: 'Skeptic_Delhi',    action: 'Commented: feels overpriced for the design', sentiment: 'negative', round: 2 },
  { time: '09:11', agent: 'Meera Insta @42K', action: 'Created Reel reaction — 12K views in 2h',   sentiment: 'positive', round: 2 },
  { time: '09:15', agent: 'Amit R.',          action: 'Searched competitor prices after seeing ad', sentiment: 'neutral',  round: 2 },
  { time: '09:19', agent: 'Influencer @180K', action: 'Amplified → reach multiplied 7x',           sentiment: 'positive', round: 3 },
  { time: '09:22', agent: 'SentimentBot',     action: 'SIGNAL: Trust score rising — +14 points',   sentiment: 'positive', round: 3 },
  { time: '09:25', agent: 'Tier2_Jaipur',     action: 'Engagement from new city cluster detected',  sentiment: 'positive', round: 3 },
]

let feedTimer = null
let feedIndex = 0

const startFeed = () => {
  feedTimer = setInterval(() => {
    if (feedIndex < allFeedEntries.length) {
      const entry = allFeedEntries[feedIndex]
      visibleFeed.value.push(entry)
      feedRound.value = entry.round

      // Update signals gradually
      feedSignals.value[0].pct = Math.min(95, feedSignals.value[0].pct + 11)
      feedSignals.value[1].pct = entry.sentiment === 'negative'
        ? Math.max(10, feedSignals.value[1].pct - 5)
        : Math.min(90, feedSignals.value[1].pct + 8)
      feedSignals.value[2].pct = entry.sentiment === 'negative'
        ? Math.min(70, feedSignals.value[2].pct + 12)
        : Math.max(5,  feedSignals.value[2].pct - 4)
      feedSignals.value[3].pct = Math.min(95, feedSignals.value[3].pct + 10)

      feedIndex++
      // Scroll feed
      setTimeout(() => {
        if (feedStreamRef.value) {
          feedStreamRef.value.scrollTop = feedStreamRef.value.scrollHeight
        }
      }, 50)
    } else {
      // Loop: reset after pause
      feedRunning.value = false
      setTimeout(() => {
        visibleFeed.value = []
        feedIndex = 0
        feedRound.value = 1
        feedSignals.value.forEach(s => { s.pct = 0 })
        feedRunning.value = true
        startFeed()
      }, 4000)
      clearInterval(feedTimer)
    }
  }, 900)
}

// ── Pipeline animation ────────────────────────────────────────
const pipeProgressWidth = computed(() => {
  return { 0: '0%', 1: '17%', 2: '50%', 3: '100%' }[pipeStep.value] || '0%'
})

const animatePipeline = () => {
  setTimeout(() => { pipeStep.value = 1 }, 300)
  setTimeout(() => { pipeStep.value = 2 }, 1400)
  setTimeout(() => { pipeStep.value = 3 }, 2500)
}

// ── Section reveal (Observer) ─────────────────────────────────
const reportRevealed = ref(0)

const observeSection = (el, onVisible) => {
  const obs = new IntersectionObserver(
    ([entry]) => { if (entry.isIntersecting) { onVisible(); obs.disconnect() } },
    { threshold: 0.2 }
  )
  if (el) obs.observe(el)
}

// ── Data ──────────────────────────────────────────────────────
const todayDate = new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })

const useCases = [
  { icon: '🚀', title: 'D2C Brand Launch',       desc: 'Test product messaging before running ads. Know which angle converts.', outcome: 'Save ₹2L+ in wasted ad spend' },
  { icon: '🎯', title: 'Ad Campaign Testing',     desc: 'Predict which creatives will drive results on each platform.',           outcome: '3× higher campaign ROI' },
  { icon: '🛡', title: 'PR Crisis Simulation',    desc: 'See how backlash spreads before it happens. Prepare your response.',     outcome: 'Prevent brand damage' },
  { icon: '🎤', title: 'Influencer Strategy',     desc: 'Know which voices genuinely drive engagement in your category.',         outcome: 'Right influencer, right timing' },
  { icon: '🏪', title: 'Festival Campaign Prep',  desc: 'Simulate Diwali, IPL, and Holi campaigns before big-spend windows.',     outcome: 'Peak-season confidence' },
  { icon: '📦', title: 'Product Positioning',     desc: 'Test 3 different positioning angles and pick the winner.',               outcome: 'Data-driven GTM strategy' },
]

const reportCaptions = [
  { label: 'VERDICT',         text: 'Clear pass/fail — no ambiguity' },
  { label: 'RISKS',           text: 'Specific threats, not generic warnings' },
  { label: 'RECOMMENDATIONS', text: 'Precise actions, not vague advice' },
  { label: 'INDIA INSIGHT',   text: 'Local context no Western tool provides' },
]

// ── Lifecycle ─────────────────────────────────────────────────
onMounted(() => {
  // Scroll listener
  const onScroll = () => { scrolled.value = window.scrollY > 20 }
  window.addEventListener('scroll', onScroll)

  // Hero entry
  setTimeout(() => { heroReady.value = true }, 100)

  // Start live feed
  setTimeout(() => { startFeed() }, 600)

  // Observe sections
  observeSection(howRef.value, () => {
    howReady.value = true
    animatePipeline()
  })

  observeSection(casesRef.value, () => { casesReady.value = true })

  observeSection(outputRef.value, () => {
    outputReady.value = true
    // Stagger report reveal
    setTimeout(() => { reportRevealed.value = 1 }, 400)
    setTimeout(() => { reportRevealed.value = 2 }, 900)
    setTimeout(() => { reportRevealed.value = 3 }, 1400)
    setTimeout(() => { reportRevealed.value = 4 }, 1900)
  })

  return () => window.removeEventListener('scroll', onScroll)
})

onUnmounted(() => { clearInterval(feedTimer) })
</script>

<style scoped>
/* ── TOKENS ──────────────────────────────────────────────────── */
.land-root {
  background: #0A0A0A;
  color: #FFFFFF;
  font-family: 'Space Grotesk', system-ui, sans-serif;
  overflow-x: hidden;
}

/* ── NAV ──────────────────────────────────────────────────────── */
.land-nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 200;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 48px;
  transition: background 0.3s, border-bottom 0.3s;
}

.nav-scrolled {
  background: rgba(10, 10, 10, 0.92);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid #1E1E1E;
}

.nav-logo {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 800;
  font-size: 18px;
  letter-spacing: 3px;
  color: #FF1744;
}

.logo-x { color: #00E5FF; font-size: 14px; margin: 0 1px; }

.nav-links {
  display: flex;
  gap: 40px;
}

.nav-link {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 1px;
  color: #555555;
  text-decoration: none;
  cursor: pointer;
  transition: color 0.2s;
}
.nav-link:hover { color: #FFFFFF; }

.nav-cta {
  background: #FF1744;
  border: none;
  color: #FFFFFF;
  padding: 9px 22px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 1.5px;
  cursor: pointer;
  transition: all 0.2s;
}
.nav-cta:hover { background: #FF4569; transform: translateY(-1px); }

/* ── HERO ──────────────────────────────────────────────────── */
.hero-section {
  min-height: 100vh;
  padding: 108px 48px 80px;
  position: relative;
  display: flex;
  align-items: center;
}

.hero-body {
  max-width: 1280px;
  margin: 0 auto;
  width: 100%;
  display: grid;
  grid-template-columns: 1fr 1.1fr;
  gap: 80px;
  align-items: center;
}

/* Entry animation */
.hero-left {
  opacity: 0;
  transform: translateY(24px) blur(8px);
  filter: blur(8px);
  transition: opacity 0.8s ease, transform 0.8s ease, filter 0.8s ease;
}
.hero-right {
  opacity: 0;
  transform: translateY(32px);
  filter: blur(4px);
  transition: opacity 0.9s ease 0.2s, transform 0.9s ease 0.2s, filter 0.9s ease 0.2s;
}
.hero-revealed {
  opacity: 1 !important;
  transform: none !important;
  filter: none !important;
}

.hero-tag {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 2px;
  color: #FF1744;
  margin-bottom: 28px;
}

.tag-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #FF1744;
  animation: pulse-dot 2s infinite;
}

@keyframes pulse-dot {
  0%,100% { opacity: 1; transform: scale(1); }
  50%      { opacity: 0.4; transform: scale(0.8); }
}

.hero-h1 {
  font-size: clamp(3rem, 5vw, 5.5rem);
  font-weight: 700;
  line-height: 1.0;
  letter-spacing: -3px;
  margin: 0 0 28px;
}

.h1-red { color: #FF1744; }

.hero-sub {
  font-size: 1.05rem;
  color: #666666;
  line-height: 1.75;
  max-width: 500px;
  margin-bottom: 40px;
}

.hero-ctas {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 32px;
}

.cta-primary {
  background: #FF1744;
  border: none;
  color: #FFFFFF;
  padding: 16px 32px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  letter-spacing: 1.5px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.2s;
  font-weight: 700;
}
.cta-primary:hover { background: #FF4569; transform: translateY(-2px); box-shadow: 0 8px 32px rgba(255,23,68,0.3); }

.cta-arrow { font-size: 16px; transition: transform 0.2s; }
.cta-primary:hover .cta-arrow { transform: translateX(4px); }

.cta-note {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #333333;
  letter-spacing: 0.5px;
}

.hero-trust {
  padding-top: 32px;
  border-top: 1px solid #111111;
}

.trust-text {
  font-size: 12px;
  color: #333333;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.5px;
}

/* LIVE FEED WINDOW */
.feed-window {
  background: #0D0D0D;
  border: 1px solid #1E1E1E;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 0 80px rgba(255,23,68,0.06);
}

.feed-titlebar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: #111111;
  border-bottom: 1px solid #1E1E1E;
}

.feed-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.feed-dot.red   { background: #FF5F57; }
.feed-dot.amber { background: #FEBC2E; }
.feed-dot.green { background: #28C840; }

.feed-title {
  flex: 1;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #333333;
  letter-spacing: 1px;
  margin-left: 8px;
}

.feed-live {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #FF1744;
  display: flex;
  align-items: center;
  gap: 6px;
}

.live-blink {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #FF1744;
  animation: pulse-dot 1s infinite;
}

.feed-meta {
  display: flex;
  gap: 20px;
  padding: 10px 16px;
  border-bottom: 1px solid #1E1E1E;
  flex-wrap: wrap;
}

.fm-item {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #444444;
}
.fm-item strong { color: #888888; }

.feed-stream {
  height: 280px;
  overflow-y: auto;
  padding: 12px 0;
  display: flex;
  flex-direction: column;
  gap: 0;
}

/* Hide scrollbar */
.feed-stream::-webkit-scrollbar { width: 0; }

.feed-entry {
  display: grid;
  grid-template-columns: 50px 100px 1fr 64px;
  gap: 8px;
  align-items: center;
  padding: 7px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.02);
  animation: entry-in 0.4s ease both;
}

@keyframes entry-in {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

.fe-time   { font-family: 'JetBrains Mono', monospace; font-size: 9px; color: #333333; }
.fe-agent  { font-family: 'JetBrains Mono', monospace; font-size: 9px; color: #555555; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fe-action { font-size: 11px; color: #888888; }

.fe-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 8px;
  padding: 2px 6px;
  border: 1px solid currentColor;
  text-align: center;
  letter-spacing: 0.5px;
}
.badge-positive { color: #00FF88; }
.badge-negative { color: #FF1744; }
.badge-neutral  { color: #444444; }

.feed-cursor {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #333333;
}

.cursor-blink {
  color: #FF1744;
  animation: blink 1s step-end infinite;
}
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }

.feed-footer {
  border-top: 1px solid #1E1E1E;
  padding: 12px 16px;
  background: #0D0D0D;
}

.ff-signals { display: flex; flex-direction: column; gap: 6px; }

.ffs-item {
  display: grid;
  grid-template-columns: 80px 1fr 32px;
  gap: 8px;
  align-items: center;
}

.ffs-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 8px;
  color: #333333;
  letter-spacing: 1px;
}

.ffs-bar { height: 2px; background: #1E1E1E; overflow: hidden; }

.ffs-fill {
  height: 100%;
  transition: width 0.8s ease;
}

.ffs-val {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  color: #555555;
  text-align: right;
}

/* Background noise */
.hero-noise {
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E");
  pointer-events: none;
  z-index: 0;
}

/* ── SECTION SHARED ──────────────────────────────────────────── */
.section-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 48px;
}

.section-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 3px;
  color: #333333;
  margin-bottom: 20px;
}

.section-h2 {
  font-size: clamp(2rem, 3.5vw, 3.5rem);
  font-weight: 700;
  letter-spacing: -2px;
  line-height: 1.1;
  color: #FFFFFF;
  margin-bottom: 60px;
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.7s ease, transform 0.7s ease;
}

.section-h2.revealed { opacity: 1; transform: translateY(0); }

/* ── HOW IT WORKS ────────────────────────────────────────────── */
.how-section {
  padding: 120px 0;
  border-top: 1px solid #111111;
}

.pipeline {
  display: grid;
  grid-template-columns: 1fr auto 1fr auto 1fr;
  gap: 0;
  align-items: start;
  opacity: 0;
  transform: translateY(24px);
  transition: opacity 0.7s ease 0.2s, transform 0.7s ease 0.2s;
}
.pipeline.revealed { opacity: 1; transform: translateY(0); }

.pipe-step {
  border: 1px solid #1E1E1E;
  padding: 28px;
  transition: border-color 0.4s, background 0.4s;
  position: relative;
}

.pipe-step.pipe-active {
  border-color: #FF1744;
  background: rgba(255, 23, 68, 0.04);
}

.ps-number {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #333333;
  margin-bottom: 16px;
  letter-spacing: 2px;
}

.pipe-step.pipe-active .ps-number { color: #FF1744; }

.ps-icon {
  font-size: 24px;
  margin-bottom: 12px;
  opacity: 0.7;
}

.ps-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 8px;
  color: #FFFFFF;
}

.ps-desc {
  font-size: 13px;
  color: #555555;
  line-height: 1.6;
}

.ps-state {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #555555;
  letter-spacing: 1px;
}
.ps-state.running { color: #FF1744; }

.pss-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #00FF88;
  flex-shrink: 0;
}
.pss-dot.pulsing { background: #FF1744; animation: pulse-dot 0.8s infinite; }

.pipe-arrow {
  display: flex;
  align-items: center;
  padding: 0 16px;
  padding-top: 60px;
  flex-direction: column;
  gap: 0;
}

.pa-line {
  height: 1px;
  width: 40px;
  background: #1E1E1E;
  transition: background 0.4s;
}

.pa-head {
  font-size: 10px;
  color: #1E1E1E;
  margin-left: 24px;
  transition: color 0.4s;
}

.pipe-arrow.arrow-active .pa-line { background: #FF1744; }
.pipe-arrow.arrow-active .pa-head { color: #FF1744; }

/* Progress bar */
.pipe-progress {
  height: 1px;
  background: #111111;
  margin-top: 32px;
  overflow: hidden;
}

.pp-fill {
  height: 100%;
  background: #FF1744;
  transition: width 1.2s ease;
}

/* ── USE CASES ───────────────────────────────────────────────── */
.cases-section {
  padding: 120px 0;
  border-top: 1px solid #111111;
}

.cases-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  background: #111111;
  opacity: 0;
  transform: translateY(24px);
  transition: opacity 0.7s ease 0.2s, transform 0.7s ease 0.2s;
}

.cases-grid.revealed { opacity: 1; transform: translateY(0); }

.case-card {
  background: #0A0A0A;
  padding: 32px;
  transition: background 0.2s;
  animation: none;
}

.case-card:hover {
  background: #0F0F0F;
}

.cc-icon {
  font-size: 28px;
  margin-bottom: 16px;
}

.cc-title {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 8px;
  color: #FFFFFF;
}

.cc-desc {
  font-size: 13px;
  color: #555555;
  line-height: 1.65;
  margin-bottom: 16px;
}

.cc-outcome {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #00FF88;
  letter-spacing: 0.5px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.outcome-label {
  color: #333333;
  display: block;
}

/* ── OUTPUT (REPORT PREVIEW) ─────────────────────────────────── */
.output-section {
  padding: 120px 0;
  border-top: 1px solid #111111;
}

.report-preview {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 48px;
  align-items: start;
  opacity: 0;
  transform: translateY(24px);
  transition: opacity 0.7s ease 0.2s, transform 0.7s ease 0.2s;
}
.report-preview.revealed { opacity: 1; transform: translateY(0); }

.rp-card {
  background: #111111;
  border: 1px solid #1E1E1E;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.rp-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: #0D0D0D;
  border-bottom: 1px solid #1E1E1E;
}

.rp-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  letter-spacing: 2px;
  color: #FF1744;
}

.rp-date {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  color: #333333;
}

/* VERDICT */
.rp-verdict {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 28px 24px;
  border-bottom: 1px solid #1E1E1E;
  border-left: 3px solid #00FF88;
  opacity: 0;
  transform: translateY(10px);
  transition: opacity 0.5s ease, transform 0.5s ease;
}
.rp-verdict.verdict-in { opacity: 1; transform: translateY(0); }

.rv-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  letter-spacing: 2px;
  color: #444444;
  margin-bottom: 8px;
}

.rv-headline {
  font-size: 1.8rem;
  font-weight: 700;
  color: #00FF88;
  letter-spacing: -1px;
  margin-bottom: 6px;
}

.rv-reason {
  font-size: 12px;
  color: #666666;
  line-height: 1.5;
}

/* Score Ring */
.score-ring {
  width: 72px;
  height: 72px;
  position: relative;
}

.score-ring svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.sr-track { fill: none; stroke: #1E1E1E; stroke-width: 3; }
.sr-fill  { fill: none; stroke: #00FF88; stroke-width: 3; stroke-linecap: butt; transition: stroke-dasharray 1s ease; }

.score-num {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 18px;
  font-weight: 800;
  color: #FFFFFF;
}

.score-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  color: #444444;
  text-align: center;
  letter-spacing: 1px;
  margin-top: 4px;
}

/* Report sections */
.rp-section {
  padding: 20px 24px;
  border-bottom: 1px solid #1E1E1E;
  opacity: 0;
  transform: translateY(8px);
  transition: opacity 0.5s ease, transform 0.5s ease;
}
.rp-section.section-in { opacity: 1; transform: translateY(0); }

.rps-header {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  letter-spacing: 2px;
  color: #444444;
  margin-bottom: 12px;
}

.rps-items { display: flex; flex-direction: column; gap: 8px; }

.rps-item {
  font-size: 12px;
  color: #888888;
  line-height: 1.5;
  padding: 8px 12px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.rps-item.risk { background: rgba(255,23,68,0.04); border-left: 2px solid #FF1744; color: #AAAAAA; }
.rps-item.rec  { background: rgba(255,179,0,0.04); border-left: 2px solid #FFB300; color: #AAAAAA; }

.rec-n {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: #FF1744;
  font-weight: 700;
  opacity: 0.5;
  flex-shrink: 0;
}

/* India Insight */
.rp-insight {
  padding: 20px 24px;
  background: rgba(0,229,255,0.02);
  opacity: 0;
  transform: translateY(8px);
  transition: opacity 0.5s ease, transform 0.5s ease;
}
.rp-insight.section-in { opacity: 1; transform: translateY(0); }

.ri-flag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  letter-spacing: 2px;
  color: #00E5FF;
  margin-bottom: 10px;
}

.ri-text {
  font-size: 12px;
  color: #888888;
  line-height: 1.65;
  border-left: 2px solid #00E5FF;
  padding-left: 12px;
}

/* Captions */
.rp-captions {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding-top: 40px;
}

.rp-cap {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  opacity: 0.2;
  transition: opacity 0.5s ease;
}
.rp-cap.cap-active { opacity: 1; }

.cap-line {
  width: 2px;
  min-height: 40px;
  background: #1E1E1E;
  flex-shrink: 0;
  transition: background 0.4s;
}
.rp-cap.cap-active .cap-line { background: #FF1744; }

.cap-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  letter-spacing: 1.5px;
  color: #FF1744;
  margin-bottom: 4px;
}

.cap-text {
  font-size: 12px;
  color: #555555;
  line-height: 1.5;
}

/* ── FINAL CTA ───────────────────────────────────────────────── */
.cta-section {
  padding: 120px 0;
  border-top: 1px solid #111111;
  text-align: center;
}

.cta-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
}

.cta-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 3px;
  color: #333333;
  margin-bottom: 24px;
}

.cta-h2 {
  font-size: clamp(2.5rem, 4vw, 4rem);
  font-weight: 700;
  letter-spacing: -2px;
  line-height: 1.1;
  color: #FFFFFF;
  margin-bottom: 20px;
}

.cta-sub {
  font-size: 1rem;
  color: #555555;
  margin-bottom: 40px;
  max-width: 480px;
}

.cta-big {
  background: #FF1744;
  border: none;
  color: #FFFFFF;
  padding: 20px 48px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  letter-spacing: 2px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 14px;
  transition: all 0.2s;
  font-weight: 700;
  margin-bottom: 20px;
}

.cta-big:hover {
  background: #FF4569;
  transform: translateY(-3px);
  box-shadow: 0 16px 48px rgba(255,23,68,0.35);
}

.cta-big:hover .cta-arrow { transform: translateX(4px); }

.cta-arrow { font-size: 16px; transition: transform 0.2s; }

.cta-meta {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #2A2A2A;
  letter-spacing: 0.5px;
}

/* ── FOOTER ──────────────────────────────────────────────────── */
.land-footer {
  height: 60px;
  border-top: 1px solid #111111;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 48px;
}

.lf-logo {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 800;
  font-size: 14px;
  letter-spacing: 2px;
  color: #FF1744;
}

.lf-copy {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #222222;
  letter-spacing: 0.5px;
}

/* ── SCROLLBAR ───────────────────────────────────────────────── */
::-webkit-scrollbar       { width: 4px; }
::-webkit-scrollbar-track { background: #0A0A0A; }
::-webkit-scrollbar-thumb { background: #1E1E1E; }
</style>
