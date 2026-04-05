<script setup>
defineProps({
  fontSize: { type: String, default: '' },
})
</script>

<template>
  <div class="slidev-layout blank" :style="fontSize ? { fontSize } : {}">
    <slot />
  </div>
</template>

<style scoped>
.blank {
  height: 100%;
  padding: 48px;
  background: var(--c-bg);
  position: relative;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.blank.v-center {
  justify-content: center;
}

.blank :deep(img) {
  max-width: 100%;
  max-height: 280px;
  object-fit: contain;
  display: block;
  margin: 0 auto;
  flex-shrink: 1;
}

.blank :deep(li) {
  margin-bottom: 6px;
}

.blank::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--c-primary);
}
</style>
