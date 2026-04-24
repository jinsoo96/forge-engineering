# Harness Engineering Research

> 2026-04-24 · 리서치 에이전트 조사 결과
>
> Forge Engineering의 출발점인 Harness Engineering 분야의 최신 사례·패턴·한계 정리.

---

## 1. 정의와 기원

### 핵심 정의

**Harness Engineering** = "AI 에이전트를 둘러싼 스캐폴딩 — context delivery, tool interfaces, planning artifacts, verification loops, memory systems, sandboxes — 를 설계하는 분야이며, 에이전트가 실제 태스크에서 성공/실패하는지를 결정한다" (awesome-harness-engineering 레포).

핵심 공식: **Agent = Model + Harness**.

### 용어 기원 (실제 타임라인)

| 시점 | 사건 | 주체 |
|------|------|------|
| 2022–2024 | **Prompt Engineering** — 단일 메시지 설계 | 커뮤니티 |
| 2025 중반 | **Context Engineering** — Tobi Lütke(Shopify), Karpathy가 트윗으로 주창 | Karpathy, Lütke |
| **2026-02** | Mitchell Hashimoto(HashiCorp)가 블로그에서 **"harness engineering"** 최초 명명 | Mitchell Hashimoto |
| **2026-02-11** | OpenAI Ryan Lopopolo "Harness engineering: leveraging Codex in an agent-first world". Symphony 팀 5개월/1M LOC/0% human-written code 케이스 공개 | OpenAI |
| 2026-02~04 | Martin Fowler, Anthropic, Red Hat, Microsoft, Google 연달아 공식 글 | 전 산업 |
| 2026-04 | Anthropic "Effective harnesses for long-running agents" — Planner/Generator/Evaluator 3-에이전트 | Anthropic |

> ⚠️ **정정:** "Thinking Machines가 Harness Engineering을 만들었다"는 기록은 확인되지 않음. 실제 원류는 **Hashimoto → OpenAI**.

### 계보도

```
Prompt Engineering (2022-24) — 단일 메시지
Context Engineering (2025, Karpathy) — RAG/few-shot/tools/state/compaction
Harness Engineering (2026, Hashimoto/OpenAI) — loop + tools + perms + verify + memory + sandbox
                                    ↓
Forge Engineering (2026-04, 본 프로젝트) — 하네스의 자가 진화
```

포함 관계: `Prompt ⊂ Context ⊂ Harness`.

---

## 2. awesome-harness-engineering 레포 정리

- 유지자: ai-boost (GitHub org), CC0
- 통계: ~408 stars / 30 forks / 60 commits (2026 초)
- 핵심 파일: `README.md`, `AGENTS.md`, `CLAUDE.md`(AGENTS.md 심볼릭 링크), `templates/AGENTS.md`

### templates/AGENTS.md 7개 섹션 구조

1. **Project overview**
2. **Repository structure** — `src/`, `tests/`, `docs/`, `scripts/` 맵
3. **Conventions** — Code style / Naming / Testing / Commits
4. **Tool permissions** — 3단계 레이어:
   - Allowed
   - Restricted (ask before proceeding)
   - Not allowed
5. **Known constraints**
6. **Verification gates** — tests pass / linter pass / scope check
7. **Contact / escalation** — "cannot proceed" 시 stop + describe

### CLAUDE.md = AGENTS.md (심볼릭)

Agentic AI Foundation(Linux Foundation 산하)이 AGENTS.md 스펙 관리, 60,000+ OSS 채택. Claude Code·Cursor·Continue.dev·Cline·RooCode·Kilo 지원.

---

## 3. 주요 구현 사례 비교

| 도구 | Harness 구성 | 특징 | 한계 |
|------|--------------|------|------|
| **Claude Code** | CLAUDE.md/AGENTS.md + 24 툴 + Plan/Explore 서브에이전트 + Skills + Hooks + MCP + Compaction | 시스템 프롬프트 ~50 instruction, 서브에이전트 독립 context, CLAUDE.md 매 턴 re-read | 프롬프트 비대, compaction 품질 의존, context anxiety (Sonnet 4.5) |
| **Cursor** | `.cursor/rules/` (MDC 5-level) + glob-triggered + Agents Mode | 룰 자동 주입, 2026 dynamic context discovery로 46.9% 토큰 절감 | 500줄 넘으면 효과 급감 |
| **Codex CLI** (OpenAI) | AGENTS.md + 내부 Harness 런타임 + Symphony | 5개월/1M LOC 프로덕션 앱 0% human 코드 | 내부 툴 비공개 |
| **Aider** | Repo map (tree-sitter + PageRank) + Architect/Editor 2-model + micro-diff + 자동 git | 토큰 효율적, 대규모 레포 PageRank relevance | 장시간 태스크 약함, persistent memory 없음 |
| **Cline** | Memory Bank (projectbrief/productContext/activeContext/systemPatterns MD) + Mermaid | 세션 간 리셋을 Memory Bank로 극복 | 수동 업데이트 부담 |
| **Devin** (Cognition) | Devin Wiki 자동 인덱싱 + Interactive Planning + self-reviewing PR | Full-autonomy 지향 | context anxiety, 비용·브리틀함 |
| **Continue.dev** | config.yaml + Rules + AGENTS.md (Issue #6716) | 오픈소스, 멀티모델 | 복잡 시 일관성 저하 |

**공통 관찰:** 상위 코딩 에이전트들은 기반 모델보다 **서로 더 닮아 보인다** — 4기둥(system prompt / tools / context / subagents)으로 수렴.

---

## 4. 핵심 패턴 (공통 원칙)

### 반복되는 10가지 디자인 패턴

1. **Rules-as-Code** — AGENTS.md/CLAUDE.md/.cursorrules
2. **Hierarchical Context Assembly** — system → tools → memory → history → msg
3. **3단계 권한 게이팅** — Allowed / Restricted(ask) / Not allowed
4. **Verification Gates** — 테스트·린트·스코프
5. **3-agent Separation** — Planner + Generator + Evaluator (self-eval weakness 대응)
6. **Context Compaction & Reset** — Sonnet 4.5는 compaction만으론 부족 → reset 필수
7. **Memory Bank / Scratchpad**
8. **Tool Lazy-loading** — name만 주고 on-demand fetch
9. **Hook/Middleware Layer** — deterministic 개입 지점
10. **Sandbox + Permission Broker** — HITL

### 공통 철학

- **"모델이 못하는 것을 둘러싸 보완"** — 모델이 나아지면 불필요해진다는 전제.
- **Feedforward + Feedback 이중 통제** — steering + self-correction.
- **Bounded > unbounded autonomy** — 프로덕션 합의.

---

## 5. Harness Engineering의 7대 구조적 한계 ★

### 한계 1: Markdown Brittleness / 문서 부패(rot)
- "A single markdown file of rules is a brittle solution that will rapidly decay" — stale rule 공동묘지.
- Feature velocity vs impact weekly audit 필수.
- **Forge의 여지:** 선언적 MD가 아닌 **실행 가능·자가 검증 아티팩트**(테스트처럼 실패 시 빨갛게 뜨는).

### 한계 2: "65% 실패는 Harness 결함"
- Adnan Masood (2026-04): 엔터프라이즈 AI 실패의 65%는 **모델이 아니라 harness-level data defects** (Context Drift / Schema Misalignment / State Degradation).
- Harness가 문제를 해결하기보다 **새 실패 표면** 생성.
- **Forge의 여지:** harness의 정합성을 보증하는 상위 레이어 = **harness의 harness**.

### 한계 3: Orientation Tax
- 에이전트가 hostile·unmapped 시스템을 탐색하며 수천 토큰 낭비. 모델 capability로 보상 불가.
- 현재 harness는 *지시*는 하지만 *환경 재구조화*는 안 함.
- **Forge의 여지:** 에이전트 주변을 **감싸기**가 아니라 환경을 **agent-native하게 주조**.

### 한계 4: Autonomy Ceiling / Self-Eval Weakness
- Anthropic 실험: 에이전트가 자기 작업 평가 시 "confidently praising even mediocre work" → Evaluator 분리 필수.
- 그러나 Evaluator도 shallow testing 문제.
- **Forge의 여지:** 다층 검증(물리적 구현 → 자동화 사실 확인 → 경제적 시그널).

### 한계 5: Token Cost / Runtime 경제성 천정
- Anthropic 3-agent harness: **$124–200, 4–6시간** per build.
- Neil Dave: "9 months and $12K in API bills" 학습 비용.
- **Forge의 여지:** **한 번 주조되어 재사용되는 컴파일된 에이전트 아티팩트**. 용광로 은유의 경제적 핵심.

### 한계 6: Behavior Verification 공백
- "Today's tools are fine at checking maintainability but weak at confirming whether the agent actually did what was asked."
- 린트·테스트 통과해도 **비즈니스 의도 실패** 가능.
- **Forge의 여지:** **Intent-as-Code** 레이어 — 스펙 자체를 실행 가능한 형태로 주조.

### 한계 7: Multi-Agent Swarm Brittleness
- "Highly autonomous swarms are brittle, prohibitively expensive, and nearly impossible to debug in production" (전 벤더 공통).
- 시장은 "chaotic mesh" 대신 **bounded, deterministic workflows + HITL**로 수렴.
- **Forge의 여지:** multi-agent를 free-form 채팅이 아니라 **타입 시스템/컴파일러처럼 정적 검증 가능한 구조**.

### Harness의 구조적 한계 5축 요약

1. **서술적(declarative)만큼만 강함** — MD는 실행·검증 약함
2. **둘러싸기(wrapping)에 머무름** — 환경 자체 재조형 불가
3. **평가자 공백** — 자가 평가 구조적 편향
4. **경제적 비대칭** — 매 세션 비용, 재사용 어려움
5. **의도 검증 부재** — "맞게 만들었는가" 확인 불가

**→ Forge의 4가지 답변 방향:**

| Harness | Forge |
|---------|-------|
| 에이전트를 둘러싼다(wrap) | 환경을 주조(forge)한다 |
| 세션마다 재조립된다 | 한 번 주조된 아티팩트 재사용 |
| 자가 평가 루프 | 외부 물리적/경제적 실재와의 정합성 검증 |
| 모델 개선 시 불필요해지는 스캐폴딩 | 모델 개선과 무관한 영속적 조직 지식 아티팩트 |

---

## 6. 참고 링크 모음

### Canonical
- [OpenAI — Harness Engineering (Lopopolo, 2026-02-11)](https://openai.com/index/harness-engineering/)
- [Mitchell Hashimoto — My AI Adoption Journey](https://mitchellh.com/writing/my-ai-adoption-journey)
- [Martin Fowler — Harness engineering for coding agent users](https://martinfowler.com/articles/harness-engineering.html)
- [Martin Fowler — Harness Engineering first thoughts](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering-memo.html)
- [Latent Space — Extreme Harness Engineering (Lopopolo interview)](https://www.latent.space/p/harness-eng)

### Anthropic
- [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps)
- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Scaling Managed Agents: Decoupling brain from hands](https://www.anthropic.com/engineering/managed-agents)

### 레포/표준
- [awesome-harness-engineering](https://github.com/ai-boost/awesome-harness-engineering)
- [AGENTS.md template](https://github.com/ai-boost/awesome-harness-engineering/blob/main/templates/AGENTS.md)
- [AGENTS.md site](https://agents.md/) · [spec repo](https://github.com/agentsmd/agents.md)
- [OpenAI Codex AGENTS.md guide](https://developers.openai.com/codex/guides/agents-md)

### 툴별
- [Cursor — Rules](https://cursor.com/docs/context/rules) · [Best practices](https://cursor.com/blog/agent-best-practices)
- [Cline Memory Bank](https://docs.cline.bot/prompting/cline-memory-bank)
- [Aider docs](https://aider.chat/docs/) · [repomap.py](https://github.com/paul-gauthier/aider/blob/main/aider/repomap.py)
- [Continue.dev Rules](https://docs.continue.dev/customize/rules) · [Issue #6716](https://github.com/continuedev/continue/issues/6716)
- [Claude Code system prompts](https://github.com/Piebald-AI/claude-code-system-prompts)
- [HumanLayer — Writing a good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
- [HumanLayer — Skill Issue: Harness Engineering](https://www.humanlayer.dev/blog/skill-issue-harness-engineering-for-coding-agents)

### Context/Prompt 계보
- [Karpathy — context engineering tweet](https://x.com/karpathy/status/1937902205765607626)
- [Addy Osmani — Context Engineering](https://addyo.substack.com/p/context-engineering-bringing-engineering)
- [dbreunig — Prompts vs Context](https://www.dbreunig.com/2025/06/25/prompts-vs-context.html)
- [Atlan — Prompt vs Context vs Harness Engineering](https://atlan.com/know/harness-engineering-vs-prompt-engineering/)

### 한계·비판 (섹션 5 근거)
- [Adnan Masood — Agent Harness Engineering: AI Control Plane (65% 실패 근거)](https://medium.com/@adnanmasood/agent-harness-engineering-the-rise-of-the-ai-control-plane-938ead884b1d)
- [Chintan Jain — Why Most AI Coding Agents Fail](https://medium.com/@chintan080/why-most-ai-coding-agents-fail-harness-engineering-is-the-missing-layer-42376e560859)
- [Adam Baitch — Model vs Harness: Which matters more?](https://medium.com/@adambaitch/the-model-vs-the-harness-which-actually-matters-more-59dd3116bb31)
- [Neil Dave — 7 Harness Secrets ($12K in API bills)](https://theneildave.medium.com/7-harness-engineering-secrets-top-1-of-agentic-ai-teams-know-that-took-me-9-months-and-12k-in-65204b263f78)
- [New Stack — AI Agent Harness Pricing Split](https://thenewstack.io/ai-agent-harness-pricing-split/)
- [jock.pl — Coding Harness 2026 (Claude Code vs Codex vs Aider 등 비교)](https://thoughts.jock.pl/p/ai-coding-harness-agents-2026)
- [AddyOsmani.com — Agent Harness Engineering](https://addyosmani.com/blog/agent-harness-engineering/)

### ⚠️ "Forge" 네이밍 관련 주의
- **ForgeCode** — 이미 존재하는 멀티에이전트 코딩 harness 제품 (Terminal-Bench 2.0 우승). [링크](https://medium.com/@richardhightower/forgecode-dominating-terminal-bench-2-0-harness-engineering-beat-claude-code-codex-gemini-etc-eb5df74a3fa4)
- **Platform Engineering's AI Forge** (WebProNews)
- **Mistral Forge** — Mistral의 제품명
- 그러나 **"Forge Engineering"이라는 독립 학술/산업 개념은 현재 시점에 정립되어 있지 않음** → 선점 가능.

---

## 7. 핵심 Takeaway (Forge 설계 시 참고)

1. **Harness Engineering은 2026-02에 이름 붙은 매우 젊은 분야** — 개념 공간 열려 있음.
2. Harness는 "모델을 감싸는" 패러다임 — **"환경을 주조하는" 패러다임은 비어 있음**.
3. 가장 취약한 축: **(a) 의도 검증, (b) 자가 평가 편향, (c) 경제성, (d) MD 부패** — Forge가 이 4축에 답하면 독자 분야로 성립.
4. **AGENTS.md는 표준화된 계약 포맷** — Forge는 이를 대체하기보다 **상위에서 컴파일·검증하는 레이어**로 포지셔닝하는 게 현실적.
5. **"Harness는 세션마다 조립"의 한계 → "한 번 주조된 재사용 아티팩트" 개념**이 Forge 은유의 경제적 핵심.
