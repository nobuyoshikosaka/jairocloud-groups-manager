<script setup lang="ts">
const route = useRoute()
const router = useRouter()
const toast = useToast()
const { handleFetchError } = useErrorHandling()

const { currentUser } = useAuth()

const repositoryId = computed(() => route.params.id as string)
const mode = computed(() => (currentUser.value?.isSystemAdmin ? 'edit' : 'view'))

const { defaultData, state } = useRepositoryForm()

const { data: repository, refresh } = useFetch<RepositoryDetail>(
  `/api/repositories/${repositoryId.value}`, {
    method: 'GET',
    server: false,
    default: () => defaultData,
    onResponseError({ response }) {
      switch (response.status) {
        case 403: {
          showError({
            status: 403,
            message: $t('error-page.forbidden.repository-access'),
          })
          break
        }
        case 404: {
          showError({
            status: 404,
            message: $t('error-page.not-found.repository'),
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
    title: $t('repository.number-of-groups'),
    count: repository.value?.groupsCount ?? 0,
    color: 'primary' as const,
    icon: 'i-lucide-users',
    to: `/groups?r=${repositoryId.value}`,
  },
  {
    title: $t('repository.number-of-users'),
    count: repository.value?.usersCount ?? 0,
    color: 'secondary' as const,
    icon: 'i-lucide-user',
    to: `/users?r=${repositoryId.value}`,
  },
])

watch(repository, (newRepo: RepositoryDetail) => {
  if (!newRepo) return

  const date = newRepo.created ? new Date(newRepo.created) : undefined
  Object.assign(state, {
    id: newRepo.id,
    serviceName: newRepo.serviceName,
    serviceUrl: newRepo.serviceUrl?.replace(/^https?:\/\//, '') || defaultData.serviceUrl,
    entityIds: newRepo.entityIds?.length ? [...newRepo.entityIds] : [...defaultData.entityIds],
    spConnectorId: newRepo.spConnectorId || defaultData.spConnectorId,
    active: newRepo.active ?? defaultData.active,
    created: date ? datetimeFormatter.format(date) : defaultData.created,
  })
}, { immediate: true })

const onSubmit = async (data: RepositoryForm) => {
  const { created, spConnectorId, ...payload } = data
  try {
    await $fetch(`/api/repositories/${repositoryId.value}`, {
      method: 'PUT',
      body: payload,
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
              status: 403,
              message: $t('error-page.forbidden.repository-edit'),
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
      description: $t('toast.success.repository-updated.description'),
      color: 'success',
      icon: 'i-lucide-circle-check',
    })

    router.push('/repositories')
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
    :title="repository?.serviceName || ''"
    :description="$t('repositories.description')"
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
            {{ $t('repository.details-title') }}
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

      <RepositoryForm
        v-model="state" :mode="mode"
        @submit="(event) => onSubmit(event.data as RepositoryForm)"
        @cancel="onCancel"
      />
    </UCard>
  </div>
</template>
