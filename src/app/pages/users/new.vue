<script setup lang="ts">
import type { FetchError } from 'ofetch'

const toast = useToast()

const { stateAsCreate: state } = useUserForm()

const { handleFetchError } = useErrorHandling()
const onSubmit = async (data: UserCreatePayload) => {
  try {
    await $fetch('/api/users', {
      method: 'POST',
      body: data,
    })

    toast.add({
      title: $t('toast.success.creation.title'),
      description: $t('toast.success.user-created.description'),
      color: 'success',
      icon: 'i-lucide-circle-check',
    })
    await navigateTo('/users')
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
          message: $t('error-page.forbidden.user-create'),
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
</script>

<template>
  <UPageHeader
    :title="$t('user.new-title')"
    :description="$t('user.new-description')"
    :ui="{ root: 'py-2 mb-6', description: 'mt-4' }"
  />

  <div class="max-w-210 m-auto">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h2 class="text-2xl font-semibold">
            {{ $t('user.details-title') }}
          </h2>
          <div />
        </div>
      </template>

      <UserForm
        v-model="state"
        mode="new"
        @submit="onSubmit"
        @cancel="() => navigateTo('/users')"
      />
    </UCard>
  </div>
</template>
