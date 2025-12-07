/**
 * NOTAM 날짜/시간 파싱 (YYMMDDHHMM 및 ISO 형식 지원)
 */
export const parseNotamDateTime = (dateStr) => {
  if (!dateStr) return null

  // 특수 케이스 처리
  if (dateStr === 'PERM' || dateStr === 'UFN' || dateStr === 'UNKNOWN') {
    return null
  }

  try {
    // ISO 형식 (YYYY-MM-DDTHH:MM:SSZ)
    if (dateStr.includes('T') || dateStr.includes('-')) {
      const date = new Date(dateStr)
      return isNaN(date.getTime()) ? null : date
    }

    // NOTAM 형식 (YYMMDDHHMM)
    if (dateStr.length === 10 && /^\d+$/.test(dateStr)) {
      const year = parseInt(dateStr.substring(0, 2), 10)
      const month = parseInt(dateStr.substring(2, 4), 10) - 1
      const day = parseInt(dateStr.substring(4, 6), 10)
      const hour = parseInt(dateStr.substring(6, 8), 10)
      const minute = parseInt(dateStr.substring(8, 10), 10)

      // 2000년대인지 1900년대인지 판단
      const fullYear = year >= 70 ? 1900 + year : 2000 + year

      const date = new Date(fullYear, month, day, hour, minute)
      return isNaN(date.getTime()) ? null : date
    }

    return null
  } catch (error) {
    console.error('Date parsing error:', error)
    return null
  }
}

/**
 * NOTAM 날짜 포맷 (화면 표시용 - 간단)
 */
export const formatNotamDate = (dateStr) => {
  if (!dateStr) return '미정'
  if (dateStr === 'PERM') return '영구'
  if (dateStr === 'UFN') return '추후 공지'
  if (dateStr === 'N/A') return 'N/A'

  const date = parseNotamDateTime(dateStr)
  if (!date) return dateStr // 파싱 실패시 원본 반환

  const month = date.getMonth() + 1
  const day = date.getDate()
  const hours = date.getHours()
  const mins = date.getMinutes()

  return `${month}/${day} ${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`
}

/**
 * 날짜 포맷팅 (상세 - 년도 포함)
 */
export const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  if (dateString === 'PERM') return '영구'
  if (dateString === 'UFN') return '추후 공지'

  const date = parseNotamDateTime(dateString)
  if (!date) return dateString

  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')

  return `${year}-${month}-${day} ${hours}:${minutes}`
}

/**
 * NOTAM 타입 정보 반환 (Q-code 기반)
 */
export const getNotamTypeInfo = (qCode) => {
  if (!qCode) {
    return { icon: '📋', color: '#667eea', label: '일반', priority: 5 }
  }

  // 활주로 (최우선)
  if (qCode.includes('QMR')) {
    return { icon: '🛫', color: '#FF6B6B', label: '활주로', priority: 1 }
  }

  // 위험구역 (높은 우선순위)
  if (qCode.includes('QWD')) {
    return { icon: '⚠️', color: '#FFA500', label: '위험구역', priority: 2 }
  }

  // 장애물
  if (qCode.includes('QOB')) {
    return { icon: '🏗️', color: '#FFD93D', label: '장애물', priority: 3 }
  }

  // 시설
  if (qCode.includes('QFA') || qCode.includes('QP')) {
    return { icon: '🅿️', color: '#4ECDC4', label: '시설', priority: 4 }
  }

  // 조명
  if (qCode.includes('QL')) {
    return { icon: '💡', color: '#95E1D3', label: '조명', priority: 4 }
  }

  // 통신
  if (qCode.includes('QC')) {
    return { icon: '📡', color: '#A8E6CF', label: '통신', priority: 4 }
  }

  // 항행안전시설
  if (qCode.includes('QN')) {
    return { icon: '🎯', color: '#FFB7B2', label: '항행시설', priority: 3 }
  }

  return { icon: '📋', color: '#667eea', label: '일반', priority: 5 }
}

/**
 * NOTAM 텍스트에서 카테고리 추출
 */
export const extractCategory = (notamText) => {
  if (!notamText) return 'OTHER'

  const text = notamText.toLowerCase()

  if (text.includes('rwy') || text.includes('runway')) {
    return 'RUNWAY'
  } else if (text.includes('twy') || text.includes('taxiway')) {
    return 'TAXIWAY'
  } else if (text.includes('apron') || text.includes('parking')) {
    return 'APRON'
  } else if (text.includes('vor') || text.includes('ils') || text.includes('dme')) {
    return 'NAVIGATION'
  } else if (text.includes('airspace') || text.includes('restricted')) {
    return 'AIRSPACE'
  } else if (text.includes('obstacle') || text.includes('crane')) {
    return 'OBSTACLE'
  } else if (text.includes('facility') || text.includes('terminal')) {
    return 'FACILITY'
  }

  return 'OTHER'
}

/**
 * NOTAM 우선순위 계산
 */
export const calculatePriority = (notam) => {
  const text = notam.e_text?.toLowerCase() || ''
  let priority = 0

  // 활주로 관련 - 최고 우선순위
  if (text.includes('rwy') && (text.includes('closed') || text.includes('clo'))) {
    priority += 10
  }

  // 항행 시설 장애
  if (text.includes('u/s') || text.includes('out of service')) {
    priority += 8
  }

  // 공역 제한
  if (text.includes('restricted') || text.includes('prohibited')) {
    priority += 7
  }

  // 장애물
  if (text.includes('obstacle') || text.includes('crane')) {
    priority += 5
  }

  return priority
}

/**
 * NOTAM 유효성 상태 계산
 */
export const getNotamValidity = (notam) => {
  const now = new Date()
  const startDate = parseNotamDateTime(notam.effective_start || notam.b_start_time)
  const endDate = parseNotamDateTime(notam.effective_end || notam.c_end_time)

  // 영구 NOTAM
  if (notam.effective_end === 'PERM' || notam.c_end_time === 'PERM' ||
      notam.effective_end === 'UFN' || notam.c_end_time === 'UFN') {
    return { status: 'PERMANENT', daysRemaining: Infinity, label: '영구' }
  }

  // 날짜 없음 (트리거 NOTAM)
  if (!startDate || !endDate) {
    return { status: 'TRIGGER', daysRemaining: null, label: '트리거' }
  }

  // 시작 전
  if (now < startDate) {
    const daysUntilStart = Math.ceil((startDate - now) / (1000 * 60 * 60 * 24))
    return { status: 'SCHEDULED', daysRemaining: daysUntilStart, label: '예정' }
  }

  // 종료됨
  if (now > endDate) {
    return { status: 'EXPIRED', daysRemaining: 0, label: '만료' }
  }

  // 활성
  const daysRemaining = Math.ceil((endDate - now) / (1000 * 60 * 60 * 24))
  return { status: 'ACTIVE', daysRemaining, label: '활성' }
}

/**
 * 우선순위 색상 반환
 */
export const getPriorityColor = (priority) => {
  if (priority >= 8) return '#D32F2F' // 빨간색 - 매우 중요
  if (priority >= 5) return '#F57C00' // 주황색 - 중요
  if (priority >= 3) return '#FDD835' // 노란색 - 보통
  return '#43A047' // 초록색 - 낮음
}

/**
 * NOTAM 텍스트 추출 (우선순위: e_text > full_text)
 */
export const getNotamText = (notam) => {
  if (notam.e_text && notam.e_text.trim()) {
    return notam.e_text.trim()
  }
  if (notam.full_text && notam.full_text.trim()) {
    return notam.full_text.trim()
  }
  return '내용 없음'
}

/**
 * Q-code 해석 사전 - 2자리 주제 코드
 */
const QCODE_SUBJECT = {
  'FA': '비행장 시설',
  'FT': '터미널 시설',
  'FP': '주차장',
  'IC': '관제 서비스',
  'IG': '착륙 시설',
  'LA': '공항 조명',
  'LC': '진입 조명',
  'LG': '지상 조명',
  'LI': '활주로 조명',
  'MA': '비행장 이동 지역',
  'MH': '헬기장',
  'MK': '계류장',
  'MR': '활주로',
  'MT': '유도로',
  'MX': '비행장 운영',
  'NA': 'NAVAID 장비',
  'NB': 'NDB',
  'NV': 'VOR',
  'ND': 'DME',
  'NI': 'ILS',
  'NM': '마커',
  'NL': 'LOCALIZER',
  'OA': '항공 장애물',
  'OB': '장애물',
  'OL': '장애등',
  'PA': '항공 정보',
  'PI': '계기 접근 절차',
  'PX': '기타 절차',
  'RA': '공역 제한',
  'RC': '항로 폐쇄',
  'RD': '위험 구역',
  'RM': '군 연습',
  'RO': '제한 구역',
  'RP': '금지 구역',
  'RT': '임시 제한',
  'RU': 'UAS/드론 구역',
  'SA': '비행 서비스',
  'WA': '항공 경보',
  'WC': '공중전투 연습',
  'WD': '위험 구역',
  'WE': '연습 구역',
  'WH': '화재 사격',
  'WM': '미사일/포병 연습',
  'WP': '패러슈트/낙하',
  'WU': 'UAS/드론 활동',
}

/**
 * Q-code 상태/조건 코드
 */
const QCODE_CONDITION = {
  'A': '사용가능/재개',
  'C': '폐쇄',
  'H': '시간 변경',
  'K': '재개',
  'L': '제한',
  'N': '취소',
  'O': '운영중',
  'P': '설치됨',
  'R': '제거됨',
  'S': '서비스중',
  'T': '테스트중',
  'U': '사용불가',
  'W': '활성화',
  'X': '기타',
}

/**
 * NOTAM Q-code 해석
 * Q-code 형식: QXXYZ
 * - Q = 항상 Q
 * - XX = 2자리 주제 코드 (예: RP = 금지 구역, MR = 활주로)
 * - Y = 상태/조건 코드 (예: C = 폐쇄, A = 재개)
 * - Z = 추가 정보 (선택)
 */
export const interpretQCode = (qCode) => {
  if (!qCode) return { subject: '', condition: '', purpose: '', summary: '' }

  try {
    // Q-code는 보통 5자리: QRPCN, QMRLC 등
    let code = qCode.toUpperCase().trim()

    // Q로 시작하면 제거
    if (code.startsWith('Q')) {
      code = code.substring(1)
    }

    // 최소 3자리 필요 (주제 2자리 + 상태 1자리)
    if (code.length < 3) {
      return { subject: '', condition: '', purpose: '', summary: qCode }
    }

    // 주제 코드 (2자리)
    const subjectCode = code.substring(0, 2)
    const subject = QCODE_SUBJECT[subjectCode] || subjectCode

    // 상태/조건 코드 (3번째 문자)
    const conditionCode = code.charAt(2)
    const condition = QCODE_CONDITION[conditionCode] || conditionCode

    // 추가 정보 (4번째 문자 이후)
    const extra = code.length > 3 ? code.substring(3) : ''

    // 요약 생성
    let summary = ''
    if (subject && condition) {
      summary = `${subject} ${condition}`
    } else if (subject) {
      summary = subject
    } else {
      summary = qCode
    }

    return { subject, condition, extra, summary, qCode }
  } catch (error) {
    return { subject: '', condition: '', purpose: '', summary: qCode }
  }
}

/**
 * Q-line에서 고도 정보 추출
 * 형식: FIR/QCODE/TRAFFIC/PURPOSE/SCOPE/LOWER/UPPER/COORD
 */
export const parseAltitude = (notam) => {
  const fullText = notam.full_text || ''

  // Q) 라인 찾기
  const qLineMatch = fullText.match(/Q\)\s*([^\r\n]+)/i)
  if (!qLineMatch) return null

  const qLine = qLineMatch[1]
  const parts = qLine.split('/')

  // 최소 7개 부분이 있어야 고도 정보 추출 가능
  if (parts.length < 7) return null

  const lowerStr = parts[5]?.trim()
  const upperStr = parts[6]?.trim()

  let lowerAlt = null
  let upperAlt = null
  let lowerDisplay = 'GND'
  let upperDisplay = 'UNL'

  // 하한 고도 파싱
  if (lowerStr && /^\d+$/.test(lowerStr)) {
    const val = parseInt(lowerStr)
    if (val === 0) {
      lowerAlt = 0
      lowerDisplay = 'GND (지상)'
    } else {
      lowerAlt = val * 100
      lowerDisplay = `FL${lowerStr} (${lowerAlt.toLocaleString()}ft)`
    }
  }

  // 상한 고도 파싱
  if (upperStr && /^\d+$/.test(upperStr)) {
    const val = parseInt(upperStr)
    if (val === 999) {
      upperAlt = 99900
      upperDisplay = 'UNL (무제한)'
    } else {
      upperAlt = val * 100
      upperDisplay = `FL${upperStr} (${upperAlt.toLocaleString()}ft)`
    }
  }

  return {
    lower: lowerAlt,
    upper: upperAlt,
    lowerDisplay,
    upperDisplay,
    raw: { lowerStr, upperStr }
  }
}

/**
 * FIR 정보 추출
 */
export const parseFIR = (notam) => {
  const fullText = notam.full_text || ''

  const qLineMatch = fullText.match(/Q\)\s*([^\r\n]+)/i)
  if (!qLineMatch) return null

  const qLine = qLineMatch[1]
  const parts = qLine.split('/')

  if (parts.length < 1) return null

  return parts[0]?.trim() || null
}

/**
 * NOTAM 전체 섹션 파싱 (Q, A, B, C, D, E, F, G)
 * 각 섹션의 내용을 추출하여 객체로 반환
 */
export const parseNotamSections = (notam) => {
  const fullText = notam.full_text || ''
  const sections = {}

  // Q) 섹션 - Q-line 정보
  const qMatch = fullText.match(/Q\)\s*([^\r\n]+)/i)
  if (qMatch) sections.Q = qMatch[1].trim()

  // A) 섹션 - 위치/공항 코드
  const aMatch = fullText.match(/A\)\s*([^\r\n]+)/i)
  if (aMatch) sections.A = aMatch[1].trim()

  // B) 섹션 - 시작 시간
  const bMatch = fullText.match(/B\)\s*([^\r\n]+)/i)
  if (bMatch) sections.B = bMatch[1].trim()

  // C) 섹션 - 종료 시간
  const cMatch = fullText.match(/C\)\s*([^\r\n]+)/i)
  if (cMatch) sections.C = cMatch[1].trim()

  // D) 섹션 - 운영 시간/스케줄
  const dMatch = fullText.match(/D\)\s*([^\r\n]+(?:\r?\n(?![A-GQ]\)).*)*)/i)
  if (dMatch) sections.D = dMatch[1].trim()

  // E) 섹션 - 본문 내용 (가장 중요한 내용)
  const eMatch = fullText.match(/E\)\s*([\s\S]*?)(?=[FG]\)|$)/i)
  if (eMatch) sections.E = eMatch[1].trim()

  // F) 섹션 - 하한 고도
  const fMatch = fullText.match(/F\)\s*([^\r\n]+)/i)
  if (fMatch) sections.F = fMatch[1].trim()

  // G) 섹션 - 상한 고도
  const gMatch = fullText.match(/G\)\s*([^\r\n]+)/i)
  if (gMatch) sections.G = gMatch[1].trim()

  return sections
}

/**
 * 고도별 색상 반환 (히트맵 스타일)
 * 낮은 고도: 빨간색 (위험), 높은 고도: 파란색 (안전)
 */
export const getAltitudeColor = (upperAlt) => {
  if (upperAlt === null || upperAlt === undefined) return '#8b949e' // 회색 - 정보 없음

  // FL999 (무제한) = 99900ft
  if (upperAlt >= 99900) return '#00d4ff' // 시안 - 전체 고도
  if (upperAlt >= 45000) return '#4361ee' // 파란색 - 고고도
  if (upperAlt >= 24000) return '#7209b7' // 보라색 - 중고도
  if (upperAlt >= 10000) return '#f72585' // 핑크 - 중저고도
  if (upperAlt >= 5000) return '#ff6b35' // 주황 - 저고도
  return '#ff4757' // 빨간색 - 지상 근접
}

/**
 * 고도를 사람이 읽기 쉬운 형태로 변환
 */
export const formatAltitudeDisplay = (altFt, rawStr) => {
  if (rawStr === '000' || altFt === 0) return 'GND (지상)'
  if (rawStr === '999' || altFt >= 99900) return 'UNL (무제한)'
  if (altFt === null || altFt === undefined) return 'N/A'

  // FL 단위로 표시
  const fl = Math.round(altFt / 100)
  return `FL${String(fl).padStart(3, '0')} (${altFt.toLocaleString()}ft)`
}

/**
 * NOTAM 한글 해석 생성
 */
export const interpretNotam = (notam) => {
  if (!notam) return null

  const text = notam.e_text || notam.full_text || ''
  const qCodeInfo = interpretQCode(notam.q_code)
  const typeInfo = getNotamTypeInfo(notam.q_code)
  const validity = getNotamValidity(notam)

  let interpretation = {
    title: '',
    description: '',
    impact: '',
    action: ''
  }

  // 제목 생성
  if (qCodeInfo.summary) {
    interpretation.title = qCodeInfo.summary
  } else if (typeInfo.label !== '일반') {
    interpretation.title = `${typeInfo.label} 관련 공지`
  } else {
    interpretation.title = 'NOTAM 공지'
  }

  // 설명 생성
  const lowerText = text.toLowerCase()

  // 활주로 폐쇄
  if (lowerText.includes('rwy') && (lowerText.includes('closed') || lowerText.includes('clo'))) {
    const rwyMatch = text.match(/RWY\s*(\d{2}[LRC]?)/i)
    const runway = rwyMatch ? rwyMatch[1] : ''
    interpretation.description = `활주로 ${runway}이(가) 폐쇄되었습니다.`
    interpretation.impact = '해당 활주로를 사용할 수 없습니다. 항공기 이착륙에 영향이 있을 수 있습니다.'
    interpretation.action = '다른 활주로 사용 또는 우회 착륙을 고려하세요.'
  }
  // 항행시설 장애
  else if (lowerText.includes('u/s') || lowerText.includes('out of service') || lowerText.includes('unserviceable')) {
    interpretation.description = '항행안전시설이 작동하지 않습니다.'
    interpretation.impact = '해당 시설에 의존하는 비행 절차를 사용할 수 없습니다.'
    interpretation.action = '대체 항행 절차를 사용하거나 관제소에 문의하세요.'
  }
  // 공역 제한
  else if (lowerText.includes('restricted') || lowerText.includes('prohibited')) {
    interpretation.description = '지정된 공역의 비행이 제한됩니다.'
    interpretation.impact = '제한 공역 내 비행 시 허가가 필요하거나 진입이 금지됩니다.'
    interpretation.action = '우회 비행 또는 사전 허가를 받으세요.'
  }
  // 장애물
  else if (lowerText.includes('obstacle') || lowerText.includes('crane')) {
    interpretation.description = '새로운 장애물이 설치되었거나 기존 장애물 정보가 변경되었습니다.'
    interpretation.impact = '접근 및 이륙 시 장애물에 유의해야 합니다.'
    interpretation.action = '장애물 위치와 높이를 확인하고 안전 고도를 유지하세요.'
  }
  // 조명 시설
  else if (lowerText.includes('light') || lowerText.includes('lgt')) {
    interpretation.description = '공항 조명 시설의 운영 상태가 변경되었습니다.'
    interpretation.impact = '야간 또는 저시정 상황에서 시각 참조가 제한될 수 있습니다.'
    interpretation.action = '조명 상태를 확인하고 필요시 대체 절차를 준비하세요.'
  }
  // 일반적인 경우
  else {
    interpretation.description = 'NOTAM 내용을 확인하여 비행 계획에 반영하세요.'
    interpretation.impact = '명시된 위치, 시간, 조건에 유의가 필요합니다.'
    interpretation.action = '상세 내용을 확인하고 필요시 관련 부서에 문의하세요.'
  }

  // 유효기간 정보 추가
  const startDate = formatDate(notam.effective_start || notam.b_start_time)
  const endDate = formatDate(notam.effective_end || notam.c_end_time)

  interpretation.period = `유효기간: ${startDate} ~ ${endDate}`
  interpretation.status = validity.label

  return interpretation
}
