import type { Session } from '@supabase/supabase-js'
import { useQuery } from '@tanstack/react-query'
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, setTokenProvider } from './api'
import { supabase } from './supabase'
import type { Me } from './types'

interface AuthState {
  ready: boolean
  session: Session | null
  me: Me | null
  isEngineer: boolean
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

// Client-side lock after 5 failed attempts for 10 minutes (App Flow, A1).
const LOCK_KEY = 'roadsense.loginFailures'
const MAX_FAILURES = 5
const LOCK_MS = 10 * 60 * 1000

export class LoginError extends Error {
  constructor(readonly kind: 'wrong' | 'locked' | 'not_configured') {
    super(kind)
  }
}

function failures(): number[] {
  try {
    const now = Date.now()
    return (JSON.parse(localStorage.getItem(LOCK_KEY) ?? '[]') as number[]).filter(
      (t) => now - t < LOCK_MS,
    )
  } catch {
    return []
  }
}

function recordFailure() {
  try {
    localStorage.setItem(LOCK_KEY, JSON.stringify([...failures(), Date.now()]))
  } catch {
    /* ignore */
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [ready, setReady] = useState(!supabase)

  useEffect(() => {
    if (!supabase) return
    setTokenProvider(async () => (await supabase!.auth.getSession()).data.session?.access_token ?? null)
    void supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
      setReady(true)
    })
    const { data } = supabase.auth.onAuthStateChange((_event, s) => setSession(s))
    return () => data.subscription.unsubscribe()
  }, [])

  const meQuery = useQuery({
    queryKey: ['me', session?.user.id],
    queryFn: () => api<Me>('/me', { auth: true }),
    enabled: !!session,
    staleTime: 5 * 60 * 1000,
  })

  const value = useMemo<AuthState>(
    () => ({
      ready: ready && (!session || !meQuery.isLoading),
      session,
      me: meQuery.data ?? null,
      isEngineer: meQuery.data?.role === 'engineer',
      async signIn(email, password) {
        if (!supabase) throw new LoginError('not_configured')
        if (failures().length >= MAX_FAILURES) throw new LoginError('locked')
        const { error } = await supabase.auth.signInWithPassword({ email, password })
        if (error) {
          recordFailure()
          throw new LoginError(failures().length >= MAX_FAILURES ? 'locked' : 'wrong')
        }
        localStorage.removeItem(LOCK_KEY)
      },
      async signOut() {
        await supabase?.auth.signOut()
      },
    }),
    [ready, session, meQuery.data, meQuery.isLoading],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth outside AuthProvider')
  return ctx
}
