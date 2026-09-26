import { useState } from 'react'
import { ConnectionGuard } from '@/components/ConnectionGuard'
import { Layout } from '@/components/Layout'
import { useConnection } from '@/hooks/useConnection'
import type { AppTab } from '@/types'

export default function App() {
  const connection = useConnection()
  const [activeTab, setActiveTab] = useState<AppTab>('dashboard')

  if (!connection.status.connected) {
    return (
      <ConnectionGuard
        status={connection.status}
        loading={connection.loading}
        error={connection.error}
        onConnect={connection.connect}
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
