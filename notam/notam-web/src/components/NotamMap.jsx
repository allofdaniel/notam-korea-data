import { useState, useEffect, useCallback, useMemo } from 'react'
import Map, { Source, Layer, Popup } from 'react-map-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import './NotamMap.css'
import { parseNotamCoordinates } from '../utils/notamParser'
import { formatDate, interpretQCode, getNotamText, parseAltitude, parseNotamSections, getAltitudeColor, interpretNotam } from '../utils/notamUtils'

const MAPBOX_TOKEN = 'pk.eyJ1IjoiYWxsb2ZkYW5pZWwiLCJhIjoiY21pbzYzNGcxMGo3YjNocjF2cnFsOTAwYyJ9.QPYBKPCE-jvhrF7npeVIqA'

// 고도 범위 옵션 (수정: 범위 조정)
const ALTITUDE_RANGES = [
  { id: 'all', label: '전체', min: -1, max: 999999, color: '#00d4ff' },
  { id: 'gnd-5000', label: 'GND~FL050', min: -1, max: 5000, color: '#ff4757' },
  { id: '5000-10000', label: 'FL050~100', min: 5000, max: 10000, color: '#ff6b35' },
  { id: '10000-24000', label: 'FL100~240', min: 10000, max: 24000, color: '#f72585' },
  { id: '24000-45000', label: 'FL240~450', min: 24000, max: 45000, color: '#7209b7' },
  { id: '45000-unl', label: 'FL450+', min: 45000, max: 999999, color: '#4361ee' },
]

const NotamMap = ({ notams = [], focusNotam, onFocusComplete }) => {
  const [viewport, setViewport] = useState({
    longitude: 127.0,
    latitude: 37.5,
    zoom: 6,
  })
  const [hoveredNotam, setHoveredNotam] = useState(null)
  const [hoverCoords, setHoverCoords] = useState(null)
  const [selectedNotam, setSelectedNotam] = useState(null)
  const [circles, setCircles] = useState([])
  const [polygons, setPolygons] = useState([])
  const [maxRadius, setMaxRadius] = useState(500) // km, 기본값 500km
  const [showFilters, setShowFilters] = useState(false)
  const [altitudeFilter, setAltitudeFilter] = useState('all') // 고도 필터
  const [showLabels, setShowLabels] = useState(true) // 라벨 표시 여부
  const [airportFilter, setAirportFilter] = useState('') // 공항 필터

  // 고유 공항 목록 추출
  const uniqueAirports = useMemo(() => {
    const airports = new Set()
    notams.forEach(notam => {
      const loc = notam.location || notam.a_location
      if (loc) airports.add(loc)
    })
    return Array.from(airports).sort()
  }, [notams])

  // focusNotam이 변경되면 해당 위치로 이동
  useEffect(() => {
    if (focusNotam) {
      const coords = parseNotamCoordinates(focusNotam)
      if (coords?.center) {
        // 지도 이동
        setViewport(prev => ({
          ...prev,
          longitude: coords.center[0],
          latitude: coords.center[1],
          zoom: 10,
        }))
        // 해당 NOTAM 선택
        setSelectedNotam({ ...focusNotam, coordinates: coords })
        // 반경 필터 조정 (해당 NOTAM이 보이도록)
        if (coords.radius && coords.radius > maxRadius) {
          setMaxRadius(Math.ceil(coords.radius / 100) * 100 + 100)
        }
      }
      // 콜백 호출 (focusNotam 초기화)
      if (onFocusComplete) {
        setTimeout(() => onFocusComplete(), 100)
      }
    }
  }, [focusNotam, onFocusComplete, maxRadius])

  useEffect(() => {
    if (!notams || notams.length === 0) return

    const parsedCircles = []
    const parsedPolygons = []

    notams.forEach((notam, index) => {
      const coordinates = parseNotamCoordinates(notam)
      if (!coordinates) return

      // 고도 정보 파싱
      const altitude = parseAltitude(notam)
      const sections = parseNotamSections(notam)

      const notamWithAltitude = {
        ...notam,
        coordinates,
        altitude,
        sections,
        upperAlt: altitude?.upper ?? 99900, // 기본값은 UNL
        lowerAlt: altitude?.lower ?? 0,
      }

      if (coordinates.type === 'circle') {
        parsedCircles.push({
          id: `circle-${index}`,
          notam: notamWithAltitude,
          center: coordinates.center,
          radius: coordinates.radius,
          upperAlt: notamWithAltitude.upperAlt,
          lowerAlt: notamWithAltitude.lowerAlt,
        })
      } else if (coordinates.type === 'polygon') {
        parsedPolygons.push({
          id: `polygon-${index}`,
          notam: notamWithAltitude,
          coordinates: coordinates.coordinates,
          upperAlt: notamWithAltitude.upperAlt,
          lowerAlt: notamWithAltitude.lowerAlt,
        })
      }
    })

    // 반경이 큰 순서로 정렬 (큰 것이 먼저 그려져서 작은 것 위에)
    parsedCircles.sort((a, b) => b.radius - a.radius)

    console.log(`🗺️ 파싱 결과: 원형 ${parsedCircles.length}개, 다각형 ${parsedPolygons.length}개`)

    setCircles(parsedCircles)
    setPolygons(parsedPolygons)
  }, [notams])

  // 원형을 다각형으로 변환
  const createCirclePolygon = useCallback((center, radiusKm) => {
    const points = 64
    const coords = []
    const distanceX = radiusKm / (111.32 * Math.cos((center[1] * Math.PI) / 180))
    const distanceY = radiusKm / 110.574

    for (let i = 0; i < points; i++) {
      const theta = (i / points) * (2 * Math.PI)
      const x = distanceX * Math.cos(theta)
      const y = distanceY * Math.sin(theta)
      coords.push([center[0] + x, center[1] + y])
    }
    coords.push(coords[0])
    return coords
  }, [])

  // 고도 필터 함수
  const matchAltitudeFilter = useCallback((upperAlt, lowerAlt) => {
    if (altitudeFilter === 'all') return true
    const range = ALTITUDE_RANGES.find(r => r.id === altitudeFilter)
    if (!range) return true
    // 범위가 겹치면 표시
    return !(upperAlt < range.min || lowerAlt > range.max)
  }, [altitudeFilter])

  // 공항 필터 함수
  const matchAirportFilter = useCallback((notam) => {
    if (!airportFilter) return true
    const loc = notam.location || notam.a_location
    return loc === airportFilter
  }, [airportFilter])

  // 필터링된 원형 (반경 + 고도 + 공항)
  const filteredCircles = useMemo(() => {
    return circles.filter(circle =>
      circle.radius <= maxRadius &&
      matchAltitudeFilter(circle.upperAlt, circle.lowerAlt) &&
      matchAirportFilter(circle.notam)
    )
  }, [circles, maxRadius, matchAltitudeFilter, matchAirportFilter])

  // 필터링된 다각형 (고도 + 공항)
  const filteredPolygons = useMemo(() => {
    return polygons.filter(polygon =>
      matchAltitudeFilter(polygon.upperAlt, polygon.lowerAlt) &&
      matchAirportFilter(polygon.notam)
    )
  }, [polygons, matchAltitudeFilter, matchAirportFilter])

  // 원형 레이어 데이터
  const circlesGeoJSON = useMemo(() => ({
    type: 'FeatureCollection',
    features: filteredCircles.map((circle) => ({
      type: 'Feature',
      properties: {
        notamId: circle.notam.id || circle.notam.notam_id,
        notamNo: circle.notam.notam_no || circle.notam.id,
        location: circle.notam.location || circle.notam.a_location,
        qCode: circle.notam.q_code || circle.notam.qcode,
        radius: circle.radius,
        centerLng: circle.center[0],
        centerLat: circle.center[1],
        upperAlt: circle.upperAlt,
        lowerAlt: circle.lowerAlt,
        color: getAltitudeColor(circle.upperAlt),
      },
      geometry: {
        type: 'Polygon',
        coordinates: [createCirclePolygon(circle.center, circle.radius)],
      },
    })),
  }), [filteredCircles, createCirclePolygon])

  // 다각형 레이어 데이터
  const polygonsGeoJSON = useMemo(() => ({
    type: 'FeatureCollection',
    features: filteredPolygons.map((polygon) => ({
      type: 'Feature',
      properties: {
        notamId: polygon.notam.id || polygon.notam.notam_id,
        notamNo: polygon.notam.notam_no || polygon.notam.id,
        location: polygon.notam.location || polygon.notam.a_location,
        qCode: polygon.notam.q_code || polygon.notam.qcode,
        upperAlt: polygon.upperAlt,
        lowerAlt: polygon.lowerAlt,
        color: getAltitudeColor(polygon.upperAlt),
      },
      geometry: {
        type: 'Polygon',
        coordinates: [polygon.coordinates],
      },
    })),
  }), [filteredPolygons])

  // 라벨용 포인트 데이터 (원형 + 다각형 중심점)
  const labelsGeoJSON = useMemo(() => {
    if (!showLabels) return { type: 'FeatureCollection', features: [] }

    const circlePoints = filteredCircles.map((circle) => ({
      type: 'Feature',
      properties: {
        label: circle.notam.q_code || circle.notam.location || circle.notam.id,
        notamId: circle.notam.id,
      },
      geometry: {
        type: 'Point',
        coordinates: circle.center,
      },
    }))

    const polygonPoints = filteredPolygons.map((polygon) => {
      // 다각형 중심점 계산
      const coords = polygon.coordinates
      const centerLng = coords.reduce((sum, c) => sum + c[0], 0) / coords.length
      const centerLat = coords.reduce((sum, c) => sum + c[1], 0) / coords.length
      return {
        type: 'Feature',
        properties: {
          label: polygon.notam.q_code || polygon.notam.location || polygon.notam.id,
          notamId: polygon.notam.id,
        },
        geometry: {
          type: 'Point',
          coordinates: [centerLng, centerLat],
        },
      }
    })

    return {
      type: 'FeatureCollection',
      features: [...circlePoints, ...polygonPoints],
    }
  }, [filteredCircles, filteredPolygons, showLabels])

  // 클릭 핸들러
  const handleMapClick = useCallback((event) => {
    const features = event.features
    if (features && features.length > 0) {
      const feature = features[0]
      const notamId = feature.properties.notamId

      // circles나 polygons에서 해당 NOTAM 찾기
      const circleMatch = circles.find((c) => (c.notam.id || c.notam.notam_id) === notamId)
      const polygonMatch = polygons.find((p) => (p.notam.id || p.notam.notam_id) === notamId)

      const matchedNotam = circleMatch?.notam || polygonMatch?.notam
      if (matchedNotam) {
        setSelectedNotam(matchedNotam)
      }
    }
  }, [circles, polygons])

  // 호버 핸들러
  const handleMapHover = useCallback((event) => {
    const features = event.features
    if (features && features.length > 0) {
      const feature = features[0]
      setHoveredNotam({
        notamNo: feature.properties.notamNo,
        location: feature.properties.location,
        radius: feature.properties.radius,
      })
      setHoverCoords({ x: event.point.x, y: event.point.y })
    } else {
      setHoveredNotam(null)
      setHoverCoords(null)
    }
  }, [])

  // 상태에 따른 색상
  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return '#00ff87'
      case 'expired': return '#ffaa00'
      case 'scheduled': return '#00d4ff'
      default: return '#8b949e'
    }
  }

  // Q-Code 의미 가져오기
  const getQCodeMeaning = (qcode) => {
    if (!qcode) return 'N/A'
    const interpretation = interpretQCode(qcode)
    return interpretation.summary || qcode
  }

  return (
    <div className="notam-map-container">
      <Map
        {...viewport}
        onMove={(evt) => setViewport(evt.viewState)}
        mapStyle="mapbox://styles/mapbox/dark-v11"
        mapboxAccessToken={MAPBOX_TOKEN}
        style={{ width: '100%', height: selectedNotam ? '400px' : '600px' }}
        onClick={handleMapClick}
        onMouseMove={handleMapHover}
        onMouseLeave={() => { setHoveredNotam(null); setHoverCoords(null); }}
        interactiveLayerIds={['circles-fill', 'polygons-fill']}
        cursor={hoveredNotam ? 'pointer' : 'grab'}
      >
        {/* 원형 레이어 - 고도별 색상 */}
        <Source id="circles" type="geojson" data={circlesGeoJSON}>
          <Layer
            id="circles-fill"
            type="fill"
            paint={{
              'fill-color': ['get', 'color'],
              'fill-opacity': 0.3,
            }}
          />
          <Layer
            id="circles-outline"
            type="line"
            paint={{
              'line-color': ['get', 'color'],
              'line-width': 2,
            }}
          />
        </Source>

        {/* 다각형 레이어 - 고도별 색상 */}
        <Source id="polygons" type="geojson" data={polygonsGeoJSON}>
          <Layer
            id="polygons-fill"
            type="fill"
            paint={{
              'fill-color': ['get', 'color'],
              'fill-opacity': 0.3,
            }}
          />
          <Layer
            id="polygons-outline"
            type="line"
            paint={{
              'line-color': ['get', 'color'],
              'line-width': 2,
            }}
          />
        </Source>

        {/* NOTAM 코드 라벨 레이어 */}
        {showLabels && (
          <Source id="labels" type="geojson" data={labelsGeoJSON}>
            <Layer
              id="labels-text"
              type="symbol"
              layout={{
                'text-field': ['get', 'label'],
                'text-size': 10,
                'text-anchor': 'center',
                'text-offset': [0, 1.5],
                'text-allow-overlap': false,
                'text-ignore-placement': false,
              }}
              paint={{
                'text-color': '#ffffff',
                'text-halo-color': '#000000',
                'text-halo-width': 1.5,
              }}
            />
          </Source>
        )}
      </Map>

      {/* 호버 툴팁 */}
      {hoveredNotam && hoverCoords && (
        <div
          className="hover-tooltip"
          style={{
            left: hoverCoords.x + 10,
            top: hoverCoords.y + 10,
          }}
        >
          <div className="tooltip-id">{hoveredNotam.notamNo}</div>
          <div className="tooltip-location">{hoveredNotam.location}</div>
          {hoveredNotam.radius && (
            <div className="tooltip-radius">반경: {hoveredNotam.radius.toFixed(1)} km</div>
          )}
        </div>
      )}

      {/* 필터 컨트롤 */}
      <div className="map-controls">
        <button
          className="filter-toggle-btn"
          onClick={() => setShowFilters(!showFilters)}
        >
          ⚙️ 필터 {showFilters ? '닫기' : '열기'}
        </button>

        {showFilters && (
          <div className="filter-panel">
            <div className="filter-item">
              <label className="filter-label">최대 반경: {maxRadius} km</label>
              <input
                type="range"
                min="10"
                max="1000"
                step="10"
                value={maxRadius}
                onChange={(e) => setMaxRadius(Number(e.target.value))}
                className="filter-slider"
              />
              <div className="filter-range-labels">
                <span>10km</span>
                <span>1000km</span>
              </div>
            </div>
            <div className="filter-presets">
              <button onClick={() => setMaxRadius(50)}>50km</button>
              <button onClick={() => setMaxRadius(100)}>100km</button>
              <button onClick={() => setMaxRadius(200)}>200km</button>
              <button onClick={() => setMaxRadius(500)}>500km</button>
              <button onClick={() => setMaxRadius(1000)}>전체</button>
            </div>

            {/* 고도 필터 */}
            <div className="filter-item" style={{ marginTop: '16px' }}>
              <label className="filter-label">고도 필터</label>
              <div className="altitude-filter-btns" style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '8px' }}>
                {ALTITUDE_RANGES.map(range => (
                  <button
                    key={range.id}
                    onClick={() => setAltitudeFilter(range.id)}
                    style={{
                      padding: '6px 10px',
                      fontSize: '10px',
                      background: altitudeFilter === range.id ? (range.color || '#00d4ff') : 'transparent',
                      border: `1px solid ${range.color || '#00d4ff'}`,
                      borderRadius: '4px',
                      color: altitudeFilter === range.id ? '#fff' : (range.color || '#00d4ff'),
                      cursor: 'pointer',
                      fontFamily: 'monospace',
                      fontWeight: '600',
                    }}
                  >
                    {range.label}
                  </button>
                ))}
              </div>
            </div>

            {/* 공항 필터 */}
            <div className="filter-item" style={{ marginTop: '16px' }}>
              <label className="filter-label">공항 필터</label>
              <select
                value={airportFilter}
                onChange={(e) => setAirportFilter(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  marginTop: '8px',
                  background: '#0d1117',
                  border: '1px solid rgba(0, 212, 255, 0.3)',
                  borderRadius: '4px',
                  color: '#e6edf3',
                  fontFamily: 'monospace',
                  fontSize: '12px',
                  cursor: 'pointer'
                }}
              >
                <option value="">전체 공항</option>
                {uniqueAirports.map(airport => (
                  <option key={airport} value={airport}>{airport}</option>
                ))}
              </select>
            </div>

            {/* 라벨 토글 */}
            <div className="filter-item" style={{ marginTop: '12px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={showLabels}
                  onChange={(e) => setShowLabels(e.target.checked)}
                  style={{ width: '16px', height: '16px' }}
                />
                <span className="filter-label" style={{ margin: 0 }}>NOTAM 코드 라벨 표시</span>
              </label>
            </div>
          </div>
        )}
      </div>

      {/* 지도 범례 - 고도별 색상 (compact 세로 바) */}
      <div className="map-legend-compact" style={{
        position: 'absolute',
        right: '12px',
        top: '50%',
        transform: 'translateY(-50%)',
        background: 'rgba(22, 27, 34, 0.95)',
        borderRadius: '6px',
        padding: '8px 6px',
        border: '1px solid rgba(0, 212, 255, 0.3)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '2px',
        zIndex: 10
      }}>
        <div style={{ fontSize: '8px', color: '#00d4ff', marginBottom: '4px', fontWeight: '600', writingMode: 'vertical-rl', textOrientation: 'mixed' }}>UNL</div>
        <div style={{ width: '10px', height: '20px', background: '#00d4ff', borderRadius: '2px' }} title="UNL (전체)"></div>
        <div style={{ width: '10px', height: '20px', background: '#4361ee', borderRadius: '2px' }} title="FL450+"></div>
        <div style={{ width: '10px', height: '20px', background: '#7209b7', borderRadius: '2px' }} title="FL240~450"></div>
        <div style={{ width: '10px', height: '20px', background: '#f72585', borderRadius: '2px' }} title="FL100~240"></div>
        <div style={{ width: '10px', height: '20px', background: '#ff6b35', borderRadius: '2px' }} title="FL050~100"></div>
        <div style={{ width: '10px', height: '20px', background: '#ff4757', borderRadius: '2px' }} title="GND~FL050"></div>
        <div style={{ fontSize: '8px', color: '#ff4757', marginTop: '4px', fontWeight: '600', writingMode: 'vertical-rl', textOrientation: 'mixed' }}>GND</div>
        <div style={{
          marginTop: '6px',
          paddingTop: '6px',
          borderTop: '1px solid rgba(0, 212, 255, 0.3)',
          fontSize: '9px',
          color: '#8b949e',
          textAlign: 'center',
          lineHeight: '1.2'
        }}>
          <div style={{ fontWeight: '600', color: '#00d4ff' }}>{filteredCircles.length + filteredPolygons.length}</div>
          <div style={{ fontSize: '7px' }}>표시</div>
        </div>
      </div>

      {/* 선택된 NOTAM 상세 정보 패널 */}
      {selectedNotam && (
        <div className="notam-detail-panel">
          <div className="detail-panel-header">
            <div className="panel-title">
              <span className="notam-badge">#{selectedNotam.id}</span>
              <span className="location-badge">{selectedNotam.location}</span>
              <span
                className="status-badge"
                style={{ background: getStatusColor(selectedNotam.status) + '20', color: getStatusColor(selectedNotam.status) }}
              >
                {selectedNotam.status?.toUpperCase() || 'ACTIVE'}
              </span>
            </div>
            <button className="close-btn" onClick={() => setSelectedNotam(null)}>×</button>
          </div>

          <div className="detail-panel-body">
            <div className="detail-grid">
              <div className="detail-item">
                <span className="detail-label">Q-Code</span>
                <span className="detail-value">{selectedNotam.qcode || selectedNotam.q_code || 'N/A'}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Q-Code 의미</span>
                <span className="detail-value">{getQCodeMeaning(selectedNotam.qcode || selectedNotam.q_code)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">시작 시간</span>
                <span className="detail-value">{formatDate(selectedNotam.effective_start)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">종료 시간</span>
                <span className="detail-value">{formatDate(selectedNotam.effective_end) || '미정'}</span>
              </div>
              {selectedNotam.coordinates?.radius && (
                <div className="detail-item">
                  <span className="detail-label">영향 반경</span>
                  <span className="detail-value">{selectedNotam.coordinates.radius.toFixed(1)} km</span>
                </div>
              )}
              {selectedNotam.coordinates?.center && (
                <div className="detail-item">
                  <span className="detail-label">중심 좌표</span>
                  <span className="detail-value">
                    {selectedNotam.coordinates.center[1].toFixed(4)}°N, {selectedNotam.coordinates.center[0].toFixed(4)}°E
                  </span>
                </div>
              )}
            </div>

            {/* 고도 정보 */}
            {selectedNotam.altitude && (
              <div className="altitude-section" style={{ marginTop: '12px', marginBottom: '12px' }}>
                <span className="detail-label">고도 범위</span>
                <div style={{
                  background: `linear-gradient(90deg, ${getAltitudeColor(selectedNotam.altitude.lower)} 0%, ${getAltitudeColor(selectedNotam.altitude.upper)} 100%)`,
                  padding: '12px 16px',
                  borderRadius: '6px',
                  marginTop: '6px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '9px', color: 'rgba(255,255,255,0.7)' }}>하한</div>
                    <div style={{ fontSize: '13px', fontWeight: '700', color: '#fff' }}>{selectedNotam.altitude.lowerDisplay}</div>
                  </div>
                  <div style={{ fontSize: '16px', color: 'rgba(255,255,255,0.5)' }}>↔</div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '9px', color: 'rgba(255,255,255,0.7)' }}>상한</div>
                    <div style={{ fontSize: '13px', fontWeight: '700', color: '#fff' }}>{selectedNotam.altitude.upperDisplay}</div>
                  </div>
                </div>
              </div>
            )}

            {/* E) 본문 내용 - 가장 중요 */}
            {(selectedNotam.sections?.E || selectedNotam.e_text) && (
              <div className="full-text-section" style={{ marginTop: '12px' }}>
                <span className="detail-label" style={{ color: '#00d4ff' }}>E) NOTAM 본문</span>
                <pre className="full-text" style={{
                  border: '2px solid #00d4ff',
                  background: '#0d1117',
                  padding: '12px',
                  fontSize: '12px',
                  lineHeight: '1.6',
                  color: '#e6edf3'
                }}>
                  {selectedNotam.sections?.E || selectedNotam.e_text || getNotamText(selectedNotam)}
                </pre>

                {/* 한글 해석 */}
                {(() => {
                  const interpretation = interpretNotam(selectedNotam)
                  if (!interpretation) return null
                  return (
                    <div style={{
                      marginTop: '12px',
                      background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%)',
                      border: '1px solid rgba(102, 126, 234, 0.4)',
                      borderRadius: '8px',
                      padding: '12px'
                    }}>
                      <div style={{ fontSize: '11px', color: '#667eea', fontWeight: '600', marginBottom: '8px' }}>
                        한글 해석
                      </div>
                      <div style={{ fontSize: '13px', fontWeight: '600', color: '#e6edf3', marginBottom: '8px' }}>
                        {interpretation.title}
                      </div>
                      <div style={{ fontSize: '12px', color: '#c9d1d9', lineHeight: '1.5', marginBottom: '6px' }}>
                        <strong style={{ color: '#00d4ff' }}>내용:</strong> {interpretation.description}
                      </div>
                      <div style={{ fontSize: '12px', color: '#c9d1d9', lineHeight: '1.5', marginBottom: '6px' }}>
                        <strong style={{ color: '#ffaa00' }}>영향:</strong> {interpretation.impact}
                      </div>
                      <div style={{ fontSize: '12px', color: '#c9d1d9', lineHeight: '1.5' }}>
                        <strong style={{ color: '#00ff87' }}>조치:</strong> {interpretation.action}
                      </div>
                    </div>
                  )
                })()}
              </div>
            )}

            {/* NOTAM 전문 (전체 섹션) */}
            {selectedNotam.full_text && (
              <div className="full-text-section" style={{ marginTop: '12px' }}>
                <span className="detail-label">NOTAM 전문</span>
                <pre className="full-text" style={{ fontSize: '10px', color: '#8b949e', lineHeight: '1.5' }}>
                  {selectedNotam.full_text}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default NotamMap
