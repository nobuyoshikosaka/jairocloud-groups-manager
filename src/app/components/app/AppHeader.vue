<!--
 Copyright (C) 2026 National Institute of Informatics.
-->

<script setup lang="ts">
const { setLocale } = useI18n()
const { currentUser, isAuthenticated } = useAuth()
const { currentLocale: locale, locales } = useAvailableLocales()

const { navigation: items } = useMenu()
</script>

<template>
  <UHeader
    toggle-side="left" mode="slideover"
    :toggle="{ class: isAuthenticated ? '' : 'invisible' }" :menu="{ side: 'left' }"
  >
    <template #title>
      <AppLogo />
    </template>

    <template #right>
      <UColorModeButton />
      <ULocaleSelect
        v-model="locale" :locales="locales" :ui="{ base: 'h-8 w-30 my-auto' }"
        @update:model-value="setLocale($event as AvailableLocaleCode)"
      />
    </template>

    <template
      v-if="isAuthenticated"
      #body
    >
      <UBadge
        v-if="currentUser?.isSystemAdmin"
        variant="subtle" color="error" :ui="{ base: 'mb-8 w-45' }"
      >
        {{ $t('users.roles.system-admin') }}
      </UBadge>
      <UNavigationMenu :items="items" orientation="vertical" />
    </template>
  </UHeader>
</template>
