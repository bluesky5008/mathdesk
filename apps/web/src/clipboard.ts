export async function copyText(text: string): Promise<void> {
  await navigator.clipboard.writeText(text)
}

export async function copyImage(url: string): Promise<void> {
  const blob = await (await fetch(url)).blob()
  await navigator.clipboard.write([new ClipboardItem({ [blob.type]: blob })])
}

export function downloadImage(url: string, fileName: string): void {
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = fileName
  anchor.click()
}
