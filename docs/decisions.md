# 결정 등록부 (Decision Registry)

> 문서 유형: `N/A — wf-design 결정 등록부(§6.2)이며 문서 유형 매핑 대상이 아님`
> 작업 ID: `20260922-mathdesk-baseline`
> 상태: `in-progress`
> 기준선: `N/A — 등록부는 기준선을 발행하지 않음`
> 작성일: `2026-09-22`
> 최종 갱신: `2026-10-11`
> 관련 문서: [REQ-mathdesk: 요구사항](./requirements.md), [DESIGN-mathdesk: 설계](./design.md)

## 요약

- 목적: 저장소 전역의 ADR·DCR을 한곳에서 조망하고 다음 일련번호를 발행할 기준을 제공한다.
- 현재 결론 또는 상태: ADR 13건과 DCR 23건이 모두 `approved`다. 유효 기준선은 `v24`이며 마지막 발행 번호는 ADR-013, DCR-023.
- 다음 행동: 없음. 새 ADR·DCR이 생기면 이 등록부를 같은 변경에서 갱신한다.

## 문서 연결

| 방향 | 관계 | 대상 문서 | 대상 항목 | 비고 |
|---|---|---|---|---|
| input | baseline | [REQ-mathdesk: 요구사항](./requirements.md) | document | 결정이 적용되는 요구사항 기준선 |
| input | baseline | [DESIGN-mathdesk: 설계](./design.md) | DES-01~DES-22 | 결정이 적용되는 설계 |

## 등록부

| ID | 유형 | 제목 | 상태 | 날짜 | 위치 | 대체·관련 |
|---|---|---|---|---|---|---|
| ADR-001 | adr | 기술 스택과 실행 형태 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/ADR-001](./work/20260922-mathdesk-baseline/ADR-001-기술-스택과-실행-형태.md) | — |
| ADR-002 | adr | PostgreSQL 단일 저장소 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/ADR-002](./work/20260922-mathdesk-baseline/ADR-002-PostgreSQL-단일-저장소.md) | ADR-001 전제 |
| ADR-003 | adr | AI 작업 분리와 개인정보 경계 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/ADR-003](./work/20260922-mathdesk-baseline/ADR-003-AI-작업-분리와-개인정보-경계.md) | ADR-006 관련 |
| ADR-004 | adr | 문서 입력 정규화 파이프라인 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/ADR-004](./work/20260922-mathdesk-baseline/ADR-004-문서-입력-정규화-파이프라인.md) | — |
| ADR-005 | adr | 메시징 어댑터 단일화 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/ADR-005](./work/20260922-mathdesk-baseline/ADR-005-메시징-어댑터-단일화.md) | — |
| ADR-006 | adr | OMR 양식 고정과 템플릿 판독 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/ADR-006](./work/20260922-mathdesk-baseline/ADR-006-OMR-양식-고정과-템플릿-판독.md) | ADR-003 관련 |
| ADR-007 | adr | 인증·권한 모델 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/ADR-007](./work/20260922-mathdesk-baseline/ADR-007-인증-권한-모델.md) | — |
| ADR-008 | adr | 테스트 운영 노출 구성 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/ADR-008](./work/20260922-mathdesk-baseline/ADR-008-테스트-운영-노출-구성.md) | ADR-001 보완, DCR-001 |
| ADR-009 | adr | LLM 공급자 추상화와 Claude 연결 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/ADR-009](./work/20260922-mathdesk-baseline/ADR-009-LLM-공급자-추상화와-Claude-연결.md) | ADR-003 결정 2 부분 대체, DCR-002 |
| ADR-010 | adr | 웹 UI 디자인 시스템 | approved | 2026-09-23 | [work/20260922-mathdesk-baseline/ADR-010](./work/20260922-mathdesk-baseline/ADR-010-웹-UI-디자인-시스템.md) | ADR-011 관련, DCR-003 |
| ADR-011 | adr | 리포트 카드 HTML 렌더링 | approved | 2026-09-23 | [work/20260922-mathdesk-baseline/ADR-011](./work/20260922-mathdesk-baseline/ADR-011-리포트-카드-HTML-렌더링.md) | ADR-010 관련, DCR-003 |
| ADR-012 | adr | 테마 팔레트와 적용 방식 | approved | 2026-09-23 | [work/20260922-mathdesk-baseline/ADR-012](./work/20260922-mathdesk-baseline/ADR-012-테마-팔레트와-적용-방식.md) | ADR-010·ADR-011 관련, DCR-004 |
| ADR-013 | adr | 운영 배포처 — 클라이언트별 AWS Lightsail 단일 서버 | approved | 2026-10-11 | [work/20260922-mathdesk-baseline/ADR-013](./work/20260922-mathdesk-baseline/ADR-013-운영-배포처-클라이언트별-Lightsail-단일-서버.md) | ADR-001 Phase B 구체화, ADR-008 적용, DCR-022 |
| ADR-014 | adr | 포털 권한 모델 | approved | 2026-10-11 | [work/20260922-mathdesk-baseline/ADR-014](./work/20260922-mathdesk-baseline/ADR-014-포털-권한-모델.md) | ADR-007 보완, DCR-024 |
| DCR-001 | dcr | 테스트 운영 환경 노출 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/DCR-001](./work/20260922-mathdesk-baseline/DCR-001-테스트-운영-환경-노출.md) | ADR-008 |
| DCR-002 | dcr | M6 LLM 공급자 중립화와 Claude 연결 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/DCR-002](./work/20260922-mathdesk-baseline/DCR-002-M6-LLM-공급자-중립화와-Claude-연결.md) | ADR-009 |
| DCR-003 | dcr | 브랜드 자산으로서의 시각 설계 | approved | 2026-09-23 | [work/20260922-mathdesk-baseline/DCR-003](./work/20260922-mathdesk-baseline/DCR-003-브랜드-자산으로서의-시각-설계.md) | ADR-010, ADR-011 |
| DCR-004 | dcr | 웹 테마 선택과 브랜드 색의 역할 분리 | approved | 2026-09-23 | [work/20260922-mathdesk-baseline/DCR-004](./work/20260922-mathdesk-baseline/DCR-004-웹-테마-선택.md) | ADR-012 |
| DCR-005 | dcr | 화면별 차등 모바일 지원 | approved | 2026-09-23 | [work/20260922-mathdesk-baseline/DCR-005](./work/20260922-mathdesk-baseline/DCR-005-모바일-지원-범위.md) | ADR-010 관련 |
| DCR-006 | dcr | 퇴원·비활성 학생과 반의 삭제 | approved | 2026-09-24 | [work/20260922-mathdesk-baseline/DCR-006](./work/20260922-mathdesk-baseline/DCR-006-퇴원-비활성-학생과-반의-삭제.md) | — |
| DCR-007 | dcr | 시작 시각만 쓰는 반 시간표 | approved | 2026-09-24 | [work/20260922-mathdesk-baseline/DCR-007](./work/20260922-mathdesk-baseline/DCR-007-시작-시각만-쓰는-반-시간표.md) | — |
| DCR-008 | dcr | 주간 시간표 | approved | 2026-09-24 | [work/20260922-mathdesk-baseline/DCR-008](./work/20260922-mathdesk-baseline/DCR-008-주간-시간표.md) | DCR-007 관련 |
| DCR-009 | dcr | 비밀번호 변경과 재설정 | approved | 2026-09-24 | [work/20260922-mathdesk-baseline/DCR-009](./work/20260922-mathdesk-baseline/DCR-009-비밀번호-변경과-재설정.md) | ADR-007 관련 |
| DCR-010 | dcr | 수업 길이 기본값 4시간 | approved | 2026-09-24 | [work/20260922-mathdesk-baseline/DCR-010](./work/20260922-mathdesk-baseline/DCR-010-수업-길이-4시간.md) | DCR-008 기본값 대체 |
| DCR-011 | dcr | 강사의 담당 반 수정 | approved | 2026-09-24 | [work/20260922-mathdesk-baseline/DCR-011](./work/20260922-mathdesk-baseline/DCR-011-강사의-담당-반-수정.md) | ADR-007 관련 |
| DCR-012 | dcr | 재원 학생의 바로 삭제 | approved | 2026-10-11 | [work/20260922-mathdesk-baseline/DCR-012](./work/20260922-mathdesk-baseline/DCR-012-재원-학생의-바로-삭제.md) | DCR-006 학생 선행 조건 변경 |
| DCR-013 | dcr | 학생 즉시 삭제 | approved | 2026-10-11 | [work/20260922-mathdesk-baseline/DCR-013](./work/20260922-mathdesk-baseline/DCR-013-학생-즉시-삭제.md) | DCR-006·DCR-012 학생 확인 절차 변경 |
| DCR-014 | dcr | 학부모 연락처와 성적 칸 | approved | 2026-10-11 | [work/20260922-mathdesk-baseline/DCR-014](./work/20260922-mathdesk-baseline/DCR-014-학부모-연락처와-성적-칸.md) | FR-05·FR-06 보강 |
| DCR-015 | dcr | 학교 관리와 학교 드롭다운 | approved | 2026-10-11 | [work/20260922-mathdesk-baseline/DCR-015](./work/20260922-mathdesk-baseline/DCR-015-학교-관리와-학교-드롭다운.md) | FR-05 보강, FR-43 신설 |
| DCR-016 | dcr | 반 바로 삭제 | approved | 2026-10-11 | [work/20260922-mathdesk-baseline/DCR-016](./work/20260922-mathdesk-baseline/DCR-016-반-바로-삭제.md) | DCR-006 반 선행 조건·확인 절차 변경 |
| DCR-017 | dcr | 학생별 코멘트와 문자 공통·개별 구조 | approved | 2026-10-11 | [work/20260922-mathdesk-baseline/DCR-017](./work/20260922-mathdesk-baseline/DCR-017-학생별-코멘트와-문자-공통-개별-구조.md) | FR-14·FR-18 상세·AC-14 변경, FR-44·AC-43 신설 |
| DCR-018 | dcr | 성적 통계 회차별 추이 | approved | 2026-10-11 | [work/20260922-mathdesk-baseline/DCR-018](./work/20260922-mathdesk-baseline/DCR-018-성적-통계-회차별-추이.md) | FR-24·FR-25·AC-19 개정 |
| DCR-019 | dcr | 테스트명 입력과 문자·리포트 공통 구획 | approved | 2026-10-11 | [work/20260922-mathdesk-baseline/DCR-019](./work/20260922-mathdesk-baseline/DCR-019-테스트명-입력과-문자-리포트-공통-구획.md) | FR-13 상세·AC-44 신설, FR-18 상세·AC-14 변경 |
| DCR-020 | dcr | 일일 입력의 학생별 정보 탭과 수업일 달력 | approved | 2026-10-11 | [work/20260922-mathdesk-baseline/DCR-020](./work/20260922-mathdesk-baseline/DCR-020-일일-입력-학생별-정보-탭과-수업일-달력.md) | FR-45·FR-46·AC-45·AC-46 신설, DES-05 상세·REST·DES-24 추가 |
| DCR-021 | dcr | 학생별 정보 이미지 저장 | approved | 2026-10-11 | [work/20260922-mathdesk-baseline/DCR-021](./work/20260922-mathdesk-baseline/DCR-021-학생별-정보-이미지-저장.md) | FR-45 상세 보강·AC-47 신설, DES-08 상세·REST 추가, DCR-020 관련 |
| DCR-022 | dcr | 운영 배포처 — 클라이언트별 AWS Lightsail 서버 | approved | 2026-10-11 | [work/20260922-mathdesk-baseline/DCR-022](./work/20260922-mathdesk-baseline/DCR-022-운영-배포처-클라이언트별-Lightsail.md) | ADR-013, 범위·NFR-08·11·17 변경, NFR-20·AC-48·DES-25 신설 |
| DCR-023 | dcr | 반 단위 일괄 발송 | approved | 2026-10-11 | [work/20260922-mathdesk-baseline/DCR-023](./work/20260922-mathdesk-baseline/DCR-023-반-단위-일괄-발송.md) | FR-47·AC-49 신설, REST 2건, DES-18 작업 종류 |
| DCR-024 | dcr | 학생·학부모 포털 | approved | 2026-10-11 | [work/20260922-mathdesk-baseline/DCR-024](./work/20260922-mathdesk-baseline/DCR-024-학생-학부모-포털.md) | ADR-014, FR-48·FR-49·AC-50~52 신설, FR-02·03·05·39·NFR-07 수정, DES-03·04·26, 기준선 v25 |
| DCR-025 | dcr | 포털 기록 달력과 추이 그래프 | awaiting-approval | 2026-10-11 | [work/20260922-mathdesk-baseline/DCR-025](./work/20260922-mathdesk-baseline/DCR-025-포털-기록-달력과-추이-그래프.md) | DCR-024 보강, FR-49 상세 ②·③, AC-51 ⑧, 포털 REST 1건 |

## 번호 발행 규칙

- ADR·DCR 번호는 저장소 전역 일련번호다. 새 번호는 이 등록부의 마지막 번호 다음 번호로 발행한다.
- 다음 ADR 번호: `ADR-015`. 다음 DCR 번호: `DCR-026`.
- 개별 ADR·DCR 파일이 정본이며 이 등록부는 목록이다. 불일치하면 파일에 맞춰 등록부를 수정한다.

## 아웃라인 결정 항목과의 대응

[SPEC-mathdesk-outline §7](./SPEC-mathdesk-outline.md)의 결정 항목 D1~D11이 ADR로 승격된 대응은 다음과 같다.

| 아웃라인 항목 | 처리 |
|---|---|
| D1 프론트엔드 스택, D2 백엔드 스택, D4 로컬 배포 형태 | [ADR-001](./work/20260922-mathdesk-baseline/ADR-001-기술-스택과-실행-형태.md) |
| D3 DB | [ADR-002](./work/20260922-mathdesk-baseline/ADR-002-PostgreSQL-단일-저장소.md) |
| D5 AI 모델 구성, D10 추론 하드웨어 전략 | [ADR-003](./work/20260922-mathdesk-baseline/ADR-003-AI-작업-분리와-개인정보-경계.md) · [ADR-009](./work/20260922-mathdesk-baseline/ADR-009-LLM-공급자-추상화와-Claude-연결.md)(공급자 결정) |
| D6 시험지 입력 포맷 | [ADR-004](./work/20260922-mathdesk-baseline/ADR-004-문서-입력-정규화-파이프라인.md) |
| D8 메시지 채널 | [ADR-005](./work/20260922-mathdesk-baseline/ADR-005-메시징-어댑터-단일화.md) |
| D11 OMR 답안지 양식 | [ADR-006](./work/20260922-mathdesk-baseline/ADR-006-OMR-양식-고정과-템플릿-판독.md) |
| D7 MVP 범위 | 요구사항 [범위](./requirements.md#범위)로 흡수. 사용자 결정으로 기준선 범위를 M0~M9 전체로 확대 |
| D9 워크플로우 단계 정의 | wf-implement 스킬 계획 수립 소유 항목이므로 ADR로 승격하지 않는다 |
| (신규) 인증·권한 모델 | [ADR-007](./work/20260922-mathdesk-baseline/ADR-007-인증-권한-모델.md) |
| (신규) 시각 설계·브랜드 | [ADR-010](./work/20260922-mathdesk-baseline/ADR-010-웹-UI-디자인-시스템.md) · [ADR-011](./work/20260922-mathdesk-baseline/ADR-011-리포트-카드-HTML-렌더링.md) · [DCR-003](./work/20260922-mathdesk-baseline/DCR-003-브랜드-자산으로서의-시각-설계.md) |
| (신규) 웹 테마 | [ADR-012](./work/20260922-mathdesk-baseline/ADR-012-테마-팔레트와-적용-방식.md) · [DCR-004](./work/20260922-mathdesk-baseline/DCR-004-웹-테마-선택.md) |
| (신규) 모바일 지원 범위 | [DCR-005](./work/20260922-mathdesk-baseline/DCR-005-모바일-지원-범위.md) (ADR 없음 — 지원 범위 조정이며 ADR-010의 구현 수단을 그대로 쓴다) |
| (신규) 테스트 운영 노출 | [ADR-008](./work/20260922-mathdesk-baseline/ADR-008-테스트-운영-노출-구성.md) · [DCR-001](./work/20260922-mathdesk-baseline/DCR-001-테스트-운영-환경-노출.md) |
