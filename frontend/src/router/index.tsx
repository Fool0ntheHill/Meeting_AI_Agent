/* eslint-disable react-refresh/only-export-components */
import { Suspense, lazy, type ReactNode } from 'react'
import { Navigate, Outlet, createBrowserRouter, useLocation } from 'react-router-dom'
import AppLayout from '@/layouts/AppLayout'
import Loading from '@/components/Loading'
import { useAuthStore } from '@/store/auth'

const Login = lazy(() => import('@/pages/Login'))
const Home = lazy(() => import('@/pages/home/Home'))
const TaskList = lazy(() => import('@/pages/tasks/TaskList'))
const CreateTask = lazy(() => import('@/pages/tasks/CreateTask'))
const CreateTaskConfig = lazy(() => import('@/pages/tasks/CreateTaskConfig'))
const TaskDetailRedirect = lazy(() => import('@/pages/tasks/TaskDetailRedirect'))
const TaskWorkbench = lazy(() => import('@/pages/workbench/TaskWorkbench'))
const TaskFolders = lazy(() => import('@/pages/tasks/Folders'))
const Workspace = lazy(() => import('@/pages/workspace/Workspace'))
const TemplatePage = lazy(() => import('@/pages/templates/Templates'))
const Billing = lazy(() => import('@/pages/billing/Billing'))
const Profile = lazy(() => import('@/pages/profile/Profile'))
const NotFound = lazy(() => import('@/pages/NotFound'))

const withSuspense = (node: ReactNode) => <Suspense fallback={<Loading />}>{node}</Suspense>

const RequireAuth = () => {
  const { token } = useAuthStore()
  const location = useLocation()
  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <Outlet />
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Navigate to="/home" replace />,
  },
  {
    path: '/login',
    element: withSuspense(<Login />),
  },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppLayout />,
        children: [
          {
            path: '/home',
            element: withSuspense(<Home />),
          },
          {
            path: '/tasks',
            children: [
              { index: true, element: withSuspense(<TaskList />) },
              { path: 'folders', element: withSuspense(<TaskFolders />) },
              { path: 'trash', element: withSuspense(<TaskList />) },
              { path: 'create', element: withSuspense(<CreateTask />) },
              { path: 'create/config', element: withSuspense(<CreateTaskConfig />) },
              { path: ':id/workbench', element: withSuspense(<TaskWorkbench />) },
              { path: ':id', element: withSuspense(<TaskDetailRedirect />) },
            ],
          },
          {
            path: '/templates',
            element: withSuspense(<TemplatePage />),
          },
          {
            path: '/billing',
            element: withSuspense(<Billing />),
          },
          {
            path: '/profile',
            element: withSuspense(<Profile />),
          },
          {
            path: '/workspace/:id',
            element: withSuspense(<Workspace />),
          },
        ],
      },
    ],
  },
  {
    path: '*',
    element: withSuspense(<NotFound />),
  },
])
