<script setup lang="ts">
import type { FetchError } from 'ofetch'

const toast = useToast()
const { currentUser } = useAuth()
const { stateAsCreate: state } = useRepositoryForm()

const { handleFetchError } = useErrorHandling()
const onSubmit = async (data: RepositoryCreatePayload) => {
  try {
    await $fetch('/api/repositories', {
      method: 'POST',
      body: data,
    })

    toast.add({
      title: $t('toast.success.creation.title'),
      description: $t('toast.success.repository-created.description'),
      color: 'success',
      icon: 'i-lucide-circle-check',
    })
    await navigateTo('/repositories')
  }
  catch (error) {
    switch ((error as FetchError).status) {
      case 400: {
        toast.add({
          title: $t('toast.error.validation.title'),
          description: $t('toast.error.validation.description'),
          color: 'error',
          icon: 'i-lucide-circle-x',
        })
        break
      }
      case 403: {
        showError({
          status: 403,
          message: $t('error-page.forbidden.repository-create'),
        })
        break
      }
      case 409: {
        toast.add({
          title: $t('toast.error.conflict.title'),
          description: $t('toast.error.conflict.description'),
          color: 'error',
          icon: 'i-lucide-circle-x',
        })
        break
      }
      default: {
        handleFetchError({ response: (error as FetchError).response! })
        break
      }
    }
  }
}

onMounted(() => {
  if (!currentUser.value?.isSystemAdmin) {
    showError({
      status: 403,
      message: $t('error-page.forbidden.repository-create'),
    })
  }
})
</script>

<template>
  <UPageHeader
    :title="$t('repository.new-title')"
    :description="$t('repository.new-description')"
    :ui="{ root: 'py-2 mb-6', description: 'mt-4' }"
  />

  <div class="max-w-210 m-auto">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h2 class="text-2xl font-semibold">
            {{ $t('repository.details-title') }}
          </h2>
          <div />
        </div>
      </template>

      <RepositoryForm
        v-model="state"
        mode="new"
        @submit="onSubmit"
        @cancel="() => navigateTo('/repositories')"
      />
    </UCard>
  </div>
</template>
