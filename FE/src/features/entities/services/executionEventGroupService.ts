import { httpClient } from '@/core/api/httpClient'
import { entityDefinitions } from '../shared/entityModels'

export interface ExecutionEventGroupPayload {
  id: string
  name: string
  execution_event_ids: string[]
}

type RuntimeAction = 'start' | 'stop'

const apiPath = entityDefinitions.executionEventGroups.apiPath

async function getById(id: string): Promise<unknown> {
  const response = await httpClient.get(`${apiPath}/${id}`)
  return response.data
}

async function create(payload: ExecutionEventGroupPayload): Promise<unknown> {
  const response = await httpClient.post(apiPath, payload)
  return response.data
}

async function update(payload: ExecutionEventGroupPayload): Promise<unknown> {
  const response = await httpClient.put(apiPath, payload)
  return response.data
}

async function remove(id: string): Promise<void> {
  await httpClient.delete(`${apiPath}/${id}`)
}

async function toggleRuntime(id: string, action: RuntimeAction): Promise<void> {
  await httpClient.post(`${apiPath}/${id}/${action}`)
}

export const executionEventGroupService = {
  getById,
  create,
  update,
  remove,
  toggleRuntime,
}
