// 한국 공항 ICAO 코드 → 한글명 매핑
export const AIRPORT_NAMES = {
  'RKSI': '인천국제공항',
  'RKSS': '김포국제공항',
  'RKPC': '제주국제공항',
  'RKPK': '김해국제공항',
  'RKTU': '청주국제공항',
  'RKTN': '대구국제공항',
  'RKJJ': '광주공항',
  'RKJY': '양양국제공항',
  'RKJB': '무안국제공항',
  'RKNY': '여수공항',
  'RKPU': '울산공항',
  'RKSM': '서울공항',
  'RKTH': '포항공항',
  'RKPS': '사천공항',
  'RKPD': '군산공항',
  'RKJU': '원주공항',
  'RKNW': '원주공항',
  'RKJK': '군산공항',
}

export const getAirportName = (icao) => {
  return AIRPORT_NAMES[icao] || icao
}

export const getFullAirportName = (icao) => {
  const koreanName = AIRPORT_NAMES[icao]
  return koreanName ? `${icao} ${koreanName}` : icao
}
