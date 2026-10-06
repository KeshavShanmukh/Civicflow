(() => {
  "use strict";

  const categories = ["Pothole", "Streetlight", "Garbage", "Water leakage", "Road damage", "Drainage", "Traffic signal", "Public infrastructure", "Other"];
  const categoryIcons = {
    Pothole: "◉", "Road damage": "⌁", Streetlight: "☼", Garbage: "♻", "Water leakage": "≈",
    Drainage: "⌇", "Traffic signal": "◉", "Public infrastructure": "⌂", Other: "＋"
  };
  let departments = [];
  let staff = [];
  const demoUsers = [
    { id: "demo-citizen", name: "Alex Morgan", email: "alex@civicflow.local", role: "citizen", department: null },
    { id: "demo-admin", name: "Jordan Lee", email: "admin@civicflow.local", role: "admin", department: null },
    { id: "demo-supervisor", name: "Sam Rivera", email: "supervisor@civicflow.local", role: "supervisor", department: "Roads" },
    { id: "demo-worker", name: "Taylor Brooks", email: "worker@civicflow.local", role: "worker", department: "Roads" },
    { id: "demo-staff", name: "Robin Singh", email: "staff@civicflow.local", role: "staff", department: "Roads" },
    { id: "demo-department_admin", name: "Priya Nair", email: "department-admin@civicflow.local", role: "department_admin", department: "Roads" },
    { id: "demo-city_admin", name: "Asha Rao", email: "city-admin@civicflow.local", role: "city_admin", department: null }
  ];
  let state = { reports: [], notifications: [], activity: [], departments: [], staff: [], metrics: {} };
  let apiReady = false;
  let backendError = "";
  let currentUser = null;
  let activeView = "overview";
  let reportFilter = "all";
  let reportSearch = "";
  let photoData = "";
  let authMode = "login";
  let modalReportId = null;

  async function apiRequest(path, options = {}) {
    const response = await fetch(path, {
      method: options.method || "GET",
      credentials: "same-origin",
      headers: options.body === undefined ? {} : { "Content-Type": "application/json" },
      body: options.body === undefined ? undefined : JSON.stringify(options.body)
    });
    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json") ? await response.json() : null;
    if (!response.ok) throw new Error(payload?.error || `Request failed (${response.status}).`);
    return payload;
  }

  async function refreshState() {
    state = await apiRequest("/api/state");
    currentUser = state.user;
    departments = state.departments;
    staff = state.staff;
    apiReady = true;
    return state;
  }

  function showApiError(error) {
    console.error("CivicFlow request failed.", error);
    toast(error.message || "The server could not complete this request.", true);
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
  }
  function safeImage(value) {
    return typeof value === "string" && value.startsWith("data:image/") ? value : "";
  }
  function formatDate(value, withTime = false) {
    const date = new Date(value);
    return date.toLocaleString(undefined, withTime ? { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" } : { month: "short", day: "numeric" });
  }
  function timeAgo(value) {
    const minutes = Math.max(0, Math.floor((Date.now() - value) / 60000));
    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes} min ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} hr${hours === 1 ? "" : "s"} ago`;
    const days = Math.floor(hours / 24);
    return `${days} day${days === 1 ? "" : "s"} ago`;
  }
  function titleCase(value) { return value.replace(/\b\w/g, char => char.toUpperCase()); }
  function role() { return currentUser?.role || "citizen"; }
  function actor() { return currentUser; }
  function visibleReports() {
    let reports = state.reports;
    if (role() === "citizen") reports = reports.filter(report => report.citizenId === actor()?.id);
    if (role() === "worker") reports = reports.filter(report => report.worker === actor().name || (actor().department && report.department === actor().department && !report.worker));
    return reports;
  }
  function canManage() { return ["admin", "city_admin", "department_admin", "supervisor", "staff"].includes(role()); }
  function recommendWorker(department, category) {
    return staff.filter(person => person.department === department)
      .sort((left, right) => Number(!left.skills.includes(category)) - Number(!right.skills.includes(category)) || left.active - right.active)[0]?.name || "";
  }
  function statusClass(status) { return `status-${status.toLowerCase().replace(/\s+/g, "-")}`; }
  function priorityClass(value) { return value >= 80 ? "critical" : value >= 60 ? "high" : value >= 40 ? "medium" : "low"; }
  function toast(message, error = false) {
    const region = document.getElementById("toast-region");
    if (!region) return;
    const node = document.createElement("div");
    node.className = `toast${error ? " error" : ""}`;
    node.textContent = message;
    region.append(node);
    setTimeout(() => node.remove(), 3600);
  }
  function render() {
    const root = document.getElementById("app");
    if (!currentUser) {
      root.innerHTML = renderAuth() + (backendError ? `<div class="backend-status backend-offline" role="alert">${escapeHtml(backendError)} <button class="text-button" id="retry-backend">Retry</button></div>` : !apiReady ? `<div class="backend-status" role="status">Connecting to the local SQLite service…</div>` : "");
      bindAuth();
      document.getElementById("retry-backend")?.addEventListener("click", startApp);
      return;
    }
    if (!["overview", "reports", "work-orders", "departments", "team", "analytics", "audit", "notifications", "platform"].includes(activeView)) activeView = "overview";
    root.innerHTML = `<div class="app-shell">${renderSidebar()}<main class="main">${renderTopbar()}<section class="page">${renderView()}</section></main></div>`;
    bindApp();
  }

  function renderAuth() {
    return `<main class="auth-shell">
      <section class="auth-story">
        <div class="auth-brand"><span class="brand-mark">c</span> civicflow</div>
        <div class="auth-copy"><span class="eyebrow">Your neighborhood, moving forward</span><h1>Small reports.<br>Real change.</h1><p>A simple way to bring local issues to the people who can fix them. See what is happening in your community, from report to resolution.</p><div class="auth-steps"><span class="auth-step">01 &nbsp; Report an issue</span><span class="auth-step">02 &nbsp; Track the work</span><span class="auth-step">03 &nbsp; See the change</span></div></div>
        <div class="auth-footer">A community service prototype · Powered by local Python & SQLite</div>
      </section>
      <section class="auth-panel"><div class="auth-card">
        <h2>${authMode === "login" ? "Welcome back" : "Join your community"}</h2>
        <p>${authMode === "login" ? "Sign in to follow local issues and help make your neighborhood better." : "Create a citizen account to report and track neighborhood issues."}</p>
        <form id="auth-form">
          ${authMode === "register" ? `<div class="form-field"><label for="auth-name">Your name</label><input id="auth-name" name="name" autocomplete="name" required maxlength="60" placeholder="e.g. Alex Morgan"></div>` : ""}
          <div class="form-field"><label for="auth-email">Email address</label><input id="auth-email" name="email" type="email" autocomplete="email" required maxlength="120" placeholder="you@example.com"></div>
          <div class="form-field"><label for="auth-password">Password</label><input id="auth-password" name="password" type="password" autocomplete="${authMode === "login" ? "current-password" : "new-password"}" required minlength="${authMode === "register" ? "10" : "1"}" maxlength="100" ${authMode === "register" ? 'pattern="(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).{10,100}"' : ""} placeholder="${authMode === "register" ? "10+ chars, upper & lowercase, and a number" : "Your password"}"></div>
          <button class="btn btn-primary btn-full" type="submit">${authMode === "login" ? "Sign in" : "Create citizen account"}</button>
        </form>
        <div class="auth-switch">${authMode === "login" ? "New to CivicFlow? " : "Already have an account? "}<button class="text-button" id="auth-toggle">${authMode === "login" ? "Create an account" : "Sign in"}</button></div>
        <div class="demo-divider">OR EXPLORE A DEMO ACCOUNT</div>
        <div class="demo-buttons">${demoUsers.map(user => `<button class="demo-button" data-demo="${user.role}">${titleCase(user.role)} view<span>${user.name}</span></button>`).join("")}</div>
        <div class="local-note">Demo accounts are for local exploration. Registered accounts use a salted password hash in the local SQLite database. This local prototype is not intended for public deployment.</div>
      </div></section>
    </main>`;
  }

  function bindAuth() {
    document.getElementById("auth-toggle")?.addEventListener("click", () => { authMode = authMode === "login" ? "register" : "login"; render(); });
    document.querySelectorAll("[data-demo]").forEach(button => button.addEventListener("click", async () => {
      try {
        const result = await apiRequest("/api/auth/demo", { method: "POST", body: { role: button.dataset.demo } });
        currentUser = result.user;
        activeView = "overview";
        await refreshState();
        render();
      } catch (error) { showApiError(error); }
    }));
    document.getElementById("auth-form")?.addEventListener("submit", async event => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const email = String(form.get("email")).trim().toLowerCase();
      const password = String(form.get("password"));
      const endpoint = authMode === "register" ? "/api/auth/register" : "/api/auth/login";
      const body = authMode === "register"
        ? { name: String(form.get("name")).trim(), email, password }
        : { email, password };
      try {
        const result = await apiRequest(endpoint, { method: "POST", body });
        await refreshState();
        activeView = "overview";
        render();
        if (authMode === "register") toast("Your citizen account is ready.");
      } catch (error) { showApiError(error); }
    });
  }

  const navigation = [
    { id: "overview", label: "Overview", icon: "⌂", roles: ["citizen", "admin", "city_admin", "department_admin", "supervisor", "staff", "worker"] },
    { id: "reports", label: "Reports", icon: "▤", roles: ["citizen", "admin", "city_admin", "department_admin", "supervisor", "staff", "worker"] },
    { id: "work-orders", label: "Work orders", icon: "✓", roles: ["admin", "city_admin", "department_admin", "supervisor", "staff", "worker"] },
    { id: "departments", label: "Departments", icon: "▦", roles: ["admin", "city_admin", "department_admin", "supervisor", "staff"] },
    { id: "team", label: "Team", icon: "♙", roles: ["admin", "city_admin", "department_admin", "supervisor", "staff"] },
    { id: "analytics", label: "Analytics", icon: "▥", roles: ["admin", "city_admin", "department_admin", "supervisor", "staff"] },
    { id: "audit", label: "Audit trail", icon: "⌑", roles: ["admin", "city_admin", "department_admin"] },
    { id: "notifications", label: "Notifications", icon: "♧", roles: ["citizen", "admin", "city_admin", "department_admin", "supervisor", "staff", "worker"] },
    { id: "platform", label: "Platform center", icon: "⚙", roles: ["citizen", "admin", "city_admin", "department_admin", "supervisor", "staff", "worker"] }
  ];

  function renderSidebar() {
    const items = navigation.filter(item => item.roles.includes(role()));
    const notificationCount = state.notifications.filter(item => !item.read && (!item.recipientId || item.recipientId === actor().id)).length;
    return `<aside class="sidebar">
      <div class="brand"><span class="brand-mark">c</span> civicflow</div>
      <div class="nav-label">Workspace</div><nav class="nav-list" aria-label="Main navigation">${items.map(item => `<button class="nav-item${activeView === item.id ? " active" : ""}" data-view="${item.id}"><span class="nav-icon">${item.icon}</span>${item.label}${item.id === "notifications" && notificationCount ? `<span class="nav-count">${notificationCount}</span>` : ""}</button>`).join("")}</nav>
      <div class="sidebar-bottom"><div class="city-card"><div class="city-card-head"><span class="city-dot"></span> SQLite service online</div><p>Reports and workflow history are stored in your local CivicFlow database.</p></div>
        <button class="profile-button" id="profile-button"><span class="avatar">${initials(actor().name)}</span><span class="profile-meta"><strong>${escapeHtml(actor().name)}</strong><small>${escapeHtml(role())}${actor().department ? ` · ${escapeHtml(actor().department)}` : ""}</small></span><span class="logout">⋯</span></button></div>
    </aside>`;
  }
  function initials(name) { return name.split(/\s+/).slice(0, 2).map(part => part[0] || "").join("").toUpperCase(); }
  function renderTopbar() {
    const currentNav = navigation.find(item => item.id === activeView);
    const notificationCount = state.notifications.filter(item => !item.read && (!item.recipientId || item.recipientId === actor().id)).length;
    return `<header class="topbar"><div class="breadcrumbs">CivicFlow <span aria-hidden="true">/</span> <strong>${currentNav?.label || "Overview"}</strong></div><div class="top-actions">
      ${currentUser.role !== "citizen" ? `<label class="hidden" for="role-select">Role view</label><select class="role-select" id="role-select" aria-label="Switch role view">${["admin", "city_admin", "department_admin", "supervisor", "staff", "worker"].map(value => `<option value="${value}" ${role() === value ? "selected" : ""}>${titleCase(value)} view</option>`).join("")}</select>` : ""}
      <button class="icon-button" id="top-notifications" aria-label="Notifications">♧${notificationCount ? `<span class="notification-count">${Math.min(notificationCount, 9)}</span>` : ""}</button>
      ${role() === "citizen" ? `<button class="btn btn-primary btn-small" data-action="new-report">＋ Report issue</button>` : ""}
    </div></header>`;
  }
  function renderView() {
    switch (activeView) {
      case "reports": return renderReports();
      case "work-orders": return renderWorkOrders();
      case "departments": return renderDepartments();
      case "team": return renderTeam();
      case "analytics": return renderAnalytics();
      case "audit": return renderAudit();
      case "notifications": return renderNotifications();
      case "platform": return renderPlatformCenter();
      default: return renderOverview();
    }
  }
  function renderPlatformCenter() {
    return `${pageHeading("Platform center", "Profiles, local intelligence, operational health and security controls")}
      <div class="dashboard-grid">
        <section class="panel"><div class="panel-header"><div><h2 class="panel-title">Your profile</h2><p class="panel-subtitle">Manage contact details, preferred language and notification behaviour.</p></div><button class="btn btn-outline btn-small" id="load-profile">Refresh</button></div><div id="profile-center" class="empty-state"><span>◌</span><strong>Loading profile data</strong><p>Use refresh to retrieve the latest local profile records.</p></div></section>
        <section class="panel"><div class="panel-header"><div><h2 class="panel-title">Offline intelligence</h2><p class="panel-subtitle">Run local, API-key-free classification and severity analysis.</p></div></div><form id="intelligence-form"><div class="form-field"><label for="intel-description">Problem description</label><textarea id="intel-description" minlength="3" required placeholder="Example: A deep pothole is forcing traffic to swerve near the school gate."></textarea></div><div class="form-actions"><button class="btn btn-primary" type="submit">Analyze locally</button></div></form><div id="intel-result" class="panel-subtitle" style="margin-top:12px"></div></section>
      </div>
      <div class="dashboard-grid section-gap">
        <section class="panel"><div class="panel-header"><div><h2 class="panel-title">System health</h2><p class="panel-subtitle">Database integrity, table inventory and local runtime checks.</p></div><button class="btn btn-outline btn-small" id="system-health">Check</button></div><div id="health-result" class="empty-state"><span>◌</span><strong>Not checked</strong><p>Run the check to inspect the local platform.</p></div></section>
        <section class="panel"><div class="panel-header"><div><h2 class="panel-title">Search CivicFlow</h2><p class="panel-subtitle">Find reports, work orders and comments you are allowed to view.</p></div></div><form id="platform-search-form" class="inline-form"><input id="platform-search" required placeholder="pothole, streetlight, work order…"><button class="btn btn-primary" type="submit">Search</button></form><div id="platform-search-results" class="activity-list" style="margin-top:16px"></div></section>
      </div>`;
  }

  function pageHeading(title, subtitle, action = "") {
    return `<div class="page-heading"><div><h1>${title}</h1><p>${subtitle}</p></div>${action ? `<div class="heading-actions">${action}</div>` : ""}</div>`;
  }
  function metricCard(label, value, foot, icon, positive = false) {
    return `<article class="stat-card"><div class="stat-top"><span>${label}</span><span class="stat-icon">${icon}</span></div><div class="stat-value">${value}</div><div class="stat-foot${positive ? " positive" : ""}">${foot}</div></article>`;
  }
  function renderOverview() {
    const reports = visibleReports();
    const open = reports.filter(report => !["Resolved"].includes(report.status)).length;
    const resolved = reports.filter(report => report.status === "Resolved").length;
    const critical = reports.filter(report => report.severity === "Critical" && report.status !== "Resolved").length;
    const greeting = actor().name.split(" ")[0];
    const workText = role() === "citizen" ? "You can report local issues and keep track of the work happening near you." : "Your teams are turning neighborhood reports into visible, lasting improvements.";
    const activity = state.activity;
    const categoryTotals = categories.slice(0, 5).map(category => ({ category, count: reports.filter(report => report.category === category).length })).filter(item => item.count);
    const maxCategory = Math.max(1, ...categoryTotals.map(item => item.count));
    return `${`<div class="welcome"><div class="welcome-copy"><small>${role() === "citizen" ? "Your community, your voice" : `${titleCase(role())} workspace`}</small><h2>Good ${new Date().getHours() < 12 ? "morning" : new Date().getHours() < 17 ? "afternoon" : "evening"}, ${escapeHtml(greeting)}.</h2><p>${workText}</p></div><div class="welcome-actions">${role() === "citizen" ? `<button class="btn" data-action="new-report">＋ Report an issue</button>` : `<button class="btn" data-view="reports">Review reports&nbsp; →</button>`}</div></div>`}
      <div class="stat-grid">${metricCard("Total reports", reports.length, "Issues shared with your city", "▤")}${metricCard("In progress", open, "Being reviewed or worked on", "↗", true)}${metricCard("Resolved", resolved, "Closed after verification", "✓")}${metricCard("Needs attention", critical, "Critical issues still open", "!", critical > 0)}</div>
      <div class="dashboard-grid"><section class="panel"><div class="panel-header"><div><h2 class="panel-title">${role() === "citizen" ? "Your recent reports" : "Latest reports"}</h2><p class="panel-subtitle">The newest updates from your community</p></div><button class="link-button" data-view="reports">View all →</button></div>
        ${reports.length ? `<div class="issue-list">${[...reports].sort((a, b) => b.createdAt - a.createdAt).slice(0, 5).map(renderIssueRow).join("")}</div>` : emptyState("No reports yet", "Share the first issue in your neighborhood.", "new-report")}</section>
        <section class="panel"><div class="panel-header"><div><h2 class="panel-title">Community activity</h2><p class="panel-subtitle">A little progress goes a long way</p></div></div>${activity.length ? `<div class="activity-list">${activity.slice(0, 5).map(item => `<div class="activity-item"><span class="activity-icon">${escapeHtml(item.icon)}</span><div><strong>${escapeHtml(item.message)}</strong><small>${timeAgo(item.createdAt)}</small></div></div>`).join("")}</div>` : `<div class="empty-state"><span>◷</span><strong>No activity yet</strong><p>Report and workflow updates will appear here.</p></div>`}</section></div>
      <div class="dashboard-grid section-gap"><section class="panel"><div class="panel-header"><div><h2 class="panel-title">Common issue types</h2><p class="panel-subtitle">Based on reports you can view</p></div></div>${categoryTotals.length ? `<div class="category-bars">${categoryTotals.map(item => `<div><div class="category-bar-head"><span>${escapeHtml(item.category)}</span><span>${item.count}</span></div><div class="bar-track"><div class="bar-fill" style="width:${Math.max(8, item.count / maxCategory * 100)}%"></div></div></div>`).join("")}</div>` : `<p class="panel-subtitle">Your report categories will appear here.</p>`}</section>
        <section class="panel"><div class="panel-header"><div><h2 class="panel-title">How CivicFlow works</h2><p class="panel-subtitle">Every report follows a clear path</p></div></div><div class="activity-list"><div class="activity-item"><span class="activity-icon">1</span><div><strong>Report & review</strong><small>Share details; the right team reviews it.</small></div></div><div class="activity-item"><span class="activity-icon">2</span><div><strong>Assign & repair</strong><small>A local crew investigates and does the work.</small></div></div><div class="activity-item"><span class="activity-icon">3</span><div><strong>Verify & resolve</strong><small>A supervisor checks the result and closes the loop.</small></div></div></div></section></div>`;
  }
  function renderIssueRow(report) {
    return `<button class="issue-row" data-report="${escapeHtml(report.id)}" style="border:0;background:transparent;text-align:left;width:100%;font:inherit;cursor:pointer"><span class="issue-symbol">${categoryIcons[report.category] || "＋"}</span><span class="issue-main"><strong>${escapeHtml(report.title)}</strong><small>${escapeHtml(report.location)} · ${timeAgo(report.createdAt)}</small></span><span class="issue-side"><span class="status ${statusClass(report.status)}">${escapeHtml(report.status)}</span><span class="priority priority-${priorityClass(report.priority)}">${escapeHtml(report.severity)} priority</span></span></button>`;
  }
  function emptyState(title, copy, action = "") {
    return `<div class="empty-state"><span>◌</span><strong>${title}</strong><p>${copy}</p>${action === "new-report" ? `<button class="btn btn-primary btn-small" data-action="new-report">Report an issue</button>` : ""}</div>`;
  }

  function renderReports() {
    const all = visibleReports();
    const reports = all.filter(report => (reportFilter === "all" || report.status === reportFilter) && (!reportSearch || `${report.id} ${report.title} ${report.location} ${report.category}`.toLowerCase().includes(reportSearch.toLowerCase()))).sort((a, b) => b.createdAt - a.createdAt);
    const filters = ["all", "Awaiting review", "Assigned", "In progress", "Awaiting verification", "Resolved"];
    const action = role() === "citizen" ? `<button class="btn btn-primary btn-small" data-action="new-report">＋ New report</button>` : "";
    return `${pageHeading("Reports", role() === "citizen" ? "Follow the issues you have raised in your community." : "Review, prioritize, and move community issues forward.", action)}
      <section class="panel"><div class="toolbar"><div class="toolbar-left"><input class="search-input" id="report-search" placeholder="Search reports or locations…" value="${escapeHtml(reportSearch)}" aria-label="Search reports"><select class="filter-select" id="report-filter" aria-label="Filter by status">${filters.map(filter => `<option value="${escapeHtml(filter)}" ${reportFilter === filter ? "selected" : ""}>${filter === "all" ? "All statuses" : filter}</option>`).join("")}</select></div><div class="toolbar-right"><span class="panel-subtitle">${reports.length} report${reports.length === 1 ? "" : "s"}</span></div></div>
      ${reports.length ? `<div class="data-table-wrap"><table class="data-table"><thead><tr><th>Report</th><th>Location</th><th>Priority</th><th>Status</th><th>Reported</th><th></th></tr></thead><tbody>${reports.map(report => `<tr><td><span class="table-primary">${escapeHtml(report.title)}</span><span class="table-secondary">${escapeHtml(report.id)} · ${escapeHtml(report.category)}</span></td><td>${escapeHtml(report.location)}</td><td><span class="priority priority-${priorityClass(report.priority)}">${escapeHtml(report.severity)} · ${report.priority}</span></td><td><span class="status ${statusClass(report.status)}">${escapeHtml(report.status)}</span></td><td>${formatDate(report.createdAt)}</td><td><button class="link-button" data-report="${escapeHtml(report.id)}">Details</button></td></tr>`).join("")}</tbody></table></div>` : emptyState("Nothing to show", "Try another search, or change the status filter.", role() === "citizen" && !all.length ? "new-report" : "")}</section>`;
  }
  function renderWorkOrders() {
    const reports = visibleReports().filter(report => report.worker || ["Assigned", "In progress", "Awaiting verification"].includes(report.status)).sort((a, b) => b.priority - a.priority);
    const relevant = role() === "worker" ? reports.filter(report => report.worker === actor().name) : reports;
    const action = role() === "admin" || role() === "supervisor" ? `<button class="btn btn-outline btn-small" data-view="reports">Review new reports</button>` : "";
    return `${pageHeading("Work orders", role() === "worker" ? "Your assigned field jobs and repair updates." : "Assignments, field progress, and resolution checks.", action)}
      <section class="panel"><div class="panel-header"><div><h2 class="panel-title">${role() === "worker" ? "My assignments" : "Active assignments"}</h2><p class="panel-subtitle">Prioritized by severity and urgency</p></div><span class="status status-assigned">${relevant.length} active</span></div>
      ${relevant.length ? `<div class="data-table-wrap"><table class="data-table"><thead><tr><th>Work order</th><th>Department</th><th>Assigned to</th><th>Priority</th><th>Status</th><th>Next step</th></tr></thead><tbody>${relevant.map(report => `<tr><td><span class="table-primary">${escapeHtml(report.title)}</span><span class="table-secondary">WO-${escapeHtml(report.id.slice(3))}</span></td><td>${escapeHtml(report.department || "—")}</td><td>${escapeHtml(report.worker || "Unassigned")}</td><td><span class="priority priority-${priorityClass(report.priority)}">${escapeHtml(report.severity)} · ${report.priority}</span></td><td><span class="status ${statusClass(report.status)}">${escapeHtml(report.status)}</span></td><td>${workOrderAction(report)}</td></tr>`).join("")}</tbody></table></div>` : emptyState("No active work orders", "Approved reports will appear here once a crew is assigned.")}</section>`;
  }
  function workOrderAction(report) {
    if (role() === "worker" && report.worker === actor().name && report.status === "Assigned") return `<button class="btn btn-primary btn-small" data-action="start-work" data-id="${escapeHtml(report.id)}">Start work</button>`;
    if (role() === "worker" && report.worker === actor().name && report.status === "In progress") return `<button class="btn btn-primary btn-small" data-action="complete-work" data-id="${escapeHtml(report.id)}">Submit repair</button>`;
    if (canManage() && report.status === "Awaiting verification") return `<button class="btn btn-primary btn-small" data-action="verify-work" data-id="${escapeHtml(report.id)}">Verify</button>`;
    return `<button class="link-button" data-report="${escapeHtml(report.id)}">Details</button>`;
  }
  function renderDepartments() {
    const reports = state.reports;
    return `${pageHeading("Departments", "See how reports are routed across city teams.", role() === "admin" ? `<button class="btn btn-outline btn-small" data-action="add-department">＋ Add department</button>` : "")}
      <div class="department-grid">${departments.map(department => {
        const owned = reports.filter(report => report.department === department.name);
        const open = owned.filter(report => report.status !== "Resolved").length;
        const resolved = owned.length - open;
        return `<article class="department-card"><div class="department-top"><span class="department-icon">${department.icon}</span><span class="status ${open ? "status-in-progress" : "status-resolved"}">${open} open</span></div><h3>${escapeHtml(department.name)}</h3><p>${escapeHtml(department.description)}</p><div class="department-metrics"><div><strong>${owned.length}</strong><small>Total reports</small></div><div><strong>${resolved}</strong><small>Resolved</small></div><div><strong>${department.sla_hours}h</strong><small>Resolution SLA</small></div></div></article>`;
      }).join("")}</div>`;
  }
  function renderTeam() {
    const list = role() === "worker" ? staff.filter(person => person.name === actor().name) : staff;
    return `${pageHeading("Team", "Field staff, skills, and current workload.", role() === "admin" ? `<button class="btn btn-outline btn-small" data-action="add-staff">＋ Add staff member</button>` : "")}
      <div class="team-grid">${list.map(person => `<article class="team-card"><div class="team-person"><span class="avatar">${initials(person.name)}</span><div><strong>${escapeHtml(person.name)}</strong><small>${escapeHtml(person.department)} department</small></div></div><div class="team-load"><span>Active work orders</span><strong>${person.active}</strong></div><div class="team-load"><span>Skills</span><strong>${person.skills.map(escapeHtml).join(", ")}</strong></div></article>`).join("")}</div>`;
  }
  function renderAnalytics() {
    const reports = state.reports;
    const analytics = state.analytics || {};
    const resolved = reports.filter(report => report.status === "Resolved");
    const rates = analytics.departments || departments.map(department => ({ ...department, total: reports.filter(report => report.department === department.name).length, resolved: reports.filter(report => report.department === department.name && report.status === "Resolved").length, open: reports.filter(report => report.department === department.name && report.status !== "Resolved").length }));
    const ratingList = resolved.filter(report => report.feedback?.rating);
    const satisfaction = analytics.satisfactionPercent == null ? (ratingList.length ? `${Math.round(ratingList.reduce((sum, report) => sum + report.feedback.rating, 0) / ratingList.length * 20)}%` : "—") : `${analytics.satisfactionPercent}%`;
    const weeks = analytics.weekly || [];
    const maxWeek = Math.max(1, ...weeks.map(item => item.count));
    const geoReports = reports.filter(report => report.latitude !== null && report.longitude !== null);
    return `${pageHeading("Analytics", "A city-wide view of service requests and team performance.", `${role() === "admin" ? `<button class="btn btn-outline btn-small" id="run-escalations">↻ Run SLA check</button>` : ""}<button class="btn btn-outline btn-small" id="export-csv">↓ Export reports</button>`)}
      <div class="stat-grid">${metricCard("All reports", analytics.total ?? reports.length, "Across your service area", "▤")}${metricCard("Resolved", analytics.resolved ?? resolved.length, "Supervisor verified", "✓")}${metricCard("Avg. resolution", analytics.averageResolutionDays == null ? "—" : `${analytics.averageResolutionDays}d`, `${analytics.overdue || 0} overdue against department SLA`, "◷", !(analytics.overdue > 0))}${metricCard("Satisfaction", satisfaction, `${analytics.ratings ?? ratingList.length} citizen ratings`, "★")}</div>
      <div class="analytics-grid"><section class="panel"><div class="panel-header"><div><h2 class="panel-title">Reports over time</h2><p class="panel-subtitle">New reports by rolling week</p></div></div><div class="chart">${weeks.map((item, index) => `<div class="chart-col"><span class="chart-bar${index === weeks.length - 1 ? " active" : ""}" style="height:${Math.max(5, item.count / maxWeek * 100)}%" title="${item.count} reports"></span><small>${index === weeks.length - 1 ? "Now" : `${index + 1}w`}</small></div>`).join("")}</div><div class="chart-legend"><i></i> Reports submitted</div></section>
      <section class="panel"><div class="panel-header"><div><h2 class="panel-title">Where reports happen</h2><p class="panel-subtitle">Pins shown when a report includes location coordinates</p></div></div><div class="map-placeholder">${geoReports.map(report => {
        const x = Math.max(5, Math.min(93, ((report.longitude + 180) % 1) * 100));
        const y = Math.max(8, Math.min(88, ((report.latitude + 90) % 1) * 100));
        return `<span class="map-pin" title="${escapeHtml(report.title)}" style="left:${x}%;top:${y}%"></span>`;
      }).join("")}</div><div class="map-legend"><span>${geoReports.length} location-tagged reports</span><span>Browser-only map preview</span></div></section>
      <section class="panel wide-panel"><div class="panel-header"><div><h2 class="panel-title">Department performance & service targets</h2><p class="panel-subtitle">Resolution counts are based on verified closures; open issues beyond target are overdue.</p></div></div><div class="data-table-wrap"><table class="data-table"><thead><tr><th>Department</th><th>Reports</th><th>Resolved</th><th>Open</th><th>Resolution rate</th><th>SLA target</th></tr></thead><tbody>${rates.map(item => `<tr><td><span class="table-primary">${escapeHtml(item.name)}</span></td><td>${item.total}</td><td>${item.resolved}</td><td>${item.open ?? item.total - item.resolved}</td><td>${item.total ? Math.round(item.resolved / item.total * 100) : 0}%</td><td>${item.sla_hours}h</td></tr>`).join("")}</tbody></table></div></section>
      <section class="panel wide-panel"><div class="panel-header"><div><h2 class="panel-title">SLA watchlist</h2><p class="panel-subtitle">Overdue cases are automatically escalated to department supervisors and administrators.</p></div><span class="status ${analytics.overdue ? "status-awaiting-review" : "status-resolved"}">${analytics.overdue || 0} overdue</span></div>${analytics.overdueReports?.length ? `<div class="data-table-wrap"><table class="data-table"><thead><tr><th>Report</th><th>Department</th><th>Status</th><th>Overdue by</th><th>Escalation</th></tr></thead><tbody>${analytics.overdueReports.map(item => `<tr><td><span class="table-primary">${escapeHtml(item.title)}</span><span class="table-secondary">${escapeHtml(item.id)}</span></td><td>${escapeHtml(item.department)}</td><td>${escapeHtml(item.status)}</td><td>${item.overdueHours}h · ${item.slaHours}h target</td><td><span class="status ${item.escalationLevel ? "status-awaiting-review" : "status-open"}">Level ${item.escalationLevel}/3</span></td></tr>`).join("")}</tbody></table></div>` : emptyState("All service targets are on track", "No open reports have exceeded their department SLA.")}</section></div>`;
  }

  function renderAudit() {
    const entries = state.audit || [];
    return `${pageHeading("Audit trail", "A chronological record of administrative actions and issue status changes.")}<section class="panel"><div class="panel-header"><div><h2 class="panel-title">Recent activity</h2><p class="panel-subtitle">Most recent 500 recorded events · stored locally</p></div><span class="status status-assigned">${entries.length} events</span></div>${entries.length ? `<div class="data-table-wrap"><table class="data-table"><thead><tr><th>When</th><th>Who</th><th>Action</th><th>Record</th><th>Details</th></tr></thead><tbody>${entries.map(item => `<tr><td>${formatDate(item.createdAt, true)}</td><td>${escapeHtml(item.actor)}</td><td>${escapeHtml(item.action.replace(/_/g, " "))}</td><td>${escapeHtml(item.entityType)} · ${escapeHtml(item.entityId || "—")}</td><td>${escapeHtml(Object.entries(item.details || {}).map(([key, value]) => `${key}: ${value}`).join(" · ") || "—")}</td></tr>`).join("")}</tbody></table></div>` : emptyState("No audit events yet", "Administrative and workflow actions will be recorded here.")}</section>`;
  }
  function renderNotifications() {
    const notifications = state.notifications.filter(item => !item.recipientId || item.recipientId === actor().id);
    return `${pageHeading("Notifications", "Updates about reports and city service activity.", `<button class="btn btn-outline btn-small" id="mark-read">Mark all as read</button>`)}
      <div class="notifications-list">${notifications.length ? notifications.map(item => `<article class="notification-item${item.read ? "" : " unread"}"><span class="activity-icon">${item.reportId ? "▤" : "✓"}</span><div><p>${escapeHtml(item.message)}</p><small>${timeAgo(item.createdAt)}${item.reportId ? ` · ${escapeHtml(item.reportId)}` : ""}</small></div>${item.reportId ? `<button class="link-button" data-report="${escapeHtml(item.reportId)}">View</button>` : ""}</article>`).join("") : emptyState("You’re all caught up", "New updates will appear here.")}</div>`;
  }

  function bindApp() {
    document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => { activeView = button.dataset.view; render(); }));
    document.querySelectorAll("[data-action]").forEach(button => button.addEventListener("click", () => handleAction(button.dataset.action, button.dataset.id)));
    document.querySelectorAll("[data-report]").forEach(button => button.addEventListener("click", () => openReport(button.dataset.report)));
    document.getElementById("role-select")?.addEventListener("change", async event => {
      try {
        const result = await apiRequest("/api/auth/demo", { method: "POST", body: { role: event.target.value } });
        currentUser = result.user;
        activeView = "overview";
        await refreshState();
        render();
      } catch (error) { showApiError(error); }
    });
    document.getElementById("top-notifications")?.addEventListener("click", () => { activeView = "notifications"; render(); });
    document.getElementById("profile-button")?.addEventListener("click", () => { signOut(); });
    document.getElementById("report-search")?.addEventListener("input", event => { reportSearch = event.target.value; const cursor = event.target.selectionStart; render(); const input = document.getElementById("report-search"); input.focus(); input.setSelectionRange(cursor, cursor); });
    document.getElementById("report-filter")?.addEventListener("change", event => { reportFilter = event.target.value; render(); });
    document.getElementById("mark-read")?.addEventListener("click", async () => {
      try { await apiRequest("/api/notifications/read", { method: "POST", body: {} }); await refreshState(); render(); }
      catch (error) { showApiError(error); }
    });
    document.getElementById("export-csv")?.addEventListener("click", exportReports);
    document.getElementById("run-escalations")?.addEventListener("click", async () => {
      try {
        const result = await apiRequest("/api/escalations/run", { method: "POST", body: {} });
        await refreshState();
        render();
        toast(result.escalated ? `${result.escalated} SLA escalation(s) created.` : "SLA check complete; no new escalation was due.");
      } catch (error) { showApiError(error); }
    });
    document.getElementById("load-profile")?.addEventListener("click", async () => {
      try {
        const data = await apiRequest("/api/profile");
        const root = document.getElementById("profile-center");
        root.className = "detail-grid";
        root.innerHTML = `<div class="detail-item"><small>Name</small><strong>${escapeHtml(data.user.name)}</strong></div><div class="detail-item"><small>Email</small><strong>${escapeHtml(data.user.email)}</strong></div><div class="detail-item"><small>Role</small><strong>${escapeHtml(data.user.role)}</strong></div><div class="detail-item"><small>City</small><strong>${escapeHtml(data.profile.city || "Not set")}</strong></div><div class="detail-item"><small>Primary address</small><strong>${escapeHtml(data.addresses.find(item => item.is_primary)?.address_text || "Not set")}</strong></div><div class="detail-item"><small>Notifications</small><strong>${data.preferences.report_updates ? "Enabled" : "Limited"}</strong></div>`;
      } catch (error) { showApiError(error); }
    });
    document.getElementById("intelligence-form")?.addEventListener("submit", async event => {
      event.preventDefault();
      const description = document.getElementById("intel-description").value.trim();
      try {
        const [category, severity] = await Promise.all([
          apiRequest("/api/intelligence/categorize", { method: "POST", body: { description } }),
          apiRequest("/api/intelligence/severity", { method: "POST", body: { description, category: "Other", affectedPeople: 0 } })
        ]);
        document.getElementById("intel-result").innerHTML = `<strong>Category:</strong> ${escapeHtml(category.category)} · <strong>Confidence:</strong> ${category.confidence} · <strong>Severity:</strong> ${escapeHtml(severity.level)} (${severity.score}/100)`;
      } catch (error) { showApiError(error); }
    });
    document.getElementById("system-health")?.addEventListener("click", async () => {
      try {
        const data = await apiRequest("/api/admin/system-health", { method: "POST", body: {} });
        document.getElementById("health-result").innerHTML = `<strong>Database:</strong> ${escapeHtml(data.checks.database)} · <strong>Tables:</strong> ${data.tableCount} · <strong>Journal:</strong> ${escapeHtml(data.checks.journalMode)}`;
      } catch (error) { showApiError(error); }
    });
    document.getElementById("platform-search-form")?.addEventListener("submit", async event => {
      event.preventDefault();
      try {
        const query = document.getElementById("platform-search").value.trim();
        const data = await apiRequest(`/api/search?q=${encodeURIComponent(query)}`);
        const root = document.getElementById("platform-search-results");
        root.innerHTML = data.results.length ? data.results.slice(0, 8).map(item => `<div class="activity-item"><span class="activity-icon">⌕</span><div><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.document_type)} · score ${item.score} · ${escapeHtml(item.snippet)}</small></div></div>`).join("") : `<div class="empty-state"><span>⌕</span><strong>No results</strong><p>Try a broader term.</p></div>`;
      } catch (error) { showApiError(error); }
    });
  }

  async function signOut() {
    try { await apiRequest("/api/auth/logout", { method: "POST", body: {} }); }
    catch (error) { showApiError(error); }
    currentUser = null;
    authMode = "login";
    render();
  }

  function handleAction(action, reportId) {
    if (action === "new-report") return openReportForm();
    if (action === "add-department") return openDepartmentForm();
    if (action === "add-staff") return openStaffForm();
    const report = state.reports.find(item => item.id === reportId);
    if (!report) return;
    if (action === "start-work") {
      if (role() !== "worker" || report.worker !== actor().name || report.status !== "Assigned") return toast("This work order is not assigned to you.", true);
      apiRequest(`/api/reports/${encodeURIComponent(report.id)}/start`, { method: "POST", body: {} })
        .then(async () => { await refreshState(); render(); toast("Work order moved to in progress."); })
        .catch(showApiError);
    }
    if (action === "complete-work") return openCompletionForm(report);
    if (action === "verify-work") return openVerification(report);
  }

  function openApproval(report) {
    if (!canManage() || report.status !== "Awaiting review") return toast("This report is no longer awaiting review.", true);
    const preferredDepartment = departments.some(item => item.name === report.department) ? report.department : departments[0]?.name;
    const workersFor = department => staff.filter(person => person.department === department);
    const workers = workersFor(preferredDepartment);
    const preferredWorker = workers.some(person => person.name === recommendWorker(preferredDepartment, report.category))
      ? recommendWorker(preferredDepartment, report.category)
      : workers[0]?.name || "";
    showModal(`<div class="modal-head"><div><h2>Approve & assign report</h2><p>Create a work order and choose the team responsible for this repair.</p></div><button class="modal-close" data-close aria-label="Close">×</button></div>
      <form id="approval-form"><div class="form-field"><label for="assign-department">Department</label><select id="assign-department" required>${departments.map(item => `<option value="${escapeHtml(item.name)}" ${item.name === preferredDepartment ? "selected" : ""}>${escapeHtml(item.name)}</option>`).join("")}</select></div>
      <div class="form-field"><label for="assign-worker">Field worker</label><select id="assign-worker" required>${workers.map(item => `<option value="${escapeHtml(item.name)}" ${item.name === preferredWorker ? "selected" : ""}>${escapeHtml(item.name)} · ${item.active} active jobs</option>`).join("")}</select><span class="form-hint">Suggested based on skill match and current workload. You can choose another team member.</span></div>
      <div class="form-actions"><button type="button" class="btn" data-close>Cancel</button><button class="btn btn-primary" type="submit">Create work order</button></div></form>`);
    document.getElementById("assign-department").addEventListener("change", event => {
      const nextWorkers = workersFor(event.target.value);
      const workerSelect = document.getElementById("assign-worker");
      workerSelect.innerHTML = nextWorkers.map(item => `<option value="${escapeHtml(item.name)}">${escapeHtml(item.name)} · ${item.active} active jobs</option>`).join("");
      workerSelect.disabled = !nextWorkers.length;
    });
    document.getElementById("approval-form").addEventListener("submit", async event => {
      event.preventDefault();
      await approveReport(report.id);
    });
  }

  function openDepartmentForm() {
    if (role() !== "admin") return toast("Only administrators can add departments.", true);
    showModal(`<div class="modal-head"><div><h2>Add a department</h2><p>Departments help route reports to the right city team.</p></div><button class="modal-close" data-close aria-label="Close">×</button></div>
      <form id="department-form"><div class="form-field"><label for="department-name">Department name</label><input id="department-name" name="name" required minlength="2" maxlength="60" placeholder="e.g. Parks & Recreation"></div>
      <div class="form-field"><label for="department-description">What does this team handle?</label><input id="department-description" name="description" required minlength="8" maxlength="120" placeholder="A short description of the team's work"></div>
      <div class="form-field"><label for="department-sla">Resolution target (hours)</label><input id="department-sla" name="slaHours" type="number" min="1" max="8760" value="48" required><span class="form-hint">Used to identify overdue reports in city analytics.</span></div>
      <div class="form-actions"><button type="button" class="btn" data-close>Cancel</button><button class="btn btn-primary" type="submit">Add department</button></div></form>`);
    document.getElementById("department-form").addEventListener("submit", async event => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const name = String(form.get("name")).trim();
      const description = String(form.get("description")).trim();
      try {
        await apiRequest("/api/departments", {
          method: "POST",
          body: { name, description, slaHours: Number(form.get("slaHours")) }
        });
        await refreshState();
        closeModal(); render(); toast(`${name} department added.`);
      } catch (error) { showApiError(error); }
    });
  }

  function openStaffForm() {
    if (role() !== "admin") return toast("Only administrators can add staff.", true);
    showModal(`<div class="modal-head"><div><h2>Add a staff member</h2><p>Set a department and skills to improve work order recommendations.</p></div><button class="modal-close" data-close aria-label="Close">×</button></div>
      <form id="staff-form"><div class="form-field"><label for="staff-name">Name</label><input id="staff-name" name="name" required minlength="2" maxlength="60" placeholder="e.g. Robin Park"></div>
      <div class="form-field"><label for="staff-department">Department</label><select id="staff-department" name="department" required>${departments.map(item => `<option value="${escapeHtml(item.name)}">${escapeHtml(item.name)}</option>`).join("")}</select></div>
      <div class="form-field"><label for="staff-skills">Skills</label><select id="staff-skills" name="skills" multiple size="5" required>${categories.map(item => `<option value="${escapeHtml(item)}">${escapeHtml(item)}</option>`).join("")}</select><span class="form-hint">Select one or more skills (use Ctrl or Command to select multiple).</span></div>
      <div class="form-actions"><button type="button" class="btn" data-close>Cancel</button><button class="btn btn-primary" type="submit">Add team member</button></div></form>`);
    document.getElementById("staff-form").addEventListener("submit", async event => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const name = String(form.get("name")).trim();
      const skills = [...document.getElementById("staff-skills").selectedOptions].map(option => option.value);
      if (!skills.length) return toast("Select at least one skill.", true);
      try {
        await apiRequest("/api/staff", {
          method: "POST",
          body: { name, department: String(form.get("department")), skills }
        });
        await refreshState();
        closeModal(); render(); toast(`${name} added to the team.`);
      } catch (error) { showApiError(error); }
    });
  }

  function openReportForm() {
    if (role() !== "citizen") return toast("Switch to the citizen view to submit a report.", true);
    photoData = "";
    showModal(`<div class="modal-head"><div><h2>Report a neighborhood issue</h2><p>Share what is happening so the right city team can take a look.</p></div><button class="modal-close" data-close aria-label="Close">×</button></div>
      <form id="report-form"><div class="form-grid"><div class="form-field"><label for="report-category">Category</label><select name="category" id="report-category" required>${categories.map(item => `<option>${escapeHtml(item)}</option>`).join("")}</select></div>
      <div class="form-field"><label for="report-date">When did you notice it?</label><input id="report-date" name="date" type="datetime-local" value="${new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16)}" required></div>
      <div class="form-field form-span"><label for="report-description">What is the issue?</label><textarea id="report-description" name="description" minlength="12" maxlength="1000" required placeholder="Describe what you noticed and how it affects the area (12–1,000 characters)."></textarea></div>
      <div class="form-field form-span"><label for="report-location">Where is it?</label><input id="report-location" name="location" required maxlength="140" placeholder="Street, intersection, or nearby landmark"><button class="btn btn-outline btn-small" id="capture-location" type="button">⌖ Use my current location</button><span class="form-hint" id="geo-message">Location access is optional and provided by your browser.</span></div>
      <div class="form-field form-span"><label for="report-photo">Add a photo (optional)</label><input id="report-photo" name="photo" type="file" accept="image/png,image/jpeg,image/webp"><span class="form-hint">PNG, JPEG, or WebP · up to 2 MB. Images stay in this browser.</span><img class="photo-preview hidden" id="photo-preview" alt="Selected report photo preview"></div></div>
      <div class="form-actions"><button type="button" class="btn" data-close>Cancel</button><button class="btn btn-primary" type="submit">Submit report</button></div></form>`, true);
    document.getElementById("capture-location").addEventListener("click", captureLocation);
    document.getElementById("report-photo").addEventListener("change", readPhoto);
    document.getElementById("report-form").addEventListener("submit", submitReport);
  }

  let capturedCoordinates = { latitude: null, longitude: null };
  function captureLocation() {
    const message = document.getElementById("geo-message");
    if (!navigator.geolocation) { message.textContent = "This browser does not support location access."; return toast("Location is not supported by this browser.", true); }
    message.textContent = "Requesting permission…";
    navigator.geolocation.getCurrentPosition(position => {
      capturedCoordinates = { latitude: position.coords.latitude, longitude: position.coords.longitude };
      const input = document.getElementById("report-location");
      if (!input.value.trim()) input.value = `My location (${capturedCoordinates.latitude.toFixed(4)}, ${capturedCoordinates.longitude.toFixed(4)})`;
      message.textContent = "Location captured from your device. No map service is used.";
    }, error => {
      message.textContent = error.code === 1 ? "Location permission was denied. You can enter a landmark instead." : "Could not get your location. Enter a landmark instead.";
    }, { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 });
  }
  function readPhoto(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) { event.target.value = ""; return toast("Choose a PNG, JPEG, or WebP image.", true); }
    if (file.size > 2 * 1024 * 1024) { event.target.value = ""; return toast("The image must be 2 MB or smaller.", true); }
    const reader = new FileReader();
    reader.onload = () => {
      photoData = typeof reader.result === "string" ? reader.result : "";
      const preview = document.getElementById("photo-preview");
      preview.src = photoData;
      preview.classList.toggle("hidden", !photoData);
    };
    reader.onerror = () => toast("Could not read this image file.", true);
    reader.readAsDataURL(file);
  }
  async function submitReport(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const description = String(form.get("description")).trim();
    const location = String(form.get("location")).trim();
    const submitted = new Date(String(form.get("date"))).getTime();
    if (description.length < 12 || description.length > 1000 || !location || !Number.isFinite(submitted) || submitted > Date.now() + 60000) return toast("Check the description, location, and report date.", true);
    try {
      const result = await apiRequest("/api/reports", {
        method: "POST",
        body: {
          category: String(form.get("category")),
          description,
          location,
          reportedDate: submitted,
          latitude: capturedCoordinates.latitude,
          longitude: capturedCoordinates.longitude,
          image: safeImage(photoData)
        }
      });
      await refreshState();
      closeModal();
      capturedCoordinates = { latitude: null, longitude: null };
      activeView = "reports";
      render();
      toast(result.duplicateOf
        ? `Report submitted and linked for review with ${result.duplicateOf}.`
        : `Report ${result.reportId} submitted.`);
    } catch (error) { showApiError(error); }
  }

  function openReport(id) {
    const report = state.reports.find(item => item.id === id);
    if (!report) return;
    if (role() === "citizen" && report.citizenId !== actor().id) return toast("You can only view your own reports.", true);
    if (role() === "worker" && report.worker !== actor().name && report.department !== actor().department) return toast("This report is outside your assigned work.", true);
    modalReportId = id;
    const actions = reportActions(report);
    showModal(`<div class="modal-head"><div><h2>${escapeHtml(report.title)}</h2><p>${escapeHtml(report.id)} · reported ${formatDate(report.createdAt, true)}</p></div><button class="modal-close" data-close aria-label="Close">×</button></div>
      ${report.duplicateOf ? `<div class="duplicate-warning">This report may be related to <button class="text-button" data-report="${escapeHtml(report.duplicateOf)}">${escapeHtml(report.duplicateOf)}</button>. Each citizen report remains visible; the city team can coordinate one repair.</div>` : ""}
      ${report.image ? `<img class="photo-preview" src="${safeImage(report.image)}" alt="Photo submitted with this report">` : ""}
      <div class="detail-grid"><div class="detail-item"><small>Status</small><strong><span class="status ${statusClass(report.status)}">${escapeHtml(report.status)}</span></strong></div><div class="detail-item"><small>Category & severity</small><strong>${escapeHtml(report.category)} · ${escapeHtml(report.severity)}</strong></div><div class="detail-item"><small>Location</small><strong>${escapeHtml(report.location)}</strong></div><div class="detail-item"><small>Department & priority</small><strong>${escapeHtml(report.department || "Pending")} · ${report.priority}/100</strong></div><div class="detail-item"><small>Reported by</small><strong>${escapeHtml(report.citizen)}</strong></div><div class="detail-item"><small>Assigned worker</small><strong>${escapeHtml(report.worker || "Awaiting assignment")}</strong></div></div>
      <p class="detail-description">${escapeHtml(report.description)}</p>
      ${report.resolution ? `<div class="detail-item"><small>Resolution details</small><strong>${escapeHtml(report.resolution)}</strong></div>` : ""}
      ${report.feedback ? `<div class="detail-item"><small>Citizen feedback · ${"★".repeat(report.feedback.rating)}${"☆".repeat(5 - report.feedback.rating)}</small><strong>${escapeHtml(report.feedback.comment || "No comment provided.")}</strong></div>` : ""}
      <div class="history"><div class="panel-title" style="margin:0 0 13px">Report history</div>${(report.history || []).slice().reverse().map(entry => `<div class="history-entry"><strong>${escapeHtml(entry.status)}${entry.note ? ` · ${escapeHtml(entry.note)}` : ""}</strong><small>${escapeHtml(entry.by)} · ${formatDate(entry.at, true)}</small></div>`).join("")}</div>
      ${actions ? `<div class="form-actions">${actions}</div>` : ""}`, true);
    document.querySelectorAll("#modal [data-action]").forEach(button => button.addEventListener("click", () => {
      const action = button.dataset.action;
      if (action === "approve-report") return openApproval(report);
      if (action === "leave-feedback") return openFeedback(report);
      if (action === "reopen-report") return openReopenForm(report);
      closeModal();
      handleAction(action, id);
    }));
    document.querySelectorAll("#modal [data-report]").forEach(button => button.addEventListener("click", () => openReport(button.dataset.report)));
  }
  function reportActions(report) {
    if (canManage() && report.status === "Awaiting review") return `<button class="btn btn-primary btn-small" data-action="approve-report">Approve & assign</button>`;
    if (role() === "citizen" && report.status === "Resolved") return `${report.feedback ? "" : `<button class="btn btn-primary btn-small" data-action="leave-feedback">Leave feedback</button>`}<button class="btn btn-outline btn-small" data-action="reopen-report">Request follow-up</button>`;
    return "";
  }

  function showModal(content, wide = false) {
    closeModal();
    const backdrop = document.createElement("div");
    backdrop.id = "modal";
    backdrop.className = "modal-backdrop";
    backdrop.innerHTML = `<section class="modal${wide ? " modal-wide" : ""}" role="dialog" aria-modal="true">${content}</section>`;
    backdrop.addEventListener("click", event => { if (event.target === backdrop || event.target.closest("[data-close]")) closeModal(); });
    document.body.append(backdrop);
    backdrop.querySelector("input,select,textarea,button")?.focus();
    document.addEventListener("keydown", onModalKeydown);
  }
  function onModalKeydown(event) { if (event.key === "Escape") closeModal(); }
  function closeModal() {
    document.getElementById("modal")?.remove();
    document.removeEventListener("keydown", onModalKeydown);
    modalReportId = null;
  }

  async function approveReport(reportId) {
    const report = state.reports.find(item => item.id === reportId);
    if (!report || !canManage() || report.status !== "Awaiting review") return toast("This report is no longer awaiting review.", true);
    const departmentInput = document.getElementById("assign-department");
    const workerInput = document.getElementById("assign-worker");
    if (!departmentInput || !workerInput) return toast("Choose a department and worker before approving.", true);
    try {
      await apiRequest(`/api/reports/${encodeURIComponent(reportId)}/approve`, {
        method: "POST",
        body: { department: departmentInput.value, worker: workerInput.value }
      });
      await refreshState();
      closeModal();
      render();
      toast("Report approved and work order created.");
    } catch (error) { showApiError(error); }
  }

  function openCompletionForm(report) {
    showModal(`<div class="modal-head"><div><h2>Submit repair for verification</h2><p>${escapeHtml(report.id)} · ${escapeHtml(report.title)}</p></div><button class="modal-close" data-close aria-label="Close">×</button></div>
      <form id="completion-form"><div class="form-field"><label for="resolution-notes">Work completed</label><textarea id="resolution-notes" name="notes" minlength="8" maxlength="700" required placeholder="Describe the repair and anything the supervisor should know."></textarea></div>
      <div class="form-field"><label for="resolution-photo">After photo (optional)</label><input id="resolution-photo" name="photo" type="file" accept="image/png,image/jpeg,image/webp"><span class="form-hint">PNG, JPEG, or WebP · up to 2 MB. Stored locally.</span></div>
      <div class="form-actions"><button type="button" class="btn" data-close>Cancel</button><button class="btn btn-primary" type="submit">Send for verification</button></div></form>`, false);
    let completionPhoto = "";
    document.getElementById("resolution-photo").addEventListener("change", event => {
      const file = event.target.files?.[0]; if (!file) return;
      if (!["image/png", "image/jpeg", "image/webp"].includes(file.type) || file.size > 2 * 1024 * 1024) { event.target.value = ""; return toast("Choose a PNG, JPEG, or WebP image up to 2 MB.", true); }
      const reader = new FileReader(); reader.onload = () => { completionPhoto = safeImage(reader.result); }; reader.onerror = () => toast("Could not read this image file.", true); reader.readAsDataURL(file);
    });
    document.getElementById("completion-form").addEventListener("submit", async event => {
      event.preventDefault();
      const notes = String(new FormData(event.currentTarget).get("notes")).trim();
      if (notes.length < 8) return toast("Add a little more detail about the repair.", true);
      try {
        await apiRequest(`/api/reports/${encodeURIComponent(report.id)}/complete`, {
          method: "POST", body: { notes, image: completionPhoto }
        });
        await refreshState();
        closeModal(); render(); toast("Repair submitted for supervisor verification.");
      } catch (error) { showApiError(error); }
    });
  }

  function openVerification(report) {
    showModal(`<div class="modal-head"><div><h2>Verify completed work</h2><p>Confirm the repair before notifying the resident.</p></div><button class="modal-close" data-close aria-label="Close">×</button></div>
      <div class="detail-item"><small>Work notes from ${escapeHtml(report.worker || "field staff")}</small><strong>${escapeHtml(report.resolution || "No notes provided.")}</strong></div>
      ${report.resolutionImage ? `<img class="photo-preview" src="${safeImage(report.resolutionImage)}" alt="Worker resolution photo">` : ""}
      <form id="verify-form"><div class="form-field" style="margin-top:16px"><label for="verification-note">Verification note (required if rejected)</label><textarea name="note" id="verification-note" maxlength="500" placeholder="Add a note for the work order history."></textarea></div>
      <div class="form-actions"><button type="button" class="btn btn-danger" id="reject-work">Reject & reassign</button><button class="btn btn-primary" type="submit">Approve resolution</button></div></form>`);
    document.getElementById("verify-form").addEventListener("submit", async event => {
      event.preventDefault();
      if (!canManage() || report.status !== "Awaiting verification") return toast("This repair is no longer awaiting verification.", true);
      const note = String(new FormData(event.currentTarget).get("note")).trim();
      try {
        await apiRequest(`/api/reports/${encodeURIComponent(report.id)}/verify`, {
          method: "POST", body: { approve: true, note }
        });
        await refreshState();
        closeModal(); render(); toast("Resolution verified; the citizen has been notified.");
      } catch (error) { showApiError(error); }
    });
    document.getElementById("reject-work").addEventListener("click", async () => {
      const note = document.getElementById("verification-note").value.trim();
      if (!note) return toast("Add a short reason before rejecting this repair.", true);
      if (!canManage() || report.status !== "Awaiting verification") return toast("This repair is no longer awaiting verification.", true);
      try {
        await apiRequest(`/api/reports/${encodeURIComponent(report.id)}/verify`, {
          method: "POST", body: { approve: false, note }
        });
        await refreshState();
        closeModal(); render(); toast("Repair rejected and reassigned.");
      } catch (error) { showApiError(error); }
    });
  }

  function openFeedback(report) {
    showModal(`<div class="modal-head"><div><h2>How did we do?</h2><p>Your feedback helps the city improve its service.</p></div><button class="modal-close" data-close aria-label="Close">×</button></div>
      <form id="feedback-form"><div class="form-field"><label for="feedback-rating">How satisfied are you?</label><select name="rating" id="feedback-rating" required><option value="5">★★★★★ — Very satisfied</option><option value="4">★★★★☆ — Satisfied</option><option value="3">★★★☆☆ — It was okay</option><option value="2">★★☆☆☆ — Not satisfied</option><option value="1">★☆☆☆☆ — Not at all satisfied</option></select></div>
      <div class="form-field"><label for="feedback-comment">Anything else? (optional)</label><textarea name="comment" id="feedback-comment" maxlength="500" placeholder="Tell us about your experience."></textarea></div>
      <div class="form-actions"><button type="button" class="btn" data-close>Cancel</button><button class="btn btn-primary" type="submit">Send feedback</button></div></form>`);
    document.getElementById("feedback-form").addEventListener("submit", async event => {
      event.preventDefault();
      if (report.status !== "Resolved" || report.feedback) return toast("Feedback is unavailable for this report.", true);
      const form = new FormData(event.currentTarget);
      try {
        await apiRequest(`/api/reports/${encodeURIComponent(report.id)}/feedback`, {
          method: "POST",
          body: { rating: Number(form.get("rating")), comment: String(form.get("comment")).trim() }
        });
        await refreshState();
        closeModal(); render(); toast("Thanks for helping make CivicFlow better.");
      } catch (error) { showApiError(error); }
    });
  }

  function openReopenForm(report) {
    if (role() !== "citizen" || report.citizenId !== actor().id || report.status !== "Resolved") return toast("Only the reporting citizen can request a follow-up.", true);
    showModal(`<div class="modal-head"><div><h2>Request a follow-up</h2><p>Tell the city team why this issue still needs attention.</p></div><button class="modal-close" data-close aria-label="Close">×</button></div>
      <form id="reopen-form"><div class="form-field"><label for="reopen-reason">What still needs to be fixed?</label><textarea id="reopen-reason" name="reason" required minlength="8" maxlength="500" placeholder="Describe what is still wrong or needs another visit."></textarea></div>
      <div class="form-actions"><button type="button" class="btn" data-close>Cancel</button><button class="btn btn-primary" type="submit">Send follow-up request</button></div></form>`);
    document.getElementById("reopen-form").addEventListener("submit", async event => {
      event.preventDefault();
      const reason = String(new FormData(event.currentTarget).get("reason")).trim();
      if (reason.length < 8 || report.status !== "Resolved") return toast("Add a reason of at least 8 characters.", true);
      try {
        await apiRequest(`/api/reports/${encodeURIComponent(report.id)}/reopen`, {
          method: "POST", body: { reason }
        });
        await refreshState();
        closeModal(); render(); toast("Follow-up request sent to the city team.");
      } catch (error) { showApiError(error); }
    });
  }

  async function exportReports() {
    try {
      const response = await fetch("/api/export.csv", { credentials: "same-origin" });
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.error || `Export failed (${response.status}).`);
      }
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a"); link.href = url; link.download = "civicflow-reports.csv"; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (error) { showApiError(error); }
  }

  async function startApp() {
    backendError = "";
    try {
      const response = await fetch("/api/state", { credentials: "same-origin" });
      if (response.status === 401) {
        apiReady = true;
        currentUser = null;
        render();
        return;
      }
      if (!response.ok) throw new Error(`CivicFlow server returned ${response.status}.`);
      const payload = await response.json();
      state = payload;
      currentUser = payload.user;
      departments = payload.departments;
      staff = payload.staff;
      apiReady = true;
      render();
    } catch (error) {
      apiReady = false;
      backendError = "Could not connect to CivicFlow. Start the Python service with: python -m backend";
      console.error("CivicFlow backend is unavailable.", error);
      render();
    }
  }

  startApp();
})();
