/**
 * 그림 메타데이터 시드 — 데모 전용
 * 설명은 UX 문서 §3.14의 지침("한 가지 볼거리를 짚어 주세요")을 따라 작성했다.
 */
export type ArtworkSeed = {
  title: string
  artist: string
  yearText: string
  description: string
  collection: string | null
  sourceUrl: string | null
  /** 세로:가로 비. 실제 서비스에서는 이미지 파이프라인이 계산한다. */
  ratio: number
}

export const ARTWORK_SEEDS: ArtworkSeed[] = [
  {
    title: '진주 귀걸이를 한 소녀',
    artist: '요하네스 페르메이르',
    yearText: '1665년경',
    description:
      '어두운 배경에서 소녀가 고개를 돌려 이쪽을 봅니다.\n귀에 걸린 진주에 창가의 빛이 한 점 맺혀 있습니다. 그 한 점이 이 그림에서 가장 밝은 자리입니다.',
    collection: '마우리츠하위스 미술관',
    sourceUrl: 'https://www.mauritshuis.nl',
    ratio: 4 / 5,
  },
  {
    title: '론강의 별이 빛나는 밤',
    artist: '빈센트 반 고흐',
    yearText: '1888년',
    description:
      '강 건너 마을의 가스등이 물 위로 길게 늘어집니다.\n하늘의 별보다 물에 비친 불빛이 더 길고 어지럽습니다. 아래쪽 물결을 먼저 보시면 좋습니다.',
    collection: '오르세 미술관',
    sourceUrl: null,
    ratio: 5 / 4,
  },
  {
    title: '우유를 따르는 여인',
    artist: '요하네스 페르메이르',
    yearText: '1658년경',
    description:
      '부엌의 작은 창으로 들어온 빛이 벽과 빵과 우유를 차례로 지납니다.\n우유가 떨어지는 자리에서 시간이 잠시 멈춰 있습니다.',
    collection: '암스테르담 국립미술관',
    sourceUrl: null,
    ratio: 4 / 5,
  },
  {
    title: '인상, 해돋이',
    artist: '클로드 모네',
    yearText: '1872년',
    description:
      '항구의 아침 안개 속에서 해가 막 떠오릅니다.\n붉은 해를 가리고 보면 하늘과 물이 거의 같은 밝기라는 것이 보입니다.',
    collection: '마르모탕 모네 미술관',
    sourceUrl: null,
    ratio: 5 / 4,
  },
  {
    title: '이삭 줍는 여인들',
    artist: '장 프랑수아 밀레',
    yearText: '1857년',
    description:
      '추수가 끝난 밭에서 세 사람이 허리를 숙이고 있습니다.\n뒤쪽 지평선의 밝은 노란빛과 앞쪽 인물의 그늘이 얼마나 다른지 보아 주세요.',
    collection: '오르세 미술관',
    sourceUrl: null,
    ratio: 5 / 4,
  },
  {
    title: '오필리아',
    artist: '존 에버렛 밀레이',
    yearText: '1852년',
    description:
      '물 위에 누운 인물 주위로 풀과 꽃이 빽빽합니다.\n그림의 절반 이상이 식물입니다. 얼굴보다 손끝을 먼저 보게 되는 구도입니다.',
    collection: '테이트 브리튼',
    sourceUrl: null,
    ratio: 5 / 4,
  },
  {
    title: '그랑드 자트 섬의 일요일 오후',
    artist: '조르주 쇠라',
    yearText: '1886년',
    description:
      '점 하나하나가 색을 섞지 않고 나란히 놓여 있습니다.\n가까이서 보면 점이, 멀리서 보면 잔디가 됩니다. 크게 보기로 한번 확대해 보세요.',
    collection: '시카고 미술관',
    sourceUrl: null,
    ratio: 5 / 4,
  },
  {
    title: '물랭 드 라 갈레트의 무도회',
    artist: '피에르 오귀스트 르누아르',
    yearText: '1876년',
    description:
      '나뭇잎 사이로 떨어진 햇빛이 사람들의 옷 위에 얼룩처럼 앉았습니다.\n그 얼룩이 그림자인지 빛인지 잠시 헷갈립니다.',
    collection: '오르세 미술관',
    sourceUrl: null,
    ratio: 5 / 4,
  },
  {
    title: '아르놀피니 부부의 초상',
    artist: '얀 반 에이크',
    yearText: '1434년',
    description:
      '두 사람 뒤에 볼록거울이 하나 걸려 있습니다.\n거울 안에는 그림 밖에 서 있는 사람이 비칩니다. 방 전체가 그 안에 들어 있습니다.',
    collection: '내셔널 갤러리',
    sourceUrl: null,
    ratio: 4 / 5,
  },
  {
    title: '기억의 지속',
    artist: '살바도르 달리',
    yearText: '1931년',
    description:
      '시계가 천처럼 늘어져 나뭇가지와 탁자에 걸쳐 있습니다.\n멀리 보이는 절벽만은 아주 또렷하게 그려져 있습니다.',
    collection: '뉴욕 현대미술관',
    sourceUrl: null,
    ratio: 5 / 4,
  },
  {
    title: '밤을 지새우는 사람들',
    artist: '에드워드 호퍼',
    yearText: '1942년',
    description:
      '늦은 밤 식당 안이 바깥보다 훨씬 밝습니다.\n문이 보이지 않습니다. 안으로 들어갈 방법도, 나올 방법도 그려져 있지 않습니다.',
    collection: '시카고 미술관',
    sourceUrl: null,
    ratio: 5 / 4,
  },
  {
    title: '수련',
    artist: '클로드 모네',
    yearText: '1916년경',
    description:
      '수면과 하늘의 경계가 없습니다.\n물에 비친 구름 위로 잎이 떠 있어, 위를 보는지 아래를 보는지 알기 어렵습니다.',
    collection: '오랑주리 미술관',
    sourceUrl: null,
    ratio: 1,
  },
]

/** 지난 전시의 제목·테마 시드 */
export const PAST_EXHIBITION_SEEDS = [
  { title: '빛을 등진 사람들', theme: '창을 등지고 선 인물들을 모았습니다.\n얼굴은 어둡고 윤곽만 밝습니다. 표정을 읽을 수 없을 때 우리는 무엇을 보게 되는지 묻고 싶었습니다.' },
  { title: '물 위에 떠 있는 것들', theme: '수면을 그린 그림 열두 점입니다.\n물은 아무것도 아닌 채로 모든 것을 비춥니다.' },
  { title: '누군가의 부엌', theme: '일하는 손과 그 주변을 그린 그림입니다.\n대단한 일이 벌어지지 않는 장면만 골랐습니다.' },
  { title: '한낮의 그늘', theme: '가장 밝은 날의 가장 짙은 그늘을 모았습니다.\n빛이 강할수록 그늘의 경계도 또렷해집니다.' },
  { title: '멀리 있는 지평선', theme: '화면의 아래 3분의 1에 지평선을 둔 그림들입니다.\n하늘이 넓어질수록 사람은 작아집니다.' },
  { title: '거울과 창', theme: '무언가를 비추는 면이 등장하는 그림입니다.\n비친 상은 늘 원래보다 조금 어둡습니다.' },
  { title: '기다리는 자세', theme: '앉아 있거나 서서 무언가를 기다리는 인물들입니다.\n기다림은 자세로 드러납니다.' },
  { title: '색을 섞지 않는 법', theme: '점과 선을 나란히 놓아 색을 만든 그림들입니다.\n가까이서 보면 흩어지고 멀리서 보면 모입니다.' },
]
