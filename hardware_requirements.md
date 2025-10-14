# 🔧 SCADA AI 시스템 하드웨어 요구사항

## 📋 개요

SCADA AI 시스템의 원활한 운영을 위한 하드웨어 요구사항 및 권장 장비 목록입니다.

## 🖥️ 서버 하드웨어

### 최소 사양 (소규모 시설)
- **CPU**: Intel Core i5-8400 또는 AMD Ryzen 5 3600 (6코어)
- **RAM**: 8GB DDR4
- **Storage**: 256GB SSD + 1TB HDD
- **Network**: Gigabit Ethernet
- **용도**: 센서 10개 이하, 동시 사용자 5명 이하

### 권장 사양 (중규모 시설)
- **CPU**: Intel Core i7-10700K 또는 AMD Ryzen 7 5700X (8코어)
- **RAM**: 32GB DDR4
- **Storage**: 512GB NVMe SSD + 2TB HDD
- **Network**: Gigabit Ethernet
- **용도**: 센서 50개 이하, 동시 사용자 20명 이하

### 고사양 (대규모 시설)
- **CPU**: Intel Xeon E-2288G 또는 AMD EPYC 7313P (16코어)
- **RAM**: 64GB DDR4 ECC
- **Storage**: 1TB NVMe SSD + 4TB HDD (RAID 1)
- **Network**: 10Gigabit Ethernet
- **용도**: 센서 100개 이상, 동시 사용자 50명 이상

## 🌐 네트워크 인프라

### 산업용 스위치
- **Cisco IE-3300-8T2S**: 산업용 이더넷 스위치
- **Phoenix Contact FL SWITCH**: DIN 레일 마운트
- **Moxa EDS-510A**: 관리형 이더넷 스위치

### 무선 접속 장치
- **Ubiquiti UniFi Access Points**: 기업급 무선 AP
- **TP-Link Omada EAP**: 관리형 무선 접속점
- **Aruba Instant On**: 클라우드 관리 AP

### 라우터/방화벽
- **pfSense**: 오픈소스 방화벽 (권장)
- **Fortinet FortiGate 40F**: 소규모 시설용
- **SonicWall TZ470**: 중소규모 시설용

## 🔌 센서 및 측정 장비

### 수질 측정 센서
- **pH 센서**:
  - Hach 5500-pH (디지털 출력)
  - Endress+Hauser CPS11 (아날로그 출력)
- **DO (용존산소) 센서**:
  - YSI ProODO (디지털)
  - Hach LDO (광학식)
- **탁도 센서**:
  - Hach SC200 컨트롤러 + Ultraturb Plus
  - Endress+Hauser CUS31
- **TDS 센서**:
  - Hach CDC401 전도도 센서
  - Endress+Hauser CLS21

### 압력/유량 센서
- **압력 센서**:
  - Endress+Hauser Cerabar PMC21
  - Rosemount 3051S
- **유량계**:
  - Endress+Hauser Proline Promag
  - ABB ProcessMaster FEP311

### 온도 센서
- **Pt100 RTD 센서**: Phoenix Contact
- **열전대**: Omega Engineering
- **디지털 온도 센서**: DS18B20 (소규모용)

## 🔌 데이터 수집 장비

### PLC (Programmable Logic Controller)
- **Siemens S7-1200**: 중소규모 시설 권장
- **Allen-Bradley CompactLogix**: 산업 표준
- **Schneider Electric Modicon M221**: 경제적 옵션

### HMI (Human Machine Interface)
- **Siemens Comfort Panel**: 산업용 터치 패널
- **Allen-Bradley PanelView**: 견고한 산업용 HMI
- **Weintek MT8000 시리즈**: 가성비 좋은 HMI

### RTU (Remote Terminal Unit)
- **Schneider Electric ION7650**: 전력 모니터링
- **ABB RTU560**: 변전소용 RTU
- **General Electric D25**: 다목적 RTU

### 데이터 로거
- **Campbell Scientific CR1000X**: 고급 데이터 로거
- **Onset HOBO**: 소규모 모니터링
- **Yokogawa STARDOM**: 산업용 컨트롤러

## 🔄 통신 모듈

### 유선 통신
- **Modbus RTU/TCP 컨버터**:
  - Moxa MGate MB3170
  - Advantech ADAM-4571
- **Ethernet/Serial 컨버터**:
  - Moxa NPort 5110
  - Digi PortServer TS

### 무선 통신
- **LoRaWAN 게이트웨이**:
  - MultiTech Conduit AP
  - Kerlink Wirnet Station
- **셀룰러 모뎀**:
  - Sierra Wireless AirLink
  - Digi IX20

### 산업용 프로토콜 지원
- **OPC UA 서버**: Matrikon OPC Server
- **Modbus 게이트웨이**: HMS Anybus
- **BACnet 게이트웨이**: Contemporary Controls

## ⚡ 전원 공급 장비

### UPS (무정전 전원 공급 장치)
- **소규모**: APC Smart-UPS SMT1500
- **중규모**: Eaton 9PX 3000VA
- **대규모**: Schneider Electric Galaxy VS

### 산업용 전원 공급기
- **Phoenix Contact QUINT**: DIN 레일 전원
- **Mean Well**: 스위칭 전원 공급기
- **TDK-Lambda**: 고신뢰성 전원

### 서지 보호기
- **Phoenix Contact VAL-MS**: 신호선 보호
- **Citel**: 전원선 서지 보호
- **DEHN**: 종합 서지 보호 솔루션

## 🏠 캐비닛 및 하우징

### 산업용 캐비닛
- **Rittal AE**: 모듈형 캐비닛 시스템
- **Hoffman**: NEMA 등급 인클로저
- **Schneider Electric Spacial**: 스테인리스 캐비닛

### DIN 레일 시스템
- **Phoenix Contact**: 35mm DIN 레일
- **Wago**: 연결 터미널 시스템
- **ABB**: 배선 덕트 시스템

### 환경 제어
- **냉각 팬**: EBM-Papst (산업용)
- **히터**: Stego (산업용 캐비닛 히터)
- **습도 제어**: Munters (제습기)

## 🔐 보안 하드웨어

### 물리적 보안
- **생체인식 시스템**:
  - Suprema BioEntry Plus
  - HID iClass SE
- **CCTV 시스템**:
  - Hikvision DS-2CD2XXX
  - Axis Communications
- **접근 제어**:
  - HID ProxCard
  - SALTO 전자 락

### 네트워크 보안
- **방화벽 어플라이언스**:
  - SonicWall NSA
  - Fortinet FortiGate
- **침입 탐지 시스템**:
  - Cisco Secure IPS
  - Snort (오픈소스)

## 📱 모바일 접속 장비

### 태블릿/패드
- **산업용 태블릿**:
  - Panasonic Toughbook
  - Getac T800
- **일반 태블릿**:
  - iPad Pro (견고한 케이스 필요)
  - Samsung Galaxy Tab Active

### 스마트폰
- **견고한 스마트폰**:
  - CAT S62 Pro
  - Samsung Galaxy XCover
- **일반 스마트폰**: 방수 케이스와 함께 사용

## 🛠️ 설치 및 유지보수 도구

### 측정 장비
- **멀티미터**: Fluke 87V
- **오실로스코프**: Tektronix TBS1000C
- **네트워크 테스터**: Fluke Networks LinkSprinter

### 설치 도구
- **케이블 압착기**: Klein Tools
- **드릴 및 비트**: Makita 산업용
- **케이블 관리**: Panduit 케이블 타이

### 안전 장비
- **절연 장갑**: Honeywell Class 0
- **안전경**: 3M SecureFit
- **안전화**: 정전기 방지 신발

## 💾 백업 및 저장소

### 로컬 백업
- **NAS (Network Attached Storage)**:
  - Synology DS920+
  - QNAP TS-453D
- **외장 하드드라이브**:
  - WD Elements Desktop
  - Seagate Backup Plus Hub

### 클라우드 백업
- **AWS S3**: 확장 가능한 클라우드 스토리지
- **Azure Blob Storage**: 기업용 클라우드
- **Google Cloud Storage**: 고성능 스토리지

## 📊 예산 가이드

### 소규모 시설 (센서 10개 이하)
| 항목 | 예상 비용 (KRW) |
|------|----------------|
| 서버 하드웨어 | 1,500,000 |
| 네트워크 장비 | 800,000 |
| 센서 및 측정 장비 | 5,000,000 |
| 데이터 수집 장비 | 2,000,000 |
| 전원 및 캐비닛 | 1,200,000 |
| 설치 및 기타 | 1,500,000 |
| **총 예산** | **12,000,000** |

### 중규모 시설 (센서 50개 이하)
| 항목 | 예상 비용 (KRW) |
|------|----------------|
| 서버 하드웨어 | 4,000,000 |
| 네트워크 장비 | 2,000,000 |
| 센서 및 측정 장비 | 15,000,000 |
| 데이터 수집 장비 | 5,000,000 |
| 전원 및 캐비닛 | 3,000,000 |
| 설치 및 기타 | 6,000,000 |
| **총 예산** | **35,000,000** |

### 대규모 시설 (센서 100개 이상)
| 항목 | 예상 비용 (KRW) |
|------|----------------|
| 서버 하드웨어 | 10,000,000 |
| 네트워크 장비 | 5,000,000 |
| 센서 및 측정 장비 | 50,000,000 |
| 데이터 수집 장비 | 15,000,000 |
| 전원 및 캐비닛 | 8,000,000 |
| 설치 및 기타 | 20,000,000 |
| **총 예산** | **108,000,000** |

## 🔧 유지보수 계획

### 정기 점검 항목
- **월간**: 센서 캘리브레이션, 시스템 로그 검토
- **분기**: 하드웨어 청소, 백업 테스트
- **연간**: 전면적 시스템 점검, 장비 교체

### 예비 부품 권장사항
- **센서**: 주요 센서 10% 예비분
- **통신 모듈**: 각 타입별 1-2개
- **전원 공급기**: 핵심 구간용 예비분
- **케이블**: 각 타입별 10% 예비분

## 📞 공급업체 연락처

### 주요 장비 공급업체
- **Siemens Korea**: 02-2183-1000
- **ABB Korea**: 02-528-2000
- **Schneider Electric Korea**: 02-3420-8000
- **Endress+Hauser Korea**: 031-716-3300

### 시스템 통합업체
- **두산디지털이노베이션**: 02-3398-3114
- **엘에스일렉트릭**: 02-2034-4114
- **효성중공업**: 02-799-1114

---

*이 하드웨어 목록은 SCADA AI 시스템의 최적 성능을 위한 권장사항입니다. 실제 시설의 요구사항에 따라 조정이 필요할 수 있습니다.*