/**
 * NOTAM 좌표 파싱 유틸리티
 * Q-code와 E) 텍스트에서 좌표 추출
 */

/**
 * Q-code에서 좌표 추출
 * 예: 4042N07410W005 -> {lat: 40.7, lng: -74.167, radius: 5}
 */
export const parseQCodeCoordinate = (qcode) => {
  if (!qcode) return null

  // Q-code 마지막 부분에서 좌표 추출
  // 형식: DDMMN/SDDDMMW/E + 반경(3자리)
  const coordPattern = /(\d{4})([NS])(\d{5})([EW])(\d{3})/
  const match = qcode.match(coordPattern)

  if (!match) return null

  const [_, latStr, latDir, lngStr, lngDir, radiusStr] = match

  // 위도: DDMM -> DD.decimal
  const latDeg = parseInt(latStr.substring(0, 2))
  const latMin = parseInt(latStr.substring(2, 4))
  let lat = latDeg + latMin / 60

  // 경도: DDDMM -> DDD.decimal
  const lngDeg = parseInt(lngStr.substring(0, 3))
  const lngMin = parseInt(lngStr.substring(3, 5))
  let lng = lngDeg + lngMin / 60

  if (latDir === 'S') lat = -lat
  if (lngDir === 'W') lng = -lng

  // 반경 (NM)
  const radius = parseInt(radiusStr)

  return {
    latitude: lat,
    longitude: lng,
    radius: radius,
    unit: 'NM'
  }
}

/**
 * DMS 좌표를 decimal로 변환
 * 예: 372818N 1265330E -> {lat: 37.471667, lng: 126.891667}
 */
export const parseDMSCoordinate = (dmsString) => {
  const pattern = /(\d{2})(\d{2})(\d{2})([NS])\s*(\d{3})(\d{2})(\d{2})([EW])/
  const match = dmsString.match(pattern)

  if (!match) return null

  const [_, latDeg, latMin, latSec, latDir, lngDeg, lngMin, lngSec, lngDir] = match

  let lat = parseInt(latDeg) + parseInt(latMin) / 60 + parseInt(latSec) / 3600
  let lng = parseInt(lngDeg) + parseInt(lngMin) / 60 + parseInt(lngSec) / 3600

  if (latDir === 'S') lat = -lat
  if (lngDir === 'W') lng = -lng

  return { latitude: lat, longitude: lng }
}

/**
 * E) 텍스트에서 좌표 추출
 */
export const extractCoordinates = (notamText) => {
  const coordinates = []

  if (!notamText) return coordinates

  // DMS 형식 찾기 (DDMMSSNDDMMSSW) - 한국 좌표 포함
  const dmsPatterns = [
    /\d{6}[NS]\s*\d{7}[EW]/g,  // 372818N 1265330E
    /\d{6}[NS]\d{7}[EW]/g,      // 372818N1265330E (공백 없음)
    /\d{4}[NS]\s*\d{5}[EW]/g,   // DDMMN DDMMME (짧은 형식)
  ]

  dmsPatterns.forEach(pattern => {
    const matches = notamText.match(pattern)
    if (matches) {
      matches.forEach(match => {
        const coord = parseDMSCoordinate(match)
        if (coord) {
          // 중복 방지
          const isDuplicate = coordinates.some(c =>
            Math.abs(c.latitude - coord.latitude) < 0.001 &&
            Math.abs(c.longitude - coord.longitude) < 0.001
          )
          if (!isDuplicate) {
            coordinates.push(coord)
          }
        }
      })
    }
  })

  return coordinates
}

/**
 * 반경 추출
 * 예: "RADIUS 5NM" -> { radius: 5, unit: 'NM' }
 */
export const extractRadius = (notamText) => {
  if (!notamText) return null

  const patterns = [
    /RADIUS\s+(\d+\.?\d*)\s*(NM|KM|M)/i,
    /(\d+\.?\d*)\s*(NM|KM|M)\s+RADIUS/i,
  ]

  for (const pattern of patterns) {
    const match = notamText.match(pattern)
    if (match) {
      return {
        radius: parseFloat(match[1]),
        unit: match[2].toUpperCase()
      }
    }
  }

  return null
}

/**
 * NM을 km로 변환
 */
export const nmToKm = (nm) => {
  return nm * 1.852
}

/**
 * NOTAM에서 좌표 정보 추출 (Q) 라인 우선, E) 텍스트 보조)
 */
export const parseNotamCoordinates = (notam) => {
  // 1. full_text의 Q) 라인에서 좌표 추출 (가장 정확)
  const fullText = notam.full_text || ''
  if (fullText) {
    // Q) 라인 찾기: Q) FIR/QCODE/TRAFFIC/PURPOSE/SCOPE/LOWER/UPPER/DDMMNDDDMMEW###
    // 한국 NOTAM: Q)RKRR (공백없음), 국제 NOTAM: Q) EPWW (공백있음)
    const qLineMatch = fullText.match(/Q\)\s*([^\r\n]+)/i)
    if (qLineMatch) {
      const qLine = qLineMatch[1]
      // Q) 라인 끝에서 좌표 추출 (예: 6449N14751W005 또는 3728N12653E010)
      const qcodeCoord = parseQCodeCoordinate(qLine)
      if (qcodeCoord) {
        return {
          type: 'circle',
          center: [qcodeCoord.longitude, qcodeCoord.latitude],
          radius: nmToKm(qcodeCoord.radius),
          radiusNM: qcodeCoord.radius,
          source: 'Q-line'
        }
      }
      // 디버깅: Q) 라인은 있지만 좌표 파싱 실패
      if (window.__NOTAM_DEBUG_COUNT === undefined) window.__NOTAM_DEBUG_COUNT = 0
      if (window.__NOTAM_DEBUG_COUNT < 3) {
        console.log(`[DEBUG] Q-line 파싱 실패 샘플:`, qLine.substring(0, 100))
        window.__NOTAM_DEBUG_COUNT++
      }
    }
  }

  // 2. qcode 필드에서 시도 (레거시)
  const qcodeValue = notam.qcode || notam.q_code
  if (qcodeValue) {
    const qcodeCoord = parseQCodeCoordinate(qcodeValue)
    if (qcodeCoord) {
      return {
        type: 'circle',
        center: [qcodeCoord.longitude, qcodeCoord.latitude],
        radius: nmToKm(qcodeCoord.radius),
        radiusNM: qcodeCoord.radius,
        source: 'qcode-field'
      }
    }
  }

  // 3. E) 텍스트에서 좌표 추출
  const eText = notam.e_text || notam.full_text || ''
  const coords = extractCoordinates(eText)
  const radiusInfo = extractRadius(eText)

  if (coords.length > 0) {
    if (coords.length === 1 && radiusInfo) {
      // 원형
      return {
        type: 'circle',
        center: [coords[0].longitude, coords[0].latitude],
        radius: radiusInfo.unit === 'NM' ? nmToKm(radiusInfo.radius) : radiusInfo.radius,
        radiusNM: radiusInfo.unit === 'NM' ? radiusInfo.radius : radiusInfo.radius / 1.852
      }
    } else if (coords.length >= 3) {
      // 다각형
      return {
        type: 'polygon',
        coordinates: coords.map(c => [c.longitude, c.latitude])
      }
    } else if (coords.length === 1) {
      // 단일 점 (반경 없음) - 기본 5NM 원으로 표시
      return {
        type: 'circle',
        center: [coords[0].longitude, coords[0].latitude],
        radius: nmToKm(5),
        radiusNM: 5
      }
    }
  }

  return null
}
