<script setup lang="ts">
import { UCheckbox, UIcon } from '#components'

const emit = defineEmits<{
  next: [ExcuteResponse]
  prev: []
}>()

const { t: $t } = useI18n()
const toast = useToast()

const taskId = inject<Ref<string | undefined>>('taskId', ref(undefined))
const selectedRepository = inject<Ref<string | undefined>>('selectedRepository', ref(undefined))
const {
  validationResults,
  missingUsers,
  selectedMissingUsers,
  selectedCount,
  summary,
  executeBulkUpdate,
  toggleSelection,
  useBulkIndicators,
  fetchValidationResults,
} = useValidation({ taskId, selectedRepository })

const { makePageInfo } = useBulk()
const { polling: { interval, maxAttempts } } = useAppConfig()
const isProcessing = ref<boolean>(false)
const { handleFetchError } = useErrorHandling()
const { data: status, execute }
  = await useFetch<BulkProcessingStatus>(`/api/bulk/validate/status/${taskId.value}`,
    {
      method: 'GET',
      lazy: true,
      server: false,
      onResponseError({ response }) { handleFetchError({ response }) },
    },
  )

const pollValidationStatus = async () => {
  for (let index = 0; index < maxAttempts; index++) {
    await execute()
    const st = (status.value?.status)
    if (st === 'SUCCESS') return
    if (st === 'FAILURE') {
      toast.add({
        title: $t('bulk.status.error'),
        description: $t('bulk.validation.failed'),
        color: 'error',
        icon: 'i-lucide-circle-x',
      })
      return
    }

    await new Promise(r => setTimeout(r, interval))
  }
  toast.add({
    title: $t('bulk.status.error'),
    description: $t('bulk.validation.timeout'),
    color: 'error',
    icon: 'i-lucide-circle-x',
  })
}
const data = ref()
const pageInfo = ref()
onMounted(async () => {
  await pollValidationStatus()
  data.value = await fetchValidationResults(`/api/bulk/validate/result/${taskId.value}`)
  pageInfo.value = makePageInfo(data)
})

const offset = computed(() => (data.value?.offset ?? 1))
const canProceed = computed(() => summary.value.error === 0)

const handleNext = async () => {
  if (!canProceed.value) return

  isProcessing.value = true

  try {
    const { taskId, historyId } = await executeBulkUpdate(`/api/bulk/execute`)
    if (historyId) {
      emit('next', { taskId, historyId })
    }
  }
  catch {
    useToast().add({
      title: $t('bulk.status.error'),
      description: $t('bulk.execute.failed'),
      color: 'error',
      icon: 'i-lucide-circle-x',
    })
  }
  finally {
    isProcessing.value = false
  }
}

const handlePrevious = () => {
  emit('prev')
}

const selectAllMissingUsers = () => {
  selectedMissingUsers.value = Object.fromEntries(
    missingUsers.value.map(user => [user.id, true]),
  )
}

const deselectAllMissingUsers = () => {
  selectedMissingUsers.value = {}
}

const totalCount = computed(() => data.value.total)
const indicators = useBulkIndicators
</script>

<template>
  <div class="space-y-6">
    <UAlert
      v-if="summary.error > 0" color="error" icon="i-lucide-alert-circle"
      :as="$t('bulk.validation.error')" :description="$t('bulk.validation.error-detail')"
    />

    <div class="sticky top-0 z-10 bg-background flex items-center justify-between gap-4">
      <NumberIndicator
        v-for="indicator in indicators"
        :key="indicator.key"
        :title="indicator.title"
        :icon="indicator.icon"
        :number="indicator.number"
        :color="indicator.color"
      />
    </div>

    <BulkUserTable
      :data="validationResults" :total-count="totalCount"
      :page-info="pageInfo" :offset="offset"
      :title="$t('bulk.validation.results')"
    />

    <div v-if="missingUsers.length > 0" variant="outline">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <h3 class="font-semibold">
            {{ $t('bulk.missing_user') }} ({{ missingUsers.length }})
          </h3>
        </div>
        <div class="flex items-center gap-2">
          <UButton
            :label="$t('bulk.select_all')" size="xs" color="neutral" variant="outline"
            @click="selectAllMissingUsers"
          />
          <UButton
            :label="$t('bulk.deselect_all')" size="xs" color="neutral" variant="outline"
            @click="deselectAllMissingUsers"
          />
        </div>
      </div>
      <p class="text-sm text-muted">
        {{ $t('bulk.missing-user.select') }}
      </p>

      <UAlert
        v-if="selectedCount > 0" color="error" icon="i-lucide-alert-triangle"
        :title="$t('bulk.missing-user.confirm')"
        :description="
          $t('bulk.missing-user.confirm_desc', { count: selectedCount })
        "
        class="mb-4" variant="solid"
      />

      <div class="space-y-2">
        <div
          v-for="user in missingUsers" :key="user.id" class="flex items-center gap-3 p-3
            rounded-lg border cursor-pointer hover:bg-elevated/50 transition-colors"
          :class="selectedMissingUsers[user.id]
            ? 'border-error bg-error/5' : 'border-default'"
          @click="toggleSelection(user.id)"
        >
          <UCheckbox
            :model-value="selectedMissingUsers[user.id]"
            @update:model-value="toggleSelection(user.id)"
          />
          <div class="flex-1">
            <p class="font-medium">
              {{ user.name }}
            </p>
            <p class="text-sm text-muted font-mono">
              {{ user.eppn }}
            </p>
          </div>
          <div class="flex flex-col text-sm">
            <div v-for="group in user.groups" :key="group">
              <span class="font-mono text-sm">{{ group }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="flex justify-between">
      <UButton
        :label="$t('button.back')" color="neutral" variant="outline" icon="i-lucide-arrow-left"
        :disabled="isProcessing" @click="handlePrevious"
      />
      <UButton
        :label="$t('bulk.upload.execute')" icon="i-lucide-arrow-right" trailing
        :loading="isProcessing"
        :disabled="!canProceed || isProcessing" @click="handleNext"
      >
        <template v-if="!canProceed" #trailing>
          <UTooltip :text="$t('bulk.validation.fix_error')">
            <UIcon name="i-lucide-alert-circle" class="size-4" />
          </UTooltip>
        </template>
      </UButton>
    </div>
  </div>
</template>
