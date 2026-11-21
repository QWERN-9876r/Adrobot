import { SelectOptions } from '../../../shared/ui/SelectOptions';
import { StreamEditor } from '../../streams/components/StreamEditor';
import type { CampaignWorkspace } from '../model/useCampaignWorkspace';

function StreamListSkeleton() {
  return (
    <div className="stream-list" aria-hidden="true">
      <div className="stream">
        <div className="stream-header">
          <span className="skeleton stream-skeleton-marker" />
          <span className="skeleton stream-skeleton-title" />
        </div>
      </div>
      <div className="stream">
        <div className="stream-header">
          <span className="skeleton stream-skeleton-marker" />
          <span className="skeleton stream-skeleton-title" />
        </div>
        {[0, 1, 2].map(row => <div className="stream-skeleton-row" key={row}>
          <span className="skeleton" />
          <span className="skeleton" />
          <span className="skeleton" />
        </div>)}
      </div>
    </div>
  );
}

export function CampaignEditor({ workspace }: { workspace: CampaignWorkspace }) {
  const { campaigns, catalog, selectedId, setSelectedId, fetchStreams, busy, loadingEditor, loadedCampaign,
    streams, drafts, acceptRemote, changeOffer, publish, cancelDraft } = workspace;
  const loadingCampaigns = loadingEditor && campaigns.length === 0;
  return (
    <section className="panel edit-panel" aria-labelledby="edit-title" aria-busy={loadingEditor}>
      <div className="panel-header"><h2 id="edit-title">Редактор кампаний</h2></div>
      {loadingCampaigns && <div className="campaign-picker campaign-picker-skeleton" aria-hidden="true">
        <div><span className="skeleton campaign-skeleton-label" /><span className="skeleton campaign-skeleton-control" /></div>
        <span className="skeleton campaign-skeleton-control" />
      </div>}
      <form onSubmit={fetchStreams} hidden={loadingCampaigns}>
        <fieldset className="campaign-picker" disabled={busy}>
          <label>
            Кампания
            <select disabled={campaigns.length === 0} value={selectedId} onChange={event => setSelectedId(event.target.value)}>
              <SelectOptions items={campaigns} placeholder="Выберите кампанию" showIds />
            </select>
          </label>
          <button type="submit" className="secondary">Обновить кампании и потоки</button>
        </fieldset>
      </form>
      {loadingEditor && <StreamListSkeleton />}
      <div hidden={loadingEditor}>
        {loadedCampaign && <div className="loaded-campaign">Потоки кампании «{loadedCampaign.name}»</div>}
        {streams.length === 0 && (
          <p className="empty">{campaigns.length === 0 && catalog ? 'Создайте первую кампанию.' : 'Нет загруженных потоков.'}</p>
        )}
        <div className="stream-list" inert={busy} aria-busy={busy}>
          {streams.map(stream => {
            const draft = drafts.get(stream.id);
            return <StreamEditor key={stream.id} stream={stream} draft={draft} catalogOffers={catalog?.offers ?? []}
              onAccept={() => acceptRemote(stream)}
              onEdit={action => changeOffer(stream, action)}
              onPublish={() => { if (draft) publish(stream, draft); }}
              onCancel={() => cancelDraft(stream.id)} />;
          })}
        </div>
      </div>
    </section>
  );
}
