<script setup lang="ts">
const route = useRoute()
const toast = useToast()

const userId = computed(() => route.params.id as string)
const mode = computed<'view' | 'edit'>(() => 'view')

const { defaultData, defaultForm, state } = useUserForm()

const { data: user } = useFetch<UserDetail>(
  `/api/users/${userId.value}`, {
    method: 'GET',
    server: false,
    default: () => defaultData,
    onResponseError({ response }) {
      if (response.status === 404) {
        showError({
          statusCode: 404,
          statusMessage: $t('user.error.not-found'),
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

watch(user, (newUser: UserDetail) => {
  if (!newUser) return

  const created = newUser.created ? new Date(newUser.created) : undefined
  const lastModified = newUser.lastModified ? new Date(newUser.lastModified) : undefined
  Object.assign(state, {
    id: newUser.id,
    emails: newUser.emails?.length ? newUser.emails : defaultForm.emails,
    eppns: newUser.eppns?.length ? newUser.eppns : defaultForm.eppns,
    userName: newUser.userName || defaultForm.userName,
    preferredLanguage: newUser.preferredLanguage || defaultForm.preferredLanguage,
    isSystemAdmin: newUser.isSystemAdmin || defaultForm.isSystemAdmin,
    repositoryRoles: newUser.repositoryRoles?.length
      ? newUser.repositoryRoles?.map(role => ({
          id: role.id,
          label: role.serviceName,
          userRole: role.userRole,
        }))
      : defaultForm.repositoryRoles,
    groups: newUser.groups?.length
      ? newUser.groups?.map(group => ({ id: group.id, label: group.displayName }))
      : defaultForm.groups,
    created: created ? dateFormatter.format(created) : defaultForm.created,
    lastModified: lastModified ? dateFormatter.format(lastModified) : defaultForm.lastModified,
  } as UserForm)
})
</script>

<template>
  <UPageHeader
    :title="user?.userName || ''"
    :description="$t('users.description')"
    :ui="{ root: 'py-2 mb-6', description: 'mt-4' }"
  />

  <div class="max-w-210 m-auto">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h2 class="text-2xl font-semibold">
            {{ $t('user.details-title') }}
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

      <UserForm v-model="state" :mode="mode" />
    </UCard>
  </div>
</template>
