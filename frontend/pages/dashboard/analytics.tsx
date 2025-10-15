import { useState } from 'react'
import {
  Box,
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tabs,
  Tab,
} from '@mui/material'
import {
  Timeline,
  TimelineItem,
  TimelineSeparator,
  TimelineConnector,
  TimelineContent,
  TimelineDot,
} from '@mui/lab'
import {
  TrendingUp,
  TrendingDown,
  Download,
} from '@mui/icons-material'
import { useAppDispatch, useAppSelector } from '../../../src/store/hooks'
import {
  getPerformanceMetrics,
  getTrades,
  getCommissions,
  exportData,
} from '../../../src/store/analyticsSlice'
import DashboardLayout from '../../../src/components/Dashboard/DashboardLayout'

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`analytics-tabpanel-${index}`}
      aria-labelledby={`analytics-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  )
}

export default function AnalyticsPage() {
  const dispatch = useAppDispatch()
  const [tabValue, setTabValue] = useState(0)
  const [periodDays, setPeriodDays] = useState(30)

  const {
    performanceMetrics,
    trades,
    commissions,
    loading,
  } = useAppSelector(state => state.analytics)

  useEffect(() => {
    dispatch(getPerformanceMetrics(periodDays))
    dispatch(getTrades({ period_days: periodDays }))
    dispatch(getCommissions(periodDays))
  }, [dispatch, periodDays])

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue)
  }

  const handlePeriodChange = (event: any) => {
    setPeriodDays(parseInt(event.target.value))
  }

  const handleExport = (format: 'json' | 'csv') => {
    dispatch(exportData({ format, periodDays }))
  }

  const MetricCard = ({ title, value, icon, trend, color }: any) => (
    <Card
      sx={{
        bgcolor: 'background.paper',
        border: '1px solid rgba(0, 188, 212, 0.2)',
        height: '100%',
      }}
    >
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" color="text.secondary">
            {title}
          </Typography>
          <Box sx={{ fontSize: 32, color }}>
            {icon}
          </Box>
        </Box>
        <Typography variant="h4" sx={{ fontWeight: 600, color }}>
          {value}
        </Typography>
        {trend && (
          <Box sx={{ display: 'flex', alignItems: 'center', mt: 1, gap: 1 }}>
            {trend === 'up' ? (
              <TrendingUp sx={{ color: 'success.main' }} />
            ) : (
              <TrendingDown sx={{ color: 'error.main' }} />
            )}
            <Typography
              variant="caption"
              color={trend === 'up' ? 'success.main' : 'error.main'}
            >
              {trend === 'up' ? 'Positive' : 'Negative'}
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  )

  return (
    <DashboardLayout>
      <Container maxWidth="xl">
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" component="h1" sx={{ fontWeight: 600, mb: 2 }}>
            Trading Analytics
          </Typography>
          <Typography variant="body2" color="text.secondary" mb={2}>
            Comprehensive performance analysis and trading metrics
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Period</InputLabel>
              <Select
                value={periodDays}
                onChange={handlePeriodChange}
                label="Period"
              >
                <MenuItem value={7}>Last 7 days</MenuItem>
                <MenuItem value={30}>Last 30 days</MenuItem>
                <MenuItem value={90}>Last 90 days</MenuItem>
                <MenuItem value={365}>Last year</MenuItem>
              </Select>
            </FormControl>
            
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                variant="outlined"
                size="small"
                startIcon={<Download />}
                onClick={() => handleExport('csv')}
                sx={{ borderRadius: 2 }}
              >
                Export CSV
              </Button>
              <Button
                variant="outlined"
                size="small"
                startIcon={<Download />}
                onClick={() => handleExport('json')}
                sx={{ borderRadius: 2 }}
              >
                Export JSON
              </Button>
            </Box>
          </Box>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="analytics tabs">
            <Tab label="Performance" />
            <Tab label="Trades" />
            <Tab label="Commissions" />
          </Tabs>
        </Box>

        {/* Performance Tab */}
        <TabPanel value={tabValue} index={0}>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6} md={3}>
              <MetricCard
                title="Total Trades"
                value={performanceMetrics?.total_trades || 0}
                icon={<TrendingUp />}
                color="primary"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <MetricCard
                title="Win Rate"
                value={`${performanceMetrics?.win_rate?.toFixed(1) || 0}%`}
                icon={<TrendingUp />}
                color={performanceMetrics?.win_rate >= 50 ? 'success' : 'error'}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <MetricCard
                title="Profit Factor"
                value={performanceMetrics?.profit_factor?.toFixed(2) || 0}
                icon={<TrendingUp />}
                color={performanceMetrics?.profit_factor >= 1 ? 'success' : 'error'}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <MetricCard
                title="Sharpe Ratio"
                value={performanceMetrics?.sharpe_ratio?.toFixed(2) || 0}
                icon={<TrendingUp />}
                color={performanceMetrics?.sharpe_ratio >= 1 ? 'success' : 'warning'}
              />
            </Grid>

            {/* Detailed Performance Metrics */}
            <Grid item xs={12}>
              <Card sx={{ bgcolor: 'background.paper', border: '1px solid rgba(0, 188, 212, 0.2)' }}>
                <CardContent sx={{ p: 3 }}>
                  <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
                    Performance Metrics Details
                  </Typography>
                  <Grid container spacing={3}>
                    <Grid item xs={12} sm={6}>
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" color="text.secondary">
                          Average Profit per Trade
                        </Typography>
                        <Typography variant="h6">
                          ${Math.abs(performanceMetrics?.average_profit || 0).toFixed(2)}
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2" color="text.secondary">
                          Maximum Drawdown
                        </Typography>
                        <Typography variant="h6" color="error">
                          ${Math.abs(performanceMetrics?.max_drawdown || 0).toFixed(2)}
                        </Typography>
                      </Box>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>

        {/* Trades Tab */}
        <TabPanel value={tabValue} index={1}>
          <Card sx={{ bgcolor: 'background.paper', border: '1px solid rgba(0, 188, 212, 0.2)' }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
                Trading History
              </Typography>
              
              {loading.trades ? (
                <Typography>Loading trades...</Typography>
              ) : trades && trades.trades && trades.trades.length > 0 ? (
                <Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {trades.summary.total_trades} trades in the selected period
                  </Typography>
                  
                  {trades.trades.slice(0, 10).map((trade: any, index: number) => (
                    <Box
                      key={trade.id}
                      sx={{
                        border: '1px solid',
                        borderColor: 'divider',
                        borderRadius: 1,
                        mb: 2,
                        p: 2,
                        '&:hover': {
                          background: 'rgba(0, 0, 0, 0.02)',
                        },
                      }}
                    >
                      <Grid container spacing={2}>
                        <Grid item xs={2}>
                          <Typography variant="body2" fontWeight={600}>
                            {trade.symbol}
                          </Typography>
                        </Grid>
                        <Grid item xs={1}>
                          <Typography variant="body2">
                            {trade.type}
                          </Typography>
                        </Grid>
                        <Grid item xs={1}>
                          <Typography variant="body2">
                            {trade.volume}
                          </Typography>
                        </Grid>
                        <Grid item xs={2}>
                          <Typography variant="body2">
                            ${trade.open_price}
                          </Typography>
                        </Grid>
                        <Grid item xs={2}>
                          <Typography variant="body2">
                            {trade.close_price || 'Open'}
                          </Typography>
                        </Grid>
                        <Grid item xs={2}>
                          <Typography
                            variant="body2"
                            color={trade.profit_loss >= 0 ? 'success.main' : 'error.main'}
                            fontWeight={600}
                          >
                            {trade.profit_loss >= 0 ? '+' : ''}
                            ${Math.abs(trade.profit_loss).toFixed(2)}
                          </Typography>
                        </Grid>
                        <Grid item xs={2}>
                          <Typography variant="caption" color="text.secondary">
                            {new Date(trade.opened_at).toLocaleDateString()}
                          </Typography>
                        </Grid>
                      </Grid>
                    </Box>
                  ))}
                  
                  {trades.trades.length > 10 && (
                    <Typography variant="caption" color="text.secondary">
                      Showing first 10 trades. Export for complete history.
                    </Typography>
                  )}
                </Box>
              ) : (
                <Alert severity="info">
                  No trades found in the selected period.
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabPanel>

        {/* Commissions Tab */}
        <TabPanel value={tabValue} index={2}>
          <Card sx={{ bgcolor: 'background.paper', border: '1px solid rgba(0, 188, 212, 0.2)' }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
                Commission History
              </Typography>
              
              {loading.commissions ? (
                <Typography>Loading commissions...</Typography>
              ) : commissions && commissions.total_commission > 0 ? (
                <Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Total Commission Earned: ${commissions.total_commission.toFixed(2)}
                  </Typography>
                  
                  <Grid container spacing={2}>
                    <Grid item xs={4}>
                      <Typography variant="body2">Volume Commissions:</Typography>
                      <Typography variant="h6" color="primary.main">
                        ${commissions.volume_commission.toFixed(2)}
                      </Typography>
                    </Grid>
                    <Grid item xs={4}>
                      <Typography variant="body2">Profit Commissions:</Typography>
                      <Typography variant="h6" color="success.main">
                        ${commissions.profit_commission.toFixed(2)}
                      </Typography>
                    </Grid>
                    <Grid item xs={4}>
                      <Typography variant="body2">Breakdown:</Typography>
                      <Typography variant="body2">
                        Volume: {((commissions.volume_commission / commissions.total_commission) * 100).toFixed(1)}%
                      </Typography>
                    </Grid>
                  </Grid>
                </Box>
              ) : (
                <Alert severity="info">
                  No commissions found in the selected period.
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabPanel>
      </Container>
    </DashboardLayout>
  )
}
