<template>
  <div class="auth-root">
    <div class="auth-bg"></div>

    <!-- Logo -->
    <div class="auth-logo" @click="$router.push('/')">
      AX<span class="logo-dot">◈</span>ONIC
    </div>

    <!-- Card -->
    <div class="auth-card" :class="{ ready }">
      <div class="auth-header">
        <h1 class="auth-title">Welcome back</h1>
        <p class="auth-sub">Sign in to your AXonic account</p>
      </div>

      <!-- Clerk SignIn Component -->
      <SignIn
        :routing="'path'"
        :path="'/sign-in'"
        :sign-up-url="'/sign-up'"
        :redirect-url="'/start'"
        :appearance="{
          elements: {
            rootBox: 'clerk-root-box',
            card: 'clerk-card',
            headerTitle: 'clerk-header-title',
            headerSubtitle: 'clerk-header-sub',
            socialButtonsBlockButton: 'clerk-social-btn',
            formFieldInput: 'clerk-input',
            formButtonPrimary: 'clerk-submit-btn',
            footerActionLink: 'clerk-footer-link',
          }
        }"
      />
    </div>

    <div class="auth-footer-note">
      Don't have an account?
      <span class="auth-switch" @click="$router.push('/sign-up')">Sign up free →</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { SignIn } from '@clerk/vue'

const ready = ref(false)
onMounted(() => setTimeout(() => { ready.value = true }, 80))
</script>

<style scoped>
.auth-root {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  position: relative;
  font-family: 'Inter', system-ui, sans-serif;
}

.auth-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  background:
    radial-gradient(ellipse at 20% 40%, rgba(232,121,58,0.22) 0%, transparent 55%),
    radial-gradient(ellipse at 80% 60%, rgba(255,200,120,0.18) 0%, transparent 50%),
    #FDF6EC;
}

.auth-logo {
  position: relative;
  z-index: 2;
  font-weight: 800;
  font-size: 18px;
  letter-spacing: 3px;
  color: #3D1E0F;
  cursor: pointer;
  margin-bottom: 40px;
  user-select: none;
}
.logo-dot { color: #E8793A; font-size: 14px; margin: 0 2px; }

.auth-card {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 420px;
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.5s ease, transform 0.5s ease;
}
.auth-card.ready { opacity: 1; transform: none; }

.auth-header {
  text-align: center;
  margin-bottom: 28px;
}
.auth-title {
  font-size: 2rem;
  font-weight: 700;
  color: #2D1A0A;
  letter-spacing: -0.5px;
  margin: 0 0 8px;
  font-family: 'Georgia', serif;
}
.auth-sub {
  font-size: 0.9rem;
  color: #8A6A50;
  margin: 0;
}

/* Clerk overrides via :deep */
:deep(.cl-rootBox) {
  width: 100%;
  font-family: 'Inter', system-ui, sans-serif;
}
:deep(.cl-card) {
  background: #FFFFFF !important;
  border: 1px solid rgba(61,30,15,0.1) !important;
  border-radius: 20px !important;
  box-shadow: 0 8px 40px rgba(61,30,15,0.1) !important;
  padding: 32px !important;
}
:deep(.cl-headerTitle),
:deep(.cl-headerSubtitle) { display: none !important; }

:deep(.cl-socialButtonsBlockButton) {
  border: 1.5px solid rgba(61,30,15,0.12) !important;
  border-radius: 10px !important;
  background: #FFFFFF !important;
  color: #3D1E0F !important;
  font-weight: 600 !important;
  transition: all 0.2s !important;
}
:deep(.cl-socialButtonsBlockButton:hover) {
  border-color: #E8793A !important;
  background: rgba(232,121,58,0.04) !important;
}

:deep(.cl-formFieldInput) {
  border: 1.5px solid rgba(61,30,15,0.12) !important;
  border-radius: 10px !important;
  padding: 12px 16px !important;
  font-size: 14px !important;
  color: #2D1A0A !important;
  background: #FFFFFF !important;
  outline: none !important;
  transition: border-color 0.2s, box-shadow 0.2s !important;
}
:deep(.cl-formFieldInput:focus) {
  border-color: #E8793A !important;
  box-shadow: 0 0 0 4px rgba(232,121,58,0.1) !important;
}

:deep(.cl-formButtonPrimary) {
  background: #E8793A !important;
  color: #fff !important;
  border: none !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
  font-size: 14px !important;
  padding: 13px !important;
  transition: background 0.2s, transform 0.15s !important;
}
:deep(.cl-formButtonPrimary:hover) {
  background: #d4622a !important;
  transform: translateY(-1px) !important;
}

:deep(.cl-footerActionLink) {
  color: #E8793A !important;
  font-weight: 600 !important;
}

:deep(.cl-dividerText),
:deep(.cl-identityPreviewText),
:deep(.cl-formFieldLabel) {
  color: #5A3E28 !important;
}

:deep(.cl-internalLink) { color: #E8793A !important; }

.auth-footer-note {
  position: relative;
  z-index: 2;
  margin-top: 24px;
  font-size: 13px;
  color: #8A6A50;
}
.auth-switch {
  color: #E8793A;
  font-weight: 700;
  cursor: pointer;
  margin-left: 6px;
  transition: opacity 0.2s;
}
.auth-switch:hover { opacity: 0.7; }
</style>
