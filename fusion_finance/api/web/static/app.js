/* Fusion-Finance web UI glue — vanilla JS, no build step. */
(function () {
    "use strict";

    var body = document.body;
    var API_KEY = body.dataset.apiKey || "";
    var page = body.dataset.page || "";

    function headers() {
        var h = { "Content-Type": "application/json" };
        if (API_KEY) h["x-api-key"] = API_KEY;
        return h;
    }

    var toastTimer = null;
    function toast(message, isError) {
        var el = document.getElementById("toast");
        el.textContent = message;
        el.classList.toggle("err", !!isError);
        el.classList.remove("hidden");
        clearTimeout(toastTimer);
        toastTimer = setTimeout(function () { el.classList.add("hidden"); }, 3500);
    }

    function fetchJSON(url, options) {
        options = options || {};
        options.headers = Object.assign(headers(), options.headers || {});
        return fetch(url, options).then(function (resp) {
            return resp.json().then(function (data) {
                if (!resp.ok) {
                    var detail = (data && (data.detail || data.error)) || resp.status;
                    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
                }
                return data;
            });
        });
    }

    function post(url, payload) {
        return fetchJSON(url, { method: "POST", body: JSON.stringify(payload || {}) });
    }

    function formData(form) {
        var out = {};
        new FormData(form).forEach(function (v, k) {
            if (typeof v !== "string") return;
            var trimmed = v.trim();
            if (trimmed !== "" && /^-?[\d.eE+]+$/.test(trimmed)) out[k] = Number(trimmed);
            else out[k] = trimmed;
        });
        return out;
    }

    function csvField(form, name) {
        var raw = form.elements[name] && form.elements[name].value.trim();
        if (!raw) return [];
        return raw.split(",").map(function (s) { return Number(s.trim()); }).filter(function (n) { return !isNaN(n); });
    }

    function setBadge(id, status, label) {
        var el = document.getElementById(id);
        if (!el) return;
        el.textContent = label || status;
        el.className = "badge " + (status === "ok" ? "ok" : status === "warn" ? "warn" : status === "err" ? "err" : "muted");
    }

    function kvList(container, pairs) {
        var dl = document.createElement("dl");
        dl.className = "kv";
        pairs.forEach(function (p) {
            var dt = document.createElement("dt");
            dt.textContent = p[0];
            var dd = document.createElement("dd");
            dd.textContent = p[1];
            dl.appendChild(dt);
            dl.appendChild(dd);
        });
        container.innerHTML = "";
        container.appendChild(dl);
    }

    function table(container, columns, rows) {
        if (!rows.length) {
            container.innerHTML = '<p class="muted">no data</p>';
            return;
        }
        var tableEl = document.createElement("table");
        tableEl.className = "data";
        var thead = document.createElement("thead");
        var headRow = document.createElement("tr");
        columns.forEach(function (c) {
            var th = document.createElement("th");
            th.textContent = c;
            headRow.appendChild(th);
        });
        thead.appendChild(headRow);
        tableEl.appendChild(thead);
        var tbody = document.createElement("tbody");
        rows.forEach(function (r) {
            var tr = document.createElement("tr");
            columns.forEach(function (c) {
                var td = document.createElement("td");
                var v = r[c];
                td.textContent = v === null || v === undefined ? "—" : String(v);
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
        tableEl.appendChild(tbody);
        container.innerHTML = "";
        container.appendChild(tableEl);
    }

    function flatRows(obj, prefix) {
        var rows = [];
        Object.keys(obj || {}).forEach(function (k) {
            var v = obj[k];
            var key = prefix ? prefix + "." + k : k;
            if (v && typeof v === "object" && !Array.isArray(v)) {
                rows = rows.concat(flatRows(v, key));
            } else if (Array.isArray(v)) {
                rows.push({ key: key, value: v.length <= 6 ? v.join(", ") : "[" + v.length + " items]" });
            } else {
                rows.push({ key: key, value: v });
            }
        });
        return rows;
    }

    function showResult(title, data) {
        document.getElementById("result-card").classList.remove("hidden");
        document.getElementById("result-title").textContent = title;
        var bodyEl = document.getElementById("result-body");
        table(bodyEl, ["field", "value"], flatRows(data).map(function (r) { return { field: r.key, value: String(r.value) }; }));
        document.getElementById("result-card").scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    function bindForm(formId, buildPayload, run, resultTitle) {
        var form = document.getElementById(formId);
        if (!form) return;
        form.addEventListener("submit", function (e) {
            e.preventDefault();
            var btn = form.querySelector('button[type="submit"]');
            btn.disabled = true;
            run(buildPayload(form))
                .then(function (data) { showResult(resultTitle, data); })
                .catch(function (err) { toast(err.message, true); })
                .finally(function () { btn.disabled = false; });
        });
    }

    /* ---------- Dashboard ---------- */

    function initDashboard() {
        fetchJSON("/api/v1/dashboard/status").then(function (s) {
            var mlx = (s.mlx && s.mlx.status) || "unknown";
            setBadge("svc-badge", "ok", "v" + s.version);
            setBadge("mlx-badge", mlx === "connected" ? "ok" : "err", mlx);
            kvList(document.getElementById("svc-info"), [["service", s.service], ["version", s.version]]);
            kvList(
                document.getElementById("mlx-info"),
                [["status", mlx], ["models", (s.mlx && s.mlx.models && s.mlx.models.join(", ")) || "—"]]
            );
        }).catch(function (err) {
            setBadge("svc-badge", "err", "error");
            setBadge("mlx-badge", "err", "unknown");
            toast(err.message, true);
        });

        var projList = document.getElementById("proj-list");
        fetchJSON("/api/v1/project/list").then(function (r) {
            var projects = r.projects || [];
            setBadge("proj-badge", "ok", String(r.total));
            projList.innerHTML = "";
            if (!projects.length) {
                projList.innerHTML = '<li class="muted">no projects yet</li>';
                return;
            }
            projects.forEach(function (p) {
                var li = document.createElement("li");
                li.textContent = (p.name || p.id) + (p.description ? " — " + p.description : "");
                projList.appendChild(li);
            });
        }).catch(function (err) {
            setBadge("proj-badge", "err", "error");
            projList.innerHTML = "";
            var li = document.createElement("li");
            li.className = "muted";
            li.textContent = err.message;
            projList.appendChild(li);
        });

        function loadScreener() {
            var preset = document.getElementById("screener-preset").value;
            var wrap = document.getElementById("screener-wrap");
            wrap.innerHTML = '<p class="muted">loading…</p>';
            fetchJSON("/api/v1/dashboard/market?preset=" + encodeURIComponent(preset) + "&limit=8").then(function (r) {
                var ranked = (r.screener && (r.screener.ranked || r.screener.results)) || [];
                var rows = ranked.map(function (x) { return x.company ? x : { symbol: x.symbol || x.name, score: x.score, rank: x.rank }; });
                if (!rows.length && r.screener) {
                    rows = flatRows(r.screener).map(function (f) { return { field: f.key, value: String(f.value) }; });
                    table(wrap, ["field", "value"], rows);
                    return;
                }
                table(wrap, Object.keys(rows[0] || { symbol: 1 }), rows);
            }).catch(function (err) { wrap.innerHTML = ""; toast(err.message, true); });
        }
        document.getElementById("screener-btn").addEventListener("click", loadScreener);
        loadScreener();

        function loadQuotes() {
            var market = document.getElementById("quotes-market").value;
            var wrap = document.getElementById("quotes-wrap");
            wrap.innerHTML = '<p class="muted">loading…</p>';
            fetchJSON("/api/v1/data/market/quotes?market=" + encodeURIComponent(market)).then(function (r) {
                var cols = r.quotes && r.quotes.length ? Object.keys(r.quotes[0]) : [];
                table(wrap, cols, r.quotes || []);
            }).catch(function (err) { wrap.innerHTML = ""; toast(err.message, true); });
        }
        document.getElementById("quotes-btn").addEventListener("click", loadQuotes);
        loadQuotes();
    }

    /* ---------- Modeling ---------- */

    function dcfPayload(form) {
        return {
            company: form.elements.company.value.trim(),
            revenue: csvField(form, "revenue"),
            ebit_margin: csvField(form, "ebit_margin"),
            wacc: Number(form.elements.wacc.value),
            terminal_growth: Number(form.elements.terminal_growth.value),
            tax_rate: Number(form.elements.tax_rate.value),
            net_debt: Number(form.elements.net_debt.value),
            shares_outstanding: Number(form.elements.shares_outstanding.value),
        };
    }

    function initModeling() {
        bindForm("dcf-form", dcfPayload, function (p) { return post("/api/v1/modeling/dcf/calculate", p); }, "DCF Result");
        bindForm("mc-form", function (form) {
            var p = dcfPayload(document.getElementById("dcf-form"));
            p.simulations = Number(form.elements.simulations.value);
            return p;
        }, function (p) { return post("/api/v1/modeling/monte-carlo", p); }, "Monte Carlo Result");
        var sensBtn = document.getElementById("sens-btn");
        sensBtn.addEventListener("click", function () {
            sensBtn.disabled = true;
            post("/api/v1/modeling/sensitivity", dcfPayload(document.getElementById("dcf-form")))
                .then(function (data) { showResult("Sensitivity Result", data); })
                .catch(function (err) { toast(err.message, true); })
                .finally(function () { sensBtn.disabled = false; });
        });
    }

    /* ---------- Risk ---------- */

    function initRisk() {
        bindForm("var-form", formData, function (p) { return post("/api/v1/risk/var/monte-carlo", p); }, "Monte Carlo VaR");
        bindForm("sanctions-form", formData, function (p) { return post("/api/v1/risk/sanctions", p); }, "Sanctions Screen");

        document.getElementById("stress-btn").addEventListener("click", function () {
            var wrap = document.getElementById("stress-wrap");
            wrap.innerHTML = '<p class="muted">loading…</p>';
            fetchJSON("/api/v1/risk/stress-scenarios").then(function (r) {
                var rows = r.scenarios || [];
                table(wrap, rows.length ? Object.keys(rows[0]) : [], rows);
            }).catch(function (err) { wrap.innerHTML = ""; toast(err.message, true); });
        });
    }

    /* ---------- Copilot ---------- */

    function initCopilot() {
        var log = document.getElementById("chat-log");
        var badge = document.getElementById("ws-badge");
        var input = document.getElementById("chat-input");
        var sendBtn = document.getElementById("chat-send");
        var ws = null;

        function addMsg(cls, text) {
            var div = document.createElement("div");
            div.className = "msg " + cls;
            div.textContent = text;
            log.appendChild(div);
            log.scrollTop = log.scrollHeight;
            return div;
        }

        function connect() {
            var proto = location.protocol === "https:" ? "wss:" : "ws:";
            var url = proto + "//" + location.host + "/ws/copilot";
            if (API_KEY) url += "?api_key=" + encodeURIComponent(API_KEY);
            setBadge("ws-badge", "muted", "connecting…");
            ws = new WebSocket(url);
            ws.onopen = function () { setBadge("ws-badge", "ok", "connected"); sendBtn.disabled = false; };
            ws.onclose = function () {
                setBadge("ws-badge", "err", "disconnected");
                sendBtn.disabled = false;
            };
            ws.onerror = function () { setBadge("ws-badge", "err", "error"); };
            ws.onmessage = function (ev) {
                var msg;
                try { msg = JSON.parse(ev.data); } catch (e) { return; }
                if (msg.type === "thinking") {
                    addMsg("msg-thinking", "thinking…");
                } else if (msg.type === "chunk") {
                    var last = log.lastElementChild;
                    if (last && last.classList.contains("msg-thinking")) last.remove();
                    var existing = log.querySelector(".msg-ai.streaming");
                    if (existing) {
                        existing.textContent += msg.content;
                    } else {
                        var div = addMsg("msg-ai streaming", msg.content);
                    }
                    log.scrollTop = log.scrollHeight;
                } else if (msg.type === "done") {
                    var streaming = log.querySelector(".msg-ai.streaming");
                    if (streaming) streaming.classList.remove("streaming");
                    sendBtn.disabled = false;
                } else if (msg.type === "error") {
                    var think = log.querySelector(".msg-thinking");
                    if (think) think.remove();
                    addMsg("msg-system", "error: " + msg.content);
                    sendBtn.disabled = false;
                }
            };
        }

        document.getElementById("chat-form").addEventListener("submit", function (e) {
            e.preventDefault();
            var text = input.value.trim();
            if (!text || !ws || ws.readyState !== WebSocket.OPEN) {
                toast("copilot not connected", true);
                return;
            }
            addMsg("msg-user", text);
            input.value = "";
            sendBtn.disabled = true;
            ws.send(JSON.stringify({ message: text }));
        });

        connect();
    }

    /* ---------- boot ---------- */

    var inits = { dashboard: initDashboard, modeling: initModeling, risk: initRisk, copilot: initCopilot };
    if (inits[page]) inits[page]();
})();
