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

  // DMS 형식 찾기 (DDMMSSNDDMMSSW)
  const dmsPattern = /\d{6}[NS]\s*\d{7}[EW]/g
  const dmsMatches = notamText.match(dmsPattern)

  if (dmsMatches) {
    dmsMatches.forEach(match => {
      const coord = parseDMSCoordinate(match)
      if (coord) coordinates.push(coord)
    })
  }

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
 * NOTAM에서 좌표 정보 추출 (Q-code 우선, E) 텍스트 보조)
 */
export const parseNotamCoordinates = (notam) => {
  // 1. Q-code에서 좌표 추출 시도
  if (notam.qcode) {
    const qcodeCoord = parseQCodeCoordinate(notam.qcode)
    if (qcodeCoord) {
      return {
        type: 'circle',
        center: [qcodeCoord.longitude, qcodeCoord.latitude], // [lng, lat] for Mapbox
        radius: nmToKm(qcodeCoord.radius), // km로 변환
        radiusNM: qcodeCoord.radius
      }
    }
  }

  // 2. E) 텍스트에서 좌표 추출
  const fullText = notam.full_text || notam.e_text || ''
  const coords = extractCoordinates(fullText)
  const radiusInfo = extractRadius(fullText)

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
