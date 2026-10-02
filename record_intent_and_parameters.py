"""GECX (CX Agent Studio) — LLM 기반 인텐트 및 파라미터 자동 추출 Python Tool.

[적용 방법]
1. GECX 웹 콘솔 좌측 메뉴 > Tools > Create Tool > Python 선택
2. Tool 이름: record_intent_and_parameters
3. 아래 코드를 그대로 복사·붙여넣기 한 뒤 저장하고, Root agent (및 Sub-Agent)의 Tools 목록에 연결합니다.
"""

from typing import Any


def record_intent_and_parameters(
    top_intent: str,
    product_category: str = "",
    symptom_or_request: str = "",
    requested_action: str = "",
) -> dict[str, Any]:
  """고객의 대화 맥락에서 파악된 핵심 문의 유형(top_intent)과 상세 상담 정보를 세션 상태(context.state)에 기록합니다.

  Args:
      top_intent: 대화 맥락을 분석하여 분류한 핵심 문의 유형. 모든 고객 문의에 대해 예외 없이 반드시 다음 중 하나를 전달하십시오:
        - 'Transfer': 양도, 양수, 명의변경, 렌탈 승계, 계약자 변경 관련 모든 문의 (절차 및 구비서류 문의 포함)
        - 'Card Payment': 렌탈 요금, 카드/계좌 결제 수단 변경, 청구서(고지서) 조회 및 비교, 제휴 할인, 미납/연체/수납 관련 모든 문의
        - 'ASDefense': 제품 고장, 작동 불량(냉온수/얼음/소음/노즐/롤러 등), 수리/점검/A/S 접수, 필터 교체/자가조치, 오프라인 매장 위치 및 기타 모든 일반 제품/서비스 안내 문의
      product_category: 고객이 언급한 제품군 (예: '정수기', '공기청정기', '비데', '매트리스', '안마의자'). 특정 제품 언급이 없으면 빈 문자열('').
      symptom_or_request: 고객이 겪고 있는 구체적 증상이나 요청 사항 요약 (예: '냉수 출수 불량', '동생에게 렌탈 계약 양도 문의', '이번 달 청구서 확인 요청').
      requested_action: 고객이 희망하는 처리 방향 (예: '기사 방문 수리', '자가조치 안내', '이번 달 청구서 확인', '구비서류 안내', '결제 카드 변경').

  Returns:
      dict: 업데이트된 세션 변수 확인 결과 및 후속 조치 지침(agent_action).
  """
  if not top_intent:
    return {
        "status": "error",
        "agent_action": "top_intent 값을 반드시 포함하여 다시 호출하십시오.",
    }

  # 1) Text (STRING) 타입 세션 변수에 단일 문자열 저장
  context.state["top_intent"] = top_intent

  # 2) Custom Schema (OBJECT) 타입 세션 변수에 기존 동적 필드(API 조회 결과 등)를 유지(Merge)하면서
  #    4대 기본 필드 + context.state의 세션 컨텍스트 정보(customer_name, account_id, auth_status)를 동적 추가
  existing_inquiry = context.state.get("customer_inquiry")
  inquiry_data = dict(existing_inquiry) if isinstance(existing_inquiry, dict) else {}

  inquiry_data.update({
      "intent": top_intent,
      "product_category": product_category,
      "symptom_or_request": symptom_or_request,
      "requested_action": requested_action,
      # app.json에 사전 선언하지 않은 context.state 변수들도 Tool에서 동적으로 병합 가능
      "customer_name": context.state.get("customer_name", ""),
      "account_id": context.state.get("account_id", ""),
      "auth_status": context.state.get("auth_status", ""),
  })
  context.state["customer_inquiry"] = inquiry_data

  # 3) 호출 직후 같은 턴에서 에이전트가 멈추지 않고 후속 동작(호전환/조회/에스컬레이션)을 이어가도록 유도
  if top_intent == "Card Payment":
    agent_action = (
        "CRITICAL: 절대 안내 텍스트만 출력하고 턴을 종료하지 마십시오. "
        "1) 현재 에이전트가 Root agent인 경우: 반드시 이번 응답에서 transfer_to_agent(agent_name='billing_agent')를 함께 호출하여 즉시 billing_agent로 세션을 전환하십시오. "
        "2) 이미 billing_agent로 전환된 상태인 경우: "
        "결제 수단(카드/계좌) 변경 요청이면 먼저 set_session_state(_action_trigger='escalate', _escalation_topic='billing', _escalation_reason=symptom_or_request) 도구를 호출하고, "
        "요금/고지서/미납 조회 요청이면 get_invoice_breakdown, compare_invoices, list_invoices, lookup_customer 중 알맞은 도구를 즉시 호출하십시오."
    )
  else:
    agent_action = (
        "CRITICAL: 세션 변수 기록이 완료되었습니다. 고객에게 내부 기록 사실을 언급하지 마십시오. "
        "1) 현재 에이전트가 billing_agent인 경우: 요금 외 문의이므로 이번 응답에서 즉시 transfer_to_agent(agent_name='Root agent')를 호출하여 Root agent로 세션을 돌려보내십시오. "
        "2) 현재 에이전트가 Root agent인 경우: "
        "방문 A/S·점검 접수나 실제 명의변경 처리 또는 상담원 연결 요청이면 이번 응답에서 set_session_state(_action_trigger='escalate', _escalation_reason=symptom_or_request) 도구를 호출하고, "
        "단순 일반 정보 문의(매장 위치, 필터 교체 주기, 구비서류, 자가조치 등)는 직접 답변하십시오."
    )

  return {
      "status": "SUCCESS",
      "top_intent": top_intent,
      "customer_inquiry": inquiry_data,
      "agent_action": agent_action,
  }
