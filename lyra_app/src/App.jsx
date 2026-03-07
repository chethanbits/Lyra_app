import { useLocation, useRoutes, Navigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'motion/react'
import Layout from './components/Layout'
import Splash from './pages/Splash'
import Onboarding from './pages/Onboarding'
import Welcome from './pages/Welcome'
import PersonalizationChoice from './pages/PersonalizationChoice'
import BirthDetails from './pages/BirthDetails'
import Registration from './pages/Registration'
import Login from './pages/Login'
import Home from './pages/Home'
import Planner from './pages/Planner'
import Calendar from './pages/Calendar'
import Festivals from './pages/Festivals'
import Settings from './pages/Settings'

/* Route-level transition: same pattern as Lyra Mobile App Design reference.
   When navigating (e.g. Onboarding → Welcome), outgoing page exits, incoming enters. */
const routeConfig = [
  { path: '/', element: <Splash /> },
  { path: '/onboarding', element: <Onboarding /> },
  { path: '/welcome', element: <Welcome /> },
  { path: '/personalization', element: <PersonalizationChoice /> },
  { path: '/birth-details', element: <BirthDetails /> },
  { path: '/register', element: <Registration /> },
  { path: '/login', element: <Login /> },
  {
    path: '/app',
    element: <Layout />,
    children: [
      { index: true, element: <Navigate to="/app/home" replace /> },
      { path: 'home', element: <Home /> },
      { path: 'planner', element: <Planner /> },
      { path: 'calendar', element: <Calendar /> },
      { path: 'festivals', element: <Festivals /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
  { path: '/home', element: <Navigate to="/app/home" replace /> },
  { path: '/planner', element: <Navigate to="/app/planner" replace /> },
  { path: '/calendar', element: <Navigate to="/app/calendar" replace /> },
  { path: '/festivals', element: <Navigate to="/app/festivals" replace /> },
  { path: '/settings', element: <Navigate to="/app/settings" replace /> },
  { path: '*', element: <Navigate to="/onboarding" replace /> },
]

export default function App() {
  const location = useLocation()
  const element = useRoutes(routeConfig)

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, x: 100 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -100 }}
        transition={{ duration: 0.3, ease: 'easeInOut' }}
        style={{ minHeight: '100vh' }}
      >
        {element}
      </motion.div>
    </AnimatePresence>
  )
}
