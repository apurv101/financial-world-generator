(() => {
  const state = {
    worlds: [],
    currentWorldId: null,
    payload: null,
    activeView: "explorer",
    selectedNodeId: null,
    nodeSubtab: "overview",
    collapsedNodes: new Set(),
    nodeFilter: "all",
    nodeSearch: "",
    docSource: "story_md",
    readerSearch: "",
    logKindFilter: "all",
    logSearch: "",
    usingServerApi: false,
  };

  // DOM Elements
  const worldSelect = document.getElementById("world-select");
  const refreshBtn = document.getElementById("refresh-btn");
  const fileInput = document.getElementById("file-input");
  const connectionMode = document.getElementById("connection-mode");
  const metricsRibbon = document.getElementById("metrics-ribbon");
  const treeContainer = document.getElementById("tree-container");
  const nodeDetailPane = document.getElementById("node-detail-pane");
  const nodeSearchInput = document.getElementById("node-search");
  const roleFilters = document.getElementById("role-filters");
  const readerContent = document.getElementById("reader-content");
  const tocList = document.getElementById("toc-list");
  const docSourceSwitch = document.getElementById("doc-source-switch");
  const readerSearchInput = document.getElementById("reader-search");
  const logTimelineContainer = document.getElementById("log-timeline-container");
  const obsSummaryStats = document.getElementById("obs-summary-stats");
  const logKindFilters = document.getElementById("log-kind-filters");
  const logSearchInput = document.getElementById("log-search");

  // Escape HTML safely
  function esc(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatNumber(n) {
    return Number(n || 0).toLocaleString();
  }

  // Lightweight Markdown to HTML renderer supporting headings, tables, blockquotes, lists, code, bold
  function renderMarkdown(mdText, assignHeadingIds = false) {
    if (!mdText) return '<div class="empty-state">No content available.</div>';
    const lines = String(mdText).replace(/\r\n/g, "\n").split("\n");
    let html = "";
    let inCode = false;
    let codeLines = [];
    let inList = false;
    let listType = "ul";
    let inBlockquote = false;
    let quoteLines = [];
    let tableLines = [];
    let headingIndex = 0;

    function flushList() {
      if (inList) {
        html += `</${listType}>`;
        inList = false;
      }
    }

    function flushQuote() {
      if (inBlockquote) {
        html += `<blockquote>${quoteLines.map((l) => formatInline(l)).join("<br/>")}</blockquote>`;
        inBlockquote = false;
        quoteLines = [];
      }
    }

    function flushTable() {
      if (tableLines.length > 0) {
        if (tableLines.length >= 2) {
          const headerCells = splitTableRow(tableLines[0]);
          const bodyRows = tableLines.slice(2).map(splitTableRow);
          html += "<table><thead><tr>";
          headerCells.forEach((c) => {
            html += `<th>${formatInline(c)}</th>`;
          });
          html += "</tr></thead><tbody>";
          bodyRows.forEach((row) => {
            html += "<tr>";
            row.forEach((c) => {
              html += `<td>${formatInline(c)}</td>`;
            });
            html += "</tr>";
          });
          html += "</tbody></table>";
        } else {
          tableLines.forEach((l) => {
            html += `<p>${formatInline(l)}</p>`;
          });
        }
        tableLines = [];
      }
    }

    function splitTableRow(rowStr) {
      return rowStr
        .trim()
        .replace(/^\|/, "")
        .replace(/\|$/, "")
        .split("|")
        .map((c) => c.trim());
    }

    function formatInline(text) {
      let s = esc(text);
      s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
      s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
      s = s.replace(/\*([^*]+)\*/g, "<em>$1</em>");
      s = s.replace(
        /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
        '<a href="$2" target="_blank" rel="noopener noreferrer" style="color:var(--accent-blue)">$1</a>'
      );
      return s;
    }

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      if (line.trim().startsWith("```")) {
        flushList();
        flushQuote();
        flushTable();
        if (!inCode) {
          inCode = true;
          codeLines = [];
        } else {
          html += `<pre><code>${esc(codeLines.join("\n"))}</code></pre>`;
          inCode = false;
        }
        continue;
      }

      if (inCode) {
        codeLines.push(line);
        continue;
      }

      // Table detection
      if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
        flushList();
        flushQuote();
        tableLines.push(line);
        continue;
      } else {
        flushTable();
      }

      // Blockquote detection
      if (line.trim().startsWith(">")) {
        flushList();
        inBlockquote = true;
        quoteLines.push(line.trim().replace(/^>\s?/, ""));
        continue;
      } else {
        flushQuote();
      }

      const trimmed = line.trim();
      if (!trimmed) {
        flushList();
        continue;
      }

      // Headings
      const hMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
      if (hMatch) {
        flushList();
        const level = hMatch[1].length;
        const titleText = hMatch[2];
        const idAttr = assignHeadingIds ? ` id=" reader-h-${++headingIndex}" data-level="${level}"` : "";
        html += `<h${level}${idAttr}>${formatInline(titleText)}</h${level}>`;
        continue;
      }

      // Numbered heading style like "1. What this part is"
      const numHeading = trimmed.match(/^([1-9]\d?)\.\s+([A-Z][^.:]{2,70})$/);
      if (numHeading) {
        flushList();
        const idAttr = assignHeadingIds ? ` id="reader-h-${++headingIndex}" data-level="2"` : "";
        html += `<h2${idAttr}>${formatInline(trimmed)}</h2>`;
        continue;
      }

      // Unordered list
      const ulMatch = line.match(/^\s*[-*]\s+(.*)$/);
      if (ulMatch) {
        if (!inList || listType !== "ul") {
          flushList();
          html += "<ul>";
          inList = true;
          listType = "ul";
        }
        html += `<li>${formatInline(ulMatch[1])}</li>`;
        continue;
      }

      // Ordered list
      const olMatch = line.match(/^\s*\d+[.)]\s+(.*)$/);
      if (olMatch) {
        if (!inList || listType !== "ol") {
          flushList();
          html += "<ol>";
          inList = true;
          listType = "ol";
        }
        html += `<li>${formatInline(olMatch[1])}</li>`;
        continue;
      }

      flushList();
      html += `<p>${formatInline(trimmed)}</p>`;
    }

    flushList();
    flushQuote();
    flushTable();
    if (inCode) {
      html += `<pre><code>${esc(codeLines.join("\n"))}</code></pre>`;
    }
    return html;
  }

  // Initialization: try live API first, fall back to prebuilt window.__WORLDGEN_BUNDLE__
  async function init() {
    bindEvents();
    await loadWorldsList();
  }

  async function loadWorldsList() {
    try {
      const resp = await fetch("/api/worlds", { cache: "no-store" });
      if (!resp.ok) throw new Error("API unavailable");
      const data = await resp.json();
      state.worlds = data.worlds || [];
      state.usingServerApi = true;
      connectionMode.textContent = "Live Server Mode (auto-discovers worlds/)";
    } catch {
      const bundle = window.__WORLDGEN_BUNDLE__ || { worlds: [], payloads: {} };
      state.worlds = bundle.worlds || [];
      state.usingServerApi = false;
      connectionMode.textContent = "Static Bundle Mode (offline file:// ready)";
    }

    renderWorldSelector();
    if (state.worlds.length > 0) {
      const targetId = state.currentWorldId && state.worlds.some((w) => w.id === state.currentWorldId)
        ? state.currentWorldId
        : state.worlds[0].id;
      await selectWorld(targetId);
    }
  }

  function renderWorldSelector() {
    worldSelect.innerHTML = state.worlds
      .map(
        (w) =>
          `<option value="${esc(w.id)}">${esc(w.id)} — ${esc(w.title)} (${w.node_count} nodes)</option>`
      )
      .join("");
  }

  async function selectWorld(worldId) {
    state.currentWorldId = worldId;
    worldSelect.value = worldId;

    if (state.usingServerApi) {
      const resp = await fetch(`/api/worlds/${encodeURIComponent(worldId)}`, { cache: "no-store" });
      state.payload = await resp.json();
    } else {
      const bundle = window.__WORLDGEN_BUNDLE__ || { payloads: {} };
      state.payload = bundle.payloads[worldId] || null;
    }

    if (!state.payload) return;

    const tree = state.payload.tree || { root: "n_root", nodes: {} };
    state.selectedNodeId = tree.root || Object.keys(tree.nodes || {})[0] || null;
    state.docSource = state.payload.narrator_output_md ? "narrator_output_md" : "story_md";

    renderMetricsRibbon();
    renderTreeSidebar();
    renderNodeDetail();
    renderReaderView();
    renderObservatoryView();
  }

  function renderMetricsRibbon() {
    const s = state.payload?.summary;
    if (!s) {
      metricsRibbon.innerHTML = "";
      return;
    }
    const statusParts = Object.entries(s.status_counts || {})
      .map(([k, v]) => `${v} ${k}`)
      .join(", ");

    metricsRibbon.innerHTML = `
      <div class="metric-item">
        <span class="metric-label">Folder:</span>
        <span class="metric-value">${esc(s.path)}</span>
      </div>
      <div class="metric-divider"></div>
      <div class="metric-item">
        <span class="metric-label">Nodes:</span>
        <span class="metric-value">${s.node_count} (${s.narrator_count} narrators, ${s.actor_count} actors)</span>
      </div>
      <div class="metric-divider"></div>
      <div class="metric-item">
        <span class="metric-label">Statuses:</span>
        <span class="metric-value">${esc(statusParts)}</span>
      </div>
      <div class="metric-divider"></div>
      <div class="metric-item">
        <span class="metric-label">Story Words:</span>
        <span class="metric-value">${formatNumber(s.story_words)}</span>
      </div>
      ${
        s.llm
          ? `
        <div class="metric-divider"></div>
        <div class="metric-item">
          <span class="metric-label">Model:</span>
          <span class="metric-value">${esc(s.llm)} (${esc(s.effort || "default")})</span>
        </div>
        <div class="metric-divider"></div>
        <div class="metric-item">
          <span class="metric-label">Tokens (In / Cached / Out):</span>
          <span class="metric-value">${formatNumber(s.usage?.input_tokens)} / ${formatNumber(
              s.usage?.cache_read_input_tokens
            )} / ${formatNumber(s.usage?.output_tokens)}</span>
        </div>
      `
          : ""
      }
    `;
  }

  function nodeMatchesFilter(node) {
    if (state.nodeFilter === "narrator" && node.role !== "narrator") return false;
    if (state.nodeFilter === "actor" && node.role !== "actor") return false;
    if (state.nodeFilter === "has-story" && !node.story) return false;
    if (state.nodeFilter === "pending" && node.status !== "pending") return false;

    if (state.nodeSearch) {
      const q = state.nodeSearch.toLowerCase();
      const hay = `${node.id} ${node.name} ${node.prompt || ""} ${node.brief || ""} ${
        node.story || ""
      }`.toLowerCase();
      return hay.includes(q);
    }
    return true;
  }

  function renderTreeSidebar() {
    const tree = state.payload?.tree;
    if (!tree || !tree.nodes) {
      treeContainer.innerHTML = '<div class="empty-state">No tree.json found in this world.</div>';
      return;
    }

    const nodes = tree.nodes;
    const rows = [];

    function walk(nodeId, depth) {
      const node = nodes[nodeId];
      if (!node) return;
      const children = node.children || [];
      const hasChildren = children.length > 0;
      const isCollapsed = state.collapsedNodes.has(nodeId);
      const matches = nodeMatchesFilter(node);

      if (matches) {
        const isSelected = state.selectedNodeId === nodeId;
        const wordCount = node.story ? node.story.trim().split(/\s+/).length : 0;
        const statusBadge =
          node.role === "narrator"
            ? `<span class="badge badge-${esc(node.status)}">${esc(node.status)}</span>`
            : `<span class="badge badge-actor">actor</span>`;

        rows.push(`
          <div class="tree-node-row ${isSelected ? "selected" : ""}" data-node-id="${esc(
          nodeId
        )}" style="padding-left: ${10 + depth * 18}px">
            <div class="tree-node-left">
              ${
                hasChildren
                  ? `<button class="tree-toggle-btn" data-toggle-id="${esc(nodeId)}">${
                      isCollapsed ? "▶" : "▼"
                    }</button>`
                  : `<span class="tree-toggle-btn"></span>`
              }
              <span class="node-icon role-${esc(node.role)}"></span>
              <div class="tree-node-titles">
                <div class="tree-node-name" title="${esc(node.name)}">${esc(node.name)}</div>
                <div class="tree-node-id">${esc(node.id)}${
          hasChildren ? ` · ${children.length} children` : ""
        }</div>
              </div>
            </div>
            <div class="tree-node-badges">
              ${wordCount > 0 ? `<span class="badge badge-words">${formatNumber(wordCount)}w</span>` : ""}
              ${statusBadge}
            </div>
          </div>
        `);
      }

      if (!isCollapsed || state.nodeSearch || state.nodeFilter !== "all") {
        children.forEach((childId) => walk(childId, depth + 1));
      }
    }

    walk(tree.root, 0);
    treeContainer.innerHTML =
      rows.length > 0
        ? rows.join("")
        : '<div class="empty-state">No nodes match your current filter.</div>';
  }

  function getAncestors(nodeId) {
    const nodes = state.payload?.tree?.nodes || {};
    const chain = [];
    let curr = nodes[nodeId];
    while (curr) {
      chain.unshift(curr);
      curr = curr.parent ? nodes[curr.parent] : null;
    }
    return chain;
  }

  function renderNodeDetail() {
    const nodes = state.payload?.tree?.nodes || {};
    const node = nodes[state.selectedNodeId];
    if (!node) {
      nodeDetailPane.innerHTML =
        '<div class="empty-state">Select a node on the left to inspect its story, brief, and prompt.</div>';
      return;
    }

    const ancestors = getAncestors(node.id);
    const children = (node.children || []).map((cid) => nodes[cid]).filter(Boolean);
    const storyWords = node.story ? node.story.trim().split(/\s+/).length : 0;
    const promptWords = node.prompt ? node.prompt.trim().split(/\s+/).length : 0;
    const briefWords = node.brief ? node.brief.trim().split(/\s+/).length : 0;

    const breadcrumbsHtml = ancestors
      .map(
        (a, idx) =>
          `${idx > 0 ? "<span>/</span>" : ""}<button class="breadcrumb-link" data-jump-node="${esc(
            a.id
          )}">${esc(a.name)} (${esc(a.id)})</button>`
      )
      .join("");

    let bodyHtml = "";
    const activeTab = state.nodeSubtab;

    if (activeTab === "overview") {
      if (node.story) {
        bodyHtml += `
          <div class="section-card">
            <div class="section-card-header">
              <h3>Narrator Story (tell_story)</h3>
              <span class="badge badge-words">${formatNumber(storyWords)} words</span>
            </div>
            <div class="markdown-body">${renderMarkdown(node.story)}</div>
          </div>
        `;
      } else if (node.role === "narrator") {
        bodyHtml += `
          <div class="section-card">
            <div class="section-card-header">
              <h3>Narrator Story</h3>
              <span class="badge badge-${esc(node.status)}">${esc(node.status)}</span>
            </div>
            <p class="muted-note">This narrator has not taken its turn yet (status: <code>${esc(
              node.status
            )}</code>). Expand it with <code>uv run --env-file .env worldgen expand &lt;world_dir&gt; ${esc(
          node.id
        )} --depth 1</code>.</p>
          </div>
        `;
      }

      if (node.brief) {
        bodyHtml += `
          <div class="section-card">
            <div class="section-card-header">
              <h3>Current Brief (written by ${esc(node.parent || "root")})</h3>
              <span class="badge badge-words">${formatNumber(briefWords)} words</span>
            </div>
            <div class="markdown-body">${renderMarkdown(node.brief)}</div>
          </div>
        `;
      }

      if (node.prompt) {
        bodyHtml += `
          <div class="section-card">
            <div class="section-card-header">
              <h3>Standing Prompt (Identity &amp; Rules)</h3>
              <span class="badge badge-words">${formatNumber(promptWords)} words</span>
            </div>
            <div class="markdown-body">${renderMarkdown(node.prompt)}</div>
          </div>
        `;
      }

      if (children.length > 0) {
        bodyHtml += renderChildrenSection(children);
      }
    } else if (activeTab === "story") {
      bodyHtml = `
        <div class="section-card">
          <div class="section-card-header">
            <h3>Narrator Story</h3>
            <span class="badge badge-words">${formatNumber(storyWords)} words</span>
          </div>
          <div class="markdown-body">${
            node.story
              ? renderMarkdown(node.story)
              : '<div class="empty-state">No story recorded for this node.</div>'
          }</div>
        </div>
      `;
    } else if (activeTab === "brief_prompt") {
      bodyHtml = `
        <div class="section-card">
          <div class="section-card-header">
            <h3>Current Brief</h3>
            <span class="badge badge-words">${formatNumber(briefWords)} words</span>
          </div>
          <div class="markdown-body">${
            node.brief
              ? renderMarkdown(node.brief)
              : '<div class="empty-state">No brief recorded (root narrator or unbriefed child).</div>'
          }</div>
        </div>
        <div class="section-card">
          <div class="section-card-header">
            <h3>Standing Prompt</h3>
            <span class="badge badge-words">${formatNumber(promptWords)} words</span>
          </div>
          <div class="markdown-body">${renderMarkdown(node.prompt)}</div>
        </div>
      `;
    } else if (activeTab === "children") {
      bodyHtml = renderChildrenSection(children);
    }

    nodeDetailPane.innerHTML = `
      <div class="breadcrumbs">${breadcrumbsHtml}</div>
      <div class="node-header-card">
        <div class="node-header-title">
          <h2>${esc(node.name)}</h2>
          <div class="node-header-meta">
            <span class="badge badge-${esc(node.role)}">${esc(node.role)}</span>
            <span class="badge badge-${esc(node.status)}">status: ${esc(node.status)}</span>
            <span class="badge badge-words">id: ${esc(node.id)}</span>
            ${
              node.parent
                ? `<button class="breadcrumb-link" data-jump-node="${esc(
                    node.parent
                  )}">↑ Parent: ${esc(node.parent)}</button>`
                : ""
            }
          </div>
        </div>
      </div>

      <div class="node-subtabs">
        <button class="node-subtab ${activeTab === "overview" ? "active" : ""}" data-subtab="overview">
          All Sections
        </button>
        ${
          node.story
            ? `<button class="node-subtab ${activeTab === "story" ? "active" : ""}" data-subtab="story">
                Story (${formatNumber(storyWords)}w)
              </button>`
            : ""
        }
        <button class="node-subtab ${
          activeTab === "brief_prompt" ? "active" : ""
        }" data-subtab="brief_prompt">
          Brief &amp; Prompt
        </button>
        ${
          children.length > 0
            ? `<button class="node-subtab ${activeTab === "children" ? "active" : ""}" data-subtab="children">
                Spawned Children (${children.length})
              </button>`
            : ""
        }
      </div>

      ${bodyHtml}
    `;
  }

  function renderChildrenSection(children) {
    if (!children.length) {
      return '<div class="empty-state">This node has no children.</div>';
    }
    const cards = children
      .map(
        (c) => `
        <div class="child-card" data-jump-node="${esc(c.id)}">
          <div class="child-card-top">
            <div>
              <div class="child-card-name">${esc(c.name)}</div>
              <div class="child-card-id">${esc(c.id)}</div>
            </div>
            <div style="display:flex;gap:4px">
              <span class="badge badge-${esc(c.role)}">${esc(c.role)}</span>
              ${
                c.role === "narrator"
                  ? `<span class="badge badge-${esc(c.status)}">${esc(c.status)}</span>`
                  : ""
              }
            </div>
          </div>
          <div class="child-card-snippet">${esc(c.brief || c.prompt || "")}</div>
        </div>
      `
      )
      .join("");

    return `
      <div class="section-card">
        <div class="section-card-header">
          <h3>Spawned Children (${children.length})</h3>
          <span class="muted-note">Click any card to inspect child</span>
        </div>
        <div class="children-grid">${cards}</div>
      </div>
    `;
  }

  // View 2: Full Story Reader
  function renderReaderView() {
    if (!state.payload) return;
    const hasNarratorOut = Boolean(state.payload.narrator_output_md);
    const hasStoryMd = Boolean(state.payload.story_md);

    docSourceSwitch.innerHTML = `
      <div class="filter-pills">
        ${
          hasNarratorOut
            ? `<button class="pill ${
                state.docSource === "narrator_output_md" ? "active" : ""
              }" data-doc="narrator_output_md">narrator_output.md</button>`
            : ""
        }
        ${
          hasStoryMd
            ? `<button class="pill ${
                state.docSource === "story_md" ? "active" : ""
              }" data-doc="story_md">story.md</button>`
            : ""
        }
      </div>
    `;

    const rawMd =
      (state.docSource === "narrator_output_md"
        ? state.payload.narrator_output_md
        : state.payload.story_md) ||
      state.payload.story_md ||
      "";

    readerContent.innerHTML = renderMarkdown(rawMd, true);
    buildReaderToc();
  }

  function buildReaderToc() {
    const headings = Array.from(readerContent.querySelectorAll("h1, h2, h3, h4"));
    const q = state.readerSearch.toLowerCase();
    const items = headings
      .filter((h) => !q || h.textContent.toLowerCase().includes(q))
      .map((h) => {
        const level = h.tagName.toLowerCase().replace("h", "");
        return `<a class="toc-item toc-level-${level}" data-target-id="${esc(h.id)}">${esc(
          h.textContent
        )}</a>`;
      });
    tocList.innerHTML = items.join("");
  }

  // View 3: Observatory (log.jsonl inspector)
  function renderObservatoryView() {
    const entries = state.payload?.log_entries || [];
    const s = state.payload?.summary || {};

    obsSummaryStats.innerHTML = `
      <div class="obs-stat-row"><span>Total Log Events</span><strong>${entries.length}</strong></div>
      <div class="obs-stat-row"><span>LLM Replies</span><strong>${s.llm_calls || 0}</strong></div>
      <div class="obs-stat-row"><span>Tool Calls</span><strong>${s.tool_calls || 0}</strong></div>
      <div class="obs-stat-row"><span>Tool Rejections</span><strong style="color:${
        s.tool_errors ? "var(--accent-red)" : "var(--accent-green)"
      }">${s.tool_errors || 0}</strong></div>
      <div class="obs-stat-row"><span>Input Tokens</span><strong>${formatNumber(
        s.usage?.input_tokens
      )}</strong></div>
      <div class="obs-stat-row"><span>Cached Input Tokens</span><strong>${formatNumber(
        s.usage?.cache_read_input_tokens
      )}</strong></div>
      <div class="obs-stat-row"><span>Output Tokens</span><strong>${formatNumber(
        s.usage?.output_tokens
      )}</strong></div>
    `;

    const q = state.logSearch.toLowerCase();
    const filtered = entries.filter((e) => {
      const k = e.kind;
      if (state.logKindFilter === "llm_reply" && k !== "llm_reply") return false;
      if (state.logKindFilter === "tool_call" && k !== "tool_call") return false;
      if (state.logKindFilter === "errors" && !e.is_error && e.status !== "failed") return false;
      if (
        state.logKindFilter === "lifecycle" &&
        !["run_started", "turn_started", "turn_finished", "run_finished", "reminder_sent"].includes(k)
      ) {
        return false;
      }
      if (q) {
        return JSON.stringify(e).toLowerCase().includes(q);
      }
      return true;
    });

    if (!filtered.length) {
      logTimelineContainer.innerHTML =
        '<div class="empty-state">No log entries match the selected filter.</div>';
      return;
    }

    logTimelineContainer.innerHTML = filtered
      .map((entry, idx) => renderLogEntryCard(entry, idx))
      .join("");
  }

  function renderLogEntryCard(entry, idx) {
    const kind = entry.kind || "event";
    const ts = entry.at ? entry.at.replace("T", " ").replace("+00:00", " UTC") : `#${idx + 1}`;
    const isError = Boolean(entry.is_error || entry.status === "failed");

    if (kind === "llm_reply") {
      const blocks = entry.content || [];
      const thinkingBlocks = blocks.filter((b) => b.type === "thinking" && b.thinking);
      const textBlocks = blocks.filter((b) => b.type === "text" && b.text);
      const toolUses = blocks.filter((b) => b.type === "tool_use");
      const usage = entry.usage || {};

      return `
        <div class="log-card">
          <div class="log-card-header">
            <div class="log-card-left">
              <span class="badge badge-narrator">llm_reply · step ${esc(entry.step)}</span>
              <span class="badge badge-words">node: ${esc(entry.node)}</span>
              <span class="badge badge-told">stop: ${esc(entry.stop_reason)}</span>
              <span class="badge badge-words">in: ${formatNumber(
                usage.input_tokens
              )} · cached: ${formatNumber(usage.cache_read_input_tokens)} · out: ${formatNumber(
        usage.output_tokens
      )}</span>
            </div>
            <span class="log-timestamp">${esc(ts)}</span>
          </div>
          ${thinkingBlocks
            .map(
              (tb) => `
              <details class="thinking-details">
                <summary>Model Reasoning / Thinking Trace (${formatNumber(
                  tb.thinking.split(/\s+/).length
                )} words)</summary>
                <div class="thinking-body">${esc(tb.thinking)}</div>
              </details>
            `
            )
            .join("")}
          ${textBlocks
            .map(
              (tb) => `<div class="markdown-body" style="margin-top:8px">${renderMarkdown(tb.text)}</div>`
            )
            .join("")}
          ${
            toolUses.length
              ? `<div style="margin-top:8px;font-size:12px;color:var(--text-secondary)">Emitted ${
                  toolUses.length
                } tool call(s): ${toolUses
                  .map((u) => `<code>${esc(u.name)}</code>`)
                  .join(", ")}</div>`
              : ""
          }
        </div>
      `;
    }

    if (kind === "tool_call") {
      const inputSummary =
        entry.tool === "tell_story"
          ? `story (${formatNumber((entry.input?.story || "").split(/\s+/).length)} words)`
          : entry.tool === "spawn_child"
          ? `${(entry.input?.items || []).length} children: ${(entry.input?.items || [])
              .map((i) => i.id)
              .join(", ")}`
          : entry.tool === "brief_child"
          ? `child: ${entry.input?.child}`
          : JSON.stringify(entry.input);

      return `
        <div class="log-card ${isError ? "log-error" : ""}">
          <div class="log-card-header">
            <div class="log-card-left">
              <span class="badge ${isError ? "badge-failed" : "badge-actor"}">tool_call · ${esc(
        entry.tool
      )}</span>
              <span class="badge badge-words">step ${esc(entry.step)}</span>
              <span style="font-size:12.5px;color:var(--text-secondary)">${esc(inputSummary)}</span>
            </div>
            <span class="log-timestamp">${esc(ts)}</span>
          </div>
          <div style="font-size:13px;font-weight:500;color:${
            isError ? "var(--accent-red)" : "var(--accent-green)"
          }">${esc(entry.result)}</div>
          <details class="thinking-details" style="margin-top:8px">
            <summary>Inspect Raw Tool Input JSON</summary>
            <div class="tool-io-box">${esc(JSON.stringify(entry.input, null, 2))}</div>
          </details>
        </div>
      `;
    }

    return `
      <div class="log-card ${isError ? "log-error" : ""}">
        <div class="log-card-header">
          <div class="log-card-left">
            <span class="badge badge-leaf">${esc(kind)}</span>
            ${entry.node ? `<span class="badge badge-words">node: ${esc(entry.node)}</span>` : ""}
            ${entry.status ? `<span class="badge badge-${esc(entry.status)}">${esc(entry.status)}</span>` : ""}
          </div>
          <span class="log-timestamp">${esc(ts)}</span>
        </div>
        <div class="tool-io-box">${esc(JSON.stringify(entry, null, 2))}</div>
      </div>
    `;
  }

  function bindEvents() {
    worldSelect.addEventListener("change", (e) => {
      selectWorld(e.target.value);
    });

    refreshBtn.addEventListener("click", () => {
      loadWorldsList();
    });

    // View Tabs
    document.querySelectorAll(".view-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".view-tab").forEach((b) => b.classList.remove("active"));
        document.querySelectorAll(".view-panel").forEach((p) => p.classList.remove("active"));
        btn.classList.add("active");
        state.activeView = btn.dataset.view;
        document.getElementById(`view-${state.activeView}`).classList.add("active");
      });
    });

    // Tree selection & collapse
    treeContainer.addEventListener("click", (e) => {
      const toggleBtn = e.target.closest("[data-toggle-id]");
      if (toggleBtn) {
        e.stopPropagation();
        const tid = toggleBtn.dataset.toggleId;
        if (state.collapsedNodes.has(tid)) {
          state.collapsedNodes.delete(tid);
        } else {
          state.collapsedNodes.add(tid);
        }
        renderTreeSidebar();
        return;
      }

      const row = e.target.closest("[data-node-id]");
      if (row) {
        state.selectedNodeId = row.dataset.nodeId;
        renderTreeSidebar();
        renderNodeDetail();
      }
    });

    // Node detail subtabs & child card jumps
    nodeDetailPane.addEventListener("click", (e) => {
      const jumpBtn = e.target.closest("[data-jump-node]");
      if (jumpBtn) {
        state.selectedNodeId = jumpBtn.dataset.jumpNode;
        state.nodeSubtab = "overview";
        renderTreeSidebar();
        renderNodeDetail();
        nodeDetailPane.scrollTop = 0;
        return;
      }

      const subtabBtn = e.target.closest("[data-subtab]");
      if (subtabBtn) {
        state.nodeSubtab = subtabBtn.dataset.subtab;
        renderNodeDetail();
      }
    });

    // Tree Search & Role filter
    nodeSearchInput.addEventListener("input", (e) => {
      state.nodeSearch = e.target.value.trim();
      renderTreeSidebar();
    });

    roleFilters.addEventListener("click", (e) => {
      const pill = e.target.closest("[data-filter]");
      if (!pill) return;
      roleFilters.querySelectorAll(".pill").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      state.nodeFilter = pill.dataset.filter;
      renderTreeSidebar();
    });

    // Reader TOC & Doc Switch
    docSourceSwitch.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-doc]");
      if (!btn) return;
      state.docSource = btn.dataset.doc;
      renderReaderView();
    });

    readerSearchInput.addEventListener("input", (e) => {
      state.readerSearch = e.target.value.trim();
      buildReaderToc();
    });

    tocList.addEventListener("click", (e) => {
      const item = e.target.closest("[data-target-id]");
      if (!item) return;
      const el = document.getElementById(item.dataset.targetId);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    // Observatory filters
    logKindFilters.addEventListener("click", (e) => {
      const pill = e.target.closest("[data-kind]");
      if (!pill) return;
      logKindFilters.querySelectorAll(".pill").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      state.logKindFilter = pill.dataset.kind;
      renderObservatoryView();
    });

    logSearchInput.addEventListener("input", (e) => {
      state.logSearch = e.target.value.trim();
      renderObservatoryView();
    });

    // Custom File Loader
    fileInput.addEventListener("change", async (e) => {
      const files = Array.from(e.target.files || []);
      if (!files.length) return;
      let customTree = state.payload?.tree || null;
      let customStory = state.payload?.story_md || null;
      let customLog = state.payload?.log_entries || [];

      for (const file of files) {
        const text = await file.text();
        if (file.name.endsWith(".json")) {
          customTree = JSON.parse(text);
        } else if (file.name.endsWith(".jsonl")) {
          customLog = text
            .split(/\r?\n/)
            .filter((l) => l.trim())
            .map((l) => JSON.parse(l));
        } else if (file.name.endsWith(".md")) {
          customStory = text;
        }
      }

      const nodes = customTree?.nodes || {};
      const customId = `custom (${files.map((f) => f.name).join(", ")})`;
      state.payload = {
        summary: {
          id: customId,
          title: customId,
          path: "local file upload",
          node_count: Object.keys(nodes).length,
          narrator_count: Object.values(nodes).filter((n) => n.role === "narrator").length,
          actor_count: Object.values(nodes).filter((n) => n.role === "actor").length,
          status_counts: {},
          story_words: Object.values(nodes).reduce(
            (acc, n) => acc + (n.story ? n.story.split(/\s+/).length : 0),
            0
          ),
        },
        tree: customTree,
        story_md: customStory,
        narrator_output_md: null,
        log_entries: customLog,
      };
      state.selectedNodeId = customTree?.root || Object.keys(nodes)[0] || null;
      renderMetricsRibbon();
      renderTreeSidebar();
      renderNodeDetail();
      renderReaderView();
      renderObservatoryView();
    });
  }

  init();
})();
