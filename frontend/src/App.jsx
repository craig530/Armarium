import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Layout from './components/layout/Layout'
import ProtectedRoute from './components/auth/ProtectedRoute'
import Login from './pages/Login'
import Library from './pages/Library'
import AddItem from './pages/AddItem'
import ItemDetail from './pages/ItemDetail'
import Locations from './pages/Locations'
import Admin from './pages/Admin'

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
          <Route index element={<Navigate to="/library" replace />} />
          <Route path="library" element={<Library />} />
          <Route path="add" element={<AddItem />} />
          <Route path="item/:id" element={<ItemDetail />} />
          <Route path="locations" element={<Locations />} />
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
