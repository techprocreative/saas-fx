import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import { useAppDispatch, useAppSelector } from '../store/hooks'
import { login, register, logout, checkAuth } from '../store/authSlice'

export const useAuth = () => {
  const router = useRouter()
  const dispatch = useAppDispatch()
  const { user, token, loading, error, isAuthenticated } = useAppSelector(state => state.auth)

  useEffect(() => {
    // Check authentication status on mount
    dispatch(checkAuth())
  }, [dispatch])

  const handleLogin = async (username: string, password: string) => {
    try {
      await dispatch(login({ username, password })).unwrap()
    } catch (error) {
      console.error('Login failed:', error)
      throw error
    }
  }

  const handleRegister = async (email: string, username: string, password: string) => {
    try {
      await dispatch(register({ email, username, password })).unwrap()
    } catch (error) {
      console.error('Registration failed:', error)
      throw error
    }
  }

  const handleLogout = async () => {
    try {
      await dispatch(logout()).unwrap()
      router.push('/auth/login')
    } catch (error) {
      console.error('Logout failed:', error)
    }
  }

  return {
    user,
    token,
    loading,
    error,
    isAuthenticated,
    login: handleLogin,
    register: handleRegister,
    logout: handleLogout,
  }
}
