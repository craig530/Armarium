import { describe, it, expect, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import IGDBAttribution from './IGDBAttribution'

afterEach(() => cleanup())

describe('IGDBAttribution', () => {
  it('renders an attribution link pointing to igdb.com', () => {
    render(<IGDBAttribution />)
    const link = screen.getByRole('link')
    expect(link.href).toContain('igdb.com')
    expect(link.rel).toContain('noopener')
  })

  it('renders the IGDB logo image', () => {
    render(<IGDBAttribution />)
    const img = screen.getByAltText('IGDB')
    expect(img).toBeTruthy()
  })

  it('applies a custom className', () => {
    const { container } = render(<IGDBAttribution className="custom-class" />)
    expect(container.firstChild.className).toContain('custom-class')
  })
})
