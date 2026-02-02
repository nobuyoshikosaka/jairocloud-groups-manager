<script setup lang="ts">
import { FetchError } from 'ofetch'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const groupId = computed(() => route.params.id as string)
const mode = 'edit'

const { defaultData, defaultForm, state } = useGroupForm()

const { data: group, refresh } = useFetch<GroupDetail>(
  `/api/groups/${groupId.value}`, {
    method: 'GET',
    server: false,
    default: () => defaultData,
    onResponseError({ response }) {
      if (response.status === 404) {
        showError({
          statusCode: 404,
          statusMessage: $t('group.error.not-found'),
        })
      }
      toast.add({
        title: $t('error.server.title'),
        description: $t('error.server.description'),
        color: 'error',
      })
    },
  },
)

const indicators = computed(() => [
  {
    title: $t('group.number-of-users'),
    count: group.value?.usersCount ?? defaultData.usersCount,
    color: 'primary' as const,
    icon: 'i-lucide-user',
    to: `/users?g=${groupId.value}`,
  },
])

watch(group, (newGroup: GroupDetail) => {
  if (!newGroup) return

  const created = newGroup.created ? new Date(newGroup.created) : undefined
  Object.assign(state, {
    id: newGroup.id,
    displayName: newGroup.displayName || defaultForm.displayName,
    description: newGroup.description || defaultForm.description,
    repository: newGroup.repository
      ? { id: newGroup.repository.id, label: newGroup.repository.serviceName }
      : defaultForm.repository,
    public: newGroup.public ?? defaultForm.public,
    memberListVisibility: newGroup.memberListVisibility || defaultForm.memberListVisibility,
    created: created ? dateFormatter.format(created) : defaultForm.created,
  } as GroupUpdateForm)
}, { immediate: true })

const onSubmit = async (data: GroupUpdatePayload) => {
  try {
    await $fetch(`/api/groups/${groupId.value}`, {
      method: 'PUT',
      body: data,
    })

    toast.add({
      title: $t('success.updated.title'),
      description: $t('success.group.updated-description'),
      color: 'success',
    })
    await router.replace({ name: 'groups-id', params: { id: groupId.value } })
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
          title: $t('error.conflict.title'),
          description: $t('error.conflict.description'),
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

const onCancel = () => {
  refresh()

  if (import.meta.client) {
    nextTick(() => {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    })
  }
}
</script>

<template>
  <UPageHeader
    :title="group?.displayName || ''"
    :description="$t('groups.description')"
    :ui="{ root: 'py-2 mb-6', description: 'mt-4' }"
  />

  <div class="max-w-210 m-auto">
    <div class="grid grid-cols-2 gap-4 mb-6">
      <NumberIndicator
        v-for="(indicator, index) in indicators"
        :key="index" :title="indicator.title" :to="indicator.to"
        :number="indicator.count" :color="indicator.color" :icon="indicator.icon"
      />
    </div>

    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h2 class="text-2xl font-semibold">
            {{ $t('group.details-title') }}
          </h2>

          <UButton
            v-if="mode === 'edit'"
            :label="$t('button.delete')"
            icon="i-lucide-trash"
            variant="subtle"
            color="error"
          />
        </div>
      </template>

      <GroupForm
        v-model="state" :mode="mode"
        @submit="onSubmit" @cancel="onCancel"
      />
    </UCard>
  </div>
</template>
