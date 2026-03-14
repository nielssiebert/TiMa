import { httpClient } from '@/core/api/httpClient'
import { entityDefinitions } from '../shared/entityModels'

interface SequenceItemPayload {
  order: number
  execution_event_id?: string
  execution_event_group_id?: string
}

export interface SequencePayload {
  id: string
  name: string
  trigger_ids: string[]
  sequence_items?: SequenceItemPayload[]
}

type RuntimeAction = 'start' | 'stop'

const apiPath = entityDefinitions.sequences.apiPath

async function getById(id: string): Promise<unknown> {
  const response = await httpClient.get(`${apiPath}/${id}`)
  return response.data
}

async function create(payload: SequencePayload): Promise<unknown> {
  const response = await httpClient.post(apiPath, payload)
  return response.data
}

async function update(payload: SequencePayload): Promise<unknown> {
  const response = await httpClient.put(apiPath, payload)
  return response.data
}

async function remove(id: string): Promise<void> {
  await httpClient.delete(`${apiPath}/${id}`)
}

async function toggleRuntime(id: string, action: RuntimeAction): Promise<void> {
  await httpClient.post(`${apiPath}/${id}/${action}`)
}

export const sequenceService = {
  getById,
  create,
  update,
  remove,
  toggleRuntime,
}
