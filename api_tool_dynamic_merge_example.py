"""GECX (CX Agent Studio) — 기존 API 조회 Tool에서 응답 데이터를 customer_inquiry에 동적 병합하는 예제.

[적용 방법]
고객이 이미 보유하고 있는 CXAS 애플리케이션의 API 조회 Tool(예: 청구서 조회, 요금 비교, 고객 정보 조회 등)
파이썬 코드 내에 아래 `_sync_inquiry_with_api_data()` 헬퍼 함수를 추가하고,
API 응답(return 직전)에서 원하는 필드들을 넘겨 호출하면 `app.json` 스키마 수정 없이
`customer_inquiry` 세션 변수에 실시간으로 병합(Merge)됩니다.
"""

from typing import Any


# =====================================================================
# 1. 범용 동적 병합 헬퍼 함수 (기존 API Tool 코드 하단에 복사하여 사용)
# =====================================================================
def _sync_inquiry_with_api_data(**api_fields: Any) -> None:
  """API를 통해 조회된 결과값들과 context.state 정보를 customer_inquiry에 동적 병합합니다.

  기존 customer_inquiry에 저장된 4개 기본 필드(intent, product_category,
  symptom_or_request, requested_action)를 덮어쓰지 않고 보존(Merge)하면서,
  전달받은 API 응답 필드(예: invoice_total, billing_month 등)를 추가·갱신합니다.
  """
  existing = context.state.get("customer_inquiry")
  inquiry = dict(existing) if isinstance(existing, dict) else {}

  # 기본 4대 필드가 비어 있을 경우 안전하게 기본값 보장
  if not inquiry.get("intent"):
    inquiry["intent"] = context.state.get("top_intent") or "Card Payment"
  inquiry.setdefault("product_category", "")
  inquiry.setdefault("symptom_or_request", "")
  inquiry.setdefault("requested_action", "")

  # context.state의 기본 고객 세션 정보도 함께 동기화
  inquiry.update({
      "customer_name": context.state.get("customer_name", ""),
      "account_id": context.state.get("account_id", ""),
      "auth_status": context.state.get("auth_status", ""),
  })

  # API 응답에서 추출한 동적 필드(청구 금액, 청구월, 납부기한 등) 병합
  inquiry.update(api_fields)
  context.state["customer_inquiry"] = inquiry


# =====================================================================
# 2. 적용 예시 ①: 청구서 상세 조회 Tool (get_invoice_breakdown) 내 적용
# =====================================================================
def get_invoice_breakdown_example(month: str = "latest", line: str = "") -> dict[str, Any]:
  """기존 청구서 조회 API Tool 내부에서 API 응답값을 customer_inquiry에 반영하는 예시입니다."""
  # (가정) 백엔드/OpenAPI 호출 결과
  # detail = _get_bills(account_id, bill_id=target["id"])[0]
  billing_month = "2026년 3월"
  payment_due = "2026년 4월 14일"

  if line:
    # 개별 제품(예: 일련번호 끝자리 '703') 조회 시
    product_total = 0
    _sync_inquiry_with_api_data(
        billing_month=billing_month,
        invoice_total=f"{int(product_total):,}원",
        payment_due=payment_due,
        queried_product=f"일련번호 끝자리 {line}",
    )
    return {
        "status": "success",
        "scope": "product",
        "product": f"…{line}",
        "month": billing_month,
        "total": product_total,
        "payment_due": payment_due,
    }

  # 전체 계정 청구서 조회 시
  account_total = 5370
  product_endings = ["048", "703", "843"]
  _sync_inquiry_with_api_data(
      billing_month=billing_month,
      invoice_total=f"{int(account_total):,}원",
      payment_due=payment_due,
      queried_product=f"전체 계정 ({', '.join(product_endings)})",
  )
  return {
      "status": "success",
      "scope": "account",
      "month": billing_month,
      "total": account_total,
      "payment_due": payment_due,
      "product_endings": product_endings,
  }


# =====================================================================
# 3. 적용 예시 ②: 전월 대비 요금 비교 Tool (compare_invoices) 내 적용
# =====================================================================
def compare_invoices_example(month: str = "latest", compare_to: str = "previous") -> dict[str, Any]:
  """전월 대비 청구 요금 비교 API Tool 내부에서 차액 정보를 동적 반영하는 예시입니다."""
  current_total = 5370
  previous_total = -1790
  diff_amount = 7160
  direction = "higher"

  _sync_inquiry_with_api_data(
      billing_month="2026년 3월",
      invoice_total=f"{current_total:,}원",
      previous_invoice_total=f"{previous_total:,}원",
      invoice_diff=f"{diff_amount:,}원 ({direction})",
  )
  return {
      "status": "success",
      "current": {"month": "2026년 3월", "total": current_total},
      "previous": {"month": "2026년 2월", "total": previous_total},
      "difference": {"amount": diff_amount, "direction": direction},
  }
