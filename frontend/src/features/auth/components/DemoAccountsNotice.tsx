import { env } from '@/shared/config/env'

// [MOCK] 데모 전용 컴포넌트. `src/mocks`와 함께 삭제한다.
import { DEMO_ACCOUNTS } from '@/mocks/db'

/**
 * 데모 계정 안내 — **데모 전용**
 * 백엔드가 붙기 전 시연에서 로그인 정보를 찾아 헤매지 않도록 두는 임시 카드다.
 */
export function DemoAccountsNotice() {
  if (!env.useMock) return null

  return (
    <aside className="mt-8 rounded-md border border-dashed border-border-strong p-4">
      <p className="text-label text-tertiary">데모 계정</p>
      <ul className="mt-2 flex flex-col gap-1">
        {Object.values(DEMO_ACCOUNTS).map((account) => (
          <li key={account.phone} className="tabular text-body-sm text-secondary">
            {account.label} · {account.phone} / {account.password}
          </li>
        ))}
      </ul>
    </aside>
  )
}
