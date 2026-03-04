import { httpClient } from '@/core/api/httpClient'
import { entityDefinitions } from '../shared/entityModels'

export interface FactorPayload {
  id: string
  name: string
  min_val: number | null
  max_val: number | null
}

type ActivationAction = 'activate' | 'deactivate'

const apiPath = entityDefinitions.factors.apiPath

async function getById(id: string): Promise<unknown> {
  const response = await httpClient.get(`${apiPath}/${id}`)
  return response.data
}

async function create(payload: FactorPayload): Promise<unknown> {
  const response = await httpClient.post(apiPath, payload)
  return response.data
}

async function update(payload: FactorPayload): Promise<unknown> {
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

async function updateFactorValue(id: string, value: number): Promise<unknown> {
  const response = await httpClient.post(`${apiPath}/updateFactor`, { id, value })
  return response.data
}

export const factorService = {
  getById,
  create,
  update,
  remove,
  setActivation,
  updateFactorValue,
}
