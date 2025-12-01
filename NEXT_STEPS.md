# 다음 단계 실행 가이드

**작성일**: 2025-11-18

---

## 📋 현재 상태 요약

### ✅ 완료된 것
1. Flight Level → Feet 변환 수정 (notamParser.js)
2. 클러스터링 구현 (react-native-map-clustering)
3. 고도 필터 로직 구현 (altitudeFilter state)
4. Circle 페이드 애니메이션 구현
5. 햅틱 피드백 구현 (expo-haptics)
6. 필요한 패키지 모두 설치
7. 구문 오류 없음

### ❌ 아직 안 한 것
1. **앱 실제 실행 테스트** ← 가장 중요!
2. 성능 최적화
3. 충분한 NOTAM 데이터 (현재 79개만)
4. 고도 필터 UI 버튼 (로직만 있고 UI 없음)
5. useEffect 의존성 경고 수정

---

## 🚀 지금 바로 실행할 작업들

### 1. 앱 실행 테스트 (가장 중요!)

```bash
# notam-app 폴더로 이동
cd notam-app

# 앱 시작
npm start
```

**확인사항**:
- Metro Bundler가 정상적으로 시작되는가?
- QR 코드가 나타나는가?
- Expo Go로 스캔 시 앱이 로드되는가?
- 지도가 정상적으로 표시되는가?
- 클러스터링이 동작하는가?
- Circle 애니메이션이 보이는가?
- Callout 터치 시 햅틱 피드백이 느껴지는가?

**예상 결과**:
- ✅ 앱이 정상적으로 실행됨
- ⚠️ 79개 NOTAM만 표시됨 (클러스터링 효과 미미)

**문제 발생 시**:
1. Metro Bundler 재시작: `r` 키 입력
2. 캐시 삭제: `npm start --clear`
3. 에러 로그 확인 후 수정

---

### 2. 더 많은 NOTAM 데이터 수집

```bash
# 30일치 데이터 크롤링 (새로 생성한 스크립트)
python crawl_30days.py
```

**예상 시간**: 30-60분
**예상 결과**: 500-2000개 NOTAM

**완료 후 확인**:
```bash
# SQLite로 데이터 확인
python -c "import sqlite3; conn = sqlite3.connect('notam_realtime.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM notams'); print(f'Total NOTAMs: {cursor.fetchone()[0]}'); conn.close()"
```

---

### 3. useEffect 의존성 경고 수정

**파일**: `notam-app/src/screens/ImprovedMapScreen.js`

**문제 위치**: 70-74줄
```javascript
useEffect(() => {
  if (notams.length > 0) {
    loadNotams(); // ⚠️ loadNotams가 의존성에 없음
  }
}, [altitudeFilter]);
```

**해결 방법 1**: loadNotams를 useCallback으로 감싸기
```javascript
// loadNotams 함수를 useCallback으로 감싸기
const loadNotams = useCallback(() => {
  // 기존 loadNotams 로직
  setLoading(true);
  // ...
}, [altitudeFilter]); // 의존성 추가

// useEffect는 그대로
useEffect(() => {
  if (notams.length > 0) {
    loadNotams();
  }
}, [altitudeFilter, loadNotams]); // ✅ loadNotams 추가
```

**해결 방법 2**: 의존성 배열에 추가 (간단)
```javascript
useEffect(() => {
  if (notams.length > 0) {
    loadNotams();
  }
}, [altitudeFilter, notams.length]); // ✅ notams.length 추가
```

---

### 4. 고도 필터 UI 버튼 추가 (선택사항)

**파일**: `notam-app/src/screens/ImprovedMapScreen.js`

**추가 위치**: return 문 안, MapView 위

```javascript
{/* 고도 필터 버튼 */}
<View style={styles.filterContainer}>
  <TouchableOpacity
    style={[styles.filterButton, altitudeFilter === 'all' && styles.filterButtonActive]}
    onPress={() => setAltitudeFilter('all')}
  >
    <Text style={[styles.filterText, altitudeFilter === 'all' && styles.filterTextActive]}>
      전체
    </Text>
  </TouchableOpacity>

  <TouchableOpacity
    style={[styles.filterButton, altitudeFilter === 'high' && styles.filterButtonActive]}
    onPress={() => setAltitudeFilter('high')}
  >
    <Text style={[styles.filterText, altitudeFilter === 'high' && styles.filterTextActive]}>
      높음
    </Text>
  </TouchableOpacity>

  <TouchableOpacity
    style={[styles.filterButton, altitudeFilter === 'medium' && styles.filterButtonActive]}
    onPress={() => setAltitudeFilter('medium')}
  >
    <Text style={[styles.filterText, altitudeFilter === 'medium' && styles.filterTextActive]}>
      중간
    </Text>
  </TouchableOpacity>

  <TouchableOpacity
    style={[styles.filterButton, altitudeFilter === 'low' && styles.filterButtonActive]}
    onPress={() => setAltitudeFilter('low')}
  >
    <Text style={[styles.filterText, altitudeFilter === 'low' && styles.filterTextActive]}>
      낮음
    </Text>
  </TouchableOpacity>
</View>
```

**스타일 추가**:
```javascript
const styles = StyleSheet.create({
  // ... 기존 스타일 ...

  filterContainer: {
    position: 'absolute',
    top: 60,
    left: 10,
    right: 10,
    flexDirection: 'row',
    justifyContent: 'space-around',
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderRadius: 8,
    padding: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  filterButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 6,
    backgroundColor: '#E5E7EB',
  },
  filterButtonActive: {
    backgroundColor: '#2563EB',
  },
  filterText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
  },
  filterTextActive: {
    color: '#FFFFFF',
  },
});
```

---

## 📊 성능 최적화 (대량 NOTAM 대비)

### 5. 메모이제이션 추가

**파일**: `notam-app/src/screens/ImprovedMapScreen.js`

```javascript
import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';

// circles 생성을 useMemo로 감싸기
const filteredCircles = useMemo(() => {
  return circles.filter(circle => {
    if (altitudeFilter === 'all') return true;
    const altitude = circle.analyzedNotam?.altitude?.upper;
    if (!altitude) return altitudeFilter === 'all';

    if (altitudeFilter === 'high') return altitude >= 10000;
    if (altitudeFilter === 'medium') return altitude >= 3000 && altitude < 10000;
    if (altitudeFilter === 'low') return altitude < 3000;
    return true;
  });
}, [circles, altitudeFilter]);

// polygons도 동일하게 처리
const filteredPolygons = useMemo(() => {
  return polygons.filter(polygon => {
    // 필터 로직
  });
}, [polygons, altitudeFilter]);
```

---

## 🧪 테스트 체크리스트

### 앱 실행 후 확인할 사항

- [ ] 앱이 정상적으로 시작됨
- [ ] 지도가 로드됨 (한국 중심)
- [ ] NOTAM이 지도에 표시됨
- [ ] Circle 색상이 정확함 (높음=빨강, 낮음=초록)
- [ ] 클러스터링이 동작함 (줌 인/아웃 시)
- [ ] Callout이 열림 (마커 탭 시)
- [ ] "자세히 보기" 버튼 터치 시 햅틱 느껴짐 (모바일만)
- [ ] Circle 페이드 애니메이션이 보임
- [ ] 성능 이슈 없음 (부드러운 스크롤)

### 에러 확인

- [ ] Metro Bundler 에러 로그 확인
- [ ] React Native 경고 메시지 확인
- [ ] useEffect 의존성 경고 확인
- [ ] Console.log 확인

---

## 📈 성능 벤치마크 (많은 데이터 수집 후)

### 5000+ NOTAM 테스트 시나리오

1. **렌더링 성능**
   - 초기 로딩 시간 측정
   - 지도 패닝/줌 시 FPS 확인
   - 메모리 사용량 모니터링

2. **클러스터링 효과**
   - 줌 레벨별 클러스터 개수 확인
   - 클러스터 전환 속도 확인
   - 성능 비교 (클러스터링 ON vs OFF)

3. **필터링 성능**
   - 필터 변경 시 응답 시간
   - 5000개 NOTAM 필터링 시간 측정

---

## 🎯 최종 목표

### 단기 (오늘)
- [x] 모든 개선사항 코드 구현
- [ ] 앱 실제 실행 테스트 ← **지금 할 것!**
- [ ] 30일치 데이터 수집
- [ ] useEffect 경고 수정

### 중기 (1-2일)
- [ ] 고도 필터 UI 완성
- [ ] 성능 최적화 (메모이제이션)
- [ ] 실제 디바이스 테스트
- [ ] 버그 수정

### 장기 (1주)
- [ ] 5000+ NOTAM 성능 테스트
- [ ] 추가 필터 (타입별)
- [ ] 실시간 업데이트 구현
- [ ] 오프라인 모드

---

## 💡 실행 순서 요약

```bash
# 1. 앱 실행 (가장 중요!)
cd notam-app
npm start
# → Expo Go로 QR 스캔, 동작 확인

# 2. 더 많은 데이터 수집
cd ..
python crawl_30days.py
# → 30분 대기

# 3. useEffect 경고 수정
# → ImprovedMapScreen.js 수정

# 4. 고도 필터 UI 추가 (선택)
# → ImprovedMapScreen.js에 버튼 추가

# 5. 앱 재실행 및 최종 테스트
cd notam-app
npm start --clear
```

---

**작성자**: Claude Code Assistant
**다음 업데이트**: 앱 실행 후
