export function isEntityLike(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

export function resolveEntityId(payload: unknown): string {
  if (!isEntityLike(payload)) {
    return ''
  }
  return typeof payload.id === 'string' ? payload.id : ''
}
