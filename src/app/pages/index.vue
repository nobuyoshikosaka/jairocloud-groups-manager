<script setup lang="ts">
import { name as title, description } from '@@/package.json'
</script>

<template>
  <div>
    <UPageHero
      :title="title"
      :description="description"
    />
  </div>
</template>
