# Self-Improving Agents Research (Forge Engineering 기반 자료)

> 2026-04-24 · 리서치 에이전트 조사 결과
>
> Forge Engineering의 핵심 가설 — "에이전트가 실패를 연료로 자기 프롬프트/도구/워크플로우를 재제련한다" — 를 뒷받침할 학술·오픈소스 선행 사례 정리.

---

## 1. 실패 피드백 루프 (Reflexion 계열)

| 사례 | 실패 → 재제련 메커니즘 |
|------|------------------------|
| **Reflexion** (Shinn et al., NeurIPS 2023) | 에이전트가 실패한 trajectory를 받아 **"왜 실패했는지"를 자연어로 스스로 기술(verbal reflection)** 하고, 이 반성문을 episodic memory buffer에 저장해 다음 시도의 프롬프트에 주입. Weight 업데이트 없이 HumanEval 80% → 91% 달성. |
| **Self-Refine** (Madaan et al., NeurIPS 2023) | 동일한 LLM이 생성자·피드백·리파이너 3역할을 맡아, 출력 → 자기비평(문제 위치 + 개선 지시) → 재생성 루프. 평균 20% 성능 향상. |
| **SELF: Self-Evolution with Language Feedback** (Lu et al., 2023) | 무라벨 instruction에 대해 LLM이 스스로 응답·언어 피드백·수정본을 생성하고, 이 합성 데이터로 반복 fine-tuning (GSM8k +6.82%). |
| **Constitutional AI / RLAIF** (Anthropic, 2022) | "헌법" 원칙에 따라 LLM이 자기 출력을 critique·revise → 그 데이터로 self-preference 학습. 인간 라벨 최소화. |
| **EvolveR** (2025) | Offline Self-Distillation(trajectory → 재사용 가능한 "전략 원칙" 저장소) + Online Interaction + RL loop. 실패/성공 경험을 추상 원칙으로 승화. |

**핵심 패턴:** 실패 trace → 자연어 요약(lesson) → 메모리 → 다음 시도 프롬프트에 재주입.

---

## 2. 스킬 라이브러리 자동 축적 (Voyager 계열)

| 사례 | 실패 → 재제련 메커니즘 |
|------|------------------------|
| **Voyager** (Wang et al., NVIDIA/Caltech, 2023) | Minecraft에서 (a) automatic curriculum (b) **executable code로 된 skill library가 계속 자라남** (c) 환경 피드백 + execution error + self-verification로 코드를 반복 개선. 실패한 코드는 고쳐서 스킬로 승격. |
| **Agent Workflow Memory** (Wang et al., 2024) | 과거 에이전트 trajectory에서 **공통 서브루틴을 추출해 "workflow"로 추상화**, 이후 쿼리에 selectively 주입. WebArena +24.6%, Mind2Web +51.1%. |
| **STaR** (Zelikman, NeurIPS 2022) | 답이 틀렸으면 **정답을 주고 rationale을 역생성(rationalization)**, 그 중 맞은 것만 남겨 fine-tune. 실패를 학습 데이터로 전환하는 원형. |

**핵심 패턴:** 성공한 실행 단위(code/workflow)를 이름 붙여 재사용 가능한 자산으로 적립.

---

## 3. 프롬프트/도구 자동 최적화 (DSPy, TextGrad 등)

| 사례 | 실패 → 재제련 메커니즘 |
|------|------------------------|
| **DSPy** (Stanford, 2023) | LM 파이프라인을 "signature + module + metric"으로 선언하고 컴파일러가 few-shot demo·instruction·심지어 weight까지 metric 기준으로 자동 최적화 (MIPROv2 등). |
| **TextGrad** (Stanford, Nature 2024) | PyTorch-like API로 **"텍스트 gradient"를 LLM이 자연어로 생성해 역전파**. 프롬프트·코드·분자구조·방사선계획까지 미분 가능. GPQA 51→55%, GSM8K 72.9→81.1%. |
| **OPRO** (DeepMind, 2023) | Meta-prompt에 "(prompt, score)" 이력을 계속 누적 → LLM이 다음 후보 프롬프트 생성. GSM8K +8%, BBH +50%. |
| **Promptbreeder** (DeepMind, 2023) | **Mutation prompt 자체가 진화**하는 self-referential 진화 알고리즘. task prompt와 mutation prompt가 동시에 개선됨. |
| **Meta-Prompting** (Suzgun & Kalai, 2024) | 단일 LM이 conductor가 되어 자기 자신을 expert instance로 호출·통합. 서브태스크 분해 + 자가 검증. |

**핵심 패턴:** metric을 정의하고, 프롬프트/구조를 탐색 변수로 취급해 자동 서치.

---

## 4. 도구 자동 생성 (Toolformer 계열)

| 사례 | 실패 → 재제련 메커니즘 |
|------|------------------------|
| **Toolformer** (Meta, Schick 2023) | LM이 **스스로 API 호출 위치를 주석처럼 삽입**하고, self-supervised loss로 "그 호출이 next-token 예측을 도왔나?"를 검증해 유용한 것만 남겨 fine-tune. |
| **CREATOR** (Qian et al., EMNLP 2023) | 추상(tool 설계) vs 구체(tool 호출)를 분리. LLM이 documentation + Python 구현을 직접 쓰고, 실행 실패하면 수정. |
| **LATM — LLMs As Tool Makers** (Cai et al., 2023) | GPT-4가 tool-maker, GPT-3.5가 tool-user. 비싼 모델이 만든 tool을 싼 모델이 반복 사용하는 **cost amortization 패턴**. |
| **ToolMaker** (KatherLab, ACL 2025) | GitHub repo를 받아 **자동으로 의존성 설치 + 실행 코드 작성 + closed-loop self-correction**으로 에러를 진단·수정하며 LLM-호출 가능한 tool로 변환. |

**핵심 패턴:** "내가 자주 쓰는 서브루틴이면 → 코드화 → 재호출 가능한 tool로 굳히기".

---

## 5. 메타-학습 / 자기 수정 에이전트

| 사례 | 실패 → 재제련 메커니즘 |
|------|------------------------|
| **Gödel Agent** (Yin et al., 2024) | Gödel machine 철학에 따라 에이전트가 **자기 자신의 로직·모듈·업데이트 방식까지 재귀적으로 수정**. human-designed 제약 제거. (단 error accumulation 불안정성 경고) |
| **ADAS — Automated Design of Agentic Systems** (Hu, Lu, Clune, ICLR 2025) | "Meta Agent Search" — meta-agent가 **Python 코드로 새 에이전트를 계속 발명**하고 archive에 누적. Turing-complete이라 novel prompts/tools/workflows를 이론상 모두 탐색 가능. |
| **Self-Discover** (DeepMind, 2024) | 태스크마다 atomic reasoning module들을 선택·조합해 task-unique **명시적 reasoning structure**를 self-compose. CoT 대비 +20~30%, 추론 비용 10~40x 절감. |
| **Self-Rewarding Language Models** (Meta, 2024) | LLM-as-Judge로 자기 출력을 채점 → DPO로 반복 학습. 리워드 모델이 인간 천장에 박히지 않음. |
| **Survey: Self-Evolving Agents** (2025) | "What/When/How/Where to evolve" 축으로 전 분야 매핑. MUSE (Plan-Execute-Reflect-Memorize), SPO (prompt 자가 최적화), RAGEN (MDP + env feedback) 등. |

**핵심 패턴:** 자기 설계 자체를 탐색 변수로 삼아 archive에 축적하고 재조합.

---

## 6. Forge Engineering에 직접 응용할 메커니즘 7가지 ⭐

**이 7개가 Forge의 6대 메커니즘(Failure Furnace / Reflection Hammer / Skill Anvil / Prompt Tempering / Tool Smithing / Harness Rewrite)의 구현 자재다.**

### M1. Verbal Reflection Buffer (from Reflexion)
- 원천: https://arxiv.org/abs/2303.11366 · https://github.com/noahshinn/reflexion
- 원리: 실패 trajectory를 자연어 "lesson"으로 요약해 episodic memory에 append, 다음 실행 시 system prompt에 주입.
- Forge 적용: 모든 실행을 `run_id → {goal, trace, outcome, lesson}` 스키마로 SQLite에 저장. 실패 시 자동으로 3줄 lesson 생성, 다음 동종 태스크에 top-k 주입. → **Reflection Hammer** 핵심 구현.

### M2. Growing Skill Library as Code (from Voyager)
- 원천: https://voyager.minedojo.org/ · https://github.com/MineDojo/Voyager · arXiv 2305.16291
- 원리: 반복 성공한 행동 시퀀스를 **이름 붙인 실행 가능한 코드**로 라이브러리화, embedding으로 재검색.
- Forge 적용: 성공 태스크의 핵심 서브루틴을 `skills/<skill_name>.py`로 자동 추출 + docstring + embedding 인덱스. 새 태스크에 유사도 top-k skill을 도구로 노출. → **Skill Anvil** 핵심 구현.

### M3. Self-Referential Mutation (from Promptbreeder) ★
- 원천: https://arxiv.org/abs/2309.16797
- 원리: task prompt뿐 아니라 **그것을 돌연변이시키는 mutation prompt도 함께 진화**. 2-layer self-reference.
- Forge 적용: `{현재 프롬프트, 변이 지시문, metric}` 삼중쌍을 세대마다 LLM이 동시 mutate. 변이 지시문까지 진화하므로 **개선 방식 자체가 개선**됨. → **Forge의 간판 차별점**.

### M4. Textual Gradient Backprop (from TextGrad)
- 원천: https://textgrad.com/ · https://github.com/zou-group/textgrad · arXiv 2406.07496
- 원리: 어떤 변수든 LLM이 **"이걸 이렇게 바꿔라"를 자연어로 출력 = gradient**. 계산 그래프 따라 역전파.
- Forge 적용: 에이전트 파이프라인을 TextGrad 그래프로 wrapping. 최종 신호를 leaf부터 root까지 역전파 → 프롬프트·도구 코드·워크플로우 분기 동시 튜닝. → **Prompt Tempering** 핵심 구현.

### M5. Workflow Induction from Traces (from Agent Workflow Memory)
- 원천: https://arxiv.org/abs/2409.07429
- 원리: 완료된 trajectory들에서 **공통 서브루틴을 LLM이 추출**해 추상화, 이후 태스크에 selectively 제공.
- Forge 적용: N trace마다(online) 또는 매일 밤(batch) "최근 100개 성공 trace에서 공통 패턴 뽑기" 배치 → `workflows.yaml`에 추가. Skill Library의 상위 레이어.

### M6. Closed-Loop Self-Correcting Tool Builder (from ToolMaker / CREATOR / LATM)
- 원천: https://github.com/KatherLab/ToolMaker · https://arxiv.org/abs/2305.14318 · https://arxiv.org/abs/2305.17126
- 원리: 새 태스크에 tool이 없으면 LLM이 tool 스펙·구현·테스트를 쓰고, 실행 에러 시 자동 진단-수정 루프.
- Forge 적용: "세 번 이상 같은 외부 API를 ad-hoc 호출" 감지 → 자동으로 Python wrapper 생성 + 샘플 input 테스트 + 실패 시 self-repair. 통과하면 영구 tool로 등록. → **Tool Smithing** 핵심 구현.

### M7. Meta-Agent Archive Search (from ADAS) ★
- 원천: https://github.com/ShengranHu/ADAS · arXiv 2408.08435 · ICLR 2025
- 원리: **Meta-agent가 에이전트 자체를 Python 코드로 발명**하고 archive에 누적, 매 세대 새 조합 시도. Turing-complete 탐색 공간.
- Forge 적용: 주 1회 meta-agent가 지난 주 로그를 읽고 **에이전트 전체 아키텍처(시스템 프롬프트 골격, 도구 선택 정책, 메모리 검색 전략)의 변주를 코드로 생성**, A/B 벤치마크 후 winner 승격. → **Harness Rewrite**의 최상위 루프.

---

## 7. 참고 링크 모음

### 실패 피드백 루프
- Reflexion: https://arxiv.org/abs/2303.11366 · https://github.com/noahshinn/reflexion
- Self-Refine: https://arxiv.org/abs/2303.17651 · https://selfrefine.info/ · https://github.com/madaan/self-refine
- SELF: https://arxiv.org/abs/2310.00533
- Constitutional AI: https://www.anthropic.com/research/constitutional-ai-harmlessness-from-ai-feedback · https://arxiv.org/abs/2212.08073
- EvolveR (2025): https://arxiv.org/abs/2510.16079

### 스킬 라이브러리
- Voyager: https://voyager.minedojo.org/ · https://arxiv.org/abs/2305.16291 · https://github.com/MineDojo/Voyager
- Agent Workflow Memory: https://arxiv.org/abs/2409.07429
- STaR: https://arxiv.org/abs/2203.14465 · https://github.com/ezelikman/STaR

### 프롬프트/도구 최적화
- DSPy: https://dspy.ai/ · https://github.com/stanfordnlp/dspy · https://arxiv.org/abs/2310.03714
- TextGrad: https://textgrad.com/ · https://github.com/zou-group/textgrad · https://arxiv.org/abs/2406.07496
- OPRO: https://arxiv.org/abs/2309.03409 · https://github.com/google-deepmind/opro
- Promptbreeder: https://arxiv.org/abs/2309.16797
- Meta-Prompting: https://arxiv.org/abs/2401.12954 · https://github.com/suzgunmirac/meta-prompting
- AutoGen: https://github.com/microsoft/autogen · https://arxiv.org/abs/2308.08155

### 도구 자동 생성
- Toolformer: https://arxiv.org/abs/2302.04761
- CREATOR: https://arxiv.org/abs/2305.14318 · https://github.com/qiancheng0/CREATOR
- LATM: https://arxiv.org/abs/2305.17126 · https://github.com/ctlllll/LLM-ToolMaker
- ToolMaker (ACL 2025): https://github.com/KatherLab/ToolMaker

### 메타-학습/자기 수정
- Gödel Agent: https://arxiv.org/abs/2410.04444 · https://github.com/Arvid-pku/Godel_Agent
- ADAS (ICLR 2025): https://arxiv.org/abs/2408.08435 · https://github.com/ShengranHu/ADAS · https://www.shengranhu.com/ADAS/
- Self-Discover: https://arxiv.org/abs/2402.03620
- Self-Rewarding LM: https://arxiv.org/abs/2401.10020

### 2025 Survey & Ecosystem
- Self-Evolving Agents Survey (What/When/How/Where): https://arxiv.org/abs/2507.21046
- Comprehensive Survey of Self-Evolving AI Agents: https://arxiv.org/abs/2508.07407
- Awesome-Self-Evolving-Agents (XMU): https://github.com/XMUDeepLIT/Awesome-Self-Evolving-Agents
- Awesome-Self-Evolving-Agents (EvoAgentX): https://github.com/EvoAgentX/Awesome-Self-Evolving-Agents
- EvoAgentX framework: https://github.com/EvoAgentX/EvoAgentX

---

## 조사 결과 핵심 진단 ★

Forge Engineering은 **기존 연구들의 "세로 기둥"을 가로로 엮는 통합 포지션**이 가능하다. 각각은 조각이다:

| 연구 | 담당 레이어 |
|------|-------------|
| Reflexion | 실패 로그 → 자연어 lesson |
| Voyager | 성공 행동 → 코드 스킬 |
| AWM | trajectory → 워크플로우 |
| ToolMaker | ad-hoc 호출 → 영구 tool |
| Promptbreeder/TextGrad | 프롬프트 자체 튜닝 |
| ADAS | 에이전트 구조 자체 진화 |

**Forge의 독창성 포인트:**
1. 이들을 **단일 "재제련 큐(forge queue)"로 통합**
2. **실패 이벤트를 트리거**로 계층별(prompt → skill → tool → workflow → architecture) **자동 승격**
3. **"금속학적 비유 + 실패 우선 설계"** 로 포지셔닝

**결정적 틈새:** **M3(self-referential mutation) + M7(meta-agent archive) 조합**이 아직 어느 프레임워크에도 통합되지 않았다. "개선 방법 자체를 개선하는 엔진"을 간판 기능으로 삼으면 차별화가 명확해진다.
