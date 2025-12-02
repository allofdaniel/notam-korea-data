import { useState, useEffect, useCallback } from 'react'
import Map, { Source, Layer, Popup } from 'react-map-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import './NotamMap.css'
import { parseNotamCoordinates } from '../utils/notamParser'

const MAPBOX_TOKEN = 'pk.eyJ1IjoiYWxsb2ZkYW5pZWwiLCJhIjoiY21pbzYzNGcxMGo3YjNocjF2cnFsOTAwYyJ9.QPYBKPCE-jvhrF7npeVIqA'

const NotamMap = ({ notams = [] }) => {
  const [viewport, setViewport] = useState({
    longitude: 127.0,
    latitude: 37.5,
    zoom: 6,
  })
  const [selectedNotam, setSelectedNotam] = useState(null)
  const [circles, setCircles] = useState([])
  const [polygons, setPolygons] = useState([])

  useEffect(() => {
    if (!notams || notams.length === 0) return

    const parsedCircles = []
    const parsedPolygons = []
    const failedNotams = []

    notams.forEach((notam, index) => {
      // Q-code와 E) 텍스트에서 좌표 실시간 파싱
      const coordinates = parseNotamCoordinates(notam)

      if (!coordinates) {
        // 파싱 실패한 NOTAM 기록
        failedNotams.push({
          id: notam.id,
          location: notam.location || notam.a_location,
          qcode: notam.qcode || notam.q_code,
          hasEText: !!(notam.e_text || notam.full_text)
        })
        return
      }

      if (coordinates.type === 'circle') {
        parsedCircles.push({
          id: `circle-${index}`,
          notam: { ...notam, coordinates },
          center: coordinates.center,
          radius: coordinates.radius,
        })
      } else if (coordinates.type === 'polygon') {
        parsedPolygons.push({
          id: `polygon-${index}`,
          notam: { ...notam, coordinates },
          coordinates: coordinates.coordinates,
        })
      }
    })

    console.log(`🗺️ 파싱 결과: 원형 ${parsedCircles.length}개, 다각형 ${parsedPolygons.length}개`)
    console.log(`❌ 파싱 실패: ${failedNotams.length}개 (전체 ${notams.length}개 중)`)

    // 실패한 NOTAM 중 처음 5개만 샘플 출력
    if (failedNotams.length > 0) {
      console.log('📋 파싱 실패 샘플 (처음 5개):')
      failedNotams.slice(0, 5).forEach(n => {
        console.log(`  - ${n.id} (${n.location}): Q-code=${n.qcode || 'N/A'}, E-text=${n.hasEText ? 'Yes' : 'No'}`)
      })
    }

    setCircles(parsedCircles)
    setPolygons(parsedPolygons)
  }, [notams])

  // 원형을 다각형으로 변환 (Mapbox는 원형을 직접 지원하지 않음)
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
    coords.push(coords[0]) // 닫기

    return coords
  }, [])

  // 원형 레이어 데이터
  const circlesGeoJSON = {
    type: 'FeatureCollection',
    features: circles.map((circle) => ({
      type: 'Feature',
      properties: {
        notamId: circle.notam.id,
        location: circle.notam.location,
        qCode: circle.notam.q_code,
      },
      geometry: {
        type: 'Polygon',
        coordinates: [createCirclePolygon(circle.center, circle.radius)],
      },
    })),
  }

  // 다각형 레이어 데이터
  const polygonsGeoJSON = {
    type: 'FeatureCollection',
    features: polygons.map((polygon) => ({
      type: 'Feature',
      properties: {
        notamId: polygon.notam.id,
        location: polygon.notam.location,
        qCode: polygon.notam.q_code,
      },
      geometry: {
        type: 'Polygon',
        coordinates: [polygon.coordinates],
      },
    })),
  }

  const handleMapClick = useCallback((event) => {
    const features = event.features
    if (features && features.length > 0) {
      const feature = features[0]
      const notamId = feature.properties.notamId
      const notam = notams.find((n) => n.id === notamId)
      if (notam) {
        setSelectedNotam(notam)
      }
    }
  }, [notams])

  return (
    <div className="notam-map-container">
      <Map
        {...viewport}
        onMove={(evt) => setViewport(evt.viewState)}
        mapStyle="mapbox://styles/mapbox/dark-v11"
        mapboxAccessToken={MAPBOX_TOKEN}
        style={{ width: '100%', height: '600px' }}
        onClick={handleMapClick}
        interactiveLayerIds={['circles-fill', 'polygons-fill']}
      >
        {/* 원형 레이어 */}
        <Source id="circles" type="geojson" data={circlesGeoJSON}>
          <Layer
            id="circles-fill"
            type="fill"
            paint={{
              'fill-color': '#FF6B6B',
              'fill-opacity': 0.3,
            }}
          />
          <Layer
            id="circles-outline"
            type="line"
            paint={{
              'line-color': '#FF0000',
              'line-width': 2,
            }}
          />
        </Source>

        {/* 다각형 레이어 */}
        <Source id="polygons" type="geojson" data={polygonsGeoJSON}>
          <Layer
            id="polygons-fill"
            type="fill"
            paint={{
              'fill-color': '#4ECDC4',
              'fill-opacity': 0.3,
            }}
          />
          <Layer
            id="polygons-outline"
            type="line"
            paint={{
              'line-color': '#00CEC9',
              'line-width': 2,
            }}
          />
        </Source>

        {/* 선택된 NOTAM 팝업 */}
        {selectedNotam && selectedNotam.coordinates && (
          <Popup
            longitude={selectedNotam.coordinates.center?.[0] || selectedNotam.coordinates.coordinates?.[0]?.[0] || 127.0}
            latitude={selectedNotam.coordinates.center?.[1] || selectedNotam.coordinates.coordinates?.[0]?.[1] || 37.5}
            anchor="bottom"
            onClose={() => setSelectedNotam(null)}
            closeOnClick={false}
          >
            <div className="notam-popup">
              <h3>{selectedNotam.location}</h3>
              <p><strong>ID:</strong> {selectedNotam.id}</p>
              <p><strong>Q-Code:</strong> {selectedNotam.q_code}</p>
              <p><strong>상태:</strong> {selectedNotam.status}</p>
              {selectedNotam.e_text && (
                <p className="notam-text">{selectedNotam.e_text.substring(0, 100)}...</p>
              )}
            </div>
          </Popup>
        )}
      </Map>

      {/* 지도 정보 */}
      <div className="map-info">
        <div className="map-legend">
          <div className="legend-item">
            <div className="legend-color" style={{ background: '#FF6B6B' }}></div>
            <span>원형 구역 ({circles.length}개)</span>
          </div>
          <div className="legend-item">
            <div className="legend-color" style={{ background: '#4ECDC4' }}></div>
            <span>다각형 구역 ({polygons.length}개)</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default NotamMap
