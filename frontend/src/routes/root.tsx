import { useState } from 'react'
import { Outlet } from 'react-router'
import TopMenuBar from '../components/TopMenuBar'

export default function Root() {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <div className={`layout${sidebarOpen ? '' : ' layout--collapsed'}`}>
      <TopMenuBar sidebarOpen={sidebarOpen} onToggleSidebar={() => setSidebarOpen((v) => !v)} />
      <main className='layout__main'>
        <Outlet />
      </main>
    </div>
  )
}
