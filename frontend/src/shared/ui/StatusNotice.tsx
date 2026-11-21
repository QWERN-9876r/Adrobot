export interface Notice {
  message: string;
  error?: boolean;
  code?: string;
}

export function StatusNotice({ notice, retry }: { notice: Notice; retry?: () => void }) {
  return <div className="status-line">
    {notice.code === 'uncertain' && <strong>Результат требует проверки</strong>}
    <p className={notice.error ? 'status error' : 'status'} role="status">{notice.message}</p>
    {retry && <button type="button" className="secondary" onClick={retry}>Повторить</button>}
  </div>;
}
