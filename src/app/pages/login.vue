<script setup lang="ts">
import { description, name as title } from '@@/package.json'

const toast = useToast()

const route = useRoute()

let { next } = route.query
if (Array.isArray(next)) {
  next = next[0]
}
const imageUrl = ref<string | undefined>('/Logo_JAIRO_Cloud-2.png')
const handleImageError = () => {
  imageUrl.value = undefined
}

onMounted(() => {
  const error = route.query.error as string | undefined
  if (!error) return
  const message = ref<string>('')
  if (error == '401') {
    message.value = $t('login.errors.unauthenticated')
  }
  else if (error == '403') {
    message.value = $t('login.errors.unauthorized')
  }
  else {
    message.value = $t('login.errors.unknown')
  }

  toast.add({
    title: message.value,
    color: 'error',
    icon: 'i-lucide-triangle-alert',
    duration: Infinity,
  })
})
</script>

<template>
  <UPage>
    <UPageSection
      :description="description"
      :ui="{ title: 'flex justify-center items-center',
             body: 'flex flex-col justify-center items-center' }"
    >
      <template #title>
        <img
          v-if="imageUrl"
          :src="imageUrl"
          :alt="title"
          class="max-w-full min-w-xl rounded-lg"
          @error="handleImageError"
        >
        <span v-else>{{ title }}</span>
      </template>
      <template #body>
        <EmbeddedDs :next="next as (string | undefined)" />
      </template>
    </UPageSection>
  </UPage>
</template>
