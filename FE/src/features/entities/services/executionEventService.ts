import { httpClient } from '@/core/api/httpClient'
import { entityDefinitions } from '../shared/entityModels'

export interface ExecutionEventPayload {
  id: string
  name: string
  duration_ms: number
  activated: boolean
  factor_ids: string[]
  start_event_attributes: Record<string, string>
  stop_event_attributes: Record<string, string>
}

type ToggleAction = 'start' | 'stop'

const apiPath = entityDefinitions.executionEvents.apiPath

async function getById(id: string): Promise<unknown> {
  const response = await httpClient.get(`${apiPath}/${id}`)
  return response.data
}

async function create(payload: ExecutionEventPayload): Promise<unknown> {
  const response = await httpClient.post(apiPath, payload)
  return response.data
}

async function update(payload: ExecutionEventPayload): Promise<void> {
  await httpClient.put(apiPath, payload)
}

async function remove(id: string): Promise<void> {
  await httpClient.delete(`${apiPath}/${id}`)
}

async function toggleStatus(id: string, action: ToggleAction): Promise<void> {
  await httpClient.post(`${apiPath}/${id}/${action}`)
}

export const executionEventService = {
  getById,
  create,
  update,
  remove,
  toggleStatus,
}
