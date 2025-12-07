import './NotamDetailModal.css'
import { formatDate, getNotamTypeInfo, extractCategory, getNotamValidity, getPriorityColor, calculatePriority, interpretNotam, parseAltitude, parseFIR, parseNotamSections, getAltitudeColor } from '../utils/notamUtils'
import { getFullAirportName } from '../utils/airportNames'

const NotamDetailModal = ({ notam, onClose }) => {
  if (!notam) return null

  const typeInfo = getNotamTypeInfo(notam.q_code)
  const category = extractCategory(notam.e_text)
  const validity = getNotamValidity(notam)
  const priority = calculatePriority(notam)
  const priorityColor = getPriorityColor(priority)
  const interpretation = interpretNotam(notam)
  const altitude = parseAltitude(notam)
  const fir = parseFIR(notam)
  const sections = parseNotamSections(notam)

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
              {fir && (
                <div className="detail-item">
                  <span className="detail-label">FIR:</span>
                  <span className="detail-value">{fir}</span>
                </div>
              )}
            </div>
          </div>

          {altitude && (
            <div className="detail-section">
              <h3>📐 고도 정보</h3>
              <div className="altitude-display" style={{
                background: `linear-gradient(135deg, ${getAltitudeColor(altitude.lower)} 0%, ${getAltitudeColor(altitude.upper)} 100%)`,
                padding: '16px',
                borderRadius: '8px',
                marginBottom: '12px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ textAlign: 'center', flex: 1 }}>
                    <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.7)', marginBottom: '4px' }}>하한 고도</div>
                    <div style={{ fontSize: '16px', fontWeight: '700', color: 'white' }}>{altitude.lowerDisplay}</div>
                  </div>
                  <div style={{ fontSize: '24px', color: 'rgba(255,255,255,0.5)' }}>↕</div>
                  <div style={{ textAlign: 'center', flex: 1 }}>
                    <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.7)', marginBottom: '4px' }}>상한 고도</div>
                    <div style={{ fontSize: '16px', fontWeight: '700', color: 'white' }}>{altitude.upperDisplay}</div>
                  </div>
                </div>
              </div>
              {altitude.raw && (
                <div style={{ fontSize: '11px', color: '#8b949e', textAlign: 'center' }}>
                  Q-Line 원본: {altitude.raw.lowerStr || '000'}/{altitude.raw.upperStr || '999'}
                </div>
              )}
            </div>
          )}

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

          {/* NOTAM 본문 내용 (E 섹션) - 가장 중요 */}
          {(sections.E || notam.e_text) && (
            <div className="detail-section">
              <h3>📝 E) NOTAM 본문 내용</h3>
              <div className="notam-e-text" style={{
                whiteSpace: 'pre-wrap',
                background: 'var(--bg-secondary, #0d1117)',
                padding: '16px',
                borderRadius: '8px',
                fontSize: '13px',
                lineHeight: '1.8',
                color: 'var(--text-primary, #e6edf3)',
                border: '2px solid var(--accent-cyan, #00d4ff)',
                fontFamily: 'var(--font-mono, monospace)'
              }}>
                {sections.E || notam.e_text}
              </div>
            </div>
          )}

          {/* NOTAM 전체 섹션 (Q~G) */}
          {(notam.full_text && Object.keys(sections).length > 0) && (
            <div className="detail-section">
              <h3>📄 NOTAM 전문 (전체 섹션)</h3>
              <div className="notam-sections" style={{
                background: 'var(--bg-secondary, #0d1117)',
                padding: '16px',
                borderRadius: '8px',
                border: '1px solid var(--border-color, rgba(0, 212, 255, 0.2))'
              }}>
                {sections.Q && (
                  <div className="notam-section-item" style={{ marginBottom: '12px' }}>
                    <span style={{ color: '#00d4ff', fontWeight: '700', fontFamily: 'monospace' }}>Q) </span>
                    <span style={{ color: '#8b949e', fontFamily: 'monospace', fontSize: '12px' }}>{sections.Q}</span>
                  </div>
                )}
                {sections.A && (
                  <div className="notam-section-item" style={{ marginBottom: '8px' }}>
                    <span style={{ color: '#00ff87', fontWeight: '700', fontFamily: 'monospace' }}>A) </span>
                    <span style={{ color: '#e6edf3', fontFamily: 'monospace', fontSize: '12px' }}>{sections.A}</span>
                  </div>
                )}
                {sections.B && (
                  <div className="notam-section-item" style={{ marginBottom: '8px' }}>
                    <span style={{ color: '#ffaa00', fontWeight: '700', fontFamily: 'monospace' }}>B) </span>
                    <span style={{ color: '#e6edf3', fontFamily: 'monospace', fontSize: '12px' }}>{sections.B}</span>
                    <span style={{ color: '#8b949e', fontSize: '11px', marginLeft: '8px' }}>(시작)</span>
                  </div>
                )}
                {sections.C && (
                  <div className="notam-section-item" style={{ marginBottom: '8px' }}>
                    <span style={{ color: '#ffaa00', fontWeight: '700', fontFamily: 'monospace' }}>C) </span>
                    <span style={{ color: '#e6edf3', fontFamily: 'monospace', fontSize: '12px' }}>{sections.C}</span>
                    <span style={{ color: '#8b949e', fontSize: '11px', marginLeft: '8px' }}>(종료)</span>
                  </div>
                )}
                {sections.D && (
                  <div className="notam-section-item" style={{ marginBottom: '8px' }}>
                    <span style={{ color: '#f72585', fontWeight: '700', fontFamily: 'monospace' }}>D) </span>
                    <span style={{ color: '#e6edf3', fontFamily: 'monospace', fontSize: '12px', whiteSpace: 'pre-wrap' }}>{sections.D}</span>
                    <span style={{ color: '#8b949e', fontSize: '11px', marginLeft: '8px' }}>(운영시간)</span>
                  </div>
                )}
                {sections.E && (
                  <div className="notam-section-item" style={{ marginBottom: '8px', paddingTop: '8px', borderTop: '1px dashed rgba(0, 212, 255, 0.2)' }}>
                    <span style={{ color: '#00d4ff', fontWeight: '700', fontFamily: 'monospace' }}>E) </span>
                    <span style={{ color: '#e6edf3', fontFamily: 'monospace', fontSize: '12px', whiteSpace: 'pre-wrap' }}>{sections.E}</span>
                    <span style={{ color: '#8b949e', fontSize: '11px', marginLeft: '8px' }}>(본문)</span>
                  </div>
                )}
                {sections.F && (
                  <div className="notam-section-item" style={{ marginBottom: '8px' }}>
                    <span style={{ color: '#7209b7', fontWeight: '700', fontFamily: 'monospace' }}>F) </span>
                    <span style={{ color: '#e6edf3', fontFamily: 'monospace', fontSize: '12px' }}>{sections.F}</span>
                    <span style={{ color: '#8b949e', fontSize: '11px', marginLeft: '8px' }}>(하한고도)</span>
                  </div>
                )}
                {sections.G && (
                  <div className="notam-section-item" style={{ marginBottom: '8px' }}>
                    <span style={{ color: '#7209b7', fontWeight: '700', fontFamily: 'monospace' }}>G) </span>
                    <span style={{ color: '#e6edf3', fontFamily: 'monospace', fontSize: '12px' }}>{sections.G}</span>
                    <span style={{ color: '#8b949e', fontSize: '11px', marginLeft: '8px' }}>(상한고도)</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 원본 전문 (파싱되지 않은 경우) */}
          {notam.full_text && Object.keys(sections).length === 0 && (
            <div className="detail-section">
              <h3>📄 NOTAM 원본 전문</h3>
              <div className="notam-full-text" style={{
                whiteSpace: 'pre-wrap',
                fontFamily: 'monospace',
                background: 'var(--bg-secondary, #0d1117)',
                padding: '12px',
                borderRadius: '8px',
                fontSize: '12px',
                lineHeight: '1.6',
                overflowX: 'auto',
                color: 'var(--text-secondary, #8b949e)'
              }}>
                {notam.full_text}
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
