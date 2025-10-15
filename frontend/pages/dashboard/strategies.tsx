import { useState } from 'react'
import {
  Box,
  Container,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  LoadingButton,
  Chip,
  IconButton,
  Tooltip,
} from '@mui/material'
import {
  Add as AddIcon,
  PlayArrow,
  Stop,
  Delete,
  Edit,
  Psychology,
} from '@mui/icons-material'
import { useAppDispatch, useAppSelector } from '../../../src/store/hooks'
import {
  fetchStrategies,
  generateAIStrategy,
  clearError,
} from '../../../src/store/tradingSlice'
import DashboardLayout from '../../../src/components/Dashboard/DashboardLayout'

export default function StrategiesPage() {
  const dispatch = useAppDispatch()
  const {
    strategies,
    loading,
    error,
  } = useAppSelector(state => state.trading)

  const [generateDialogOpen, setGenerateDialogOpen] = useState(false)
  const [strategyForm, setStrategyForm] = useState({
    name: '',
    llm_model: 'claude-3-opus',
    user_preferences: {
      risk_level: 'medium',
      trading_style: 'swing',
      timeframes: ['H1', 'H4'],
      max_risk_percent: 2.0,
      preferred_pairs: ['EURUSD', 'GBPUSD', 'XAUUSD'],
    },
  })

  useEffect(() => {
    dispatch(fetchStrategies())
  }, [dispatch])

  const handleOpenGenerateDialog = () => {
    setGenerateDialogOpen(true)
    dispatch(clearError())
  }

  const handleCloseGenerateDialog = () => {
    setGenerateDialogOpen(false)
    setStrategyForm({
      name: '',
      llm_model: 'claude-3-opus',
      user_preferences: {
        risk_level: 'medium',
        trading_style: 'swing',
        timeframes: ['H1', 'H4'],
        max_risk_percent: 2.0,
        preferred_pairs: ['EURUSD', 'GBPUSD', 'XAUUSD'],
      },
    })
    dispatch(clearError())
  }

  const handleGenerateStrategy = async () => {
    if (!strategyForm.name) {
      return
    }

    try {
      await dispatch(generateAIStrategy(strategyForm)).unwrap()
      handleCloseGenerateDialog()
      await dispatch(fetchStrategies()) // Refresh strategies list
    } catch (error) {
      // Error is handled by Redux state
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success'
      case 'inactive':
        return 'default'
      case 'deleted':
        return 'error'
      default:
        return 'default'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <PlayArrow />
      case 'inactive':
        return <Stop />
      case 'deleted':
        return <Delete />
      default:
        return <Psychology />
    }
  }

  if (loading.strategies && strategies.length === 0) {
    return (
      <DashboardLayout>
        <Container maxWidth="xl">
          <Typography>Loading strategies...</Typography>
        </Container>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <Container maxWidth="xl">
        <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h4" component="h1" sx={{ fontWeight: 600, mb: 1 }}>
              AI Trading Strategies
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Create and manage AI-powered trading strategies
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleOpenGenerateDialog}
            sx={{
              background: 'linear-gradient(45deg, #00bcd4 30%, #ff9800 90%)',
              borderRadius: 2,
              px: 4,
            }}
          >
            Generate AI Strategy
          </Button>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => dispatch(clearError())}>
            {error}
          </Alert>
        )}

        <Grid container spacing={3}>
          {strategies.map((strategy) => (
            <Grid item xs={12} md={6} lg={4} key={strategy.id}>
              <Card
                sx={{
                  bgcolor: 'background.paper',
                  border: '1px solid rgba(0, 188, 212, 0.2)',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    boxShadow: '0 8px 32px rgba(0, 188, 212, 0.2)',
                    transform: 'translateY(-4px)',
                  },
                }}
              >
                <CardContent sx={{ p: 3 }}>
                  <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <Box sx={{ flexGrow: 1 }}>
                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                        {strategy.name}
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          Model:
                        </Typography>
                        <Chip
                          label={strategy.llm_model}
                          size="small"
                          color="primary"
                          variant="outlined"
                        />
                      </Box>
                      <Typography variant="caption" color="text.secondary">
                        Created: {new Date(strategy.created_at).toLocaleDateString()}
                      </Typography>
                    </Box>
                    <Tooltip title={strategy.status}>
                      <Chip
                        icon={getStatusIcon(strategy.status)}
                        label={strategy.status.toUpperCase()}
                        color={getStatusColor(strategy.status)}
                        size="small"
                        sx={{ fontweight: 600 }}
                      />
                    </Tooltip>
                  </Box>

                  {/* Performance Metrics */}
                  {strategy.performance_metrics && Object.keys(strategy.performance_metrics).length > 0 && (
                    <Box sx={{ mb: 3, p: 2, bgcolor: 'rgba(0, 0, 0, 0.02)', borderRadius: 1 }}>
                      <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                        Expected Performance:
                      </Typography>
                      <Grid container spacing={2} sx={{ fontSize: '0.875rem' }}>
                        <Grid item xs={6}>
                          <Typography variant="body2">
                            Win Rate: {strategy.performance_metrics.win_rate}%
                          </Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2">
                            Profit Factor: {strategy.performance_metrics.profit_factor}
                          </Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2">
                            Max Drawdown: {strategy.performance_metrics.max_drawdown}%
                          </Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2">
                            Sharpe Ratio: {strategy.performance_metrics.sharpe_ratio}
                          </Typography>
                        </Grid>
                      </Grid>
                    </Box>
                  )}

                  {/* Strategy Configuration Preview */}
                  {strategy.strategy_config && (
                    <Box sx={{ mb: 3, p: 2, bgcolor: 'rgba(0, 0, 0, 0.02)', borderRadius: 1 }}>
                      <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                        Strategy Configuration:
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        {strategy.strategy_config.timeframes && (
                          strategy.strategy_config.timeframes.map((tf: string, idx: number) => (
                            <Chip
                              key={idx}
                              label={tf}
                              size="small"
                              color="secondary"
                              variant="outlined"
                            />
                          ))
                        )}
                      </Box>
                    </Box>
                  )}

                  {/* Action Buttons */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Tooltip title="Edit Strategy">
                        <IconButton size="small" color="primary">
                          <Edit />
                        </IconButton>
                      </Tooltip>
                      {strategy.status === 'active' ? (
                        <Tooltip title="Stop Strategy">
                          <IconButton size="small" color="error">
                            <Stop />
                          </IconButton>
                        </Tooltip>
                      ) : strategy.status === 'inactive' ? (
                        <Tooltip title="Start Strategy">
                          <IconButton size="small" color="success">
                            <PlayArrow />
                          </IconButton>
                        </Tooltip>
                      ) : null}
                    </Box>
                    <Button
                      size="small"
                      variant="outlined"
                      color="error"
                      startIcon={<Delete />}
                      sx={{ borderRadius: 2 }}
                    >
                      Delete
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}

          {strategies.length === 0 && !loading.strategies && (
            <Grid item xs={12}>
              <Card sx={{ bgcolor: 'background.paper', border: '1px solid rgba(0, 188, 212, 0.2)' }}>
                <CardContent sx={{ textAlign: 'center', py: 6 }}>
                  <Psychology sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                  <Typography variant="h6" sx={{ mb: 1, color: 'text.secondary' }}>
                    No Strategies Yet
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    Create your first AI-powered trading strategy to start automated trading.
                  </Typography>
                  <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={handleOpenGenerateDialog}
                    sx={{
                      background: 'linear-gradient(45deg, #00bcd4 30%, #ff9800 90%)',
                      borderRadius: 2,
                    }}
                  >
                    Create Your First Strategy
                  </Button>
                </CardContent>
              </Card>
            </Grid>
          )}
        </Grid>

        {/* Generate Strategy Dialog */}
        <Dialog open={generateDialogOpen} onClose={handleCloseGenerateDialog} maxWidth="md" fullWidth>
          <DialogTitle>Generate AI Trading Strategy</DialogTitle>
          <DialogContent>
            <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 3 }}>
              <TextField
                label="Strategy Name"
                value={strategyForm.name}
                onChange={(e) => setStrategyForm(prev => ({ ...prev, name: e.target.value }))}
                fullWidth
                required
              />

              <FormControl fullWidth>
                <InputLabel>AI Model</InputLabel>
                <Select
                  value={strategyForm.llm_model}
                  onChange={(e) => setStrategyForm(prev => ({ ...prev, llm_model: e.target.value }))}
                  label="AI Model"
                >
                  <MenuItem value="claude-3-opus">Claude 3 Opus</MenuItem>
                  <MenuItem value="gpt-4">GPT-4</MenuItem>
                  <MenuItem value="llama-2">LLaMA 2</MenuItem>
                  <MenuItem value="gemini-pro">Gemini Pro</MenuItem>
                </Select>
              </FormControl>

              <FormControl fullWidth>
                <InputLabel>Risk Level</InputLabel>
                <Select
                  value={strategyForm.user_preferences.risk_level}
                  onChange={(e) => setStrategyForm(prev => ({
                    ...prev,
                    user_preferences: {
                      ...prev.user_preferences,
                      risk_level: e.target.value
                    }
                  }))}
                  label="Risk Level"
                >
                  <MenuItem value="conservative">Conservative</MenuItem>
                  <MenuItem value="medium">Medium</MenuItem>
                  <MenuItem value="aggressive">Aggressive</MenuItem>
                </Select>
              </FormControl>

              <FormControl fullWidth>
                <InputLabel>Trading Style</InputLabel>
                <Select
                  value={strategyForm.user_preferences.trading_style}
                  onChange={(e) => setStrategyForm(prev => ({
                    ...prev,
                    user_preferences: {
                      ...prev.user_preferences,
                      trading_style: e.target.value
                    }
                  }))}
                  label="Trading Style"
                >
                  <MenuItem value="scalping">Scalping</MenuItem>
                  <MenuItem value="day-trading">Day Trading</MenuItem>
                  <MenuItem value="swing">Swing Trading</MenuItem>
                  <MenuItem value="position">Position Trading</MenuItem>
                </Select>
              </FormControl>

              <TextField
                label="Max Risk per Trade (%)"
                type="number"
                value={strategyForm.user_preferences.max_risk_percent}
                onChange={(e) => setStrategyForm(prev => ({
                  ...prev,
                  user_preferences: {
                    ...prev.user_preferences,
                    max_risk_percent: parseFloat(e.target.value)
                  }
                }))}
                fullWidth
                inputProps={{ min: 0.1, max: 5, step: 0.1 }}
              />

              {error && (
                <Alert severity="error" onClose={() => dispatch(clearError())}>
                  {error}
                </Alert>
              )}
            </Box>
          </DialogContent>
          <DialogActions sx={{ p: 3 }}>
            <Button onClick={handleCloseGenerateDialog}>Cancel</Button>
            <LoadingButton
              onClick={handleGenerateStrategy}
              loading={loading.strategies}
              variant="contained"
              disabled={!strategyForm.name}
              startIcon={<Psychology />}
            >
              Generate Strategy
            </LoadingButton>
          </DialogActions>
        </Dialog>
      </Container>
    </DashboardLayout>
  )
}
