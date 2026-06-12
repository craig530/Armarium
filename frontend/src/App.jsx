import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Layout from './components/layout/Layout'
import ProtectedRoute from './components/auth/ProtectedRoute'
import { PageLoader } from './components/ui/LoadingSpinner'
import { DEFAULT_CATEGORY_SLUG } from './lib/categories'

const Login = lazy(() => import('./pages/Login'))
const Home = lazy(() => import('./pages/Home'))
const Library = lazy(() => import('./pages/Library'))
const AddItem = lazy(() => import('./pages/AddItem'))
const ItemDetail = lazy(() => import('./pages/ItemDetail'))
const Admin = lazy(() => import('./pages/Admin'))
const SettingsLayout = lazy(() => import('./pages/Settings/SettingsLayout'))
const SettingsLocations = lazy(() => import('./pages/Settings/SettingsLocations'))
const SettingsPlatforms = lazy(() => import('./pages/Settings/SettingsPlatforms'))
const SettingsMediaSubtypes = lazy(() => import('./pages/Settings/SettingsMediaSubtypes'))

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          className: 'dark:!bg-gray-800 dark:!text-white dark:!border-gray-700',
          duration: 3500,
        }}
      />
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Home />} />
            <Route path="library" element={<Navigate to={`/library/${DEFAULT_CATEGORY_SLUG}`} replace />} />
            <Route path="library/:category" element={<Library />} />
            <Route
              path="add"
              element={
                <ProtectedRoute requirePermission="can_add_items">
                  <AddItem />
                </ProtectedRoute>
              }
            />
            <Route path="item/:id" element={<ItemDetail />} />
            <Route path="locations" element={<Navigate to="/settings/locations" replace />} />
            <Route path="settings" element={<SettingsLayout />}>
              <Route index element={<Navigate to="/settings/locations" replace />} />
              <Route path="locations" element={<SettingsLocations />} />
              <Route path="platforms" element={<SettingsPlatforms />} />
              <Route path="media-subtypes" element={<SettingsMediaSubtypes />} />
            </Route>
            <Route
              path="admin"
              element={
                <ProtectedRoute requireAdmin>
                  <Admin />
                </ProtectedRoute>
              }
            />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
