import { formatMobile, formatMoney, initials, searchTerm, sumMoney, suggestFinancialYear } from '../utils/format'

describe('format helpers', () => {
  it('formats money from decimal strings with Indian grouping', () => {
    expect(formatMoney('150000.50')).toBe('₹1,50,000.50')
    expect(formatMoney('2600.00')).toBe('₹2,600.00')
    expect(formatMoney(null)).toBe('—')
  })

  it('formats Indian mobiles for reading', () => {
    expect(formatMobile('+919812345678')).toBe('+91 98123 45678')
    expect(formatMobile('+14155550100')).toBe('+14155550100')
  })

  it('builds initials for organizations without a logo', () => {
    expect(initials('Shivaji Nagar Mandal')).toBe('SN')
  })

  it('suggests the April–March financial year', () => {
    expect(suggestFinancialYear(new Date(2026, 9, 5))).toEqual({ label: '2026–27', start_date: '2026-04-01', end_date: '2027-03-31' })
    expect(suggestFinancialYear(new Date(2027, 1, 10)).label).toBe('2026–27')
  })

  it('adds money exactly, without floating point errors', () => {
    expect(sumMoney(['500', '700', '1000', '400'])).toBe('2600.00')
    expect(sumMoney(['0.1', '0.2'])).toBe('0.30')
    expect(sumMoney(['300.5', '200.05', '', 'abc'])).toBe('500.55')
    expect(sumMoney([])).toBe('0.00')
  })
})

describe('searchTerm', () => {
  it('drops spaces and dashes from a typed mobile number', () => {
    expect(searchTerm(' +91 98678 50909 ')).toBe('+919867850909')
    expect(searchTerm('98678-50909')).toBe('9867850909')
  })

  it('leaves names alone', () => {
    expect(searchTerm('  Tanaji Patil ')).toBe('Tanaji Patil')
  })
})
