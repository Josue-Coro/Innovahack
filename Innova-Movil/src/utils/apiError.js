export function getApiError(error, fallback = 'Error de servidor') {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg ?? String(item)).join(', ');
  }
  const message = error?.response?.data?.message;
  if (typeof message === 'string') return message;
  if (error?.message) return error.message;
  return fallback;
}
