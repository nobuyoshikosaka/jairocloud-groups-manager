/*
 * Copyright (C) 2026 National Institute of Informatics.
 */

/**
 * Composable to manage the application menu items
 */

import type { FooterColumn, NavigationMenuItem } from '@nuxt/ui'

export function useMenu() {
  const route = useRoute()
  const { t: $t } = useI18n()
  const { currentUser } = useAuth()

  const items = computed(() => ([
    {
      label: $t('menu.management'),
      children: [
        {
          label: $t('repositories.title'),
          to: '/repositories',
          icon: 'i-lucide-folder',
        },
        {
          label: $t('groups.title'),
          to: '/groups',
          icon: 'i-lucide-users',
        },
        {
          label: $t('users.title'),
          to: '/users',
          icon: 'i-lucide-user',
        },
      ],
    },
    {
      label: $t('menu.other'),
      children: [
        {
          label: $t('history.title'),
          to: '/history',
          icon: 'i-lucide-clock',

        },
        {
          label: $t('cache-groups.title'),
          to: '/cache-groups',
          icon: 'i-lucide-database',
          requiredSystemAdmin: true,
        },
      ],
    }]
  ))

  const navigation = computed<NavigationMenuItem[]>(() => items.value.map(section => ([
    { label: section.label, type: 'label' },
    ...section.children
      .filter(item => !item.requiredSystemAdmin || currentUser.value?.isSystemAdmin)
      .map(item => ({
        label: item.label,
        to: item.to,
        icon: item.icon,
        active: route.path.startsWith(item.to),
      })),
  ])))

  const footer = computed<FooterColumn[]>(() => items.value.map(section => ({
    label: section.label,
    children: section.children
      .filter(item => !item.requiredSystemAdmin || currentUser.value?.isSystemAdmin)
      .map(item => ({
        label: item.label,
        to: item.to,
      })),
  })))

  return { navigation, footer }
}
