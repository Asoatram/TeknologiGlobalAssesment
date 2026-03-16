import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { Header } from './component/Header'
import { InsightPage } from './page/insight'
import { ItemDetailsPage } from './page/item-details'
import { ListPage } from './page/list'
import './App.css'

function AppLayout() {
  return (
    <div className="app-shell">
      <Header />
      <Outlet />
    </div>
  )
}

function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Navigate to="/inventory" replace />} />
        <Route path="/inventory" element={<ListPage />} />
        <Route path="/inventory/items/sku/:sku" element={<ItemDetailsPage />} />
        <Route path="/insight" element={<InsightPage />} />
      </Route>
    </Routes>
  )
}

export default App
