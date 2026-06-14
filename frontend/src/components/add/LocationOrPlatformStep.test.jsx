import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/react'
import LocationOrPlatformStep from './LocationOrPlatformStep'
import { locationsApi } from '../../api/locations'
import { platformsApi } from '../../api/platforms'
import { mediaSubtypesApi } from '../../api/mediaSubtypes'
import { useReferenceDataStore } from '../../store'

vi.mock('../../api/locations', () => ({ locationsApi: { list: vi.fn(), create: vi.fn() } }))
vi.mock('../../api/platforms', () => ({ platformsApi: { list: vi.fn(), create: vi.fn() } }))
vi.mock('../../api/mediaSubtypes', () => ({ mediaSubtypesApi: { list: vi.fn() } }))

const noop = {
  onSelectLocation: () => {},
  onSelectPlatform: () => {},
  onLocationCreated: () => {},
  onPlatformCreated: () => {},
  onContinue: () => {},
}

beforeEach(() => {
  vi.clearAllMocks()
  locationsApi.list.mockResolvedValue([])
  platformsApi.list.mockResolvedValue([])
  mediaSubtypesApi.list.mockResolvedValue([])
})

afterEach(() => {
  cleanup()
})

describe('LocationOrPlatformStep', () => {
  it('shows a loading spinner until reference data has loaded', () => {
    useReferenceDataStore.setState({ locations: [], platforms: [], mediaSubtypes: [], loaded: false, loading: null })

    render(<LocationOrPlatformStep supertype="physical" locationId="" platformId="" {...noop} />)

    expect(screen.queryByText('Select a location…')).toBeNull()
    expect(document.querySelector('.animate-spin')).toBeTruthy()
  })

  it('physical: selecting a location calls onSelectLocation with its id', () => {
    useReferenceDataStore.setState({
      locations: [{ id: 1, name: 'Living Room', children: [] }],
      platforms: [], mediaSubtypes: [], loaded: true, loading: null,
    })
    const onSelectLocation = vi.fn()

    render(<LocationOrPlatformStep supertype="physical" locationId="" platformId="" {...noop} onSelectLocation={onSelectLocation} />)

    expect(screen.getByText('Where will this be kept?')).toBeTruthy()

    fireEvent.click(screen.getByText('Select a location…'))
    fireEvent.click(screen.getByText('Living Room'))

    expect(onSelectLocation).toHaveBeenCalledWith('1')
  })

  it('digital: selecting a platform calls onSelectPlatform with its id', () => {
    useReferenceDataStore.setState({
      locations: [], platforms: [{ id: 5, name: 'Netflix' }], mediaSubtypes: [], loaded: true, loading: null,
    })
    const onSelectPlatform = vi.fn()

    render(<LocationOrPlatformStep supertype="digital" locationId="" platformId="" {...noop} onSelectPlatform={onSelectPlatform} />)

    expect(screen.getByText('Where will you access this?')).toBeTruthy()

    fireEvent.click(screen.getByText('Select a platform…'))
    fireEvent.click(screen.getByText('Netflix'))

    expect(onSelectPlatform).toHaveBeenCalledWith('5')
  })

  it('hides the Continue button until a location is selected', () => {
    useReferenceDataStore.setState({
      locations: [{ id: 1, name: 'Living Room', children: [] }],
      platforms: [], mediaSubtypes: [], loaded: true, loading: null,
    })

    const { rerender } = render(<LocationOrPlatformStep supertype="physical" locationId="" platformId="" {...noop} />)
    expect(screen.queryByText('Continue')).toBeNull()

    rerender(<LocationOrPlatformStep supertype="physical" locationId="1" platformId="" {...noop} />)
    expect(screen.getByText('Continue')).toBeTruthy()
  })

  it('physical: creating a new location calls locationsApi.create and onLocationCreated', async () => {
    useReferenceDataStore.setState({
      locations: [{ id: 1, name: 'Living Room', children: [] }],
      platforms: [], mediaSubtypes: [], loaded: true, loading: null,
    })
    locationsApi.create.mockResolvedValue({ id: 99, name: 'Bookshelf' })
    const onLocationCreated = vi.fn()

    render(<LocationOrPlatformStep supertype="physical" locationId="" platformId="" {...noop} onLocationCreated={onLocationCreated} />)

    fireEvent.click(screen.getByText('+ Create new location'))
    fireEvent.change(screen.getByPlaceholderText('e.g. Bookshelf, Living Room'), { target: { value: 'Bookshelf' } })
    fireEvent.click(screen.getByText('Create & select'))

    await waitFor(() => {
      expect(locationsApi.create).toHaveBeenCalledWith({ name: 'Bookshelf', parent_id: null, icon_key: null })
    })
    expect(onLocationCreated).toHaveBeenCalledWith('99')
  })
})
