/* Worldgen UI — structured like Lumen Metrics Dry Run:
 * One lane runs down the page; when agents start in parallel the page widens and each gets its own lane beside its parent,
 * then the lanes merge back. Each LLM call is three stacked slips: Sent, Model replied, Engine.
 */

let SYSTEM = {};
let TOOLDOC = {};
let TOOLS = { narrator: [], actor: [] };

function applyCodeMetadata(meta) {
  if (!meta) return;
  if (meta.templates && Object.keys(meta.templates).length) {
    SYSTEM = meta.templates;
  }
  if (meta.tooldoc && Object.keys(meta.tooldoc).length) {
    TOOLDOC = meta.tooldoc;
    TOOLS.narrator = Object.keys(TOOLDOC);
  }
}

const POLICY = {
  child_roles: "Controls which child roles a narrator may spawn (from src/worldgen/config.py).",
  list_calls: "Controls whether a failing item in spawn_child rejects the whole call ('all_or_nothing' vs 'partial', from src/worldgen/config.py).",
  unfinished_turn: "Controls whether the loop asks once when a narrator stops before telling its story or briefing all children ('ask_once', from src/worldgen/config.py)."
};

const esc = s => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

function wordCount(s) {
  const t = String(s || "").trim();
  return t ? t.split(/\s+/).length : 0;
}

function tipAttr(key) {
  return ' class="tip" tabindex="0" data-tip="' + esc(key) + '"';
}

function warn(text) {
  return '<span class="warn tip" tabindex="0" role="img" aria-label="Note" data-tip="' + esc("note:" + text) + '">⚠︎</span>';
}

function fmt(s) {
  return esc(s).replace(/`([^`]+)`/g, (m, c) => {
    const k = TOOLDOC[c] ? "tool:" + c : POLICY[c] ? "pol:" + c : CURRENT_NODES[c] ? "node:" + c : null;
    return k ? '<code class="tip" tabindex="0" data-tip="' + esc(k) + '">' + esc(c) + '</code>' : '<code>' + esc(c) + '</code>';
  });
}

function toolCode(u) {
  return '<code' + (TOOLDOC[u] ? ' class="tip" tabindex="0" data-tip="tool:' + esc(u) + '"' : '') + '>' + esc(u) + '</code>';
}

function sysLine(role, toolList) {
  const r = SYSTEM[role] ? role : "narrator";
  const tools = toolList && toolList.length ? toolList : TOOLS[r];
  return (
    '<span>system</span><span><span' + tipAttr("sys:" + r) + '>' + esc(SYSTEM[r].name) + '</span> (cached)</span>' +
    '<span>tools</span><span>' + (tools.length ? '<span' + tipAttr("set:" + r) + '>' + tools.length + ' ' + esc(r) + ' tools</span> (cached)' : 'none') + '</span>'
  );
}

let CURRENT_NODES = {};
let CURRENT_WORLD = null;
let NAV = [];

function nameTip(id) {
  const N = CURRENT_NODES[id];
  if (!N) return '<code>' + esc(id) + '</code>';
  return '<span' + tipAttr("node:" + id) + '>' + esc(N.name || id) + '</span> <code class="tip" tabindex="0" data-tip="node:' + esc(id) + '">' + esc(id) + '</code>';
}

function laneHead(n, labelHtml, role, isNew) {
  return (
    '<div class="lanehead">' +
      '<span class="ln">lane ' + n + '</span>' +
      '<span class="nm">' + labelHtml + '</span>' +
      '<span class="rlc' + (isNew ? ' new' : '') + '">' + esc(role) + '</span>' +
    '</div>'
  );
}

/* ============ FLOW GRID (identical to Lumen Metrics Dry Run.html) ============ */
function Flow(n) {
  this.n = Math.max(1, n);
  this.r = 1;
  this.out = [];
  this.alive = new Array(this.n).fill(null);
}
Flow.prototype.dIdx = function(depth) {
  return Math.min(3, Math.max(0, depth || 0));
};
Flow.prototype.cell = function(col, cls, html, depth) {
  const d = this.dIdx(depth);
  this.out.push(
    '<div class="cell ' + cls + '" style="grid-row:' + this.r + ';grid-column:' + (col + 1) + ';--lc:var(--lane' + d + ')">' +
      (html || "") +
    '</div>'
  );
};
Flow.prototype.rails = function(skip) {
  this.alive.forEach((d, c) => {
    if (d !== null && !skip.includes(c)) this.cell(c, "", null, d);
  });
};
Flow.prototype.head = function(col, depth, html) {
  this.alive[col] = depth;
  this.cell(col, "", html, depth);
  this.rails([col]);
  this.r++;
};
Flow.prototype.card = function(col, html) {
  this.cell(col, "", html, this.alive[col]);
  this.rails([col]);
  this.r++;
};
Flow.prototype.par = function(map) {
  const cols = Object.keys(map).map(Number);
  cols.forEach(c => this.cell(c, "", map[c], this.alive[c]));
  this.rails(cols);
  this.r++;
};
Flow.prototype.fork = function(p, kids, label) {
  if (!kids.length) return;
  const maxc = Math.max(...kids.map(k => k.col));
  const d = this.dIdx(kids[0].depth);
  this.out.push(
    '<div class="conn" style="grid-row:' + this.r + ';grid-column:' + (p + 1) + '/' + (maxc + 2) + ';--lc:var(--lane' + d + ')">' +
      '<span class="lbl">' + fmt(label) + '</span>' +
    '</div>'
  );
  kids.forEach(k => this.cell(k.col, "drop", null, k.depth));
  this.rails(kids.map(k => k.col));
  this.r++;
  kids.forEach(k => {
    this.alive[k.col] = k.depth;
    this.cell(k.col, "", k.head, k.depth);
  });
  this.rails(kids.map(k => k.col));
  this.r++;
};
Flow.prototype.join = function(cols, p, label) {
  if (!cols.length) return;
  const maxc = Math.max(...cols);
  const d = this.dIdx(this.alive[cols[0]]);
  this.out.push(
    '<div class="conn join" style="grid-row:' + this.r + ';grid-column:' + (p + 1) + '/' + (maxc + 2) + ';--lc:var(--lane' + d + ')">' +
      '<span class="lbl">' + fmt(label) + '</span>' +
    '</div>'
  );
  cols.forEach(c => this.cell(c, "rise", null, this.alive[c]));
  this.rails(cols);
  cols.forEach(c => { this.alive[c] = null; });
  this.r++;
};
Flow.prototype.html = function() {
  return '<div class="flow"><div class="grid" style="--n:' + this.n + '">' + this.out.join("") + '</div></div>';
};

/* ============ PARSE LOG.JSONL INTO TURNS & 3-SLIP CALLS ============ */
function buildTurnsFromPayload(payload) {
  const tree = payload.tree || { nodes: {}, root: "n_root" };
  const nodes = tree.nodes || {};
  CURRENT_NODES = nodes;
  const entries = payload.log_entries || [];

  const turnsByNode = {};
  const activeTurnByNode = {};
  let defaultModel = (payload.summary && payload.summary.llm) || "llm";

  entries.forEach(ev => {
    const kind = ev.kind;
    if (kind === "run_started") {
      if (ev.llm) defaultModel = ev.llm;
      return;
    }
    const nid = ev.node;
    if (!nid) return;

    if (kind === "turn_started") {
      const t = {
        node: nid,
        llm: ev.llm || defaultModel,
        tools: ev.tools || ["tell_story", "spawn_child", "brief_child"],
        userMessage: ev.message || "",
        startedAt: ev.at,
        finishedAt: null,
        status: "running",
        reason: null,
        calls: [],
        callsByStep: {}
      };
      if (!turnsByNode[nid]) turnsByNode[nid] = [];
      turnsByNode[nid].push(t);
      activeTurnByNode[nid] = t;
    } else if (kind === "llm_reply") {
      let t = activeTurnByNode[nid];
      if (!t) {
        t = {
          node: nid,
          llm: ev.model || defaultModel,
          tools: ["tell_story", "spawn_child", "brief_child"],
          userMessage: "",
          startedAt: ev.at,
          finishedAt: null,
          status: "running",
          reason: null,
          calls: [],
          callsByStep: {}
        };
        if (!turnsByNode[nid]) turnsByNode[nid] = [];
        turnsByNode[nid].push(t);
        activeTurnByNode[nid] = t;
      }
      const stepNo = ev.step || (t.calls.length + 1);
      const thinkingBlocks = [];
      const textBlocks = [];
      const uses = [];
      (ev.content || []).forEach(block => {
        if (block.type === "thinking" || block.thinking) {
          thinkingBlocks.push(block.thinking || "");
        } else if (block.type === "text" || (block.text && !block.name)) {
          textBlocks.push(block.text || "");
        } else if (block.type === "tool_use" || block.name) {
          uses.push({
            id: block.id,
            name: block.name,
            input: block.input || {}
          });
        }
      });
      const callObj = {
        id: "c-" + nid + "-" + stepNo,
        step: stepNo,
        model: ev.model || t.llm || defaultModel,
        usage: ev.usage || null,
        stop_reason: ev.stop_reason,
        sent: stepNo === 1 ? {
          system: "narrator",
          tools: t.tools,
          user: t.userMessage
        } : null,
        reply: {
          thinking: thinkingBlocks.join("\n\n").trim(),
          text: textBlocks.join("\n\n").trim(),
          uses: uses
        },
        engine: []
      };
      t.calls.push(callObj);
      t.callsByStep[stepNo] = callObj;
    } else if (kind === "tool_call") {
      const t = activeTurnByNode[nid];
      if (!t) return;
      const stepNo = ev.step || t.calls.length || 1;
      let callObj = t.callsByStep[stepNo] || t.calls[t.calls.length - 1];
      if (!callObj) {
        callObj = {
          id: "c-" + nid + "-" + stepNo,
          step: stepNo,
          model: t.llm || defaultModel,
          usage: null,
          sent: stepNo === 1 ? { system: "narrator", tools: t.tools, user: t.userMessage } : null,
          reply: { thinking: "", text: "", uses: [{ name: ev.tool, input: ev.input || {} }] },
          engine: []
        };
        t.calls.push(callObj);
        t.callsByStep[stepNo] = callObj;
      }
      callObj.engine.push(buildEngineToolStep(nid, ev));
    } else if (kind === "turn_finished") {
      const t = activeTurnByNode[nid];
      if (!t) return;
      t.finishedAt = ev.at;
      t.status = ev.status || "done";
      t.reason = ev.reason || null;

      // Mark normal turn end if last call had no tool uses
      const lastCall = t.calls[t.calls.length - 1];
      if (lastCall && (!lastCall.reply.uses || lastCall.reply.uses.length === 0) && lastCall.engine.length === 0) {
        lastCall.engine.push({
          name: "turn ends",
          steps: [["info", "No tool call: narrator turn completed (`status: " + t.status + "`)."]],
          result: null,
          rej: false
        });
      }

      // If turn failed on a subsequent request (e.g. API error after step 1 tool results were sent)
      if (t.status === "failed" && t.reason) {
        const failStep = t.calls.length + 1;
        t.calls.push({
          id: "c-" + nid + "-" + failStep,
          step: failStep,
          model: t.llm || defaultModel,
          usage: null,
          sent: null,
          reply: {
            thinking: "",
            text: "",
            uses: [],
            failedBeforeReply: true
          },
          engine: [{
            name: "API / Engine error",
            steps: [["no", "Turn aborted during step " + failStep + " LLM request."]],
            result: t.reason,
            rej: true
          }]
        });
      }
    }
  });

  return turnsByNode;
}

function buildEngineToolStep(nid, ev) {
  const tool = ev.tool;
  const inp = ev.input || {};
  const isErr = Boolean(ev.is_error);
  const steps = [];

  if (tool === "tell_story") {
    const wc = wordCount(inp.story || "");
    if (isErr) {
      steps.push(["no", "Story validation failed."]);
    } else {
      steps.push(["ok", "Saved `" + wc.toLocaleString() + " words` to `" + nid + ".story` in `tree.json`."]);
    }
  } else if (tool === "spawn_child") {
    const items = Array.isArray(inp.items) ? inp.items : [];
    const narrs = items.filter(x => x.role === "narrator");
    const acts = items.filter(x => x.role === "actor");
    if (isErr) {
      steps.push(["no", "Rejected `" + items.length + "` items under `list_calls` / `child_roles` policy."]);
      steps.push(["info", "All-or-nothing check: no children were added by this call."]);
    } else {
      steps.push(["ok", "`" + items.length + "` items validated (policy `list_calls`, `child_roles`)."]);
      if (narrs.length) {
        steps.push(["info", "Spawned sub-narrator" + (narrs.length > 1 ? "s" : "") + ": " + narrs.map(x => "`" + x.id + "` (" + x.name + ")").join(", ") + " — will open parallel lane" + (narrs.length > 1 ? "s" : "") + "."]);
      }
      if (acts.length) {
        steps.push(["info", "Spawned actor" + (acts.length > 1 ? "s" : "") + ": " + acts.map(x => "`" + x.id + "` (" + x.name + ")").join(", ") + " — parent `" + nid + "`, waiting for `brief_child`."]);
      }
    }
  } else if (tool === "brief_child") {
    const cid = inp.child || "";
    const wc = wordCount(inp.brief || "");
    if (isErr) {
      steps.push(["no", "Rejected brief for `" + cid + "`."]);
    } else {
      const cnode = CURRENT_NODES[cid];
      const role = cnode ? cnode.role : "child";
      steps.push(["ok", "`" + cid + "` is a child of `" + nid + "`; saved brief (`" + wc + " words`)."]);
      steps.push(["info", "Data flow `" + nid + " → " + cid + "`: status becomes `" + (role === "narrator" ? "pending (ready for parallel narrator wave)" : "ready (briefed for Day 1)") + "`."]);
    }
  } else {
    steps.push([isErr ? "no" : "ok", "Executed `" + tool + "`."]);
  }

  return {
    name: tool,
    steps: steps,
    result: ev.result != null ? String(ev.result) : null,
    rej: isErr
  };
}

/* ============ RENDER 3 SLIPS (Sent / Model replied / Engine) ============ */
function formatTokensLine(usage) {
  if (!usage) return "";
  const inp = Number(usage.input_tokens || 0);
  const cache = Number(usage.cache_read_input_tokens || 0);
  const out = Number(usage.output_tokens || 0);
  const parts = [];
  if (inp) parts.push(inp.toLocaleString() + " in");
  if (cache) parts.push(cache.toLocaleString() + " cached");
  if (out) parts.push(out.toLocaleString() + " out");
  return parts.length ? '<span>tokens</span><span>' + esc(parts.join(" · ")) + '</span>' : "";
}

function sentHTML(call, prev, parentId) {
  const modelLabel = esc(call.model || "llm");
  if (call.sent) {
    const s = call.sent;
    const fromLabel = parentId ? 'user (prompt &amp; brief from ' + esc(parentId) + ')' : 'user (initial world prompt)';
    const msgText = s.user || "";
    const isLong = msgText.length > 750;
    const msgBlock = isLong
      ? '<details><summary>Read full prompt &amp; brief sent (' + wordCount(msgText) + ' words)</summary><pre>' + esc(msgText) + '</pre></details><pre>' + esc(msgText.slice(0, 620) + "\n… [expand above for full text]") + '</pre>'
      : '<pre>' + esc(msgText) + '</pre>';
    return (
      '<div class="slip sent">' +
        '<span class="lab">Sent to ' + modelLabel + '</span>' +
        '<div class="kv">' +
          sysLine(s.system, s.tools) +
          '<span>messages</span><span>1: user' + (parentId ? ' (from <code>' + esc(parentId) + '</code>)' : '') + '</span>' +
          formatTokensLine(call.usage) +
        '</div>' +
        '<span class="who">' + fromLabel + '</span>' +
        msgBlock +
      '</div>'
    );
  }
  if (!prev) return "";
  const uses = (prev.reply.uses || []).map(u => u.name);
  const res = (prev.engine || []).filter(e => e.result != null);
  return (
    '<div class="slip sent">' +
      '<span class="lab">Sent to ' + modelLabel + '</span>' +
      '<div class="kv">' +
        '<span>request</span><span>the previous request plus 2 messages</span>' +
        formatTokensLine(call.usage) +
      '</div>' +
      '<span class="who">assistant (previous reply)</span>' +
      '<span class="said">' +
        (prev.reply.text ? '"' + fmt(prev.reply.text) + '" ' : '') +
        (uses.length ? '+ tool_use: ' + uses.map(toolCode).join(", ") : '') +
      '</span>' +
      '<span class="who">user (tool results returned by engine)</span>' +
      '<pre>' + esc(res.map((r, i) => '[' + (i + 1) + '] ' + r.name + ': ' + r.result).join("\n")) + '</pre>' +
    '</div>'
  );
}

function formatToolUseInput(u) {
  if (u.name === "tell_story" && u.input && typeof u.input.story === "string") {
    const story = u.input.story;
    const wc = wordCount(story);
    const previewLines = story.split("\n").filter(Boolean).slice(0, 4).join("\n");
    return (
      '<details>' +
        '<summary>story markdown (' + wc.toLocaleString() + ' words) — click to expand full story</summary>' +
        '<pre style="max-height:460px">' + esc(story) + '</pre>' +
      '</details>' +
      '<pre>' + esc(previewLines + "\n… [" + wc.toLocaleString() + " words total]") + '</pre>'
    );
  }
  if (u.name === "spawn_child" && u.input && Array.isArray(u.input.items)) {
    const items = u.input.items;
    const summaryLines = items.map(it =>
      `• ${it.id} (${it.role}) — ${it.name || it.id}: "${String(it.prompt || "").slice(0, 110)}…"`
    ).join("\n");
    return (
      '<pre>' + esc(summaryLines) + '</pre>' +
      '<details>' +
        '<summary>full spawn_child JSON (' + items.length + ' children with full prompts)</summary>' +
        '<pre>' + esc(JSON.stringify(u.input, null, 2)) + '</pre>' +
      '</details>'
    );
  }
  if (u.name === "brief_child" && u.input) {
    const cid = u.input.child || "";
    const brief = String(u.input.brief || "");
    return (
      '<pre>child: ' + esc(cid) + '\nbrief: ' + esc(brief) + '</pre>'
    );
  }
  return '<pre>' + esc(JSON.stringify(u.input, null, 2)) + '</pre>';
}

function replyHTML(r) {
  if (r.failedBeforeReply) {
    return (
      '<div class="slip reply">' +
        '<span class="lab">Model replied</span>' +
        '<span class="muted" style="font-size:.8rem">No reply received — request failed before completion.</span>' +
      '</div>'
    );
  }
  let h = '<div class="slip reply"><span class="lab">Model replied</span>';
  if (r.thinking) {
    const twc = wordCount(r.thinking);
    h += (
      '<details>' +
        '<summary>thinking trace (' + twc.toLocaleString() + ' words)</summary>' +
        '<pre>' + esc(r.thinking) + '</pre>' +
      '</details>'
    );
  }
  if (r.text) {
    h += '<p class="said">"' + fmt(r.text) + '"</p>';
  }
  (r.uses || []).forEach(u => {
    const tAttr = TOOLDOC[u.name] ? tipAttr("tool:" + u.name) : "";
    let targetBadge = "";
    if (u.name === "brief_child" && u.input && u.input.child) {
      targetBadge = ' → <code class="tip" tabindex="0" data-tip="node:' + esc(u.input.child) + '">' + esc(u.input.child) + '</code>';
    } else if (u.name === "spawn_child" && u.input && Array.isArray(u.input.items)) {
      targetBadge = ' (' + u.input.items.length + ' children)';
    }
    h += '<span class="use-name">tool_use → <span' + tAttr + '>' + esc(u.name) + '</span>' + targetBadge + '</span>';
    h += formatToolUseInput(u);
  });
  if (!(r.uses || []).length) {
    h += '<span class="muted" style="font-size:.8rem">No tool call: the turn ends.</span>';
  }
  return h + '</div>';
}

function engineHTML(eng) {
  if (!eng || !eng.length) return "";
  let h = '<div class="slip engine"><span class="lab">Engine</span>';
  eng.forEach(t => {
    const tn = t.name;
    h += (
      '<div class="tool">' +
        '<span class="tool-name">' + (TOOLDOC[tn] ? '<span' + tipAttr("tool:" + tn) + '>' + esc(tn) + '</span>' : esc(tn)) + '</span>' +
        '<ul class="steps">' +
          (t.steps || []).map(s => '<li class="' + esc(s[0]) + '"><span>' + fmt(s[1]) + '</span></li>').join("") +
        '</ul>' +
        (t.result != null
          ? '<div class="result' + (t.rej ? ' rej' : '') + '"><b>returned to the model</b>' + esc(t.result).replace(/\n/g, "<br>") + '</div>'
          : '') +
      '</div>'
    );
  });
  return h + '</div>';
}

function callsHTML(calls, parentId) {
  return calls.map((c, i) => {
    const hasRej = (c.engine || []).some(e => e.rej);
    return (
      '<div class="call" id="' + esc(c.id) + '">' +
        '<span class="call-no">Call ' + (i + 1) + ' of ' + calls.length +
          (hasRej ? ' ' + warn("Rejected tool call or error in this step — see Engine slip below.") : '') +
        '</span>' +
        sentHTML(c, i ? calls[i - 1] : null, parentId) +
        replyHTML(c.reply) +
        engineHTML(c.engine) +
      '</div>'
    );
  }).join("");
}

function summarizeTurn(id, turn) {
  const N = CURRENT_NODES[id] || {};
  const kids = N.children || [];
  const narrKids = kids.filter(k => CURRENT_NODES[k] && CURRENT_NODES[k].role === "narrator");
  const actKids = kids.filter(k => !CURRENT_NODES[k] || CURRENT_NODES[k].role !== "narrator");
  const storyWords = wordCount(N.story || "");
  const parts = [];
  if (storyWords) parts.push("Writes its `" + storyWords.toLocaleString() + "-word` story");
  if (narrKids.length && actKids.length) {
    parts.push("spawns `" + narrKids.length + "` sub-narrator" + (narrKids.length > 1 ? "s" : "") + " (" + narrKids.map(k => "`" + k + "`").join(", ") + ") and `" + actKids.length + "` actor" + (actKids.length > 1 ? "s" : ""));
  } else if (narrKids.length) {
    parts.push("spawns `" + narrKids.length + "` sub-narrator" + (narrKids.length > 1 ? "s" : "") + " (" + narrKids.map(k => "`" + k + "`").join(", ") + ")");
  } else if (actKids.length) {
    parts.push("spawns `" + actKids.length + "` actor" + (actKids.length > 1 ? "s" : "") + " (" + actKids.slice(0, 5).map(k => "`" + k + "`").join(", ") + (actKids.length > 5 ? ", …" : "") + ")");
  }
  const briefedCount = kids.filter(k => CURRENT_NODES[k] && CURRENT_NODES[k].brief).length;
  if (briefedCount) {
    parts.push("briefs `" + briefedCount + "` of `" + kids.length + "` children");
  }
  if (turn && turn.status === "failed") {
    parts.push("stopped early on step " + turn.calls.length + " (`status: failed`)");
  }
  return parts.length ? parts.join(", ") + "." : "Runs narrator turn.";
}

function turnCard(flowId, id, turn, label, suffix, navLabel) {
  const N = CURRENT_NODES[id] || { name: id, role: "narrator" };
  const cid = "t-" + flowId + "-" + id + (suffix || "");
  if (navLabel !== false) NAV.push([cid, navLabel || (N.name + " (" + id + ")"), flowId]);
  const statusCls = turn && turn.status === "done" ? "ok" : turn && turn.status === "failed" ? "bad" : "warn";
  const roleBadge = label || (N.role + " · " + (turn ? turn.status : N.status));
  const sumText = summarizeTurn(id, turn);

  let bodyHtml = "";
  if (turn && turn.calls && turn.calls.length) {
    bodyHtml = callsHTML(turn.calls, N.parent);
  } else {
    // Fallback if log.jsonl has no turn for this narrator
    bodyHtml = (
      '<div class="call">' +
        '<span class="call-no">State in tree.json (no turn in log.jsonl)</span>' +
        '<div class="slip sent">' +
          '<span class="lab">Received from ' + esc(N.parent || "parent") + '</span>' +
          '<span class="who">prompt</span><pre>' + esc(N.prompt || "—") + '</pre>' +
          '<span class="who">brief</span><pre>' + esc(N.brief || "No brief written yet.") + '</pre>' +
        '</div>' +
        (N.story ? '<div class="slip reply"><span class="lab">Story on node</span><pre>' + esc(N.story) + '</pre></div>' : '') +
      '</div>'
    );
  }

  return (
    '<article class="card" id="' + esc(cid) + '">' +
      '<div class="card-head">' +
        '<h3>' + nameTip(id) + '</h3>' +
        '<span class="role ' + statusCls + '">' + esc(roleBadge) + '</span>' +
      '</div>' +
      '<p class="sumline">' + fmt(sumText) + '</p>' +
      bodyHtml +
    '</article>'
  );
}

function actorsGroupCard(flowId, parentId, actorIds, titleLabel) {
  const cid = "actors-" + flowId + "-" + parentId;
  NAV.push([cid, titleLabel || (actorIds.length + " actors from " + parentId), flowId]);

  let h = (
    '<article class="card" id="' + esc(cid) + '">' +
      '<div class="card-head">' +
        '<h3>' + esc(actorIds.length + " actor" + (actorIds.length > 1 ? "s" : "") + " spawned by ") + '<code>' + esc(parentId) + '</code></h3>' +
        '<span class="role">leaf actors · data received</span>' +
      '</div>' +
      '<p class="sumline">' +
        'Actors do not run on Day 0; they receive their standing <code>prompt</code> and chapter <code>brief</code> from <code>' + esc(parentId) + '</code> and wait for Day 1. Expand any actor to inspect the exact prompt and brief passed down.' +
      '</p>'
  );

  actorIds.forEach(aid => {
    const A = CURRENT_NODES[aid] || { name: aid, role: "actor", status: "unknown" };
    const hasBrief = Boolean(A.brief);
    h += (
      '<div class="idle-row" id="node-card-' + esc(aid) + '">' +
        '<span class="nm">' +
          nameTip(aid) +
          '<small>' + esc(A.role) + ' · status: ' + esc(A.status) + (hasBrief ? ' · briefed ✓' : ' · unbriefed ✗') + '</small>' +
        '</span>' +
        '<span>' +
          '<span class="flow-tag">' + esc(parentId) + ' → ' + esc(aid) + '</span>' +
          '<span class="said">"' + esc((A.prompt || "").slice(0, 115)) + (String(A.prompt || "").length > 115 ? '…"' : '"') + '</span>' +
          '<details>' +
            '<summary>prompt &amp; brief received from ' + esc(parentId) + '</summary>' +
            '<span class="who">standing prompt (from spawn_child)</span>' +
            '<pre>' + esc(A.prompt || "—") + '</pre>' +
            '<span class="who">chapter brief (from brief_child)</span>' +
            '<pre>' + esc(A.brief || "No brief written yet (parent turn ended before brief_child).") + '</pre>' +
          '</details>' +
        '</span>' +
      '</div>'
    );
  });

  return h + '</article>';
}

/* ============ BUILD MULTI-LANE DAY 0 FLOW FOR ANY WORLD ============ */
function buildWorldFlow(payload, turnsByNode) {
  const tree = payload.tree || { root: "n_root", nodes: {} };
  const nodes = tree.nodes || {};
  const rootId = tree.root || "n_root";
  const rootNode = nodes[rootId] || { name: "Root narrator", role: "narrator", children: [] };
  const rootKids = rootNode.children || [];
  const childNarrators = rootKids.filter(k => nodes[k] && nodes[k].role === "narrator");
  const rootActors = rootKids.filter(k => !nodes[k] || nodes[k].role !== "narrator");

  // Calculate total columns needed:
  // Col 0: Root narrator (Lane 1)
  // Col 1..M: Each child narrator gets its own parallel lane!
  // Col M+1: Leaf actors spawned directly by root (if any) get a lane beside the child narrators.
  const totalCols = 1 + childNarrators.length + (rootActors.length > 0 ? 1 : 0);
  const F = new Flow(totalCols);

  // Phase 1: ONLY Root narrator in Lane 1 at the top! Empty space to the right.
  const rootTurn = (turnsByNode[rootId] || [])[0] || null;
  F.head(0, 0, laneHead(1, nameTip(rootId), "narrator · root"));
  F.card(0, turnCard("day0", rootId, rootTurn, "① root build", "-1", "Root narrator (" + rootId + ")"));

  // Phase 2: If root spawned children, fork horizontally from Col 0 across the parallel lanes!
  if (childNarrators.length > 0 || rootActors.length > 0) {
    const forkKids = [];
    let colIdx = 1;
    const childNarrCols = {};

    childNarrators.forEach(cnId => {
      childNarrCols[cnId] = colIdx;
      forkKids.push({
        col: colIdx,
        depth: 1,
        id: cnId,
        kind: "narrator",
        head: laneHead(colIdx + 1, nameTip(cnId), "narrator · spawned by " + rootId)
      });
      colIdx++;
    });

    let rootActorsCol = null;
    if (rootActors.length > 0) {
      rootActorsCol = colIdx;
      forkKids.push({
        col: colIdx,
        depth: 2,
        kind: "actors",
        head: laneHead(colIdx + 1, esc(rootActors.length + " direct actors"), "actors · spawned by " + rootId)
      });
      colIdx++;
    }

    const forkDescParts = [];
    if (childNarrators.length > 0) {
      forkDescParts.push(
        "`" + rootId + "` spawns & briefs " + childNarrators.length + " child narrator" +
        (childNarrators.length > 1 ? "s (" + childNarrators.map(x => "`" + x + "`").join(", ") + ") — they start in parallel lanes and can't see each other" : " (`" + childNarrators[0] + "`)")
      );
    }
    if (rootActors.length > 0) {
      forkDescParts.push(
        rootActors.length + " actor" + (rootActors.length > 1 ? "s" : "") + " receive their prompts & briefs and wait for Day 1"
      );
    }
    F.fork(0, forkKids, forkDescParts.join("; ") + ".");

    // Parallel row: all child narrators run their turns at the same time in their respective columns,
    // while rootActorsCol shows the direct actors card.
    const parMap = {};
    childNarrators.forEach(cnId => {
      const cnTurn = (turnsByNode[cnId] || [])[0] || null;
      const c = childNarrCols[cnId];
      parMap[c] = turnCard("day0", cnId, cnTurn, "② parallel build", "-2", (nodes[cnId].name || cnId) + " (" + cnId + ")");
    });
    if (rootActorsCol !== null) {
      parMap[rootActorsCol] = actorsGroupCard("day0", rootId, rootActors, rootActors.length + " actors (" + rootId + ")");
    }
    F.par(parMap);

    // Phase 3: If any child narrator spawned grandchildren (e.g., n_engineering -> n_dan, n_sam),
    // show the grandchildren handoff cards directly in each child narrator's lane!
    const grandParMap = {};
    let hasGrandchildren = false;
    childNarrators.forEach(cnId => {
      const gKids = (nodes[cnId] && nodes[cnId].children) || [];
      if (gKids.length > 0) {
        hasGrandchildren = true;
        const c = childNarrCols[cnId];
        grandParMap[c] = actorsGroupCard("day0", cnId, gKids, gKids.length + " children of " + cnId);
      }
    });
    if (hasGrandchildren) {
      F.par(grandParMap);
    }

    // Join all opened child lanes back into Lane 1 (Root / Manifest)
    const allOpenedCols = forkKids.map(k => k.col);
    F.join(
      allOpenedCols,
      0,
      "All parallel branches merge back into the world manifest (`tree.json` + `narrator_output.md`)."
    );
  }

  return F.html();
}

/* ============ ASCII TREE & MANIFEST CARD ============ */
function buildAsciiTree(tree) {
  const nodes = (tree && tree.nodes) || {};
  const rootId = (tree && tree.root) || "n_root";
  if (!nodes[rootId]) return "";
  const lines = [];

  function walk(nid, prefix, isLast, isRoot) {
    const n = nodes[nid] || { id: nid, name: nid, role: "?" };
    const wc = wordCount(n.story || "");
    const statusStr = n.status ? " [" + n.status + "]" : "";
    const storyStr = wc ? " · story: " + wc.toLocaleString() + "w" : "";
    const briefStr = n.brief ? " · briefed ✓" : (isRoot ? "" : " · unbriefed");
    const connector = isRoot ? "" : (isLast ? "└─ " : "├─ ");
    lines.push(prefix + connector + nid + " (" + n.role + ") · " + (n.name || nid) + statusStr + storyStr + briefStr);

    const kids = n.children || [];
    const childPrefix = isRoot ? "" : prefix + (isLast ? "   " : "│  ");
    kids.forEach((kid, idx) => {
      walk(kid, childPrefix, idx === kids.length - 1, false);
    });
  }

  walk(rootId, "", true, true);
  return lines.join("\n");
}

function renderWorld(payload) {
  CURRENT_WORLD = payload;
  applyCodeMetadata(payload.code_metadata || (window.__WORLDGEN_BUNDLE__ && window.__WORLDGEN_BUNDLE__.code_metadata));
  const summary = payload.summary || {};
  const tree = payload.tree || { root: "n_root", nodes: {} };
  const nodes = tree.nodes || {};
  CURRENT_NODES = nodes;

  const turnsByNode = buildTurnsFromPayload(payload);
  NAV = [];

  // Update header
  document.getElementById("world-eyebrow").textContent =
    "worldgen · " + (summary.path || ("worlds/" + summary.id)) + " · " + (summary.llm || "narrator run");
  document.getElementById("world-title").textContent = summary.title || summary.id;

  const rootNode = nodes[tree.root || "n_root"] || {};
  document.getElementById("world-lede").innerHTML =
    'Seed prompt: <code>' + esc(rootNode.prompt || "—") + '</code>. ' +
    'Read it top to bottom: Lane 1 starts with <code>n_root</code> alone; when <code>n_root</code> spawns subagents, the page widens into parallel lanes beside their parent and merges back into the manifest. Hover any dotted underline to inspect prompts, tools, or policies.';

  // Facts bar
  const usage = summary.usage || {};
  const totalIn = (usage.input_tokens || 0) + (usage.cache_read_input_tokens || 0);
  const totalOut = usage.output_tokens || 0;
  document.getElementById("facts").innerHTML = [
    '<span><b>' + (summary.llm_calls || 0) + '</b> LLM calls</span>',
    '<span><b>' + (summary.tool_calls || 0) + '</b> tool calls</span>',
    '<span><b>' + (summary.tool_errors || 0) + '</b> rejected</span>',
    '<span><b>' + Object.keys(turnsByNode).length + '</b> narrator turns</span>',
    '<span><b>' + (summary.node_count || 0) + '</b> nodes (' + (summary.narrator_count || 0) + ' narrators, ' + (summary.actor_count || 0) + ' actors)</span>',
    '<span><b>' + (summary.story_words || 0).toLocaleString() + '</b> story words</span>',
    '<span><b>' + totalIn.toLocaleString() + '</b> in / <b>' + totalOut.toLocaleString() + '</b> out tokens</span>'
  ].join("");

  // Build Walk section
  let html = "";
  let nav = '<div class="grp">Making the world</div>';

  // Stage 1: Seed Prompt -> Root Story overview (if story_md exists)
  const flowHtml = buildWorldFlow(payload, turnsByNode);
  html += (
    '<div class="part" id="stage-day0">' +
      '<div class="part-head">' +
        '<h2>Day 0: the narrator tree builds the world</h2>' +
        '<p class="muted">' +
          'Before the simulation clock starts. The root narrator builds the top-level story, spawns its children, and briefs each one. ' +
          'When child narrators are spawned, they open parallel lanes to the right and build their own branches concurrently.' +
        '</p>' +
        '<p class="howto">' +
          'Scroll sideways when parallel lanes open. Lane 1 is <code>n_root</code>; each spawned narrator opens its own lane to the right, and horizontal connectors show who spawned and briefed whom.' +
        '</p>' +
      '</div>' +
      flowHtml
  );

  // Manifest card at the bottom of Stage Day 0 (just like Lumen Metrics Dry Run.html)
  const asciiTree = buildAsciiTree(tree);
  const pols = summary.policies || {};
  const polHtml = Object.keys(pols).length
    ? Object.entries(pols).map(([k, v]) => '<code class="tip" tabindex="0" data-tip="pol:' + esc(k) + '">' + esc(k) + '=' + esc(v) + '</code>').join(", ")
    : "default";

  const statusSummary = Object.entries(summary.status_counts || {})
    .map(([k, v]) => v + " " + k)
    .join(", ");

  html += (
    '<article class="card close" id="manifest">' +
      '<div class="card-head">' +
        '<h3>The manifest after day 0 (<code>' + esc(summary.path || summary.id) + '/tree.json</code>)</h3>' +
        '<span class="role ok">stage output</span>' +
      '</div>' +
      '<p class="sumline">' +
        Object.keys(turnsByNode).length + ' narrator turns, ' +
        (summary.llm_calls || 0) + ' LLM calls, ' +
        (summary.tool_calls || 0) + ' tool calls (' + (summary.tool_errors || 0) + ' rejected). ' +
        'Total stories written: <b>' + (summary.story_words || 0).toLocaleString() + ' words</b>.' +
      '</p>' +
      '<div class="kv">' +
        '<span>model</span><span><code>' + esc(summary.llm || "—") + '</code> (effort: <code>' + esc(summary.effort || "—") + '</code>)</span>' +
        '<span>nodes</span><span>' + (summary.node_count || 0) + ': ' + (summary.narrator_count || 0) + ' narrators, ' + (summary.actor_count || 0) + ' actors (' + esc(statusSummary) + ')</span>' +
        '<span>policies</span><span>' + polHtml + '</span>' +
        '<span>files</span><span><code>tree.json</code>, <code>story.md</code>, <code>narrator_output.md</code>, <code>log.jsonl</code></span>' +
      '</div>' +
      '<span class="who">agent tree &amp; data flow status</span>' +
      '<pre>' + esc(asciiTree) + '</pre>' +
      (payload.narrator_output_md
        ? '<details><summary>Read complete compiled narrator_output.md (' + wordCount(payload.narrator_output_md).toLocaleString() + ' words)</summary><pre style="max-height:520px">' + esc(payload.narrator_output_md) + '</pre></details>'
        : '') +
    '</article>' +
    '</div>'
  );

  nav += '<a href="#stage-day0">Day 0: narrator tree</a>';
  nav += NAV.map(x => '<a class="sub" href="#' + esc(x[0]) + '">' + esc(x[1]) + '</a>').join("");
  nav += '<a class="sub" href="#manifest">Manifest (tree.json)</a>';
  nav += '<div class="grp">Reference</div>';
  nav += '<a href="#reference">System prompts &amp; tools</a>';

  document.getElementById("body").innerHTML = html;
  document.getElementById("tl").innerHTML = nav;

  // Render Reference section
  document.getElementById("refs").innerHTML = Object.keys(SYSTEM).map(k => (
    '<div class="ref">' +
      '<h3>' + esc(SYSTEM[k].name) + '</h3>' +
      '<pre>' + esc(SYSTEM[k].text) + '</pre>' +
      (TOOLS[k].length
        ? '<span class="eyebrow">tools (' + TOOLS[k].length + ')</span>' +
          '<div class="toolsig">' +
            TOOLS[k].map(t => '<div><span' + tipAttr("tool:" + t) + '>' + esc(TOOLDOC[t][0]) + '</span></div>').join("") +
          '</div>'
        : '<span class="eyebrow">tools: day 1+ simulation tools</span>') +
    '</div>'
  )).join("");
}

/* ============ TOOLTIPS (identical to Lumen Metrics Dry Run.html) ============ */
const tip = document.getElementById("tip");
function tipContent(key) {
  const i = key.indexOf(":");
  const kind = key.slice(0, i);
  const name = key.slice(i + 1);
  if (kind === "sys" && SYSTEM[name]) {
    return '<b>System prompt · ' + esc(SYSTEM[name].name) + '</b>' + esc(SYSTEM[name].text);
  }
  if (kind === "set" && TOOLS[name]) {
    return '<b>' + TOOLS[name].length + ' ' + esc(name) + ' tools</b>' +
      TOOLS[name].map(t => '<span class="sig">' + esc(TOOLDOC[t][0]) + '</span>').join("");
  }
  if (kind === "tool" && TOOLDOC[name]) {
    const d = TOOLDOC[name];
    return '<b>Tool</b><span class="sig">' + esc(d[0]) + '</span>' + esc(d[1]);
  }
  if (kind === "pol" && POLICY[name]) {
    return '<b>Policy · ' + esc(name) + '</b>' + esc(POLICY[name]);
  }
  if (kind === "note") {
    return '<b>Note</b>' + esc(name);
  }
  if (kind === "node" && CURRENT_NODES[name]) {
    const N = CURRENT_NODES[name];
    const cb = N.brief
      ? '\n\nChapter brief (from ' + (N.parent || "parent") + '): ' + N.brief
      : '\n\nChapter brief: (none written yet)';
    return (
      '<b>' + esc(name) + ' · ' + esc(N.role) +
      (N.parent ? ' · parent ' + esc(N.parent) : ' · root') +
      ' · status: ' + esc(N.status || "—") + '</b>' +
      'Prompt: ' + esc(N.prompt || "—") + esc(cb)
    );
  }
  return esc(key);
}

let tipEl = null;
function showTip(el) {
  tipEl = el;
  tip.innerHTML = tipContent(el.dataset.tip);
  tip.hidden = false;
  const r = el.getBoundingClientRect();
  const tw = tip.offsetWidth;
  const th = tip.offsetHeight;
  const x = Math.min(Math.max(8, r.left), window.innerWidth - tw - 8);
  let y = r.bottom + 6;
  if (y + th > window.innerHeight - 8) y = Math.max(8, r.top - th - 6);
  tip.style.left = x + "px";
  tip.style.top = y + "px";
}
function hideTip() {
  tip.hidden = true;
  tipEl = null;
}
document.addEventListener("mouseover", e => {
  const el = e.target.closest("[data-tip]");
  if (el && el !== tipEl) showTip(el);
  else if (!el && tipEl) hideTip();
});
document.addEventListener("focusin", e => {
  const el = e.target.closest("[data-tip]");
  if (el) showTip(el);
});
document.addEventListener("focusout", hideTip);
document.addEventListener("scroll", () => { if (tipEl) hideTip(); }, true);
document.addEventListener("click", e => {
  const el = e.target.closest("[data-tip]");
  if (el && !e.target.closest("summary")) showTip(el);
});

/* follow links into lanes */
function openTarget() {
  const id = location.hash.slice(1);
  if (!id) return;
  const el = document.getElementById(id);
  if (!el) return;
  let p = el;
  while (p) {
    if (p.tagName === "DETAILS") p.open = true;
    p = p.parentElement;
  }
  requestAnimationFrame(() => el.scrollIntoView({ block: "start", inline: "center" }));
}
window.addEventListener("hashchange", openTarget);

/* theme switch */
const tb = document.getElementById("themebtn");
function effDark() {
  const t = document.documentElement.getAttribute("data-theme");
  return t ? t === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
}
function setThemeLabel() {
  tb.textContent = effDark() ? "Switch to light mode" : "Switch to dark mode";
}
try {
  const saved = localStorage.getItem("lumen-theme");
  if (saved) document.documentElement.setAttribute("data-theme", saved);
} catch (e) {}
setThemeLabel();
tb.addEventListener("click", () => {
  const t = effDark() ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", t);
  try { localStorage.setItem("lumen-theme", t); } catch (e) {}
  setThemeLabel();
});

/* ============ WORLD LOADING & DROPDOWN ============ */
async function loadWorld(worldId) {
  let payload = null;
  if (window.__WORLDGEN_BUNDLE__ && window.__WORLDGEN_BUNDLE__.payloads && window.__WORLDGEN_BUNDLE__.payloads[worldId]) {
    payload = window.__WORLDGEN_BUNDLE__.payloads[worldId];
  }
  try {
    const res = await fetch("/api/worlds/" + encodeURIComponent(worldId), { cache: "no-store" });
    if (res.ok) payload = await res.json();
  } catch (e) {}

  if (payload) {
    renderWorld(payload);
    openTarget();
  }
}

async function init() {
  const sel = document.getElementById("world-select");
  let worlds = (window.__WORLDGEN_BUNDLE__ && window.__WORLDGEN_BUNDLE__.worlds) || [];
  try {
    const res = await fetch("/api/worlds", { cache: "no-store" });
    if (res.ok) {
      const data = await res.json();
      if (data && Array.isArray(data.worlds) && data.worlds.length) {
        worlds = data.worlds;
      }
    }
  } catch (e) {}

  if (worlds.length) {
    // Sort demo_deep first so the multi-lane parallel narrator run is default
    worlds.sort((a, b) => (a.id === "demo_deep" ? -1 : b.id === "demo_deep" ? 1 : a.id.localeCompare(b.id)));
    sel.innerHTML = worlds.map(w =>
      '<option value="' + esc(w.id) + '">' +
        esc(w.id) + ' — ' + esc(w.title || w.id) +
        ' (' + (w.narrator_count || 0) + ' narrators, ' + (w.actor_count || 0) + ' actors)' +
      '</option>'
    ).join("");
  }

  const params = new URLSearchParams(location.search);
  const initialWorld = params.get("world") || (worlds[0] ? worlds[0].id : "demo_deep");
  sel.value = initialWorld;
  sel.addEventListener("change", () => {
    const wid = sel.value;
    try {
      const url = new URL(location.href);
      url.searchParams.set("world", wid);
      history.replaceState(null, "", url);
    } catch (e) {}
    loadWorld(wid);
  });

  await loadWorld(sel.value || "demo_deep");
}

init();
