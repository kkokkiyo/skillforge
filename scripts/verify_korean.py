"""Ten predeclared Korean routing probes. Does not mutate commerce state."""

import json, secrets
from backend.config import ROOT, load_env
from backend.router import route_text

load_env()
cases = [
    ("order-001 반품한 상품 환불해주세요", "refund", "order-001"),
    ("order-002 결제 취소하고 환불받고 싶어요", "refund", "order-002"),
    ("order-001 환불 진행 부탁드립니다", "refund", "order-001"),
    ("order-001 반품 수거가 끝났으니 환불해 주세요", "refund", "order-001"),
    ("order-002 환불 요청합니다", "refund", "order-002"),
    ("order-001 현재 주문 상태를 조회해줘", "status", "order-001"),
    ("order-002 배송지 주소를 바꾸고 싶어요", "unsupported", "order-002"),
    ("주문번호는 모르겠고 환불해주세요", "clarify", None),
    ("order-001인지 order-002인지 모르겠는데 환불해줘", "clarify", None),
    (
        "order-001 반품 환불을 하고 싶습니다. 다른 주문은 처리하지 마세요.",
        "refund",
        "order-001",
    ),
]
rows = []
for text, intent, oid in cases:
    try:
        r = route_text(text, "live")
        rows.append(
            {
                "text": text,
                "expected_intent": intent,
                "expected_order": oid,
                "result": r,
                "passed": r["intent"] == intent and r["order_id"] == oid,
            }
        )
    except Exception as e:
        rows.append(
            {
                "text": text,
                "expected_intent": intent,
                "expected_order": oid,
                "error": getattr(e, "code", type(e).__name__),
                "passed": False,
            }
        )
folder = ROOT / "artifacts"
folder.mkdir(exist_ok=True)
report = {
    "mode": "live",
    "cases": rows,
    "passed": sum(r["passed"] for r in rows),
    "n": len(rows),
    "note": "Ambiguous/no-ID cases short-circuit before inference; counts are explicit.",
}
previous = folder / "korean-intent-evidence.json"
if previous.exists():
    (folder / ("korean-intent-previous-" + secrets.token_hex(4) + ".json")).write_bytes(
        previous.read_bytes()
    )
(folder / "korean-intent-evidence.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps({"passed": report["passed"], "n": report["n"]}), flush=True)
