import { httpClient } from '@/core/api/httpClient'

export interface UserPayload {
  id: string
  username: string
  confirmed: boolean
}

async function getAll(): Promise<unknown> {
  const response = await httpClient.get('/users')
  return response.data
}

async function confirm(userId: string): Promise<void> {
  await httpClient.post(`/users/${userId}/confirm`)
}

async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  await httpClient.post('/users/change_password', {
    old_password: oldPassword,
    new_password: newPassword,
  })
}

export const userService = {
  getAll,
  confirm,
  changePassword,
}
