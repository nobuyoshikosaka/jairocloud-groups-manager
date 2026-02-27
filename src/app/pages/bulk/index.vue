<script setup lang="ts">
const { currentStep, items } = useBulk()
const selectedRepository = ref<string | undefined>(undefined)
provide('selectedRepository', selectedRepository)
const taskId = ref<string | undefined>(undefined)
provide('taskId', taskId)

const onValidateComplete = (taskIdValue: string) => {
  taskId.value = taskIdValue
  currentStep.value = 'validate'
}

const onUploadComplete = ({ taskId: taskIdValue, historyId }: ExcuteResponse) => {
  taskId.value = taskIdValue
  navigateTo(`/bulk/${historyId}?taskId=${taskIdValue}`)
}

const goBackToUpload = () => {
  currentStep.value = 'upload'
}
</script>

<template>
  <div>
    <UPageHeader
      :title="$t('bulk.title')"
      :description="$t('bulk.description')"
      :ui="{ root: 'py-2', description: 'mt-2' }"
    />

    <UStepper
      ref="stepper"
      v-model="currentStep"
      :items="items"
      disabled
      orientation="horizontal"
      class="my-10"
    />

    <BulkValidationStep
      v-if="currentStep === 'validate'"
      @next="onUploadComplete"
      @prev="goBackToUpload"
    />
    <BulkUploadStep
      v-else
      @next="onValidateComplete"
    />
  </div>
</template>
