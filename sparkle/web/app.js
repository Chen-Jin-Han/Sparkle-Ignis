const form = document.querySelector("#run-form");
const runButton = document.querySelector("#run-button");
const progress = document.querySelector("#progress");
const resultTitle = document.querySelector("#result-title");
const traceList = document.querySelector("#trace-list");
const report = document.querySelector("#report");
const links = document.querySelector("#artifact-links");
const agents = document.querySelector("#agents");
const deepseekStatus = document.querySelector("#deepseek-status");
const modelStatus = document.querySelector("#model-status");
const metricAgents = document.querySelector("#metric-agents");
const metricSections = document.querySelector("#metric-sections");
const metricArtifacts = document.querySelector("#metric-artifacts");

async function loadStatus() {
  const response = await fetch("/api/status");
  const status = await response.json();
  deepseekStatus.textContent = status.has_deepseek_key ? "已配置" : "未配置";
  modelStatus.textContent = status.deepseek_model || "-";
  renderAgents(status.agents || []);
}

function renderAgents(agentItems) {
  agents.innerHTML = agentItems
    .map(
      (agent) => `
        <div class="agent-card">
          <strong>${escapeHtml(agent.name)}</strong>
          <span>${escapeHtml(agent.role)}</span>
        </div>
      `
    )
    .join("");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setLoading(true);

  const payload = {
    query: document.querySelector("#query").value.trim(),
    max_sections: Number(document.querySelector("#max-sections").value || 6),
    use_deepseek: document.querySelector("#use-deepseek").checked,
  };

  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Sparkle workflow failed");
    }
    renderResult(data);
  } catch (error) {
    resultTitle.textContent = "运行失败";
    report.innerHTML = `<p class="empty-state">${escapeHtml(error.message)}</p>`;
  } finally {
    setLoading(false);
  }
});

function setLoading(isLoading) {
  runButton.disabled = isLoading;
  runButton.textContent = isLoading ? "Sparkle 运行中..." : "启动 Sparkle 工作流";
  progress.classList.toggle("hidden", !isLoading);
}

function renderResult(data) {
  resultTitle.textContent = data.task || "Sparkle 报告";
  const trace = data.agents || [];
  const sections = data.plan?.sections || [];
  const artifacts = data.download_urls || {};

  metricAgents.textContent = trace.length;
  metricSections.textContent = sections.length;
  metricArtifacts.textContent = Object.keys(artifacts).length;

  traceList.innerHTML = trace
    .map(
      (item, index) => `
        <li>
          <strong>${index + 1}. ${escapeHtml(item.agent_name)} · ${escapeHtml(item.role)}</strong>
          <span>${escapeHtml(item.summary)}</span>
        </li>
      `
    )
    .join("");

  links.innerHTML = Object.entries(artifacts)
    .map(
      ([name, url]) => `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${escapeHtml(name)} 下载</a>`
    )
    .join("");

  report.innerHTML = renderMarkdown(data.report || "");

  if (data.deepseek?.requested && !data.deepseek?.enabled) {
    const note = document.createElement("p");
    note.className = "empty-state";
    note.textContent = "已请求 DeepSeek 润色，但容器未检测到 DEEPSEEK_API_KEY，已使用本地工作流结果。";
    report.prepend(note);
  }
}

function renderMarkdown(markdown) {
  const lines = markdown.split(/\r?\n/);
  let html = "";
  let inList = false;
  let tableBuffer = [];

  const flushList = () => {
    if (inList) {
      html += "</ul>";
      inList = false;
    }
  };

  const flushTable = () => {
    if (!tableBuffer.length) return;
    html += "<table>";
    tableBuffer.forEach((row, index) => {
      if (/^\s*\|?\s*:?-{3,}/.test(row)) return;
      const cells = row
        .split("|")
        .map((cell) => cell.trim())
        .filter(Boolean);
      if (!cells.length) return;
      html += "<tr>";
      cells.forEach((cell) => {
        const tag = index === 0 ? "th" : "td";
        html += `<${tag}>${escapeHtml(cell)}</${tag}>`;
      });
      html += "</tr>";
    });
    html += "</table>";
    tableBuffer = [];
  };

  lines.forEach((line) => {
    if (line.trim().startsWith("|")) {
      flushList();
      tableBuffer.push(line);
      return;
    }

    flushTable();

    if (line.startsWith("# ")) {
      flushList();
      html += `<h1>${escapeHtml(line.slice(2))}</h1>`;
    } else if (line.startsWith("## ")) {
      flushList();
      html += `<h2>${escapeHtml(line.slice(3))}</h2>`;
    } else if (line.startsWith("### ")) {
      flushList();
      html += `<h3>${escapeHtml(line.slice(4))}</h3>`;
    } else if (line.startsWith("- ")) {
      if (!inList) {
        html += "<ul>";
        inList = true;
      }
      html += `<li>${escapeHtml(line.slice(2))}</li>`;
    } else if (line.trim()) {
      flushList();
      html += `<p>${escapeHtml(line)}</p>`;
    }
  });

  flushList();
  flushTable();
  return html || '<p class="empty-state">暂无报告内容。</p>';
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

loadStatus().catch(() => {
  deepseekStatus.textContent = "检测失败";
});
