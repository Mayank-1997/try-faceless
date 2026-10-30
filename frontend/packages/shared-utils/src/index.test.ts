import { describe, it, expect } from 'vitest'
import { formatDate, formatRelativeTime, formatDuration, formatNumber, formatBytes } from '../format'
import { isValidEmail, isValidUrl, isStrongPassword } from '../validate'
import { slugify, truncate, capitalize, initials, maskApiKey } from '../string'

describe('format utils', () => {
  it('formatDate should format ISO date string', () => {
    const result = formatDate('2024-01-15T10:30:00Z')
    expect(result).toBeTruthy()
    expect(typeof result).toBe('string')
  })

  it('formatRelativeTime should return relative time', () => {
    const past = new Date(Date.now() - 60000).toISOString()
    const result = formatRelativeTime(past)
    expect(result).toBeTruthy()
  })

  it('formatDuration should format seconds', () => {
    expect(formatDuration(0)).toBeTruthy()
    expect(formatDuration(65)).toBeTruthy()
  })

  it('formatNumber should format numbers', () => {
    expect(formatNumber(1000)).toBeTruthy()
  })

  it('formatBytes should format file sizes', () => {
    expect(formatBytes(0)).toBeTruthy()
    expect(formatBytes(1024)).toBeTruthy()
  })
})

describe('validate utils', () => {
  it('isValidEmail should validate emails', () => {
    expect(isValidEmail('test@example.com')).toBe(true)
    expect(isValidEmail('invalid')).toBe(false)
  })

  it('isValidUrl should validate URLs', () => {
    expect(isValidUrl('https://example.com')).toBe(true)
    expect(isValidUrl('not-a-url')).toBe(false)
  })

  it('isStrongPassword should validate password strength', () => {
    expect(isStrongPassword('Test1234!')).toBe(true)
    expect(isStrongPassword('weak')).toBe(false)
  })
})

describe('string utils', () => {
  it('slugify should convert to slug', () => {
    expect(slugify('Hello World!')).toBe('hello-world')
  })

  it('truncate should truncate long strings', () => {
    expect(truncate('Hello World', 5)).toHaveLength(5)
  })

  it('capitalize should capitalize first letter', () => {
    expect(capitalize('hello')).toBe('Hello')
  })

  it('initials should extract initials', () => {
    expect(initials('John Doe')).toBe('JD')
  })

  it('maskApiKey should mask key', () => {
    const result = maskApiKey('sk-1234567890abcdef')
    expect(result).toContain('•')
  })
})
