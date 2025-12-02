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
 * Q-code 해석 사전
 */
const QCODE_TRANSLATIONS = {
  // 1차 식별자 (Subject)
  'QMR': '활주로',
  'QMX': '활주로 방향',
  'QMH': '활주로 시간',
  'QMT': '유도로',
  'QMA': '계류장',
  'QFA': '공항 시설',
  'QFT': '터미널',
  'QFP': '주차장',
  'QLA': '공항 조명',
  'QLC': '통신',
  'QCN': '항행 시설',
  'QNA': '항행 경고',
  'QOB': '장애물',
  'QWD': '위험 구역',
  'QWP': '훈련 구역',
  'QWA': '공역',
  'QRA': '제한 구역',
  'QRT': '운영 시간',
  'QRO': '공항 운영',
  'QSL': '조명 시스템',
  'QSN': 'SNOWTAM',
  'QFU': '활주로 방향',
  'QGO': '운영 정보',
  // 2차 식별자 (Condition)
  'A': '사용불가',
  'C': '폐쇄',
  'L': '제한',
  'O': '운영중',
  'S': '서비스중',
  'U': '사용가능',
  'W': '경고',
  // 3차 식별자 (Purpose)
  'N': '즉시',
  'O': '운영',
  'M': '필수',
  'V': 'VFR',
  'I': 'IFR',
  'B': '모두',
}

/**
 * NOTAM Q-code 해석
 */
export const interpretQCode = (qCode) => {
  if (!qCode) return { subject: '', condition: '', purpose: '', summary: '' }

  try {
    // Q-code 형식: QMRLC/QMRXX/IV/NBO/A/000/999/...
    const parts = qCode.split('/')
    if (parts.length < 2) return { subject: '', condition: '', purpose: '', summary: '' }

    const firstPart = parts[0] // QMRLC
    const secondPart = parts[1] // QMRXX

    // Subject (3자리) 추출
    const subjectCode = firstPart.substring(0, 3) || ''
    const subject = QCODE_TRANSLATIONS[subjectCode] || subjectCode

    // Condition (4번째 문자)
    const conditionCode = firstPart.charAt(3) || ''
    const condition = QCODE_TRANSLATIONS[conditionCode] || conditionCode

    // Purpose (5번째 문자)
    const purposeCode = firstPart.charAt(4) || ''
    const purpose = QCODE_TRANSLATIONS[purposeCode] || purposeCode

    // 요약 생성
    let summary = ''
    if (subject && condition) {
      summary = `${subject} ${condition}`
      if (purpose) {
        summary += ` (${purpose})`
      }
    }

    return { subject, condition, purpose, summary, qCode }
  } catch (error) {
    return { subject: '', condition: '', purpose: '', summary: '', qCode }
  }
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
