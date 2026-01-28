import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider, App as AntApp } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { RouterProvider } from 'react-router-dom'
import { ENV } from './config/env'
import { router } from './router'
import { useAuthStore } from './store/auth'
import './styles/index.css'

const bootstrap = async () => {
  if (ENV.ENABLE_MOCK) {
    const { worker } = await import('./mocks/browser')
    await worker.start({ onUnhandledRequest: 'bypass' })
  }

  useAuthStore.getState().hydrate()

  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <ConfigProvider
        locale={zhCN}
        theme={{
          token: {
            colorPrimary: '#1677ff',
            colorBgLayout: '#f5f7fa',
            borderRadius: 8,
          },
          components: {
            Layout: {
              bodyBg: '#f7f9fc',
            },
            Card: {
              boxShadowSecondary: '0 6px 20px rgba(0,0,0,0.06)',
            },
          },
        }}
      >
        <AntApp>
          <RouterProvider router={router} />
        </AntApp>
      </ConfigProvider>
    </React.StrictMode>
)
}

bootstrap()
