import axios, { AxiosInstance, AxiosResponse } from 'axios'
import Cookies from 'js-cookie'

// Create axios instance
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

class API {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}/api/v1`,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Add request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Add response interceptor to handle token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true

          try {
            const refreshToken = typeof window !== 'undefined' ? localStorage.getItem('refresh_token') : null
            if (refreshToken) {
              const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
                refresh_token: refreshToken,
              })

              const { access_token } = response.data
              if (typeof window !== 'undefined') {
                localStorage.setItem('access_token', access_token)
                originalRequest.headers.Authorization = `Bearer ${access_token}`
              }

              return this.client(originalRequest)
            }
          } catch (refreshError) {
            // Refresh token failed, logout user
            if (typeof window !== 'undefined') {
              localStorage.removeItem('access_token')
              localStorage.removeItem('refresh_token')
              window.location.href = '/auth/login'
            }
          }
        }

        return Promise.reject(error)
      }
    )
  }

  // Generic request methods
  async get<T = any>(url: string, config?: any): Promise<AxiosResponse<T>> {
    return this.client.get(url, config)
  }

  async post<T = any>(url: string, data?: any, config?: any): Promise<AxiosResponse<T>> {
    return this.client.post(url, data, config)
  }

  async put<T = any>(url: string, data?: any, config?: any): Promise<AxiosResponse<T>> {
    return this.client.put(url, data, config)
  }

  async delete<T = any>(url: string, config?: any): Promise<AxiosResponse<T>> {
    return this.client.delete(url, config)
  }
}

// Create API instance
const api = new API()

// Authentication API
export const authAPI = {
  login: (credentials: { username: string; password: string }) =>
    api.post('/auth/login', credentials),

  register: (userData: { email: string; username: string; password: string }) =>
    api.post('/auth/register', userData),

  refresh: (refreshToken: string) =>
    api.post('/auth/refresh', { refresh_token: refreshToken }),

  logout: () =>
    api.post('/auth/logout'),

  getMe: () =>
    api.get('/auth/me'),
}

// Trading API
export const tradingAPI = {
  getAccounts: () =>
    api.get('/trading/accounts'),

  createAccount: (accountData: any) =>
    api.post('/trading/accounts', accountData),

  downloadEA: (accountId: string) =>
    api.get(`/trading/account/${accountId}/ea-download`),

  getStrategies: () =>
    api.get('/trading/strategies'),

  generateStrategy: (strategyData: any) =>
    api.post('/trading/strategies/generate', strategyData),

  startTrading: (config: any) =>
    api.post('/trading/start', config),

  stopTrading: (strategyId: string) =>
    api.post('/trading/stop', { strategy_id: strategyId }),

  getTrades: (limit: number = 100) =>
    api.get(`/trading/trades?limit=${limit}`),

  getTradingStatus: () =>
    api.get('/trading/status'),
}

// Analytics API
export const analyticsAPI = {
  getDashboardStats: () =>
    api.get('/analytics/dashboard'),

  getPerformanceMetrics: (periodDays: number = 30) =>
    api.get(`/analytics/performance?period_days=${periodDays}`),

  getTrades: (filters?: {
    period_days?: number
    symbol?: string
    strategy_id?: string
  }) => {
    const params = new URLSearchParams()
    if (filters?.period_days) params.append('period_days', filters.period_days.toString())
    if (filters?.symbol) params.append('symbol', filters.symbol)
    if (filters?.strategy_id) params.append('strategy_id', filters.strategy_id)
    return api.get(`/analytics/trades?${params}`)
  },

  getCommissions: (periodDays: number = 30) =>
    api.get(`/analytics/commissions?period_days=${periodDays}`),

  getStrategyPerformance: (strategyId: string, periodDays: number = 30) =>
    api.get(`/analytics/strategies/${strategyId}/performance?period_days=${periodDays}`),

  getRealTimeUpdates: () =>
    api.get('/analytics/real-time'),

  exportData: (format: 'json' | 'csv', periodDays: number = 30) =>
    api.get(`/analytics/export/performance?format=${format}&period_days=${periodDays}`),
}

// Strategies API
export const strategiesAPI = {
  getStrategies: () =>
    api.get('/strategies'),

  getStrategy: (id: string) =>
    api.get(`/strategies/${id}`),

  updateStrategy: (id: string, data: any) =>
    api.put(`/strategies/${id}`, data),

  deleteStrategy: (id: string) =>
    api.delete(`/strategies/${id}`),

  activateStrategy: (id: string) =>
    api.post(`/strategies/${id}/activate`),

  deactivateStrategy: (id: string) =>
    api.post(`/strategies/${id}/deactivate`),
}

// WebSocket for real-time updates
export class WebSocketClient {
  private ws: WebSocket | null = null
  private userId: string | null = null
  private pingInterval: NodeJS.Timeout | null = null

  connect(userId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const wsUrl = `${API_BASE_URL.replace('http', 'ws')}/ws/trading/${userId}`
        this.ws = new WebSocket(wsUrl)
        this.userId = userId

        this.ws.onopen = () => {
          console.log('WebSocket connected')
          
          // Start ping interval
          this.pingInterval = setInterval(() => {
            this.sendPing()
          }, 30000) // Ping every 30 seconds
          
          resolve()
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          reject(error)
        }

        this.ws.onmessage = (event) => {
          this.handleMessage(event.data)
        }

        this.ws.onclose = () => {
          console.log('WebSocket disconnected')
          if (this.pingInterval) {
            clearInterval(this.pingInterval)
          }
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
  }

  private sendPing() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message = {
        type: 'heartbeat',
        account_data: {
          login: 'demo_account', // This would be updated with real account data
          balance: 10000
        }
      }
      this.ws.send(JSON.stringify(message))
    }
  }

  private handleMessage(data: string) {
    try {
      const message = JSON.parse(data)
      
      // Emit custom events based on message type
      this.emit(message.type, message)
    } catch (error) {
      console.error('Error parsing WebSocket message:', error)
    }
  }

  private emit(event: string, data: any) {
    // Create custom event and dispatch it
    const customEvent = new CustomEvent(event, { detail: data })
    window.dispatchEvent(customEvent)
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

export const wsClient = new WebSocketClient()

export default api
