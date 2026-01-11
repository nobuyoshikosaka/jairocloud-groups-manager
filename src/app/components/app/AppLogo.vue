<!--
 Copyright (C) 2026 National Institute of Informatics.
-->

<script setup lang="ts">
const { header } = useAppConfig()
const imageError = ref(false)
</script>

<template>
  <img
    v-if="!imageError"
    :src="header.serviceLogo"
    :alt="$t('header.logoAlt')"
    class="h-8 object-cover rounded-full"
    @error="imageError = true"
  >
  <span v-else class="text-lg font-bold">{{ header.serviceAltName }}</span>
</template>
