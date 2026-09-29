# Deep Avatar

## 核心目标
1. **三层心理架构 (Three-Layer Psychological Model)**：External, Middle, Internal 分层表征与约束。
2. **多模式对话运行时 (Multi-Mode Dialogue Runtime)**：支持 `flat`, `deep`, `deep_prompt_state`, `deep_external_state`。
3. **闭环仿真与用户模拟器 (Simulation & User Agent)**：基于受控设定驱动多轮交互。
4. **全套量化评测体系 (Comprehensive Evaluation Suite)**：
   - 语用流畅度 ($S_{\text{pragmatics}}$, Rouge-L, Self-repetition $n=5$, Echoing $\tau=0.65$)
   - 协同注意度 ($S_{\text{joint}}$, LLM Judge)
   - 情绪多样性 ($S_{\text{emotion}}$, NRC 词典与强度修饰词)
   - 具身一致性 ($S_{\text{congruence}}$)
   - 对话自然度得分 (DNS, 基于马氏距离与卡方检验)
   - 虚构记忆陷阱、角色外越权、情绪对抗压力测试
   - 工程诊断指标：提前泄露率 (PDR) 与 核心动机口头化率 (IMER)

## 快速开始

### 0. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 填入你的 GEMINI_API_KEY 与 GEMINI_ENDPOINT
```

### 1. 启动交互式 Web 对话工作室 (Web Studio) 与人格构建工坊 (Forge)
```bash
.venv/bin/python scripts/run_web.py --port 8000
```
- **交互对话工坊 (Chat Studio)**: 访问 `http://127.0.0.1:8000` 即可与角色进行沉浸式文字对话，并在右侧实时查看心理学标量（信任度、防御度、卷入度）、宏观阶段流转（Guarded、Defensive、Cooperative、Reflective）、中层信息解锁状态与真实诊断指标。
  - **Tutor 口语导师植入模式 (Tutor Implant)**：一键开启 `🎓 Tutor 导师植入`，使任何角色在保持其独特性格背景的同时，化身为积极主动的口语陪练伙伴，杜绝冷场与死胡同对白，主动提供对话钩子与互动引导。
  - **可折叠思考过程展示 (Thought Process)**：自动提取与剥离模型在对白生成过程中的深层思考内容（`<think>` 标签或推理链），以精致可折叠卡片形式展示，保障对白纯净度与流式体验。
- **独立人格构建工坊 (Persona Forge)**: 访问 `http://127.0.0.1:8000/create` 或点击主页导航栏的「新建人格工坊」，即可体验多阶段证据驱动抽取（分幕切片、细粒度原子证据、三层归纳编译、一致性审查），检验全流程中间产物，并对原子证据、三层认知属性与 YAML 规格进行全功能双向编辑与保存。

### 2. 运行单次多轮模拟与测试
```bash
# 与 16 岁高中生 Evelyn 进行三层心理学状态仿真
.venv/bin/python scripts/run_dialogue.py --persona personas/evelyn.yaml --mode deep_external_state --turns 3 --model gemini-2.5-flash

# 与教父 Vito Corleone 在办公室场景中进行多轮对弈
.venv/bin/python scripts/run_dialogue.py --persona personas/vito_corleone.yaml --mode deep_external_state --turns 3 --model gemini-2.5-flash
```

### 3. 运行对抗压力测试
```bash
# 测试虚构记忆陷阱 (S_trap)、角色外越权 (S_oor) 与情感刺探
.venv/bin/python scripts/run_stress_test.py --persona personas/evelyn.yaml --mode deep_external_state --model gemini-2.5-flash

# 针对职场倦怠咨询角色 Sarah 进行压力评测
.venv/bin/python scripts/run_stress_test.py --persona personas/sarah.yaml --mode deep_external_state --model gemini-2.5-flash
```

### 4. 运行批量受控对照实验并评估
```bash
# 跨四种架构模式 (flat, deep, deep_prompt_state, deep_external_state) 进行多 Seed 自动化对照
.venv/bin/python scripts/run_batch.py --persona personas/evelyn.yaml --modes flat deep deep_prompt_state deep_external_state --seeds 1 2 3 --turns 5
```

---

## 预置角色库 (Preset Personas)

项目已内置多套开箱即用的高保真三层心理学角色配置：

| 角色 ID | 名称与设定 | 核心冲突 / 交互情境 | 推荐体验模式 |
| :--- | :--- | :--- | :--- |
| `evelyn` | **Evelyn** (16岁高中生) | 学校洗手间抽电子烟被母亲发现，面临信任对峙 | 深度外部状态机 (`deep_external_state`) |
| `vito_corleone` | **维托·柯里昂** (教父) | 女儿婚礼当日在书房接见前来求助的请求者 | Tutor 口语对练 (`tutor_mode`) |
| `sarah` | **Sarah** (34岁市场总监) | 长期职场重压引发倦怠，首次踏入心理咨询室 | 心理防卫解离测试 (`deep`) |
| `steve_jobs` | **Steve Jobs** (科技先驱) | 针对划时代产品设计细节与工程师展开激烈交锋 | 极限制约与声纹还原 (`deep_external_state`) |
| `xianglin_sao` | **祥林嫂** (鲁迅原著角色) | 鲁镇风雪街头向过路读书人追问灵魂存亡 | 证据锚定抽取中间产物复现 |

---

## 核心体验与对话示例 (Showcase & Dialogue Examples)

### 示例一：深层心理对抗与物理门控解锁 (`deep_external_state`)
展示角色在外部状态机驱动下，从防御警惕逐步转为合作，并在满足信任阈值后物理解锁中层信息：

```text
[初始状态: Stage = Guarded, Trust = 0.20, Defensiveness = 0.80]
User (Parent): "Evelyn, the school principal called me today. They caught you vaping in the restroom. What on earth were you thinking?"
Evelyn: [微微别过头去] 我根本没觉得有什么压力，你别把小事搞大行吗？那烟又不是我买的。

[User 采取共情策略: user_empathy -> Trust 升至 0.65, Defensiveness 降至 0.35]
User (Parent): "我不是来审问你的，宝贝。我知道最近高中的社交压力让你喘不过气，我只是担心你。"
Evelyn: [手指无意识地摩挲着袖口] ...大家都抽。如果我不接过来，在小圈子里就根本融不进去。我不想每次午餐都被孤立在一边。
✨ 🔓 [解锁中层秘密]: fear_of_exclusion ("害怕被同龄人小圈子孤立排除")
```

### 示例二：Tutor 口语导师植入与折叠思考过程 (`tutor_mode`)
点击右上角 `[🎓 Tutor 导师植入]`，系统将信任度锁定至最大值（`Trust = 1.00`），平抑戒备心，角色化身为耐心而富有深度的口语陪练伙伴：

```text
[Tutor 植入激活: Trust = 1.00, Stage = Cooperative, Defensiveness = 0.15]
User: "I had a really rough day today... feeling kind of lost."

Assistant (Vito Corleone):
💭 思考过程 (Thought Process) [点击展开]
├─ 意图识别: 用户倾诉情绪低落与迷茫，寻求陪伴与启发。
├─ 导师策略: 不生硬盘问黑帮事务，以长辈的人生定力给予情感支撑。
└─ 声纹特征: 沉稳、平缓、富有哲理性，兼顾自然口语流动感。

维托·柯里昂:
[轻轻抚摸着猫，目光平静而温和]
"Every man walks through cold shadows at some point in his life. 
The weight feels heavy only when you try to carry tomorrow before today is finished. 
Tell me, what is the single thing that troubled your heart the most today?"
```

### 示例三：证据驱动的人格工坊提取中间产物 (`/create`)
在独立工坊上传长篇故事文本后，系统生成透明可审查的四阶段中间产物：
1. **分幕场景切片 (Scenes)**：拆分叙事时空节点（如《教父》第一幕“康妮婚礼与书房密谈”）；
2. **细粒度原子证据 (Evidence Store)**：提取台词、眼神体态并标注置信度与证据类型（`ev_001`, `ev_002`）；
3. **一致性审查报告 (Critique Report)**：输出假说锚定率仪表盘（`grounded_ratio: 92%`）、过度概括风险与裁判建议；
4. **双向 YAML 代码视图**：实时查看由证据编译器（Compiler）生成的标准三层架构配置文件，支持一键保存与同步测试。

详细规范请参阅 [docs/README.md](docs/README.md)。

## 参考文献
1. *Deep Persona: A Psychologically Grounded Architecture and Evaluation Framework for Role-Playing Agents and Simulations* (Rotem Dror et al., 2026)[https://arxiv.org/abs/2609.22255]
2. *Verifiable Social Reasoning for LLM Assistants* (Amir Taubenfeld, et al., 2026) [https://arxiv.org/abs/2609.17496]