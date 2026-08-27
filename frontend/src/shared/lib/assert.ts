/** 도메인 불변식을 코드로 못 박는다. 실패는 버그이지 사용자 오류가 아니다. */
export function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(`[assert] ${message}`)
  }
}

/** 판별 유니온의 모든 갈래를 처리했는지 컴파일 타임에 강제한다. */
export function assertNever(value: never, message = 'unhandled branch'): never {
  throw new Error(`[assert] ${message}: ${String(value)}`)
}
