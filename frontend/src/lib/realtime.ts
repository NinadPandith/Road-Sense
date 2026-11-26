import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { supabase } from './supabase'

/** Live dashboard: refresh defect lists and KPIs when a defect is inserted or updated
 * (Supabase Realtime on the defects table; RLS limits events to signed-in staff). */
export function useRealtimeDefects(enabled: boolean): void {
  const qc = useQueryClient()
  useEffect(() => {
    if (!enabled || !supabase) return
    let timer: number | undefined
    const refresh = () => {
      window.clearTimeout(timer)
      timer = window.setTimeout(() => {
        void qc.invalidateQueries({ queryKey: ['defects'] })
        void qc.invalidateQueries({ queryKey: ['stats'] })
      }, 1000)
    }
    const channel = supabase
      .channel('defects-live')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'defects' }, refresh)
      .subscribe()
    return () => {
      window.clearTimeout(timer)
      void supabase?.removeChannel(channel)
    }
  }, [enabled, qc])
}
