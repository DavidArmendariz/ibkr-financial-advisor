import { useEffect, useState } from 'react'
import { ConnectionGuard } from '@/components/ConnectionGuard'
import { Layout } from '@/components/Layout'
import { useConnection } from '@/hooks/useConnection'
import type { AppTab } from '@/types'

export default function App() {
  const connection = useConnection()
  const [activeTab, setActiveTab] = useState<AppTab>('dashboard')

  // Clicking a signal notification asks the window to open the Signals view.
  useEffect(() => window.electronAPI?.onNavigate?.((tab) => setActiveTab(tab as AppTab)), [])

  if (!connection.status.connected) {
    return (
      <ConnectionGuard
        status={connection.status}
        loading={connection.loading}
        error={connection.error}
        autoConnect={connection.autoConnect}
        onConnect={(mode) => connection.connect(mode)}
      />
    )
  }

  return (
    <Layout
      activeTab={activeTab}
      onTabChange={setActiveTab}
      connectionStatus={connection.status}
      onDisconnect={connection.disconnect}
    />
  )
}
