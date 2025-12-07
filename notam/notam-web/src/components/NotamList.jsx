import { useState, useMemo } from 'react'
import './NotamList.css'
import { formatNotamDate, getNotamTypeInfo, extractCategory, getNotamValidity } from '../utils/notamUtils'
import { getFullAirportName } from '../utils/airportNames'

const NotamList = ({ notams = [], onSelectNotam, onViewOnMap }) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedStatus, setSelectedStatus] = useState('all')
  const [selectedAirport, setSelectedAirport] = useState('all')
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 20

  // 필터링된 NOTAM
  const filteredNotams = useMemo(() => {
    return notams.filter((notam) => {
      const matchesSearch =
        !searchTerm ||
        notam.id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        notam.location?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        notam.e_text?.toLowerCase().includes(searchTerm.toLowerCase())

      const matchesStatus = selectedStatus === 'all' || notam.status === selectedStatus

      const matchesAirport = selectedAirport === 'all' || notam.location === selectedAirport

      return matchesSearch && matchesStatus && matchesAirport
    })
  }, [notams, searchTerm, selectedStatus, selectedAirport])

  // 페이지네이션
  const totalPages = Math.ceil(filteredNotams.length / itemsPerPage)
  const paginatedNotams = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage
    return filteredNotams.slice(startIndex, startIndex + itemsPerPage)
  }, [filteredNotams, currentPage])

  // 공항 목록
  const airports = useMemo(() => {
    return [...new Set(notams.map((n) => n.location || n.a_location).filter(Boolean))].sort()
  }, [notams])

  const getStatusBadge = (notam) => {
    const validity = getNotamValidity(notam)
    const typeInfo = getNotamTypeInfo(notam.q_code)

    return (
      <span className={`status-badge status-${validity.status.toLowerCase()}`}>
        {typeInfo.icon} {validity.label}
      </span>
    )
  }

  return (
    <div className="notam-list-container">
      {/* 필터 섹션 */}
      <div className="notam-filters">
        <input
          type="text"
          placeholder="🔍 NOTAM ID, 공항, 내용 검색..."
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value)
            setCurrentPage(1)
          }}
          className="search-input"
        />

        <select
          value={selectedStatus}
          onChange={(e) => {
            setSelectedStatus(e.target.value)
            setCurrentPage(1)
          }}
          className="filter-select"
        >
          <option value="all">전체 상태</option>
          <option value="active">활성</option>
          <option value="expired">만료</option>
          <option value="scheduled">예정</option>
          <option value="trigger">트리거</option>
        </select>

        <select
          value={selectedAirport}
          onChange={(e) => {
            setSelectedAirport(e.target.value)
            setCurrentPage(1)
          }}
          className="filter-select"
        >
          <option value="all">전체 공항 ({airports.length})</option>
          {airports.map((airport) => (
            <option key={airport} value={airport}>
              {airport}
            </option>
          ))}
        </select>

        <div className="filter-summary">
          {filteredNotams.length.toLocaleString()}개 / {notams.length.toLocaleString()}개
        </div>
      </div>

      {/* NOTAM 리스트 */}
      <div className="notam-list">
        {paginatedNotams.length === 0 ? (
          <div className="empty-state">
            <p>검색 결과가 없습니다.</p>
          </div>
        ) : (
          paginatedNotams.map((notam) => {
            const category = extractCategory(notam.e_text)
            const typeInfo = getNotamTypeInfo(notam.q_code)

            return (
              <div
                key={notam.id}
                className="notam-card"
                onClick={() => onSelectNotam && onSelectNotam(notam)}
              >
                <div className="notam-header">
                  <div className="notam-id-section">
                    <span className="notam-id">{notam.id}</span>
                    <span className="notam-location">{getFullAirportName(notam.location || notam.a_location)}</span>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    {getStatusBadge(notam)}
                    {category && category !== 'OTHER' && (
                      <span style={{
                        background: '#f0f0f0',
                        padding: '4px 10px',
                        borderRadius: '10px',
                        fontSize: '11px',
                        fontWeight: '600'
                      }}>
                        {category}
                      </span>
                    )}
                  </div>
                </div>

                {notam.q_code && (
                  <div className="notam-qcode">
                    <span style={{ color: typeInfo.color, fontWeight: '600' }}>
                      {typeInfo.icon} {typeInfo.label}
                    </span>
                    {' | '}
                    <strong>{notam.q_code}</strong>
                  </div>
                )}

                <div className="notam-dates">
                  <div className="date-item">
                    <span className="date-label">시작:</span>
                    <span className="date-value">{formatNotamDate(notam.effective_start || notam.b_start_time)}</span>
                  </div>
                  <div className="date-item">
                    <span className="date-label">종료:</span>
                    <span className="date-value">{formatNotamDate(notam.effective_end || notam.c_end_time)}</span>
                  </div>
                </div>

                {notam.e_text && (
                  <div className="notam-preview">
                    {notam.e_text.substring(0, 150)}
                    {notam.e_text.length > 150 && '...'}
                  </div>
                )}

                {onViewOnMap && (
                  <button
                    className="view-on-map-btn"
                    onClick={(e) => {
                      e.stopPropagation()
                      onViewOnMap(notam)
                    }}
                  >
                    🗺️ 지도에서 보기
                  </button>
                )}
              </div>
            )
          })
        )}
      </div>

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <div className="pagination">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="page-btn"
          >
            ← 이전
          </button>

          <span className="page-info">
            {currentPage} / {totalPages}
          </span>

          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="page-btn"
          >
            다음 →
          </button>
        </div>
      )}
    </div>
  )
}

export default NotamList
