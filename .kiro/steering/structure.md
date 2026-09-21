---
inclusion: always
---
# 예정 코드 구조

```text
app/
  api/          # REST, SSE, demo operator session
  domain/       # order, return, refund, transactional policy
  tools/        # common gateway + MCP adapter
  agent/        # model interface, NAT integration, bounded ReAct, router
  traces/       # event schemas, export, redaction
  compiler/     # grouping, bindings, linear DSL validation
  workflows/    # interpreter, immutable registry, promotion
  evaluation/   # dataset splits, state oracle, report
web/src/        # operator console
configs/        # model/NAT/runtime configs, no credentials
tests/          # unit, contract, integration, evaluation
data/fixtures/  # synthetic reproducible cases
artifacts/      # sanitized evidence, reports
docs/           # strategy, design, research, pitch
.kiro/specs/skillforge-mvp/ # authoritative requirements/design/tasks
```

이 구조는 구현 목표다. 빈 패키지를 대량 생성하지 말고 담당 태스크에 필요한 모듈부터 만든다.
