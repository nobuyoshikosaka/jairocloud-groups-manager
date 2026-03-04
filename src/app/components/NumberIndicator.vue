<script setup lang="ts">
withDefaults(defineProps<{
  title: string
  number: number
  color?: 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info'
  icon: string
  to?: string
  ui?: {
    body?: string
    icon?: string
  }
}>(), {
  color: 'primary',
  ui: () => ({ body: 'left-0', icon: 'size-10' }),
})
</script>

<template>
  <UPageCard
    :title="title" :description="String(number)" :to="to"
    orientation="horizontal" reverse
    :ui="{
      container: 'grid grid-cols-3 lg:grid-cols-3 gap-2',
      wrapper: 'col-span-2 relative',
      body: `absolute top-1/2 -translate-y-1/2 ${ui?.body}`,
      description: 'text-2xl font-bold text-highlighted',
    }"
  >
    <div class="p-3 m-auto h-16 w-16 rounded-lg" :class="`bg-${color}/10`">
      <UIcon :name="icon" :class="`${ui?.icon} text-${color}`" />
    </div>
  </UPageCard>
</template>
