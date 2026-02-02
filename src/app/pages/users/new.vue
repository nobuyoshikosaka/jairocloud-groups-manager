<script setup lang="ts">
import { FetchError } from 'ofetch'

const toast = useToast()

const { stateAsCreate: state } = useUserForm()

const onSubmit = async (data: UserCreatePayload) => {
  try {
    await $fetch('/api/users', {
      method: 'POST',
      body: data,
    })

    toast.add({
      title: $t('success.creation.title'),
      description: $t('success.user.created-description'),
      color: 'success',
    })
    await navigateTo('/users')
  }
  catch (error) {
    if (error instanceof FetchError) {
      if (error.status === 400) {
        toast.add({
          title: $t('error.validation.title'),
          description: error?.data?.message ?? $t('error.validation.description'),
          color: 'error',
        })
      }
      else if (error.status === 409) {
        toast.add({
          title: $t('user.error.conflict-title'),
          description: $t('user.error.conflict-description'),
          color: 'error',
        })
      }
      else {
        toast.add({
          title: $t('error.server.title'),
          description: $t('error.server.description'),
          color: 'error',
        })
      }
    }
    else {
      toast.add({
        title: $t('error.unexpected.title'),
        description: $t('error.unexpected.description'),
        color: 'error',
      })
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
