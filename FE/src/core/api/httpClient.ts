import axios, { AxiosError } from 'axios'
import { appConfig } from '../config/appConfig'

export const httpClient = axios.create({
  baseURL: appConfig.apiBaseUrl,
  timeout: 10000,
})

type UnauthorizedHandler = () => void

let unauthorizedHandler: UnauthorizedHandler | null = null
let handlingUnauthorized = false

function isUnauthorizedResponse(error: unknown): error is AxiosError {
  return error instanceof AxiosError && error.response?.status === 401
}

function isLoginRequest(error: AxiosError): boolean {
  const requestUrl = error.config?.url ?? ''
  return requestUrl.endsWith('/login')
}

httpClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (
      isUnauthorizedResponse(error) &&
      !isLoginRequest(error) &&
      unauthorizedHandler &&
      !handlingUnauthorized
    ) {
      handlingUnauthorized = true
      unauthorizedHandler()
      handlingUnauthorized = false
    }
    return Promise.reject(error)
  },
)

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  unauthorizedHandler = handler
}

export function setBasicAuthToken(token: string | null): void {
  if (!token) {
    delete httpClient.defaults.headers.common.Authorization
    return
  }
  httpClient.defaults.headers.common.Authorization = `Basic ${token}`
}

export function createBasicAuthToken(username: string, password: string): string {
  return btoa(`${username}:${password}`)
}
