-- 한국 공항 초기 데이터
-- 작성일: 2025-11-10
-- 설명: 대한민국 18개 공항의 마스터 데이터

-- PostgreSQL과 SQLite 호환성을 위해 INSERT INTO 형식 사용
INSERT INTO airports (code, name_kr, name_en, icao_code, iata_code, country, is_domestic, is_active) VALUES
-- 국제 공항
('RKSI', '인천국제공항', 'Incheon International Airport', 'RKSI', 'ICN', '대한민국', 0, 1),
('RKSS', '서울/김포공항', 'Gimpo International Airport', 'RKSS', 'GMP', '대한민국', 1, 1),
('RKPK', '부산/김해공항', 'Busan/Gimhae International Airport', 'RKPK', 'PUS', '대한민국', 1, 1),
('RKPC', '광주공항', 'Gwangju Airport', 'RKPC', 'KWJ', '대한민국', 1, 1),
('RKPS', '대구공항', 'Daegu International Airport', 'RKPS', 'TAE', '대한민국', 1, 1),

-- 지역 공항
('RKPU', '울산공항', 'Ulsan Airport', 'RKPU', 'USN', '대한민국', 1, 1),
('RKSM', '무안공항', 'Muan International Airport', 'RKSM', 'MWX', '대한민국', 1, 1),
('RKTH', '대전공항', 'Daejeon International Airport', 'RKTH', 'CJJ', '대한민국', 1, 1),
('RKPD', '포항공항', 'Pohang Airport', 'RKPD', 'POU', '대한민국', 1, 1),

-- 충청권
('RKTL', '청주국제공항', 'Cheongju International Airport', 'RKTL', 'CJU', '대한민국', 1, 1),

-- 강원권
('RKNW', '강릉공항', 'Gangneung Airport', 'RKNW', 'KAG', '대한민국', 1, 1),

-- 전라권
('RKJK', '전주공항', 'Jeonju Airport', 'RKJK', 'JIU', '대한민국', 1, 1),
('RKJB', '전주/이석공항', 'Jeonju Isoik Airport', 'RKJB', 'JIU', '대한민국', 1, 0),

-- 제주권
('RKJY', '제주국제공항', 'Jeju International Airport', 'RKJY', 'CJU', '대한민국', 1, 1),
('RKJJ', '제주/동부공항', 'Jeju East Airport', 'RKJJ', 'CJU', '대한민국', 1, 1),

-- 경상권 추가
('RKTN', '통영공항', 'Tongyeong Airport', 'RKTN', 'TYO', '대한민국', 1, 1),

-- 경기권
('RKTU', '수원공항', 'Suwon Airport', 'RKTU', 'SWU', '대한민국', 1, 1),
('RKNY', '남이섬공항', 'Nami Island Airport', 'RKNY', 'NIA', '대한민국', 1, 0);

-- 초기 생성 후 데이터 확인 쿼리 (선택사항)
-- SELECT COUNT(*) as total_airports,
--        SUM(CASE WHEN is_domestic = 1 THEN 1 ELSE 0 END) as domestic_count,
--        SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_count
-- FROM airports;
