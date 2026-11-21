import { useCallback, useEffect, useRef, useState } from 'react';
import type { SubmitEvent } from 'react';
import { api } from '../../../api/campaigns';
import { ApiError } from '../../../api/client';
import type { CampaignInput, Catalog, CatalogItem, Draft, Stream } from '../../../api/types';
import { editDraft, hasDraftChanges } from '../../streams/model/shares';
import type { DraftAction } from '../../streams/model/shares';
import type { Notice } from '../../../shared/ui/StatusNotice';
import { useUnsavedChanges } from '../../../shared/hooks/useUnsavedChanges';

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'Произошла непредвиденная ошибка.';
}

async function requestCatalog(signal?: AbortSignal): Promise<Catalog | string> {
  try {
    return await api.catalog(signal);
  } catch (error) {
    return errorMessage(error);
  }
}

type WorkspaceActivity = 'loading-editor' | 'working';
const campaignQueryParam = 'campaign';

export function useCampaignWorkspace() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [campaigns, setCampaigns] = useState<CatalogItem[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const rememberCampaign = useCallback((id?: number) => {
    setSelectedId(id === undefined ? '' : String(id));
    const url = new URL(window.location.href);
    if (id === undefined) url.searchParams.delete(campaignQueryParam);
    else url.searchParams.set(campaignQueryParam, String(id));
    if (url.href !== window.location.href) window.history.replaceState(window.history.state, '', url);
  }, []);
  const [loadedCampaignId, setLoadedCampaignId] = useState<number | null>(null);
  const [streams, setStreams] = useState<Stream[]>([]);
  const [drafts, setDrafts] = useState<ReadonlyMap<number, Draft>>(() => new Map());
  const [activity, setActivity] = useState<WorkspaceActivity | null>('loading-editor');
  const busy = activity !== null;
  const loadingEditor = activity === 'loading-editor';
  const performing = useRef(false);
  const [startupFailed, setStartupFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [notice, setNotice] = useState<Notice>({ message: 'Подключаемся…' });
  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;

    async function load() {
      const catalogRequest = requestCatalog(signal);
      try {
        const nextCampaigns = await api.campaigns(signal);
        if (signal.aborted) return;
        const requestedId = new URLSearchParams(window.location.search).get(campaignQueryParam);
        const selected = nextCampaigns.find(item => String(item.id) === requestedId) ?? nextCampaigns[0];
        setCampaigns(nextCampaigns);
        rememberCampaign(selected?.id);
        if (selected) {
          const initialStreams = await api.streams(selected.id, signal);
          if (signal.aborted) return;
          setStreams(initialStreams);
          setLoadedCampaignId(selected.id);
        }
        const nextCatalog = await catalogRequest;
        if (signal.aborted) return;
        if (typeof nextCatalog === 'string') {
          setStartupFailed(true);
          setNotice({ message: `Справочники не обновились. ${nextCatalog}` });
        } else {
          setCatalog(nextCatalog);
          setNotice({ message: '' });
        }
      } catch (error) {
        const nextCatalog = await catalogRequest;
        if (signal.aborted) return;
        if (typeof nextCatalog !== 'string') setCatalog(nextCatalog);
        setStartupFailed(true);
        setNotice({ message: errorMessage(error), error: true, code: error instanceof ApiError ? error.code : 'error' });
      } finally {
        if (!signal.aborted) setActivity(null);
      }
    }

    void load();
    return () => controller.abort();
  }, [attempt, rememberCampaign]);

  useUnsavedChanges(drafts.size > 0);

  function retryStartup() {
    setActivity('loading-editor');
    setStartupFailed(false);
    setNotice({ message: 'Подключаемся…' });
    setAttempt(value => value + 1);
  }

  async function loadCampaign(id: number) {
    const updated = await api.streams(id);
    setStreams(updated);
    setLoadedCampaignId(id);
    setDrafts(new Map());
  }

  function clearDraft(id: number) {
    setDrafts(previous => {
      const next = new Map(previous);
      next.delete(id);
      return next;
    });
  }

  async function perform(message: string, work: () => Promise<string>, activity: WorkspaceActivity = 'working') {
    if (busy || performing.current) return;
    performing.current = true;
    setActivity(activity);
    setNotice({ message });
    try {
      setNotice({ message: await work() });
    } catch (error) {
      setNotice({ message: errorMessage(error), error: true, code: error instanceof ApiError ? error.code : 'error' });
    } finally {
      performing.current = false;
      setActivity(null);
    }
  }

  function confirmStreamLoad() {
    return drafts.size === 0 || window.confirm('Отменить неопубликованные изменения и загрузить потоки?');
  }

  function selectCampaign(id: string) {
    const campaignId = Number(id);
    if (!id || campaignId === loadedCampaignId || !confirmStreamLoad()) return;
    void perform('Загружаем потоки…', async () => {
      await loadCampaign(campaignId);
      rememberCampaign(campaignId);
      return 'Потоки загружены.';
    }, 'loading-editor');
  }

  function fetchStreams(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!confirmStreamLoad()) return;
    void perform('Загружаем потоки…', async () => {
      const catalogRequest = requestCatalog();
      const warnings: string[] = [];
      const nextCampaigns = await api.campaigns().catch((error: unknown) => {
        if (campaigns.length === 0) throw error;
        warnings.push(`Список кампаний не обновился. ${errorMessage(error)}`);
        return campaigns;
      });
      const selected = nextCampaigns.find(item => String(item.id) === selectedId) ?? nextCampaigns[0];
      if (selected) await loadCampaign(selected.id);
      else {
        setStreams([]);
        setLoadedCampaignId(null);
        setDrafts(new Map());
      }
      setCampaigns(nextCampaigns);
      rememberCampaign(selected?.id);
      const nextCatalog = await catalogRequest;
      if (typeof nextCatalog === 'string') warnings.push(`Справочники не обновились. ${nextCatalog}`);
      else setCatalog(nextCatalog);
      setStartupFailed(false);
      return ['Потоки обновлены.', ...warnings].join(' ');
    }, 'loading-editor');
  }

  async function createCampaign(input: CampaignInput & { operation_id: string }) {
    if (drafts.size && !window.confirm('Отменить неопубликованные изменения и создать кампанию?')) return 'discarded' as const;
    let created = false;
    let discarded = false;
    await perform('Создаём кампанию…', async () => {
      const campaign = await api.create(input).catch((error: unknown) => {
        discarded = error instanceof ApiError && error.status === 400;
        throw error;
      });
      created = true;
      setCampaigns(previous => [...previous.filter(item => item.id !== campaign.id), campaign]);
      rememberCampaign(campaign.id);
      setActivity('loading-editor');
      try {
        await loadCampaign(campaign.id);
      } catch (error) {
        throw new Error(`Кампания #${campaign.id} создана, но загрузить её потоки не удалось. ${errorMessage(error)}`);
      }
      return `Кампания «${campaign.name}» (#${campaign.id}) создана: ${input.country.toUpperCase()} → Google; остальной трафик → оффер #${input.offers}. Домен, группа и источник проверены.`;
    });
    return discarded ? 'discarded' as const : created;
  }

  function changeOffer(stream: Stream, action: DraftAction) {
    try {
      const next = editDraft(drafts.get(stream.id) ?? stream, action);
      if (hasDraftChanges(stream, next)) {
        setDrafts(previous => new Map(previous).set(stream.id, next));
        setNotice({ message: 'Черновик обновлён.' });
      } else {
        clearDraft(stream.id);
        setNotice({ message: 'Все изменения потока отменены.' });
      }
      return true;
    } catch (error) {
      setNotice({ message: errorMessage(error), error: true, code: error instanceof ApiError ? error.code : 'error' });
      return false;
    }
  }

  function publish(stream: Stream, draft: Draft) {
    void perform('Публикуем изменения…', async () => {
      const updated = await api.publish(stream, draft);
      setStreams(previous => previous.map(item => item.id === stream.id ? updated : item));
      clearDraft(stream.id);
      return 'Изменения потока опубликованы.';
    });
  }

  function acceptRemote(stream: Stream) {
    if (!window.confirm('Принять текущее состояние Keitaro и отменить местный черновик? Сначала убедитесь в Keitaro, что предыдущая запись завершена.')) return;
    void perform('Проверяем состояние…', async () => {
      const updated = await api.accept(stream.id);
      setStreams(previous => previous.map(item => item.id === stream.id ? updated : item));
      clearDraft(stream.id);
      return 'Текущее состояние Keitaro принято.';
    });
  }

  const loadedCampaign = campaigns.find(campaign => campaign.id === loadedCampaignId);

  function cancelDraft(id: number) {
    clearDraft(id);
    setNotice({ message: 'Черновик отменён.' });
  }

  function dismissCreationAttempt() {
    setNotice({ message: 'Попытка закрыта в этой вкладке. Можно создать новую кампанию.' });
  }

  return { catalog, campaigns, selectedId, selectCampaign, streams, drafts, busy, loadingEditor, startupFailed,
    notice, retryStartup, fetchStreams, createCampaign, changeOffer, publish, acceptRemote,
    loadedCampaign, cancelDraft, dismissCreationAttempt };
}

export type CampaignWorkspace = ReturnType<typeof useCampaignWorkspace>;
