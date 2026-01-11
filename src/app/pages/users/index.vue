<script setup lang="ts">
import type { ButtonProps, DropdownMenuItem } from '@nuxt/ui'

const isEmpty = ref(false)
const creationButtons = computed<ButtonProps[]>(() => [
  {
    icon: 'i-lucide-user-plus',
    label: $t('button.create-new'),
    to: '/users/new',
    color: 'primary',
    variant: 'solid',
  },
  {
    icon: 'i-lucide-file-up',
    label: $t('button.upload-users'),
    to: '/upload',
    color: 'primary',
    variant: 'solid',
  },
])
const emptyActions = computed<ButtonProps[]>(() => [
  ...creationButtons.value,
  {
    icon: 'i-lucide-refresh-cw',
    label: $t('button.reload'),
    color: 'neutral',
    variant: 'subtle',
    onClick: () => {
      // TODO: Placeholder for reload action
    },
  },
])

const selectedUsers = ref<{ id: string, userName: string }[]>([])

const selectedUsersActions = computed<DropdownMenuItem[]>(() => [
  {
    icon: 'i-lucide-download',
    label: $t('users.button.selected-users-export'),
    onSelect() {
      // Export selected users
    },
  },
  {
    type: 'separator' as const,
  },
  {
    icon: 'i-lucide-user-plus',
    label: $t('users.button.selected-users-add-to-group'),
    color: 'neutral',
    onSelect() {
      // Open add users modal
    },
  },
  {
    icon: 'i-lucide-user-minus',
    label: $t('users.button.selected-users-remove-from-group'),
    color: 'error',
    onSelect() {
      // Open remove users modal
    },
  },
])

const searchTerm = ref('')
</script>

<template>
  <div>
    <UPageHeader
      :title="$t('users.list.title')"
      :description="$t('users.description')"
      :ui="{ root: 'py-2', description: 'mt-2' }"
    />
  </div>

  <UEmpty
    v-if="isEmpty"
    :title="$t('users.list.no-users-title')"
    :description="$t('users.list.no-users-description')"
    :actions="emptyActions"
  />
  <dev v-else>
    <div class="flex justify-between items-center my-4">
      <div class="flex space-x-2">
        <UButton
          v-for="(button, index) in creationButtons"
          :key="index"
          :icon="button.icon" :label="button.label"
          :to="button.to" :color="button.color" :variant="button.variant"
          :ui="{ base: 'gap-1' }"
        />
      </div>

      <UDropdownMenu :items="selectedUsersActions">
        <UButton
          :label="$t('users.button.selected-users-actions')"
          color="warning" variant="subtle"
          :ui="{ base: 'gap-1' }"
          :disabled="selectedUsers.length === 0"
        />
      </UDropdownMenu>
    </div>

    <div class="flex justify-between mb-4">
      <div>
        <UInput
          v-model="searchTerm" :placeholder="$t('users.list.search-placeholder')"
          icon="i-lucide-search" :ui="{ base: 'w-sm' }"
        >
          <template #trailing>
            <UKbd value="enter" />
          </template>
        </UInput>
      </div>
    </div>

    <UTable :data="[]" />
  </dev>
</template>
