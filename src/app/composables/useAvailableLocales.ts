/*
 * Copyright (C) 2026 National Institute of Informatics.
 */

import * as uiLocales from '@nuxt/ui/locale'

import type { LocaleObject } from '@nuxtjs/i18n'

type AvailableLocalesObject = ReturnType<typeof useI18n>['locales']
export type AvailableLocaleCode
  = AvailableLocalesObject extends globalThis.ComputedRef<LocaleObject<infer V>[]> ? V : never

export function useAvailableLocales() {
  const { locale: currentLocaleReference, locales: availableLocales } = useI18n()

  const locales = computed(() =>
    Object.values(uiLocales).filter((locale) => {
      return availableLocales.value.some(l => l.code === locale.code)
    }),
  )

  const currentLocale = ref(currentLocaleReference.value)
  watch(currentLocaleReference, (newLocale) => {
    currentLocale.value = newLocale
  })

  return {
    currentLocale,
    locales,
  }
}
