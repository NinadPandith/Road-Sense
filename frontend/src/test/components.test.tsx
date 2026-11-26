import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { SeverityBadge } from '../components/Badges'
import { FactorBars } from '../components/FactorBars'
import { ResultPage } from '../pages/citizen/ResultPage'
import { TrackPage } from '../pages/citizen/TrackPage'
import type { ReportResult } from '../lib/types'

function wrap(ui: React.ReactNode, path = '/', route = '*', state?: unknown) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[{ pathname: path, state }]}>
        <Routes>
          <Route path={route} element={ui} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const merged: ReportResult = {
  tracking_code: 'RS-7K2Q',
  status: 'done',
  outcome: 'merged',
  defect_id: 'd1',
  report_count: 4,
  damage_class: 'pothole',
  confidence_label: 'very_likely',
  severity: {
    label: 'dangerous',
    score: 0.82,
    factors: { size: 0.74, depth: 0.88, type: 1, position: 0.9 },
    reason: 'large, looks deep and in the wheel path',
  },
  boxes: [],
  thumb_url: null,
  image_url: null,
}

describe('SeverityBadge', () => {
  it('shows a word, not only a colour', () => {
    render(<SeverityBadge label="dangerous" />)
    expect(screen.getByText('Dangerous')).toBeInTheDocument()
  })
})

describe('FactorBars', () => {
  it('labels each bar for citizens without numbers', () => {
    render(<FactorBars factors={{ size: 0.2, depth: null, type: 1, position: 0.5 }} />)
    expect(screen.getByRole('meter', { name: 'Size' })).toHaveAttribute('aria-valuetext', 'Low')
    expect(screen.getByRole('meter', { name: 'Depth' })).toHaveAttribute('aria-valuetext', 'Not measured')
    expect(screen.queryByText('(0.20)')).not.toBeInTheDocument()
  })
})

describe('ResultPage (P4)', () => {
  it('shows the merged copy, severity and tracking code', () => {
    wrap(<ResultPage />, '/report/result/RS-7K2Q', '/report/result/:code', { result: merged })
    expect(screen.getByText('Thanks! Added to an existing report.')).toBeInTheDocument()
    expect(screen.getByText('4 people have reported this spot. More reports help it get fixed sooner.')).toBeInTheDocument()
    expect(screen.getByText('Dangerous because it is large, looks deep and in the wheel path.')).toBeInTheDocument()
    expect(screen.getByText('RS-7K2Q')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Copy tracking code' })).toBeInTheDocument()
  })

  it('offers Retake and Send anyway when no damage was found', () => {
    wrap(<ResultPage />, '/report/result/RS-7K2Q', '/report/result/:code', {
      result: { ...merged, outcome: 'no_damage', severity: null, damage_class: null },
    })
    expect(screen.getByText(/couldn't find road damage/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retake photo' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send anyway' })).toBeInTheDocument()
  })
})

describe('TrackPage (P5)', () => {
  it('shows the empty state for a phone with no reports', () => {
    localStorage.clear()
    wrap(<TrackPage />, '/track', '/track')
    expect(screen.getByText("You haven't reported anything from this phone yet.")).toBeInTheDocument()
  })

  it('shows the wrong-code message', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ error: { code: 'not_found', message: 'x' } }), { status: 404 }),
      ),
    )
    wrap(<TrackPage />, '/track/RS-ZZZZ', '/track/:code')
    expect(await screen.findByText('No report found with this code. Check it and try again.')).toBeInTheDocument()
    vi.unstubAllGlobals()
  })
})
