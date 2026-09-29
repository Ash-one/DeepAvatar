/**
 * Deep Persona Forge — Creator Studio & Intermediate Artifacts Engine
 */

(function () {
  "use strict";

  // --- State ---
  let currentLang = "zh";
  let currentStoryFile = null;
  let intermediateData = {
    scenes: [],
    evidence_list: [],
    critique_report: null,
  };
  let activeEvidenceFilter = "all";

  // Predefined templates
  const TEMPLATES = {
    alex: {
      id: "alex_intern",
      name: "Alex",
      age: 25,
      role: "规培实习医生 (Medical Intern)",
      scenario_title: "临床差错对质 (Clinical Error Confrontation)",
      scenario_initial_context: "夜班查房时，主任医师拿着一张写错抗生素剂量的医嘱单，快步走入医生办公室，严厉注视着 Alex。值班室气氛骤然紧张。",
      scenario_user_role: "主任医师 (Attending Physician)",
      scenario_persona_role: "规培实习医生 (Alex)",
      communication_style: ["语速迟疑", "紧张时堆砌医学术语", "习惯性使用防御性委婉语"],
      emotional_tone: ["焦虑惶恐", "谨小慎微", "深层自责"],
      observable_behavior: ["不自觉抠白大褂下摆纽扣", "视线在病历夹与地面之间回避", "喉结频繁滚动"],
      beliefs: [
        "高层与科室总是习惯找规培生背锅",
        "承认全部差错可能直接断送规培转正资格与行医前景",
        "主任医师虽然严厉，但也是唯一的专业庇护者"
      ],
      conditional_secrets: [
        {
          id: "exhaustion_secret",
          content: "为了顶替突发急性胃肠炎的同届规培同事，自己在开医嘱前已经连续高强度值班超过 34 小时，当时眼前已出现重影。",
          reveal_if: ["trust >= 0.55"]
        }
      ],
      motivations: ["职业生存", "渴望获得专业认可", "极度害怕犯错被行业驱逐"],
      fears: ["被撤销处方权与规培资格", "同行群体公开羞辱", "彻底断送行医梦想"],
      psychological_needs: ["心理安全感", "获得导师指导而非惩戒", "被视为有潜力的青年医生"],
      behavior_patterns: [
        {
          id: "bp_accusation_superior",
          trigger: { event: "accusation", relationship: "superior" },
          appraisal: ["threat_to_career", "feels_isolated"],
          response_tendencies: { terminology_deflection: 0.8, deferential_apology: 0.6 },
          evidence: ["ev_001"]
        }
      ],
      voice_profile: {
        lexical: { sentence_length: "hesitant_medium", style: "clinical_defensive" },
        discourse: { preferred_patterns: ["apology_then_clinical_rationale"] },
        pragmatic: { directness: 0.45, hedging: 0.65 },
        exemplars: [
          { evidence_id: "ev_001", quote: "主任，我...我记得核对过血肌酐值的，难道是我看错系统更新时间了？" }
        ]
      },
      latent_hypotheses: [
        {
          id: "hyp_imposter_syndrome",
          hypothesis: "严重的冒名顶替综合征与完美主义焦虑",
          description: "将合理的制度疲劳过失内化为个人能力的根本不合格，外在表现为过度顺从与防御交织。",
          confidence: 0.85,
          evidence_for: ["ev_001"],
          evidence_against: []
        }
      ],
      dynamics_config: {
        initial_stage: "guarded",
        baseline: { trust: 0.2, defensiveness: 0.8, engagement: 0.4 }
      }
    },
    xianglin_sao: {
      id: "xianglin_sao",
      name: "祥林嫂",
      age: 42,
      role: "鲁镇鲁四老爷家的女帮工",
      scenario_title: "阿毛之殇的反复倾诉与死后灵魂求证",
      scenario_initial_context: "新年前夕，雪花落在鲁镇石板街上。祥林嫂在街头拦住同乡读书人，两眼直直地瞪着，双手紧抓粗布围裙，颤声打听人死之后究竟有没有灵魂。",
      scenario_user_role: "同乡读书人 (回乡旅人)",
      scenario_persona_role: "祥林嫂",
      communication_style: ["反复絮叨阿毛与狼的故事", "语气怯懦发颤", "急切追问却不敢直视对方"],
      emotional_tone: ["麻木哀绝", "神经质惶恐", "渴望救赎"],
      observable_behavior: ["双手神经质地搓着粗布围裙", "眼角挂着风干的泪痕", "两眼直视前方毫无神采"],
      beliefs: [
        "人死后真的有阎罗地狱和恶鬼索命",
        "阿毛的死全是因为自己没有看好堂屋的门槛",
        "改嫁死后会被阎王锯开分给两个男人"
      ],
      conditional_secrets: [
        {
          id: "threshold_donation",
          content: "自己在土地庙捐了门槛，本以为替自己赎了一世的罪孽，然而祭祀时四婶依然厉声喝止不许她沾手祭器。",
          reveal_if: ["trust >= 0.50"]
        }
      ],
      motivations: ["赎罪渴望", "对阿毛灵魂安息的执念", "在宗法道德压迫下寻得一丝灵魂立足之地"],
      fears: ["死后在地狱被锯开分尸", "阿毛在阴间无人喂食挨冻", "再度被所有人嫌弃驱逐"],
      psychological_needs: ["罪恶感解除", "被同乡视为普通活人接纳"],
      behavior_patterns: [
        {
          id: "bp_soul_inquiry",
          trigger: { event: "meet_intellectual", relationship: "townsman" },
          appraisal: ["fearing_hell_punishment", "desperate_for_reassurance"],
          response_tendencies: { question_about_soul: 0.9, repetitive_remorse: 0.8 },
          evidence: ["ev_001"]
        }
      ],
      voice_profile: {
        lexical: { sentence_length: "short_repetitive", style: "archaic_folk" },
        discourse: { preferred_patterns: ["rhetorical_confession_then_inquiry"] },
        pragmatic: { directness: 0.75, hedging: 0.15 },
        exemplars: [
          { evidence_id: "ev_001", quote: "人死了之后，究竟有没有魂灵的？" }
        ]
      },
      latent_hypotheses: [
        {
          id: "hyp_atonement_obsession",
          hypothesis: "绝望的仪式性赎罪强迫症",
          description: "由于传统封建伦理内化，将所有不幸归咎于自身罪孽，试图通过反复诉说与寻求神灵赦免来减轻剧烈心理崩溃。",
          confidence: 0.95,
          evidence_for: ["ev_001"],
          evidence_against: []
        }
      ],
      dynamics_config: {
        initial_stage: "guarded",
        baseline: { trust: 0.15, defensiveness: 0.75, engagement: 0.6 }
      }
    },
    evelyn: {
      id: "evelyn",
      name: "Evelyn",
      age: 16,
      role: "High School Junior (叛逆高中生)",
      scenario_title: "电子烟被发现后的家庭对质",
      scenario_initial_context: "放学回家后，父母在她的书包夹层里搜出了电子烟与薄荷烟弹，将它们拍在餐桌上。对质在晚饭前瞬间爆发。",
      scenario_user_role: "Parent (父母)",
      scenario_persona_role: "Evelyn (女儿)",
      communication_style: ["语带讽刺", "短句回怼", "频繁使用叹气与翻白眼"],
      emotional_tone: ["防卫戒备", "易怒激惹", "内隐脆弱"],
      observable_behavior: ["双手抱胸倚靠门框", "嚼口香糖不看父母眼睛", "用鞋尖踢踢脚线"],
      beliefs: [
        "父母根本不在乎我的压力，只在乎他们在亲友面前的面子",
        "在学校如果不够酷就会被边缘化",
        "成人的说教全都是虚伪的双重标准"
      ],
      conditional_secrets: [
        {
          id: "peer_pressure_panic",
          content: "自己根本不喜欢吸烟，抽电子烟纯粹是为了不被年级最有权势的闺蜜圈子排挤孤立，而且最近 AP 课程压力大到整夜失眠。",
          reveal_if: ["trust >= 0.60"]
        }
      ],
      motivations: ["同伴认同", "掌控个人界限与自主权", "防御被当作小孩控制的屈辱感"],
      fears: ["被同伴群体排斥成怪人", "失去对个人生活的自主控制", "向父母示弱后被进一步严加管束"],
      psychological_needs: ["平等的同理心倾听", "无条件的被理解感", "个人隐私边界尊重"],
      behavior_patterns: [
        {
          id: "bp_parent_criticism",
          trigger: { event: "accusation", relationship: "parent" },
          appraisal: ["autonomy_threat", "feels_misunderstood"],
          response_tendencies: { sarcasm_deflection: 0.85, emotional_withdrawal: 0.7 },
          evidence: ["ev_001"]
        }
      ],
      voice_profile: {
        lexical: { sentence_length: "terse", style: "colloquial_cynical" },
        discourse: { preferred_patterns: ["rhetorical_challenge", "eye_roll_deflection"] },
        pragmatic: { directness: 0.8, hedging: 0.1 },
        exemplars: [
          { evidence_id: "ev_001", quote: "随便你们怎么想，反正你们从来没真正听过我说话。" }
        ]
      },
      latent_hypotheses: [
        {
          id: "hyp_reactive_autonomy",
          hypothesis: "对抗式自主防御机制 (Reactance & Defensive Autonomy)",
          description: "将父母的关切本能地解释为控制欲侵害，以攻击性冷漠掩饰内心对失去同伴归属感的恐慌。",
          confidence: 0.9,
          evidence_for: ["ev_001"],
          evidence_against: []
        }
      ],
      dynamics_config: {
        initial_stage: "guarded",
        baseline: { trust: 0.2, defensiveness: 0.8, engagement: 0.4 }
      }
    }
  };

  // --- DOM Elements ---
  const el = {
    // Tabs
    tabBtns: document.querySelectorAll(".studio-tab-btn"),
    tabContents: document.querySelectorAll(".studio-tab-content"),
    badgeEvCount: document.getElementById("badge-ev-count"),

    // Header actions
    selectLoadPersona: document.getElementById("select-load-persona"),
    selectTemplate: document.getElementById("select-template"),
    langBtnZh: document.getElementById("lang-btn-zh"),
    langBtnEn: document.getElementById("lang-btn-en"),
    btnExportYaml: document.getElementById("btn-export-yaml"),
    btnSaveOnly: document.getElementById("btn-save-only"),
    btnSaveAndChat: document.getElementById("btn-save-and-chat"),

    // Tab 1: Extraction Inputs
    extractCharName: document.getElementById("extract-char-name"),
    extractCharAliases: document.getElementById("extract-char-aliases"),
    fileDropzone: document.getElementById("file-dropzone"),
    fileInput: document.getElementById("file-input"),
    dropzoneContent: document.getElementById("dropzone-content"),
    fileSelectedBadge: document.getElementById("file-selected-badge"),
    fileSelectedName: document.getElementById("file-selected-name"),
    btnClearFile: document.getElementById("btn-clear-file"),
    extractText: document.getElementById("extract-text"),
    lblCharCount: document.getElementById("lbl-char-count"),
    selectMaxChars: document.getElementById("select-max-chars"),
    btnStartExtract: document.getElementById("btn-start-extract"),
    txtStartExtract: document.getElementById("txt-start-extract"),
    pipelineStepper: document.getElementById("pipeline-stepper"),

    // Tab 1: Intermediate Artifacts
    scenesContainer: document.getElementById("scenes-container"),
    txtScenesCount: document.getElementById("txt-scenes-count"),
    evidenceContainer: document.getElementById("evidence-container"),
    txtEvidenceCount: document.getElementById("txt-evidence-count"),
    btnAddEvidence: document.getElementById("btn-add-evidence"),
    btnRecompileEvidence: document.getElementById("btn-recompile-evidence"),
    filterBtns: document.querySelectorAll(".filter-btn"),

    // Critique Report
    valGroundingRatio: document.getElementById("val-grounding-ratio"),
    critiqueGaugeCircle: document.getElementById("critique-gauge-circle"),
    valGroundedCount: document.getElementById("val-grounded-count"),
    valCalibratedCount: document.getElementById("val-calibrated-count"),
    critiqueContradictionsList: document.getElementById("critique-contradictions-list"),
    critiqueSuggestionsList: document.getElementById("critique-suggestions-list"),
    btnNextToForm: document.getElementById("btn-next-to-form"),

    // Tab 2: Form Inputs
    personaId: document.getElementById("persona-id"),
    personaName: document.getElementById("persona-name"),
    personaAge: document.getElementById("persona-age"),
    personaRole: document.getElementById("persona-role"),
    scenarioTitle: document.getElementById("scenario-title"),
    userRole: document.getElementById("user-role"),
    scenarioContext: document.getElementById("scenario-context"),
    commStyle: document.getElementById("comm-style"),
    emotionalTone: document.getElementById("emotional-tone"),
    observableBehavior: document.getElementById("observable-behavior"),
    patternsContainer: document.getElementById("patterns-container"),
    btnAddPattern: document.getElementById("btn-add-pattern"),
    voiceLength: document.getElementById("voice-length"),
    voiceDirectness: document.getElementById("voice-directness"),
    voiceHedging: document.getElementById("voice-hedging"),
    voiceExemplars: document.getElementById("voice-exemplars"),
    beliefs: document.getElementById("beliefs"),
    secretsContainer: document.getElementById("secrets-container"),
    btnAddSecret: document.getElementById("btn-add-secret"),
    motivations: document.getElementById("motivations"),
    fears: document.getElementById("fears"),
    needs: document.getElementById("needs"),
    hypothesesContainer: document.getElementById("hypotheses-container"),
    btnAddHypothesis: document.getElementById("btn-add-hypothesis"),
    dynTrust: document.getElementById("dyn-trust"),
    dynDefensiveness: document.getElementById("dyn-defensiveness"),
    dynEngagement: document.getElementById("dyn-engagement"),
    btnSyncToYaml: document.getElementById("btn-sync-to-yaml"),

    // Tab 3: YAML Editor
    yamlCodeEditor: document.getElementById("yaml-code-editor"),
    btnYamlFromForm: document.getElementById("btn-yaml-from-form"),
    btnYamlToForm: document.getElementById("btn-yaml-to-form"),
    btnValidateYaml: document.getElementById("btn-validate-yaml"),
    btnCopyYaml: document.getElementById("btn-copy-yaml"),
    yamlStatusText: document.getElementById("yaml-status-text"),

    // Evidence Edit Modal
    modalEvidence: document.getElementById("modal-evidence"),
    modalEvTitle: document.getElementById("modal-ev-title"),
    btnCloseEvModal: document.getElementById("btn-close-ev-modal"),
    btnCancelEvModal: document.getElementById("btn-cancel-ev-modal"),
    btnSaveEvModal: document.getElementById("btn-save-ev-modal"),
    editEvIndex: document.getElementById("edit-ev-index"),
    editEvId: document.getElementById("edit-ev-id"),
    editEvType: document.getElementById("edit-ev-type"),
    editEvSpan: document.getElementById("edit-ev-span"),
    editEvScene: document.getElementById("edit-ev-scene"),
    editEvConf: document.getElementById("edit-ev-conf"),
    editEvSituation: document.getElementById("edit-ev-situation"),
    editEvInterlocutor: document.getElementById("edit-ev-interlocutor"),
    editEvObservation: document.getElementById("edit-ev-observation"),

    // Toast Container
    toastContainer: document.getElementById("toast-container"),
  };

  // --- Toast Notification Helper ---
  function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast-msg toast-${type}`;
    const icon = type === "success" ? "✅" : type === "error" ? "❌" : "ℹ️";
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    el.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(12px)";
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  // --- Tab Navigation ---
  function switchTab(tabId) {
    el.tabBtns.forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === tabId);
    });
    el.tabContents.forEach((sec) => {
      sec.classList.toggle("active", sec.id === tabId);
    });
    if (tabId === "tab-yaml") {
      updateYamlFromForm(false);
    }
  }

  el.tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  if (el.btnNextToForm) {
    el.btnNextToForm.addEventListener("click", () => switchTab("tab-form"));
  }
  if (el.btnSyncToYaml) {
    el.btnSyncToYaml.addEventListener("click", () => switchTab("tab-yaml"));
  }

  // --- File Drag & Drop Handling ---
  function handleSelectedFile(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".txt")) {
      showToast(currentLang === "zh" ? "仅支持上传 .txt 文本文件" : "Only .txt files are supported", "error");
      return;
    }
    currentStoryFile = file;
    el.fileSelectedName.textContent = file.name;
    el.dropzoneContent.classList.add("hidden");
    el.fileSelectedBadge.classList.remove("hidden");
  }

  function clearSelectedFile() {
    currentStoryFile = null;
    el.fileInput.value = "";
    el.dropzoneContent.classList.remove("hidden");
    el.fileSelectedBadge.classList.add("hidden");
  }

  if (el.fileDropzone && el.fileInput) {
    el.fileDropzone.addEventListener("click", (e) => {
      if (e.target !== el.btnClearFile) el.fileInput.click();
    });
    el.fileDropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      el.fileDropzone.classList.add("dragover");
    });
    el.fileDropzone.addEventListener("dragleave", () => el.fileDropzone.classList.remove("dragover"));
    el.fileDropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      el.fileDropzone.classList.remove("dragover");
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleSelectedFile(e.dataTransfer.files[0]);
      }
    });
    el.fileInput.addEventListener("change", () => {
      if (el.fileInput.files && el.fileInput.files.length > 0) {
        handleSelectedFile(el.fileInput.files[0]);
      }
    });
  }

  if (el.btnClearFile) {
    el.btnClearFile.addEventListener("click", (e) => {
      e.stopPropagation();
      clearSelectedFile();
    });
  }

  if (el.extractText && el.lblCharCount) {
    el.extractText.addEventListener("input", () => {
      const len = el.extractText.value.length;
      el.lblCharCount.textContent = currentLang === "zh" ? `${len} 字` : `${len} chars`;
    });
  }

  // --- Stepper UI Update ---
  function setStepperStage(stepNumber) {
    for (let i = 1; i <= 4; i++) {
      const step = document.getElementById(`step-${i}`);
      if (!step) continue;
      step.classList.remove("active", "completed");
      if (i < stepNumber) {
        step.classList.add("completed");
      } else if (i === stepNumber) {
        step.classList.add("active");
      }
    }
  }

  // --- Rendering Intermediate Artifacts ---
  function renderScenes(scenes) {
    el.scenesContainer.innerHTML = "";
    if (!scenes || scenes.length === 0) {
      el.txtScenesCount.textContent = currentLang === "zh" ? "0 幕" : "0 scenes";
      el.scenesContainer.innerHTML = `<div style="color:var(--text-muted);font-size:0.8rem;font-style:italic;">${
        currentLang === "zh" ? "未检测到分幕场景。" : "No scenes detected."
      }</div>`;
      return;
    }

    el.txtScenesCount.textContent = currentLang === "zh" ? `${scenes.length} 幕` : `${scenes.length} scenes`;
    scenes.forEach((sc, idx) => {
      const card = document.createElement("div");
      card.className = "scene-card";
      card.innerHTML = `
        <div class="scene-card-top">
          <span class="scene-badge">Scene ${sc.chapter || idx + 1}</span>
          <span style="font-size:0.7rem; color:var(--text-muted);">${sc.char_count || 0} 字</span>
        </div>
        <div class="scene-title">${escapeHtml(sc.scene || `Scene ${idx + 1}`)}</div>
        <div class="scene-preview">${escapeHtml(sc.text_preview || "")}</div>
      `;
      el.scenesContainer.appendChild(card);
    });
  }

  function renderEvidenceList() {
    const list = intermediateData.evidence_list || [];
    el.evidenceContainer.innerHTML = "";
    el.badgeEvCount.textContent = `${list.length} ${currentLang === "zh" ? "证据" : "ev"}`;
    el.txtEvidenceCount.textContent = `${list.length} ${currentLang === "zh" ? "项证据" : "items"}`;

    const filtered = list.filter((ev) => {
      if (activeEvidenceFilter === "all") return true;
      return ev.type === activeEvidenceFilter;
    });

    if (filtered.length === 0) {
      el.evidenceContainer.innerHTML = `<div style="color:var(--text-muted);font-size:0.8rem;font-style:italic;">${
        currentLang === "zh" ? "暂无匹配的证据条目。" : "No matching evidence items."
      }</div>`;
      return;
    }

    filtered.forEach((ev) => {
      const originalIndex = list.indexOf(ev);
      const card = document.createElement("div");
      card.className = "evidence-card";

      const typeClass = `type-${ev.type || "dialogue"}`;
      const confPercent = Math.round((ev.confidence || 0.8) * 100);
      const quote = ev.source ? ev.source.span || "" : "";
      const sceneTitle = ev.source ? ev.source.scene || `Chapter ${ev.source.chapter || 1}` : "";
      const observation = ev.observation ? ev.observation.speech || ev.observation.behavior || ev.observation.content || "" : "";
      const situation = ev.context ? ev.context.situation || "" : "";
      const interlocutor = ev.context ? ev.context.interlocutor || "" : "";

      card.innerHTML = `
        <div class="evidence-card-top">
          <div class="evidence-meta-left">
            <span class="ev-id-badge">${escapeHtml(ev.id || `ev_${originalIndex + 1}`)}</span>
            <span class="ev-type-badge ${typeClass}">${escapeHtml(ev.type || "dialogue")}</span>
            <span class="ev-source-tag">${escapeHtml(sceneTitle)}</span>
          </div>
          <span style="font-size:0.75rem; font-weight:600; color:var(--accent-emerald);">${confPercent}% 置信</span>
        </div>
        <div class="evidence-card-body">
          ${quote ? `<div class="evidence-span-quote">“${escapeHtml(quote)}”</div>` : ""}
          ${observation ? `<div class="evidence-observation"><strong>观察:</strong> ${escapeHtml(observation)}</div>` : ""}
          ${situation || interlocutor ? `
            <div class="evidence-context-tag" style="margin-top:4px;">
              ${situation ? `<span>情境: ${escapeHtml(situation)}</span>` : ""}
              ${interlocutor ? `<span style="margin-left:8px;">交互者: ${escapeHtml(interlocutor)}</span>` : ""}
            </div>` : ""}
        </div>
        <div class="evidence-card-actions">
          <button type="button" class="btn-ev-action btn-edit-ev" data-index="${originalIndex}">✏️ 编辑</button>
          <button type="button" class="btn-ev-action btn-ev-delete btn-delete-ev" data-index="${originalIndex}">🗑️ 删除</button>
        </div>
      `;
      el.evidenceContainer.appendChild(card);
    });

    // Wire edit & delete buttons
    el.evidenceContainer.querySelectorAll(".btn-edit-ev").forEach((btn) => {
      btn.addEventListener("click", () => openEditEvidenceModal(parseInt(btn.dataset.index, 10)));
    });
    el.evidenceContainer.querySelectorAll(".btn-delete-ev").forEach((btn) => {
      btn.addEventListener("click", () => deleteEvidenceItem(parseInt(btn.dataset.index, 10)));
    });
  }

  function renderCritiqueReport(report) {
    if (!report) {
      el.valGroundingRatio.textContent = "100%";
      el.valGroundedCount.textContent = "0 / 0";
      el.valCalibratedCount.textContent = "0";
      return;
    }

    const ratioPercent = Math.round((report.grounded_ratio || 1.0) * 100);
    el.valGroundingRatio.textContent = `${ratioPercent}%`;
    el.valGroundedCount.textContent = `${report.grounded_hypotheses || 0} / ${report.total_hypotheses || 0}`;
    el.valCalibratedCount.textContent = `${report.calibrated_hypotheses_count || 0}`;

    // Color gauge based on ratio
    if (ratioPercent >= 80) {
      el.critiqueGaugeCircle.style.borderColor = "var(--accent-emerald)";
      el.valGroundingRatio.style.color = "#6ee7b7";
    } else if (ratioPercent >= 50) {
      el.critiqueGaugeCircle.style.borderColor = "var(--accent-amber)";
      el.valGroundingRatio.style.color = "#fde68a";
    } else {
      el.critiqueGaugeCircle.style.borderColor = "var(--accent-rose)";
      el.valGroundingRatio.style.color = "#fda4af";
    }

    // Contradictions list
    el.critiqueContradictionsList.innerHTML = "";
    const contradictions = report.contradictions || [];
    const unsupported = report.unsupported_claims || [];
    if (contradictions.length === 0 && unsupported.length === 0) {
      el.critiqueContradictionsList.innerHTML = `
        <div class="finding-item" style="color: #6ee7b7;">
          ✅ ${currentLang === "zh" ? "未检测到与文本证据相抵触的矛盾论断。" : "No explicit contradictions detected."}
        </div>`;
    } else {
      contradictions.forEach((c) => {
        const item = document.createElement("div");
        item.className = "finding-item";
        item.style.color = "#fda4af";
        item.textContent = `❌ ${c}`;
        el.critiqueContradictionsList.appendChild(item);
      });
      unsupported.forEach((u) => {
        const item = document.createElement("div");
        item.className = "finding-item";
        item.style.color = "#fde68a";
        item.textContent = `⚠️ 未锚定论断: ${u}`;
        el.critiqueContradictionsList.appendChild(item);
      });
    }

    // Suggestions list
    el.critiqueSuggestionsList.innerHTML = "";
    const suggestions = report.suggestions || [];
    if (suggestions.length === 0) {
      el.critiqueSuggestionsList.innerHTML = `
        <div class="finding-item">
          ${currentLang === "zh" ? "当前角色三层架构锚定表现优良，无额外修正建议。" : "Persona grounding is consistent with source evidence."}
        </div>`;
    } else {
      suggestions.forEach((s) => {
        const item = document.createElement("div");
        item.className = "finding-item";
        item.textContent = `💡 ${s}`;
        el.critiqueSuggestionsList.appendChild(item);
      });
    }
  }

  // Filter evidence
  el.filterBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      el.filterBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeEvidenceFilter = btn.dataset.filter;
      renderEvidenceList();
    });
  });

  // --- Evidence Modal Handling ---
  function openEditEvidenceModal(index) {
    el.editEvIndex.value = index;
    if (index >= 0 && intermediateData.evidence_list[index]) {
      const ev = intermediateData.evidence_list[index];
      el.modalEvTitle.textContent = currentLang === "zh" ? `编辑证据 (${ev.id || "ev"})` : `Edit Evidence (${ev.id || "ev"})`;
      el.editEvId.value = ev.id || `ev_${index + 1}`;
      el.editEvType.value = ev.type || "dialogue";
      el.editEvSpan.value = ev.source ? ev.source.span || "" : "";
      el.editEvScene.value = ev.source ? ev.source.scene || "" : "";
      el.editEvConf.value = ev.confidence !== undefined ? ev.confidence : 0.9;
      el.editEvSituation.value = ev.context ? ev.context.situation || "" : "";
      el.editEvInterlocutor.value = ev.context ? ev.context.interlocutor || "" : "";
      el.editEvObservation.value = ev.observation ? ev.observation.speech || ev.observation.behavior || ev.observation.content || "" : "";
    } else {
      // Add new evidence
      const newIdx = intermediateData.evidence_list.length + 1;
      el.modalEvTitle.textContent = currentLang === "zh" ? "添加原子证据 (New Atomic Evidence)" : "Add Atomic Evidence";
      el.editEvId.value = `ev_${String(newIdx).padStart(3, "0")}`;
      el.editEvType.value = "dialogue";
      el.editEvSpan.value = "";
      el.editEvScene.value = "Scene 1";
      el.editEvConf.value = 0.9;
      el.editEvSituation.value = "";
      el.editEvInterlocutor.value = "";
      el.editEvObservation.value = "";
    }
    el.modalEvidence.classList.remove("hidden");
  }

  function closeEditEvidenceModal() {
    el.modalEvidence.classList.add("hidden");
  }

  function saveEvidenceFromModal() {
    const idx = parseInt(el.editEvIndex.value, 10);
    const evItem = {
      id: el.editEvId.value.trim() || `ev_${Date.now()}`,
      type: el.editEvType.value,
      source: {
        chapter: 1,
        scene: el.editEvScene.value.trim() || "Scene 1",
        span: el.editEvSpan.value.trim(),
      },
      context: {
        situation: el.editEvSituation.value.trim(),
        interlocutor: el.editEvInterlocutor.value.trim(),
      },
      observation: {
        speech: el.editEvType.value === "dialogue" ? el.editEvSpan.value.trim() : null,
        behavior: el.editEvType.value === "behavior" ? el.editEvObservation.value.trim() : null,
        content: el.editEvObservation.value.trim() || el.editEvSpan.value.trim(),
      },
      confidence: parseFloat(el.editEvConf.value) || 0.85,
    };

    if (idx >= 0 && idx < intermediateData.evidence_list.length) {
      intermediateData.evidence_list[idx] = evItem;
      showToast(currentLang === "zh" ? `已更新证据 ${evItem.id}` : `Updated evidence ${evItem.id}`, "success");
    } else {
      intermediateData.evidence_list.push(evItem);
      showToast(currentLang === "zh" ? `已添加新证据 ${evItem.id}` : `Added new evidence ${evItem.id}`, "success");
    }

    closeEditEvidenceModal();
    renderEvidenceList();
  }

  function deleteEvidenceItem(index) {
    if (index >= 0 && index < intermediateData.evidence_list.length) {
      const removed = intermediateData.evidence_list.splice(index, 1);
      showToast(currentLang === "zh" ? `已删除证据 ${removed[0].id}` : `Deleted evidence ${removed[0].id}`, "info");
      renderEvidenceList();
    }
  }

  if (el.btnAddEvidence) {
    el.btnAddEvidence.addEventListener("click", () => openEditEvidenceModal(-1));
  }
  if (el.btnCloseEvModal) {
    el.btnCloseEvModal.addEventListener("click", closeEditEvidenceModal);
  }
  if (el.btnCancelEvModal) {
    el.btnCancelEvModal.addEventListener("click", closeEditEvidenceModal);
  }
  if (el.btnSaveEvModal) {
    el.btnSaveEvModal.addEventListener("click", saveEvidenceFromModal);
  }

  // --- Re-compile Persona from Edited Evidence ---
  async function recompileFromEvidence() {
    const list = intermediateData.evidence_list || [];
    if (list.length === 0) {
      showToast(currentLang === "zh" ? "证据库为空，无法推导人格" : "Evidence store is empty", "error");
      return;
    }
    const charName = el.personaName.value.trim() || el.extractCharName.value.trim() || "Character";

    el.btnRecompileEvidence.disabled = true;
    el.btnRecompileEvidence.textContent = currentLang === "zh" ? "⏳ 正在推导..." : "⏳ Compiling...";

    try {
      const res = await fetch("/api/personas/compile-from-evidence", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          character_name: charName,
          evidence_list: list,
          run_llm_critic: false,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Re-compilation failed");
      }

      const data = await res.json();
      intermediateData.critique_report = data.critique_report;
      renderCritiqueReport(data.critique_report);
      populateFormFromData(data.extracted);
      showToast(currentLang === "zh" ? "✅ 已根据当前证据重新归纳三层人格与质检报告！" : "Re-compiled persona from current evidence!", "success");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      el.btnRecompileEvidence.disabled = false;
      el.btnRecompileEvidence.textContent = currentLang === "zh" ? "⚡ 基于当前证据重新归纳" : "⚡ Re-compile from Evidence";
    }
  }

  if (el.btnRecompileEvidence) {
    el.btnRecompileEvidence.addEventListener("click", recompileFromEvidence);
  }

  // --- Dynamic Form Lists (Patterns, Secrets, Hypotheses) ---
  function addPatternRow(pattern = null) {
    const p = pattern || {
      id: `bp_${Date.now()}`,
      trigger: { event: "accusation", relationship: "interlocutor" },
      appraisal: ["threat_appraisal"],
      response_tendencies: { deflection: 0.8 },
      evidence: ["ev_001"],
    };

    const row = document.createElement("div");
    row.className = "dynamic-row pattern-row";
    row.innerHTML = `
      <div style="flex:1; display:grid; grid-template-columns: 140px 140px 1fr 140px; gap:8px;">
        <input type="text" class="text-input p-id" placeholder="模式ID (bp_criticism)" value="${escapeHtml(p.id || "")}">
        <input type="text" class="text-input p-trigger" placeholder="触发事件 (accusation)" value="${escapeHtml(typeof p.trigger === 'object' ? p.trigger.event || '' : p.trigger || '')}">
        <input type="text" class="text-input p-appraisal" placeholder="认知评估标签 (逗号分隔)" value="${escapeHtml(Array.isArray(p.appraisal) ? p.appraisal.join(', ') : '')}">
        <input type="text" class="text-input p-evidence" placeholder="关联证据ID (ev_001)" value="${escapeHtml(Array.isArray(p.evidence) ? p.evidence.join(', ') : '')}">
      </div>
      <button type="button" class="btn-remove-row" title="删除模式">&times;</button>
    `;

    row.querySelector(".btn-remove-row").addEventListener("click", () => row.remove());
    el.patternsContainer.appendChild(row);
  }

  function addSecretRow(secret = null) {
    const s = secret || {
      id: `secret_${Date.now()}`,
      content: "",
      reveal_if: ["trust >= 0.50"],
    };

    const row = document.createElement("div");
    row.className = "dynamic-row secret-row";
    const condStr = Array.isArray(s.reveal_if) ? s.reveal_if.join("; ") : s.reveal_if || "trust >= 0.50";

    row.innerHTML = `
      <div style="flex:1; display:grid; grid-template-columns: 140px 1fr 180px; gap:8px;">
        <input type="text" class="text-input s-id" placeholder="秘密ID (secret_1)" value="${escapeHtml(s.id || "")}">
        <input type="text" class="text-input s-content" placeholder="条件门控秘密正文内容..." value="${escapeHtml(s.content || "")}">
        <input type="text" class="text-input s-cond" placeholder="解锁条件 (trust >= 0.50)" value="${escapeHtml(condStr)}">
      </div>
      <button type="button" class="btn-remove-row" title="删除秘密">&times;</button>
    `;

    row.querySelector(".btn-remove-row").addEventListener("click", () => row.remove());
    el.secretsContainer.appendChild(row);
  }

  function addHypothesisRow(hyp = null) {
    const h = hyp || {
      id: `hyp_${Date.now()}`,
      hypothesis: "",
      description: "",
      confidence: 0.85,
      evidence_for: ["ev_001"],
      evidence_against: [],
    };

    const row = document.createElement("div");
    row.className = "dynamic-row hypothesis-row";
    row.innerHTML = `
      <div style="flex:1; display:grid; grid-template-columns: 120px 180px 1fr 90px 120px; gap:8px;">
        <input type="text" class="text-input h-id" placeholder="假说ID (hyp_atonement)" value="${escapeHtml(h.id || "")}">
        <input type="text" class="text-input h-hyp" placeholder="假说核心概括" value="${escapeHtml(h.hypothesis || "")}">
        <input type="text" class="text-input h-desc" placeholder="心理学内隐机制阐述..." value="${escapeHtml(h.description || "")}">
        <input type="number" class="text-input h-conf" placeholder="置信度" step="0.05" min="0" max="1" value="${h.confidence !== undefined ? h.confidence : 0.85}">
        <input type="text" class="text-input h-evfor" placeholder="证据引用 (ev_001)" value="${escapeHtml(Array.isArray(h.evidence_for) ? h.evidence_for.join(', ') : '')}">
      </div>
      <button type="button" class="btn-remove-row" title="删除假说">&times;</button>
    `;

    row.querySelector(".btn-remove-row").addEventListener("click", () => row.remove());
    el.hypothesesContainer.appendChild(row);
  }

  if (el.btnAddPattern) el.btnAddPattern.addEventListener("click", () => addPatternRow());
  if (el.btnAddSecret) el.btnAddSecret.addEventListener("click", () => addSecretRow());
  if (el.btnAddHypothesis) el.btnAddHypothesis.addEventListener("click", () => addHypothesisRow());

  // --- Populate Visual Form from Data Object ---
  function populateFormFromData(data) {
    if (!data) return;

    if (data.id) el.personaId.value = data.id;
    if (data.name) el.personaName.value = data.name;
    if (data.age !== undefined && data.age !== null) el.personaAge.value = data.age;
    if (data.role) el.personaRole.value = data.role;

    if (data.scenario_title) el.scenarioTitle.value = data.scenario_title;
    if (data.scenario_user_role) el.userRole.value = data.scenario_user_role;
    if (data.scenario_initial_context) el.scenarioContext.value = data.scenario_initial_context;

    // External
    if (data.communication_style) el.commStyle.value = toCommaStr(data.communication_style);
    if (data.emotional_tone) el.emotionalTone.value = toCommaStr(data.emotional_tone);
    if (data.observable_behavior) el.observableBehavior.value = toCommaStr(data.observable_behavior);

    // Behavior patterns
    el.patternsContainer.innerHTML = "";
    const patterns = data.behavior_patterns || (data.external_layer && data.external_layer.behavior_patterns) || [];
    if (patterns.length > 0) {
      patterns.forEach((p) => addPatternRow(p));
    } else {
      addPatternRow();
    }

    // Voice profile
    const vp = data.voice_profile || (data.external_layer && data.external_layer.voice_profile) || {};
    if (vp.lexical) el.voiceLength.value = vp.lexical.style || vp.lexical.sentence_length || "";
    if (vp.pragmatic) {
      if (vp.pragmatic.directness !== undefined) el.voiceDirectness.value = vp.pragmatic.directness;
      if (vp.pragmatic.hedging !== undefined) el.voiceHedging.value = vp.pragmatic.hedging;
    }
    if (vp.exemplars && Array.isArray(vp.exemplars)) {
      el.voiceExemplars.value = vp.exemplars.map((ex) => (typeof ex === "object" ? ex.quote : ex)).join("\n");
    }

    // Middle
    if (data.beliefs) el.beliefs.value = toSemicolonStr(data.beliefs);

    // Conditional secrets
    el.secretsContainer.innerHTML = "";
    const secrets = data.conditional_secrets || (data.middle_layer && data.middle_layer.conditional_information) || [];
    if (secrets.length > 0) {
      secrets.forEach((s) => addSecretRow(s));
    } else {
      addSecretRow();
    }

    // Internal
    if (data.motivations) el.motivations.value = toCommaStr(data.motivations);
    if (data.fears) el.fears.value = toCommaStr(data.fears);
    if (data.psychological_needs) el.needs.value = toCommaStr(data.psychological_needs);

    // Hypotheses
    el.hypothesesContainer.innerHTML = "";
    const hyps = data.latent_hypotheses || (data.internal_layer && data.internal_layer.latent_hypotheses) || [];
    if (hyps.length > 0) {
      hyps.forEach((h) => addHypothesisRow(h));
    } else {
      addHypothesisRow();
    }

    // Dynamics baseline
    const dyn = data.dynamics_config || data.dynamics || {};
    const base = dyn.baseline || dyn;
    if (base.trust !== undefined) el.dynTrust.value = base.trust;
    if (base.defensiveness !== undefined) el.dynDefensiveness.value = base.defensiveness;
    if (base.engagement !== undefined) el.dynEngagement.value = base.engagement;
  }

  // --- Collect Form into JSON Payload ---
  function collectFormData() {
    const parseList = (str, sep = /[,，]/) =>
      str ? str.split(sep).map((s) => s.trim()).filter((s) => s.length > 0) : [];

    // Patterns
    const patterns = [];
    el.patternsContainer.querySelectorAll(".pattern-row").forEach((row) => {
      const pid = row.querySelector(".p-id").value.trim();
      const trig = row.querySelector(".p-trigger").value.trim();
      const appr = parseList(row.querySelector(".p-appraisal").value.trim());
      const evs = parseList(row.querySelector(".p-evidence").value.trim());
      if (pid) {
        patterns.push({
          id: pid,
          trigger: { event: trig || "dialogue", relationship: "interlocutor" },
          appraisal: appr,
          response_tendencies: { default_response: 0.8 },
          evidence: evs,
        });
      }
    });

    // Secrets
    const secrets = [];
    el.secretsContainer.querySelectorAll(".secret-row").forEach((row) => {
      const sid = row.querySelector(".s-id").value.trim();
      const cnt = row.querySelector(".s-content").value.trim();
      const cnd = row.querySelector(".s-cond").value.trim();
      if (sid || cnt) {
        secrets.push({
          id: sid || `secret_${secrets.length + 1}`,
          content: cnt,
          reveal_if: cnd ? [cnd] : ["trust >= 0.50"],
        });
      }
    });

    // Hypotheses
    const hypotheses = [];
    el.hypothesesContainer.querySelectorAll(".hypothesis-row").forEach((row) => {
      const hid = row.querySelector(".h-id").value.trim();
      const hhyp = row.querySelector(".h-hyp").value.trim();
      const hdesc = row.querySelector(".h-desc").value.trim();
      const hconf = parseFloat(row.querySelector(".h-conf").value) || 0.85;
      const hevs = parseList(row.querySelector(".h-evfor").value.trim());
      if (hid || hhyp) {
        hypotheses.push({
          id: hid || `hyp_${hypotheses.length + 1}`,
          hypothesis: hhyp,
          description: hdesc || hhyp,
          confidence: hconf,
          evidence_for: hevs,
          evidence_against: [],
        });
      }
    });

    // Exemplars
    const exemplars = [];
    if (el.voiceExemplars && el.voiceExemplars.value) {
      el.voiceExemplars.value.split("\n").map((s) => s.trim()).filter(Boolean).forEach((quote, idx) => {
        exemplars.push({
          evidence_id: `ev_voice_${idx + 1}`,
          quote: quote,
        });
      });
    }

    const payload = {
      id: el.personaId.value.trim().toLowerCase().replace(/[^a-z0-9_]/g, "_") || "new_persona",
      name: el.personaName.value.trim() || "Character",
      age: parseInt(el.personaAge.value, 10) || 25,
      role: el.personaRole.value.trim() || "Role",
      scenario_title: el.scenarioTitle.value.trim() || "Encounter",
      scenario_initial_context: el.scenarioContext.value.trim() || "The encounter begins.",
      scenario_user_role: el.userRole.value.trim() || "Interlocutor",
      scenario_persona_role: el.personaName.value.trim() || "Character",
      communication_style: parseList(el.commStyle.value),
      emotional_tone: parseList(el.emotionalTone.value),
      observable_behavior: parseList(el.observableBehavior.value),
      beliefs: parseList(el.beliefs.value, /[;；,，]/),
      conditional_secrets: secrets,
      motivations: parseList(el.motivations.value),
      fears: parseList(el.fears.value),
      psychological_needs: parseList(el.needs.value),
      latent_hypotheses: hypotheses,
      behavior_patterns: patterns,
      voice_profile: {
        lexical: { style: el.voiceLength.value.trim() || "standard" },
        discourse: { preferred_patterns: ["direct_reply"] },
        pragmatic: {
          directness: parseFloat(el.voiceDirectness.value) || 0.7,
          hedging: parseFloat(el.voiceHedging.value) || 0.2,
        },
        exemplars: exemplars,
      },
      evidence_index: intermediateData.evidence_list || [],
      dynamics_config: {
        initial_stage: "guarded",
        baseline: {
          trust: parseFloat(el.dynTrust.value) || 0.2,
          defensiveness: parseFloat(el.dynDefensiveness.value) || 0.8,
          engagement: parseFloat(el.dynEngagement.value) || 0.4,
        },
      },
      overwrite: true,
    };

    return payload;
  }

  // --- Two-Way YAML Synchronization ---
  function updateYamlFromForm(notify = true) {
    const data = collectFormData();
    try {
      if (window.jsyaml) {
        const yamlStr = window.jsyaml.dump(data, { indent: 2, lineWidth: -1, noRefs: true });
        el.yamlCodeEditor.value = yamlStr;
      } else {
        el.yamlCodeEditor.value = JSON.stringify(data, null, 2);
      }
      el.yamlStatusText.textContent = currentLang === "zh" ? "✅ 已从表单生成最新 YAML" : "Updated from form";
      el.yamlStatusText.style.color = "#6ee7b7";
      if (notify) showToast(currentLang === "zh" ? "已从表单同步至 YAML" : "Synced form to YAML", "info");
    } catch (err) {
      el.yamlStatusText.textContent = `❌ ${err.message}`;
      el.yamlStatusText.style.color = "#fda4af";
    }
  }

  async function applyYamlToForm() {
    const yamlStr = el.yamlCodeEditor.value.trim();
    if (!yamlStr) {
      showToast(currentLang === "zh" ? "YAML 文本为空" : "YAML text is empty", "error");
      return;
    }

    try {
      // Validate via API first
      const res = await fetch("/api/personas/validate-yaml", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ yaml_content: yamlStr }),
      });
      const result = await res.json();
      if (!result.valid) {
        throw new Error(result.error || "YAML validation failed");
      }

      let parsed = null;
      if (window.jsyaml) {
        parsed = window.jsyaml.load(yamlStr);
      } else {
        parsed = result.config;
      }

      populateFormFromData(parsed);
      if (parsed.evidence_index && Array.isArray(parsed.evidence_index)) {
        intermediateData.evidence_list = parsed.evidence_index;
        renderEvidenceList();
      }

      el.yamlStatusText.textContent = currentLang === "zh" ? "✅ YAML 验证通过并已更新表单" : "YAML validated & applied";
      el.yamlStatusText.style.color = "#6ee7b7";
      showToast(currentLang === "zh" ? "✅ YAML 解析成功并已同步回表单！" : "YAML applied to form!", "success");
    } catch (err) {
      el.yamlStatusText.textContent = `❌ 语法或格式错误: ${err.message}`;
      el.yamlStatusText.style.color = "#fda4af";
      showToast(err.message, "error");
    }
  }

  async function validateYamlOnly() {
    const yamlStr = el.yamlCodeEditor.value.trim();
    if (!yamlStr) {
      showToast(currentLang === "zh" ? "YAML 文本为空" : "YAML text is empty", "error");
      return;
    }

    try {
      const res = await fetch("/api/personas/validate-yaml", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ yaml_content: yamlStr }),
      });
      const result = await res.json();
      if (result.valid) {
        el.yamlStatusText.textContent = currentLang === "zh" ? `✅ 规格合法！角色: ${result.name} (${result.id})` : `Valid persona: ${result.name} (${result.id})`;
        el.yamlStatusText.style.color = "#6ee7b7";
        showToast(currentLang === "zh" ? `✅ YAML 规格校验合法 (角色: ${result.name})` : "YAML specification is valid!", "success");
      } else {
        el.yamlStatusText.textContent = `❌ 校验失败: ${result.error}`;
        el.yamlStatusText.style.color = "#fda4af";
        showToast(`校验失败: ${result.error}`, "error");
      }
    } catch (err) {
      el.yamlStatusText.textContent = `❌ 请求错误: ${err.message}`;
      el.yamlStatusText.style.color = "#fda4af";
      showToast(err.message, "error");
    }
  }

  if (el.btnYamlFromForm) el.btnYamlFromForm.addEventListener("click", () => updateYamlFromForm(true));
  if (el.btnYamlToForm) el.btnYamlToForm.addEventListener("click", applyYamlToForm);
  if (el.btnValidateYaml) el.btnValidateYaml.addEventListener("click", validateYamlOnly);

  if (el.btnCopyYaml) {
    el.btnCopyYaml.addEventListener("click", () => {
      const yamlStr = el.yamlCodeEditor.value;
      if (!yamlStr) return;
      navigator.clipboard.writeText(yamlStr).then(() => {
        showToast(currentLang === "zh" ? "📋 已复制 YAML 规格到剪贴板！" : "Copied YAML to clipboard!", "success");
      });
    });
  }

  // --- Start Evidence-Grounded Extraction Pipeline ---
  async function startExtractionPipeline() {
    const charName = el.extractCharName.value.trim();
    if (!charName) {
      showToast(currentLang === "zh" ? "请输入目标角色姓名！" : "Please enter character name!", "error");
      el.extractCharName.focus();
      return;
    }

    const pasteText = el.extractText ? el.extractText.value.trim() : "";
    if (!currentStoryFile && (!pasteText || pasteText.length < 20)) {
      showToast(currentLang === "zh" ? "请上传 .txt 文件或粘贴至少 20 字的故事正文！" : "Please upload a .txt file or paste narrative text!", "error");
      return;
    }

    el.btnStartExtract.disabled = true;
    el.txtStartExtract.textContent = currentLang === "zh" ? "正在执行多阶段证据抽取..." : "Extracting evidence...";
    setStepperStage(1);

    const formData = new FormData();
    formData.append("character_name", charName);
    if (currentStoryFile) {
      formData.append("file", currentStoryFile);
    } else {
      formData.append("story_text", pasteText);
    }

    try {
      setStepperStage(2);
      const res = await fetch("/api/personas/extract", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Extraction failed");
      }

      setStepperStage(3);
      const data = await res.json();
      const extracted = data.extracted || {};
      const intermediate = data.intermediate || {};

      // 1. Populate Scenes
      intermediateData.scenes = intermediate.scenes || [];
      renderScenes(intermediateData.scenes);

      // 2. Populate Evidence
      intermediateData.evidence_list = intermediate.evidence_list || extracted.evidence_index || [];
      renderEvidenceList();

      // 3. Populate Critique Report
      setStepperStage(4);
      intermediateData.critique_report = intermediate.critique_report || null;
      renderCritiqueReport(intermediateData.critique_report);

      // 4. Fill 3-Layer Form
      populateFormFromData(extracted);

      // 5. Update YAML editor
      updateYamlFromForm(false);

      // Complete Stepper
      for (let i = 1; i <= 4; i++) {
        const step = document.getElementById(`step-${i}`);
        if (step) {
          step.classList.remove("active");
          step.classList.add("completed");
        }
      }

      showToast(currentLang === "zh" ? "🎉 证据提取与三层归纳成功！中间产物已生成。" : "Extraction completed successfully!", "success");
    } catch (err) {
      showToast(err.message, "error");
      setStepperStage(1);
    } finally {
      el.btnStartExtract.disabled = false;
      el.txtStartExtract.textContent = currentLang === "zh" ? "开始证据抽取与三层构建" : "Start Evidence Extraction";
    }
  }

  if (el.btnStartExtract) {
    el.btnStartExtract.addEventListener("click", startExtractionPipeline);
  }

  // --- Save Persona Operations ---
  async function savePersona(launchChat = false) {
    const payload = collectFormData();
    if (!payload.id || !payload.name) {
      showToast(currentLang === "zh" ? "请先填写角色 ID 和角色姓名！" : "Please provide persona ID and name!", "error");
      switchTab("tab-form");
      return;
    }

    try {
      const res = await fetch("/api/personas/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to save persona");
      }

      const result = await res.json();
      showToast(currentLang === "zh" ? `✅ 角色规格 ${result.name} (${result.persona_id}) 保存成功！` : `Persona ${result.name} saved!`, "success");

      // Refresh existing personas dropdown
      loadExistingPersonas();

      if (launchChat) {
        // Navigate to chat studio with selected persona
        setTimeout(() => {
          window.location.href = `/?persona=${encodeURIComponent(result.persona_id)}`;
        }, 500);
      }
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  if (el.btnSaveOnly) {
    el.btnSaveOnly.addEventListener("click", () => savePersona(false));
  }
  if (el.btnSaveAndChat) {
    el.btnSaveAndChat.addEventListener("click", () => savePersona(true));
  }

  // --- Export YAML Download ---
  if (el.btnExportYaml) {
    el.btnExportYaml.addEventListener("click", () => {
      updateYamlFromForm(false);
      const yamlStr = el.yamlCodeEditor.value;
      const personaId = el.personaId.value.trim() || "persona";
      const blob = new Blob([yamlStr], { type: "text/yaml;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${personaId}.yaml`;
      a.click();
      URL.revokeObjectURL(url);
      showToast(currentLang === "zh" ? `已下载 ${personaId}.yaml` : `Downloaded ${personaId}.yaml`, "info");
    });
  }

  // --- Load Existing Persona Dropdown ---
  async function loadExistingPersonas() {
    try {
      const res = await fetch("/api/personas");
      if (!res.ok) return;
      const data = await res.json();
      el.selectLoadPersona.innerHTML = `<option value="">-- ${currentLang === "zh" ? "选择角色" : "Select Persona"} --</option>`;
      (data.personas || []).forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = `${p.name} (${p.id})`;
        el.selectLoadPersona.appendChild(opt);
      });
    } catch (e) {
      // silently ignore
    }
  }

  if (el.selectLoadPersona) {
    el.selectLoadPersona.addEventListener("change", async () => {
      const personaId = el.selectLoadPersona.value;
      if (!personaId) return;

      try {
        const res = await fetch(`/api/personas/${personaId}`);
        if (!res.ok) throw new Error("Failed to load persona");
        const data = await res.json();
        const cfg = data.config || {};

        populateFormFromData(cfg);
        if (cfg.evidence_index && Array.isArray(cfg.evidence_index)) {
          intermediateData.evidence_list = cfg.evidence_index;
          renderEvidenceList();
        }

        if (data.raw_yaml) {
          el.yamlCodeEditor.value = data.raw_yaml;
        } else {
          updateYamlFromForm(false);
        }

        showToast(currentLang === "zh" ? `已成功载入角色: ${cfg.persona?.name || personaId}` : `Loaded ${personaId}`, "success");
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  }

  // --- Predefined Templates ---
  if (el.selectTemplate) {
    el.selectTemplate.addEventListener("change", () => {
      const tKey = el.selectTemplate.value;
      if (!tKey || !TEMPLATES[tKey]) return;
      const t = TEMPLATES[tKey];
      populateFormFromData(t);
      updateYamlFromForm(false);
      showToast(currentLang === "zh" ? `已填入模板: ${t.name}` : `Loaded template: ${t.name}`, "info");
    });
  }

  // --- Language Toggle ---
  function setLanguage(lang) {
    currentLang = lang;
    el.langBtnZh.classList.toggle("active", lang === "zh");
    el.langBtnEn.classList.toggle("active", lang === "en");

    const t = {
      navBack: lang === "zh" ? "返回对话工坊" : "Back to Studio",
      brandSub: lang === "zh" ? "证据驱动的人格归纳、中间产物检验与三层认知编辑系统" : "Evidence-grounded induction, intermediate verification & 3-layer editor",
      loadPersona: lang === "zh" ? "载入已有角色:" : "Load Persona:",
      exportYaml: lang === "zh" ? "导出 YAML" : "Export YAML",
      saveOnly: lang === "zh" ? "保存角色" : "Save Persona",
      saveChat: lang === "zh" ? "保存并开始对话" : "Save & Launch Chat",
      tabExtract: lang === "zh" ? "文本抽取与流水线中间产物" : "Story Extraction & Intermediates",
      tabForm: lang === "zh" ? "三层人格可视化编辑" : "3-Layer Visual Editor",
      tabYaml: lang === "zh" ? "YAML 规格代码与校验" : "YAML Code & Validation",
    };

    document.getElementById("txt-nav-back").textContent = t.navBack;
    document.getElementById("txt-brand-sub").textContent = t.brandSub;
    document.getElementById("lbl-load-persona").textContent = t.loadPersona;
    document.getElementById("txt-export-yaml").textContent = t.exportYaml;
    document.getElementById("txt-save-only").textContent = t.saveOnly;
    document.getElementById("txt-save-chat").textContent = t.saveChat;
    document.getElementById("txt-tab-extract").textContent = t.tabExtract;
    document.getElementById("txt-tab-form").textContent = t.tabForm;
    document.getElementById("txt-tab-yaml").textContent = t.tabYaml;
  }

  el.langBtnZh.addEventListener("click", () => setLanguage("zh"));
  el.langBtnEn.addEventListener("click", () => setLanguage("en"));

  // --- Utility functions ---
  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function toCommaStr(arr) {
    if (!arr || !Array.isArray(arr)) return "";
    return arr.join(", ");
  }

  function toSemicolonStr(arr) {
    if (!arr || !Array.isArray(arr)) return "";
    return arr.join("; ");
  }

  // --- Initial Setup ---
  loadExistingPersonas();

  // Check URL params e.g. /create?load=alex
  const urlParams = new URLSearchParams(window.location.search);
  const loadTarget = urlParams.get("load") || urlParams.get("persona");
  if (loadTarget) {
    setTimeout(() => {
      if (el.selectLoadPersona) {
        el.selectLoadPersona.value = loadTarget;
        el.selectLoadPersona.dispatchEvent(new Event("change"));
      }
    }, 400);
  } else {
    // Default template Alex
    populateFormFromData(TEMPLATES.alex);
  }
})();
