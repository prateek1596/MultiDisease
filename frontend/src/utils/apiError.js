function formatDetail(detail) {
  if (!detail) return null

  if (typeof detail === 'string') return detail

  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (!item || typeof item !== 'object') return null

        const field = Array.isArray(item.loc) ? item.loc.join('.') : null
        const message = item.msg || item.message || null

        if (field && message) return `${field}: ${message}`
        return message || null
      })
      .filter(Boolean)

    return parts.length ? parts.join(' | ') : null
  }

  if (typeof detail === 'object') {
    if (typeof detail.message === 'string') return detail.message
    if (typeof detail.msg === 'string') return detail.msg
    try {
      return JSON.stringify(detail)
    } catch {
      return null
    }
  }

  return String(detail)
}

export function getApiErrorMessage(error, fallback = 'Request failed') {
  const data = error?.response?.data

  const fromDetail = formatDetail(data?.detail)
  if (fromDetail) return fromDetail

  const fromMessage =
    (typeof data?.message === 'string' && data.message) ||
    (typeof error?.message === 'string' && error.message)

  return fromMessage || fallback
}
