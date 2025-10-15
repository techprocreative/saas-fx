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
} from '@mui/material'
import { Add as AddIcon, PlayArrow, Stop } from '@mui/icons-material'
import { useAppDispatch, useAppSelector } from '../../../src/store/hooks'
import {
  fetchAccounts,
  startTrading,
  stopTrading,
  clearError,
} from '../../../src/store/tradingSlice'
import DashboardLayout from '../../../src/components/Dashboard/DashboardLayout'

export default function TradingPage() {
  const dispatch = useAppDispatch()
  const {
    accounts,
    strategies,
    loading,
    error,
  } = useAppSelector(state => state.trading)

  const [startDialogOpen, setStartDialogOpen] = useState(false)
  const [selectedAccount, setSelectedAccount] = useState('')
  const [selectedStrategy, setSelectedStrategy] = useState('')

  useEffect(() => {
    dispatch(fetchAccounts())
  }, [dispatch])

  const handleOpenStartDialog = () => {
    setStartDialogOpen(true)
    dispatch(clearError())
  }

  const handleCloseStartDialog = () => {
    setStartDialogOpen(false)
    setSelectedAccount('')
    setSelectedStrategy('')
    dispatch(clearError())
  }

  const handleStartTrading = async () => {
    if (!selectedAccount || !selectedStrategy) {
      return
    }

    try {
      await dispatch(startTrading({
        strategy_id: selectedStrategy,
        account_id: selectedAccount,
        is_active: true,
      })).unwrap()
      
      handleCloseStartDialog()
    } catch (error) {
      // Error is handled by Redux state
    }
  }

  const handleStopTrading = async (strategyId: string, accountId: string) => {
    try {
      await dispatch(stopTrading(strategyId)).unwrap()
    } catch (error) {
      // Error is handled by Redux state
    }
  }

  return (
    <DashboardLayout>
      <Container maxWidth="xl">
        <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h4" component="h1" sx={{ fontWeight: 600, mb: 1 }}>
              Trading Management
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Manage your trading accounts and strategies
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleOpenStartDialog}
            sx={{
              background: 'linear-gradient(45deg, #00bcd4 30%, #ff9800 90%)',
              borderRadius: 2,
              px: 4,
            }}
          >
            Add Trading Account
          </Button>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => dispatch(clearError())}>
            {error}
          </Alert>
        )}

        {/* Existing Accounts */}
        <Grid container spacing={3}>
          {loading.accounts ? (
            <Grid item xs={12}>
              <Typography>Loading accounts...</Typography>
            </Grid>
          ) : accounts.length === 0 ? (
            <Grid item xs={12}>
              <Alert severity="info">
                No trading accounts found. Add your MT5 account to start trading with AI strategies.
              </Alert>
            </Grid>
          ) : (
            accounts.map((account) => (
              <Grid item xs={12} md={6} lg={4} key={account.id}>
                <Card
                  sx={{
                    bgcolor: 'background.paper',
                    border: '1px solid rgba(0, 188, 212, 0.2)',
                    transition: 'all 0.3s ease',
                    '&:hover': {
                      boxShadow: '0 8px 32px rgba(0, 188, 212, 0.2)',
                    },
                  }}
                >
                  <CardContent sx={{ p: 3 }}>
                    <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <Box>
                        <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                          {account.mt5_login}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                          {account.broker}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Type: {account.account_type}
                        </Typography>
                      </Box>
                      <Box sx={{ textAlign: 'right' }}>
                        <Typography variant="h6" sx={{ fontWeight: 600, color: 'primary.main' }}>
                          ${parseFloat(account.balance).toFixed(2)}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Balance
                        </Typography>
                      </Box>
                    </Box>

                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Status:{' '}
                          <span
                            style={{
                              color: account.connection_status === 'online' ? '#4caf50' : '#9e9e9e',
                              fontWeight: 600,
                            }}
                          >
                            {account.connection_status.toUpperCase()}
                          </span>
                        </Typography>
                      </Box>
                      <Button
                        variant="outlined"
                        size="small"
                        sx={{
                          borderRadius: 2,
                          color: 'primary.main',
                          borderColor: 'primary.main',
                        }}
                      >
                        Manage EA
                      </Button>
                    </Box>

                    {/* Active strategies for this account */}
                    {strategies && strategies.filter(s => s.status === 'active').length > 0 && (
                      <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                        <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                          Active Strategies:
                        </Typography>
                        {strategies.filter(s => s.status === 'active').map((strategy) => (
                          <Box
                            key={strategy.id}
                            sx={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              mb: 1,
                            }}
                          >
                            <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
                              {strategy.name}
                            </Typography>
                            <Button
                              size="small"
                              color="error"
                              onClick={() => handleStopTrading(strategy.id, account.id)}
                            >
                              <Stop sx={{ fontSize: 16 }} />
                            </Button>
                          </Box>
                        ))}
                      </Box>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            ))
          )}
        </Grid>

        {/* Start Trading Dialog */}
        <Dialog open={startDialogOpen} onClose={handleCloseStartDialog} maxWidth="sm" fullWidth>
          <DialogTitle>Start Automated Trading</DialogTitle>
          <DialogContent>
            <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 3 }}>
              <FormControl fullWidth>
                <InputLabel id="account-select">Trading Account</InputLabel>
                <Select
                  labelId="account-select"
                  label="Trading Account"
                  value={selectedAccount}
                  onChange={(e) => setSelectedAccount(e.target.value)}
                >
                  {accounts.map((account) => (
                    <MenuItem key={account.id} value={account.id}>
                      {account.mt5_login} - {account.broker}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth>
                <InputLabel id="strategy-select">Strategy</InputLabel>
                <Select
                  labelId="strategy-select"
                  label="Strategy"
                  value={selectedStrategy}
                  onChange={(e) => setSelectedStrategy(e.target.value)}
                >
                  {strategies.map((strategy) => (
                    <MenuItem key={strategy.id} value={strategy.id}>
                      {strategy.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {error && (
                <Alert severity="error" onClose={() => dispatch(clearError())}>
                  {error}
                </Alert>
              )}
            </Box>
          </DialogContent>
          <DialogActions sx={{ p: 3 }}>
            <Button onClick={handleCloseStartDialog}>Cancel</Button>
            <LoadingButton
              onClick={handleStartTrading}
              loading={loading.dashboard}
              variant="contained"
              disabled={!selectedAccount || !selectedStrategy}
              startIcon={<PlayArrow />}
            >
              Start Trading
            </LoadingButton>
          </DialogActions>
        </Dialog>
      </Container>
    </DashboardLayout>
  )
}
