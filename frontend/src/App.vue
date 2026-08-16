<template>
  <div id="app-root">
    <AppHeader />
    <main class="container main-content">
      <router-view v-slot="{ Component, route }">
        <Transition name="route" mode="out-in">
          <component :is="Component" :key="route.fullPath" />
        </Transition>
      </router-view>
    </main>
    <AppFooter />
  </div>
</template>

<script setup>
import AppHeader from './components/AppHeader.vue'
import AppFooter from './components/AppFooter.vue'
</script>

<style scoped>
#app-root {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
#app-root > * {
  width: 100%;
}
#app-root .main-content {
  flex: 1;
}
</style>
