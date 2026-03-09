import { useState } from 'react'
import { Outlet } from 'react-router'
import { TopMenuBar } from '../components'
import useDocumentTitle from '../hooks/useDocumentTitle'

export default function Root() {
  const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth >= 768)
  useDocumentTitle()

  let layoutClass = 'layout'
  if (!sidebarOpen) {
    layoutClass = 'layout layout--collapsed'
  }

  return (
    <div className={layoutClass}>
      <TopMenuBar sidebarOpen={sidebarOpen} onToggleSidebar={() => setSidebarOpen((v) => !v)} />
      <main className='layout__main'>
        <Outlet />
      </main>
    </div>
  )
}
