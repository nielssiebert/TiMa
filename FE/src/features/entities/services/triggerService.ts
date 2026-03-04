import { httpClient } from '@/core/api/httpClient'
import { entityDefinitions } from '../shared/entityModels'

export interface TriggerPayload {
  id: string
  name: string
  trigger_type: string
  recurrance_type: string
  date: string | null
  time: string | null
  weekdays: string[]
  from_date: string | null
  to_date: string | null
  recurring: boolean
  sequence_ids: string[]
}

type ActivationAction = 'activate' | 'deactivate'

const apiPath = entityDefinitions.triggers.apiPath

async function getById(id: string): Promise<unknown> {
  const response = await httpClient.get(`${apiPath}/${id}`)
  return response.data
}

async function create(payload: TriggerPayload): Promise<unknown> {
  const response = await httpClient.post(apiPath, payload)
  return response.data
}

async function update(payload: TriggerPayload): Promise<unknown> {
  const response = await httpClient.put(apiPath, payload)
  return response.data
}

async function remove(id: string): Promise<void> {
  await httpClient.delete(`${apiPath}/${id}`)
}

async function setActivation(id: string, action: ActivationAction): Promise<unknown> {
  const response = await httpClient.post(`${apiPath}/${id}/${action}`)
  return response.data
}

export const triggerService = {
  getById,
  create,
  update,
  remove,
  setActivation,
}
