import './NotamDetailModal.css'
import { formatDate, getNotamTypeInfo, extractCategory, getNotamValidity, getPriorityColor, calculatePriority, interpretNotam } from '../utils/notamUtils'
import { getFullAirportName } from '../utils/airportNames'

const NotamDetailModal = ({ notam, onClose }) => {
  if (!notam) return null

  const typeInfo = getNotamTypeInfo(notam.q_code)
  const category = extractCategory(notam.e_text)
  const validity = getNotamValidity(notam)
  const priority = calculatePriority(notam)
  const priorityColor = getPriorityColor(priority)
  const interpretation = interpretNotam(notam)

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>
          ✕
        </button>

        <div className="modal-header">
          <div>
            <h2>{notam.id}</h2>
            <p style={{ fontSize: '14px', color: '#666', marginTop: '4px' }}>
              {getFullAirportName(notam.location || notam.a_location)}
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span className={`status-${validity.status.toLowerCase()}`}>
              {typeInfo.icon} {validity.label}
            </span>
            {category && (
              <span style={{
                background: '#f0f0f0',
                padding: '6px 12px',
                borderRadius: '12px',
                fontSize: '12px',
                fontWeight: '600'
              }}>
                {category}
              </span>
            )}
          </div>
        </div>

        <div className="modal-body">
          {interpretation && (
            <div className="detail-section" style={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              padding: '16px',
              borderRadius: '12px',
              marginBottom: '20px'
            }}>
              <h3 style={{ color: 'white', marginBottom: '12px' }}>💡 NOTAM 해석</h3>

              <div style={{ marginBottom: '12px' }}>
                <div style={{
                  fontSize: '16px',
                  fontWeight: '600',
                  marginBottom: '8px',
                  padding: '8px 12px',
                  background: 'rgba(255, 255, 255, 0.2)',
                  borderRadius: '8px'
                }}>
                  {interpretation.title}
                </div>
              </div>

              <div style={{ marginBottom: '10px' }}>
                <strong style={{ fontSize: '14px' }}>📋 내용:</strong>
                <div style={{ marginTop: '4px', fontSize: '14px', lineHeight: '1.5' }}>
                  {interpretation.description}
                </div>
              </div>

              <div style={{ marginBottom: '10px' }}>
                <strong style={{ fontSize: '14px' }}>⚠️ 영향:</strong>
                <div style={{ marginTop: '4px', fontSize: '14px', lineHeight: '1.5' }}>
                  {interpretation.impact}
                </div>
              </div>

              <div style={{ marginBottom: '10px' }}>
                <strong style={{ fontSize: '14px' }}>✈️ 조치:</strong>
                <div style={{ marginTop: '4px', fontSize: '14px', lineHeight: '1.5' }}>
                  {interpretation.action}
                </div>
              </div>

              {interpretation.period && (
                <div style={{
                  marginTop: '12px',
                  paddingTop: '12px',
                  borderTop: '1px solid rgba(255, 255, 255, 0.3)',
                  fontSize: '13px'
                }}>
                  📅 {interpretation.period}
                </div>
              )}
            </div>
          )}

          <div className="detail-section">
            <h3>📍 위치 정보</h3>
            <div className="detail-grid">
              <div className="detail-item">
                <span className="detail-label">공항:</span>
                <span className="detail-value">{getFullAirportName(notam.location || notam.a_location)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Q-Code:</span>
                <span className="detail-value">{notam.q_code || 'N/A'}</span>
              </div>
            </div>
          </div>

          {notam.q_code && (
            <div className="detail-section">
              <h3>{typeInfo.icon} NOTAM 유형</h3>
              <div className="detail-grid">
                <div className="detail-item">
                  <span className="detail-label">카테고리:</span>
                  <span className="detail-value" style={{ color: typeInfo.color, fontWeight: '600' }}>
                    {typeInfo.label}
                  </span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">우선순위:</span>
                  <span className="detail-value" style={{ color: priorityColor, fontWeight: '600' }}>
                    {priority >= 8 ? '긴급' : priority >= 5 ? '중요' : '일반'} ({priority})
                  </span>
                </div>
              </div>
            </div>
          )}

          <div className="detail-section">
            <h3>📅 유효 기간</h3>
            <div className="detail-grid">
              <div className="detail-item">
                <span className="detail-label">시작 (발효일):</span>
                <span className="detail-value">{formatDate(notam.effective_start || notam.b_start_time)}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">종료 (만료일):</span>
                <span className="detail-value">{formatDate(notam.effective_end || notam.c_end_time)}</span>
              </div>
            </div>
            {validity.daysRemaining !== null && validity.daysRemaining !== Infinity && (
              <p style={{ marginTop: '12px', fontSize: '14px', color: '#666', textAlign: 'center' }}>
                {validity.status === 'ACTIVE' && `⏳ ${validity.daysRemaining}일 남음`}
                {validity.status === 'SCHEDULED' && `🕐 ${validity.daysRemaining}일 후 시작`}
              </p>
            )}
          </div>

          {(notam.full_text || notam.e_text) && (
            <div className="detail-section">
              <h3>📄 NOTAM 전문 (Full Text)</h3>
              <div className="notam-full-text" style={{
                whiteSpace: 'pre-wrap',
                fontFamily: 'monospace',
                background: '#f5f5f5',
                padding: '12px',
                borderRadius: '8px',
                fontSize: '13px',
                lineHeight: '1.6',
                overflowX: 'auto'
              }}>
                {notam.full_text || notam.e_text}
              </div>
            </div>
          )}

          {notam.e_text && notam.full_text && notam.e_text !== notam.full_text && (
            <div className="detail-section">
              <h3>📝 E) 텍스트</h3>
              <div className="notam-e-text" style={{
                whiteSpace: 'pre-wrap',
                background: '#fafafa',
                padding: '10px',
                borderRadius: '6px',
                fontSize: '12px',
                lineHeight: '1.5'
              }}>
                {notam.e_text}
              </div>
            </div>
          )}

          {notam.coordinates && (
            <div className="detail-section">
              <h3>🗺️ 좌표 정보</h3>
              <div className="coordinates-info">
                <div className="detail-item">
                  <span className="detail-label">타입:</span>
                  <span className="detail-value">{notam.coordinates.type}</span>
                </div>
                {notam.coordinates.center && (
                  <div className="detail-item">
                    <span className="detail-label">중심:</span>
                    <span className="detail-value">
                      {notam.coordinates.center[1].toFixed(6)}, {notam.coordinates.center[0].toFixed(6)}
                    </span>
                  </div>
                )}
                {notam.coordinates.radius && (
                  <div className="detail-item">
                    <span className="detail-label">반경:</span>
                    <span className="detail-value">{notam.coordinates.radius} km</span>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="detail-section">
            <h3>ℹ️ 추가 정보</h3>
            <div className="detail-grid">
              {notam.a_location && (
                <div className="detail-item">
                  <span className="detail-label">A Location:</span>
                  <span className="detail-value">{notam.a_location}</span>
                </div>
              )}
              {notam.created_date && (
                <div className="detail-item">
                  <span className="detail-label">생성일:</span>
                  <span className="detail-value">{formatDate(notam.created_date)}</span>
                </div>
              )}
              {notam.series && (
                <div className="detail-item">
                  <span className="detail-label">시리즈:</span>
                  <span className="detail-value">{notam.series}</span>
                </div>
              )}
              {notam.number && (
                <div className="detail-item">
                  <span className="detail-label">번호:</span>
                  <span className="detail-value">{notam.number}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default NotamDetailModal
