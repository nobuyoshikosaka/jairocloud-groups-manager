<script setup lang="ts">
import type { FormErrorEvent, FormSubmitEvent } from '@nuxt/ui'

interface Properties {
  modelValue: GroupCreateForm | GroupUpdateForm
  mode: FormMode
}
const properties = defineProps<Properties>()

const emit = defineEmits<{
  'update:modelValue': [value: GroupCreateForm | GroupUpdateForm]
  'submit': [data: GroupCreatePayload | GroupUpdatePayload]
  'error': [event: FormErrorEvent]
  'cancel': []
}>()

const { table: { pageSize } } = useAppConfig()
const { schema, getMaxIdLength } = useGroupSchema(() => properties.mode)
const { handleFormError } = useFormError()

const state = computed({
  get: () => properties.modelValue,
  set: value => emit('update:modelValue', value),
})
const stateAsCreate = computed(() => properties.modelValue as GroupCreateForm)
const stateAsEdit = computed(() => properties.modelValue as GroupUpdateForm)

const toast = useToast()
const { copy } = useClipboard()
const copyId = (id: string) => {
  copy(id)
  toast.add({
    title: $t('toast.success.title'),
    description: $t('toast.success.copy-group-id.description'),
    color: 'success',
    icon: 'i-lucide-circle-check',
  })
}

const repositorySelect = useTemplateRef('repositorySelect')
const {
  items: repositoryNames,
  searchTerm: repoSearchTerm,
  status: repoSearchStatus,
  onOpen: onRepoOpen,
  setupInfiniteScroll: setupRepoScroll,
} = useSelectMenuInfiniteScroll<RepositorySummary>({
  url: '/api/repositories',
  limit: pageSize.repositories[0],
  transform: (repository: RepositorySummary) => ({
    label: repository.serviceName,
    value: repository.id,
  }),
})
setupRepoScroll(repositorySelect)

const maxIdLength = computed(() => getMaxIdLength(state.value.repository.id),
)

const form = useTemplateRef('form')
const onSubmit = (event: FormSubmitEvent<GroupCreatePayload | GroupUpdatePayload>) => {
  emit('submit', event.data)
}
const onError = (event: FormErrorEvent) => {
  handleFormError(event)
  emit('error', event)
}
const onCancel = () => {
  form.value?.clear()
  emit('cancel')
}
</script>

<template>
  <UForm
    ref="form"
    :schema="schema" :state="state" class="space-y-6"
    @submit="(event) => onSubmit(
      event as FormSubmitEvent<GroupCreatePayload | GroupUpdatePayload>,
    )"
    @error="onError"
  >
    <h3 class="text-lg font-semibold">
      {{ $t('group.details-basic-section') }}
    </h3>

    <UFormField
      name="repository" :error-pattern="/repository\..*/"
      :label="$t('group.repository')"
      :description="$t('group.repository-description')"
      :ui="{ wrapper: 'mb-2' }" :required="mode !== 'view'"
    >
      <USelectMenu
        ref="repositorySelect"
        v-model="state.repository.id"
        :search-term="repoSearchTerm" value-key="value" size="xl"
        :placeholder="$t('group.placeholder.repository')"
        :items="repositoryNames" :loading="repoSearchStatus === 'pending'" ignore-filter
        :ui="{ base: 'w-full' }" :disabled="mode !== 'new'"
        @update:open="onRepoOpen"
      />
    </UFormField>

    <UFormField
      :label="$t('group.id')" :ui="{ wrapper: 'mb-2' }"
      :required="mode === 'new'"
    >
      <div
        v-if="mode !== 'new'"
        class="f-ful mt-1 px-3 py-2 text-base"
      >
        {{ stateAsEdit.id || '-' }}
        <UButton
          icon="i-lucide-copy" variant="ghost" color="neutral"
          :ui="{ base: 'p-0 ml-2', leadingIcon: 'size-3' }"
          @click="() => copyId(stateAsEdit.id)"
        />
      </div>
      <!-- eslint-disable vue/attribute-hyphenation -->
      <UInput
        v-else
        v-model="stateAsCreate.userDefinedId" size="xl"
        :ui="{ root: 'w-full' }"
        :placeholder="$t('group.placeholder.id')"
        :maxLength="maxIdLength"
      >
        <!-- eslint-enable vue/attribute-hyphenation -->
        <template #trailing>
          {{ stateAsCreate.userDefinedId.length }} / {{ maxIdLength }}
        </template>
      </UInput>
    </UFormField>

    <UFormField
      name="displayName"
      :label="$t('group.display-name')"
      :description="$t('group.display-name-description')"
      :ui="{ wrapper: 'mb-2' }" :required="mode !== 'view'"
    >
      <UInput
        v-model="state.displayName" size="xl"
        :placeholder="$t('group.placeholder.display-name')"
        :ui="{ root: 'w-full' }" :disabled="mode === 'view'"
      />
    </UFormField>

    <UFormField
      name="description"
      :label="$t('group.description')"
      :description="$t('group.description-description')"
      :ui="{ wrapper: 'mb-2' }"
    >
      <UTextarea
        v-model="state.description" size="xl"
        :ui="{ root: 'w-full' }" :disabled="mode === 'view'" autoresize
      />
    </UFormField>

    <UFormField
      v-if="mode !== 'new'"
      :label="$t('user.created')" :ui="{ wrapper: 'mb-2' }"
    >
      <div class="f-ful mt-1 px-3 py-2 text-base">
        {{ stateAsEdit.created || '-' }}
      </div>
    </UFormField>

    <div v-if="mode !== 'view'" class="flex justify-between items-center mt-2">
      <UButton
        :label="$t('button.cancel')"
        icon="i-lucide-ban" color="neutral" variant="subtle"
        @click="onCancel"
      />
      <UButton
        v-if="mode === 'new'"
        :label="$t('button.save')"
        type="submit" icon="i-lucide-save" color="info" variant="subtle"
      />
      <UButton
        v-else
        :label="$t('button.update')"
        type="submit" icon="i-lucide-save" color="info" variant="subtle"
      />
    </div>
  </UForm>
</template>
