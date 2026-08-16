<template>
  <footer class="app-footer">
    <div class="container footer-inner">
      <span class="footer-copy">© {{ year }} 郑财论坛</span>
      <a
        class="footer-beian"
        href="https://beian.miit.gov.cn/"
        target="_blank"
        rel="noopener noreferrer"
      >豫ICP备2026030629号</a>
      <a
        class="footer-beian"
        href="https://beian.mps.gov.cn/#/query/webSearch"
        target="_blank"
        rel="noopener noreferrer"
      >豫公网安备41018102001534号</a>
    </div>
  </footer>
</template>

<script setup>
const year = new Date().getFullYear()
</script>

<style scoped>
.app-footer {
  border-top: 2px solid var(--text);
  background: #fffdf5;
  padding: 16px 0;
  margin-top: 32px;
}
.footer-inner {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--text-muted);
}
.footer-copy {
  color: var(--text-muted);
}
.footer-beian {
  color: var(--text-muted);
  text-decoration: none;
  transition: color 0.2s ease;
}
.footer-beian:hover {
  color: var(--primary);
  text-decoration: underline;
  background-image: none;
}

@media (max-width: 768px) {
  .footer-inner {
    gap: 6px;
    font-size: 11px;
  }
}
</style>
