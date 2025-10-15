import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import { analyticsAPI } from '../services/api'
import { PerformanceMetrics } from '../types'

interface AnalyticsState {
  performanceMetrics: PerformanceMetrics | null
  trades: {
    trades: any[]
    summary: any
  } | null
  commissions: {
    total_commission: number
    volume_commission: number
    profit_commission: number
  } | null
  loading: {
    performance: boolean
    trades: boolean
    commissions: boolean
    export: boolean
  }
  error: string | null
}

const initialState: AnalyticsState = {
  performanceMetrics: null,
  trades: null,
  commissions: null,
  loading: {
    performance: false,
    trades: false,
    commissions: false,
    export: false,
  },
  error: null,
}

// Async thunks
export const getPerformanceMetrics = createAsyncThunk(
  'analytics/getPerformanceMetrics',
  async (periodDays: number, { rejectWithValue }) => {
    try {
      const response = await analyticsAPI.getPerformanceMetrics(periodDays)
      return response.data
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch performance metrics')
    }
  }
)

export const getTrades = createAsyncThunk(
  'analytics/getTrades',
  async (filters: { period_days?: number; symbol?: string; strategy_id?: string }, { rejectWithValue }) => {
    try {
      const response = await analyticsAPI.getTrades(filters)
      return response.data
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch trades')
    }
  }
)

export const getCommissions = createAsyncThunk(
  'analytics/getCommissions',
  async (periodDays: number, { rejectWithValue }) => {
    try {
      const response = await analyticsAPI.getCommissions(periodDays)
      return response.data
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch commissions')
    }
  }
)

export const exportData = createAsyncThunk(
  'analytics/exportData',
  async (params: { format: 'json' | 'csv'; periodDays: number }, { rejectWithValue }) => {
    try {
      const response = await analyticsAPI.exportData(params.format, params.periodDays)
      
      // Create download link for the exported data
      const blob = new Blob([response.data.data], { 
        type: params.format === 'json' ? 'application/json' : 'text/csv' 
      })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = response.data.filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      
      return response.data
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to export data')
    }
  }
)

const analyticsSlice = createSlice({
  name: 'analytics',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      // Performance Metrics
      builder
        .addCase(getPerformanceMetrics.pending, (state) => {
          state.loading.performance = true
        })
        .addCase(getPerformanceMetrics.fulfilled, (state, action) => {
          state.loading.performance = false
          state.performanceMetrics = action.payload
        })
        .addCase(getPerformanceMetrics.rejected, (state, action) => {
          state.loading.performance = false
          state.error = action.payload as string
        })

      // Trades
      builder
        .addCase(getTrades.pending, (state) => {
          state.loading.trades = true
        })
        .addCase(getTrades.fulfilled, (state, action) => {
          state.loading.trades = false
          state.trades = action.payload
        })
        .addCase(getTrades.rejected, (state, action) => {
          state.loading.trades = false
          state.error = action.payload as string
        })

      // Commissions
      builder
        .addCase(getCommissions.pending, (state) => {
          state.loading.commissions = true
        })
        .addCase(getCommissions.fulfilled, (state, action) => {
          state.loading.commissions = false
          const summary = action.payload.summary
          state.commissions = {
            total_commission: summary.total_commission,
            volume_commission: summary.volume_commission,
            profit_commission: summary.profit_commission,
          }
        })
        .addCase(getCommissions.rejected, (state, action) => {
          state.loading.commissions = false
          state.error = action.payload as string
        })

      // Export Data
      builder
        .addCase(exportData.pending, (state) => {
          state.loading.export = true
        })
        .addCase(exportData.fulfilled, (state) => {
          state.loading.export = false
        })
        .addCase(exportData.rejected, (state, action) => {
          state.loading.export = false
          state.error = action.payload as string
        })
  },
})

export const { clearError } = analyticsSlice.actions
export default analyticsSlice.reducer
