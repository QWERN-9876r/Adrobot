import { CampaignForm } from '../features/campaigns/components/CampaignForm';
import { CampaignEditor } from '../features/workspace/components/CampaignEditor';
import { useCampaignWorkspace } from '../features/workspace/model/useCampaignWorkspace';
import { StatusNotice } from '../shared/ui/StatusNotice';
import { AppHeader } from './AppHeader';

export function App() {
  const workspace = useCampaignWorkspace();
  return <>
    <AppHeader mode={workspace.catalog?.mode} />
    <div className="loading-bar" aria-hidden="true">
      {workspace.busy && <span className="loading-bar-indicator" />}
    </div>
    <main className="shell">
      <div className="page-heading"><h1>Управление кампаниями</h1></div>
      <StatusNotice notice={workspace.notice} retry={workspace.startupFailed ? workspace.retryStartup : undefined} />
      <div className="workspace">
        <CampaignForm catalog={workspace.catalog} busy={workspace.busy} onCreate={workspace.createCampaign}
          onStartNew={workspace.dismissCreationAttempt} />
        <CampaignEditor workspace={workspace} />
      </div>
    </main>
  </>;
}
