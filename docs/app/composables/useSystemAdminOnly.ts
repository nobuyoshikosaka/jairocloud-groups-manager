export const useSystemAdminVisibility = () => {
  const systemAdminVisible = useState<boolean>('systemAdminVisible', () => false)

  return {
    systemAdminVisible,
  }
}
