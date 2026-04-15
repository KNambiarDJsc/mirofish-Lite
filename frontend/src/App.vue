<template>
  <router-view />
</template>

<script setup>
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  background: #0A0A0A;
  color: #FFFFFF;
  font-family: 'Space Grotesk', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
}

::-webkit-scrollbar       { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #0A0A0A; }
::-webkit-scrollbar-thumb { background: #1E1E1E; border-radius: 0; }

button { font-family: inherit; }

input, textarea, select {
  font-family: inherit;
  color-scheme: dark;
}

a { color: inherit; text-decoration: none; }
</style>
