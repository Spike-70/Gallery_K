/**
 * 마이크로카피 단일 원천 — UX 설계서 §5
 *
 * JSX에 한국어 문자열을 직접 쓰지 않는다(프런트 문서 §16).
 * 문체 규칙(§5.1): 해요체 · 시스템을 주어로 삼지 않음 · 사용자를 탓하지 않음 ·
 * 사과 남발 금지 · 전문 용어 금지 · 마침표를 찍는다(버튼·라벨 제외) · 느낌표 금지.
 */

/** 버튼·링크 (§5.2) */
export const actions = {
  enterGallery: '갤러리 입장',
  signup: '회원가입',
  login: '입장',
  backHome: '첫 화면으로',
  backGallery: '갤러리 화면으로',
  backPrev: '이전 화면으로',
  backAdmin: '관리자 화면으로',
  backLogin: '로그인 화면으로',
  backSettings: '설정으로',
  backArchive: '지난 전시 목록으로',
  backThisExhibition: '이 전시로',
  archive: '지난 전시',
  settings: '설정',
  retry: '다시 시도',
  cancel: '취소',
  confirmWithdraw: '탈퇴',
  withdraw: '탈퇴',
  viewLarge: '크게 보기',
  zoomIn: '확대',
  zoomOut: '원래 크기로',
  prevArtwork: '← 이전 그림',
  nextArtwork: '다음 그림 →',
  todayExhibition: '오늘의 전시로',
  uploadMany: '사진 여러 장 올리기',
  preview: '미리보기',
  carryDraft: '이어서 쓰기',
  createAccount: '계정 만들기',
  sendCode: '인증번호 받기',
  resendCode: '인증번호 다시 받기',
  changePassword: '비밀번호 바꾸기',
  logout: '로그아웃',
  close: '닫기',
  refresh: '새로고침',
  save: '저장',
  edit: '수정',
  publishUp: 'UP',
  hideExhibition: '전시 숨김',
  unhideExhibition: '숨김 해제',
  move: '옮기기',
  block: '차단',
  unblock: '차단 해제',
  resetPassword: '비밀번호 초기화',
  addNotice: '공지 추가',
  replacePhoto: '사진 바꾸기',
  reupload: '다시 올리기',
  clearSlot: '자리 비우기',
  viewTerms: '보기',
  viewPastExhibitions: '지난 전시 보기',
  goLogin: '로그인하러 가기',
  allowNotification: '알림 받기',
  later: '나중에',
  understood: '알겠습니다',
} as const

/**
 * 랜드마크·보조 기술 전용 라벨 (§9)
 * 눈에 보이지 않아도 사용자 문구다. JSX에 직접 쓰지 않는다.
 */
export const landmarks = {
  back: '되돌아가기',
  galleryNav: '갤러리 이동',
  artworkNav: '그림 이동',
  adminNav: '관리 메뉴',
  memberActions: (name: string) => `${name} 관리`,
  slotIncomplete: '설명이 아직 없습니다',
} as const

/** 화면 제목 */
export const screenTitles = {
  login: '입장',
  signup: "'갤러리 K'는",
  passwordReset: '비밀번호 재설정',
  passwordChange: '비밀번호 변경',
  socialLink: '계정 연결',
  archive: '지난 전시',
  settings: '설정',
  adminMembers: '회원 관리',
  adminSettings: '설정 · 휴관 공지',
  adminStats: '관람 현황',
  preview: '미리보기',
} as const

/**
 * 웹푸시 폴백 문구 — UX 설계서 §8
 * 페이로드가 깨져도 알림은 뜬다. 서비스워커가 이 값을 쓴다.
 */
export const push = {
  fallbackTitle: '오늘의 전시',
  fallbackBody: '새 전시가 걸렸습니다',
} as const

/** 브랜드 */
export const brand = {
  logo: 'Morning Gallery K',
  curatorLink: 'Curator K',
} as const

/** 상태·안내 (§5.3) */
export const status = {
  firstExhibitionPending: '첫 전시를 준비하고 있습니다',
  archiveBanner: '지난 전시를 보고 있습니다',
  archiveEnd: '여기까지입니다',
  archiveEmpty: '아직 지난 전시가 없습니다',
  offlineBanner: '연결이 없어 마지막으로 본 전시를 보여드립니다',
  updateAvailable: '새 버전이 있습니다',
  zoomHint: '손가락으로 벌려 확대할 수 있습니다',
  saved: '저장됨 · 방금',
  saving: '저장 중…',
  saveFailed: '저장 실패 · 다시 시도',
  published: '전시가 발행되었습니다.',
  carryoverNoticeAdmin: '이틀째 같은 전시가 걸려 있습니다',
  adminOffline: '연결이 없어 관리자 화면을 열 수 없습니다',
  exhibitionLoadFailed: '전시를 불러오지 못했습니다',
  imageLoadFailed: '그림을 불러오지 못했습니다',
  memberEmpty: '아직 회원이 없습니다',
  statsEmpty: '아직 기록이 없습니다',
  noticeEmpty: '예정된 공지가 없습니다',
  loading: '불러오는 중',
} as const

/**
 * 서버가 완성해 주는 문자열의 클라이언트 폴백.
 * 원칙적으로 표시 문자열은 서버가 준다(API 문서 §6.1). 목/오프라인 대비용이다.
 */
export const templates = {
  /** `8월 30일의 전시` — 연장 라벨 (§5.3) */
  carriedOverLabel: (month: number, day: number) => `${month}월 ${day}일의 전시`,
  /** `3 / 12` — 위치 표시 */
  positionLabel: (position: number, total: number) => `${position} / ${total}`,
  /** `발행까지 — 그림 3점, 전시 테마` */
  publishPending: (blockers: string) => `발행까지 — ${blockers}`,
  /** `인증번호가 맞지 않습니다. (남은 횟수 3회)` — UX §3.4 */
  codeAttemptsLeft: (message: string, attempts: number) => `${message} (남은 횟수 ${attempts}회)`,
  /** `인증번호 다시 받기 (43초)` — 재발송 대기 */
  resendAvailableIn: (label: string, seconds: number) => `${label} (${seconds}초)`,
  /** `12명` — 입장자 수 */
  entrantCount: (count: number) => `${count}명`,
  /** `↑ 한낮의 그늘` — 연장된 날의 전시 제목 */
  carriedOverTitle: (title: string) => `↑ ${title}`,
  /** `8 / 12` — 회원별 감상 진행 */
  viewedRatio: (viewed: number, total: number) => `${viewed} / ${total}`,
  /** 값이 없는 자리 */
  none: '—',
  /** `7/12` — 드래프트 진행률 */
  draftProgress: (done: number, total: number) => `${done}/${total}`,
  /** 글자 수 카운터 `12 / 20` */
  charCounter: (current: number, max: number) => `${current} / ${max}`,
} as const

/** 화면별 문구 */
export const screens = {
  landing: {
    firstExhibitionPending: status.firstExhibitionPending,
  },

  login: {
    phoneLabel: '전화번호',
    passwordLabel: '비밀번호',
    forgotPassword: '비밀번호를 잊으셨나요?',
    showPassword: '비밀번호 보기',
    hidePassword: '비밀번호 숨기기',
  },

  social: {
    divider: '또는',
    /** `카카오로 시작하기` — 제공자 이름은 서버가 준 `label`이다 */
    startWith: (label: string) => `${label}로 시작하기`,
    linkWith: (label: string) => `${label} 연결하기`,
    linkedWith: (label: string) => `${label} 연결됨`,
    unlink: '해제',
    unlinked: '연결을 해제했습니다.',
    section: '연결된 로그인',
    lastIdentityHint: '마지막 로그인 수단은 해제할 수 없습니다.',
    /** A-4 상단 안내. 어느 제공자로 들어왔는지 먼저 알려 준다 */
    linkIntro: (label: string) => `${label} 계정으로 들어오셨습니다.`,
    linkExistingGuide: '쓰시던 전화번호와 비밀번호를 넣으면 이 계정에 연결됩니다.',
    linkNewGuide: '전화번호와 이름만 넣으면 바로 시작하실 수 있습니다.',
    toExisting: '이미 회원이신가요? 기존 계정에 연결하기',
    toNew: '처음이신가요? 새로 시작하기',
    submitLink: '연결하기',
    submitNew: '시작하기',
    expired: '연결 시간이 지났습니다. 처음부터 다시 시도해 주세요.',
  },

  signup: {
    intro: [
      '갤러리 K는 매일 아침 12점의 그림이 걸리는 작은 미술관입니다.',
      '전시는 매일 바뀌고, 하나의 테마로 묶입니다.',
      '무엇을 볼지 고르실 필요는 없습니다. 그저 오시면 됩니다.',
      '초대받은 분들만 입장하실 수 있고, 광고도 비용도 없습니다.',
    ],
    phoneLabel: '전화번호',
    phoneHint: '로그인할 때 쓰는 번호입니다',
    passwordLabel: '비밀번호',
    passwordHint: '8자 이상',
    passwordOk: '8자 이상 — 확인되었습니다',
    nameLabel: '이름',
    nameHint: '갤러리에서 부를 이름입니다',
    termsLabel: '서비스 이용과 개인정보 처리에 동의합니다',
    termsTitle: '서비스 이용과 개인정보 처리 동의',
    submit: '회원 가입',
    closedTitle: '지금은 새로운 회원을 받고 있지 않습니다.',
  },

  notifyPrompt: {
    title: '매일 아침, 새 전시를 알려드릴까요?',
    body: '하루에 한 번, 새로운 전시가 걸린 날에만 보내드립니다.',
    iosTitle: '홈 화면에 추가하면 매일 아침 알려드립니다',
    iosBody: "아래 공유 버튼을 누르고 '홈 화면에 추가'를 선택해 주세요.",
    iosStepShare: '공유',
    iosStepAdd: '홈 화면에 추가',
  },

  passwordReset: {
    step1Guide: '가입하신 전화번호로 인증번호를 보내드립니다.',
    codeLabel: '인증번호',
    newPasswordLabel: '새 비밀번호',
    expired: '시간이 지났습니다. 다시 받아 주세요.',
    doneBanner: '비밀번호를 바꿨습니다. 새 비밀번호로 입장해 주세요.',
  },

  passwordChange: {
    forcedGuide: '안전을 위해 비밀번호를 새로 정해 주세요.',
    currentLabel: '현재 비밀번호',
    newLabel: '새 비밀번호',
    done: '비밀번호를 바꿨습니다.',
  },

  gallery: {
    exhibitionThemeLink: '전시 테마',
  },

  artwork: {
    sourceLabel: '출처',
  },

  settings: {
    socialSection: '연결된 로그인',
    notifySection: '알림',
    notifyToggle: '아침 알림',
    notifyTime: '알림 시각',
    notifyTimeSheetTitle: '알림 시각 선택',
    notifyDenied: '브라우저 설정에서 알림을 허용해 주세요',
    notifyIosGuide: '홈 화면에 추가하면 알림을 받을 수 있습니다',
    notifyIosGuideOpen: '안내 열기',
    notifyFailed: '알림 설정에 실패했습니다. 잠시 후 다시 시도해 주세요.',
    displaySection: '화면',
    fontScaleToggle: '큰 글씨',
    accountSection: '계정',
    nameLabel: '이름',
    phoneLabel: '전화번호',
    passwordChangeLink: '비밀번호 변경',
    withdrawLink: '탈퇴',
    withdrawTitle: '정말 탈퇴하시겠어요?',
    withdrawBody: '계정과 감상 기록이 모두 지워집니다. 되돌릴 수 없습니다.',
    withdrawDone: '탈퇴가 완료되었습니다.',
  },

  admin: {
    summaryEntrants: (count: number) => `오늘 입장 ${count}명`,
    summaryWeekly: (ratio: number) => `이번 주 꾸준히 보는 분 ${Math.round(ratio * 100)}%`,
    statsLink: '관람 현황',
    membersLink: '회원 관리',
    settingsLink: '설정',
    today: '오늘',
    carryDialogTitle: (fromLabel: string) => `${fromLabel}에 쓰던 전시를 오늘로 옮길까요?`,
    carryDialogBody: (count: number, fromLabel: string, toLabel: string) =>
      `그림 ${count}점과 원고가 오늘(${toLabel}) 전시로 옮겨집니다. ${fromLabel}은 비어 있는 채로 남습니다.`,
    carryBlocked: '오늘 날짜에 이미 작업 중인 전시가 있습니다. 먼저 정리한 뒤에 옮겨 주세요.',
  },

  editor: {
    themeCardTitle: '전시 테마',
    themeCardEmpty: '제목과 테마를 아직 쓰지 않았습니다',
    titleLabel: '전시 제목',
    themeLabel: '전시 테마',
    themeHint: '줄바꿈은 그대로 보입니다',
    publishedEditing: '발행된 전시입니다. 수정 내용은 바로 반영됩니다.',
    uploadDone: (count: number) => `사진 ${count}장을 올렸습니다. 설명을 채워 주세요.`,
    uploadOverflow: (count: number) => `빈 자리보다 ${count}장이 많습니다. 나머지는 올리지 않았습니다.`,
    slotEmpty: '빈 자리',
    slotUploading: '올리는 중',
    slotFailed: '올리지 못했습니다',
    /** 미완성 슬롯의 문자 표기 — 색 단독 표기를 피한다(DS-5, GAP-15) */
    slotIncompleteMark: 'N',
    slotsSection: '그림 12점',
    themeCardCounter: (title: number, theme: number) => `제목 ${title}자 · 테마 ${theme}자`,
    tooLong: '글자 수가 넘어 저장하지 못했습니다. 줄여 주세요.',
    imageLabel: '그림',
    imageHint: 'JPG · PNG · WebP · 20MB까지',
    artworkTitleLabel: '그림 제목',
    artistLabel: '작가',
    yearLabel: '제작 연도',
    yearHint: '1665년경처럼 자유롭게 쓰셔도 됩니다',
    descriptionLabel: '설명',
    descriptionHint: '40자 이상 권장 · 한 가지 볼거리를 짚어 주세요',
    descriptionShortHint: '조금 더 써 주시면 좋습니다',
    collectionLabel: '소장처',
    collectionHint: '선택',
    sourceLabel: '출처 링크',
    sourceHint: 'https://',
    replaceConfirmTitle: '사진을 바꿀까요?',
    replaceConfirmBody: '지금 올라가 있는 그림이 새 사진으로 바뀝니다.',
    previewIncomplete: '준비 중',
    hiddenBanner: '숨긴 전시입니다. 관람자에게 보이지 않습니다.',
    hideConfirmTitle: '이 전시를 숨길까요?',
    hideConfirmBody:
      '관람자에게 보이지 않게 되고 지난 전시 목록에서도 빠집니다. 지금 걸려 있는 전시라면 직전 전시가 대신 걸립니다.',
    unhideConfirmTitle: '다시 보이게 할까요?',
    unhideConfirmBody: '관람자와 지난 전시 목록에 다시 나타납니다.',
    previewIncompleteNote: '준비 중인 자리는 관람자에게 보이지 않습니다.',
    blockerTitle: '전시 제목',
    blockerTheme: '전시 테마',
    blockerArtwork: (count: number) => `그림 ${count}점`,
  },

  members: {
    signupOpenLabel: '신규 가입 받기',
    signupOpenOn: '링크를 아는 분은 가입할 수 있습니다',
    signupOpenOff: '새로운 가입을 받지 않습니다',
    searchPlaceholder: '이름 또는 전화번호',
    filterAll: '전체',
    filterBlocked: '차단됨',
    filterNotifyOff: '알림 꺼짐',
    joinedAt: '가입',
    lastViewed: '마지막 입장',
    blockTitle: (name: string) => `${name} 님을 차단할까요?`,
    blockBody: '다음 로그인부터 입장할 수 없습니다. 지금 로그인해 둔 상태는 유지됩니다.',
    resetPasswordTitle: (name: string) => `${name} 님의 비밀번호를 초기화할까요?`,
    resetPasswordBody: '새 비밀번호를 정하면 회원의 모든 기기에서 다시 로그인해야 합니다.',
    resetPasswordDone: (name: string, password: string) =>
      `${name} 님의 비밀번호를 ${password} 로 바꿨습니다. 전화로 알려주세요.`,
    createTitle: '계정 만들기',
    initialPasswordLabel: '초기 비밀번호',
    createdTitle: (name: string) => `${name} 님의 계정을 만들었습니다.`,
    createdDetail: (phone: string, password: string) => `전화번호 ${phone} · 초기 비밀번호 ${password}`,
    createdGuide: '전화로 알려주세요. 처음 로그인할 때 새 비밀번호를 정하게 됩니다.',
    pushActive: '알림 받는 중',
    pushInactive: '알림 실패 중',
    pushNone: '알림 꺼짐',
  },

  /** 운영 설정 키의 한국어 라벨 — 서버는 영문 키를 준다(UX §3.16) */
  settingLabels: {
    signup_open: '신규 가입 받기',
    notify_default_hour: '기본 알림 시각',
    notify_cutoff_hour: '알림 컷오프 시각',
    archive_size: '아카이브 개수',
    media_signing_mode: '이미지 접근 방식',
  } as Record<string, string>,

  adminSettings: {
    noticeConflictLink: '겹친 공지 보기',
    noticeSection: '휴관 공지',
    noticeStart: '시작일',
    noticeEnd: '종료일',
    noticeBody: '문구',
    noticeBodyPlaceholder: '9월 5일까지 잠시 쉬어갑니다. 그동안 지난 전시를 둘러보세요.',
    noticePreview: '미리보기',
    operationSection: '운영 설정',
  },

  stats: {
    privacyNote: '이 화면은 개인의 열람 기록을 보여줍니다. 가입 시 안내된 범위 안에서만 확인해 주세요.',
    searchLabel: '회원 검색',
  },

  errors: {
    notFoundTitle: '찾으시는 화면이 없습니다.',
    exhibitionNotFoundTitle: '전시를 찾을 수 없습니다.',
    renderErrorTitle: '문제가 생겼습니다.',
    maintenanceTitle: '잠시 점검 중입니다.',
    requestIdLabel: '문의 번호',
  },
} as const

/** 폼 검증 문구 — 서버 `field_errors`가 없을 때의 클라이언트 폴백 */
export const validation = {
  phoneRequired: '전화번호를 입력해 주세요.',
  phoneFormat: '전화번호를 정확히 입력해 주세요.',
  passwordRequired: '비밀번호를 입력해 주세요.',
  passwordTooShort: '8자 이상 입력해 주세요.',
  passwordTooLong: '64자까지 입력할 수 있습니다.',
  nameRequired: '이름을 입력해 주세요.',
  nameTooLong: '20자까지 입력할 수 있습니다.',
  termsRequired: '동의가 필요합니다.',
  codeFormat: '인증번호 6자리를 입력해 주세요.',
  urlFormat: 'https:// 로 시작하는 주소를 입력해 주세요.',
  tooLong: (limit: number) => `${limit}자까지 입력할 수 있습니다.`,
  dateOrder: '종료일은 시작일보다 빠를 수 없습니다.',
  required: '입력해 주세요.',
} as const
