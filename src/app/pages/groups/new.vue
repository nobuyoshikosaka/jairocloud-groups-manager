<script setup lang="ts">
import { FetchError } from 'ofetch'

const { stateAsCreate: state } = useGroupForm()

const onSubmit = async (data: GroupCreatePayload) => {
  const toast = useToast()
  try {
    await $fetch('/api/groups', {
      method: 'POST',
      body: data,
    })

    toast.add({
      title: $t('success.creation.title'),
      description: $t('success.group.created-description'),
      color: 'success',
    })
    await navigateTo('/groups')
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
    :title="$t('group.new-title')"
    :description="$t('group.new-description')"
    :ui="{ root: 'py-2 mb-6', description: 'mt-4' }"
  />

  <div class="max-w-210 m-auto">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h2 class="text-2xl font-semibold">
            {{ $t('group.details-title') }}
          </h2>
          <div />
        </div>
      </template>

      <GroupForm
        :model-value="state"
        mode="new"
        @submit="(data) => onSubmit(data as GroupCreatePayload)"
        @cancel="() => navigateTo('/groups')"
      />
    </UCard>
  </div>
</template>
