import { useForm } from 'react-hook-form'
import { useMutation } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { authAPI } from '../api/client'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'
import { Loader2, Heart, Eye, EyeOff } from 'lucide-react'
import { useState } from 'react'

// ── Helper: safely extract a string from any FastAPI error shape ─────────────
function extractErrorMessage(err, fallback = 'Something went wrong') {
  const detail = err?.response?.data?.detail
  if (!detail) return err?.message || fallback
  // Pydantic 422 returns detail as an array of {loc, msg, type, ...}
  if (Array.isArray(detail)) {
    return detail.map(d => {
      const field = Array.isArray(d.loc) ? d.loc.slice(1).join(' → ') : ''
      return field ? `${field}: ${d.msg}` : d.msg
    }).join(' · ')
  }
  // Plain string detail
  if (typeof detail === 'string') return detail
  // Object with message key
  if (typeof detail === 'object' && detail.msg) return detail.msg
  return fallback
}

// ── Login ────────────────────────────────────────────────────────────────────

export function LoginPage() {
  const { register, handleSubmit, formState: { errors } } = useForm()
  const { login } = useAuthStore()
  const navigate   = useNavigate()
  const [showPw, setShowPw] = useState(false)

  const mutation = useMutation({
    mutationFn: (data) => authAPI.login(data).then(r => r.data),
    onSuccess: (data) => {
      login(data.access_token, data.user)
      toast.success(`Welcome back, ${data.user.username}!`)
      navigate('/')
    },
    onError: (err) => toast.error(extractErrorMessage(err, 'Login failed')),
  })

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-brand-50 px-4">
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-lg mb-4">
            <Heart className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900">MedPredict</h1>
          <p className="text-slate-500 text-sm mt-1">Multi-Disease Prediction System</p>
        </div>

        <div className="card p-8">
          <h2 className="text-xl font-bold text-slate-900 mb-6">Sign in to your account</h2>
          <form onSubmit={handleSubmit(d => mutation.mutate(d))} className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-slate-600 mb-1.5">Username</label>
              <input
                type="text"
                placeholder="admin"
                autoComplete="username"
                {...register('username', { required: 'Required' })}
                className="input-field"
              />
              {errors.username && <p className="text-xs text-red-500 mt-1">{errors.username.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-600 mb-1.5">Password</label>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  {...register('password', { required: 'Required' })}
                  className="input-field pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && <p className="text-xs text-red-500 mt-1">{errors.password.message}</p>}
            </div>

            {/* Server error banner */}
            {mutation.isError && (
              <div className="rounded-xl bg-red-50 border border-red-200 px-3 py-2.5 text-sm text-red-700">
                {extractErrorMessage(mutation.error, 'Login failed')}
              </div>
            )}

            <button
              type="submit"
              disabled={mutation.isPending}
              className="btn-primary w-full flex justify-center items-center gap-2 mt-2"
            >
              {mutation.isPending
                ? <><Loader2 className="w-4 h-4 animate-spin" />Signing in…</>
                : 'Sign In'
              }
            </button>
          </form>

          <p className="text-center text-sm text-slate-500 mt-5">
            No account?{' '}
            <Link to="/register" className="text-brand-600 font-semibold hover:underline">Create one</Link>
          </p>
          <div className="mt-4 p-3 bg-slate-50 rounded-xl text-xs text-slate-500 text-center">
            Default admin: <strong>admin</strong> / <strong>admin123</strong>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Register ─────────────────────────────────────────────────────────────────

export function RegisterPage() {
  const { register, handleSubmit, formState: { errors } } = useForm()
  const navigate = useNavigate()

  const mutation = useMutation({
    mutationFn: (data) => authAPI.register(data).then(r => r.data),
    onSuccess: () => {
      toast.success('Account created! Please sign in.')
      navigate('/login')
    },
    onError: (err) => toast.error(extractErrorMessage(err, 'Registration failed')),
  })

  const fields = [
    {
      name: 'username', label: 'Username', type: 'text',
      placeholder: 'johndoe',
      autoComplete: 'username',
      rules: { required: 'Required', minLength: { value: 3, message: 'Min 3 characters' } },
    },
    {
      name: 'email', label: 'Email', type: 'email',
      placeholder: 'john@example.com',
      autoComplete: 'email',
      rules: {
        required: 'Required',
        pattern: { value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: 'Enter a valid email' },
      },
    },
    {
      name: 'password', label: 'Password', type: 'password',
      placeholder: '••••••••',
      autoComplete: 'new-password',
      rules: { required: 'Required', minLength: { value: 6, message: 'Min 6 characters' } },
    },
  ]

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-brand-50 px-4">
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-lg mb-4">
            <Heart className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900">MedPredict</h1>
          <p className="text-slate-500 text-sm mt-1">Create your account</p>
        </div>

        <div className="card p-8">
          <h2 className="text-xl font-bold text-slate-900 mb-6">Create account</h2>
          <form onSubmit={handleSubmit(d => mutation.mutate(d))} className="space-y-4">
            {fields.map(({ name, label, type, placeholder, autoComplete, rules }) => (
              <div key={name}>
                <label className="block text-sm font-semibold text-slate-600 mb-1.5">{label}</label>
                <input
                  type={type}
                  placeholder={placeholder}
                  autoComplete={autoComplete}
                  {...register(name, rules)}
                  className="input-field"
                />
                {errors[name] && (
                  <p className="text-xs text-red-500 mt-1">{errors[name].message}</p>
                )}
              </div>
            ))}

            {/* Server error banner */}
            {mutation.isError && (
              <div className="rounded-xl bg-red-50 border border-red-200 px-3 py-2.5 text-sm text-red-700">
                {extractErrorMessage(mutation.error, 'Registration failed')}
              </div>
            )}

            <button
              type="submit"
              disabled={mutation.isPending}
              className="btn-primary w-full flex justify-center items-center gap-2 mt-2"
            >
              {mutation.isPending
                ? <><Loader2 className="w-4 h-4 animate-spin" />Creating account…</>
                : 'Create Account'
              }
            </button>
          </form>

          <p className="text-center text-sm text-slate-500 mt-5">
            Already have an account?{' '}
            <Link to="/login" className="text-brand-600 font-semibold hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}


