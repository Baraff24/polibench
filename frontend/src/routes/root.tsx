import { Outlet } from 'react-router'
import TopMenuBar from '../components/TopMenuBar'

export default function Root() {
  return (
    <div className='layout'>
      <TopMenuBar />
      <main className='layout__main'>
        <Outlet />
      </main>
    </div>
  )
}
