import { BrowserRouter, Route, Routes } from 'react-router'

import TestPage from '@/pages/TestPage'
import TestsPage from '@/pages/TestsPage'

export default function App() {
  return (
    <BrowserRouter>
      <main className="mx-auto max-w-5xl px-6 py-10">
        <Routes>
          <Route path="/" element={<TestsPage />} />
          <Route path="/tests/:testId" element={<TestPage />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
