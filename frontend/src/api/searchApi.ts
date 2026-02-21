import axios from 'axios'
import type { SearchResult } from '../components/ResultsList'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface SearchRequest {
  query: string
}

export interface SearchResponse {
  results: SearchResult[]
}

export const searchApi = {
  async search(query: string): Promise<SearchResponse> {
    const response = await api.post<SearchResponse>('/search', { query })
    return response.data
  },
}
