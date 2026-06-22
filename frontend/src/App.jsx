import { lazy, Suspense } from 'react'
import { createBrowserRouter, createRoutesFromElements, RouterProvider, Route, Navigate } from 'react-router-dom'
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
const Profile = lazy(() => import('./pages/Profile'))
const Admin = lazy(() => import('./pages/Admin'))
const AdminUsers = lazy(() => import('./pages/AdminUsers'))
const SettingsLayout = lazy(() => import('./pages/Settings/SettingsLayout'))
const SettingsLocations = lazy(() => import('./pages/Settings/SettingsLocations'))
const SettingsPlatforms = lazy(() => import('./pages/Settings/SettingsPlatforms'))
const SettingsMediaSubtypes = lazy(() => import('./pages/Settings/SettingsMediaSubtypes'))
const SettingsLists = lazy(() => import('./pages/Settings/SettingsLists'))
const SettingsOwnership = lazy(() => import('./pages/Settings/SettingsOwnership'))
const SettingsPlex = lazy(() => import('./pages/Settings/SettingsPlex'))

const router = createBrowserRouter(
  createRoutesFromElements(
    <>
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
        <Route path="profile" element={<Profile />} />
        <Route path="locations" element={<Navigate to="/settings/locations" replace />} />
        <Route path="settings" element={<SettingsLayout />}>
          <Route index element={<Navigate to="/settings/locations" replace />} />
          <Route path="locations" element={<SettingsLocations />} />
          <Route path="platforms" element={<SettingsPlatforms />} />
          <Route path="media-subtypes" element={<SettingsMediaSubtypes />} />
        </Route>
        <Route path="settings/lists" element={<SettingsLists />} />
        <Route path="settings/ownership" element={<SettingsOwnership />} />
        <Route path="settings/plex" element={<SettingsPlex />} />
        <Route
          path="admin"
          element={
            <ProtectedRoute requireAdmin>
              <Admin />
            </ProtectedRoute>
          }
        />
        <Route
          path="admin/users"
          element={
            <ProtectedRoute requireAdmin>
              <AdminUsers />
            </ProtectedRoute>
          }
        />
      </Route>
    </>
  )
)

export default function App() {
  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          className: 'dark:bg-gray-800! dark:text-white! dark:border-gray-700!',
          duration: 3500,
        }}
      />
      <Suspense fallback={<PageLoader />}>
        <RouterProvider router={router} />
      </Suspense>
    </>
  )
}
