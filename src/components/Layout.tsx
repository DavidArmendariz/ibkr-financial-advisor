import { Sidebar } from '@/components/Sidebar'
import { Dashboard } from '@/pages/Dashboard'
import { ChatPage } from '@/pages/Chat'
import { SettingsPage } from '@/pages/Settings'
import { SignalsPage } from '@/pages/Signals'
import { usePortfolio } from '@/hooks/usePortfolio'
import type { AppTab, ConnectionStatus } from '@/types'

interface Props {
  activeTab: AppTab
  onTabChange: (tab: AppTab) => void
  connectionStatus: ConnectionStatus
  onDisconnect: () => void
}

export function Layout({ activeTab, onTabChange, connectionStatus, onDisconnect }: Props) {
  const portfolio = usePortfolio(connectionStatus.connected)

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar
        activeTab={activeTab}
        onTabChange={onTabChange}
        connectionStatus={connectionStatus}
        summary={portfolio.summary}
      />

      <main className="flex-1 overflow-hidden">
        {activeTab === 'dashboard' && (
          <Dashboard
            summary={portfolio.summary}
            positions={portfolio.positions}
            loading={portfolio.loading}
            onRefresh={portfolio.refresh}
          />
        )}
        {activeTab === 'chat' && <ChatPage onOpenSettings={() => onTabChange('settings')} />}
        {activeTab === 'signals' && <SignalsPage />}
        {activeTab === 'settings' && <SettingsPage />}
      </main>
    </div>
  )
}
