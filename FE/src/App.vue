<template>
  <AppToast :breakpoints="toastBreakpoints" />
  <RouterView />
</template>

<script setup lang="ts">
const toastBreakpoints = {
  '640px': {
    width: 'calc(100vw - 2rem)',
    left: '1rem',
    right: '1rem',
  },
}
</script>
