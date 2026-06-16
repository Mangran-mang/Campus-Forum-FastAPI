<template>
  <div id="app-root">
    <AppHeader />
    <main class="container main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import AppHeader from './components/AppHeader.vue'
</script>
