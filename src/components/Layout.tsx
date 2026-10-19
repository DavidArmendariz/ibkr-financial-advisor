import { useEffect } from 'react'
import { PanelLeftOpen } from 'lucide-react'
import { ConnectionIndicator } from '@/components/ConnectionIndicator'
import { Sidebar } from '@/components/Sidebar'
import { Dashboard } from '@/pages/Dashboard'
import { ChatPage } from '@/pages/Chat'
import { SettingsPage } from '@/pages/Settings'
import { SignalsPage } from '@/pages/Signals'
import { GammaPage } from '@/pages/Gamma'
import { MacroPage } from '@/pages/Macro'
import { usePortfolio } from '@/hooks/usePortfolio'
import { useSidebarCollapsed } from '@/hooks/useSidebarCollapsed'
import { SIDEBAR_SHORTCUT, cn, isMac, isSidebarShortcut } from '@/lib/utils'
import type { AppTab, ConnectionStatus } from '@/types'

interface Props {
  activeTab: AppTab
  onTabChange: (tab: AppTab) => void
  connectionStatus: ConnectionStatus
  onDisconnect: () => void
}

export function Layout({ activeTab, onTabChange, connectionStatus, onDisconnect }: Props) {
  const portfolio = usePortfolio(connectionStatus.connected)
  const sidebar = useSidebarCollapsed()
  const { toggle: toggleSidebar } = sidebar

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.repeat || !isSidebarShortcut(e)) return
      e.preventDefault()
      toggleSidebar()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [toggleSidebar])

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {!sidebar.collapsed && (
        <Sidebar
          activeTab={activeTab}
          onTabChange={onTabChange}
          connectionStatus={connectionStatus}
          summary={portfolio.summary}
          onCollapse={toggleSidebar}
        />
      )}

      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Stands in for the sidebar header: window drag region, room for the macOS
            traffic lights, and the connection status, which must stay visible. */}
        {sidebar.collapsed && (
          <div
            className={cn(
              'drag-region flex h-12 shrink-0 items-center gap-2 border-b border-sidebar-border bg-sidebar pl-4 pr-6',
              isMac && 'pl-20',
            )}
          >
            <button
              onClick={toggleSidebar}
              aria-label="Show sidebar"
              title={`Show sidebar (${SIDEBAR_SHORTCUT})`}
              className="no-drag rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent/50 hover:text-foreground"
            >
              <PanelLeftOpen className="h-4 w-4" />
            </button>
            <ConnectionIndicator status={connectionStatus} className="no-drag ml-auto" />
          </div>
        )}

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
          {activeTab === 'gamma' && <GammaPage />}
          {activeTab === 'macro' && <MacroPage />}
          {activeTab === 'settings' && <SettingsPage />}
        </main>
      </div>
    </div>
  )
}
