import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export interface TestCase {
  id: number
  name: string
  folder: string
  filename: string
  tags: string
  priority: string
  status: string
  last_run_at: string | null
  content?: string
  created_at: string | null
}

export interface FolderNode {
  label: string
  path: string
  children: FolderNode[]
}

export interface CaseCreate {
  name: string
  folder?: string
  tags?: string
  priority?: string
  content?: string
}

export const caseApi = {
  list: (params?: Record<string, string>) => api.get<TestCase[]>('/cases', { params }),
  get: (id: number) => api.get<TestCase>(`/cases/${id}`),
  create: (data: CaseCreate) => api.post<TestCase>('/cases', data),
  update: (id: number, data: Partial<CaseCreate>) => api.put<TestCase>(`/cases/${id}`, data),
  delete: (id: number) => api.delete(`/cases/${id}`),
  folders: () => api.get<FolderNode[]>('/cases/folders'),
}

export default api
