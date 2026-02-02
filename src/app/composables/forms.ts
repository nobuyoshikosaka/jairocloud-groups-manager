import * as z from 'zod'

import type { MaybeRefOrGetter } from 'vue'
import type { FormErrorEvent } from '@nuxt/ui'

export type FormMode = 'new' | 'edit' | 'view'

const hasViewportReference = (
  object: unknown,
): object is { viewportRef: Ref<HTMLDivElement | null> } => {
  return (
    typeof object === 'object'
    && object !== null
    && 'viewportRef' in object
  )
}

const useSelectMenuInfiniteScroll = <T>(
  options: UseSelectMenuInfiniteScrollOptions<T>,
): UseSelectMenuInfiniteScrollReturn => {
  const {
    url,
    limit = 20,
    transform,
    debounce = 300,
    scrollDistance = 10,
    params: parameters = {},
  } = options

  const page = ref(0)
  const hasMore = ref(true)

  const searchTerm = ref('')
  const searchTermDebounced = refDebounced(searchTerm, debounce)

  const items = ref<Array<{ label: string, value: string }>>([])

  const { data, status, execute } = useFetch<SearchResult<T>>(url, {
    params: computed(() => ({
      q: searchTermDebounced.value || undefined,
      p: page.value,
      l: limit,
      ...parameters,
    })),
    lazy: true,
    immediate: false,
  })

  watch(data, (newData) => {
    if (!newData) return

    const transformedItems = newData.resources.map(element => transform(element))
    items.value = page.value === 1 ? transformedItems : [...items.value, ...transformedItems]

    hasMore.value = items.value.length < newData.total
  })

  watch(searchTermDebounced, () => {
    page.value = 1
    hasMore.value = true
    execute()
  })

  const onOpen = (isOpen: boolean) => {
    if (isOpen && items.value.length === 0) {
      execute()
    }
  }

  const setupInfiniteScroll = (
    selectMenuReference: Ref<unknown>,
  ) => {
    onMounted(() => {
      // eslint-disable-next-line unicorn/consistent-function-scoping
      const getViewportReference = () => {
        const reference = selectMenuReference.value
        if (Array.isArray(reference)) {
          return reference[0]?.viewportRef
        }
        if (hasViewportReference(reference)) {
          return reference.viewportRef
        }
        return
      }

      useInfiniteScroll(
        getViewportReference(),
        () => {
          if (hasMore.value && status.value !== 'pending') {
            page.value++
            execute()
          }
        },
        {
          distance: scrollDistance,
          canLoadMore: () => hasMore.value && status.value !== 'pending',
        },
      )
    })
  }

  return {
    items,
    searchTerm,
    status,
    onOpen,
    setupInfiniteScroll,
  }
}

const useRepositoryForm = () => {
  const defaultData: Required<RepositoryDetail> = {
    id: '',
    serviceName: '',
    serviceUrl: '',
    entityIds: [''],
    spConnectorId: '',
    active: false,
    created: '',
    groupsCount: 0,
    usersCount: 0,
  }
  const { groupsCount, usersCount, ...defaultForm } = defaultData
  const state = reactive<RepositoryForm>({ ...defaultForm })

  const { id, spConnectorId, created, ...defaultCreateForm } = defaultForm
  const stateAsCreate = reactive<RepositoryCreateForm>({ ...defaultCreateForm })

  return { defaultData, state, stateAsCreate }
}

const useRepositorySchema = (mode?: MaybeRefOrGetter<FormMode>) => {
  const { t: $t } = useI18n()

  const { repositories: { maxUrlLength } } = useAppConfig()

  const createSchema = computed(() => z.object({
    serviceName: z.string().min(1, $t('repository.validation.serviceName.required')),
    serviceUrl: z.string()
      .min(1, $t('repository.validation.serviceUrl.required'))
      .max(maxUrlLength, $t('repository.validation.serviceUrl.max-length', { max: maxUrlLength }))
      .transform(value => `https://${value}`)
      .pipe(z.string().url($t('repository.validation.serviceUrl.invalid'))),
    entityIds: z.array(z.string().min(1, $t('repository.validation.entityIds.required')))
      .nonempty($t('repository.validation.entityIds.at-least-one')),
    active: z.boolean(),
  }))

  const updateSchema = computed(() => z.object({
    id: z.string().min(1, $t('repository.validation.id.required')),
    serviceName: z.string().min(1, $t('repository.validation.serviceName.required')),
    serviceUrl: z.string()
      .min(1, $t('repository.validation.serviceUrl.required'))
      .transform(value => `https://${value}`)
      .pipe(z.string().url($t('repository.validation.serviceUrl.invalid'))),
    entityIds: z.array(z.string().min(1, $t('repository.validation.entityIds.required')))
      .nonempty($t('repository.validation.entityIds.at-least-one')),
    active: z.boolean(),
  }))

  const getSchemaByMode = (m: FormMode) => {
    return m === 'new' ? createSchema.value : updateSchema.value
  }

  const schema = mode
    ? computed(() => {
        const currentMode = toValue(mode)
        return getSchemaByMode(currentMode)
      })
    : undefined

  return { schema, maxUrlLength }
}

const useGroupForm = () => {
  const defaultData: Required<GroupDetail> = {
    id: '',
    userDefinedId: '',
    displayName: '',
    description: '',
    repository: { id: '', serviceName: '' },
    public: false,
    memberListVisibility: 'Private',
    usersCount: 0,
    created: '',
  }

  const { usersCount, ..._defaultForm } = defaultData
  const defaultForm = {
    ..._defaultForm,
    repository: { id: '', label: '' },
  }
  const state = reactive<Omit<GroupForm, 'usersCount'>>({ ...defaultForm })

  const defaultCreateForm: GroupCreateForm = {
    ..._defaultForm,
    repository: { id: '', label: '' },
  }
  const stateAsCreate = reactive<GroupCreateForm>({ ...defaultCreateForm })

  return { defaultData, defaultForm, defaultCreateForm, state, stateAsCreate }
}

const useGroupFormOptions = () => {
  const { t: $t } = useI18n()

  const publicStatusOptions = computed(() => [
    { label: $t('group.public-status.public'), value: true },
    { label: $t('group.public-status.private'), value: false },
  ])

  const visibilityOptions = computed(() =>
    VISIBILITY_OPTIONS.map((visibility) => {
      let label = ''
      switch (visibility) {
        case 'Public': {
          label = $t('group.member-list-visibility.public')
          break
        }
        case 'Private': {
          label = $t('group.member-list-visibility.private')
          break
        }
        case 'Hidden': {
          label = $t('group.member-list-visibility.hidden')
          break
        }
      }
      return { label, value: visibility }
    }))

  return { publicStatusOptions, visibilityOptions }
}

const useGroupSchema = (mode?: MaybeRefOrGetter<FormMode>) => {
  const { t: $t } = useI18n()

  const { groups: { maxUrlLength } } = useAppConfig()
  const getMaxIdLength = (repositoryId: string) => maxUrlLength - repositoryId.length

  const createSchema = computed(() => z.object({
    userDefinedId: z.string().optional(),
    displayName: z.string().min(1, $t('group.validation.displayName.required')),
    description: z.string().optional(),
    repository: z.object({
      id: z.string().min(1, $t('group.validation.repository.id.required')),
    }),
    public: z.boolean().default(false),
    memberListVisibility: z.enum(VISIBILITY_OPTIONS, {
      errorMap: () => ({ message: $t('group.validation.memberListVisibility.invalid') }),
    }).default('Hidden'),
  }))

  const updateSchema = computed(() => z.object({
    displayName: z.string().min(1, $t('group.validation.displayName.required')),
    description: z.string().optional(),
    public: z.boolean().default(false),
    memberListVisibility: z.enum(VISIBILITY_OPTIONS, {
      errorMap: () => ({ message: $t('group.validation.memberListVisibility.invalid') }),
    }).default('Hidden'),
  }))

  const getSchemaByMode = (m: FormMode) => {
    return m === 'new' ? createSchema.value : updateSchema.value
  }

  const schema = mode
    ? computed(() => {
        const currentMode = toValue(mode)
        return getSchemaByMode(currentMode)
      })
    : undefined

  return { schema, getMaxIdLength }
}

const useUserForm = () => {
  const defaultData: Required<UserDetail> = {
    id: '',
    eppns: [''],
    userName: '',
    emails: [''],
    preferredLanguage: '' as PreferredLanguage,
    isSystemAdmin: false,
    repositoryRoles: [{ id: '', serviceName: '', userRole: undefined }],
    groups: [{ id: '', displayName: '' }],
    created: '',
    lastModified: '',
  }
  const { repositoryRoles, groups, ..._defaultForm } = defaultData
  const defaultForm: UserForm = {
    ..._defaultForm,
    repositoryRoles: [{ id: '', label: '', userRole: undefined }],
    groups: [{ id: '', label: '' }],
  }
  const state = reactive<UserForm>({ ...defaultForm })

  const { id, created, lastModified, ...defaultCreateForm } = defaultForm
  const stateAsCreate = reactive<UserCreateForm>({ ...defaultCreateForm })

  return { defaultData, defaultForm, state, stateAsCreate }
}

const useUserFormOptions = () => {
  const { t: $t } = useI18n()

  const langLabel = computed(() => ({
    ja: $t('user.preferred-language-ja'),
    en: $t('user.preferred-language-en'),
  }))

  const preferredLanguageOptions = computed(() =>
    PREFERRED_LANGUAGE
      .filter(Boolean)
      .map(lang => ({
        label: lang ? langLabel.value[lang] : undefined,
        value: lang,
      })))

  const userRoleOptions = computed(() => {
    const roles = {
      repositoryAdmin: $t('users.roles.repository-admin'),
      communityAdmin: $t('users.roles.community-admin'),
      contributor: $t('users.roles.contributor'),
      generalUser: $t('users.roles.general-user'),
    }
    return Object.entries(roles).map(([key, label]) => ({
      label,
      value: key,
    }))
  })

  return { preferredLanguageOptions, userRoleOptions }
}

const useUserSchema = (mode?: MaybeRefOrGetter<FormMode>) => {
  const { t: $t } = useI18n()
  const userRoles = Object.keys(USER_ROLES) as [string, ...string[]]

  const createSchema = computed(() => z.object({
    eppns: z.array(z.string()
      .min(1, $t('user.validation.eppns.required')))
      .nonempty($t('user.validation.eppns.at-least-one')),
    userName: z.string().min(1, $t('user.validation.userName.required')),
    emails: z.array(z.string()
      .min(1, $t('user.validation.emails.required'))
      .email($t('user.validation.emails.invalid')),
    ).nonempty($t('user.validation.emails.at-least-one')),
    preferredLanguage: z.enum(PREFERRED_LANGUAGE, {
      errorMap: () => ({ message: $t('user.validation.preferredLanguage.invalid') }),
    }).optional(),
    isSystemAdmin: z.boolean().default(false),
    repositoryRoles: z.array(z.object({
      id: z.string().optional().default(''),
      userRole: z.enum(userRoles).optional(),
    })),
    groups: z.array(z.object({ id: z.string() })).optional(),
  }).superRefine((data, context) => {
    if (data.isSystemAdmin === true) {
      const hasFilledRole = data.repositoryRoles.some(role => role.id || role.userRole)
      if (hasFilledRole) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: $t('user.validation.repositoryRoles.must-be-empty-for-system-admin'),
          path: ['repositoryRoles'],
        })
      }
    }
    else {
      const hasValidRole = data.repositoryRoles.some(role => role.id && role.userRole)
      if (!hasValidRole) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: $t('user.validation.repositoryRoles.at-least-one'),
          path: ['repositoryRoles'],
        })
      }

      for (const [index, role] of data.repositoryRoles.entries()) {
        if (role.id || role.userRole) {
          if (!role.id || role.id.length === 0) {
            context.addIssue({
              code: z.ZodIssueCode.custom,
              message: $t('user.validation.repositoryRoles.id.required'),
              path: ['repositoryRoles', index, 'id'],
            })
          }
          if (!role.userRole) {
            context.addIssue({
              code: z.ZodIssueCode.custom,
              message: $t('user.validation.repositoryRoles.userRole.required'),
              path: ['repositoryRoles', index, 'userRole'],
            })
          }
        }
      }
    }
  }))

  const updateSchema = computed(() => ({} as unknown))

  const getSchemaByMode = (m: FormMode) => {
    return m === 'new'
      ? createSchema.value
      : updateSchema.value as Record<keyof UserCreatePayload, z.ZodTypeAny>
  }

  const schema = mode
    ? computed(() => {
        const currentMode = toValue(mode)
        return getSchemaByMode(currentMode)
      })
    : undefined

  return { schema }
}

const useFormError = () => {
  const { t: $t } = useI18n()
  const toast = useToast()

  const handleFormError = (event: FormErrorEvent) => {
    toast.add({
      title: $t('error.validation.title'),
      description: $t('error.validation.description'),
      color: 'error',
    })

    focusFirstError(event)
  }

  return {
    handleFormError,
  }
}

const focusFirstError = (event: FormErrorEvent) => {
  const errorId = event?.errors?.[0]?.id
  if (import.meta.client && errorId) {
    nextTick(() => {
      const id = CSS.escape(errorId)
      const element = document.querySelector(`#${id}`) as HTMLElement
      element?.focus()
      element?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    })
  }
}

export {
  useRepositoryForm, useRepositorySchema,
  useGroupForm, useGroupSchema, useGroupFormOptions,
  useUserForm, useUserSchema, useUserFormOptions,
  useFormError, useSelectMenuInfiniteScroll,
}
