<template>
  <div class="land-root">
    <!-- Grain texture overlay -->
    <div class="grain-overlay"></div>

    <!-- Animated gradient background -->
    <div class="gradient-bg"></div>

    <!-- ══════════════════════════════════════════════════
         NAV
    ══════════════════════════════════════════════════ -->
    <nav class="land-nav" :class="{ 'nav-scrolled': scrolled }">
      <div class="nav-logo">AX<span class="logo-accent">◈</span>ONIC</div>
      <div class="nav-links">
        <a href="#how"     class="nav-link" @click.prevent="scrollTo('how')">How it works</a>
        <a href="#output"  class="nav-link" @click.prevent="scrollTo('output')">Output</a>
        <a href="#pricing" class="nav-link" @click.prevent="scrollTo('pricing')">Pricing</a>
        <a href="#cases"   class="nav-link" @click.prevent="scrollTo('cases')">Use Cases</a>
      </div>
      <div class="nav-right">
        <!-- If user is already signed in, show avatar + go to app -->
        <template v-if="isSignedIn">
          <button class="nav-signup" @click="$router.push('/start')">Open App →</button>
          <UserButton after-sign-out-url="/" />
        </template>
        <!-- Guest -->
        <template v-else>
          <button class="nav-login"  @click="$router.push('/sign-in')">Log in</button>
          <button class="nav-signup" @click="$router.push('/sign-up')">Sign up</button>
        </template>
      </div>
    </nav>

    <!-- ══════════════════════════════════════════════════
         HERO
    ══════════════════════════════════════════════════ -->
    <section class="hero-section">
      <div class="hero-body" :class="{ 'hero-ready': heroReady }">

        <div class="hero-tag">
          <span class="tag-pulse"></span>
          MARKETING DECISION ENGINE · INDIA 2026
        </div>

        <h1 class="hero-h1">
          Stop guessing what will work.<br>
          <span class="h1-accent">Simulate how India will react.</span>
        </h1>

        <p class="hero-sub">
          Test your campaign against real Indian consumer behavior — before you spend a single rupee.<br>
          From Mumbai to Tier-3 Bharat, see exactly what happens when your strategy goes live.
        </p>

        <!-- Prompt Input Box -->
        <div class="hero-input-wrap" :class="{ 'input-active': inputActive }">
          <div class="input-icon">◈</div>
          <input
            ref="heroInput"
            class="hero-input"
            :value="typewriterText"
            readonly
            placeholder=""
            @click="handleInputClick"
          />
          <button
            class="hero-run-btn"
            :class="{ 'btn-firing': btnFiring }"
            @click="handleRunClick"
          >
            <span class="run-btn-text">Run →</span>
            <span class="btn-glow"></span>
          </button>
        </div>

        <div class="hero-sub-cta">
          <button class="cta-primary" @click="handleRunClick">
            Run Your First Simulation →
          </button>
          <div class="trust-line">
            Used by growth teams &amp; marketing agencies to validate campaigns before launch
          </div>
        </div>

        <!-- Free badge -->
        <div class="hero-badges">
          <span class="hb-badge">✓ 2 simulations free</span>
          <span class="hb-badge">✓ No credit card</span>
          <span class="hb-badge">✓ Results in 30 min</span>
        </div>
      </div>

      <!-- Floating Live Feed Preview -->
      <div class="hero-feed" :class="{ 'feed-ready': heroReady }">
        <div class="feed-topbar">
          <span class="ftb-dot red"></span>
          <span class="ftb-dot amber"></span>
          <span class="ftb-dot green"></span>
          <span class="ftb-title">axonic · live simulation</span>
          <span class="ftb-live"><span class="live-dot"></span> LIVE</span>
        </div>
        <div class="feed-campaign">
          Campaign: <strong>Diwali Collection 2026</strong> · Round <strong>{{ feedRound }}</strong>/3
        </div>
        <div class="feed-stream" ref="feedStreamRef">
          <div
            v-for="(entry, i) in visibleFeed"
            :key="i"
            class="feed-row"
            :class="`row-${entry.sentiment}`"
          >
            <span class="fr-time">{{ entry.time }}</span>
            <span class="fr-agent">{{ entry.agent }}</span>
            <span class="fr-action">{{ entry.action }}</span>
            <span class="fr-tag" :class="`tag-${entry.sentiment}`">{{ entry.sentiment }}</span>
          </div>
          <div class="feed-cursor" v-if="feedRunning">
            <span class="cur-blink">_</span> agents processing...
          </div>
        </div>
        <div class="feed-bars">
          <div class="fb-row" v-for="sig in feedSignals" :key="sig.label">
            <span class="fb-label">{{ sig.label }}</span>
            <div class="fb-track">
              <div class="fb-fill" :style="{ width: sig.pct + '%', background: sig.color }"></div>
            </div>
            <span class="fb-val">{{ sig.pct }}%</span>
          </div>
        </div>
      </div>
    </section>

    <!-- ══════════════════════════════════════════════════
         SECTION 2 — PAIN
    ══════════════════════════════════════════════════ -->
    <section class="pain-section reveal-section" ref="painRef" :class="{ revealed: painReady }">
      <div class="section-inner">
        <div class="s-label">// THE PROBLEM</div>
        <h2 class="s-h2">
          The Indian market isn't one market.<br>
          <span class="h2-muted">It's 100 markets behaving differently.</span>
        </h2>
        <div class="pain-body">
          <p class="pain-p">
            900M+ internet users. 22+ languages. Tier 1, Tier 2, Tier 3 — all reacting differently.
          </p>
          <div class="pain-facts">
            <div class="pf-item">
              <span class="pf-icon">✗</span>
              <span>What works in Mumbai fails in Indore.</span>
            </div>
            <div class="pf-item">
              <span class="pf-icon">✗</span>
              <span>What trends on Instagram dies on WhatsApp.</span>
            </div>
            <div class="pf-item">
              <span class="pf-icon">✗</span>
              <span>Most campaigns are still launched on gut instinct.</span>
            </div>
            <div class="pf-item pf-final">
              <span class="pf-icon">⚡</span>
              <span>And when they fail, it's already too late.</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ══════════════════════════════════════════════════
         HOW IT WORKS
    ══════════════════════════════════════════════════ -->
    <section id="how" class="how-section reveal-section" ref="howRef" :class="{ revealed: howReady }">
      <div class="section-inner">
        <div class="s-label">// HOW IT WORKS</div>
        <h2 class="s-h2">Simulate before you spend.</h2>
        <p class="s-sub">AXonic runs your strategy through a multi-agent simulation of Indian consumers.</p>

        <div class="how-grid">
          <div class="how-card" v-for="(step, i) in howSteps" :key="i" :style="{ animationDelay: `${i * 0.12}s` }">
            <div class="hc-num">{{ String(i + 1).padStart(2, '0') }}</div>
            <div class="hc-icon">{{ step.icon }}</div>
            <div class="hc-title">{{ step.title }}</div>
            <div class="hc-desc">{{ step.desc }}</div>
            <div class="hc-example" v-if="step.example">"{{ step.example }}"</div>
          </div>
        </div>
      </div>
    </section>

    <!-- ══════════════════════════════════════════════════
         OUTPUT / WHAT YOU GET
    ══════════════════════════════════════════════════ -->
    <section id="output" class="output-section reveal-section" ref="outputRef" :class="{ revealed: outputReady }">
      <div class="section-inner output-inner">

        <div class="output-left">
          <div class="s-label">// WHAT YOU GET</div>
          <h2 class="s-h2">Not analytics.<br><span class="h2-accent">Decisions.</span></h2>
          <p class="s-sub">Get a clear answer, not dashboards.</p>

          <div class="output-features">
            <div class="of-item" v-for="(f, i) in outputFeatures" :key="i" :class="{ 'of-active': reportStep >= i + 1 }">
              <span class="of-check">✔</span>
              <span>{{ f }}</span>
            </div>
          </div>
          <div class="output-time">All in under <strong>30 minutes.</strong></div>
        </div>

        <!-- Animated Report Card -->
        <div class="report-card" :class="{ 'card-revealed': outputReady }">
          <div class="rc-header">
            <span class="rc-label">AXONIC DECISION REPORT</span>
            <span class="rc-date">{{ todayDate }}</span>
          </div>

          <div class="rc-verdict" :class="{ 'vin': reportStep >= 1 }">
            <div class="rv-left">
              <div class="rv-tag">VERDICT</div>
              <div class="rv-decision">LAUNCH</div>
              <div class="rv-reason">High resonance with urban millennials · Tier 2 opportunity confirmed</div>
            </div>
            <div class="rv-score">
              <svg viewBox="0 0 60 60" class="score-svg">
                <circle cx="30" cy="30" r="24" class="sc-track"/>
                <circle cx="30" cy="30" r="24" class="sc-fill"
                  :stroke-dasharray="`${reportStep >= 1 ? 131 : 0} 151`"/>
              </svg>
              <span class="score-num">87</span>
              <div class="score-lbl">CONFIDENCE</div>
            </div>
          </div>

          <div class="rc-section" :class="{ 'sin': reportStep >= 2 }">
            <div class="rcs-head">▲ RISKS</div>
            <div class="rcs-item risk">Pricing perception gap in Tier 2 — 34% likelihood</div>
            <div class="rcs-item risk">Instagram saturation after 72-hour peak window</div>
          </div>

          <div class="rc-section" :class="{ 'sin': reportStep >= 3 }">
            <div class="rcs-head">◆ RECOMMENDATIONS</div>
            <div class="rcs-item rec"><span class="rec-n">01</span> Launch 8–10 PM IST · Delhi NCR engagement peaks</div>
            <div class="rcs-item rec"><span class="rec-n">02</span> Activate micro-influencers (50K–200K) for Tier 2</div>
            <div class="rcs-item rec"><span class="rec-n">03</span> Add Hinglish CTA + UPI cashback hook for Tier 2</div>
          </div>

          <div class="rc-india" :class="{ 'sin': reportStep >= 4 }">
            <span class="ri-flag">🇮🇳 INDIA INSIGHT</span>
            <p>WhatsApp forward potential is high — family groups in Tier 2 cities are the primary amplification vector.</p>
          </div>
        </div>

      </div>
    </section>

    <!-- ══════════════════════════════════════════════════
         INDIAN EDGE
    ══════════════════════════════════════════════════ -->
    <section class="edge-section reveal-section" ref="edgeRef" :class="{ revealed: edgeReady }">
      <div class="section-inner">
        <div class="s-label">// THE DIFFERENCE</div>
        <h2 class="s-h2">Built for how India<br>actually behaves.</h2>
        <p class="s-sub">Most tools understand global users. We simulate Indian consumers.</p>

        <div class="edge-grid">
          <div class="edge-card" v-for="(e, i) in edgeFeatures" :key="i" :style="{ animationDelay: `${i * 0.08}s` }">
            <div class="ec-icon">{{ e.icon }}</div>
            <div class="ec-title">{{ e.title }}</div>
            <div class="ec-desc">{{ e.desc }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- ══════════════════════════════════════════════════
         VALUE COMPARISON (KILLER BLOCK)
    ══════════════════════════════════════════════════ -->
    <section id="pricing" class="pricing-section reveal-section" ref="pricingRef" :class="{ revealed: pricingReady }">
      <div class="section-inner">
        <div class="s-label">// VALUE COMPARISON</div>
        <h2 class="s-h2">One simulation costs less<br>than a single ad test.</h2>
        <p class="s-sub">But saves you an entire campaign budget.</p>

        <div class="pricing-compare">

          <!-- Old Way -->
          <div class="price-card old-way">
            <div class="pc-badge">OLD WAY</div>
            <div class="pc-title">Traditional Research</div>
            <div class="pc-price">₹5,00,000 – ₹15,00,000</div>
            <div class="pc-items">
              <div class="pci bad"><span>✗</span> Agencies + focus groups</div>
              <div class="pci bad"><span>✗</span> 4–6 week delay</div>
              <div class="pci bad"><span>✗</span> Static reports</div>
              <div class="pci bad"><span>✗</span> Expensive revisions</div>
            </div>
          </div>

          <!-- VS Divider -->
          <div class="vs-divider">
            <div class="vs-line"></div>
            <div class="vs-text">VS</div>
            <div class="vs-line"></div>
          </div>

          <!-- AXonic -->
          <div class="price-card axonic-way">
            <div class="pc-badge winner">AXONIC</div>
            <div class="pc-title">AXonic Simulation</div>
            <div class="pc-price accent">₹7,000 – ₹8,000</div>
            <div class="pc-items">
              <div class="pci good"><span>✓</span> 7 full simulations</div>
              <div class="pci good"><span>✓</span> Results in 30 minutes</div>
              <div class="pci good"><span>✓</span> Real-time outcomes</div>
              <div class="pci good"><span>✓</span> Actionable decisions</div>
            </div>
            <button class="pc-cta" @click="$router.push('/start')">Start Simulating →</button>
          </div>

        </div>

        <!-- Efficiency callout -->
        <div class="efficiency-bar">
          <div class="eb-stat">
            <span class="eb-num">₹166</span>
            <span class="eb-label">cost per simulation</span>
          </div>
          <div class="eb-divider"></div>
          <div class="eb-stat">
            <span class="eb-num">7x</span>
            <span class="eb-label">simulations per plan</span>
          </div>
          <div class="eb-divider"></div>
          <div class="eb-stat">
            <span class="eb-num">85%</span>
            <span class="eb-label">efficiency at scale</span>
          </div>
          <div class="eb-divider"></div>
          <div class="eb-quote">
            You're not paying for compute.<br>
            You're paying for <strong>decision clarity.</strong>
          </div>
        </div>
      </div>
    </section>

    <!-- ══════════════════════════════════════════════════
         USE CASES
    ══════════════════════════════════════════════════ -->
    <section id="cases" class="cases-section reveal-section" ref="casesRef" :class="{ revealed: casesReady }">
      <div class="section-inner">
        <div class="s-label">// FOR AGENCIES &amp; GROWTH TEAMS</div>
        <h2 class="s-h2">Built for teams that<br>make decisions fast.</h2>
        <p class="s-sub">Agencies and growth teams use AXonic to validate, pitch, and win.</p>

        <div class="cases-grid">
          <div class="case-card" v-for="(c, i) in useCases" :key="i" :style="{ animationDelay: `${i * 0.1}s` }">
            <div class="cc-arrow">→</div>
            <div class="cc-title">{{ c.title }}</div>
            <div class="cc-desc">{{ c.desc }}</div>
          </div>
        </div>

        <!-- Agency positioning -->
        <div class="agency-block">
          <div class="ab-quote">One client saved = tool pays for itself.</div>
        </div>
      </div>
    </section>

    <!-- ══════════════════════════════════════════════════
         FUNNEL / TRY IT FREE
    ══════════════════════════════════════════════════ -->
    <section class="funnel-section reveal-section" ref="funnelRef" :class="{ revealed: funnelReady }">
      <div class="section-inner funnel-inner">
        <div class="funnel-left">
          <div class="s-label">// TRY BEFORE YOU COMMIT</div>
          <h2 class="s-h2 funnel-h2">Try it before<br>you commit.</h2>
          <div class="funnel-bullets">
            <div class="fb-bullet"><span class="fbb-icon">✓</span> 2 simulations free</div>
            <div class="fb-bullet"><span class="fbb-icon">✓</span> No credit card required</div>
            <div class="fb-bullet"><span class="fbb-icon">✓</span> Real use case, not a demo</div>
          </div>
          <p class="funnel-close">If it works, you already know.</p>
        </div>
        <div class="funnel-right">
          <div class="risk-card">
            <div class="risk-line fail">If your campaign fails → it costs <strong>lakhs.</strong></div>
            <div class="risk-divider"></div>
            <div class="risk-line safe">If you simulate first → it costs <strong>thousands.</strong></div>
          </div>
        </div>
      </div>
    </section>

    <!-- ══════════════════════════════════════════════════
         FINAL CTA
    ══════════════════════════════════════════════════ -->
    <section class="final-cta-section">
      <div class="section-inner fcs-inner">
        <h2 class="fcs-h2">
          Before you launch your next campaign,<br>
          <span class="fcs-accent">run it here first.</span>
        </h2>
        <button class="fcs-btn breathing" @click="$router.push('/start')">
          Run Simulation →
          <span class="btn-breath-glow"></span>
        </button>
        <div class="fcs-meta">No credit card · First 2 simulations free</div>
      </div>
    </section>

    <!-- FOOTER -->
    <footer class="land-footer">
      <div class="lf-logo">AX<span class="logo-accent">◈</span>ONIC</div>
      <div class="lf-copy">© 2026 AXonic. Marketing intelligence built for India.</div>
    </footer>

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth, UserButton } from '@clerk/vue'

const { isSignedIn } = useAuth()

const router = useRouter()

// ── State ─────────────────────────────────────────────────────
const scrolled     = ref(false)
const heroReady    = ref(false)
const painReady    = ref(false)
const howReady     = ref(false)
const outputReady  = ref(false)
const edgeReady    = ref(false)
const pricingReady = ref(false)
const casesReady   = ref(false)
const funnelReady  = ref(false)
const inputActive  = ref(false)
const btnFiring    = ref(false)
const reportStep   = ref(0)

const painRef    = ref(null)
const howRef     = ref(null)
const outputRef  = ref(null)
const edgeRef    = ref(null)
const pricingRef = ref(null)
const casesRef   = ref(null)
const funnelRef  = ref(null)
const feedStreamRef = ref(null)
const heroInput  = ref(null)

const scrollTo = (id) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })

const todayDate = new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })

// ── Typewriter Effect ─────────────────────────────────────────
const typewriterQueries = [
  'Test this campaign for Diwali launch in Tier 2 cities',
  'Will this FinTech ad work for 25–35 year olds in Pune?',
  'Which influencer strategy converts for D2C beauty in India?',
  'How will Tier 3 users react to this pricing?',
  'Validate this IPL campaign before ₹50L spend',
]
const typewriterText = ref('')
let twIndex = 0
let twCharIdx = 0
let twDeleting = false
let twTimer = null

const typeNext = () => {
  const target = typewriterQueries[twIndex]
  if (!twDeleting) {
    typewriterText.value = target.slice(0, ++twCharIdx)
    if (twCharIdx === target.length) {
      twDeleting = true
      twTimer = setTimeout(typeNext, 2400)
      return
    }
  } else {
    typewriterText.value = target.slice(0, --twCharIdx)
    if (twCharIdx === 0) {
      twDeleting = false
      twIndex = (twIndex + 1) % typewriterQueries.length
    }
  }
  twTimer = setTimeout(typeNext, twDeleting ? 32 : 58)
}

// ── Input / CTA Interactions ──────────────────────────────────
const handleInputClick = () => {
  inputActive.value = true
  router.push(isSignedIn.value ? '/start' : '/sign-up')
}

const handleRunClick = () => {
  btnFiring.value = true
  setTimeout(() => {
    btnFiring.value = false
    router.push(isSignedIn.value ? '/start' : '/sign-up')
  }, 380)
}

// ── Live Feed ─────────────────────────────────────────────────
const feedRound   = ref(1)
const feedRunning = ref(true)
const visibleFeed = ref([])
const feedSignals = ref([
  { label: 'ATTENTION',     pct: 0, color: '#E8793A' },
  { label: 'TRUST',         pct: 0, color: '#5dbb7e' },
  { label: 'RISK',          pct: 0, color: '#e85d5d' },
  { label: 'AMPLIFICATION', pct: 0, color: '#c17de8' },
])

const allFeedEntries = [
  { time: '09:01', agent: 'Priya M.', action: 'Saved to wishlist · premium tag resonating', sentiment: 'positive', round: 1 },
  { time: '09:03', agent: 'Rahul K.', action: 'Forwarded to family WhatsApp group', sentiment: 'positive', round: 1 },
  { time: '09:07', agent: 'Skeptic_Delhi', action: '"Feels overpriced yaar" — negative comment', sentiment: 'negative', round: 2 },
  { time: '09:11', agent: 'Meera @42K', action: 'Created Reel · 12K views in 2h', sentiment: 'positive', round: 2 },
  { time: '09:15', agent: 'Amit R.', action: 'Searched competitor prices after seeing ad', sentiment: 'neutral', round: 2 },
  { time: '09:19', agent: 'Influencer @180K', action: 'Amplified → reach multiplied 7×', sentiment: 'positive', round: 3 },
  { time: '09:22', agent: 'SentimentBot', action: 'SIGNAL: Trust score rising +14 pts', sentiment: 'positive', round: 3 },
  { time: '09:25', agent: 'Tier2_Jaipur', action: 'New city cluster engagement detected', sentiment: 'positive', round: 3 },
]

let feedTimer = null
let feedIdx = 0

const startFeed = () => {
  feedTimer = setInterval(() => {
    if (feedIdx < allFeedEntries.length) {
      const e = allFeedEntries[feedIdx]
      visibleFeed.value.push(e)
      feedRound.value = e.round
      feedSignals.value[0].pct = Math.min(95, feedSignals.value[0].pct + 11)
      feedSignals.value[1].pct = e.sentiment === 'negative'
        ? Math.max(10, feedSignals.value[1].pct - 5)
        : Math.min(88, feedSignals.value[1].pct + 8)
      feedSignals.value[2].pct = e.sentiment === 'negative'
        ? Math.min(65, feedSignals.value[2].pct + 12)
        : Math.max(5, feedSignals.value[2].pct - 4)
      feedSignals.value[3].pct = Math.min(95, feedSignals.value[3].pct + 10)
      feedIdx++
      setTimeout(() => {
        if (feedStreamRef.value) feedStreamRef.value.scrollTop = feedStreamRef.value.scrollHeight
      }, 50)
    } else {
      feedRunning.value = false
      setTimeout(() => {
        visibleFeed.value = []
        feedIdx = 0
        feedRound.value = 1
        feedSignals.value.forEach(s => { s.pct = 0 })
        feedRunning.value = true
        startFeed()
      }, 3500)
      clearInterval(feedTimer)
    }
  }, 850)
}

// ── Section Observer ──────────────────────────────────────────
const observe = (el, onVisible, delay = 0) => {
  const obs = new IntersectionObserver(([entry]) => {
    if (entry.isIntersecting) {
      setTimeout(() => onVisible(), delay)
      obs.disconnect()
    }
  }, { threshold: 0.15 })
  if (el) obs.observe(el)
}

// ── Data ──────────────────────────────────────────────────────
const howSteps = [
  { icon: '⌨', title: 'Upload your strategy', desc: 'Add campaign briefs, messaging, or research documents.', example: null },
  { icon: '🎯', title: 'Define what to test', desc: 'Ask anything specific to your campaign.', example: 'Will this pricing work in Tier 2?' },
  { icon: '⚙', title: 'Run the simulation', desc: 'Watch how Indian consumers react across segments, cities, and behaviors.', example: null },
]

const outputFeatures = [
  'Launch / Hold / Kill decision',
  'Persona-wise reactions (Tier 1 / 2 / 3)',
  'Risks before they become expensive mistakes',
  'Opportunities competitors won\'t see',
  'Exact changes to improve performance',
]

const edgeFeatures = [
  { icon: '💬', title: 'WhatsApp-driven virality', desc: 'Model how campaigns move from public platforms into private groups — where most Indian buying decisions happen.' },
  { icon: '💰', title: '"Paisa Vasool" mindset', desc: 'Simulate the deep price sensitivity and value perception that drives 80% of Indian purchase decisions.' },
  { icon: '🏙', title: 'Tier 2 / Tier 3 aspiration', desc: 'Understand how aspiration behavior differs from metros to emerging markets — it\'s a completely different psychology.' },
  { icon: '🌟', title: 'Influencer amplification', desc: 'Map exactly how messages travel through creator networks and which tier of influencer moves which segment.' },
  { icon: '🎉', title: 'Festival-driven buying', desc: 'Diwali, IPL, Eid, Holi — Indian commerce is event-driven. Simulate season-specific behavior before you spend.' },
]

const useCases = [
  { title: 'Campaign validation', desc: 'Will this actually convert? Know before you spend.' },
  { title: 'Pitch differentiation', desc: 'Show clients predicted outcomes, not just strategy slides.' },
  { title: 'Creative testing', desc: 'Which message works best across Tier 1, 2, 3?' },
  { title: 'Pricing strategy', desc: 'Too premium or just right? Test before the launch.' },
  { title: 'Tier 2 / Tier 3 expansion', desc: 'What breaks outside metros? Simulate it first.' },
  { title: 'Avoid expensive failures', desc: 'One campaign failure costs more than a year of simulations.' },
]

// ── Lifecycle ─────────────────────────────────────────────────
onMounted(() => {
  const onScroll = () => { scrolled.value = window.scrollY > 20 }
  window.addEventListener('scroll', onScroll)

  setTimeout(() => { heroReady.value = true }, 80)
  setTimeout(() => { startFeed() }, 700)
  setTimeout(() => { typeNext() }, 1200)

  observe(painRef.value,    () => { painReady.value    = true })
  observe(howRef.value,     () => { howReady.value     = true })
  observe(outputRef.value,  () => {
    outputReady.value = true
    setTimeout(() => { reportStep.value = 1 }, 400)
    setTimeout(() => { reportStep.value = 2 }, 900)
    setTimeout(() => { reportStep.value = 3 }, 1400)
    setTimeout(() => { reportStep.value = 4 }, 1900)
  })
  observe(edgeRef.value,    () => { edgeReady.value    = true })
  observe(pricingRef.value, () => { pricingReady.value = true })
  observe(casesRef.value,   () => { casesReady.value   = true })
  observe(funnelRef.value,  () => { funnelReady.value  = true })

  return () => window.removeEventListener('scroll', onScroll)
})

onUnmounted(() => {
  clearInterval(feedTimer)
  clearTimeout(twTimer)
})
</script>

<style scoped>
/* ──────────────────────────────────────────────────────────────
   TOKENS
────────────────────────────────────────────────────────────── */
:root {
  --cream:   #FDF6EC;
  --warm:    #F5E6CE;
  --orange:  #E8793A;
  --brown:   #3D1E0F;
  --text:    #2D1A0A;
  --muted:   #8A6A50;
  --card:    #FFFFFF;
  --border:  rgba(61, 30, 15, 0.1);
}

.land-root {
  background: #FDF6EC;
  color: #2D1A0A;
  font-family: 'Inter', system-ui, sans-serif;
  overflow-x: hidden;
  position: relative;
  min-height: 100vh;
}

/* Grain texture */
.grain-overlay {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 1;
  opacity: 0.035;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
  animation: grain-move 8s steps(10) infinite;
}
@keyframes grain-move {
  0%  { transform: translate(0,0); }
  10% { transform: translate(-2%,-3%); }
  20% { transform: translate(3%,2%); }
  30% { transform: translate(-1%,4%); }
  40% { transform: translate(4%,-1%); }
  50% { transform: translate(-3%,1%); }
  60% { transform: translate(2%,-4%); }
  70% { transform: translate(-4%,3%); }
  80% { transform: translate(1%,-2%); }
  90% { transform: translate(-2%,4%); }
}

/* Animated gradient bg */
.gradient-bg {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background: radial-gradient(ellipse at 20% 50%, rgba(232,121,58,0.12) 0%, transparent 60%),
              radial-gradient(ellipse at 80% 20%, rgba(245,230,206,0.4) 0%, transparent 50%),
              radial-gradient(ellipse at 50% 90%, rgba(232,121,58,0.07) 0%, transparent 50%);
  animation: grad-shift 25s ease-in-out infinite alternate;
}
@keyframes grad-shift {
  0%   { background-position: 20% 50%, 80% 20%, 50% 90%; }
  100% { background-position: 30% 40%, 70% 30%, 40% 80%; }
}

/* ── NAV ──────────────────────────────────────────────────── */
.land-nav {
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: 200;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 48px;
  transition: background 0.3s, box-shadow 0.3s;
}
.nav-scrolled {
  background: rgba(253, 246, 236, 0.92);
  backdrop-filter: blur(12px);
  box-shadow: 0 1px 0 rgba(61,30,15,0.08);
}

.nav-logo {
  font-family: 'Inter', monospace;
  font-weight: 800;
  font-size: 16px;
  letter-spacing: 3px;
  color: #3D1E0F;
}
.logo-accent { color: #E8793A; font-size: 13px; margin: 0 2px; }

.nav-links { display: flex; gap: 36px; }
.nav-link {
  font-size: 13px;
  color: #8A6A50;
  text-decoration: none;
  cursor: pointer;
  transition: color 0.2s;
  position: relative;
}
.nav-link::after {
  content: '';
  position: absolute;
  bottom: -2px; left: 0;
  width: 0; height: 1px;
  background: #E8793A;
  transition: width 0.25s;
}
.nav-link:hover { color: #3D1E0F; }
.nav-link:hover::after { width: 100%; }

.nav-right { display: flex; align-items: center; gap: 12px; }
.nav-login {
  background: none;
  border: none;
  color: #8A6A50;
  font-size: 13px;
  cursor: pointer;
  padding: 8px 16px;
  transition: color 0.2s;
}
.nav-login:hover { color: #3D1E0F; }
.nav-signup {
  background: #E8793A;
  border: none;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  padding: 9px 20px;
  border-radius: 6px;
  transition: all 0.2s;
}
.nav-signup:hover { background: #d4622a; transform: translateY(-1px); box-shadow: 0 4px 16px rgba(232,121,58,0.3); }

/* ── HERO ──────────────────────────────────────────────────── */
.hero-section {
  min-height: 100vh;
  padding: 100px 48px 80px;
  position: relative;
  z-index: 2;
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 60px;
  max-width: 1280px;
  margin: 0 auto;
  align-items: center;
}

.hero-body {
  opacity: 0;
  transform: translateY(28px);
  transition: opacity 0.8s ease, transform 0.8s ease;
}
.hero-body.hero-ready { opacity: 1; transform: none; }

.hero-tag {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11px;
  letter-spacing: 2px;
  color: #E8793A;
  font-weight: 600;
  margin-bottom: 24px;
}
.tag-pulse {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: #E8793A;
  animation: pulse-tag 2s infinite;
}
@keyframes pulse-tag {
  0%,100% { opacity: 1; box-shadow: 0 0 0 0 rgba(232,121,58,0.4); }
  50%      { opacity: 0.7; box-shadow: 0 0 0 6px rgba(232,121,58,0); }
}

.hero-h1 {
  font-size: clamp(2.4rem, 3.8vw, 4rem);
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -1.5px;
  margin: 0 0 24px;
  color: #2D1A0A;
}
.h1-accent { color: #E8793A; }

.hero-sub {
  font-size: 1rem;
  color: #7A5C42;
  line-height: 1.75;
  max-width: 520px;
  margin-bottom: 36px;
}

/* INPUT BOX */
.hero-input-wrap {
  display: flex;
  align-items: center;
  background: #FFFFFF;
  border: 1.5px solid rgba(61,30,15,0.12);
  border-radius: 14px;
  padding: 12px 12px 12px 20px;
  gap: 12px;
  margin-bottom: 24px;
  transition: border-color 0.3s, box-shadow 0.3s, transform 0.15s;
  cursor: pointer;
  box-shadow: 0 2px 16px rgba(61,30,15,0.06);
}
.hero-input-wrap:hover,
.hero-input-wrap.input-active {
  border-color: #E8793A;
  box-shadow: 0 4px 24px rgba(232,121,58,0.18);
}
.hero-input-wrap.input-active { transform: scale(0.99); }

.input-icon { color: #E8793A; font-size: 16px; flex-shrink: 0; }

.hero-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  color: #2D1A0A;
  font-family: 'Inter', sans-serif;
  cursor: pointer;
  min-width: 0;
}
.hero-input::placeholder { color: #BBA890; }

.hero-run-btn {
  background: #E8793A;
  border: none;
  color: #fff;
  padding: 12px 24px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  position: relative;
  overflow: hidden;
  transition: background 0.2s, transform 0.1s, box-shadow 0.2s;
  flex-shrink: 0;
}
.hero-run-btn:hover {
  background: #d4622a;
  box-shadow: 0 4px 20px rgba(232,121,58,0.4);
}
.hero-run-btn.btn-firing { transform: scale(0.96); }

.btn-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at center, rgba(255,255,255,0.25), transparent 70%);
  animation: btn-glow-idle 3s ease-in-out infinite;
  pointer-events: none;
}
@keyframes btn-glow-idle {
  0%,100% { opacity: 0.3; }
  50%      { opacity: 0.8; }
}

.hero-sub-cta { display: flex; align-items: center; gap: 24px; margin-bottom: 28px; }
.cta-primary {
  background: #E8793A;
  border: none;
  color: #fff;
  padding: 14px 28px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}
.cta-primary:hover { background: #d4622a; transform: translateY(-2px); box-shadow: 0 6px 24px rgba(232,121,58,0.35); }

.trust-line { font-size: 12px; color: #BBA890; line-height: 1.5; }

.hero-badges { display: flex; gap: 16px; flex-wrap: wrap; }
.hb-badge {
  font-size: 12px;
  color: #7A5C42;
  background: rgba(232,121,58,0.08);
  border: 1px solid rgba(232,121,58,0.2);
  padding: 5px 12px;
  border-radius: 20px;
}

/* LIVE FEED */
.hero-feed {
  opacity: 0;
  transform: translateY(32px);
  transition: opacity 0.9s ease 0.25s, transform 0.9s ease 0.25s;
  background: #FFFFFF;
  border-radius: 16px;
  border: 1px solid rgba(61,30,15,0.08);
  overflow: hidden;
  box-shadow: 0 8px 48px rgba(61,30,15,0.1);
  position: relative;
  z-index: 2;
}
.hero-feed.feed-ready { opacity: 1; transform: none; }

.feed-topbar {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 10px 16px;
  background: #FDF6EC;
  border-bottom: 1px solid rgba(61,30,15,0.07);
}
.ftb-dot { width: 10px; height: 10px; border-radius: 50%; }
.ftb-dot.red   { background: #FF5F57; }
.ftb-dot.amber { background: #FEBC2E; }
.ftb-dot.green { background: #28C840; }
.ftb-title { flex: 1; font-size: 11px; color: #BBA890; letter-spacing: 0.5px; margin-left: 6px; }
.ftb-live { font-size: 11px; color: #E8793A; display: flex; align-items: center; gap: 5px; font-weight: 600; }
.live-dot { width: 6px; height: 6px; border-radius: 50%; background: #E8793A; animation: pulse-tag 1s infinite; }

.feed-campaign { padding: 10px 16px; font-size: 11px; color: #BBA890; border-bottom: 1px solid rgba(61,30,15,0.06); }
.feed-campaign strong { color: #3D1E0F; }

.feed-stream {
  height: 240px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  padding: 8px 0;
}
.feed-stream::-webkit-scrollbar { width: 0; }

.feed-row {
  display: grid;
  grid-template-columns: 44px 96px 1fr 64px;
  gap: 6px;
  align-items: center;
  padding: 6px 16px;
  border-bottom: 1px solid rgba(61,30,15,0.04);
  animation: row-in 0.35s ease both;
}
@keyframes row-in {
  from { opacity: 0; transform: translateY(5px); }
  to   { opacity: 1; transform: none; }
}
.fr-time   { font-size: 9px; color: #D4B9A0; font-family: monospace; }
.fr-agent  { font-size: 10px; color: #8A6A50; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fr-action { font-size: 11px; color: #5A3E28; }
.fr-tag { font-size: 9px; padding: 2px 7px; border-radius: 20px; font-weight: 600; text-align: center; }
.tag-positive { background: rgba(93,187,126,0.15); color: #2d7a4f; border: 1px solid rgba(93,187,126,0.3); }
.tag-negative { background: rgba(232,93,93,0.12); color: #9a2d2d; border: 1px solid rgba(232,93,93,0.25); }
.tag-neutral  { background: rgba(138,106,80,0.1); color: #8A6A50; border: 1px solid rgba(138,106,80,0.2); }

.feed-cursor { padding: 8px 16px; font-size: 10px; color: #BBA890; display: flex; gap: 6px; align-items: center; }
.cur-blink { animation: blink 1s step-end infinite; }
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }

.feed-bars { padding: 12px 16px; border-top: 1px solid rgba(61,30,15,0.07); display: flex; flex-direction: column; gap: 7px; }
.fb-row { display: grid; grid-template-columns: 90px 1fr 32px; gap: 8px; align-items: center; }
.fb-label { font-size: 9px; color: #BBA890; letter-spacing: 0.5px; }
.fb-track { height: 4px; background: rgba(61,30,15,0.08); border-radius: 2px; overflow: hidden; }
.fb-fill  { height: 100%; border-radius: 2px; transition: width 0.6s ease; }
.fb-val   { font-size: 9px; color: #8A6A50; text-align: right; font-family: monospace; }

/* ── SECTION COMMONS ──────────────────────────────────────── */
.section-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 48px;
}
.reveal-section {
  padding: 100px 0;
  position: relative;
  z-index: 2;
}
.reveal-section .s-h2,
.reveal-section .s-sub,
.reveal-section .how-grid,
.reveal-section .cases-grid,
.reveal-section .edge-grid,
.reveal-section .pricing-compare,
.reveal-section .output-inner,
.reveal-section .pain-body,
.reveal-section .funnel-inner {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}
.reveal-section.revealed .s-h2    { opacity: 1; transform: none; }
.reveal-section.revealed .s-sub   { opacity: 1; transform: none; transition-delay: 0.1s; }
.reveal-section.revealed .how-grid,
.reveal-section.revealed .cases-grid,
.reveal-section.revealed .edge-grid,
.reveal-section.revealed .pricing-compare,
.reveal-section.revealed .output-inner,
.reveal-section.revealed .pain-body,
.reveal-section.revealed .funnel-inner { opacity: 1; transform: none; transition-delay: 0.2s; }

.s-label {
  font-size: 11px;
  letter-spacing: 2.5px;
  color: #E8793A;
  font-weight: 700;
  margin-bottom: 16px;
}
.s-h2 {
  font-size: clamp(2rem, 3.2vw, 3.2rem);
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: -1px;
  margin: 0 0 16px;
  color: #2D1A0A;
}
.h2-muted  { color: #BBA890; }
.h2-accent { color: #E8793A; }
.s-sub     { font-size: 1rem; color: #7A5C42; margin-bottom: 52px; }

/* ── PAIN ────────────────────────────────────────────────── */
.pain-section {
  background: linear-gradient(180deg, #FDF6EC 0%, #F5E6CE 100%);
}
.pain-body {}
.pain-p { font-size: 1.05rem; color: #5A3E28; margin-bottom: 28px; line-height: 1.7; }
.pain-facts { display: flex; flex-direction: column; gap: 14px; max-width: 600px; }
.pf-item { display: flex; align-items: flex-start; gap: 14px; font-size: 1rem; color: #5A3E28; }
.pf-icon { color: #E8793A; font-size: 16px; flex-shrink: 0; margin-top: 2px; }
.pf-final { font-size: 1.1rem; font-weight: 600; color: #3D1E0F; background: rgba(232,121,58,0.08); padding: 14px 20px; border-radius: 10px; border-left: 3px solid #E8793A; margin-top: 8px; }

/* ── HOW IT WORKS ────────────────────────────────────────── */
.how-section { background: #FDF6EC; }
.how-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}
.how-card {
  background: #FFFFFF;
  border: 1px solid rgba(61,30,15,0.08);
  border-radius: 16px;
  padding: 32px 28px;
  transition: transform 0.25s, box-shadow 0.25s;
}
.how-card:hover { transform: translateY(-4px); box-shadow: 0 12px 40px rgba(61,30,15,0.1); }
.hc-num { font-size: 11px; color: #E8793A; font-weight: 700; letter-spacing: 1px; margin-bottom: 14px; }
.hc-icon { font-size: 28px; margin-bottom: 14px; }
.hc-title { font-size: 1.05rem; font-weight: 700; color: #2D1A0A; margin-bottom: 10px; }
.hc-desc  { font-size: 0.9rem; color: #7A5C42; line-height: 1.6; }
.hc-example { margin-top: 14px; font-size: 0.85rem; color: #3D1E0F; background: rgba(232,121,58,0.07); padding: 10px 14px; border-radius: 8px; border-left: 2px solid #E8793A; }

/* ── OUTPUT ──────────────────────────────────────────────── */
.output-section { background: #F5E6CE; }
.output-inner {
  display: grid;
  grid-template-columns: 1fr 1.1fr;
  gap: 72px;
  align-items: start;
}
.output-features { margin-bottom: 24px; }
.of-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 0;
  font-size: 0.95rem;
  color: #7A5C42;
  border-bottom: 1px solid rgba(61,30,15,0.07);
  opacity: 0.3;
  transition: opacity 0.4s, color 0.3s;
}
.of-item.of-active { opacity: 1; color: #2D1A0A; }
.of-check { color: #E8793A; font-size: 14px; flex-shrink: 0; }
.output-time { font-size: 0.9rem; color: #BBA890; }
.output-time strong { color: #3D1E0F; }

/* REPORT CARD */
.report-card {
  background: #FFFFFF;
  border-radius: 20px;
  border: 1px solid rgba(61,30,15,0.1);
  overflow: hidden;
  box-shadow: 0 12px 56px rgba(61,30,15,0.12);
  opacity: 0;
  transform: translateY(20px) scale(0.97);
  transition: opacity 0.7s ease 0.3s, transform 0.7s ease 0.3s;
}
.report-card.card-revealed { opacity: 1; transform: none; }

.rc-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 20px;
  background: #FDF6EC;
  border-bottom: 1px solid rgba(61,30,15,0.08);
}
.rc-label { font-size: 10px; font-weight: 700; letter-spacing: 2px; color: #E8793A; }
.rc-date  { font-size: 10px; color: #BBA890; }

.rc-verdict {
  display: flex; justify-content: space-between; align-items: flex-start;
  padding: 20px 20px 16px;
  opacity: 0; transform: translateY(10px);
  transition: opacity 0.5s, transform 0.5s;
}
.rc-verdict.vin { opacity: 1; transform: none; }
.rv-left {}
.rv-tag { font-size: 9px; letter-spacing: 2px; color: #BBA890; margin-bottom: 4px; }
.rv-decision { font-size: 1.8rem; font-weight: 800; color: #2d7a4f; letter-spacing: -1px; }
.rv-reason { font-size: 0.8rem; color: #7A5C42; margin-top: 6px; max-width: 200px; line-height: 1.4; }

.rv-score { text-align: center; }
.score-svg { width: 72px; height: 72px; }
.sc-track { fill: none; stroke: rgba(61,30,15,0.08); stroke-width: 6; }
.sc-fill {
  fill: none; stroke: #E8793A; stroke-width: 6;
  stroke-linecap: round;
  transform-origin: center;
  transform: rotate(-90deg);
  transition: stroke-dasharray 1.2s ease;
}
.score-num { display: block; font-size: 1rem; font-weight: 800; color: #2D1A0A; margin-top: -44px; }
.score-lbl { font-size: 8px; letter-spacing: 1.5px; color: #BBA890; margin-top: 4px; }

.rc-section {
  padding: 14px 20px;
  border-top: 1px solid rgba(61,30,15,0.07);
  opacity: 0; transform: translateY(8px);
  transition: opacity 0.5s, transform 0.5s;
}
.rc-section.sin { opacity: 1; transform: none; }
.rcs-head { font-size: 9px; font-weight: 700; letter-spacing: 2px; color: #3D1E0F; margin-bottom: 10px; }
.rcs-item {
  font-size: 0.82rem;
  padding: 6px 10px;
  border-radius: 6px;
  margin-bottom: 4px;
}
.rcs-item.risk { background: rgba(232,93,93,0.07); color: #7a2d2d; }
.rcs-item.rec  { background: rgba(61,30,15,0.04); color: #5A3E28; display: flex; gap: 8px; }
.rec-n { color: #E8793A; font-weight: 700; font-size: 9px; flex-shrink: 0; margin-top: 2px; }

.rc-india {
  padding: 14px 20px;
  border-top: 1px solid rgba(61,30,15,0.07);
  background: rgba(232,121,58,0.04);
  opacity: 0; transform: translateY(8px);
  transition: opacity 0.5s, transform 0.5s;
}
.rc-india.sin { opacity: 1; transform: none; }
.ri-flag { font-size: 11px; font-weight: 700; color: #E8793A; margin-bottom: 6px; display: block; }
.rc-india p { font-size: 0.82rem; color: #5A3E28; line-height: 1.5; margin: 0; }

/* ── EDGE ────────────────────────────────────────────────── */
.edge-section { background: #FDF6EC; }
.edge-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}
.edge-card {
  background: #FFFFFF;
  border: 1px solid rgba(61,30,15,0.08);
  border-radius: 14px;
  padding: 28px 24px;
  transition: transform 0.25s, box-shadow 0.25s;
}
.edge-card:hover { transform: translateY(-3px); box-shadow: 0 8px 32px rgba(61,30,15,0.09); }
.ec-icon  { font-size: 24px; margin-bottom: 12px; }
.ec-title { font-size: 0.95rem; font-weight: 700; color: #2D1A0A; margin-bottom: 8px; }
.ec-desc  { font-size: 0.85rem; color: #7A5C42; line-height: 1.6; }

/* ── PRICING ─────────────────────────────────────────────── */
.pricing-section { background: #F5E6CE; }
.pricing-compare {
  display: flex;
  align-items: stretch;
  gap: 0;
  max-width: 780px;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 12px 48px rgba(61,30,15,0.1);
  margin: 0 auto 48px;
}
.price-card { flex: 1; padding: 36px 32px; }
.old-way { background: #FFFFFF; }
.axonic-way { background: #3D1E0F; color: #FDF6EC; }
.pc-badge {
  display: inline-block;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 2px;
  padding: 4px 10px;
  border-radius: 20px;
  margin-bottom: 16px;
  background: rgba(61,30,15,0.08);
  color: #8A6A50;
}
.pc-badge.winner { background: #E8793A; color: #fff; }
.pc-title { font-size: 1rem; font-weight: 700; margin-bottom: 10px; }
.old-way .pc-title { color: #2D1A0A; }
.pc-price { font-size: 1.4rem; font-weight: 800; margin-bottom: 24px; color: #8A6A50; }
.pc-price.accent { color: #E8793A; }
.pc-items { display: flex; flex-direction: column; gap: 10px; margin-bottom: 28px; }
.pci { font-size: 0.88rem; display: flex; align-items: center; gap: 10px; }
.pci.bad { color: #BBA890; }
.pci.bad span { color: #e05555; }
.pci.good { color: #D4B9A0; }
.pci.good span { color: #5dbb7e; }
.pc-cta {
  width: 100%;
  background: #E8793A;
  border: none;
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  padding: 14px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.2s;
}
.pc-cta:hover { background: #c96428; }

.vs-divider {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0 20px;
  background: #F5E6CE;
}
.vs-line { flex: 1; width: 1px; background: rgba(61,30,15,0.12); }
.vs-text { font-size: 13px; font-weight: 700; color: #BBA890; padding: 12px 0; }

.efficiency-bar {
  display: flex;
  align-items: center;
  gap: 0;
  background: #FFFFFF;
  border-radius: 14px;
  border: 1px solid rgba(61,30,15,0.08);
  overflow: hidden;
  max-width: 900px;
  margin: 0 auto;
}
.eb-stat { flex: 1; padding: 24px; text-align: center; }
.eb-num { display: block; font-size: 1.8rem; font-weight: 800; color: #E8793A; }
.eb-label { font-size: 11px; color: #BBA890; margin-top: 4px; display: block; }
.eb-divider { width: 1px; background: rgba(61,30,15,0.08); align-self: stretch; }
.eb-quote { flex: 1.2; padding: 24px; font-size: 0.9rem; color: #5A3E28; line-height: 1.6; }
.eb-quote strong { color: #2D1A0A; }

/* ── USE CASES ───────────────────────────────────────────── */
.cases-section { background: #FDF6EC; }
.cases-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 48px;
}
.case-card {
  background: #FFFFFF;
  border: 1px solid rgba(61,30,15,0.08);
  border-radius: 14px;
  padding: 24px 22px;
  transition: transform 0.25s, box-shadow 0.25s;
  cursor: default;
}
.case-card:hover { transform: translateY(-3px); box-shadow: 0 8px 28px rgba(61,30,15,0.08); }
.cc-arrow { font-size: 18px; color: #E8793A; margin-bottom: 10px; }
.cc-title { font-size: 0.95rem; font-weight: 700; color: #2D1A0A; margin-bottom: 8px; }
.cc-desc  { font-size: 0.85rem; color: #7A5C42; line-height: 1.5; }

.agency-block { text-align: center; padding: 32px; background: rgba(232,121,58,0.06); border-radius: 16px; }
.ab-quote { font-size: 1.2rem; font-weight: 700; color: #3D1E0F; }

/* ── FUNNEL ──────────────────────────────────────────────── */
.funnel-section { background: #F5E6CE; }
.funnel-inner {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 64px;
  align-items: center;
}
.funnel-h2 { margin-bottom: 28px; }
.funnel-bullets { display: flex; flex-direction: column; gap: 14px; margin-bottom: 24px; }
.fb-bullet { font-size: 0.95rem; color: #5A3E28; display: flex; align-items: center; gap: 12px; }
.fbb-icon { color: #E8793A; font-size: 16px; }
.funnel-close { font-size: 0.95rem; color: #BBA890; font-style: italic; }

.risk-card { background: #FFFFFF; border-radius: 16px; padding: 36px; border: 1px solid rgba(61,30,15,0.08); box-shadow: 0 8px 32px rgba(61,30,15,0.08); }
.risk-line { font-size: 1rem; padding: 16px 0; }
.risk-line.fail { color: #9a2d2d; }
.risk-line.fail strong { color: #c0392b; }
.risk-line.safe { color: #2d7a4f; }
.risk-line.safe strong { color: #27ae60; font-size: 1.05rem; }
.risk-divider { height: 1px; background: rgba(61,30,15,0.1); margin: 4px 0; }

/* ── FINAL CTA ───────────────────────────────────────────── */
.final-cta-section {
  background: #3D1E0F;
  padding: 120px 48px;
  position: relative;
  z-index: 2;
  text-align: center;
}
.fcs-inner { text-align: center; }
.fcs-h2 {
  font-size: clamp(1.8rem, 3vw, 3rem);
  font-weight: 700;
  color: #FDF6EC;
  line-height: 1.2;
  margin-bottom: 40px;
  letter-spacing: -0.5px;
}
.fcs-accent { color: #E8793A; }
.fcs-btn {
  position: relative;
  background: #E8793A;
  border: none;
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  padding: 18px 42px;
  border-radius: 12px;
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
  margin-bottom: 20px;
}
.fcs-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 36px rgba(232,121,58,0.5); }
.fcs-btn:active { transform: scale(0.97); }
.btn-breath-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at center, rgba(255,255,255,0.2), transparent 70%);
  animation: breathe 2.5s ease-in-out infinite;
  pointer-events: none;
}
@keyframes breathe {
  0%,100% { opacity: 0.2; transform: scale(0.9); }
  50%      { opacity: 0.7; transform: scale(1.05); }
}
.fcs-meta { font-size: 12px; color: rgba(253,246,236,0.4); letter-spacing: 0.5px; }

/* ── FOOTER ──────────────────────────────────────────────── */
.land-footer {
  background: #2D1A0A;
  padding: 32px 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
  z-index: 2;
}
.lf-logo { font-weight: 800; font-size: 14px; letter-spacing: 3px; color: #FDF6EC; }
.lf-copy { font-size: 12px; color: rgba(253,246,236,0.35); }

/* ── RESPONSIVE ──────────────────────────────────────────── */
@media (max-width: 900px) {
  .hero-section { grid-template-columns: 1fr; padding: 90px 24px 60px; gap: 40px; }
  .hero-feed { display: none; }
  .how-grid, .edge-grid, .cases-grid { grid-template-columns: 1fr 1fr; }
  .output-inner { grid-template-columns: 1fr; }
  .funnel-inner { grid-template-columns: 1fr; }
  .pricing-compare { flex-direction: column; }
  .vs-divider { flex-direction: row; padding: 20px 0; }
  .vs-line { flex: 1; height: 1px; width: auto; }
  .efficiency-bar { flex-wrap: wrap; }
  .eb-divider { display: none; }
  .section-inner { padding: 0 24px; }
  .land-nav { padding: 0 24px; }
  .nav-links { display: none; }
}
@media (max-width: 600px) {
  .how-grid, .edge-grid, .cases-grid { grid-template-columns: 1fr; }
  .hero-sub-cta { flex-direction: column; align-items: flex-start; }
}
</style>
