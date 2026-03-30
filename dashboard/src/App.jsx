import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Sessions from './pages/Sessions.jsx'
import Flagged from './pages/Flagged.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="sessions" element={<Sessions />} />
          <Route path="flagged" element={<Flagged />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
