import { useState } from 'react'
import { login, register, saveSession } from '../api'

export function AuthScreen({ onSignedIn }: { onSignedIn: (username: string) => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (busy) return
    setError('')

    if (mode === 'register' && password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }

    setBusy(true)
    try {
      const fn = mode === 'login' ? login : register
      const data = await fn(username.trim(), password)
      saveSession(data.token, data.username)
      onSignedIn(data.username)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <p className="eyebrow">Yale School of Management</p>
        <h1>Course Explorer</h1>
        <p className="auth-sub">
          {mode === 'login'
            ? 'Sign in to pick up your chat where you left off.'
            : 'Create an account to save your chat history.'}
        </p>

        <form onSubmit={submit}>
          <label className="field">
            Username
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              minLength={3}
              required
              autoFocus
            />
          </label>

          <label className="field">
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              minLength={8}
              required
            />
          </label>

          {mode === 'register' && (
            <p className="hint">At least 8 characters.</p>
          )}

          {error && <p className="auth-error">{error}</p>}

          <button className="auth-btn" type="submit" disabled={busy}>
            {busy ? 'Working…' : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>

        <p className="auth-switch">
          {mode === 'login' ? "Don't have an account?" : 'Already have an account?'}{' '}
          <button
            className="link-btn"
            onClick={() => {
              setMode(mode === 'login' ? 'register' : 'login')
              setError('')
            }}
          >
            {mode === 'login' ? 'Create one' : 'Sign in'}
          </button>
        </p>
      </div>
    </div>
  )
}
