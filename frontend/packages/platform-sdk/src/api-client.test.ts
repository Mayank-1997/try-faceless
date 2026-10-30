import { describe, it, expect } from 'vitest'
import { ApiClient } from '../api-client'

describe('ApiClient', () => {
  it('should create an instance with config', () => {
    const client = new ApiClient({
      baseURL: 'http://localhost:8000/api/v1',
    })
    expect(client).toBeDefined()
    expect(client.axiosInstance).toBeDefined()
  })

  it('should have default timeout', () => {
    const client = new ApiClient({
      baseURL: 'http://localhost:8000/api/v1',
    })
    expect(client.axiosInstance.defaults.timeout).toBe(30000)
  })

  it('should accept custom timeout', () => {
    const client = new ApiClient({
      baseURL: 'http://localhost:8000/api/v1',
      timeout: 5000,
    })
    expect(client.axiosInstance.defaults.timeout).toBe(5000)
  })

  it('should set content type header', () => {
    const client = new ApiClient({
      baseURL: 'http://localhost:8000/api/v1',
    })
    expect(client.axiosInstance.defaults.headers['Content-Type']).toBe('application/json')
  })
})
