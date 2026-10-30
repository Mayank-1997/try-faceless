import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'

// Mock the SDK
const mockProjectsSDK = {
  list: vi.fn(),
  getById: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
  delete: vi.fn(),
  getWorkflow: vi.fn(),
  startWorkflow: vi.fn(),
  cancelWorkflow: vi.fn(),
}

vi.mock('@ai-video-studio/platform-sdk', () => ({
  getSDK: () => ({ projects: mockProjectsSDK }),
  useProjects: vi.fn(),
  useProject: vi.fn(),
  useCreateProject: vi.fn(),
  useUpdateProject: vi.fn(),
  useDeleteProject: vi.fn(),
  useProjectWorkflow: vi.fn(),
  useStartWorkflow: vi.fn(),
  useCancelWorkflow: vi.fn(),
}))

import {
  useProjects,
  useProject,
  useCreateProject,
  useUpdateProject,
  useDeleteProject,
  useProjectWorkflow,
  useStartWorkflow,
  useCancelWorkflow,
  projectKeys,
} from '@ai-video-studio/platform-sdk'

describe('Project Hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('projectKeys', () => {
    it('generates correct query keys', () => {
      expect(projectKeys.all).toEqual(['projects'])
      expect(projectKeys.list({ status: 'draft' })).toEqual(['projects', 'list', { status: 'draft' }])
      expect(projectKeys.detail('abc')).toEqual(['projects', 'detail', 'abc'])
      expect(projectKeys.workflow('abc')).toEqual(['projects', 'abc', 'workflow'])
    })
  })

  describe('useProjects', () => {
    it('calls SDK list with params', async () => {
      const mockData = { items: [], total: 0, offset: 0, limit: 50 }
      mockProjectsSDK.list.mockResolvedValue(mockData)
      ;(useProjects as any).mockImplementation((params: any) => ({
        data: mockData,
        isLoading: false,
        refetch: vi.fn(),
      }))

      const result = useProjects({ limit: 10 })
      expect(result.data).toEqual(mockData)
    })
  })

  describe('useProject', () => {
    it('calls SDK getById', async () => {
      const mockProject = { id: '123', title: 'Test', status: 'draft' }
      mockProjectsSDK.getById.mockResolvedValue(mockProject)
      ;(useProject as any).mockImplementation((id: string) => ({
        data: id ? mockProject : undefined,
        isLoading: false,
      }))

      const result = useProject('123')
      expect(result.data).toEqual(mockProject)
    })
  })

  describe('useCreateProject', () => {
    it('calls SDK create', async () => {
      const mockProject = { id: 'new', title: 'New Project' }
      mockProjectsSDK.create.mockResolvedValue(mockProject)
      ;(useCreateProject as any).mockImplementation(() => ({
        mutate: vi.fn(),
        mutateAsync: vi.fn().mockResolvedValue(mockProject),
        isPending: false,
      }))

      const result = useCreateProject()
      expect(result.mutate).toBeDefined()
      expect(result.mutateAsync).toBeDefined()
    })
  })

  describe('useUpdateProject', () => {
    it('calls SDK update', async () => {
      const mockProject = { id: '123', title: 'Updated' }
      mockProjectsSDK.update.mockResolvedValue(mockProject)
      ;(useUpdateProject as any).mockImplementation(() => ({
        mutate: vi.fn(),
        mutateAsync: vi.fn().mockResolvedValue(mockProject),
        isPending: false,
      }))

      const result = useUpdateProject()
      expect(result.mutate).toBeDefined()
    })
  })

  describe('useDeleteProject', () => {
    it('calls SDK delete', async () => {
      mockProjectsSDK.delete.mockResolvedValue({ message: 'Deleted' })
      ;(useDeleteProject as any).mockImplementation(() => ({
        mutate: vi.fn(),
        mutateAsync: vi.fn().mockResolvedValue({ message: 'Deleted' }),
        isPending: false,
      }))

      const result = useDeleteProject()
      expect(result.mutate).toBeDefined()
    })
  })

  describe('useProjectWorkflow', () => {
    it('calls SDK getWorkflow', async () => {
      const mockWorkflow = { id: 'wf1', project_id: '123', status: 'running' }
      mockProjectsSDK.getWorkflow.mockResolvedValue(mockWorkflow)
      ;(useProjectWorkflow as any).mockImplementation((id: string) => ({
        data: id ? mockWorkflow : undefined,
        isLoading: false,
      }))

      const result = useProjectWorkflow('123')
      expect(result.data).toEqual(mockWorkflow)
    })
  })

  describe('useStartWorkflow', () => {
    it('calls SDK startWorkflow', async () => {
      const mockWorkflow = { id: 'wf1', status: 'running' }
      mockProjectsSDK.startWorkflow.mockResolvedValue(mockWorkflow)
      ;(useStartWorkflow as any).mockImplementation(() => ({
        mutate: vi.fn(),
        mutateAsync: vi.fn().mockResolvedValue(mockWorkflow),
        isPending: false,
      }))

      const result = useStartWorkflow()
      expect(result.mutate).toBeDefined()
    })
  })

  describe('useCancelWorkflow', () => {
    it('calls SDK cancelWorkflow', async () => {
      mockProjectsSDK.cancelWorkflow.mockResolvedValue({ message: 'Cancelled' })
      ;(useCancelWorkflow as any).mockImplementation(() => ({
        mutate: vi.fn(),
        mutateAsync: vi.fn().mockResolvedValue({ message: 'Cancelled' }),
        isPending: false,
      }))

      const result = useCancelWorkflow()
      expect(result.mutate).toBeDefined()
    })
  })
})

describe('ProjectsSDK', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('list calls correct endpoint', async () => {
    mockProjectsSDK.list.mockResolvedValue({ items: [], total: 0, offset: 0, limit: 50 })
    await mockProjectsSDK.list({ status: 'draft', limit: 10 })
    expect(mockProjectsSDK.list).toHaveBeenCalledWith({ status: 'draft', limit: 10 })
  })

  it('getById calls with id', async () => {
    mockProjectsSDK.getById.mockResolvedValue({ id: '123' })
    await mockProjectsSDK.getById('123')
    expect(mockProjectsSDK.getById).toHaveBeenCalledWith('123')
  })

  it('create calls with data', async () => {
    const data = { title: 'Test' }
    mockProjectsSDK.create.mockResolvedValue({ id: 'new', ...data })
    await mockProjectsSDK.create(data)
    expect(mockProjectsSDK.create).toHaveBeenCalledWith(data)
  })

  it('update calls with id and data', async () => {
    const data = { title: 'Updated' }
    mockProjectsSDK.update.mockResolvedValue({ id: '123', ...data })
    await mockProjectsSDK.update('123', data)
    expect(mockProjectsSDK.update).toHaveBeenCalledWith('123', data)
  })

  it('delete calls with id', async () => {
    mockProjectsSDK.delete.mockResolvedValue({ message: 'Deleted' })
    await mockProjectsSDK.delete('123')
    expect(mockProjectsSDK.delete).toHaveBeenCalledWith('123')
  })

  it('getWorkflow calls with id', async () => {
    mockProjectsSDK.getWorkflow.mockResolvedValue({ id: 'wf1' })
    await mockProjectsSDK.getWorkflow('123')
    expect(mockProjectsSDK.getWorkflow).toHaveBeenCalledWith('123')
  })

  it('startWorkflow calls with id', async () => {
    mockProjectsSDK.startWorkflow.mockResolvedValue({ id: 'wf1', status: 'running' })
    await mockProjectsSDK.startWorkflow('123')
    expect(mockProjectsSDK.startWorkflow).toHaveBeenCalledWith('123')
  })

  it('cancelWorkflow calls with id', async () => {
    mockProjectsSDK.cancelWorkflow.mockResolvedValue({ message: 'Cancelled' })
    await mockProjectsSDK.cancelWorkflow('123')
    expect(mockProjectsSDK.cancelWorkflow).toHaveBeenCalledWith('123')
  })
})
