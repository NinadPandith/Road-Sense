import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'
import { allDefects, type Filters } from './admin'
import { formatDate } from './format'
import i18n from './i18n'

async function toDataUrl(url: string): Promise<string | null> {
  try {
    const res = await fetch(url)
    if (!res.ok) return null
    const blob = await res.blob()
    return await new Promise((resolve) => {
      const r = new FileReader()
      r.onload = () => resolve(r.result as string)
      r.onerror = () => resolve(null)
      r.readAsDataURL(blob)
    })
  } catch {
    return null
  }
}

/** Work-order PDF: rank, location link, photo, severity (App Flow, A3). */
export async function exportWorkOrderPdf(filters: Filters, max = 50): Promise<void> {
  const t = i18n.t.bind(i18n)
  const defects = (await allDefects(filters, max)).slice(0, max)
  const photos = await Promise.all(defects.map((d) => (d.thumb_url ? toDataUrl(d.thumb_url) : null)))

  const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' })
  doc.setFontSize(16)
  doc.text(`RoadSense · ${t('admin.nav.repairs')}`, 14, 14)
  doc.setFontSize(10)
  doc.text(formatDate(new Date()), 14, 20)

  autoTable(doc, {
    startY: 25,
    head: [[t('admin.rank'), t('admin.photo'), t('admin.type'), t('admin.severity'), t('admin.priority'), t('admin.roadCol'), t('admin.ward'), 'Map']],
    body: defects.map((d) => [
      d.rank ? `#${d.rank}` : '–',
      '',
      d.damage_class ? t(`damage.${d.damage_class}`) : t('damage.unknown'),
      d.severity_label ? t(`severity.${d.severity_label}`) : t('severity.unscored'),
      d.priority_reason,
      d.road_name ?? t(`road.${d.road_class}`),
      d.ward?.name ?? '–',
      `${d.lat.toFixed(5)}, ${d.lon.toFixed(5)}`,
    ]),
    styles: { fontSize: 9, cellPadding: 2, minCellHeight: 18, valign: 'middle' },
    columnStyles: { 1: { cellWidth: 26 }, 4: { cellWidth: 70 } },
    didDrawCell: (data) => {
      if (data.section !== 'body') return
      const d = defects[data.row.index]
      if (data.column.index === 1) {
        const img = photos[data.row.index]
        if (img) doc.addImage(img, 'JPEG', data.cell.x + 1, data.cell.y + 1, 24, data.cell.height - 2)
      }
      if (data.column.index === 7) {
        doc.link(data.cell.x, data.cell.y, data.cell.width, data.cell.height, {
          url: `https://www.openstreetmap.org/?mlat=${d.lat}&mlon=${d.lon}#map=19/${d.lat}/${d.lon}`,
        })
      }
    },
  })
  doc.save(`roadsense-work-order-${new Date().toISOString().slice(0, 10)}.pdf`)
}
