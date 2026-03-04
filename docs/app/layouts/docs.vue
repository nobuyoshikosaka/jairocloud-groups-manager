<!-- eslint-disable unicorn/prevent-abbreviations -->
<script setup lang="ts">
import { ja } from '@nuxt/ui/locale'

const { navigation, collection } = await useNavigation()
provide('collection', collection)
provide('navigation', navigation)

const { data: files } = useLazyAsyncData(() => `search-${collection.value}`, () => {
  return queryCollectionSearchSections(collection.value)
}, {
  watch: [collection],
},
)
</script>

<template>
  <UApp :locale="ja">
    <AppHeader />

    <UMain>
      <UContainer>
        <UPage>
          <template #left>
            <UPageAside>
              <template #top>
                <UContentSearchButton :collapsed="false" :kbds="['/']" />
              </template>

              <UContentNavigation :navigation="navigation" highlight />
            </UPageAside>
          </template>

          <slot />
        </UPage>
      </UContainer>
    </UMain>

    <LazyUContentSearch
      shortcut="/" :files="files" :navigation="navigation"
      :fuse="{ resultLimit: 42 }"
    />
  </UApp>
</template>
