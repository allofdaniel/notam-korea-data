# NOTAM 지도 UI 개선 사항

## 수정 날짜: 2025-11-17

---

## 개선 사항

### 1. **세련된 색상 팔레트** ✨

**문제**: 파란색 원이 투명도 없이 너무 진하게 표시되어 UI가 별로였음

**해결**:
- **새로운 색상 팔레트** (고도 기반):
  - 🔴 **높음 (≥10K ft)**: `#EF4444` (부드러운 빨강)
  - 🟠 **중간 (3-10K ft)**: `#F59E0B` (부드러운 오렌지)
  - 🟢 **낮음 (<3K ft)**: `#10B981` (부드러운 녹색)
  - 🟣 **정보 없음**: `#8B5CF6` (보라색)

**투명도 조정**:
- **2D 모드**: 15% 투명도 (기존: 20%)
- **3D 모드**:
  - 높음: 35% (기존: 100%)
  - 중간: 25% (기존: 70%)
  - 낮음: 18% (기존: 40%)
  - 정보 없음: 20%

**선 두께 조정**:
- **2D 모드**: 1.5px (기존: 2px)
- **3D 모드**: 고도에 따라 차등 적용

---

### 2. **커스텀 툴팁 (말풍선)** 💬

**문제**: 기본 툴팁이 너무 단순하고 자세히 보기 버튼이 없었음

**해결**:
- **Circle 위에 투명 Marker 배치** (Circle은 커스텀 Callout 미지원)
- **세련된 카드 스타일 툴팁**:
  - 🎯 헤더: NOTAM 번호 + 공항 코드 배지
  - 📍 반경 정보: NM 단위와 KM 단위 모두 표시
  - ✈️ 고도 정보: 고도 범위 표시
  - 🔵 **"자세히 보기 →" 버튼**: 터치 시 NOTAM 상세 화면으로 이동

**툴팁 디자인**:
```
┌──────────────────────────┐
│ C2121/25        [RKJJ]  │
├──────────────────────────┤
│ 🎯 반경: 5.0 NM (9.3 km)│
│ ✈️ 고도: 0-999ft        │
├──────────────────────────┤
│   [자세히 보기 →]        │
└──────────────────────────┘
```

---

### 3. **NOTAM 표시 개수 배지** 📊

**위치**: 지도 왼쪽 하단
**스타일**: 파란색 배지
**내용**: `🗺️ 지도에 표시된 NOTAM: XXX개`

---

### 4. **개선된 마커 디자인** 📍

- **크기**: 12px × 12px 원형
- **색상**: 파란색 (`rgba(37, 99, 235, 0.8)`)
- **테두리**: 흰색 2px
- **그림자**: 부드러운 드롭 섀도우
- **중심점 명확**: Circle 중심에 정확히 배치

---

### 5. **업데이트된 범례** 🗺️

**타이틀**: ✈️ 고도 범례
**항목**:
1. 🔴 높음 (≥10K ft)
2. 🟠 중간 (3-10K ft)
3. 🟢 낮음 (<3K ft)
4. 🟣 정보 없음 (새로 추가!)

---

## 상태 분포 설명

### 대시보드 상태 분포
```
📊 상태 분포
5654 활성    ← ACTIVE + PERMANENT + TRIGGER
0 비활성     ← SCHEDULED (아직 시작 안 됨)
11 만료      ← EXPIRED
```

### 상태 정의
- **활성 (Active)**:
  - 현재 진행 중인 NOTAM
  - 영구(PERM/UFN) NOTAM
  - 날짜 정보 없는 트리거 NOTAM

- **비활성 (Inactive)**:
  - 아직 시작하지 않은 예정 NOTAM

- **만료 (Expired)**:
  - 종료일이 지난 NOTAM

---

## 기술적 세부사항

### 코드 변경사항

#### 1. Imports 추가
```javascript
const { Marker, Polygon, Circle, Callout, PROVIDER_GOOGLE } = Platform.OS === 'web'
  ? {}
  : require('react-native-maps');
```

#### 2. Circle 렌더링 개선
```javascript
<React.Fragment key={`circle-group-${index}`}>
  {/* Circle with improved transparency */}
  <Circle
    fillColor={color + Math.floor(0.15 * 255).toString(16)}
    strokeWidth={1.5}
    ...
  />

  {/* Marker with Custom Callout */}
  <Marker coordinate={...} tracksViewChanges={false}>
    <View style={styles.markerContainer}>
      <View style={styles.markerDot} />
    </View>
    <Callout tooltip={true}>
      <View style={styles.calloutContainer}>
        {/* Custom callout content */}
      </View>
    </Callout>
  </Marker>
</React.Fragment>
```

#### 3. 색상 함수 개선
```javascript
const getNotamColor = (notam) => {
  const altitude = notam.altitude;

  if (!altitude || !altitude.upper) return '#8B5CF6'; // 보라색
  if (altitude.upper >= 10000) return '#EF4444';     // 빨강
  if (altitude.upper >= 3000) return '#F59E0B';      // 오렌지
  return '#10B981';                                  // 녹색
};
```

---

## 시각적 개선 전후 비교

### 이전 (Before) ❌
- 파란색으로만 표시, 너무 진함
- 투명도 부족, 지도가 잘 안 보임
- 기본 툴팁만 표시
- 자세히 보기 불가능
- 표시 개수 알 수 없음

### 이후 (After) ✅
- 4가지 색상 (빨강, 오렌지, 녹색, 보라)
- 적절한 투명도 (15-35%)
- 세련된 커스텀 툴팁
- "자세히 보기" 버튼 포함
- 지도에 표시 개수 배지

---

## 성능 최적화

### 1. `tracksViewChanges={false}`
- Marker 리렌더링 최소화
- 지도 이동/줌 시 성능 향상

### 2. 조건부 렌더링
```javascript
{Platform.OS !== 'web' && (
  <Marker ...>
    ...
  </Marker>
)}
```
- Web에서는 기본 Circle만 표시
- Native에서만 커스텀 Callout 활성화

---

## 사용자 경험 개선

### 1. 직관적인 색상 코딩
- 빨강 = 위험 (고고도)
- 오렌지 = 주의 (중고도)
- 녹색 = 안전 (저고도)
- 보라 = 정보 확인 필요

### 2. 정보 접근성 향상
- 툴팁에서 주요 정보 즉시 확인
- "자세히 보기" 버튼으로 상세 정보 접근
- 반경을 NM과 KM 모두 표시

### 3. 시각적 피드백
- 부드러운 그림자 효과
- 명확한 중심점 마커
- 터치 가능한 버튼 디자인

---

## 수정된 파일

1. `notam-app/src/screens/ImprovedMapScreen.js`
   - Callout import 추가
   - Circle 렌더링 개선
   - Marker + Callout 추가
   - 색상 팔레트 업데이트
   - 투명도 및 선 두께 조정
   - 범례 업데이트
   - 스타일 추가 (callout, marker 등)

---

## 알려진 제한사항

1. **Web 플랫폼**: 커스텀 Callout 미지원 (기본 툴팁만 표시)
2. **성능**: 많은 NOTAM (5000+)에서는 지도 렌더링이 느려질 수 있음
3. **Callout 위치**: 일부 zoom level에서 위치가 약간 어긋날 수 있음

---

## 향후 개선 사항

1. **클러스터링**: 밀집 지역의 NOTAM을 클러스터로 그룹화
2. **필터링**: 고도별, 타입별 필터 추가
3. **애니메이션**: Circle 등장/사라질 때 페이드 효과
4. **Web 지원**: Web에서도 커스텀 Callout 구현
5. **터치 피드백**: Callout 열릴 때 햅틱 피드백
