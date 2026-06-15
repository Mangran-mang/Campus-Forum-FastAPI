<template>
  <div id="app-root">
    <AppHeader />
    <main class="container" style="padding-top: 80px; padding-bottom: 40px;">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import AppHeader from './components/AppHeader.vue'
</script>
