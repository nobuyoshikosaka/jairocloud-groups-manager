<script setup lang="ts">
import { FetchError } from 'ofetch'

const { currentUser } = useAuth()
const { stateAsCreate: state } = useRepositoryForm()

const onSubmit = async (data: RepositoryCreatePayload) => {
  const toast = useToast()
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
    if (error instanceof FetchError) {
      if (error.status === 400) {
        toast.add({
          title: $t('toast.error.validation.title'),
          description: error?.data?.message ?? $t('toast.error.validation.description'),
          color: 'error',
          icon: 'i-lucide-circle-x',
        })
      }
      else if (error.status === 409) {
        toast.add({
          title: $t('toast.error.conflict.title'),
          description: $t('toast.error.conflict.description'),
          color: 'error',
          icon: 'i-lucide-circle-x',
        })
      }
      else {
        toast.add({
          title: $t('toast.error.server.title'),
          description: $t('toast.error.server.description'),
          color: 'error',
          icon: 'i-lucide-circle-x',
        })
      }
    }
    else {
      toast.add({
        title: $t('toast.error.unexpected.title'),
        description: $t('toast.error.unexpected.description'),
        color: 'error',
        icon: 'i-lucide-circle-x',
      })
    }
  }
}

onMounted(() => {
  if (!currentUser.value?.isSystemAdmin) {
    showError({
      status: 403,
      statusText: $t('repository.error-page.forbidden'),
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
