# NOTAM 모니터링 앱 상용화 로드맵

## 🎯 목표

**글로벌 NOTAM 모니터링 앱**
- 멀티플랫폼 (웹, iOS, Android)
- 지도 기반 시각화 (2D/3D)
- 비전공자도 이해 가능한 한글 설명
- 검색/필터링
- 구독제 비즈니스 모델

---

## 📋 Phase 1: 백엔드 강화 (1-2개월)

### 1.1 데이터 수집 확장

**현재 문제**:
- 한국 18개 공항만
- 최근 24시간만
- 전 세계 NOTAM 없음

**개선 방안**:

#### 옵션 A: 공식 데이터 소스 활용 (권장)
- **ICAO NOTAM API**: 전 세계 NOTAM 공식 데이터
  - 비용: 월 $500-2000 (규모에 따라)
  - 커버리지: 전 세계 모든 공항
  - 신뢰도: 공식 데이터
  - 법적 문제: 없음

- **FAA NOTAM Search**: 미국 NOTAM
  - 비용: 무료
  - 커버리지: 미국 전역
  - API: https://notams.aim.faa.gov/notamSearch/

- **EUROCONTROL**: 유럽 NOTAM
  - 비용: 협상 필요
  - 커버리지: 유럽 전역

#### 옵션 B: 웹 크롤링 확장
- **장점**: 무료
- **단점**:
  - 법적 리스크 (저작권, 이용약관 위반)
  - 불안정 (사이트 변경 시 중단)
  - 상업적 사용 제한 가능
  - ⚠️ **상용 서비스로는 권장하지 않음**

**추천**: ICAO NOTAM API 구독

---

### 1.2 데이터베이스 개선

**현재**:
- DynamoDB만 사용
- 중복 데이터 덮어씀
- 히스토리 없음

**개선**:

```
DynamoDB 테이블 구조 재설계:

1. NOTAM_Records (메인)
   - notam_id (파티션 키)
   - version_timestamp (정렬 키) ← 히스토리 추적
   - location, type, status, etc.

2. NOTAM_History (히스토리)
   - notam_id + timestamp
   - 변경 이력 추적

3. NOTAM_Translations (한글 번역)
   - notam_id
   - translated_text (AI 번역)
   - translation_version

4. Users (사용자)
   - user_id
   - email, subscription_tier, payment_info

5. User_Favorites (즐겨찾기)
   - user_id + notam_id
   - 사용자별 관심 NOTAM
```

**S3 활용**:
```
s3://notam-data/
  ├── raw/                   # 원본 데이터 백업
  │   └── 2025-11-13/
  │       ├── domestic/
  │       └── international/
  ├── processed/             # 처리된 데이터
  ├── translations/          # 번역 캐시
  └── exports/              # 사용자 다운로드용
```

---

### 1.3 보안 강화 🔒

**필수 구현**:

#### 1. API 인증 (API Gateway + Cognito)

```
사용자 → Cognito 로그인 → JWT 토큰 발급
     ↓
API Gateway → JWT 검증 → Lambda 실행
```

**구독 티어**:
- **Free**: 하루 100 요청, 한국만
- **Pro**: 월 $9.99, 무제한, 전 세계
- **Enterprise**: 월 $99, API 직접 접근, 우선 지원

#### 2. Rate Limiting

```
API Gateway 설정:
- Free: 10 요청/분
- Pro: 100 요청/분
- Enterprise: 1000 요청/분
```

#### 3. API 키 관리

```python
# Lambda Authorizer
def lambda_handler(event, context):
    token = event['authorizationToken']

    # Cognito JWT 검증
    user = verify_jwt(token)

    # 구독 상태 확인
    subscription = get_subscription(user['sub'])

    if subscription['tier'] == 'free':
        # Rate limit 체크
        if exceeded_rate_limit(user['sub']):
            return deny_policy()

    return allow_policy(user['sub'])
```

---

### 1.4 AI 번역 (비전공자용)

**NOTAM 한글 번역 + 쉬운 설명**

#### OpenAI GPT-4 활용:

```python
def translate_notam(notam_text, qcode):
    prompt = f"""
    다음 NOTAM을 비전공자도 이해할 수 있게 한글로 번역하고 설명해주세요:

    Q-Code: {qcode}
    내용: {notam_text}

    다음 형식으로 답변:
    1. 요약 (한 문장)
    2. 상세 설명 (쉬운 한글)
    3. 영향 범위
    4. 주의사항
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content
```

**비용**:
- GPT-4: NOTAM당 $0.01-0.02
- 캐싱으로 비용 절감 (동일 NOTAM은 재번역 안 함)

---

## 📋 Phase 2: 프론트엔드 개발 (2-3개월)

### 2.1 기술 스택 선택

#### 옵션 A: React Native (권장)

**장점**:
- 하나의 코드로 iOS, Android, Web
- 큰 커뮤니티
- React 생태계 활용

**구조**:
```
notam-app/
├── src/
│   ├── screens/          # 화면
│   │   ├── MapScreen.tsx      # 지도 뷰
│   │   ├── ListScreen.tsx     # 리스트 뷰
│   │   ├── DetailScreen.tsx   # 상세 정보
│   │   └── SettingsScreen.tsx
│   ├── components/       # 컴포넌트
│   │   ├── NotamMarker.tsx    # 지도 마커
│   │   ├── NotamCard.tsx      # NOTAM 카드
│   │   └── Map2D3DToggle.tsx
│   ├── services/         # API 호출
│   │   ├── api.ts
│   │   └── auth.ts
│   ├── store/           # 상태 관리 (Redux/Zustand)
│   └── utils/
├── ios/
├── android/
└── web/
```

**필수 라이브러리**:
```json
{
  "dependencies": {
    "react-native": "^0.73.0",
    "react-native-maps": "^1.10.0",        // 2D 지도
    "react-native-webview": "^13.0.0",     // 3D 지도 (Cesium)
    "@react-navigation/native": "^6.0.0",  // 네비게이션
    "axios": "^1.6.0",                     // API 호출
    "aws-amplify": "^6.0.0",               // AWS 인증
    "react-native-gesture-handler": "^2.0.0",
    "zustand": "^4.0.0"                    // 상태 관리
  }
}
```

#### 옵션 B: Flutter

**장점**:
- 네이티브 성능
- 아름다운 UI

**단점**:
- Dart 언어 학습 필요
- React 생태계와 다름

---

### 2.2 핵심 기능 구현

#### 2D 지도 (React Native Maps)

```typescript
import MapView, { Marker } from 'react-native-maps';

function NotamMapScreen() {
  const [notams, setNotams] = useState([]);

  useEffect(() => {
    fetch('https://api.example.com/notams')
      .then(res => res.json())
      .then(data => setNotams(data.data));
  }, []);

  return (
    <MapView
      initialRegion={{
        latitude: 37.5665,  // 서울
        longitude: 126.9780,
        latitudeDelta: 10,
        longitudeDelta: 10,
      }}
    >
      {notams.map(notam => (
        <Marker
          key={notam.notam_id}
          coordinate={parseCoordinates(notam.location)}
          title={notam.notam_id}
          description={notam.translated_text}
          pinColor={notam.status === 'ACTIVE' ? 'red' : 'gray'}
        />
      ))}
    </MapView>
  );
}
```

#### 3D 지도 (Cesium via WebView)

```typescript
import { WebView } from 'react-native-webview';

function Map3DScreen() {
  const cesiumHTML = `
    <!DOCTYPE html>
    <html>
    <head>
      <script src="https://cesium.com/downloads/cesiumjs/releases/1.111/Build/Cesium/Cesium.js"></script>
      <link href="https://cesium.com/downloads/cesiumjs/releases/1.111/Build/Cesium/Widgets/widgets.css" rel="stylesheet">
    </head>
    <body>
      <div id="cesiumContainer"></div>
      <script>
        const viewer = new Cesium.Viewer('cesiumContainer');

        // NOTAM 마커 추가
        const notams = ${JSON.stringify(notams)};
        notams.forEach(notam => {
          viewer.entities.add({
            position: Cesium.Cartesian3.fromDegrees(
              notam.longitude,
              notam.latitude,
              1000  // 고도
            ),
            billboard: {
              image: notam.status === 'ACTIVE' ? 'red-pin.png' : 'gray-pin.png',
              scale: 0.5
            },
            description: notam.translated_text
          });
        });
      </script>
    </body>
    </html>
  `;

  return <WebView source={{ html: cesiumHTML }} />;
}
```

#### NOTAM 좌표 파싱

```typescript
// Q-Code에서 좌표 추출
function parseCoordinates(notam) {
  // 예: "373325N1264751E" → { lat: 37.5569, lng: 126.7975 }

  const coordMatch = notam.full_text.match(/(\d{6}[NS])(\d{7}[EW])/);

  if (!coordMatch) {
    // 공항 코드로 대체
    return getAirportCoordinates(notam.location);
  }

  const lat = parseDMS(coordMatch[1]);
  const lng = parseDMS(coordMatch[2]);

  return { latitude: lat, longitude: lng };
}

function parseDMS(dms) {
  // DMS (Degrees Minutes Seconds) → Decimal
  const match = dms.match(/(\d{2})(\d{2})(\d{2})([NSEW])/);
  const deg = parseInt(match[1]);
  const min = parseInt(match[2]);
  const sec = parseInt(match[3]);
  const dir = match[4];

  let decimal = deg + min / 60 + sec / 3600;
  if (dir === 'S' || dir === 'W') decimal *= -1;

  return decimal;
}
```

---

### 2.3 UI/UX 기능

#### 토글 ON/OFF (활성/만료)

```typescript
function NotamList() {
  const [showActive, setShowActive] = useState(true);
  const [showExpired, setShowExpired] = useState(false);

  const filteredNotams = notams.filter(n => {
    if (showActive && n.status === 'ACTIVE') return true;
    if (showExpired && n.status === 'EXPIRED') return true;
    return false;
  });

  return (
    <>
      <Switch value={showActive} onValueChange={setShowActive} />
      <Switch value={showExpired} onValueChange={setShowExpired} />
      <FlatList data={filteredNotams} ... />
    </>
  );
}
```

#### 검색 기능

```typescript
function SearchBar() {
  const [query, setQuery] = useState('');

  const searchNotams = async () => {
    const response = await fetch(
      `${API_URL}/notams?search=${query}&data_source=international`
    );
    const data = await response.json();
    return data.data;
  };

  return (
    <TextInput
      placeholder="NOTAM ID 또는 공항 코드 검색"
      value={query}
      onChangeText={setQuery}
      onSubmitEditing={searchNotams}
    />
  );
}
```

---

## 📋 Phase 3: 결제 시스템 (1개월)

### 3.1 구독 관리

**Stripe 통합**:

```typescript
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

// 구독 생성
async function createSubscription(userId, priceId) {
  const customer = await stripe.customers.create({
    email: user.email,
    metadata: { userId }
  });

  const subscription = await stripe.subscriptions.create({
    customer: customer.id,
    items: [{ price: priceId }],  // price_pro, price_enterprise
    payment_behavior: 'default_incomplete',
    expand: ['latest_invoice.payment_intent'],
  });

  // DynamoDB 업데이트
  await updateUserSubscription(userId, {
    tier: 'pro',
    stripeCustomerId: customer.id,
    stripeSubscriptionId: subscription.id
  });

  return subscription;
}
```

**가격 정책**:
```
Free:
- 한국만
- 하루 100 요청
- 광고 있음
- $0/월

Pro:
- 전 세계
- 무제한 요청
- 광고 없음
- AI 번역 포함
- $9.99/월

Enterprise:
- API 직접 접근
- 우선 지원
- 커스텀 기능
- $99/월
```

---

## 📋 Phase 4: 배포 및 운영 (1개월)

### 4.1 앱 스토어 출시

**Google Play Store**:
- 개발자 등록: $25 (일회성)
- 심사 기간: 1-3일

**Apple App Store**:
- 개발자 등록: $99/년
- 심사 기간: 1-2주
- 더 엄격한 심사

**웹**:
- Vercel/AWS Amplify 호스팅
- 도메인: notam-monitor.com ($12/년)

---

### 4.2 비용 추정

**월간 운영 비용** (사용자 1,000명 기준):

| 항목 | 비용 |
|------|------|
| **데이터 소스** |
| ICAO NOTAM API | $500 |
| **AWS 서비스** |
| Lambda (100만 요청) | $0.20 |
| DynamoDB (1GB, 100만 요청) | $1.50 |
| API Gateway (100만 요청) | $3.50 |
| S3 (100GB 저장) | $2.30 |
| CloudFront (100GB 전송) | $8.50 |
| Cognito (1,000 사용자) | $5.50 |
| **AI 번역** |
| OpenAI GPT-4 (1,000 NOTAM) | $20 |
| **결제** |
| Stripe 수수료 (2.9% + $0.30) | ~$30 |
| **기타** |
| 도메인, 인증서 | $5 |
| **총계** | **~$576/월** |

**수익 모델** (사용자 1,000명):
- Free: 800명 × $0 = $0
- Pro: 180명 × $9.99 = $1,798
- Enterprise: 20명 × $99 = $1,980

**월 수익**: $3,778
**월 비용**: $576
**월 이익**: **$3,202**

---

## ⚠️ 법적/규제 이슈

### 1. NOTAM 데이터 저작권

**문제**:
- NOTAM 데이터는 각국 항공청 소유
- 상업적 사용 제한 가능
- 크롤링한 데이터 판매는 저작권 위반 가능성

**해결**:
- **ICAO 공식 API 사용** (라이센스 포함)
- 또는 각국 항공청과 계약
- 법률 자문 필수

### 2. 항공 안전 정보 책임

**문제**:
- 잘못된 NOTAM 정보로 사고 발생 시 법적 책임
- 실시간성 보장 어려움

**해결**:
- 면책 조항 명시
- "참고용 정보, 공식 NOTAM 확인 필수" 경고
- 보험 가입

### 3. 개인정보 보호 (GDPR, 개인정보보호법)

**필수**:
- 개인정보 처리방침
- 데이터 암호화
- 사용자 동의

---

## 🎯 최종 권장 사항

### ✅ 해야 할 것

1. **ICAO NOTAM API 구독** (월 $500)
   - 법적 안전
   - 전 세계 커버리지
   - 신뢰도 높음

2. **MVP 먼저 개발** (3개월)
   - React Native
   - 2D 지도만 (3D는 나중에)
   - 한국 NOTAM만 (초기)
   - Free 티어만

3. **베타 테스트** (1개월)
   - 파일럿, 항공 관련 커뮤니티
   - 피드백 수집

4. **정식 출시**
   - Pro/Enterprise 티어 추가
   - 전 세계 NOTAM
   - 3D 지도, AI 번역

### ❌ 하지 말아야 할 것

1. **크롤링 데이터로 상업 서비스** ← 법적 리스크
2. **보안 없이 API 공개** ← 비용 폭탄
3. **모든 기능 한번에 개발** ← 시간/비용 낭비

---

## 📞 다음 단계

**지금 결정해야 할 것**:

1. **데이터 소스**: ICAO API vs 크롤링
2. **MVP 범위**: 기능 최소화
3. **기술 스택**: React Native vs Flutter
4. **법률 자문**: 변호사 상담

**제가 도와드릴 것**:
1. ✅ MVP 백엔드 구축 (보안 강화)
2. ✅ React Native 앱 프로토타입
3. ✅ Stripe 결제 연동
4. ✅ 배포 가이드

**어떤 것부터 시작하시겠어요?**
