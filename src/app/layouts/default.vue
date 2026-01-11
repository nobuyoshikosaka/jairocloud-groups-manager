<!--
 Copyright (C) 2026 National Institute of Informatics.
-->
<script setup lang="ts">
const { isAuthenticated } = useAuth()
</script>

<template>
  <UApp :toaster="{ position: 'top-center' }">
    <AppHeader />

    <UMain>
      <UContainer>
        <UPage :key="String(isAuthenticated)">
          <template
            v-if="isAuthenticated"
            #left
          >
            <AppSideMenu />
          </template>

          <UPageBody>
            <slot />
          </UPageBody>
        </UPage>
      </UContainer>
    </UMain>

    <AppFooter />
  </UApp>
</template>
