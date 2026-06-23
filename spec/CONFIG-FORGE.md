# CONFIG-FORGE — 자가단조(Self-Forging) xgen 하네스 엔진 고도화 설계

> **Status:** Design draft v0.1 · 2026-06-17
> **Scope:** xgen 하네스 엔진(`xgen-harness-executor` / `xgen-sdk.harness`)을 *정적으로 설정되는 파이프라인*에서 *자기 실행 trace로부터 스스로 설정을 진화시키는* 하네스로 고도화하는 전체 방향과, 그 첫 단일-층 PoC(`prototypes/config-forge/`) 사양.
> **관계:** `FORGE.md`(하네스가 *어떻게 변경되어도 되는가*의 계약) ⊃ 본 문서(그 계약을 *실제 xgen 엔진의 타입 설정*에 적용하는 구현 설계). `research/self-improving-agents.md`·`research/harness-engineering.md`(이론 근거)를 전제로 한다.

---

## 0. 한 문장

**forge-v0는 brittle한 markdown(CLAUDE.md)을 재작성한다. 자가단조 xgen 하네스는 타입화된 `HarnessConfig`를 — 어느 stage에 어느 등록된 strategy/guard/effort/criteria를 쓸지 — 자기 run trace로부터 진화시키고, 외부 벤치마크(judge 점수)로 검증해 개선되면 채택·회귀하면 롤백한다.** 이것이 HarnessX(arXiv:2606.14249)가 말한 "타입 프리미티브의 치환대수 + trace 기반 진화"의 xgen 구현이며, xgen은 이를 만들기에 거의 유일하게 유리하다(타입 프리미티브 레지스트리 + NOM IR + FORGE 이론을 이미 셋 다 보유).

---

## 1. 배경 — 네 레퍼런스가 한 줄기로 정렬된다

비-온톨로지 축에서, 사용자가 지목한 네 레퍼런스는 **서로를 먹여주는 단일 스택**으로 정렬된다.

| 층 | 무엇 (출처) | 역할 |
|---|---|---|
| **L1 상태외부화 루프** | 2-tier WorkingMemory·결정전용 액션·결정론적 bookkeeping (harness-1, arXiv:2606.02373) | 깨끗한 **복원가능 trace**를 생산 → 진화의 연료 |
| **L2 진단→복원 자가치유** | Monitor→Detect→Diagnose→Recover→Verify, 근본원인 타이핑, rollback-first (자가치유 클러스터) | **타입화된 실패 진단**을 생산 → 진화가 무엇을 고칠지 가르침 |
| **L3 Speculative 이중모델** | 소형 드래프터 K개 → 대형 검증기 `ρ_Draft·ρ_SC·ρ_SR` argmax (Speculative RAG, arXiv:2407.08223) | 비용·지연 절감 (런타임 최적화 프리미티브) |
| **L4 자가단조(crown)** | trace→프리미티브 치환→critic 검증→진화 (HarnessX AEGIS + FORGE) | L1·L2가 만든 trace/진단을 digest해 **하네스 설정을 스스로 단조** |
| **공통** | per-stage `effort`, 검증 서브에이전트>self-critique, boundary/`assess-only` (Claude Fable 5) | 모든 stage가 노출하는 제어 노브 |

**핵심 인과:** 상태를 외부화하면(L1) 깨끗한 trace가 나오고 → 실패를 근본원인까지 진단하며(L2) → 이 둘이 만든 *타입화된 trace*를 하네스가 digest해 자기 설정을 단조한다(L4). L3·effort는 그 위에서 비용을 깎는다.

본 설계는 **L4(자가단조 루프)를 척추로 삼고**, L1·L2·L3·effort를 그 루프가 진화시키는 *프리미티브*이자 *연료*로 배치한다.

---

## 2. 현 자산 진단 — 무엇이 이미 있고, 무엇이 갭인가

### 2.1 엔진은 "치환대수의 어휘"를 이미 노출한다
`xgen-harness-executor` 정독 결과, 엔진은 도메인-무지 + 플러그인 확장형이며 **20+개의 `entry_points` 레지스트리 + role 기반 stage 디스패치**를 가진다. 자가단조가 조작할 **합법 수의 어휘**가 바로 여기 있다:

- `xgen_harness.strategies` — stage별 슬롯 구현(s00 transport, s06 compactor, s07 executor/router, **s08 evaluation/decide**…). `active_strategies[stage_id]`로 선택.
- `xgen_harness.guards` — `HookPoint`(PRE_MAIN/PRE_TOOL/POST_RESPONSE/LOOP_BOUNDARY)에 거는 정책 게이트. `guards: [{name, params}]`로 켬.
- `xgen_harness.evaluation_criteria` — judge 기준 `{name, description, weight, hard}`. `hard=true`면 미달 시 overall=0 → 무조건 retry.
- `xgen_harness.orchestrators` — `OrchestratorSpec`(linear/iterative/react/plan_execute/dag). `orchestrator_hint`로 선택.
- 스칼라 노브 — `validation_threshold`, `max_retries`, `max_iterations`, (예정)`effort`.

이 어휘는 **타입체크된다**: stage의 슬롯이 받는 strategy 이름, 등록된 guard 이름, 기준 스키마가 모두 레지스트리에 의해 검증된다. → **자가단조의 탐색공간을 "자유 텍스트(brittle)"가 아니라 "등록된 프리미티브의 조합(bounded·typed)"으로 둘 수 있다.** 이것이 forge-v0 대비 결정적 승격.

### 2.2 forge-v0는 루프를 완성했으나 엔진과 미연결 + MD에 갇혀 있다
`prototypes/forge-v0/` 정독 결과:
- `runner/runner.py` — **일반 Claude Code CLI**를 repo에서 돌리고 **pytest 통과율 델타**로 채점. (xgen 하네스 엔진이 아님.)
- `smith/rewriter.py` — reflection → LLM이 **파일 전체 내용 재작성** → `_resolve_target`이 `system_prompt→CLAUDE.md`, `workflow→workflows.yaml` 등 **markdown/yaml 파일**로 매핑. (타입 프리미티브가 아님.)
- `safety/inertia_brake.py` — bench 측정 전/후, `delta < -0.05`면 `git revert`. (구조는 정확히 재사용 가능.)
- `schemas/{reflection,rewrite,run}.v1.json` — 스키마 골격 존재.

**갭(= 연구문서 §5 한계 1을 forge-v0 자신이 답습):** 쓰기 대상이 brittle한 markdown이고, 엔진의 타입 어휘와 무관하며, 채점이 코드 테스트(하네스 답변 품질 아님)다.

### 2.3 결론 — 고도화의 정확한 한 수
> **forge-v0의 4축을 엔진-네이티브로 승격한다:**
>
> | forge-v0 (현재) | CONFIG-FORGE (목표) |
> |---|---|
> | 러너 = 일반 Claude Code CLI | 러너 = **xgen 하네스 엔진**이 벤치 태스크 실행 |
> | 쓰기 대상 = CLAUDE.md (brittle MD) | 쓰기 대상 = **타입 `HarnessConfig`** (stage→strategy/guard/effort/criteria) |
> | 채점 = pytest 통과율 | 채점 = **judge 점수**(하네스 답변 품질) over 벤치셋 |
> | smith = 자유 텍스트 라인 추가 | smith = **등록된 프리미티브의 치환**(치환대수, 타입체크) |

이 승격이 연구문서 §5의 한계들에 직접 답한다 — **한계1**(MD brittleness→타입 설정), **한계4**(self-eval 편향→외부 judge 벤치 + cross_check), **한계5**(경제성→설정 진화는 저렴 + 결과는 엔진이 이미 wheel/MCP로 *컴파일하는 재사용 아티팩트*), **한계6**(의도 검증→벤치=intent-as-code).

---

## 3. 전체 아키텍처 — 자가단조 루프 (L4 척추)

```
                 ┌──────────────────────────────────────────────────────────┐
                 │              CONFIG-FORGE  (offline / batch)              │
                 │                                                          │
   run traces ──▶│  Furnace        Reflection        Smith                  │
   (L1/L2 산)    │  실패 intake  →  근본원인 lesson  →  치환 수(手) 제안       │
                 │  + 분류          (reflection.v1)    (치환대수 = 등록       │
                 │                                     프리미티브 조합)      │
                 │                         │                                │
                 │                         ▼                                │
                 │   Cross-Check Validator (validator ≠ smith, 만장/다수)    │
                 │                         │                                │
                 │                         ▼                                │
                 │   Inertia Brake:  J(H_new) − J(H_old) ≥ −ε ?             │
                 │        ├ yes → 채택(promote) + Audit(Derived-From-Reflection)│
                 │        └ no  → 롤백(rollback) + 롤백도 연료로            │
                 └──────────────────────────────────────────────────────────┘
                                          │  (진화된 HarnessConfig)
                                          ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │                    런타임 하네스 (xgen 엔진, per request)               │
   │  L1 상태외부화 루프 ─ 깨끗한 복원가능 trace 생산 ──────────┐            │
   │  L2 진단→복원 자가치유 ─ 타입화된 실패 진단 생산 ─────────┤──▶ traces │
   │  L3 speculative + per-stage effort ─ 비용/품질 노브 ───────┘            │
   └──────────────────────────────────────────────────────────────────────┘
```

**이중 루프 = HarnessX의 harness↔model 공진화의 xgen판.** 단 우리는 모델 가중치는 건드리지 않고(provider-agnostic 기조) **하네스 설정만** 진화시킨다 — 안전하고, 즉시 가역이며, 컴파일 가능한 아티팩트로 굳는다.

---

## 4. 치환대수(Substitution Algebra) — 합법 수의 정의

자가단조의 탐색공간 = `HarnessConfig`에 가할 수 있는 **타입체크된 mutation의 집합**. 각 수(手)는 엔진 레지스트리에서 **자동 발견**되며(하드코딩 금지), 적용 전 스키마 검증된다.

| 수(手) 종류 | 정의 | 합법성 출처(레지스트리) |
|---|---|---|
| `set_strategy(stage, slot, impl)` | stage 슬롯의 strategy 교체 | `xgen_harness.strategies`에 등록된 `(stage, slot, impl)` |
| `toggle_guard(name, on, params)` | guard 체인에 add/remove | `xgen_harness.guards` 등록명 + `param_schema()` |
| `set_effort(stage, level)` | stage별 effort ∈ {low,medium,high,xhigh,max} | (예정) per-stage effort enum |
| `tune_scalar(key, value)` | `validation_threshold`/`max_retries`/`max_iterations`/`judge_threshold` | `runtime_defaults`의 안전 floor/ceiling |
| `edit_criterion(name, weight, hard)` | judge 기준 가중/하드 토글 | `xgen_harness.evaluation_criteria` |
| `set_orchestrator(name)` | 루프 패턴 교체 | `xgen_harness.orchestrators` |

**불변식(locked surface, FORGE.md §1 준수):** 엔진 코어 코드·`criteria_defs`의 의미축 정의·provider 키·벤치셋 자체는 smith가 못 건드린다. smith는 **설정 키만** 조작한다 → 엔진의 standalone 순수성·plugin 확장성을 절대 깨지 않음(기조 부합).

**왜 대수(algebra)인가:** 수들은 합성 가능(compose)하고, 각 수는 역(inverse)이 있어(이전 값 복원) inertia-brake 롤백이 결정론적이다. 이것이 HarnessX "substitution algebra"의 실질이다.

---

## 5. 엔진 측 / 이식 측 부착 seam (양면)

기조: **엔진 = provider-agnostic 프리미티브(무도메인) / 이식 = xgen 배선**. 한쪽만 고치면 안 됨.

| 메커니즘 | 엔진 측 (`xgen-harness-executor`, entry_points) | 이식 측 (`xgen-workflow/harness_bridge`) |
|---|---|---|
| **L4 자가단조** | `forge-engineering`(엔진 위 레이어): runs/ reflection digest, NOM 설정 치환, 벤치 게이트. 엔진엔 read-only(trace 읽기)+config 산출만. | run trace → `xgen-core.harness_execution` 영속, 벤치셋 보관, offline forge 잡(스케줄러) |
| **L2 자가치유** | `s08_decide`에 `diagnose_then_recover` DecideStrategy(진단 aux_call→8-액션 메뉴→진단 messages 재주입). circuit-breaker는 `tool_diversity` guard 확장. **현 갭: `validation_feedback` 저장만·재주입X** | 롯데 QA를 이 전략으로 라우팅(보류 편향·retry-death 직격). 이식측 `reflexive_judge.py`엔 이미 `_inject_reflection` 있음 → 엔진으로 상향 |
| **L1 상태외부화** | `memory/recall.py`(RecallSet)+`progress.py`+`pd_stores`를 통합 2-tier WorkingMemory로; `WorkingMemorySnapshot` 직렬화; "decision-only" OrchestratorSpec + curate/review/verify 빌트인 | `register_service`로 Redis/DB 복원 스냅샷 store; RAG 결과→후보풀 |
| **L3 speculative** | `speculative` OrchestratorSpec + `fan_out_strategy`(휴면 DAGOrchestrator 부활) + 검증기 EvaluationStrategy(`ρ_Draft·ρ_SC·ρ_SR`) | 드래프터=vLLM Qwen, 검증기=Bedrock Claude; perspective=RAG 부분집합 |
| **per-stage effort** | 모든 Stage에 `effort` enum(기본 high); provider effort 매핑; xhigh/max 시 max_tokens 자동 상향 | 캔버스 노드에 effort 노출 |
| **검증 서브에이전트** | subpipeline 도구(이미 존재) 기반 verify stage; fresh-context | QA verify 서브에이전트 |

---

## 6. 단계적 로드맵

- **Phase 0 — PoC (본 작업):** `prototypes/config-forge/`. 치환대수 + 자가단조 루프 + inertia-brake를 **오프라인 MockRunner**로 end-to-end 시연. 실엔진 무의존, 단 `Runner` 프로토콜로 실엔진 연결 seam 확보.
- **Phase 1 — 실엔진 연결:** `XgenHarnessRunner` 구현(설치된 `xgen-harness`/`xgen-sdk` 호출), 벤치셋 = 소형 QA 태스크, J = judge 점수. 로컬 검증.
- **Phase 2 — L2 자가치유 런타임:** `diagnose_then_recover` DecideStrategy 엔진 추가 + 이식 라우팅. (즉시 실효: 롯데 QA.)
- **Phase 3 — L1 상태외부화:** WorkingMemory 통합 + 복원 스냅샷. (장기 trace 품질↑ = Phase 4 연료.)
- **Phase 4 — 메타 진화:** smith가 LLM 기반 치환 제안 + cross_check; (선택) Promptbreeder식 *변이 지시문 자체의 진화*(연구문서 M3, Forge 간판 차별점).

---

## 7. 안전·기조 준수

- **확장성:** 모든 수(手)는 등록된 프리미티브에서만 나온다. 도메인 로직을 코어에 박지 않음.
- **연동성:** 엔진은 trace를 읽고 config를 낼 뿐, 무거운 인프라에 역결합하지 않음(standalone 유지). forge 레이어가 xgen DB에 붙는 건 이식측에서.
- **무하드코딩:** 임계값·move set은 레지스트리/벤치에서 파생. 매직넘버 금지.
- **롤백 우선(inertia_brake):** 회귀 시 "다시 시도" 루프 없이 즉시 가역.
- **cross_check:** validator ≠ smith(만장/다수). 자기선호 편향 차단.
- **locked surface:** 코어 코드·벤치셋·의미축 정의·시크릿은 불가침.
- **HITL:** `full-rewrite` 모드는 사람 승인. PoC는 config-only라 본질적으로 저위험.

---

## 8. PoC 사양 (`prototypes/config-forge/`)

### 8.1 목표
forge-v0의 루프를 **타입 설정 진화**로 승격한 최소 동작본을, **오프라인·무API·결정론적**으로 시연한다. 실엔진/실LLM 없이도 "trace→reflection→치환 제안→inertia-brake→채택/롤백→audit"가 J를 단조 개선시키는 것을 눈으로 확인.

### 8.2 구조
```
config-forge/
├── README.md
├── algebra.py        # 치환대수: 등록 프리미티브 발견(주입형) + 합법 수 생성/적용/역
├── runner.py         # Runner 프로토콜 + MockRunner(오프라인) + XgenHarnessRunner(Phase1 stub)
├── reflect.py        # trace → reflection(근본원인 lesson + 후보 수). 휴리스틱 기본 + LLM 선택
├── forge.py          # 자가단조 루프: measure→reflect→propose→validate→inertia-brake→audit
├── bench.py          # 소형 벤치셋(태스크+기대) — 정적, smith 불가침
└── demo.py           # 10-step 워크스루 실행 → J 개선 곡선 + commits.jsonl 출력
```

### 8.3 인터페이스 (요지)
```python
# Runner: config + task → 점수 [0,1] (실엔진이든 mock이든 동일 계약)
class Runner(Protocol):
    def run(self, config: dict, task: dict) -> RunRecord: ...   # {score, outcome, trace}

# 치환대수: 등록 프리미티브(주입)에서 합법 수만 생성
class Algebra:
    def legal_moves(self, config) -> list[Move]
    def apply(self, config, move) -> dict        # 새 config (불변)
    def invert(self, move) -> Move               # 롤백용 역수

# 루프: bench 평균 J 측정 → 실패 reflect → 수 제안 → validator → inertia-brake
forge_loop(runner, algebra, bench, steps, epsilon=-0.02) -> list[CommitRecord]
```

### 8.4 성공 기준 (forge-v0 README의 falsifiable 정신 계승)
1. 초기 config의 벤치 J가 의도적으로 낮다(예: judge off, threshold 부적합, guard 없음).
2. 루프가 trace에서 근본원인 reflection을 생성한다(예: "hard 기준 미달 다수 → judge 미활성").
3. **타입체크된 수(手)** 하나가 제안된다(예: `tune_scalar(validation_threshold, 0.8)` 또는 `toggle_guard(content, on)`).
4. inertia-brake가 J 개선을 확인하고 채택, 회귀 수는 롤백한다.
5. `commits.jsonl`에 `Derived-From-Reflection`/`Bench-Before`/`Bench-After`/`verdict`가 남는다.
6. 최종 J > 초기 J (단조 개선), 전 과정 오프라인·결정론.

### 8.5 실엔진 연결 seam (Phase 1)
`XgenHarnessRunner.run(config, task)`만 구현하면 동일 루프가 실엔진에 작동. config = `HarnessConfig` dict, task = {input, expected}, score = judge 점수. 치환대수의 프리미티브 발견은 `import xgen_harness; registry.list_*()`로 교체(주입형이라 PoC 코드 무변경).

---

## 9. 미해결 / 결정 필요
- 벤치 J의 정의(judge 점수 vs 태스크 통과 vs 혼합)와 벤치셋 출처(롯데 QA 샘플 사용 여부).
- per-stage `effort`를 엔진에 1급 파라미터로 추가하는 시점(Fable5 기조 반영).
- forge 레이어 배포 형태(엔진 repo 내 `forge-engineering` vs 별도 offline 잡).
- 실엔진 연결 시 로컬 스택 사용 여부(RAM 16GB 주의 — docker는 허락 후).
