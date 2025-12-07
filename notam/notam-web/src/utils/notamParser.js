/**
 * NOTAM 좌표 파싱 유틸리티
 * Q-code와 E) 텍스트에서 좌표 추출
 */

// FIR 중심 좌표 (좌표가 없는 NOTAM용)
const FIR_CENTERS = {
  // 한국
  'RKRR': { lat: 37.5, lng: 127.0, name: '인천 FIR' },
  // 일본
  'RJJJ': { lat: 35.7, lng: 139.7, name: 'Tokyo FIR' },
  'RJTG': { lat: 35.7, lng: 139.7, name: 'Tokyo FIR' },
  // 미국
  'PAZA': { lat: 64.8, lng: -147.7, name: 'Anchorage FIR' },
  'KZAK': { lat: 21.3, lng: -157.9, name: 'Oakland Oceanic FIR' },
  'KZWY': { lat: 40.6, lng: -73.8, name: 'New York Oceanic FIR' },
  'KZAB': { lat: 33.4, lng: -112.0, name: 'Albuquerque FIR' },
  'KZDC': { lat: 38.9, lng: -77.0, name: 'Washington FIR' },
  'KZLA': { lat: 34.0, lng: -118.2, name: 'Los Angeles FIR' },
  'KZNY': { lat: 40.7, lng: -74.0, name: 'New York FIR' },
  // 중국
  'ZBPE': { lat: 39.9, lng: 116.4, name: 'Beijing FIR' },
  'ZSHA': { lat: 31.2, lng: 121.5, name: 'Shanghai FIR' },
  'ZGZU': { lat: 23.1, lng: 113.3, name: 'Guangzhou FIR' },
  'ZYSH': { lat: 45.8, lng: 126.5, name: 'Shenyang FIR' },
  // 호주
  'YBBB': { lat: -27.5, lng: 153.0, name: 'Brisbane FIR' },
  'YMMM': { lat: -37.8, lng: 144.9, name: 'Melbourne FIR' },
  // 기타
  'MMFR': { lat: 19.4, lng: -99.1, name: 'Mexico FIR' },
  'SEQM': { lat: -0.2, lng: -78.5, name: 'Quito FIR' },
}

/**
 * Q-code에서 좌표 추출
 * 예: 4042N07410W005 -> {lat: 40.7, lng: -74.167, radius: 5}
 */
export const parseQCodeCoordinate = (qcode) => {
  if (!qcode) return null

  // Q-code 마지막 부분에서 좌표 추출
  // 형식 1: DDMMN/SDDDMMW/E + 반경(3자리) - 표준
  // 형식 2: DDMMSSNDDDDMMSSERRR - 초 포함

  // 표준 형식 시도
  const coordPattern = /(\d{4})([NS])(\d{5})([EW])(\d{3})/
  const match = qcode.match(coordPattern)

  if (match) {
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

  // 초 포함 형식 시도 (DDMMSS N DDDMMSS E RRR)
  const coordPatternWithSec = /(\d{6})([NS])(\d{7})([EW])(\d{3})/
  const matchSec = qcode.match(coordPatternWithSec)

  if (matchSec) {
    const [_, latStr, latDir, lngStr, lngDir, radiusStr] = matchSec

    // 위도: DDMMSS -> DD.decimal
    const latDeg = parseInt(latStr.substring(0, 2))
    const latMin = parseInt(latStr.substring(2, 4))
    const latSec = parseInt(latStr.substring(4, 6))
    let lat = latDeg + latMin / 60 + latSec / 3600

    // 경도: DDDMMSS -> DDD.decimal
    const lngDeg = parseInt(lngStr.substring(0, 3))
    const lngMin = parseInt(lngStr.substring(3, 5))
    const lngSec = parseInt(lngStr.substring(5, 7))
    let lng = lngDeg + lngMin / 60 + lngSec / 3600

    if (latDir === 'S') lat = -lat
    if (lngDir === 'W') lng = -lng

    const radius = parseInt(radiusStr)

    return {
      latitude: lat,
      longitude: lng,
      radius: radius,
      unit: 'NM'
    }
  }

  return null
}

/**
 * Q-line에서 FIR 코드와 고도 정보 추출
 */
export const parseQLineMetadata = (qLine) => {
  if (!qLine) return null

  // Q) FIR/QCODE/TRAFFIC/PURPOSE/SCOPE/LOWER/UPPER/COORD
  const parts = qLine.split('/')
  if (parts.length < 2) return null

  const fir = parts[0].trim()
  const qcode = parts.length > 1 ? parts[1].trim() : null

  // 고도 정보 추출 (FL 또는 feet)
  let lowerAlt = null
  let upperAlt = null

  if (parts.length >= 7) {
    const lowerStr = parts[5]
    const upperStr = parts[6]

    if (lowerStr && /^\d+$/.test(lowerStr)) {
      lowerAlt = parseInt(lowerStr) * 100 // FL -> feet
    }
    if (upperStr && /^\d+$/.test(upperStr)) {
      upperAlt = parseInt(upperStr) * 100
    }
  }

  return {
    fir,
    qcode,
    lowerAltitude: lowerAlt,
    upperAltitude: upperAlt
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
 * NOTAM에서 좌표 정보 추출 (Q) 라인 우선, E) 텍스트 보조, FIR 폴백)
 */
export const parseNotamCoordinates = (notam) => {
  const fullText = notam.full_text || ''
  let qLineData = null

  // 1. full_text의 Q) 라인에서 좌표 추출 (가장 정확)
  if (fullText) {
    // Q) 라인 찾기: Q) FIR/QCODE/TRAFFIC/PURPOSE/SCOPE/LOWER/UPPER/DDMMNDDDMMEW###
    const qLineMatch = fullText.match(/Q\)\s*([^\r\n]+)/i)
    if (qLineMatch) {
      const qLine = qLineMatch[1]
      qLineData = parseQLineMetadata(qLine)

      // Q) 라인 끝에서 좌표 추출
      const qcodeCoord = parseQCodeCoordinate(qLine)
      if (qcodeCoord) {
        return {
          type: 'circle',
          center: [qcodeCoord.longitude, qcodeCoord.latitude],
          radius: nmToKm(qcodeCoord.radius),
          radiusNM: qcodeCoord.radius,
          source: 'Q-line',
          metadata: qLineData
        }
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
        source: 'qcode-field',
        metadata: qLineData
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
        radiusNM: radiusInfo.unit === 'NM' ? radiusInfo.radius : radiusInfo.radius / 1.852,
        source: 'E-text',
        metadata: qLineData
      }
    } else if (coords.length >= 3) {
      // 다각형
      return {
        type: 'polygon',
        coordinates: coords.map(c => [c.longitude, c.latitude]),
        source: 'E-text',
        metadata: qLineData
      }
    } else if (coords.length === 1) {
      // 단일 점 (반경 없음) - 기본 5NM 원으로 표시
      return {
        type: 'circle',
        center: [coords[0].longitude, coords[0].latitude],
        radius: nmToKm(5),
        radiusNM: 5,
        source: 'E-text-single',
        metadata: qLineData
      }
    }
  }

  // 4. FIR 중심 좌표로 폴백 (좌표가 없는 NOTAM)
  if (qLineData && qLineData.fir) {
    const firCenter = FIR_CENTERS[qLineData.fir]
    if (firCenter) {
      return {
        type: 'circle',
        center: [firCenter.lng, firCenter.lat],
        radius: nmToKm(100), // FIR 전체는 큰 반경으로
        radiusNM: 100,
        source: 'FIR-fallback',
        firName: firCenter.name,
        metadata: qLineData
      }
    }
  }

  // 5. location 필드로 공항 좌표 사용
  const location = notam.location || notam.a_location
  if (location) {
    const airportCoord = getAirportCoordinates(location)
    if (airportCoord) {
      return {
        type: 'circle',
        center: [airportCoord.lng, airportCoord.lat],
        radius: nmToKm(5),
        radiusNM: 5,
        source: 'airport-location',
        metadata: qLineData
      }
    }
  }

  return null
}

/**
 * 공항 코드로 좌표 가져오기 (주요 공항)
 */
const getAirportCoordinates = (icao) => {
  const AIRPORT_COORDS = {
    // 한국
    'RKSI': { lat: 37.4691, lng: 126.4505 }, // 인천
    'RKSS': { lat: 37.5583, lng: 126.7906 }, // 김포
    'RKPK': { lat: 35.1795, lng: 128.9382 }, // 김해
    'RKPC': { lat: 33.5067, lng: 126.4926 }, // 제주
    'RKJJ': { lat: 35.1261, lng: 126.8089 }, // 광주
    'RKTU': { lat: 36.7167, lng: 127.4986 }, // 청주
    'RKTN': { lat: 35.8941, lng: 128.6589 }, // 대구
    'RKNY': { lat: 37.7529, lng: 128.9445 }, // 양양
    'RKNW': { lat: 37.4412, lng: 126.6897 }, // 원주
    'RKPU': { lat: 35.9879, lng: 129.4206 }, // 울산
    'RKPS': { lat: 34.8424, lng: 128.0700 }, // 사천
    'RKJB': { lat: 34.9914, lng: 126.3828 }, // 무안
    'RKJY': { lat: 35.4931, lng: 127.1174 }, // 여수
    // 일본
    'RJTT': { lat: 35.5533, lng: 139.7811 }, // 도쿄 하네다
    'RJAA': { lat: 35.7647, lng: 140.3864 }, // 나리타
    'RJBB': { lat: 34.4347, lng: 135.2441 }, // 간사이
    'RJCC': { lat: 42.7752, lng: 141.6924 }, // 신치토세
    'RJFF': { lat: 33.5859, lng: 130.4511 }, // 후쿠오카
    // 미국
    'KJFK': { lat: 40.6413, lng: -73.7781 }, // JFK
    'KLAX': { lat: 33.9425, lng: -118.4081 }, // LAX
    'KORD': { lat: 41.9742, lng: -87.9073 }, // 시카고
    'KSFO': { lat: 37.6213, lng: -122.3790 }, // 샌프란시스코
    'KEWR': { lat: 40.6895, lng: -74.1745 }, // 뉴어크
    'PAFA': { lat: 64.8151, lng: -147.8561 }, // 페어뱅크스
    'PANC': { lat: 61.1744, lng: -149.9964 }, // 앵커리지
    // 중국
    'ZBAA': { lat: 40.0799, lng: 116.6031 }, // 베이징
    'ZSPD': { lat: 31.1434, lng: 121.8052 }, // 상하이 푸동
    'ZGGG': { lat: 23.3924, lng: 113.2988 }, // 광저우
  }
  return AIRPORT_COORDS[icao] || null
}
