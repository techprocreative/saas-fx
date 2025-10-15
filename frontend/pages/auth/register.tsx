import { useState } from 'react'
import { useRouter } from 'next/router'
import Link from 'next/link'
import {
  Box,
  Container,
  Typography,
  TextField,
  Button,
  Alert,
  CircularProgress,
  Paper,
  Checkbox,
  FormControlLabel,
} from '@mui/material'
import { useAuth } from '../../../src/hooks/useAuth'

export default function RegisterPage() {
  const router = useRouter()
  const { register, loading, error } = useAuth()
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    confirmPassword: '',
  })
  const [agreedToTerms, setAgreedToTerms] = useState(false)
  const [errors, setErrors] = useState<{ [key: string]: string }>({})

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
    
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }))
    }
  }

  const validateForm = () => {
    const newErrors: { [key: string]: string } = {}

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required'
    } else if (!emailRegex.test(formData.email)) {
      newErrors.email = 'Please enter a valid email address'
    }

    // Username validation
    if (!formData.username.trim()) {
      newErrors.username = 'Username is required'
    } else if (formData.username.length < 3) {
      newErrors.username = 'Username must be at least 3 characters'
    } else if (formData.username.length > 20) {
      newErrors.username = 'Username must be less than 20 characters'
    }

    // Password validation
    if (!formData.password) {
      newErrors.password = 'Password is required'
    } else if (formData.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters'
    } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(formData.password)) {
      newErrors.password = 'Password must contain uppercase, lowercase, and number'
    }

    // Confirm password validation
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password'
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match'
    }

    // Terms agreement
    if (!agreedToTerms) {
      newErrors.terms = 'You must agree to the terms and conditions'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    try {
      await register(formData.email, formData.username, formData.password)
      router.push('/dashboard')
    } catch (error) {
      // Error is handled by the useAuth hook
    }
  }

  return (
    <Container component="main" maxWidth="sm">
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          py: 4,
        }}
      >
        <Paper
          elevation={24}
          sx={{
            p: 4,
            borderRadius: 2,
            background: 'linear-gradient(145deg, #151929 0%, #1e2338 100%)',
            border: '1px solid rgba(0, 188, 212, 0.2)',
          }}
        >
          <Box sx={{ textAlign: 'center', mb: 4 }}>
            <Typography
              variant="h4"
              component="h1"
              sx={{
                fontWeight: 700,
                mb: 1,
                background: 'linear-gradient(45deg, #00bcd4 30%, #ff9800 90%)',
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                color: 'transparent',
              }}
            >
              Create Account
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Join thousands of traders using AI-powered strategies
            </Typography>
          </Box>

          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit} sx={{ mb: 3 }}>
            <TextField
              fullWidth
              label="Email Address"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              error={!!errors.email}
              helperText={errors.email}
              disabled={loading}
              sx={{ mb: 2 }}
              InputProps={{
                sx: {
                  bgcolor: 'rgba(0, 188, 212, 0.05)',
                }
              }}
            />

            <TextField
              fullWidth
              label="Username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              error={!!errors.username}
              helperText={errors.username}
              disabled={loading}
              sx={{ mb: 2 }}
              InputProps={{
                sx: {
                  bgcolor: 'rgba(0, 188, 212, 0.05)',
                }
              }}
            />

            <TextField
              fullWidth
              label="Password"
              name="password"
              type="password"
              value={formData.password}
              onChange={handleChange}
              error={!!errors.password}
              helperText={errors.password}
              disabled={loading}
              sx={{ mb: 2 }}
              InputProps={{
                sx: {
                  bgcolor: 'rgba(0, 188, 212, 0.05)',
                }
              }}
            />

            <TextField
              fullWidth
              label="Confirm Password"
              name="confirmPassword"
              type="password"
              value={formData.confirmPassword}
              onChange={handleChange}
              error={!!errors.confirmPassword}
              helperText={errors.confirmPassword}
              disabled={loading}
              sx={{ mb: 3 }}
              InputProps={{
                sx: {
                  bgcolor: 'rgba(0, 188, 212, 0.05)',
                }
              }}
            />

            <FormControlLabel
              control={
                <Checkbox
                  checked={agreedToTerms}
                  onChange={(e) => {
                    setAgreedToTerms(e.target.checked)
                    if (errors.terms) {
                      setErrors(prev => ({ ...prev, terms: '' }))
                    }
                  }}
                  disabled={loading}
                  sx={{
                    color: 'primary.main',
                  }}
                />
              }
              label={
                <Box component="span">
                  I agree to the{' '}
                  <Link href="/terms" passHref>
                    <Typography
                      component="span"
                      sx={{
                        color: 'primary.main',
                        textDecoration: 'none',
                        '&:hover': {
                          textDecoration: 'underline',
                        },
                      }}
                    >
                      Terms of Service
                    </Typography>
                  </Link>{' '}
                  and{' '}
                  <Link href="/privacy" passHref>
                    <Typography
                      component="span"
                      sx={{
                        color: 'primary.main',
                        textDecoration: 'none',
                        '&:hover': {
                          textDecoration: 'underline',
                        },
                      }}
                    >
                      Privacy Policy
                    </Typography>
                  </Link>
                </Box>
              }
              sx={{ mb: 3 }}
            />
            {errors.terms && (
              <Typography variant="caption" color="error" sx={{ mb: 2, display: 'block' }}>
                {errors.terms}
              </Typography>
            )}

            <Button
              type="submit"
              fullWidth
              variant="contained"
              size="large"
              disabled={loading}
              sx={{
                mb: 3,
                background: 'linear-gradient(45deg, #00bcd4 30%, #ff9800 90%)',
                py: 1.5,
                borderRadius: 2,
              }}
            >
              {loading ? (
                <CircularProgress size={24} color="inherit" />
              ) : (
                'Create Account'
              )}
            </Button>
          </Box>

          <Box sx={{ textAlign: 'center' }}>
            <Link href="/auth/login" passHref>
              <Typography
                variant="body2"
                sx={{
                  color: 'primary.main',
                  textDecoration: 'none',
                  fontWeight: 600,
                  '&:hover': {
                    textDecoration: 'underline',
                  },
                }}
              >
                Already have an account? Sign In
              </Typography>
            </Link>
          </Box>
        </Paper>
      </Box>
    </Container>
  )
}
