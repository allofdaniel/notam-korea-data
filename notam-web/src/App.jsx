import { useState, useEffect } from 'react'
import axios from 'axios'
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import NotamMap from './components/NotamMap'
import NotamList from './components/NotamList'
import NotamDetailModal from './components/NotamDetailModal'
import './App.css'

// Vercel Serverless Function으로 프록시 (HTTPS 지원)
const API_BASE_URL = '/api/proxy'

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8']

function App() {
  const [stats, setStats] = useState(null)
  const [trendData, setTrendData] = useState([])
  const [dailyChangeData, setDailyChangeData] = useState([])
  const [allNotams, setAllNotams] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('dashboard')
  const [selectedNotam, setSelectedNotam] = useState(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)

      // 캐시 확인 (5분간 유효, AWS 비용 절감)
      const cacheKey = 'notam_data_cache'
      const cached = sessionStorage.getItem(cacheKey)
      if (cached) {
        const { data, timestamp } = JSON.parse(cached)
        const age = Date.now() - timestamp
        if (age < 5 * 60 * 1000) { // 5분 이내
          console.log(`📦 캐시에서 ${data.length}개 NOTAM 로드 (${Math.round(age/1000)}초 전)`)
          setAllNotams(data)
          // 통계만 새로 로드 (가벼움)
          const statsResponse = await axios.get(`${API_BASE_URL}?path=/notams/stats`)
          setStats(statsResponse.data)
          setLoading(false)
          return
        }
      }

      // 통계 로드
      const statsResponse = await axios.get(`${API_BASE_URL}?path=/notams/stats`)
      setStats(statsResponse.data)

      // 활성 NOTAM 로드 (최근 15,000개 - 지도 표시 충분)
      const notamsResponse = await axios.get(`${API_BASE_URL}?path=/notams/realtime?limit=15000`)
      const notamData = notamsResponse.data.data || []
      setAllNotams(notamData)
      console.log(`📋 ${notamData.length}개 NOTAM 로드됨 (전체 ${notamsResponse.data.count || 0}개 중)`)

      // 캐시에 저장 (5분간 유효)
      sessionStorage.setItem(cacheKey, JSON.stringify({
        data: notamData,
        timestamp: Date.now()
      }))

      // 최근 7일 추세 로드
      const days = []
      const changes = []
      let previousActive = 0

      for (let i = 6; i >= 0; i--) {
        const date = new Date()
        date.setDate(date.getDate() - i)
        const dateStr = date.toISOString().split('T')[0]

        try {
          const response = await axios.get(`${API_BASE_URL}?path=/notams/stats?date=${dateStr}`)
          const active = response.data.active || 0
          const expired = response.data.expired || 0

          days.push({
            date: `${date.getMonth() + 1}/${date.getDate()}`,
            활성: active,
          })

          // 일일 변화량 계산
          if (i < 6) {
            const dailyChange = active - previousActive
            changes.push({
              date: `${date.getMonth() + 1}/${date.getDate()}`,
              신규: Math.max(0, dailyChange),
              만료: Math.max(0, -dailyChange),
            })
          }
          previousActive = active
        } catch (err) {
          console.error(`Error loading stats for ${dateStr}:`, err)
        }
      }
      setTrendData(days)
      setDailyChangeData(changes)

      setLoading(false)
    } catch (err) {
      console.error('Error loading data:', err)
      setError(err.message)
      setLoading(false)
    }
  }

  const getStatusData = () => {
    if (!stats) return []
    return [
      { name: '활성', value: stats.active, color: '#00C49F' },
      { name: '만료', value: stats.expired, color: '#FF8042' },
      { name: '예정', value: stats.scheduled, color: '#0088FE' },
    ]
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <h2>NOTAM 데이터 로딩 중...</h2>
      </div>
    )
  }

  if (error) {
    return (
      <div className="error-container">
        <h2>⚠️ 오류 발생</h2>
        <p>{error}</p>
        <button onClick={loadData}>다시 시도</button>
      </div>
    )
  }

  return (
    <div className="app">
      <header className="header">
        <h1>🛫 NOTAM 모니터링 대시보드</h1>
        <p className="subtitle">대한민국 항공 공지 실시간 모니터링</p>
        <button className="refresh-btn" onClick={loadData}>🔄 새로고침</button>
      </header>

      {/* 탭 네비게이션 */}
      <div className="tabs">
        <button
          className={`tab ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          📊 대시보드
        </button>
        <button
          className={`tab ${activeTab === 'map' ? 'active' : ''}`}
          onClick={() => setActiveTab('map')}
        >
          🗺️ 지도
        </button>
        <button
          className={`tab ${activeTab === 'list' ? 'active' : ''}`}
          onClick={() => setActiveTab('list')}
        >
          📋 NOTAM 리스트
        </button>
      </div>

      {activeTab === 'dashboard' && stats && (
        <>
          {/* 통계 카드 */}
          <div className="stats-grid">
            <div className="stat-card primary">
              <div className="stat-icon">📊</div>
              <div className="stat-content">
                <h3>{stats.total?.toLocaleString() || 0}</h3>
                <p>전체 NOTAM</p>
                <small>S3 저장 데이터</small>
              </div>
            </div>

            <div className="stat-card success">
              <div className="stat-icon">✅</div>
              <div className="stat-content">
                <h3>{stats.active?.toLocaleString() || 0}</h3>
                <p>활성 NOTAM</p>
                <small>현재 유효한 공지</small>
              </div>
            </div>

            <div className="stat-card warning">
              <div className="stat-icon">⏱️</div>
              <div className="stat-content">
                <h3>{stats.expired?.toLocaleString() || 0}</h3>
                <p>만료된 NOTAM</p>
                <small>종료된 공지</small>
              </div>
            </div>

            <div className="stat-card info">
              <div className="stat-icon">📅</div>
              <div className="stat-content">
                <h3>{stats.scheduled?.toLocaleString() || 0}</h3>
                <p>예정된 NOTAM</p>
                <small>향후 시작 예정</small>
              </div>
            </div>
          </div>

          {/* 차트 섹션 */}
          <div className="charts-container">
            {/* NOTAM 추세 차트 */}
            <div className="chart-card">
              <h2>📈 최근 7일 활성 NOTAM 추세</h2>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="활성" stroke="#00C49F" strokeWidth={3} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* 상태 분포 차트 */}
            <div className="chart-card">
              <h2>📊 NOTAM 상태 분포</h2>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={getStatusData()}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value }) => `${name}: ${value.toLocaleString()}`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {getStatusData().map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* 일일 신규/만료 NOTAM 차트 */}
            {dailyChangeData.length > 0 && (
              <div className="chart-card full-width">
                <h2>📉 일일 신규/만료 NOTAM 변화</h2>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={dailyChangeData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="신규" stroke="#0088FE" strokeWidth={3} />
                    <Line type="monotone" dataKey="만료" stroke="#FF8042" strokeWidth={3} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* API 정보 */}
          <div className="api-info">
            <h3>📡 API 엔드포인트</h3>
            <div className="endpoint-list">
              <code>GET /api/proxy?path=/notams/stats</code>
              <code>GET /api/proxy?path=/notams/active</code>
              <code>GET /api/proxy?path=/notams/expired</code>
              <code>GET /api/proxy?path=/notams/realtime</code>
            </div>
            <p className="update-time">
              EC2 서버: http://3.27.240.67:8000 (Vercel Proxy 경유)
              <br />
              마지막 업데이트: {new Date().toLocaleString('ko-KR')}
            </p>
          </div>
        </>
      )}

      {/* 지도 탭 */}
      {activeTab === 'map' && (
        <div className="map-tab">
          <h2 className="section-title">🗺️ NOTAM 지도</h2>
          <p className="section-subtitle">
            {allNotams.length.toLocaleString()}개 NOTAM 구역 표시
          </p>
          <NotamMap notams={allNotams} />
        </div>
      )}

      {/* 리스트 탭 */}
      {activeTab === 'list' && (
        <div className="list-tab">
          <h2 className="section-title">📋 NOTAM 리스트</h2>
          <NotamList notams={allNotams} onSelectNotam={setSelectedNotam} />
        </div>
      )}

      {/* NOTAM 상세보기 모달 */}
      {selectedNotam && (
        <NotamDetailModal notam={selectedNotam} onClose={() => setSelectedNotam(null)} />
      )}

      <footer className="footer">
        <p>© 2024 NOTAM 모니터링 시스템 | EC2 + S3 기반</p>
      </footer>
    </div>
  )
}

export default App
