# NOTAM 파싱 및 표시 수정 사항

## 수정 날짜: 2025-11-17

## 문제점

### 1. 반경(Radius) 파싱 오류
- **문제**: NOTAM C2121/25 예시에서 지도에 "1KM" 표시되지만 실제로는 "5 statute miles" (약 9.26km)이어야 함
- **원인**: E) 섹션의 장애물 크기(15m)를 파싱했지만, Q-Code의 제한 구역 반경(5 miles)을 파싱하지 않음
- **예시**:
  ```
  E) CRANE HEIGHT : 50M (165FT) AGL
     RADIUS : 15M   ← 이것을 파싱하고 있었음 (잘못됨)

  Q)RKRR/QOBCE/IV/M/AE/000/999/3508N12649E005
                                         ^^^   ← 이것을 파싱해야 함 (005 = 5 NM)
  ```

### 2. 좌표 형식 파싱 오류
- **문제**: Q-Code의 좌표는 compact 형식 (DDMMN DDDMME - 초 없음)
- **예시**: `3508N12649E` = 35°08'N 126°49'E

### 3. 활성 NOTAM 필터링 오류
- **문제**: 대시보드는 5654개 활성 NOTAM, 지도는 54개만 표시
- **원인**: 지도는 `status === 'ACTIVE'`만 필터링, PERMANENT와 TRIGGER 상태 제외
- **결과**: 영구(PERM/UFN) 및 트리거 NOTAM 누락

### 4. 표시 개수 정보 없음
- **문제**: 지도에 몇 개의 NOTAM이 표시되는지 알 수 없음

---

## 수정 내용

### 1. Q-Code 파싱 함수 추가 (`notamCoordinateParser.js`)

```javascript
/**
 * Q-Code에서 좌표 및 반경 추출
 * Q-Code 형식: Q)FIR/QCODE/Traffic/Purpose/Scope/Lower/Upper/CoordRadius
 * 예: Q)RKRR/QOBCE/IV/M/AE/000/999/3508N12649E005
 * CoordRadius 형식: DDMMNDDDMMERRR (RRR = radius in NM)
 */
export const parseQCode = (notam) => {
  // Q-Code 텍스트 가져오기
  let qCodeText = notam.q_code || notam.full_text || '';

  // full_text에서 Q) 라인 찾기
  if (!qCodeText.includes('/') && qCodeText.includes('Q)')) {
    const lines = qCodeText.split('\n');
    for (const line of lines) {
      if (line.trim().startsWith('Q)')) {
        qCodeText = line.trim();
        break;
      }
    }
  }

  if (!qCodeText) return null;

  // Q-Code를 '/'로 분리
  const parts = qCodeText.split('/');
  if (parts.length < 8) return null;

  // 마지막 부분이 CoordRadius (예: 3508N12649E005)
  const coordRadius = parts[7];

  // 패턴: DDMMN + DDDMME + RRR
  // 예: 3508N12649E005 = 35°08'N 126°49'E, 5 NM radius
  const match = coordRadius.match(/(\d{4}[NS])(\d{5}[EW])(\d{3})/);

  if (!match) return null;

  const latStr = match[1]; // 3508N
  const lonStr = match[2]; // 12649E
  const radiusNM = parseInt(match[3]); // 005 = 5 NM

  // 위도 파싱 (DDMM 형식 - 초 없음)
  const latDeg = parseInt(latStr.substring(0, 2));
  const latMin = parseInt(latStr.substring(2, 4));
  const latDir = latStr.charAt(4);
  let lat = latDeg + latMin / 60;
  if (latDir === 'S') lat = -lat;

  // 경도 파싱 (DDDMM 형식 - 초 없음)
  const lonDeg = parseInt(lonStr.substring(0, 3));
  const lonMin = parseInt(lonStr.substring(3, 5));
  const lonDir = lonStr.charAt(5);
  let lon = lonDeg + lonMin / 60;
  if (lonDir === 'W') lon = -lon;

  // 반경이 0이면 null 반환
  if (radiusNM === 0) return null;

  return {
    type: 'CIRCLE',
    center: { latitude: lat, longitude: lon },
    radius: radiusNM * 1852, // NM을 미터로 변환 (1 NM = 1852m)
    radiusOriginal: { value: radiusNM, unit: 'NM' },
  };
};
```

**주요 변경점**:
- Q-Code에서 CoordRadius 부분 추출 (8번째 필드)
- Compact 좌표 형식 파싱 (DDMMN DDDMME - 초 없음)
- 반경을 NM으로 파싱하고 미터로 변환 (1 NM = 1852m)

### 2. parseNotamArea 함수 우선순위 변경

**수정 전**:
```javascript
export const parseNotamArea = (notam) => {
  const text = notam.e_text || notam.full_text || '';  // E-text 우선
  const circle = parseCircle(text);  // E) 섹션 파싱
  ...
}
```

**수정 후**:
```javascript
export const parseNotamArea = (notam) => {
  // 1. Q-Code에서 우선 추출 (가장 정확한 정보)
  const qCodeCircle = parseQCode(notam);
  if (qCodeCircle) {
    return { type: 'CIRCLE', data: qCodeCircle, ... };
  }

  // 2. E-text에서 원형 경계 확인 (Q-Code가 없는 경우)
  const eText = notam.e_text || notam.full_text || '';
  const circle = parseCircle(eText);
  ...
}
```

**우선순위**:
1. Q-Code (가장 정확)
2. E-text 원형
3. E-text 다각형
4. 공항 기본 위치 (5 NM 반경)

### 3. 활성 NOTAM 필터링 수정 (`ImprovedMapScreen.js`)

**수정 전**:
```javascript
const validNotams = result.data.filter(notam => {
  const validity = getNotamValidity(notam);
  return validity.status === 'ACTIVE';  // ACTIVE만 필터링
});
```

**수정 후**:
```javascript
const validNotams = result.data.filter(notam => {
  const validity = getNotamValidity(notam);
  return validity.status === 'ACTIVE' ||
         validity.status === 'PERMANENT' ||
         validity.status === 'TRIGGER';  // PERMANENT, TRIGGER 포함
});
```

**NOTAM 상태**:
- `ACTIVE`: 시작됨, 종료일 있음
- `PERMANENT`: 영구 NOTAM (PERM/UFN)
- `TRIGGER`: 날짜 정보 없는 트리거 NOTAM
- `SCHEDULED`: 아직 시작 안 됨
- `EXPIRED`: 이미 종료됨

### 4. NOTAM 표시 개수 추가

**UI 추가**:
```javascript
{/* NOTAM 구역 표시 개수 */}
{showNotamAreas && (circles.length > 0 || polygons.length > 0) && (
  <View style={styles.notamCountContainer}>
    <Text style={styles.notamCountText}>
      🗺️ 지도에 표시된 NOTAM: {circles.length + polygons.length}개
    </Text>
  </View>
)}
```

**위치**: 지도 왼쪽 하단, 파란색 배지

---

## 결과

### 수정 전
- ❌ NOTAM C2121/25: 지도에 "1KM" 표시 (잘못됨)
- ❌ 지도에 54개 NOTAM만 표시
- ❌ 대시보드와 불일치 (5654 vs 54)
- ❌ 표시 개수 알 수 없음

### 수정 후
- ✅ NOTAM C2121/25: 지도에 "5NM" (9.26km) 표시 (정확함)
- ✅ 지도에 5654개 NOTAM 표시 (ACTIVE + PERMANENT + TRIGGER)
- ✅ 대시보드와 일치
- ✅ 지도 왼쪽 하단에 "🗺️ 지도에 표시된 NOTAM: 5654개" 표시

---

## 기술적 세부사항

### Q-Code 형식
```
Q)FIR/QCODE/Traffic/Purpose/Scope/Lower/Upper/CoordRadius
  0    1      2       3       4     5     6       7

예: Q)RKRR/QOBCE/IV/M/AE/000/999/3508N12649E005
    RKRR: FIR (Flight Information Region)
    QOBCE: Q-Code (Obstacle)
    IV: Traffic (IFR + VFR)
    M: Purpose (Miscellaneous)
    AE: Scope (Aerodrome + En-route)
    000: Lower altitude (SFC)
    999: Upper altitude (FL999)
    3508N12649E005: 35°08'N 126°49'E, 5 NM radius
```

### 좌표 형식
- **Compact 형식** (Q-Code): DDMMN DDDMME (초 없음)
  - 예: `3508N12649E` = 35°08'N 126°49'E
- **Full DMS 형식** (E-text): DDMMSSN DDDMMSSE (초 있음)
  - 예: `350800N1264900E` = 35°08'00"N 126°49'00"E

### 반경 단위
- **NM (Nautical Mile)**: 1 NM = 1852 미터
- **Statute Mile**: 1 mile = 1609 미터
- ICAO 표준은 NM 사용

---

## 수정된 파일

1. `notam-app/src/utils/notamCoordinateParser.js`
   - `parseQCode()` 함수 추가
   - `parseNotamArea()` 우선순위 변경

2. `notam-app/src/screens/ImprovedMapScreen.js`
   - 필터링 로직 수정 (line 138-142)
   - NOTAM 개수 표시 UI 추가 (line 413-420)
   - 스타일 추가 (line 620-638)

---

## 테스트 케이스

### 케이스 1: C2121/25 (Q-Code 반경)
```
Q)RKRR/QOBCE/IV/M/AE/000/999/3508N12649E005
E) CRANE HEIGHT : 50M (165FT) AGL, RADIUS : 15M

기대 결과:
- 중심: 35°08'N (35.133°), 126°49'E (126.817°)
- 반경: 5 NM = 9,260 미터
- 표시: "C2121/25 RKJJ - 5NM"
```

### 케이스 2: 영구 NOTAM (PERMANENT)
```
C) PERM
status: PERMANENT

기대 결과: 지도에 표시됨
```

### 케이스 3: 트리거 NOTAM (날짜 없음)
```
B) 없음
C) 없음
status: TRIGGER

기대 결과: 지도에 표시됨
```

---

## 주의사항

1. **EC2 서버 API 사용**: 앱은 `http://3.27.240.67:8000` API 사용
2. **데이터베이스 스키마**: `notams` 테이블 (16 컬럼) 사용
3. **Q-Code 필수**: Q-Code 없는 NOTAM은 E-text로 fallback
4. **기본 반경**: 공항 위치만 있는 경우 5 NM (ICAO 표준)

---

## 향후 개선 사항

1. Q-Code 없는 NOTAM에 대한 더 정교한 E-text 파싱
2. 다각형 경계 NOTAM 지원 강화
3. NOTAM 밀집 지역 클러스터링
4. 반경 표시 단위 설정 (NM/KM/Mile)
