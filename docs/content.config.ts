import { defineCollection, defineContentConfig } from '@nuxt/content'

export default defineContentConfig({
  collections: {
    detailed: defineCollection({
      type: 'page',
      source: '01.detailed/**/*',
    }),
  },
})
