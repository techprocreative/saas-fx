import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  LinearProgress,
  Alert,
  Chip,
} from '@mui/material'
import {
  TrendingUp,
  TrendingDown,
  AccountBalanceWallet as WalletIcon,
  Speed,
  Psychology,
  BarChart,
  AttachMoney,
} from '@mui/icons-material'
import { DashboardStats, Trade, TradingAccount, AIStrategy } from '../../types'

interface DashboardOverviewProps {
  dashboardStats: DashboardStats | null
  accounts: TradingAccount[]
  strategies: AIStrategy[]
  trades: Trade[]
  loading: {
    stats: boolean
    accounts: boolean
    strategies: boolean
    trades: boolean
  }
}

export default function DashboardOverview({
  dashboardStats,
  accounts,
  strategies,
  trades,
  loading,
}: DashboardOverviewProps) {
  const StatCard = ({
    title,
    value,
    icon,
    color,
    subtitle,
    trend,
  }: {
    title: string
    value: string | number
    icon: React.ReactNode
    color: string
    subtitle?: string
    trend?: 'up' | 'down' | 'neutral'
  }) => (
    <Card
      sx={{
        background: 'linear-gradient(145deg, rgba(37, 45, 64, 0.9) 0%, rgba(55, 72, 107, 0.9) 100%)',
        border: '1px solid rgba(0, 188, 212, 0.2)',
        position: 'relative',
        overflow: 'hidden',
        '&::before': {
          content: '""',
          position: 'absolute',
          top: 0,
          right: 0,
          width: 60,
          height: 60,
          background: 'rgba(0, 188, 212, 0.1)',
          borderRadius: '0 12px 0 60px',
        },
      }}
    >
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {title}
            </Typography>
            <Typography variant="h4" component="div" sx={{ fontWeight: 700 }}>
              {value}
            </Typography>
            {subtitle && (
              <Typography variant="caption" color="text.secondary">
                {subtitle}
              </Typography>
            )}
          </Box>
          <Box sx={{ color, fontSize: 40 }}>
            {icon}
          </Box>
        </Box>
        {trend && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {trend === 'up' && <TrendingUp color="success" />}
            {trend === 'down' && <TrendingDown color="error" />}
            <Typography
              variant="caption"
              color={trend === 'up' ? 'success.main' : trend === 'down' ? 'error.main' : 'text.secondary'}
            >
              {trend === 'up' ? '+12%' : trend === 'down' ? '-8%' : '0%'}
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  )

  if (!dashboardStats && loading.stats) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <Typography>Loading dashboard stats...</Typography>
      </Box>
    )
  }

  if (!dashboardStats) {
    return (
      <Alert severity="error" sx={{ mb: 3 }}>
        Unable to load dashboard statistics. Please try refreshing the page.
      </Alert>
    )
  }

  const recentTrades = trades.slice(0, 5)
  const totalProfit = dashboardStats.total_profit_loss
  const profitTrend = totalProfit >= 0 ? 'up' : 'down'

  return (
    <Grid container spacing={3}>
      {/* Stats Cards */}
      <Grid item xs={12} sm={6} md={3}>
        <StatCard
          title="Total Profit/Loss"
          value={`$${Math.abs(totalProfit).toFixed(2)}`}
          icon={<AttachMoney />}
          color={totalProfit >= 0 ? '#4caf50' : '#f44336'}
          trend={profitTrend}
        />
      </Grid>

      <Grid item xs={12} sm={6} md={3}>
        <StatCard
          title="Open Positions"
          value={dashboardStats.open_trades}
          icon={<BarChart />}
          color="#00bcd4"
          subtitle={dashboardStats.total_trades - dashboardStats.open_trades + ' closed'}
        />
      </Grid>

      <Grid item xs={12} sm={6} md={3}>
        <StatCard
          title="Active Strategies"
          value={dashboardStats.active_strategies}
          icon={<Psychology />}
          color="#ff9800"
          subtitle={strategies.length - dashboardStats.active_strategies + ' total'}
        />
      </Grid>

      <Grid item xs={12} sm={6} md={3}>
        <StatCard
          title="Online Accounts"
          value={`${dashboardStats.online_accounts}/${dashboardStats.total_accounts}`}
          icon={<WalletIcon />}
          color="#9c27b0"
          subtitle={dashboardStats.total_accounts > 0 ? Math.round((dashboardStats.online_accounts / dashboardStats.total_accounts) * 100) + '% online' : ''}
        />
      </Grid>

      {/* Account Status */}
      <Grid item xs={12} md={6}>
        <Card sx={{ bgcolor: 'background.paper', border: '1px solid rgba(0, 188, 212, 0.2)' }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
              Trading Accounts
            </Typography>
            {loading.accounts ? (
              <LinearProgress />
            ) : accounts.length === 0 ? (
              <Alert severity="info">
                No trading accounts connected. Connect your MT5 account to start trading.
              </Alert>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {accounts.map((account) => (
                  <Box
                    key={account.id}
                    sx={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      p: 2,
                      bgcolor: 'rgba(0, 0, 0, 0.02)',
                      borderRadius: 1,
                      border: '1px solid',
                      borderColor: 'divider',
                    }}
                  >
                    <Box>
                      <Typography variant="body2" fontWeight={600}>
                        {account.mt5_login}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {account.broker}
                      </Typography>
                      <Typography variant="body2" sx={{ mt: 0.5 }}>
                        Balance: ${ parseFloat(account.balance).toFixed(2)}
                      </Typography>
                    </Box>
                    <Chip
                      label={account.connection_status.toUpperCase()}
                      color={account.connection_status === 'online' ? 'success' : 'default'}
                      size="small"
                      sx={{ fontWeight: 600 }}
                    />
                  </Box>
                ))}
              </Box>
            )}
          </CardContent>
        </Card>
      </Grid>

      {/* Recent Trades */}
      <Grid item xs={12} md={6}>
        <Card sx={{ bgcolor: 'background.paper', border: '1px solid rgba(0, 188, 212, 0.2)' }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
              Recent Trades
            </Typography>
            {loading.trades ? (
              <LinearProgress />
            ) : recentTrades.length === 0 ? (
              <Alert severity="info">
                No recent trades. Start your trading strategies to see activity.
              </Alert>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {recentTrades.map((trade) => (
                  <Box
                    key={trade.id}
                    sx={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      p: 2,
                      bgcolor: 'rgba(0, 0, 0, 0.02)',
                      borderRadius: 1,
                      border: '1px solid',
                      borderColor: 'divider',
                    }}
                  >
                    <Box>
                      <Typography variant="body2" fontWeight={600}>
                        {trade.symbol}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {trade.type} • {trade.volume}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {new Date(trade.opened_at).toLocaleDateString()}
                      </Typography>
                    </Box>
                    <Box sx={{ textAlign: 'right' }}>
                      <Typography
                        variant="body2"
                        sx={{
                          color: trade.profit_loss >= 0 ? 'success.main' : 'error.main',
                          fontWeight: 600,
                        }}
                      >
                        {trade.profit_loss >= 0 ? '+' : ''}
                        ${Math.abs(trade.profit_loss).toFixed(2)}
                      </Typography>
                      <Chip
                        label={trade.status}
                        color={trade.status === 'closed' ? 'default' : 'primary'}
                        size="small"
                        variant="outlined"
                      />
                    </Box>
                  </Box>
                ))}
              </Box>
            )}
            {recentTrades.length > 0 && (
              <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ cursor: 'pointer', '&:hover': { color: 'primary.main' } }}
                >
                  View all trades →
                </Typography>
              </Box>
            )}
          </CardContent>
        </Card>
      </Grid>

      {/* Additional Info Cards */}
      <Grid item xs={12} md={6}>
        <Card sx={{ bgcolor: 'background.paper', border: '1px solid rgba(0, 188, 212, 0.2)' }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
              Today's Activity
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="body2">Today's Trades</Typography>
                <Typography variant="body2" fontWeight={600}>
                  {dashboardStats.todays_trades}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="body2">Commission Earned</Typography>
                <Typography variant="body2" fontWeight={600} color="success.main">
                  ${dashboardStats.commission_earned.toFixed(2)}
                </Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={6}>
        <Card sx={{ bgcolor: 'background.paper', border: '1px solid rgba(0, 188, 212, 0.2)' }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
              Performance Summary
            </Typography>
            <Alert severity="info" sx={{ mb: 2 }}>
              Advanced analytics dashboard is available in the Analytics section.
            </Alert>
            <Box sx={{ mt: 2 }}>
              <Typography variant="caption" color="text.secondary">
                View detailed performance metrics, win rates, and trading analytics.
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  )
}
