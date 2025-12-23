import { ref, computed } from 'vue'

export function usePagination(defaultPageSize = 20) {
  const currentPage = ref(1)
  const pageSize = ref(defaultPageSize)
  const total = ref(0)

  const skip = computed(() => (currentPage.value - 1) * pageSize.value)

  const resetPage = () => {
    currentPage.value = 1
  }

  const handlePageChange = (page: number) => {
    currentPage.value = page
  }

  const handleSizeChange = (size: number) => {
    pageSize.value = size
    resetPage()
  }

  return {
    currentPage,
    pageSize,
    total,
    skip,
    resetPage,
    handlePageChange,
    handleSizeChange
  }
}
