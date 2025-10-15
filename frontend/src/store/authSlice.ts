import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import { User } from '../types'
import { authAPI } from '../services/api'

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  loading: boolean
  error: string | null
}

const initialState: AuthState = {
  user: null,
  token: null,
  isAuthenticated: false,
  loading: false,
  error: null,
}

// Async thunks
export const checkAuth = createAsyncThunk(
  'auth/checkAuth',
  async (_, { rejectWithValue }) => {
    try {
      const token = localStorage.getItem('access_token')
      if (!token) {
        throw new Error('No token found')
      }

      // Verify token with server and get user data
      const response = await authAPI.getMe()
      return { user: response.data, token }
    } catch (error) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      return rejectWithValue(error instanceof Error ? error.message : 'Authentication failed')
    }
  }
)

export const login = createAsyncThunk(
  'auth/login',
  async (credentials: { username: string; password: string }, { rejectWithValue }) => {
    try {
      const response = await authAPI.login(credentials)
      const { access_token, refresh_token, ...userData } = response.data

      // Store tokens
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)

      return { user: userData, token: access_token }
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Login failed')
    }
  }
)

export const register = createAsyncThunk(
  'auth/register',
  async (userData: { email: string; username: string; password: string }, { rejectWithValue }) => {
    try {
      const response = await authAPI.register(userData)
      const { access_token, refresh_token, ...userDataWithToken } = response.data

      // Store tokens
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)

      return { user: userDataWithToken, token: access_token }
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Registration failed')
    }
  }
)

export const logout = createAsyncThunk(
  'auth/logout',
  async (_, { rejectWithValue }) => {
    try {
      await authAPI.logout()
      
      // Clear tokens
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      
      return true
    } catch (error) {
      // Still clear tokens even if API call fails
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      return true
    }
  }
)

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      // Check Auth
      builder
        .addCase(checkAuth.pending, (state) => {
          state.loading = true
          state.error = null
        })
        .addCase(checkAuth.fulfilled, (state, action) => {
          state.loading = false
          state.user = action.payload.user
          state.token = action.payload.token
          state.isAuthenticated = true
        })
        .addCase(checkAuth.rejected, (state, action) => {
          state.loading = false
          state.user = null
          state.token = null
          state.isAuthenticated = false
          state.error = action.payload as string
        })

      // Login
      builder
        .addCase(login.pending, (state) => {
          state.loading = true
          state.error = null
        })
        .addCase(login.fulfilled, (state, action) => {
          state.loading = false
          state.user = action.payload.user
          state.token = action.payload.token
          state.isAuthenticated = true
        })
        .addCase(login.rejected, (state, action) => {
          state.loading = false
          state.error = action.payload as string
        })

      // Register
      builder
        .addCase(register.pending, (state) => {
          state.loading = true
          state.error = null
        })
        .addCase(register.fulfilled, (state, action) => {
          state.loading = false
          state.user = action.payload.user
          state.token = action.payload.token
          state.isAuthenticated = true
        })
        .addCase(register.rejected, (state, action) => {
          state.loading = false
          state.error = action.payload as string
        })

      // Logout
      builder
        .addCase(logout.fulfilled, (state) => {
          state.user = null
          state.token = null
          state.isAuthenticated = false
          state.error = null
        })
  },
})

export const { clearError } = authSlice.actions
export default authSlice.reducer
