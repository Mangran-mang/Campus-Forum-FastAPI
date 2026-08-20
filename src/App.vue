<template>
  <div id="app-root">
    <!-- 星空背景层（三层不同速度的星星，缓慢上移） -->
    <div id="stars"></div>
    <div id="stars2"></div>
    <div id="stars3"></div>
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
/* flex column 下子元素默认 align-items: stretch 自动占满交叉轴宽度。
   注意：不能写 #app-root > * { width: 100% } —— 会把 #stars 等 1px 固定元素
   拉伸成整行宽度，导致 box-shadow 阴影从点变成横线（已踩坑）。
   .container 自身已带 width: 100%，flex 子项靠它保持 100% 宽度。 */
#app-root .main-content {
  flex: 1;
  position: relative;
  z-index: 1;
}
.app-footer {
  position: relative;
  z-index: 1;
}
</style>
