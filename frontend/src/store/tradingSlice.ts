import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import { Trade, TradingAccount, AIStrategy, DashboardStats } from '../types'
import { tradingAPI } from '../services/api'

interface TradingState {
  accounts: TradingAccount[]
  strategies: AIStrategy[]
  trades: Trade[]
  dashboardStats: DashboardStats | null
  loading: {
    accounts: boolean
    strategies: boolean
    trades: boolean
    dashboard: boolean
  }
  error: string | null
}

const initialState: TradingState = {
  accounts: [],
  strategies: [],
  trades: [],
  dashboardStats: null,
  loading: {
    accounts: false,
    strategies: false,
    trades: false,
    dashboard: false,
  },
  error: null,
}

// Async thunks
export const fetchAccounts = createAsyncThunk(
  'trading/fetchAccounts',
  async (_, { rejectWithValue }) => {
    try {
      const response = await tradingAPI.getAccounts()
      return response.data
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch accounts')
    }
  }
)

export const fetchStrategies = createAsyncThunk(
  'trading/fetchStrategies',
  async (_, { rejectWithValue }) => {
    try {
      const response = await tradingAPI.getStrategies()
      return response.data
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch strategies')
    }
  }
)

export const generateAIStrategy = createAsyncThunk(
  'trading/generateAIStrategy',
  async (strategyData: any, { rejectWithValue }) => {
    try {
      const response = await tradingAPI.generateStrategy(strategyData)
      return response.data
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to generate strategy')
    }
  }
)

export const startTrading = createAsyncThunk(
  'trading/startTrading',
  async (config: any, { rejectWithValue }) => {
    try {
      const response = await tradingAPI.startTrading(config)
      return response.data
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to start trading')
    }
  }
)

export const stopTrading = createAsyncThunk(
  'trading/stopTrading',
  async (strategyId: string, { rejectWithValue }) => {
    try {
      const response = await tradingAPI.stopTrading(strategyId)
      return { strategyId, data: response.data }
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to stop trading')
    }
  }
)

export const fetchTrades = createAsyncThunk(
  'trading/fetchTrades',
  async (limit: number = 100, { rejectWithValue }) => {
    try {
      const response = await tradingAPI.getTrades(limit)
      return response.data
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch trades')
    }
  }
)

export const fetchDashboardStats = createAsyncThunk(
  'trading/fetchDashboardStats',
  async (_, { rejectWithValue }) => {
    try {
      const response = await tradingAPI.getDashboardStats()
      return response.data
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch dashboard stats')
    }
  }
)

const tradingSlice = createSlice({
  name: 'trading',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null
    },
    updateAccountStatus: (state, action: PayloadAction<{ accountId: string; status: string }>) => {
      const account = state.accounts.find(acc => acc.id === action.payload.accountId)
      if (account) {
        account.connection_status = action.payload.status
      }
    },
    addTrade: (state, action: PayloadAction<Trade>) => {
      state.trades.unshift(action.payload)
    },
    updateTrade: (state, action: PayloadAction<Trade>) => {
      const index = state.trades.findIndex(trade => trade.id === action.payload.id)
      if (index !== -1) {
        state.trades[index] = action.payload
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Accounts
      builder
        .addCase(fetchAccounts.pending, (state) => {
          state.loading.accounts = true
        })
        .addCase(fetchAccounts.fulfilled, (state, action) => {
          state.loading.accounts = false
          state.accounts = action.payload
        })
        .addCase(fetchAccounts.rejected, (state, action) => {
          state.loading.accounts = false
          state.error = action.payload as string
        })

      // Fetch Strategies
      builder
        .addCase(fetchStrategies.pending, (state) => {
          state.loading.strategies = true
        })
        .addCase(fetchStrategies.fulfilled, (state, action) => {
          state.loading.strategies = false
          state.strategies = action.payload
        })
        .addCase(fetchStrategies.rejected, (state, action) => {
          state.loading.strategies = false
          state.error = action.payload as string
        })

      // Generate AI Strategy
      builder
        .addCase(generateAIStrategy.pending, (state) => {
          state.loading.strategies = true
        })
        .addCase(generateAIStrategy.fulfilled, (state, action) => {
          state.loading.strategies = false
          state.strategies.push(action.payload)
        })
        .addCase(generateAIStrategy.rejected, (state, action) => {
          state.loading.strategies = false
          state.error = action.payload as string
        })

      // Start Trading
      builder
        .addCase(startTrading.pending, (state) => {
          state.error = null
        })
        .addCase(startTrading.fulfilled, (state) => {
          // Update strategy status if needed
        })
        .addCase(startTrading.rejected, (state, action) => {
          state.error = action.payload as string
        })

      // Stop Trading
      builder
        .addCase(stopTrading.fulfilled, (state, action) => {
          // Update strategy status
          const strategy = state.strategies.find(s => s.id === action.payload.strategyId)
          if (strategy) {
            strategy.status = 'inactive'
          }
        })

      // Fetch Trades
      builder
        .addCase(fetchTrades.pending, (state) => {
          state.loading.trades = true
        })
        .addCase(fetchTrades.fulfilled, (state, action) => {
          state.loading.trades = false
          state.trades = action.payload
        })
        .addCase(fetchTrades.rejected, (state, action) => {
          state.loading.trades = false
          state.error = action.payload as string
        })

      // Fetch Dashboard Stats
      builder
        .addCase(fetchDashboardStats.pending, (state) => {
          state.loading.dashboard = true
        })
        .addCase(fetchDashboardStats.fulfilled, (state, action) => {
          state.loading.dashboard = false
          state.dashboardStats = action.payload
        })
        .addCase(fetchDashboardStats.rejected, (state, action) => {
          state.loading.dashboard = false
          state.error = action.payload as string
        })
  },
})

export const { clearError, updateAccountStatus, addTrade, updateTrade } = tradingSlice.actions
export default tradingSlice.reducer
