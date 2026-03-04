<script setup lang="ts">
const { currentUser } = useAuth()

const { navigation: items } = useMenu()
</script>

<template>
  <UPageAside>
    <template
      v-if="currentUser?.isSystemAdmin"
      #top
    >
      <UBadge variant="subtle" color="error">
        {{ $t('users.roles.system-admin') }}
      </UBadge>
    </template>

    <UNavigationMenu :items="items" orientation="vertical" />
  </UPageAside>
</template>
