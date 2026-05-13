// ---- Configuration ----
// Change this to your backend API URL when deploying
const API_BASE = window.API_BASE || "http://localhost:8000";

// ---- DOM Elements ----
const uploadArea = document.getElementById("uploadArea");
const fileInput = document.getElementById("fileInput");
const fileInfo = document.getElementById("fileInfo");
const fileName = document.getElementById("fileName");
const btnRemove = document.getElementById("btnRemove");
const jobDesc = document.getElementById("jobDescription");
const btnAnalyze = document.getElementById("btnAnalyze");
const btnReset = document.getElementById("btnReset");
const loading = document.getElementById("loading");
const errorBox = document.getElementById("errorBox");
const results = document.getElementById("results");

let selectedFile = null;

// ---- Upload Handling ----
uploadArea.addEventListener("click", () => fileInput.click());

uploadArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadArea.classList.add("drag-over");
});

uploadArea.addEventListener("dragleave", () => {
    uploadArea.classList.remove("drag-over");
});

uploadArea.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadArea.classList.remove("drag-over");
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFile(files[0]);
});

fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) handleFile(fileInput.files[0]);
});

btnRemove.addEventListener("click", () => {
    clearFile();
});

function handleFile(file) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
        showError("仅支持 PDF 格式的简历文件");
        return;
    }
    if (file.size > 10 * 1024 * 1024) {
        showError("文件大小不能超过 10MB");
        return;
    }
    selectedFile = file;
    fileName.textContent = file.name;
    uploadArea.style.display = "none";
    fileInfo.style.display = "flex";
    btnAnalyze.disabled = false;
    clearResults();
}

function clearFile() {
    selectedFile = null;
    fileInput.value = "";
    uploadArea.style.display = "";
    fileInfo.style.display = "none";
    btnAnalyze.disabled = true;
    clearResults();
}

// ---- Actions ----
btnAnalyze.addEventListener("click", () => {
    if (!selectedFile) return;
    performAnalysis();
});

btnReset.addEventListener("click", () => {
    clearFile();
    jobDesc.value = "";
    clearResults();
});

// ---- API Calls ----
async function performAnalysis() {
    clearResults();
    showLoading(true);

    const formData = new FormData();
    formData.append("file", selectedFile);

    const jd = jobDesc.value.trim();
    let endpoint = `${API_BASE}/api/resume/upload`;
    if (jd) {
        endpoint = `${API_BASE}/api/resume/analyze`;
        formData.append("job_description", jd);
    }

    try {
        const response = await fetch(endpoint, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `服务器错误 (${response.status})`);
        }

        const data = await response.json();
        renderResults(data);
    } catch (err) {
        if (err.message.includes("Failed to fetch") || err.message.includes("NetworkError")) {
            showError("无法连接到后端服务，请确保后端服务已启动");
        } else {
            showError(err.message);
        }
    } finally {
        showLoading(false);
    }
}

// ---- Render ----
function renderResults(data) {
    results.style.display = "block";

    // Basic info
    const info = data.info || {};
    const basicFields = ["name", "phone", "email", "address"];
    const bonusFields = ["job_intent", "expected_salary", "work_years", "education"];

    renderInfoGrid("basicInfo", info, basicFields, {
        name: "姓名",
        phone: "电话",
        email: "邮箱",
        address: "地址",
    });

    // Bonus info
    const hasBonus = bonusFields.some((f) => info[f]);
    if (hasBonus) {
        document.getElementById("bonusSection").style.display = "";
        renderInfoGrid("bonusInfo", info, bonusFields, {
            job_intent: "求职意向",
            expected_salary: "期望薪资",
            work_years: "工作年限",
            education: "学历背景",
        });
    } else {
        document.getElementById("bonusSection").style.display = "none";
    }

    // Projects
    const projects = info.projects || [];
    if (projects.length > 0) {
        document.getElementById("projectsSection").style.display = "";
        const container = document.getElementById("projectsList");
        container.innerHTML = projects
            .map(
                (p) =>
                    `<div class="project-card">
                        <div class="project-name">${esc(p.name || "未命名项目")}</div>
                        <div class="project-desc">${esc(p.description || "")}</div>
                    </div>`
            )
            .join("");
    } else {
        document.getElementById("projectsSection").style.display = "none";
    }

    // Match result
    const match = data.match;
    if (match) {
        document.getElementById("matchSection").style.display = "";

        const overall = Math.round((match.overall_score || 0) * 100);
        const scoreCircle = document.getElementById("scoreCircle");
        document.getElementById("scoreValue").textContent = overall;

        scoreCircle.classList.remove("high", "medium", "low");
        if (overall >= 70) scoreCircle.classList.add("high");
        else if (overall >= 40) scoreCircle.classList.add("medium");
        else scoreCircle.classList.add("low");

        const detailsContainer = document.getElementById("matchDetails");
        const details = [
            { label: "技能匹配率", value: Math.round((match.skill_match_rate || 0) * 100) + "%" },
            { label: "经验相关度", value: Math.round((match.experience_score || 0) * 100) + "%" },
            { label: "学历加分", value: Math.round((match.education_bonus || match.education_score || 0) * 100) + "%" },
        ];

        if (match.analysis) {
            details.push({ label: "AI 分析", value: match.analysis });
        }

        detailsContainer.innerHTML = details
            .map(
                (d) =>
                    `<div class="match-detail-item">
                        <div class="match-detail-label">${d.label}</div>
                        <div class="match-detail-value">${esc(d.value)}</div>
                    </div>`
            )
            .join("");

        // Keywords
        const kwContainer = document.getElementById("matchKeywords");
        let kwHtml = "";

        if (match.matched_skills && match.matched_skills.length > 0) {
            kwHtml += '<h3>已匹配技能</h3><div class="keyword-tags">';
            kwHtml += match.matched_skills
                .map((s) => `<span class="keyword-tag matched">${esc(s)}</span>`)
                .join("");
            kwHtml += "</div>";
        }

        if (match.missing_skills && match.missing_skills.length > 0) {
            kwHtml += '<h3 style="margin-top:12px">缺失技能</h3><div class="keyword-tags">';
            kwHtml += match.missing_skills
                .map((s) => `<span class="keyword-tag missing">${esc(s)}</span>`)
                .join("");
            kwHtml += "</div>";
        }

        if (match.matched_keywords && match.matched_keywords.length > 0) {
            kwHtml += '<h3 style="margin-top:12px">匹配关键词</h3><div class="keyword-tags">';
            kwHtml += match.matched_keywords
                .map((s) => `<span class="keyword-tag matched">${esc(s)}</span>`)
                .join("");
            kwHtml += "</div>";
        }

        if (match.job_keywords && match.job_keywords.length > 0) {
            kwHtml += '<h3 style="margin-top:12px">岗位关键词</h3><div class="keyword-tags">';
            kwHtml += match.job_keywords
                .map((s) => `<span class="keyword-tag keyword">${esc(s)}</span>`)
                .join("");
            kwHtml += "</div>";
        }

        kwContainer.innerHTML = kwHtml;
    } else {
        document.getElementById("matchSection").style.display = "none";
    }

    // Meta
    const cacheLabel = data.cached ? " (缓存命中)" : "";
    document.getElementById("resultMeta").innerHTML =
        `简历ID: ${data.resume_id} | 解析耗时: ${data.parse_time_ms}ms | 文本长度: ${data.raw_text_length}字符${cacheLabel}`;
}

function renderInfoGrid(containerId, info, fields, labels) {
    const container = document.getElementById(containerId);
    container.innerHTML = fields
        .map((f) => {
            const value = info[f];
            const display = value != null ? esc(String(value)) : '<span class="null">未识别</span>';
            return `<div class="info-item">
                        <span class="info-label">${labels[f]}</span>
                        <span class="info-value">${display}</span>
                    </div>`;
        })
        .join("");
}

// ---- Helpers ----
function showLoading(show) {
    loading.style.display = show ? "block" : "none";
}

function showError(msg) {
    errorBox.textContent = msg;
    errorBox.style.display = "block";
    setTimeout(() => {
        errorBox.style.display = "none";
    }, 5000);
}

function clearResults() {
    results.style.display = "none";
    errorBox.style.display = "none";
}

function esc(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}
