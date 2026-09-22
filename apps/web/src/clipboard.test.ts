import { afterEach, expect, it, vi } from 'vitest'

import { copyImage, copyText, downloadImage } from './clipboard'

afterEach(() => vi.unstubAllGlobals())

it('copies text through the clipboard api', async () => {
  const writeText = vi.fn(async () => undefined)
  vi.stubGlobal('navigator', { clipboard: { writeText } })

  await copyText('안녕하세요')

  expect(writeText).toHaveBeenCalledWith('안녕하세요')
})

it('copies an image by fetching it and writing a clipboard item', async () => {
  const blob = new Blob(['png'], { type: 'image/png' })
  const write = vi.fn(async () => undefined)
  vi.stubGlobal('navigator', { clipboard: { write } })
  vi.stubGlobal('fetch', vi.fn(async () => new Response(blob, { headers: { 'Content-Type': 'image/png' } })))
  vi.stubGlobal('ClipboardItem', class { constructor(public items: Record<string, Blob>) {} })

  await copyImage('/api/messages/report.png')

  expect(write).toHaveBeenCalledOnce()
  const [items] = write.mock.calls[0] as unknown as [{ items: Record<string, Blob> }[]]
  expect(Object.keys(items[0].items)).toEqual(['image/png'])
})

it('downloads an image with the given file name', async () => {
  const click = vi.fn()
  const anchor = { click, href: '', download: '' } as unknown as HTMLAnchorElement
  vi.spyOn(document, 'createElement').mockReturnValueOnce(anchor)

  downloadImage('/api/messages/report.png', '리포트.png')

  expect(anchor.download).toBe('리포트.png')
  expect(click).toHaveBeenCalledOnce()
})
