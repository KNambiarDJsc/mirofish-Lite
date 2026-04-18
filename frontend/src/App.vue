<template>
  <ClerkLoading>
    <!-- Shown while Clerk is booting -->
    <div class="clerk-loading-screen">
      <div class="cls-logo">AX<span>◈</span>ONIC</div>
      <div class="cls-spinner"></div>
    </div>
  </ClerkLoading>

  <ClerkLoaded>
    <router-view />
  </ClerkLoaded>
</template>

<script setup>
import { ClerkLoaded, ClerkLoading } from '@clerk/vue'
</script>

<style>
/* ── Google Fonts ─────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700;800&display=swap');

/* ── Global Reset ─────────────────────────────────────────── */
*, *::before, *::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: 'Inter', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

button { font-family: inherit; cursor: pointer; }

input, textarea, select {
  font-family: inherit;
}

a { color: inherit; text-decoration: none; }

::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(61,30,15,0.15); border-radius: 4px; }

/* ── Clerk loading screen ─────────────────────────────────── */
.clerk-loading-screen {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 28px;
  background:
    radial-gradient(ellipse at 30% 40%, rgba(232,121,58,0.18) 0%, transparent 55%),
    radial-gradient(ellipse at 70% 60%, rgba(255,200,120,0.15) 0%, transparent 50%),
    #FDF6EC;
}

.cls-logo {
  font-weight: 800;
  font-size: 22px;
  letter-spacing: 4px;
  color: #3D1E0F;
}
.cls-logo span { color: #E8793A; }

.cls-spinner {
  width: 32px;
  height: 32px;
  border: 2.5px solid rgba(232,121,58,0.2);
  border-top-color: #E8793A;
  border-radius: 50%;
  animation: global-spin 0.75s linear infinite;
}

@keyframes global-spin { 100% { transform: rotate(360deg); } }
</style>
