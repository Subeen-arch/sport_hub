const currency = new Intl.NumberFormat('en-NP', {
  style: 'currency', currency: 'NPR', minimumFractionDigits: 2, maximumFractionDigits: 2,
})

export function money(value: string | number): string {
  return currency.format(Number(value))
}

export function dateTime(value: string): string {
  return new Intl.DateTimeFormat('en-NP', {
    dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Kathmandu',
  }).format(new Date(value))
}
