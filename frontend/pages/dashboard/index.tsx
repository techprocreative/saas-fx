import { useEffect } from 'react'
import { Box, Container, Typography, Alert } from '@mui/material'
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import {
  fetchDashboardStats,
  fetchAccounts,
  fetchStrategies,
  fetchTrades,
} from '../../store/tradingSlice'
import DashboardLayout from '../../src/components/Dashboard/DashboardLayout'
import DashboardOverview from '../../src/components/Dashboard/DashboardOverview'
import LoadingSpinner from '../../src/components/common/LoadingSpinner'

export default function DashboardPage() {
  const dispatch = useAppDispatch()
  const { user } = useAppSelector(state => state.auth)
  const {
    dashboardStats,
    accounts,
    strategies,
    trades,
    loading,
    error,
  } = useAppSelector(state => state.trading)

  useEffect(() => {
    if (user) {
      dispatch(fetchDashboardStats())
      dispatch(fetchAccounts())
      dispatch(fetchStrategies())
      dispatch(fetchTrades(50)) // Load recent 50 trades
    }
  }, [dispatch, user])

  if (!user) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <Typography>Please login to access the dashboard</Typography>
      </Box>
    )
  }

  if (loading.dashboard && !dashboardStats) {
    return <LoadingSpinner />
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="error">
          {error}
        </Alert>
      </Container>
    )
  }

  return (
    <DashboardLayout>
      <Container maxWidth="xl">
        <Box sx={{ mb: 4 }}>
          <Typography
            variant="h4"
            component="h1"
            sx={{ fontWeight: 600, mb: 1 }}
          >
            Welcome back, {user.username}!
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Here's your trading overview and performance metrics.
          </Typography>
        </Box>

        <DashboardOverview
          dashboardStats={dashboardStats}
          accounts={accounts}
          strategies={strategies}
          trades={trades.slice(0, 10)} // Show recent 10 trades
          loading={{
            stats: loading.dashboard,
            accounts: loading.accounts,
            strategies: loading.strategies,
            trades: loading.trades,
          }}
        />
      </Container>
    </DashboardLayout>
  )
}
