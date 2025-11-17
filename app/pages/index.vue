<script setup lang="ts">
const isAuthenticated = true

onMounted(() => {
  if (isAuthenticated) {
    navigateTo('/repos')
  }
  else {
    navigateTo('/login')
  }
})
</script>
