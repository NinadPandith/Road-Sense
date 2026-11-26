// Tracking codes saved on this phone (App Flow, Flow 2: "My reports").

const KEY = 'roadsense.myReports'

export interface SavedReport {
  code: string
  createdAt: string
  thumbUrl: string | null
}

export function loadMyReports(): SavedReport[] {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as SavedReport[]) : []
  } catch {
    return []
  }
}

export function saveMyReport(r: SavedReport): void {
  try {
    const list = loadMyReports().filter((x) => x.code !== r.code)
    list.unshift(r)
    localStorage.setItem(KEY, JSON.stringify(list.slice(0, 50)))
  } catch {
    /* storage blocked: tracking still works with the code */
  }
}
