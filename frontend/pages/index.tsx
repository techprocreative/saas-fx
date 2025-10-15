import { useEffect } from 'react'
import { useRouter } from 'next/router'
import { Box, Container, Typography, Button, Grid, Card, CardContent } from '@mui/material'
import { useAuth } from '../src/hooks/useAuth'
import { TrendingUp, AccountBalanceWallet, Speed, Psychology } from '@mui/icons-material'

const features = [
  {
    icon: <Psychology sx={{ fontSize: 40, color: 'primary.main' }} />,
    title: 'AI-Powered Strategies',
    description: 'Generate trading strategies using advanced AI models like GPT-4 and Claude'
  },
  {
    icon: <Speed sx={{ fontSize: 40, color: 'primary.main' }} />,
    title: 'Real-Time Signals',
    description: 'Receive instant trading signals directly in your MetaTrader 5 terminal'
  },
  {
    icon: <AccountBalanceWallet sx={{ fontSize: 40, color: 'primary.main' }} />,
    title: 'Smart Risk Management',
    description: 'Automated position sizing and risk controls powered by AI supervision'
  },
  {
    icon: <TrendingUp sx={{ fontSize: 40, color: 'primary.main' }} />,
    title: 'Performance Analytics',
    description: 'Comprehensive analytics dashboard with real-time profit/loss tracking'
  }
]

export default function HomePage() {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (user && !loading) {
      router.push('/dashboard')
    }
  }, [user, loading, router])

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <Typography>Loading...</Typography>
      </Box>
    )
  }

  if (user) {
    return null // Will redirect to dashboard
  }

  return (
    <Box>
      {/* Hero Section */}
      <Box
        sx={{
          bgcolor: 'background.paper',
          minHeight: '80vh',
          display: 'flex',
          alignItems: 'center',
          position: 'relative',
          overflow: 'hidden',
          '&::before': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'linear-gradient(135deg, rgba(0, 188, 212, 0.1) 0%, rgba(255, 152, 0, 0.1) 100%)',
            zIndex: 1,
          }
        }}
      >
        <Container maxWidth="lg" sx={{ position: 'relative', zIndex: 2 }}>
          <Grid container spacing={6} alignItems="center">
            <Grid item xs={12} md={6}>
              <Typography variant="h2" sx={{ fontWeight: 700, mb: 3, color: 'primary.main' }}>
                Forex AI Trading Platform
              </Typography>
              <Typography variant="h5" sx={{ mb: 4, color: 'text.secondary', lineHeight: 1.6 }}>
                Transform your trading with AI-powered strategies. Generate, automate, and optimize your forex trading with cutting-edge machine learning.
              </Typography>
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                <Button
                  variant="contained"
                  size="large"
                  onClick={() => router.push('/auth/register')}
                  sx={{
                    background: 'linear-gradient(45deg, #00bcd4 30%, #ff9800 90%)',
                    borderRadius: 2,
                    px: 4,
                    py: 1.5,
                  }}
                >
                  Get Started Free
                </Button>
                <Button
                  variant="outlined"
                  size="large"
                  onClick={() => router.push('/auth/login')}
                  sx={{
                    borderRadius: 2,
                    px: 4,
                    py: 1.5,
                    borderColor: 'primary.main',
                    color: 'primary.main',
                  }}
                >
                  Login
                </Button>
              </Box>
            </Grid>
            <Grid item xs={12} md={6}>
              {/* Trading Chart Placeholder */}
              <Box
                sx={{
                  height: 400,
                  bgcolor: 'background.default',
                  borderRadius: 2,
                  border: '2px solid',
                  borderColor: 'primary.main',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  position: 'relative',
                }}
              >
                <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', px: 2 }}>
                  Real-time Trading Charts<br/>
                  EUR/USD, GBP/USD, XAUUSD<br/>
                  Multiple Timeframes
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* Features Section */}
      <Container maxWidth="lg" sx={{ py: 8 }}>
        <Typography variant="h3" align="center" sx={{ mb: 6, fontWeight: 600 }}>
          Why Choose Our AI Trading Platform?
        </Typography>
        <Grid container spacing={4}>
          {features.map((feature, index) => (
            <Grid item xs={12} sm={6} md={3} key={index}>
              <Card
                sx={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  textAlign: 'center',
                  p: 3,
                  bgcolor: 'background.paper',
                  border: '1px solid',
                  borderColor: 'divider',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 8px 32px rgba(0, 188, 212, 0.2)',
                  }
                }}
              >
                <Box sx={{ mb: 2 }}>
                  {feature.icon}
                </Box>
                <Typography variant="h6" sx={{ mb: 1, fontWeight: 600 }}>
                  {feature.title}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {feature.description}
                </Typography>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Container>

      {/* How It Works */}
      <Box sx={{ py: 8, bgcolor: 'background.paper' }}>
        <Container maxWidth="lg">
          <Typography variant="h3" align="center" sx={{ mb: 6, fontWeight: 600 }}>
            How It Works
          </Typography>
          <Grid container spacing={4}>
            {[
              { step: 1, title: 'Create Account', desc: 'Sign up and connect your MT5 account' },
              { step: 2, title: 'Download EA', desc: 'Install our PyTrader EA in MetaTrader 5' },
              { step: 3, title: 'Generate Strategy', desc: 'Create AI-powered trading strategies' },
              { step: 4, title: 'Start Trading', desc: 'Receive signals automatically in real-time' }
            ].map((item) => (
              <Grid item xs={12} sm={6} md={3} key={item.step}>
                <Box textAlign="center">
                  <Box
                    sx={{
                      width: 60,
                      height: 60,
                      borderRadius: '50%',
                      bgcolor: 'primary.main',
                      color: 'white',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      margin: '0 auto 16px',
                      fontSize: '1.5rem',
                      fontWeight: 'bold'
                    }}
                  >
                    {item.step}
                  </Box>
                  <Typography variant="h6" sx={{ mb: 1, fontWeight: 600 }}>
                    {item.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {item.desc}
                  </Typography>
                </Box>
              </Grid>
            ))}
          </Grid>
        </Container>
      </Box>
    </Box>
  )
}
