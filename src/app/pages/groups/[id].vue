<script setup lang="ts">
const route = useRoute()
const router = useRouter()
const toast = useToast()

const groupId = computed(() => route.params.id as string)
const mode = 'edit'

const { defaultData, defaultForm, state } = useGroupForm()

const { handleFetchError } = useErrorHandling()
const { data: group, refresh } = useFetch<GroupDetail>(
  `/api/groups/${groupId.value}`, {
    method: 'GET',
    server: false,
    default: () => defaultData,
    onResponseError({ response }) {
      switch (response.status) {
        case 403: {
          showError({
            status: 403,
            message: $t('error-page.forbidden.group-access'),
          })
          break
        }
        case 404: {
          showError({
            status: 404,
            message: $t('error-page.not-found.group'),
          })
          break
        }
        default: {
          handleFetchError({ response })
          break
        }
      }
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
      ? { value: newGroup.repository.id, label: newGroup.repository.serviceName }
      : defaultForm.repository,
    public: newGroup.public ?? defaultForm.public,
    memberListVisibility: newGroup.memberListVisibility || defaultForm.memberListVisibility,
    created: created ? dateFormatter.format(created) : defaultForm.created,
  } as GroupUpdateForm)
}, { immediate: true })

const onSubmit = async (data: GroupUpdateForm) => {
  const { id, repository, created, ...payload } = data

  try {
    await $fetch(`/api/groups/${groupId.value}`, {
      method: 'PUT',
      body: payload as GroupUpdatePayload,
      onResponseError: ({ response }) => {
        switch (response.status) {
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
              statusCode: 403,
              message: $t('error-page.forbidden.group-edit'),
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
            handleFetchError({ response })
            break
          }
        }
      },
    })

    toast.add({
      title: $t('toast.success.updated.title'),
      description: $t('toast.success.group-updated.description'),
      color: 'success',
      icon: 'i-lucide-circle-check',
    })
    await router.replace({ name: 'groups-id', params: { id: groupId.value } })
  }
  catch {
  // Already handled in onResponseError
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
        @submit="(event) => onSubmit(event.data as GroupUpdateForm)" @cancel="onCancel"
      />
    </UCard>
  </div>
</template>
