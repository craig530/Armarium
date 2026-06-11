import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Layout from './components/layout/Layout'
import ProtectedRoute from './components/auth/ProtectedRoute'
import Login from './pages/Login'
import Library from './pages/Library'
import AddItem from './pages/AddItem'
import ItemDetail from './pages/ItemDetail'
import Admin from './pages/Admin'
import SettingsLayout from './pages/Settings/SettingsLayout'
import SettingsLocations from './pages/Settings/SettingsLocations'
import SettingsPlatforms from './pages/Settings/SettingsPlatforms'
import SettingsMediaSubtypes from './pages/Settings/SettingsMediaSubtypes'
import { DEFAULT_CATEGORY_SLUG } from './lib/categories'

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
          <Route index element={<Navigate to={`/library/${DEFAULT_CATEGORY_SLUG}`} replace />} />
          <Route path="library" element={<Navigate to={`/library/${DEFAULT_CATEGORY_SLUG}`} replace />} />
          <Route path="library/:category" element={<Library />} />
          <Route path="add" element={<AddItem />} />
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
    </BrowserRouter>
  )
}
