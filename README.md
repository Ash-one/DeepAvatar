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

### 1. 启动交互式 Web 对话工作室 (Web Studio)
```bash
.venv/bin/python scripts/run_web.py --port 8000
```
浏览器打开 `http://127.0.0.1:8000` 即可与角色进行沉浸式文字对话，并在右侧实时查看心理学标量（信任度、防御度、卷入度）、宏观阶段流转（Guarded、Defensive、Cooperative、Reflective）、中层信息解锁状态与真实诊断指标。

### 2. 运行单次多轮模拟与测试
```bash
.venv/bin/python scripts/run_dialogue.py --persona personas/evelyn.yaml --mode deep_external_state --turns 3 --model gemini-2.5-flash
```

### 3. 运行对抗压力测试
```bash
.venv/bin/python scripts/run_stress_test.py --persona personas/evelyn.yaml --mode deep_external_state --model gemini-2.5-flash
```

### 4. 运行批量受控对照实验并评估
```bash
.venv/bin/python scripts/run_batch.py --persona personas/evelyn.yaml --modes flat deep deep_prompt_state deep_external_state --seeds 1 2 3 --turns 5
```

详细规范请参阅 [docs/README.md](docs/README.md)。

## 参考文献
1. *Deep Persona: A Psychologically Grounded Architecture and Evaluation Framework for Role-Playing Agents and Simulations* (Rotem Dror et al., 2026)[https://arxiv.org/abs/2609.22255]
2. *Verifiable Social Reasoning for LLM Assistants* (Amir Taubenfeld, et al., 2026) [https://arxiv.org/abs/2609.17496]