const state = {
  view: "dashboard",
  listType: "people",
  page: 1,
  listTagId: "",
  listOwnerUserId: "",
  listProfileField: "",
  listProfileValue: "",
  listSort: {
    people: { field: "updated_at", direction: "desc" },
    companies: { field: "updated_at", direction: "desc" },
    leads: { field: "updated_at", direction: "desc" },
    deals: { field: "updated_at", direction: "desc" },
  },
  listStatusFilters: {
    people: { field: "", value: "" },
    companies: { field: "", value: "" },
    leads: { field: "", value: "" },
    deals: { field: "", value: "" },
  },
  listDateFilters: {
    people: { field: "", from: "", to: "" },
    companies: { field: "", from: "", to: "" },
    leads: { field: "", from: "", to: "" },
    deals: { field: "", from: "", to: "" },
  },
  listQualityIssues: {
    people: "",
    companies: "",
    leads: "",
    deals: "",
  },
  listProvenanceFilters: {
    people: "",
    companies: "",
    leads: "",
    deals: "",
  },
  listSavedViewId: {
    people: "",
    companies: "",
    leads: "",
    deals: "",
  },
  taskPage: 1,
  taskStatus: "open",
  taskQ: "",
  taskRecordType: "",
  taskSource: "",
  taskSort: "due_date",
  taskDirection: "asc",
  taskSavedViewId: "",
  tagPage: 1,
  tagQ: "",
  tagRecordType: "",
  tagSavedViewId: "",
  customFieldPage: 1,
  customFieldQ: "",
  customFieldRecordType: "",
  customFieldSavedViewId: "",
  linkedResourcePage: 1,
  linkedResourceQ: "",
  linkedResourceKind: "",
  linkedResourceRecordType: "",
  linkedResourceSavedViewId: "",
  archivePage: 1,
  archiveQ: "",
  archiveItemType: "",
  archiveRecordType: "",
  archivePreset: "",
  archiveReviewStatus: "",
  archiveTriageLane: "",
  archiveDateFrom: "",
  archiveDateTo: "",
  archiveSavedViewId: "",
  archiveLastItems: [],
  activityQ: "",
  activityType: "",
  activityRecordType: "",
  activityDateFrom: "",
  activityDateTo: "",
  activitySavedViewId: "",
  cleanupGroupType: "duplicate_people",
  cleanupStatus: "open",
  cleanupGroupPage: 1,
  cleanupGroupQ: "",
  cleanupPriority: "",
  cleanupPolicyLane: "",
  cleanupDecision: "",
  cleanupSort: "priority",
  currentCleanupGroup: null,
  q: "",
  debounce: null,
  currentDetail: null,
  currentArchiveItem: null,
  auth: null,
  appUsers: null,
  editingAppUserId: null,
  appUserNotice: null,
};

const els = {
  status: document.querySelector("#statusText"),
  environmentBadge: document.querySelector("#environmentBadge"),
  dashboard: document.querySelector("#dashboardView"),
  migrationStatus: document.querySelector("#migrationStatusView"),
  list: document.querySelector("#listView"),
  tags: document.querySelector("#tagsView"),
  customFields: document.querySelector("#customFieldsView"),
  linkedResources: document.querySelector("#linkedResourcesView"),
  archive: document.querySelector("#archiveView"),
  followup: document.querySelector("#followupView"),
  activity: document.querySelector("#activityView"),
  exports: document.querySelector("#exportsView"),
  users: document.querySelector("#usersView"),
  cleanup: document.querySelector("#cleanupView"),
  detail: document.querySelector("#detailPanel"),
  search: document.querySelector("#globalSearch"),
  navButtons: document.querySelectorAll(".nav-button"),
  authControl: document.querySelector("#authControl"),
  authOverlay: document.querySelector("#authOverlay"),
  authLoginForm: document.querySelector("#authLoginForm"),
  authMessage: document.querySelector("#authMessage"),
  ownerRecoveryOpen: document.querySelector("#ownerRecoveryOpen"),
  ownerRecoveryOverlay: document.querySelector("#ownerRecoveryOverlay"),
  ownerRecoveryForm: document.querySelector("#ownerRecoveryForm"),
  ownerRecoveryMessage: document.querySelector("#ownerRecoveryMessage"),
  passwordOverlay: document.querySelector("#passwordOverlay"),
  passwordChangeForm: document.querySelector("#passwordChangeForm"),
  passwordMessage: document.querySelector("#passwordMessage"),
};

const listTitles = {
  people: "People",
  companies: "Companies",
  leads: "Leads",
  deals: "Deals",
};

const listSortOptions = {
  people: [
    ["updated_at", "Updated"],
    ["created_at", "Created"],
    ["name", "Name"],
    ["email", "Email"],
    ["phone", "Phone"],
    ["status", "Status"],
    ["owner", "Owner"],
    ["customer_status", "Customer Status"],
    ["prospect_status", "Prospect Status"],
  ],
  companies: [
    ["updated_at", "Updated"],
    ["created_at", "Created"],
    ["name", "Name"],
    ["email", "Email"],
    ["phone", "Phone"],
    ["status", "Status"],
    ["owner", "Owner"],
    ["customer_status", "Customer Status"],
    ["prospect_status", "Prospect Status"],
  ],
  leads: [
    ["updated_at", "Updated"],
    ["created_at", "Created"],
    ["name", "Name"],
    ["organization_name", "Organization"],
    ["email", "Email"],
    ["phone", "Phone"],
    ["status", "Status"],
    ["owner", "Owner"],
  ],
  deals: [
    ["updated_at", "Updated"],
    ["created_at", "Created"],
    ["name", "Name"],
    ["stage", "Stage"],
    ["value", "Value"],
    ["contact", "Contact"],
    ["estimated_close_date", "Close Date"],
  ],
};

const listQualityIssueLabels = {
  people: {
    missing_contact: "No email or phone/mobile",
    missing_email: "Missing email",
    missing_phone: "Missing phone/mobile",
    missing_owner: "Missing owner",
  },
  companies: {
    missing_contact: "No email or phone",
    missing_email: "Missing email",
    missing_phone: "Missing phone",
    missing_owner: "Missing owner",
  },
  leads: {
    missing_email: "Missing email",
    missing_contact: "No email or phone/mobile",
    missing_phone: "Missing phone/mobile",
    missing_owner: "Missing owner",
  },
  deals: {
    missing_value: "Missing value",
    missing_relationship: "No contact/company",
    missing_stage: "Missing stage",
  },
};

const cleanupGroupTypes = [
  { type: "duplicate_people", label: "Duplicate People" },
  { type: "duplicate_leads", label: "Duplicate Leads" },
  { type: "lead_person_overlap", label: "Lead/Person Overlap" },
  { type: "duplicate_tags", label: "Duplicate Tags" },
];

const cleanupStatuses = [
  { status: "open", label: "Open" },
  { status: "ignored", label: "Ignored" },
  { status: "resolved", label: "Resolved" },
];

const cleanupPriorities = [
  { value: "", label: "All priorities" },
  { value: "high", label: "High priority" },
  { value: "medium", label: "Medium priority" },
  { value: "low", label: "Low priority" },
];

const cleanupPolicyLanes = [
  { value: "", label: "All lanes" },
  { value: "policy_review_overlap", label: "Lead/person policy review" },
  { value: "priority_review", label: "Priority manual review" },
  { value: "conflict_heavy_review", label: "Conflict-heavy review" },
  { value: "multi_record_review", label: "Multi-record review" },
  { value: "short_guided_review", label: "Short guided review" },
  { value: "tag_batch_candidate", label: "Tag batch candidate" },
];

const cleanupDecisionOptions = [
  { value: "needs_review", label: "Needs Review" },
  { value: "merge_later", label: "Merge Later" },
  { value: "keep_separate", label: "Keep Separate" },
  { value: "already_handled", label: "Already Handled" },
  { value: "false_positive", label: "False Positive" },
];

const cleanupDecisionFilters = [
  { value: "", label: "All decisions" },
  { value: "review_remaining", label: "Review remaining" },
  { value: "none", label: "No decision" },
  ...cleanupDecisionOptions,
];

const cleanupSortOptions = [
  { value: "priority", label: "Sort by Priority" },
  { value: "policy", label: "Sort by Guided Lane" },
  { value: "flags", label: "Sort by Flags" },
  { value: "records", label: "Sort by Records" },
  { value: "email", label: "Sort by Email" },
  { value: "decision", label: "Sort by Decision" },
];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatNumber(value) {
  return new Intl.NumberFormat().format(value ?? 0);
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (!bytes) return "0 bytes";
  const units = ["bytes", "KB", "MB", "GB"];
  let size = bytes;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  const maximumFractionDigits = unitIndex === 0 ? 0 : 1;
  return `${new Intl.NumberFormat(undefined, { maximumFractionDigits }).format(size)} ${units[unitIndex]}`;
}

function formatMoney(value, currency = "USD") {
  if (!value) return "$0";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    let message = text;
    let payload = null;
    try {
      payload = JSON.parse(text);
      message = payload.error || payload.message || text;
    } catch {
      message = text;
    }
    if (response.status === 401 && payload?.auth) {
      state.auth = payload.auth;
      renderAuthControl();
      showAuthOverlay(payload.auth);
    }
    throw new Error(message || `Request failed with status ${response.status}`);
  }
  return response.json();
}

async function postJson(url, payload) {
  return fetchJson(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

function setStatus(text) {
  els.status.textContent = text;
}

function setRuntimeContext(runtime = {}) {
  if (!els.environmentBadge) return;
  const environment = runtime.environment || "local";
  const label = runtime.environment_label || labelize(environment);
  els.environmentBadge.textContent = label;
  els.environmentBadge.dataset.environment = environment;
  const lockMode = runtime.remote_write_lock?.mode;
  els.environmentBadge.title = lockMode ? `${label} · Write lock ${lockMode}` : label;
}

function renderAuthControl() {
  if (!els.authControl) return;
  const auth = state.auth || {};
  updateOwnerNavigation();
  if (!auth.auth_required) {
    els.authControl.hidden = true;
    els.authControl.innerHTML = "";
    return;
  }
  els.authControl.hidden = false;
  const user = auth.user;
  if (!user) {
    els.authControl.innerHTML = `<span class="auth-user">Signed out</span>`;
    return;
  }
  els.authControl.innerHTML = `
    <span class="auth-user">${escapeHtml(user.display_name || user.email || "Signed in")}</span>
    <button class="auth-change-password" type="button">Password</button>
    <button class="auth-logout" type="button">Sign Out</button>
  `;
  els.authControl.querySelector(".auth-change-password")?.addEventListener("click", () => {
    showPasswordOverlay(true);
  });
  els.authControl.querySelector(".auth-logout")?.addEventListener("click", async () => {
    setStatus("Signing out");
    await postJson("/api/auth/logout", {});
    state.auth = await fetchJson("/api/auth/status");
    state.appUsers = null;
    state.editingAppUserId = null;
    state.appUserNotice = null;
    renderAuthControl();
    showAuthOverlay(state.auth);
    setStatus("Signed out");
  });
}

function currentUserRoles() {
  return new Set(((state.auth || {}).user?.roles || []).map((role) => String(role || "").toLowerCase()));
}

function currentUserCanManageUsers() {
  return currentUserRoles().has("owner");
}

function updateOwnerNavigation() {
  const canManageUsers = currentUserCanManageUsers();
  document.querySelectorAll(".owner-only-nav").forEach((button) => {
    button.hidden = !canManageUsers;
  });
  if (!canManageUsers && state.view === "users") {
    state.view = "dashboard";
  }
}

function showAuthOverlay(auth = state.auth || {}) {
  if (!els.authOverlay) return;
  if (els.ownerRecoveryOpen) {
    els.ownerRecoveryOpen.hidden = !auth.owner_password_recovery_enabled;
  }
  if (!auth.auth_required || auth.authenticated) {
    els.authOverlay.hidden = true;
    if (els.authMessage) els.authMessage.textContent = "";
    return;
  }
  els.authOverlay.hidden = false;
  const emailInput = els.authLoginForm?.querySelector('input[name="email"]');
  if (emailInput && !emailInput.value) emailInput.focus();
}

function showOwnerRecoveryOverlay(open) {
  if (!els.ownerRecoveryOverlay || !els.ownerRecoveryForm) return;
  els.ownerRecoveryOverlay.hidden = !open;
  if (!open) {
    els.ownerRecoveryForm.reset();
    if (els.ownerRecoveryMessage) els.ownerRecoveryMessage.textContent = "";
    return;
  }
  const loginEmail = els.authLoginForm?.querySelector('input[name="email"]')?.value || "";
  const recoveryEmail = els.ownerRecoveryForm.querySelector('input[name="email"]');
  if (recoveryEmail && loginEmail && !recoveryEmail.value) recoveryEmail.value = loginEmail;
  if (els.ownerRecoveryMessage) els.ownerRecoveryMessage.textContent = "";
  recoveryEmail?.focus();
}

async function submitOwnerRecovery(form, button) {
  const email = form.querySelector('input[name="email"]')?.value || "";
  const newPassword = form.querySelector('input[name="new_password"]')?.value || "";
  const confirmPassword = form.querySelector('input[name="confirm_password"]')?.value || "";
  if (newPassword.length < 12) {
    if (els.ownerRecoveryMessage) els.ownerRecoveryMessage.textContent = "Use at least 12 characters.";
    return;
  }
  if (newPassword !== confirmPassword) {
    if (els.ownerRecoveryMessage) els.ownerRecoveryMessage.textContent = "Passwords do not match.";
    return;
  }
  if (button) button.disabled = true;
  try {
    setStatus("Recovering owner access");
    const result = await postJson("/api/auth/owner_password_recovery", {
      email,
      new_password: newPassword,
    });
    state.auth = result.auth || (await fetchJson("/api/auth/status"));
    renderAuthControl();
    showOwnerRecoveryOverlay(false);
    showAuthOverlay(state.auth);
    await renderDashboard();
    setStatus("Ready");
  } catch (error) {
    if (els.ownerRecoveryMessage) els.ownerRecoveryMessage.textContent = error.message;
    setStatus("Owner recovery failed");
  } finally {
    if (button) button.disabled = false;
  }
}

function showPasswordOverlay(open) {
  if (!els.passwordOverlay || !els.passwordChangeForm) return;
  els.passwordOverlay.hidden = !open;
  if (!open) {
    els.passwordChangeForm.reset();
    if (els.passwordMessage) els.passwordMessage.textContent = "";
    return;
  }
  if (els.passwordMessage) els.passwordMessage.textContent = "";
  els.passwordChangeForm.querySelector('input[name="current_password"]')?.focus();
}

async function submitPasswordChange(form, button) {
  const currentPassword = form.querySelector('input[name="current_password"]')?.value || "";
  const newPassword = form.querySelector('input[name="new_password"]')?.value || "";
  const confirmPassword = form.querySelector('input[name="confirm_password"]')?.value || "";
  if (newPassword.length < 12) {
    if (els.passwordMessage) els.passwordMessage.textContent = "Use at least 12 characters.";
    return;
  }
  if (newPassword !== confirmPassword) {
    if (els.passwordMessage) els.passwordMessage.textContent = "Passwords do not match.";
    return;
  }
  if (button) button.disabled = true;
  try {
    setStatus("Changing password");
    const result = await postJson("/api/auth/change_password", {
      current_password: currentPassword,
      new_password: newPassword,
    });
    state.auth = result.auth || (await fetchJson("/api/auth/status"));
    renderAuthControl();
    showPasswordOverlay(false);
    setStatus("Password changed");
  } catch (error) {
    if (els.passwordMessage) els.passwordMessage.textContent = error.message;
    setStatus("Password change failed");
  } finally {
    if (button) button.disabled = false;
  }
}

async function initializeAuth() {
  state.auth = await fetchJson("/api/auth/status");
  renderAuthControl();
  showAuthOverlay(state.auth);
  return !state.auth.auth_required || state.auth.authenticated;
}

function showDetailFormError(message) {
  const errorBox = document.querySelector("#detailFormError");
  if (!errorBox) return;
  errorBox.textContent = message || "Something went wrong.";
  errorBox.hidden = false;
}

function clearDetailFormError() {
  const errorBox = document.querySelector("#detailFormError");
  if (!errorBox) return;
  errorBox.textContent = "";
  errorBox.hidden = true;
}

function showDetailActionError(message) {
  const errorBox = document.querySelector("#detailActionError") || document.querySelector("#detailFormError");
  if (!errorBox) return;
  errorBox.textContent = message || "Something went wrong.";
  errorBox.hidden = false;
}

function clearDetailActionError() {
  const errorBox = document.querySelector("#detailActionError") || document.querySelector("#detailFormError");
  if (!errorBox) return;
  errorBox.textContent = "";
  errorBox.hidden = true;
}

async function copyTextToClipboard(value) {
  const text = String(value || "").trim();
  if (!text) throw new Error("Nothing to copy.");
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  textarea.remove();
  if (!copied) throw new Error("Copy is not available in this browser.");
}

async function runDetailAction(button, labels, action) {
  clearDetailActionError();
  button.disabled = true;
  try {
    setStatus(labels.progress);
    await action();
    setStatus(labels.success);
  } catch (error) {
    showDetailActionError(error.message);
    setStatus(labels.failure || "Action failed");
  } finally {
    button.disabled = false;
  }
}

function setView(view) {
  if (view === "users" && !currentUserCanManageUsers()) {
    view = "dashboard";
  }
  state.view = view;
  state.page = 1;
  updateOwnerNavigation();
  els.navButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
  });
  els.dashboard.classList.toggle("active-view", view === "dashboard");
  els.migrationStatus.classList.toggle("active-view", view === "migrationStatus");
  els.list.classList.toggle("active-view", ["people", "companies", "leads", "deals"].includes(view));
  els.tags.classList.toggle("active-view", view === "tags");
  els.customFields.classList.toggle("active-view", view === "customFields");
  els.linkedResources.classList.toggle("active-view", view === "linkedResources");
  els.archive.classList.toggle("active-view", view === "archive");
  els.followup.classList.toggle("active-view", view === "followup");
  els.activity.classList.toggle("active-view", view === "activity");
  els.exports.classList.toggle("active-view", view === "exports");
  els.users.classList.toggle("active-view", view === "users");
  els.cleanup.classList.toggle("active-view", view === "cleanup");
  if (view === "migrationStatus") {
    renderMigrationStatus();
  } else if (["people", "companies", "leads", "deals"].includes(view)) {
    state.listType = view;
    if (!profileFilterSupported(view)) {
      state.listProfileField = "";
      state.listProfileValue = "";
    }
    if (!ownerFilterSupported(view)) {
      state.listOwnerUserId = "";
    }
    renderList();
  } else if (view === "followup") {
    renderFollowup();
  } else if (view === "tags") {
    state.tagPage = 1;
    renderTags();
  } else if (view === "customFields") {
    state.customFieldPage = 1;
    renderCustomFields();
  } else if (view === "linkedResources") {
    state.linkedResourcePage = 1;
    renderLinkedResources();
  } else if (view === "archive") {
    state.archivePage = 1;
    renderArchive();
  } else if (view === "activity") {
    renderActivity();
  } else if (view === "exports") {
    renderExports();
  } else if (view === "users") {
    renderUsers();
  } else if (view === "cleanup") {
    renderCleanup();
  } else {
    renderDashboard();
  }
}

function roleLabel(roleKey, roles = []) {
  const match = roles.find((role) => role.role_key === roleKey);
  return match?.label || labelize(roleKey);
}

function roleCheckboxes(roles = [], selected = [], name = "roles") {
  const selectedSet = new Set((selected || []).map((role) => String(role || "")));
  return `
    <div class="role-check-grid">
      ${roles
        .map((role) => {
          const roleKey = role.role_key || "";
          return `
            <label class="role-check">
              <input type="checkbox" name="${escapeHtml(name)}" value="${escapeHtml(roleKey)}" ${selectedSet.has(roleKey) ? "checked" : ""}>
              <span>
                <strong>${escapeHtml(role.label || labelize(roleKey))}</strong>
                <small>${escapeHtml(role.description || "")}</small>
              </span>
            </label>
          `;
        })
        .join("")}
    </div>
  `;
}

function appUserRolePills(user, roles = []) {
  const roleKeys = user.roles || [];
  if (!roleKeys.length) return `<span class="muted">No roles</span>`;
  return `
    <div class="role-pill-list">
      ${roleKeys.map((role) => `<span class="pill gold">${escapeHtml(roleLabel(role, roles))}</span>`).join("")}
    </div>
  `;
}

function appUserStatusPill(status) {
  const value = String(status || "active").toLowerCase();
  const tone = value === "active" ? "green" : "coral";
  return `<span class="pill ${tone}">${escapeHtml(labelize(value))}</span>`;
}

function appUserNoticePanel() {
  const notice = state.appUserNotice;
  if (!notice) return "";
  const tone = notice.tone || "green";
  const password = notice.temporaryPassword || "";
  return `
    <div class="app-user-notice ${escapeHtml(tone)}">
      <div>
        <strong>${escapeHtml(notice.title || "Users updated")}</strong>
        <p>${escapeHtml(notice.message || "")}</p>
        ${
          password
            ? `<div class="temporary-password-row">
                <input id="appUserTemporaryPassword" type="text" readonly value="${escapeHtml(password)}">
                <button type="button" class="text-button" id="copyTemporaryPassword">Copy</button>
              </div>`
            : ""
        }
      </div>
      <button type="button" class="icon-button" id="dismissAppUserNotice" title="Dismiss">×</button>
    </div>
  `;
}

function collectRoleSelections(form) {
  const roles = Array.from(form.querySelectorAll('input[name="roles"]:checked')).map((input) => input.value);
  if (!roles.length) {
    throw new Error("Choose at least one role.");
  }
  return roles;
}

function appUserCreatePanel(data) {
  return `
    <div class="band app-user-form-panel">
      <div class="band-header">
        <h3>Add User</h3>
      </div>
      <form id="appUserCreateForm" class="app-user-form">
        <div class="admin-form-grid">
          <label>
            <span>Email</span>
            <input name="email" type="email" autocomplete="off" required>
          </label>
          <label>
            <span>Name</span>
            <input name="display_name" type="text" autocomplete="off">
          </label>
          <label>
            <span>Password</span>
            <input name="password" type="text" autocomplete="new-password" placeholder="Generate if blank">
          </label>
          <label class="inline-check">
            <input name="generate_password" type="checkbox" checked>
            <span>Generate password</span>
          </label>
        </div>
        ${roleCheckboxes(data.roles || [], ["read_only"])}
        <div class="form-actions">
          <button type="submit" class="text-button">Create User</button>
        </div>
      </form>
    </div>
  `;
}

function appUserEditPanel(data) {
  const user = (data.users || []).find((item) => String(item.id) === String(state.editingAppUserId));
  if (!user) return "";
  return `
    <div class="band app-user-form-panel">
      <div class="band-header">
        <div>
          <h3>Edit User</h3>
          <p>${escapeHtml(user.email || "")}</p>
        </div>
        <button type="button" class="text-button app-user-cancel-edit">Close</button>
      </div>
      <form id="appUserEditForm" class="app-user-form" data-user-id="${escapeHtml(user.id)}">
        <div class="admin-form-grid two">
          <label>
            <span>Email</span>
            <input name="email" type="email" value="${escapeHtml(user.email || "")}" readonly>
          </label>
          <label>
            <span>Name</span>
            <input name="display_name" type="text" value="${escapeHtml(user.display_name || "")}" autocomplete="off">
          </label>
        </div>
        ${roleCheckboxes(data.roles || [], user.roles || [])}
        <div class="form-actions">
          <button type="submit" class="text-button">Save User</button>
          <button type="button" class="text-button app-user-reset-password-button" data-user-id="${escapeHtml(user.id)}">Reset Password</button>
          ${
            user.status === "active"
              ? `<button type="button" class="text-button danger app-user-deactivate-button" data-user-id="${escapeHtml(user.id)}">Deactivate</button>`
              : `<button type="button" class="text-button app-user-reactivate-button" data-user-id="${escapeHtml(user.id)}">Reactivate</button>`
          }
        </div>
      </form>
    </div>
  `;
}

function appUsersTable(data) {
  const users = data.users || [];
  if (!users.length) return `<div class="empty-state"><h3>No users</h3><p>No app users were returned.</p></div>`;
  return `
    <div class="table-scroll">
      <table class="data-table app-users-table">
        <thead>
          <tr>
            <th>User</th>
            <th>Status</th>
            <th>Roles</th>
            <th>Last Login</th>
            <th>Password</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${users
            .map((user) => `
              <tr class="${String(user.id) === String(state.editingAppUserId) ? "active-record-row" : ""}">
                <td>
                  <strong>${escapeHtml(user.display_name || user.email || "")}</strong>
                  <span class="muted block">${escapeHtml(user.email || "")}</span>
                </td>
                <td>${appUserStatusPill(user.status)}</td>
                <td>${appUserRolePills(user, data.roles || [])}</td>
                <td>${escapeHtml(formatDate(user.last_login_at) || "Never")}</td>
                <td>${escapeHtml(formatDate(user.password_updated_at) || "Not set")}</td>
                <td><button type="button" class="text-button app-user-edit-button" data-user-id="${escapeHtml(user.id)}">Edit</button></td>
              </tr>
            `)
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

async function renderUsers() {
  if (!els.users) return;
  if (!currentUserCanManageUsers()) {
    els.users.innerHTML = `<div class="empty-state"><h3>Users unavailable</h3><p>Your current role cannot manage users.</p></div>`;
    setStatus("Ready");
    return;
  }
  setStatus("Loading users");
  try {
    const data = await fetchJson("/api/app_users");
    state.appUsers = data;
    const activeUsers = (data.users || []).filter((user) => user.status === "active").length;
    const ownerUsers = (data.users || []).filter((user) => user.status === "active" && (user.roles || []).includes("owner")).length;
    els.users.innerHTML = `
      <div class="section-header">
        <div>
          <h2>Users</h2>
          <p>${formatNumber(activeUsers)} active · ${formatNumber(ownerUsers)} owner</p>
        </div>
      </div>
      ${appUserNoticePanel()}
      <div class="metric-grid compact">
        ${metric("Active Users", activeUsers)}
        ${metric("Owners", ownerUsers)}
        ${metric("Roles", (data.roles || []).length)}
        ${metric("Permission Groups", Object.keys(data.permission_actions || {}).length)}
      </div>
      ${appUserCreatePanel(data)}
      ${appUserEditPanel(data)}
      <div class="band">
        <div class="band-header">
          <h3>Current Users</h3>
          <span class="muted">${formatNumber((data.users || []).length)} total</span>
        </div>
        ${appUsersTable(data)}
      </div>
    `;
    wireAppUserAdmin(els.users);
    setStatus("Ready");
  } catch (error) {
    els.users.innerHTML = `<div class="empty-state"><h3>Could not load users</h3><p>${escapeHtml(error.message)}</p></div>`;
    setStatus("Users unavailable");
  }
}

async function saveAppUserFromForm(form, button) {
  if (button) button.disabled = true;
  try {
    setStatus("Saving user");
    const payload = {
      email: form.querySelector('input[name="email"]')?.value || "",
      display_name: form.querySelector('input[name="display_name"]')?.value || "",
      roles: collectRoleSelections(form),
    };
    const password = form.querySelector('input[name="password"]')?.value || "";
    const generatePassword = form.querySelector('input[name="generate_password"]')?.checked;
    if (password) payload.password = password;
    if (generatePassword) payload.generate_password = true;
    const result = await postJson("/api/app_users/save", payload);
    state.editingAppUserId = result.user?.id || state.editingAppUserId;
    state.appUserNotice = {
      tone: "green",
      title: "User saved",
      message: result.temporary_password ? "Temporary password generated." : "The user record is current.",
      temporaryPassword: result.temporary_password || "",
    };
    await renderUsers();
  } catch (error) {
    state.appUserNotice = { tone: "coral", title: "User update failed", message: error.message };
    await renderUsers();
  } finally {
    if (button) button.disabled = false;
  }
}

async function changeAppUserStatus(userId, endpoint, successTitle) {
  setStatus(successTitle);
  try {
    const result = await postJson(endpoint, { id: userId });
    state.appUserNotice = {
      tone: "green",
      title: successTitle,
      message: `${result.user?.email || "User"} is ${labelize(result.user?.status || "updated")}.`,
    };
    await renderUsers();
  } catch (error) {
    state.appUserNotice = { tone: "coral", title: "User status failed", message: error.message };
    await renderUsers();
  }
}

async function resetAppUserPassword(userId) {
  setStatus("Resetting password");
  try {
    const result = await postJson("/api/app_users/set_password", { id: userId });
    state.appUserNotice = {
      tone: "green",
      title: "Password reset",
      message: `Temporary password generated for ${result.user?.email || "user"}.`,
      temporaryPassword: result.temporary_password || "",
    };
    await renderUsers();
  } catch (error) {
    state.appUserNotice = { tone: "coral", title: "Password reset failed", message: error.message };
    await renderUsers();
  }
}

function wireAppUserAdmin(root) {
  root.querySelector("#dismissAppUserNotice")?.addEventListener("click", () => {
    state.appUserNotice = null;
    renderUsers();
  });
  root.querySelector("#copyTemporaryPassword")?.addEventListener("click", async () => {
    const input = root.querySelector("#appUserTemporaryPassword");
    if (!input?.value) return;
    await copyTextToClipboard(input.value);
    setStatus("Password copied");
  });
  root.querySelector("#appUserCreateForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await saveAppUserFromForm(event.currentTarget, event.submitter);
  });
  root.querySelector("#appUserEditForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await saveAppUserFromForm(event.currentTarget, event.submitter);
  });
  root.querySelectorAll(".app-user-edit-button").forEach((button) => {
    button.addEventListener("click", () => {
      state.editingAppUserId = button.dataset.userId;
      state.appUserNotice = null;
      renderUsers();
    });
  });
  root.querySelector(".app-user-cancel-edit")?.addEventListener("click", () => {
    state.editingAppUserId = null;
    renderUsers();
  });
  root.querySelectorAll(".app-user-deactivate-button").forEach((button) => {
    button.addEventListener("click", () => changeAppUserStatus(button.dataset.userId, "/api/app_users/deactivate", "User deactivated"));
  });
  root.querySelectorAll(".app-user-reactivate-button").forEach((button) => {
    button.addEventListener("click", () => changeAppUserStatus(button.dataset.userId, "/api/app_users/reactivate", "User reactivated"));
  });
  root.querySelectorAll(".app-user-reset-password-button").forEach((button) => {
    button.addEventListener("click", () => resetAppUserPassword(button.dataset.userId));
  });
}

function metric(label, value, className = "") {
  return `
    <div class="metric ${className}">
      <div class="metric-label">${escapeHtml(label)}</div>
      <div class="metric-value">${formatNumber(value)}</div>
    </div>
  `;
}

async function renderDashboard() {
  setStatus("Loading dashboard");
  const data = await fetchJson("/api/summary");
  setRuntimeContext(data.runtime);
  const maxDeals = Math.max(...data.pipeline.map((stage) => stage.deal_count), 1);
  els.dashboard.innerHTML = `
    <div class="section-header">
      <div>
        <h2>Dashboard</h2>
        <p>${formatNumber(data.counts.people + data.counts.companies + data.counts.leads)} client and lead records</p>
      </div>
    </div>
    ${startTodayPanel(data.start_today)}
    <div class="metric-grid">
      ${metric("People", data.counts.people)}
      ${metric("Companies", data.counts.companies)}
      ${metric("Leads", data.counts.leads)}
      ${metric("Deals", data.counts.deals)}
      ${metric("Notes", data.counts.notes)}
      ${metric("Open Tasks", data.counts.open_tasks)}
      ${metric("Overdue", data.counts.overdue_tasks, "metric-alert")}
      ${metric("Due Soon", data.counts.due_soon_tasks)}
      ${metric("Tags", data.counts.tags)}
      ${metric("Archive", data.counts.archive_items || 0)}
    </div>
    ${cleanupSummarySection(data.cleanup_summary || {})}
    ${savedViewsSection(data.saved_views || [])}
    ${applicationSegmentSection(data.profile_segments || [])}
    <div class="band">
      <div class="band-header">
        <h3>Sales Pipeline</h3>
        <span class="muted">${formatNumber(data.counts.deals)} deals</span>
      </div>
      <div class="pipeline">
        ${data.pipeline
          .map((stage) => {
            const width = Math.max(3, Math.round((stage.deal_count / maxDeals) * 100));
            return `
              <div class="stage">
                <div class="stage-name">${escapeHtml(stage.name)}</div>
                <div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div>
                <div class="stage-count">${formatNumber(stage.deal_count)} deals</div>
                <div class="stage-value">${formatMoney(stage.total_value)}</div>
              </div>
            `;
          })
          .join("")}
      </div>
    </div>
    <div class="band">
      <div class="band-header">
        <h3>Follow Up</h3>
        <button class="text-button nav-jump" data-view="followup">Open</button>
      </div>
      ${taskTable(data.upcoming_tasks, true)}
    </div>
    <div class="band">
      <div class="band-header">
        <h3>Recently Updated</h3>
      </div>
      ${recordTable(data.recently_updated, "recent")}
    </div>
  `;
  wireRecordButtons(els.dashboard);
  wireTaskButtons(els.dashboard);
  wireNavJumps(els.dashboard);
  wireNextAction(els.dashboard);
  wireWorkQueuePresets(els.dashboard);
  wireSavedViewButtons(els.dashboard, data.saved_views || []);
  wireCleanupSummaryButtons(els.dashboard);
  wireProfileSegmentButtons(els.dashboard);
  setStatus("Ready");
}

function startTodayPanel(start) {
  if (!start?.title) return "";
  const next = start.next_action || {};
  const steps = start.steps || [];
  const tone = start.status === "ready" ? "green" : start.status === "attention" ? "coral" : "gold";
  return `
    <div class="band start-today-panel ${escapeHtml(start.status || "")}">
      <div class="band-header">
        <div>
          <h3>${escapeHtml(start.title || "Start Today")}</h3>
          <p>${escapeHtml(start.message || "")}</p>
        </div>
        <div class="start-today-actions">
          <span class="pill ${tone}">${escapeHtml(labelize(start.status || "waiting"))}</span>
          <button type="button" class="text-button nav-jump" data-view="${escapeHtml(start.view || "migrationStatus")}">${escapeHtml(start.action || "Open Status")}</button>
          ${start.report ? `<a class="text-button action-link" href="${escapeHtml(start.report)}" target="_blank" rel="noreferrer">Open Guide</a>` : ""}
          ${start.export_url ? `<a class="text-button action-link" href="${escapeHtml(start.export_url)}">Export Guide</a>` : ""}
        </div>
      </div>
      <div class="start-today-body">
        <div class="start-next-card">
          <span class="eyebrow">Next Action${next.eyebrow ? ` · ${escapeHtml(next.eyebrow)}` : ""}</span>
          <strong>${escapeHtml(next.title || "Review Status")}</strong>
          <p>${escapeHtml(next.description || "")}</p>
          ${nextActionChoices(next, true)}
          <div class="start-next-actions">
            ${
              next.decision_key
                ? `<button type="button" class="text-button next-action-decision" data-key="${escapeHtml(next.decision_key)}">${escapeHtml(next.primary_action || "Open Decision")}</button>`
                : `<button type="button" class="text-button nav-jump" data-view="${escapeHtml(next.view || "migrationStatus")}">${escapeHtml(next.primary_action || "Open")}</button>`
            }
            ${next.report ? `<a class="text-button action-link" href="${escapeHtml(next.report)}" target="_blank" rel="noreferrer">Evidence</a>` : ""}
            ${worksheetActionLinks(next)}
          </div>
        </div>
        ${
          steps.length
            ? `<div class="start-guide-steps">
                ${steps.map((step) => startTodayStep(step)).join("")}
              </div>`
            : ""
        }
      </div>
    </div>
  `;
}

function startTodayStep(step) {
  const tone = step.status === "ready" || step.status === "complete" ? "green" : step.status === "attention" ? "coral" : "gold";
  const button = step.preset
    ? `<button type="button" class="text-button work-queue-preset" data-preset="${escapeHtml(step.preset)}">${escapeHtml(step.action || "Open")}</button>`
    : step.view
      ? `<button type="button" class="text-button nav-jump" data-view="${escapeHtml(step.view)}">${escapeHtml(step.action || "Open")}</button>`
      : "";
  return `
    <div class="start-guide-step ${escapeHtml(step.status || "")}">
      <div>
        <span class="step-pill">Step ${escapeHtml(step.order || "")}</span>
        <span class="pill ${tone}">${escapeHtml(labelize(step.status || "waiting"))}</span>
        <strong>${escapeHtml(step.title || "")}</strong>
      </div>
      ${button}
    </div>
  `;
}

function cleanupSummarySection(summary) {
  if (!summary.open_groups) return "";
  const priorityCounts = summary.priority_counts || {};
  return `
    <div class="band">
      <div class="band-header">
        <h3>Cleanup Review</h3>
        <span class="muted">${formatNumber(summary.open_groups)} open groups · High ${formatNumber(priorityCounts.High || 0)} · Medium ${formatNumber(priorityCounts.Medium || 0)} · Low ${formatNumber(priorityCounts.Low || 0)}</span>
      </div>
      <div class="cleanup-summary-grid">
        ${(summary.groups || [])
          .map((group) => `
            <button class="cleanup-summary-button" data-type="${escapeHtml(group.type)}">
              <strong>${escapeHtml(group.label)}</strong>
              <span>${formatNumber(group.open_groups)} open groups</span>
              <small>${cleanupPrioritySummary(group.priority_counts || {})}</small>
              ${group.top_group ? `<em>${escapeHtml(group.top_group.label || group.top_group.group_key || "")}</em>` : ""}
            </button>
          `)
          .join("")}
      </div>
    </div>
  `;
}

function cleanupPrioritySummary(counts) {
  return `High ${formatNumber(counts.High || 0)} · Medium ${formatNumber(counts.Medium || 0)} · Low ${formatNumber(counts.Low || 0)}`;
}

async function renderMigrationStatus() {
  setStatus("Loading status");
  const data = await fetchJson("/api/migration_status");
  setRuntimeContext(data.runtime);
  const account = data.snapshot?.account || {};
  const sweep = data.optional_sweep || {};
  const cleanup = data.cleanup || {};
  const statusCounts = cleanup.status_counts || {};
  const decisionCounts = cleanup.decision_counts || {};
  const openGroups = cleanup.summary?.open_groups || 0;
  const latestBackup = data.backups?.latest;
  const archiveAssociation = data.imported_archive?.association || {};
  const archiveAssociationSummary = archiveAssociation.summary || {};
  els.migrationStatus.innerHTML = `
    <div class="section-header">
      <div>
        <h2>Migration Status</h2>
        <p>${escapeHtml(account.name || "Zendesk Sell")} · ${escapeHtml(data.snapshot?.snapshot_name || "No snapshot")}</p>
      </div>
    </div>
    <div class="metric-grid">
      ${metric("People", data.counts.people)}
      ${metric("Companies", data.counts.companies)}
      ${metric("Leads", data.counts.leads)}
      ${metric("Deals", data.counts.deals)}
      ${metric("Notes", data.counts.notes)}
      ${metric("Tasks", data.counts.tasks)}
      ${metric("Tags", data.counts.tags)}
      ${metric("Linked Resources", data.counts.linked_resources)}
      ${metric("Archive Items", data.counts.archive_items)}
      ${metric("Open Flags", statusCounts.open || 0, Number(statusCounts.open || 0) ? "metric-alert" : "")}
    </div>
    ${productionGatePanel(data.production_gates)}
    ${migrationReadiness(data.readiness || [])}
    ${nextActionPanel(data.next_action)}
    ${dailyOperatingGuidePanel(data.daily_guide)}
    ${decisionPrepPacketPanel(data.decision_prep)}
    ${cleanupStarterPacketPanel(data.cleanup_starter)}
    ${operationalWorkQueuePanel(data.operational_work_queue)}
    ${projectDecisionCenter(data.project_decisions)}
    ${cleanupExecutionPreviewPanel(data.cleanup_execution_preview)}
    ${cleanupExecutionPreviewPanel(data.recommended_execution_preview, "Recommended Path Simulation")}
    <div class="status-grid">
      <div class="band">
        <div class="band-header">
          <h3>Zendesk Snapshot</h3>
          ${statusPill("Core Imported", "ok")}
        </div>
        <dl class="kv">
          <dt>Snapshot</dt><dd>${escapeHtml(data.snapshot?.snapshot_name || "Unknown")}</dd>
          <dt>Created</dt><dd>${escapeHtml(formatDate(data.snapshot?.created_at) || "Unknown")}</dd>
          <dt>Account</dt><dd>${escapeHtml(account.name || "Unknown")}</dd>
          <dt>Exports</dt><dd>${formatNumber(data.snapshot?.export_count || 0)} captured files</dd>
        </dl>
      </div>
      <div class="band">
        <div class="band-header">
          <h3>Final Zendesk Sweep</h3>
          ${statusPill(sweep.status === "complete" ? "Complete" : "Waiting", sweep.status === "complete" ? "ok" : "warn")}
        </div>
        <p>${escapeHtml(sweep.message || "")}</p>
        <dl class="kv">
          <dt>Extended endpoints</dt><dd>${sweep.include_extended ? "Captured" : "Not captured yet"}</dd>
          <dt>Document files</dt><dd>${sweep.download_documents ? "Download attempted" : "Not downloaded yet"}</dd>
          <dt>Token available now</dt><dd>${sweep.token_available ? "Yes" : "No"}</dd>
        </dl>
      </div>
      <div class="band">
        <div class="band-header">
          <h3>Cleanup Review</h3>
          <button class="text-button nav-jump" data-view="cleanup">Open Cleanup</button>
        </div>
        <div class="cleanup-detail-signals">
          <div class="signal"><strong>${formatNumber(openGroups)}</strong><span>Open groups</span></div>
          <div class="signal"><strong>${formatNumber(statusCounts.open || 0)}</strong><span>Open flags</span></div>
          <div class="signal"><strong>${formatNumber(statusCounts.resolved || 0)}</strong><span>Resolved flags</span></div>
        </div>
        ${statusCountList(decisionCounts, "Saved decisions")}
      </div>
      <div class="band">
        <div class="band-header">
          <h3>Linked Resources</h3>
          <button class="text-button nav-jump" data-view="linkedResources">Open Links</button>
        </div>
        <div class="cleanup-detail-signals">
          <div class="signal"><strong>${formatNumber(data.linked_resources?.total || 0)}</strong><span>Total links</span></div>
          <div class="signal"><strong>${formatNumber(linkedKindCount(data, "Call Recording Folder"))}</strong><span>Call folders</span></div>
          <div class="signal"><strong>${formatNumber(linkedKindCount(data, "Profile/Web Link") + linkedKindCount(data, "Profile Link"))}</strong><span>Profile links</span></div>
        </div>
        ${linkedResourceKindList(data.linked_resources?.kind_counts || [])}
      </div>
      <div class="band">
        <div class="band-header">
          <h3>Imported Archive</h3>
          <div class="inline-actions">
            <button class="text-button nav-jump" data-view="archive">Open Archive</button>
            <a class="text-button action-link" href="${escapeHtml(archiveAssociation.report || "/reports/archive_association_audit.md")}" target="_blank" rel="noreferrer">Audit</a>
          </div>
        </div>
        <div class="cleanup-detail-signals">
          <div class="signal"><strong>${formatNumber(data.imported_archive?.total || 0)}</strong><span>Total items</span></div>
          <div class="signal"><strong>${formatNumber(archiveAssociationSummary.linked_archive_items || 0)}</strong><span>Linked items</span></div>
          <div class="signal"><strong>${formatNumber(archiveAssociationSummary.unlinked_archive_items || 0)}</strong><span>Unlinked items</span></div>
        </div>
        ${archiveAssociationMiniList(archiveAssociation)}
        ${archiveStatusCountList(data.imported_archive?.type_counts || [])}
      </div>
      <div class="band">
        <div class="band-header">
          <h3>Backups</h3>
          <div class="inline-actions">
            <button class="text-button nav-jump" data-view="cleanup">Manage</button>
            <a class="text-button action-link" href="/reports/backup_safety_ledger.md" target="_blank" rel="noreferrer">Report</a>
            <a class="text-button action-link" href="/api/export?type=backup_safety_ledger">CSV</a>
          </div>
        </div>
        <dl class="kv">
          <dt>Saved backups</dt><dd>${formatNumber(data.backups?.count || 0)}</dd>
          <dt>Latest</dt><dd>${escapeHtml(latestBackup?.name || "No backups yet")}</dd>
          <dt>Modified</dt><dd>${escapeHtml(formatDate(latestBackup?.modified_at) || "")}</dd>
        </dl>
      </div>
      <div class="band">
        <div class="band-header"><h3>Verification Reports</h3></div>
        <div class="report-links">
          ${(data.reports || [])
            .map((report) =>
              report.exists
                ? `<a href="${escapeHtml(report.url)}" target="_blank" rel="noreferrer">${escapeHtml(report.name)}</a>`
                : `<span class="muted">${escapeHtml(report.name)} missing</span>`
            )
            .join("")}
        </div>
      </div>
    </div>
  `;
  wireReadinessButtons(els.migrationStatus);
  wireNextAction(els.migrationStatus);
  wireDecisionPrepPacket(els.migrationStatus);
  wireCleanupGroupButtons(els.migrationStatus);
  wireProjectDecisionForms(els.migrationStatus);
  wireNavJumps(els.migrationStatus);
  wireRecordButtons(els.migrationStatus);
  wireTaskButtons(els.migrationStatus);
  wireSavedViewButtons(els.migrationStatus, data.operational_work_queue?.saved_views || []);
  wireWorkQueuePresets(els.migrationStatus);
  setStatus("Ready");
}

function nextActionPanel(action) {
  if (!action?.title) return "";
  const metrics = (action.metrics || []).filter((item) => item.label);
  const tone = action.status === "ready" ? "green" : action.status === "attention" ? "coral" : "gold";
  const decisionKey = action.decision_key || "";
  return `
    <div class="band next-action-band ${escapeHtml(action.status || "")}">
      <div class="band-header">
        <div>
          <h3>Next Action</h3>
          <p>${escapeHtml(action.eyebrow || "")}</p>
        </div>
        <span class="pill ${tone}">${escapeHtml(labelize(action.status || "waiting"))}</span>
      </div>
      <div class="next-action-body">
        <div class="next-action-copy">
          <strong>${escapeHtml(action.title)}</strong>
          <p>${escapeHtml(action.description || "")}</p>
          ${action.why ? `<small>${escapeHtml(action.why)}</small>` : ""}
          ${action.recommended_label ? `<small>Recommended: ${escapeHtml([action.recommended_code, action.recommended_label].filter(Boolean).join(". "))}</small>` : ""}
          ${nextActionChoices(action)}
        </div>
        ${
          metrics.length
            ? `<div class="next-action-metrics">
                ${metrics
                  .map((item) => `<span><strong>${escapeHtml(formatImpactValue(item.value))}</strong>${escapeHtml(item.label)}</span>`)
                  .join("")}
              </div>`
            : ""
        }
        <div class="next-action-buttons">
          ${
            decisionKey
              ? `<button type="button" class="text-button next-action-decision" data-key="${escapeHtml(decisionKey)}">${escapeHtml(action.primary_action || "Open Decision")}</button>`
              : `<button type="button" class="text-button nav-jump" data-view="${escapeHtml(action.view || "migrationStatus")}">${escapeHtml(action.primary_action || "Open")}</button>`
          }
          ${
            decisionKey && action.recommended_value && action.secondary_action
              ? `<button type="button" class="text-button next-action-fill" data-key="${escapeHtml(decisionKey)}">${escapeHtml(action.secondary_action)}</button>`
              : ""
          }
          ${action.related_view && action.related_view !== action.view ? `<button type="button" class="text-button nav-jump" data-view="${escapeHtml(action.related_view)}">Open ${escapeHtml(labelize(action.related_view))}</button>` : ""}
          ${action.report ? `<a class="text-button action-link" href="${escapeHtml(action.report)}" target="_blank" rel="noreferrer">Evidence</a>` : ""}
          ${worksheetActionLinks(action)}
        </div>
      </div>
    </div>
  `;
}

function worksheetActionLinks(item, label = "Worksheet") {
  if (!item?.worksheet_report && !item?.worksheet_export_url) return "";
  return `
    ${item.worksheet_report ? `<a class="text-button action-link" href="${escapeHtml(item.worksheet_report)}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a>` : ""}
    ${item.worksheet_export_url ? `<a class="text-button action-link" href="${escapeHtml(item.worksheet_export_url)}">${escapeHtml(label)} CSV</a>` : ""}
  `;
}

function nextActionChoices(action, compact = false) {
  const choices = action.choices || [];
  if (!choices.length) return "";
  return `
    <div class="next-action-choices ${compact ? "compact" : ""}">
      <span>${compact ? "Choices" : "Answer Choices"}</span>
      <div>
        ${choices
          .map(
            (choice) => `
              <small class="${choice.recommended ? "recommended" : ""}">
                <strong>${escapeHtml(choice.code || "")}</strong>
                ${escapeHtml(choice.label || "")}
                ${choice.recommended ? `<em>Recommended</em>` : ""}
              </small>
            `
          )
          .join("")}
      </div>
    </div>
  `;
}

function decisionPrepPacketPanel(packet) {
  if (!packet?.message) return "";
  const decisions = packet.decisions || [];
  const visibleDecisions = decisions.slice(0, 4);
  const tone = packet.status === "ready" ? "green" : "gold";
  return `
    <div class="band decision-prep-band ${escapeHtml(packet.status || "")}">
      <div class="band-header">
        <div>
          <h3>${escapeHtml(packet.title || "Decision Prep Packet")}</h3>
          <p>${escapeHtml(packet.message || "")}</p>
        </div>
        <span class="pill ${tone}">${escapeHtml(labelize(packet.status || "waiting"))}</span>
      </div>
      <div class="decision-prep-summary">
        <span><strong>${formatNumber(packet.remaining_count || 0)}</strong>remaining</span>
        <span><strong>${formatNumber(packet.pending_count || 0)}</strong>pending</span>
        <span><strong>${formatNumber(packet.decided_count || 0)}</strong>decided</span>
        <span><strong>${formatNumber(packet.deferred_count || 0)}</strong>deferred</span>
      </div>
      ${
        visibleDecisions.length
          ? `<div class="decision-prep-list">
              ${visibleDecisions.map((decision) => decisionPrepRow(decision)).join("")}
            </div>`
          : ""
      }
      <div class="decision-prep-actions">
        ${
          packet.next_decision_key
            ? `<button type="button" class="text-button decision-prep-focus" data-key="${escapeHtml(packet.next_decision_key)}">Open Next Decision</button>`
            : ""
        }
        ${packet.export_url ? `<a class="text-button action-link" href="${escapeHtml(packet.export_url)}">Export Packet</a>` : ""}
        ${packet.report ? `<a class="text-button action-link" href="${escapeHtml(packet.report)}" target="_blank" rel="noreferrer">Open Sequence</a>` : ""}
        ${packet.brief_report ? `<a class="text-button action-link" href="${escapeHtml(packet.brief_report)}" target="_blank" rel="noreferrer">Open Brief</a>` : ""}
      </div>
    </div>
  `;
}

function decisionPrepRow(decision) {
  const facts = (decision.facts || []).slice(0, 3);
  return `
    <div class="decision-prep-row">
      <div class="decision-prep-row-main">
        <span class="step-pill">Step ${escapeHtml(decision.step || "")}</span>
        ${projectDecisionStatusPill(decision.status)}
        <strong>${escapeHtml(decision.title || "")}</strong>
        <p>${escapeHtml(decision.why || decision.impact_summary || "")}</p>
        ${decision.recommended_label ? `<small>Recommended: ${escapeHtml(decision.recommended_label)}</small>` : ""}
      </div>
      <div class="decision-prep-facts">
        ${facts.map((fact) => `<span><strong>${escapeHtml(formatImpactValue(fact.value))}</strong>${escapeHtml(fact.label || "")}</span>`).join("")}
      </div>
      <div class="decision-prep-row-actions">
        ${decision.key ? `<button type="button" class="text-button decision-prep-focus" data-key="${escapeHtml(decision.key)}">Open</button>` : ""}
        ${decision.report ? `<a class="text-button action-link" href="${escapeHtml(decision.report)}" target="_blank" rel="noreferrer">Evidence</a>` : ""}
        ${worksheetActionLinks(decision)}
      </div>
    </div>
  `;
}

function wireDecisionPrepPacket(root) {
  root.querySelectorAll(".decision-prep-focus").forEach((button) => {
    button.addEventListener("click", () => jumpToProjectDecision(button.dataset.key || "", false));
  });
}

function dailyOperatingGuidePanel(guide) {
  if (!guide?.steps?.length) return "";
  const tone = guide.status === "ready" ? "green" : guide.status === "attention" ? "coral" : "gold";
  return `
    <div class="band daily-guide-panel ${escapeHtml(guide.status || "")}">
      <div class="band-header">
        <div>
          <h3>${escapeHtml(guide.title || "Daily Operating Guide")}</h3>
          <p>${escapeHtml(guide.message || "A live runbook for safe daily CRM work.")}</p>
        </div>
        <div class="daily-guide-header-actions">
          <span class="pill ${tone}">${escapeHtml(labelize(guide.status || "waiting"))}</span>
          ${guide.report ? `<a class="text-button action-link" href="${escapeHtml(guide.report)}" target="_blank" rel="noreferrer">Open Guide</a>` : ""}
          ${guide.export_url ? `<a class="text-button action-link" href="${escapeHtml(guide.export_url)}">Export Guide</a>` : ""}
        </div>
      </div>
      <div class="daily-guide-list">
        ${guide.steps.map((step) => dailyGuideStep(step)).join("")}
      </div>
    </div>
  `;
}

function dailyGuideStep(step) {
  const metrics = (step.metrics || []).filter((item) => item.label);
  const tone = step.status === "ready" || step.status === "complete" ? "green" : step.status === "attention" ? "coral" : "gold";
  return `
    <div class="daily-guide-row ${escapeHtml(step.status || "")}">
      <div class="daily-guide-main">
        <span class="step-pill">Step ${escapeHtml(step.order || "")}</span>
        <span class="pill ${tone}">${escapeHtml(labelize(step.status || "waiting"))}</span>
        <strong>${escapeHtml(step.title || "")}</strong>
        <p>${escapeHtml(step.description || "")}</p>
        ${step.safety ? `<small>${escapeHtml(step.safety)}</small>` : ""}
      </div>
      ${
        metrics.length
          ? `<div class="daily-guide-metrics">
              ${metrics
                .map((item) => `<span><strong>${escapeHtml(formatImpactValue(item.value))}</strong>${escapeHtml(item.label)}</span>`)
                .join("")}
            </div>`
          : ""
      }
      <div class="daily-guide-actions">
        ${dailyGuideActionButton(step.action || "Open", step.view, step.preset)}
        ${dailyGuideActionButton(step.secondary_action, step.secondary_view, step.secondary_preset)}
        ${step.report ? `<a class="text-button action-link" href="${escapeHtml(step.report)}" target="_blank" rel="noreferrer">Report</a>` : ""}
        ${step.export_url ? `<a class="text-button action-link" href="${escapeHtml(step.export_url)}">CSV</a>` : ""}
      </div>
    </div>
  `;
}

function dailyGuideActionButton(label, view, preset) {
  if (!label) return "";
  if (preset) {
    return `<button type="button" class="text-button work-queue-preset" data-preset="${escapeHtml(preset)}">${escapeHtml(label)}</button>`;
  }
  if (view) {
    return `<button type="button" class="text-button nav-jump" data-view="${escapeHtml(view)}">${escapeHtml(label)}</button>`;
  }
  return "";
}

function operationalWorkQueuePanel(queue) {
  if (!queue?.cards?.length) return "";
  const tasks = queue.upcoming_tasks || [];
  const pipelineItems = queue.pipeline_focus_items || [];
  const newLeads = queue.new_lead_items || [];
  const dataQualityItems = queue.data_quality?.priority_records || [];
  const sourceMix = queue.source_mix?.rows || [];
  const archiveReviewGroups = queue.archive_review?.top_numbers || [];
  const recent = queue.recent_records || [];
  const localChanges = queue.local_change_items || [];
  const savedViews = queue.saved_views || [];
  return `
    <div class="band operational-work-queue">
      <div class="band-header">
        <div>
          <h3>${escapeHtml(queue.title || "Operating Work Queue")}</h3>
          <p>${escapeHtml(queue.message || "Safe daily-use work is separated from major cleanup decisions.")}</p>
        </div>
        <button class="text-button nav-jump" data-view="dashboard">Open Dashboard</button>
      </div>
      <div class="work-queue-card-grid">
        ${queue.cards.map((card) => workQueueCard(card)).join("")}
      </div>
      <div class="work-queue-lists">
        <div class="work-queue-list">
          <div class="mini-header">
            <strong>Next Follow Ups</strong>
            <button class="text-button nav-jump" data-view="followup">Open</button>
          </div>
          ${taskTable(tasks, true)}
        </div>
        <div class="work-queue-list">
          <div class="mini-header">
            <strong>Pipeline Focus</strong>
            <button class="text-button work-queue-preset" data-preset="active_deals">Open Active Deals</button>
          </div>
          ${recordTable(pipelineItems, "pipeline")}
        </div>
        <div class="work-queue-list">
          <div class="mini-header">
            <strong>New Leads</strong>
            <button class="text-button work-queue-preset" data-preset="new_leads">Open New Leads</button>
          </div>
          ${recordTable(newLeads, "new_leads")}
        </div>
        <div class="work-queue-list">
          <div class="mini-header">
            <strong>Data Quality</strong>
            <div class="mini-actions">
              <button class="text-button work-queue-preset" data-preset="quality_people_missing_contact">People</button>
              <button class="text-button work-queue-preset" data-preset="quality_companies_missing_contact">Companies</button>
              <button class="text-button work-queue-preset" data-preset="quality_leads_missing_email">Leads</button>
              <button class="text-button work-queue-preset" data-preset="quality_deals_missing_value">Deals</button>
              <a class="text-button action-link" href="${escapeHtml(queue.data_quality?.report || "/reports/local_crm_data_quality.md")}" target="_blank" rel="noreferrer">Report</a>
            </div>
          </div>
          ${recordTable(dataQualityItems, "data_quality")}
        </div>
        <div class="work-queue-list">
          <div class="mini-header">
            <strong>Archive Review</strong>
            <div class="mini-actions">
              <button class="text-button work-queue-preset" data-preset="archive_review_unreviewed">Unreviewed</button>
              <button class="text-button work-queue-preset" data-preset="archive_review_needs_lookup">Needs Lookup</button>
              <button class="text-button work-queue-preset" data-preset="archive_review_ready_to_link">Ready</button>
            </div>
          </div>
          ${archiveReviewGroupList(archiveReviewGroups)}
        </div>
        <div class="work-queue-list">
          <div class="mini-header">
            <strong>Source Mix</strong>
          </div>
          ${sourceMixList(sourceMix)}
        </div>
        <div class="work-queue-list">
          <div class="mini-header">
            <strong>Recently Updated</strong>
            <button class="text-button nav-jump" data-view="activity">Activity</button>
          </div>
          ${recordTable(recent, "recent")}
        </div>
        <div class="work-queue-list">
          <div class="mini-header">
            <strong>Recent Local Changes</strong>
            <button class="text-button work-queue-preset" data-preset="local_changes">Open Local Changes</button>
          </div>
          ${miniActivityList(localChanges)}
        </div>
        ${
          savedViews.length
            ? `<div class="work-queue-list saved-work-queue-list">
                <div class="mini-header">
                  <strong>Recent Saved Views</strong>
                </div>
                <div class="saved-view-grid compact">
                  ${savedViews
                    .map((view) => `
                      <button class="saved-view-button" data-view-id="${view.id}">
                        <strong>${escapeHtml(view.name)}</strong>
                        <span>${escapeHtml(savedViewCountLabel(view))}</span>
                        <small>${escapeHtml(savedViewSummary(view.settings || {}))}</small>
                      </button>
                    `)
                    .join("")}
                </div>
              </div>`
            : ""
        }
      </div>
    </div>
  `;
}

function miniActivityList(items) {
  if (!items.length) return `<div class="empty-state compact"><h3>No local changes</h3><p>Local edits will appear here after they are saved.</p></div>`;
  return `<div class="timeline mini-timeline">${items.map(globalActivityItem).join("")}</div>`;
}

function sourceMixList(items) {
  if (!items.length) return `<div class="empty-state compact"><h3>No source counts</h3><p>Imported and local record counts will appear here.</p></div>`;
  const sourceButtons = [
    ["imported", "Imported"],
    ["local", "Local"],
    ["changed", "Changed"],
  ];
  return `
    <div class="source-mix-list">
      ${items
        .map((item) => `
          <div class="source-mix-row">
            <div>
              <strong>${escapeHtml(item.label || "")}</strong>
              <span>${formatNumber(item.total || 0)} total</span>
            </div>
            <div class="source-mix-actions">
              ${sourceButtons
                .map(([key, label]) => {
                  const count = Number(item[key] || 0);
                  const preset = item.presets?.[key] || "";
                  return `<button type="button" class="text-button work-queue-preset source-mix-button" data-preset="${escapeHtml(preset)}" ${count ? "" : "disabled"}>${escapeHtml(label)} ${formatNumber(count)}</button>`;
                })
                .join("")}
            </div>
          </div>
        `)
        .join("")}
    </div>
  `;
}

function archiveReviewGroupList(items) {
  if (!items.length) return `<div class="empty-state compact"><h3>No archive review groups</h3><p>Unlinked call/text groups will appear here.</p></div>`;
  return `
    <div class="archive-review-mini-list">
      ${items.slice(0, 6)
        .map((item) => `
          <button class="archive-review-mini-row work-queue-archive-number" type="button" data-phone="${escapeHtml(item.phone_number || "")}">
            <strong>${escapeHtml(archiveItemLabel(item.item_type))} · ${escapeHtml(item.phone_number || "(blank)")}</strong>
            <span>${formatNumber(item.count)} items · ${formatNumber(item.reviewed_count || 0)} reviewed</span>
          </button>
        `)
        .join("")}
    </div>
  `;
}

function workQueueCard(card) {
  const tone = card.status === "ready" ? "green" : card.status === "attention" ? "coral" : "gold";
  const metrics = (card.metrics || []).filter((item) => item.label);
  return `
    <div class="work-queue-card ${escapeHtml(card.status || "")}">
      <div class="work-queue-card-top">
        <strong>${escapeHtml(card.title || "")}</strong>
        <span class="pill ${tone}">${escapeHtml(labelize(card.status || "waiting"))}</span>
      </div>
      <p>${escapeHtml(card.description || "")}</p>
      ${card.detail ? `<small>${escapeHtml(card.detail)}</small>` : ""}
      ${
        metrics.length
          ? `<div class="work-queue-metrics">
              ${metrics
                .map((item) => `<span><strong>${escapeHtml(formatImpactValue(item.value))}</strong>${escapeHtml(item.label)}</span>`)
                .join("")}
            </div>`
          : ""
      }
      <div class="work-queue-actions">
        ${
          card.view || card.preset
            ? `<button type="button" class="text-button ${card.preset ? "work-queue-preset" : "nav-jump"}" ${card.preset ? `data-preset="${escapeHtml(card.preset)}"` : `data-view="${escapeHtml(card.view)}"`}>${escapeHtml(card.action || "Open")}</button>`
            : ""
        }
        ${
          card.secondary_view || card.secondary_preset
            ? `<button type="button" class="text-button ${card.secondary_preset ? "work-queue-preset" : "nav-jump"}" ${card.secondary_preset ? `data-preset="${escapeHtml(card.secondary_preset)}"` : `data-view="${escapeHtml(card.secondary_view)}"`}>${escapeHtml(card.secondary_action || "Open")}</button>`
            : ""
        }
        ${card.report ? `<a class="text-button action-link" href="${escapeHtml(card.report)}" target="_blank" rel="noreferrer">Report</a>` : ""}
        ${card.secondary_report ? `<a class="text-button action-link" href="${escapeHtml(card.secondary_report)}">CSV</a>` : ""}
      </div>
    </div>
  `;
}

function wireWorkQueuePresets(root) {
  root.querySelectorAll(".work-queue-preset").forEach((button) => {
    button.addEventListener("click", () => openWorkQueuePreset(button.dataset.preset || ""));
  });
  root.querySelectorAll(".work-queue-archive-number").forEach((button) => {
    button.addEventListener("click", () => openArchivePhonePreset(button.dataset.phone || ""));
  });
}

function resetListFiltersFor(listType) {
  state.q = "";
  if (els.search) els.search.value = "";
  state.listTagId = "";
  state.listOwnerUserId = "";
  state.listProfileField = "";
  state.listProfileValue = "";
  state.listStatusFilters[listType] = { field: "", value: "" };
  state.listDateFilters[listType] = { field: "", from: "", to: "" };
  state.listQualityIssues[listType] = "";
  state.listProvenanceFilters[listType] = "";
  state.listSort[listType] = { field: "updated_at", direction: "desc" };
  state.listSavedViewId[listType] = "";
  state.page = 1;
}

function openQualityPreset(listType, issue, sort = { field: "updated_at", direction: "desc" }) {
  resetListFiltersFor(listType);
  state.listQualityIssues[listType] = issue;
  state.listSort[listType] = sort;
  setView(listType);
}

function openSourcePreset(listType, source) {
  resetListFiltersFor(listType);
  state.listProvenanceFilters[listType] = source;
  setView(listType);
}

function openArchiveReviewPreset(reviewStatus) {
  resetArchiveView();
  state.archivePreset = "unlinked_communications";
  state.archiveReviewStatus = reviewStatus;
  setView("archive");
}

function openArchivePhonePreset(phone) {
  resetArchiveView();
  state.archivePreset = "unlinked_communications";
  state.archiveQ = phone;
  setView("archive");
}

function openWorkQueuePreset(preset) {
  const sourceMatch = preset.match(/^source_(people|companies|leads|deals)_(imported|local|changed)$/);
  if (sourceMatch) {
    openSourcePreset(sourceMatch[1], sourceMatch[2]);
    return;
  }
  if (preset === "active_deals") {
    resetListFiltersFor("deals");
    state.listStatusFilters.deals = { field: "", value: "" };
    state.listSort.deals = { field: "value", direction: "desc" };
    setView("deals");
    return;
  }
  if (preset === "new_leads") {
    resetListFiltersFor("leads");
    state.listStatusFilters.leads = { field: "status", value: "New" };
    state.listSort.leads = { field: "updated_at", direction: "desc" };
    setView("leads");
    return;
  }
  if (preset === "quality_people_missing_contact") {
    openQualityPreset("people", "missing_contact");
    return;
  }
  if (preset === "quality_companies_missing_contact") {
    openQualityPreset("companies", "missing_contact");
    return;
  }
  if (preset === "quality_leads_missing_email") {
    openQualityPreset("leads", "missing_email");
    return;
  }
  if (preset === "quality_deals_missing_value") {
    openQualityPreset("deals", "missing_value");
    return;
  }
  const archiveReviewMatch = preset.match(/^archive_review_(unreviewed|needs_lookup|ready_to_link|archive_only)$/);
  if (archiveReviewMatch) {
    openArchiveReviewPreset(archiveReviewMatch[1]);
    return;
  }
  if (preset === "followup_imported_open") {
    resetTaskView();
    state.taskStatus = "open";
    state.taskSource = "imported";
    setView("followup");
    return;
  }
  if (preset === "followup_imported_overdue") {
    resetTaskView();
    state.taskStatus = "overdue";
    state.taskSource = "imported";
    setView("followup");
    return;
  }
  if (preset === "followup_local_open") {
    resetTaskView();
    state.taskStatus = "open";
    state.taskSource = "local";
    setView("followup");
    return;
  }
  if (preset === "local_changes") {
    resetActivityView();
    state.activityType = "local_change";
    setView("activity");
    return;
  }
}

function projectDecisionCenter(projectDecisions) {
  if (!projectDecisions?.decisions?.length) return "";
  const counts = projectDecisions.status_counts || {};
  const orderedDecisions = projectDecisionOrdered(projectDecisions.decisions);
  return `
    <div class="band project-decision-center">
      <div class="band-header">
        <div>
          <h3>Project Decisions</h3>
          <p>Track the major choices that unlock cleanup, merge behavior, archive handling, and the later visual redesign.</p>
        </div>
        <div class="project-decision-header-actions">
          <span class="muted">${formatNumber(counts.pending || 0)} pending · ${formatNumber(counts.decided || 0)} decided · ${formatNumber(counts.deferred || 0)} deferred</span>
          <a class="text-button action-link" href="/reports/project_decision_sequence.md" target="_blank" rel="noreferrer">Open Sequence</a>
          <a class="text-button action-link" href="/reports/project_decision_ballot.md" target="_blank" rel="noreferrer">Open Ballot</a>
          <a class="text-button action-link" href="/reports/project_decision_option_matrix.md" target="_blank" rel="noreferrer">Option Matrix</a>
          <a class="text-button action-link" href="/api/export?type=project_decision_ballot">Ballot CSV</a>
          <a class="text-button action-link" href="/api/export?type=project_decision_option_matrix">Matrix CSV</a>
          <button class="text-button" type="button" id="fillAllRecommendedDecisions">Fill Recommended</button>
          <button class="text-button" type="button" id="resetAllProjectDecisions">Reset All Staged</button>
        </div>
      </div>
      ${projectDecisionSequencePanel(projectDecisions)}
      <div class="project-decision-list">
        ${orderedDecisions.map((decision) => projectDecisionItem(decision, projectDecisions.statuses || {})).join("")}
      </div>
    </div>
  `;
}

function projectDecisionOrdered(decisions) {
  return [...(decisions || [])].sort((a, b) => {
    const aStep = Number(a.sequence?.step || 999);
    const bStep = Number(b.sequence?.step || 999);
    if (aStep !== bStep) return aStep - bStep;
    return String(a.title || "").localeCompare(String(b.title || ""));
  });
}

function projectDecisionSequencePanel(projectDecisions) {
  const sequenceItems = projectDecisions.sequence?.length
    ? projectDecisions.sequence.map((item) => ({ ...item, decision: item.decision || {} }))
    : projectDecisionOrdered(projectDecisions.decisions).map((decision) => ({ ...(decision.sequence || {}), decision }));
  if (!sequenceItems.length) return "";
  const nextItem = nextProjectDecisionSequenceItem(sequenceItems) || sequenceItems[sequenceItems.length - 1];
  const nextDecision = nextItem.decision || {};
  const nextRecommended = nextDecision.recommended_option || {};
  return `
    <div class="project-decision-sequence-panel">
      <div class="sequence-next">
        <span class="sequence-step">Next</span>
        <div>
          <strong>${escapeHtml(nextDecision.title || "All decisions saved")}</strong>
          <p>${escapeHtml(nextItem.why || "Review the saved decision paths and continue cleanup from the preview.")}</p>
          ${
            nextRecommended.label
              ? `<small>Recommended: ${escapeHtml(nextRecommended.label)} · ${escapeHtml(nextItem.recommended_timing || "")}</small>`
              : ""
          }
        </div>
        <div class="sequence-next-actions">
          ${nextDecision.view ? `<button type="button" class="text-button nav-jump" data-view="${escapeHtml(nextDecision.view)}">Open ${escapeHtml(labelize(nextDecision.view))}</button>` : ""}
          ${nextDecision.report ? `<a class="text-button action-link" href="${escapeHtml(nextDecision.report)}" target="_blank" rel="noreferrer">Evidence</a>` : ""}
          ${worksheetActionLinks(nextDecision)}
        </div>
      </div>
      <div class="decision-sequence-list">
        ${sequenceItems
          .map((item) => {
            const decision = item.decision || {};
            const recommended = decision.recommended_option || {};
            return `
              <div class="decision-sequence-step ${decision.status === "decided" ? "complete" : ""}">
                <span>${escapeHtml(item.step || "")}</span>
                <div>
                  <strong>${escapeHtml(decision.title || item.key || "")}</strong>
                  <small>${escapeHtml(item.phase || "")} · ${escapeHtml(recommended.label || "Choose path")}</small>
                </div>
                ${projectDecisionStatusPill(decision.status)}
              </div>
            `;
          })
          .join("")}
      </div>
    </div>
  `;
}

function nextProjectDecisionSequenceItem(sequenceItems) {
  return (
    sequenceItems.find((item) => item.decision?.status === "pending") ||
    sequenceItems.find((item) => item.decision?.status === "deferred") ||
    null
  );
}

function projectDecisionItem(decision, statuses) {
  const recommended = decision.recommended_option;
  const recommendedCode = projectDecisionChoiceCode(decision, decision.recommendation);
  const impact = decision.impact || {};
  const sequence = decision.sequence || {};
  return `
    <form
      class="project-decision-item project-decision-form"
      data-key="${escapeHtml(decision.key)}"
      data-recommended="${escapeHtml(decision.recommendation || "")}"
      data-initial-status="${escapeHtml(decision.status || "pending")}"
      data-initial-choice="${escapeHtml(decision.choice || "")}"
      data-initial-note="${escapeHtml(decision.note || "")}"
    >
      <div class="project-decision-copy">
        <div class="project-decision-title-row">
          ${sequence.step ? `<span class="step-pill">Step ${escapeHtml(sequence.step)}</span>` : ""}
          ${projectDecisionStatusPill(decision.status)}
          <strong>${escapeHtml(decision.title)}</strong>
          <span>${escapeHtml(decision.category)}</span>
        </div>
        <p>${escapeHtml(decision.question)}</p>
        ${sequence.why ? `<small>${escapeHtml(sequence.phase || "Sequence")} · ${escapeHtml(sequence.why)}</small>` : ""}
        ${recommended ? `<small>Recommended: ${escapeHtml([recommendedCode, recommended.label].filter(Boolean).join(". "))} · ${escapeHtml(recommended.description)}</small>` : ""}
        ${projectDecisionSaveEffect(sequence)}
        ${projectDecisionImpact(impact)}
        <div class="project-decision-links">
          ${decision.view ? `<button type="button" class="text-button nav-jump" data-view="${escapeHtml(decision.view)}">Open ${escapeHtml(labelize(decision.view))}</button>` : ""}
          ${decision.report ? `<a class="text-button action-link" href="${escapeHtml(decision.report)}" target="_blank" rel="noreferrer">Open Report</a>` : ""}
          ${worksheetActionLinks(decision)}
        </div>
      </div>
      <div class="project-decision-controls">
        <label>
          Status
          <select name="status">
            ${Object.entries(statuses)
              .map(([value, label]) => `<option value="${escapeHtml(value)}" ${decision.status === value ? "selected" : ""}>${escapeHtml(label)}</option>`)
              .join("")}
          </select>
        </label>
        <label>
          Path
          <select name="choice">
            <option
              value=""
              data-code=""
              data-label="Choose a path"
              data-description="Choose a path to see what it means before saving. Nothing is recorded until Save Decision is clicked."
              ${decision.choice ? "" : "selected"}
            >Choose path</option>
            ${decision.options
              .map(
                (option, index) => {
                  const code = projectDecisionOptionCode(index);
                  return `
                  <option
                    value="${escapeHtml(option.value)}"
                    data-code="${escapeHtml(code)}"
                    data-label="${escapeHtml(option.label)}"
                    data-description="${escapeHtml(option.description || "")}"
                    ${decision.choice === option.value ? "selected" : ""}
                  >${escapeHtml(`${code}. ${option.label}`)}</option>
                `;
                }
              )
              .join("")}
          </select>
        </label>
        ${projectDecisionOptionDetail(decision)}
        <small class="project-decision-status-guidance" hidden></small>
        <label>
          Note
          <textarea name="note" rows="2">${escapeHtml(decision.note || "")}</textarea>
        </label>
        ${recommended ? `<button class="text-button fill-recommended-decision" type="button">Fill Recommended</button>` : ""}
        <small class="project-decision-unsaved" hidden></small>
        <div class="project-decision-save-actions">
          <button class="text-button" type="submit">Save Decision</button>
          <button class="text-button save-project-decision-next" type="button">Save & Next Decision</button>
          <button class="text-button reset-project-decision" type="button">Reset Staged</button>
        </div>
        ${decision.updated_at ? `<small class="muted">Saved ${escapeHtml(formatDate(decision.updated_at))}</small>` : ""}
      </div>
    </form>
  `;
}

function projectDecisionOptionCode(index) {
  return String.fromCharCode("A".charCodeAt(0) + Number(index || 0));
}

function projectDecisionChoiceCode(decision, value) {
  if (!value) return "";
  const index = (decision.options || []).findIndex((option) => option.value === value);
  return index >= 0 ? projectDecisionOptionCode(index) : "";
}

function projectDecisionSaveEffect(sequence) {
  if (!sequence?.after_save) return "";
  return `
    <div class="project-decision-save-effect">
      <span>After Save</span>
      <p>${escapeHtml(sequence.after_save)}</p>
      <small>Records this decision only. It does not merge, delete, resolve, ignore, or rewrite CRM records.</small>
    </div>
  `;
}

function projectDecisionOptionDetail(decision) {
  const option = decision.selected_option || null;
  const code = projectDecisionChoiceCode(decision, option?.value);
  const recommended = option?.value === decision.recommendation;
  return `
    <div class="project-decision-option-detail ${option ? "" : "empty"}" aria-live="polite">
      <div class="project-decision-option-heading">
        <strong>${escapeHtml([code, option?.label].filter(Boolean).join(". ") || "Choose a path")}</strong>
        ${recommended ? `<span class="pill green">Recommended</span>` : ""}
      </div>
      <p>${escapeHtml(option?.description || "Choose a path to see what it means before saving. Nothing is recorded until Save Decision is clicked.")}</p>
    </div>
  `;
}

function projectDecisionImpact(impact) {
  if (!impact?.summary && !impact?.facts?.length) return "";
  return `
    <div class="project-decision-impact">
      ${impact.readiness ? `<span class="pill ${impact.readiness === "ready" ? "green" : "gold"}">${escapeHtml(labelize(impact.readiness))}</span>` : ""}
      ${impact.summary ? `<p>${escapeHtml(impact.summary)}</p>` : ""}
      ${
        impact.facts?.length
          ? `<div class="project-decision-facts">
              ${impact.facts.map((fact) => `<span>${escapeHtml(fact.label)} ${escapeHtml(formatImpactValue(fact.value))}</span>`).join("")}
            </div>`
          : ""
      }
      ${impact.next_step ? `<small>${escapeHtml(impact.next_step)}</small>` : ""}
    </div>
  `;
}

function formatImpactValue(value) {
  return typeof value === "number" ? formatNumber(value) : String(value ?? "");
}

function projectDecisionStatusPill(status) {
  const label = { pending: "Pending", decided: "Decided", deferred: "Deferred" }[status] || labelize(status || "Pending");
  const tone = status === "decided" ? "" : status === "deferred" ? "gold" : "coral";
  return `<span class="pill ${tone}">${escapeHtml(label)}</span>`;
}

function wireProjectDecisionForms(root) {
  root.querySelector("#fillAllRecommendedDecisions")?.addEventListener("click", () => {
    root.querySelectorAll(".project-decision-form").forEach((form) => fillRecommendedDecision(form));
    updateProjectDecisionBulkResetState(root);
    setStatus("Recommended paths filled; save each decision when ready");
  });
  root.querySelector("#resetAllProjectDecisions")?.addEventListener("click", () => {
    root.querySelectorAll(".project-decision-form").forEach((form) => resetProjectDecisionForm(form));
    updateProjectDecisionBulkResetState(root);
    setStatus("All staged decision changes reset");
  });
  root.querySelectorAll(".project-decision-form").forEach((form) => {
    updateProjectDecisionFormState(form);
    form.querySelectorAll("select, textarea").forEach((input) => {
      input.addEventListener("input", () => updateProjectDecisionFormState(form));
      input.addEventListener("change", () => updateProjectDecisionFormState(form));
    });
    form.querySelector(".fill-recommended-decision")?.addEventListener("click", () => {
      fillRecommendedDecision(form);
      setStatus("Recommended path filled; save when ready");
    });
    form.querySelector(".reset-project-decision")?.addEventListener("click", () => {
      resetProjectDecisionForm(form);
      setStatus("Staged decision changes reset");
    });
    const saveProjectDecision = async (openNext = false) => {
      updateProjectDecisionFormState(form);
      if (!hasProjectDecisionChanges(form)) {
        setStatus("No unsaved decision changes");
        return;
      }
      if (!isProjectDecisionSavable(form)) {
        setStatus("Choose a path before marking a decision decided");
        return;
      }
      const key = form.dataset.key;
      const status = form.querySelector('select[name="status"]').value;
      const choice = form.querySelector('select[name="choice"]').value;
      const note = form.querySelector('textarea[name="note"]').value.trim();
      const nextKey = openNext ? nextPendingProjectDecisionKey(key) : "";
      setStatus(openNext ? "Saving and opening next decision" : "Saving project decision");
      const result = await postJson("/api/save_project_decision", { key, status, choice, note });
      const backupName = result.backup ? result.backup.split(/[\\/]/).pop() : "";
      await renderMigrationStatus();
      const backupText = backupName ? `; backup ${backupName} created` : "";
      if (nextKey) {
        focusProjectDecision(nextKey, false);
        setStatus(`Project decision saved${backupText}; next decision opened`);
      } else {
        setStatus(openNext ? `Project decision saved${backupText}; no next pending decision` : `Project decision saved${backupText}`);
      }
    };
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      await saveProjectDecision(false);
    });
    form.querySelector(".save-project-decision-next")?.addEventListener("click", () => saveProjectDecision(true));
  });
}

function nextPendingProjectDecisionKey(currentKey) {
  const forms = [...document.querySelectorAll(".project-decision-form")];
  const currentIndex = forms.findIndex((form) => form.dataset.key === currentKey);
  const ordered = currentIndex >= 0 ? [...forms.slice(currentIndex + 1), ...forms.slice(0, currentIndex)] : forms;
  const nextPending = ordered.find((form) => form.querySelector('select[name="status"]')?.value === "pending");
  if (nextPending) return nextPending.dataset.key || "";
  const nextDeferred = ordered.find((form) => form.querySelector('select[name="status"]')?.value === "deferred");
  return nextDeferred?.dataset.key || "";
}

function wireNextAction(root) {
  root.querySelectorAll(".next-action-decision").forEach((button) => {
    button.addEventListener("click", () => jumpToProjectDecision(button.dataset.key, false));
  });
  root.querySelectorAll(".next-action-fill").forEach((button) => {
    button.addEventListener("click", () => jumpToProjectDecision(button.dataset.key, true));
  });
}

function jumpToProjectDecision(key, fillRecommended) {
  if (state.view !== "migrationStatus") {
    setView("migrationStatus");
    window.setTimeout(() => focusProjectDecision(key, fillRecommended), 450);
    return;
  }
  focusProjectDecision(key, fillRecommended);
}

function focusProjectDecision(key, fillRecommended) {
  const form = [...document.querySelectorAll(".project-decision-form")].find((item) => item.dataset.key === key);
  if (!form) return;
  if (fillRecommended) {
    fillRecommendedDecision(form);
    setStatus("Recommended path filled; save when ready");
  }
  form.scrollIntoView({ behavior: "smooth", block: "center" });
  form.classList.add("project-decision-highlight");
  window.setTimeout(() => form.classList.remove("project-decision-highlight"), 1800);
}

function fillRecommendedDecision(form) {
  const recommended = form.dataset.recommended;
  const statusSelect = form.querySelector('select[name="status"]');
  const choiceSelect = form.querySelector('select[name="choice"]');
  if (recommended && choiceSelect) choiceSelect.value = recommended;
  if (statusSelect) statusSelect.value = "decided";
  updateProjectDecisionFormState(form);
}

function resetProjectDecisionForm(form) {
  const statusSelect = form.querySelector('select[name="status"]');
  const choiceSelect = form.querySelector('select[name="choice"]');
  const noteInput = form.querySelector('textarea[name="note"]');
  if (statusSelect) statusSelect.value = form.dataset.initialStatus || "pending";
  if (choiceSelect) choiceSelect.value = form.dataset.initialChoice || "";
  if (noteInput) noteInput.value = form.dataset.initialNote || "";
  updateProjectDecisionFormState(form);
}

function projectDecisionFormValues(form) {
  return {
    status: form.querySelector('select[name="status"]')?.value || "pending",
    choice: form.querySelector('select[name="choice"]')?.value || "",
    note: form.querySelector('textarea[name="note"]')?.value.trim() || "",
  };
}

function hasProjectDecisionChanges(form) {
  const values = projectDecisionFormValues(form);
  return (
    values.status !== (form.dataset.initialStatus || "pending") ||
    values.choice !== (form.dataset.initialChoice || "") ||
    values.note !== (form.dataset.initialNote || "")
  );
}

function isProjectDecisionSavable(form) {
  const values = projectDecisionFormValues(form);
  return hasProjectDecisionChanges(form) && !(values.status === "decided" && !values.choice);
}

function updateProjectDecisionFormState(form) {
  const dirty = hasProjectDecisionChanges(form);
  const values = projectDecisionFormValues(form);
  const missingChoice = values.status === "decided" && !values.choice;
  const hint = form.querySelector(".project-decision-unsaved");
  const statusGuidance = form.querySelector(".project-decision-status-guidance");
  updateProjectDecisionOptionDetail(form);
  updateProjectDecisionStatusGuidance(statusGuidance, values);
  form.classList.toggle("unsaved", dirty);
  form.classList.toggle("invalid-decision", dirty && missingChoice);
  if (hint) {
    hint.hidden = !dirty && !missingChoice;
    hint.textContent = missingChoice
      ? "Choose a path before saving this decided decision."
      : "Unsaved changes staged on this card. Save Decision records only this choice.";
  }
  const resetButton = form.querySelector(".reset-project-decision");
  if (resetButton) resetButton.disabled = !dirty;
  form.querySelectorAll(".project-decision-save-actions button:not(.reset-project-decision)").forEach((button) => {
    button.disabled = !dirty || missingChoice;
  });
  updateProjectDecisionBulkResetState(form.closest(".project-decision-center") || document);
}

function updateProjectDecisionBulkResetState(root = document) {
  const button = root.querySelector("#resetAllProjectDecisions");
  if (!button) return;
  const dirtyCount = [...root.querySelectorAll(".project-decision-form")].filter((form) => hasProjectDecisionChanges(form)).length;
  button.disabled = dirtyCount === 0;
  button.textContent = dirtyCount ? `Reset ${formatNumber(dirtyCount)} Staged` : "Reset All Staged";
}

function updateProjectDecisionStatusGuidance(element, values) {
  if (!element) return;
  const message = projectDecisionStatusGuidanceText(values);
  element.hidden = !message;
  element.textContent = message;
}

function projectDecisionStatusGuidanceText(values) {
  if (!values.choice) return "";
  if (values.status === "pending") {
    return "Path selected, but status is still Pending. Saving as Pending records a draft only; choose Decided to make this path active in previews.";
  }
  if (values.status === "deferred") {
    return "Deferred records this path as postponed. It will not unlock cleanup preview gates until the decision is saved as Decided.";
  }
  return "Decided makes this the active saved path for previews and next steps. It still does not merge or rewrite CRM records.";
}

function updateProjectDecisionOptionDetail(form) {
  const choiceSelect = form.querySelector('select[name="choice"]');
  const detail = form.querySelector(".project-decision-option-detail");
  if (!choiceSelect || !detail) return;
  const selected = choiceSelect.options[choiceSelect.selectedIndex];
  const selectedValue = selected?.value || "";
  const code = selected?.dataset.code || "";
  const label = selected?.dataset.label || "Choose a path";
  const description =
    selected?.dataset.description ||
    "Choose a path to see what it means before saving. Nothing is recorded until Save Decision is clicked.";
  const recommended = selectedValue && selectedValue === form.dataset.recommended;
  detail.classList.toggle("empty", !selectedValue);
  detail.innerHTML = `
    <div class="project-decision-option-heading">
      <strong>${escapeHtml([code, label].filter(Boolean).join(". "))}</strong>
      ${recommended ? `<span class="pill green">Recommended</span>` : ""}
    </div>
    <p>${escapeHtml(description)}</p>
  `;
}

function cleanupExecutionPreviewPanel(preview, title = "Cleanup Execution Preview") {
  if (!preview) return "";
  const totals = preview.totals || {};
  const gates = preview.gates || [];
  const actions = preview.actions || [];
  return `
    <div class="band cleanup-execution-preview ${preview.simulation ? "simulation" : ""}">
      <div class="band-header">
        <div>
          <h3>${escapeHtml(title)}</h3>
          <p>${escapeHtml(preview.message || "")}</p>
        </div>
        ${cleanupExecutionStatusPill(preview.status)}
      </div>
      <div class="cleanup-policy-totals">
        <div class="signal"><strong>${formatNumber(totals.blocked_gates || 0)}</strong><span>Locked gates</span></div>
        <div class="signal"><strong>${formatNumber(totals.approved_merge_later_groups || 0)}</strong><span>Approved groups</span></div>
        <div class="signal"><strong>${formatNumber(totals.eligible_actions || 0)}</strong><span>Eligible actions</span></div>
        <div class="signal"><strong>${formatNumber(totals.eligible_groups || 0)}</strong><span>Eligible groups</span></div>
        <div class="signal"><strong>${formatNumber(totals.open_groups || 0)}</strong><span>Open groups</span></div>
      </div>
      <div class="execution-preview-grid">
        <div>
          <h4>Gates</h4>
          <div class="execution-preview-list">
            ${gates
              .map(
                (gate) => `
                  <div class="execution-preview-row">
                    ${cleanupExecutionStatusPill(gate.status)}
                    <div>
                      <strong>${escapeHtml(gate.label || "")}</strong>
                      <p>${escapeHtml(gate.detail || "")}</p>
                    </div>
                  </div>
                `,
              )
              .join("")}
          </div>
        </div>
        <div>
          <h4>Preview Actions</h4>
          <div class="execution-preview-list">
            ${actions
              .map(
                (action) => `
                  <div class="execution-preview-row">
                    ${cleanupExecutionStatusPill(action.status)}
                    <div>
                      <strong>${escapeHtml(action.label || "")}</strong>
                      <p>${escapeHtml(action.detail || "")}</p>
                      <small>${formatNumber(action.eligible_groups || 0)} eligible groups · ${formatNumber(action.eligible_records || 0)} records · ${formatNumber(action.open_groups || 0)} open groups</small>
                    </div>
                  </div>
                `,
              )
              .join("")}
          </div>
        </div>
      </div>
      ${
        preview.warnings?.length
          ? `<div class="cleanup-guidance-list execution-preview-warnings">
              ${preview.warnings.map((warning) => `<span>${escapeHtml(warning)}</span>`).join("")}
            </div>`
          : ""
      }
    </div>
  `;
}

function cleanupExecutionStatusPill(status) {
  const label = {
    locked: "Locked",
    ready: "Ready",
    preview_ready: "Preview Ready",
    waiting_for_group_decisions: "Waiting",
    waiting_for_project_decision: "Waiting",
    not_allowed_by_policy: "Policy Off",
    no_open_groups: "No Groups",
    no_actions: "No Actions",
    eligible: "Eligible",
  }[status] || labelize(status || "Review");
  const tone = {
    locked: "coral",
    waiting_for_group_decisions: "gold",
    waiting_for_project_decision: "gold",
    preview_ready: "green",
    ready: "green",
    eligible: "green",
  }[status] || "";
  return `<span class="pill ${tone}">${escapeHtml(label)}</span>`;
}

function productionGatePanel(gates) {
  if (!gates?.status) return "";
  const blockingItems = gates.blocking_gate_items || [];
  const neededInputs = gates.needed_inputs || [];
  const nextOwnerAction = gates.next_owner_action || null;
  const nextOperatorAction = gates.next_operator_action || null;
  const tone = Number(gates.failed || 0) ? "coral" : Number(gates.input_required || 0) ? "gold" : "green";
  const sourceTruth = gates.source_of_truth === "local_sqlite" ? "Local SQLite" : "Hosted ready for owner cutover review";
  const reportLinks = (links, fallbackUrl = "", fallbackLabel = "Proof Report") => {
    const safeLinks = Array.isArray(links) ? links : [];
    if (safeLinks.length) {
      return safeLinks
        .map((link) => `<a class="text-button action-link" href="${escapeHtml(link.url || "")}" target="_blank" rel="noreferrer">${escapeHtml(link.label || fallbackLabel)}</a>`)
        .join("");
    }
    return fallbackUrl ? `<a class="text-button action-link" href="${escapeHtml(fallbackUrl)}" target="_blank" rel="noreferrer">${escapeHtml(fallbackLabel)}</a>` : "";
  };
  const actionPanel = (action, label, className) => {
    if (!action?.title) return "";
    return `<div class="production-next-action ${className}">
      <div class="next-action-copy">
        <span class="step-pill">${escapeHtml(label)}</span>
        <strong>${escapeHtml(action.title || "")}</strong>
        <p>${escapeHtml(action.detail || action.secret_handling || "")}</p>
        ${action.owner_reply ? `<small>Reply: ${escapeHtml(action.owner_reply)}</small>` : ""}
      </div>
      <div class="decision-prep-row-actions">
        ${reportLinks(action.proof_links)}
      </div>
    </div>`;
  };
  const showOperatorAction = nextOperatorAction?.title && nextOperatorAction.input !== nextOwnerAction?.input;
  return `
    <div class="band production-gate-panel">
      <div class="band-header">
        <div>
          <h3>Production Gates</h3>
          <p>${escapeHtml(sourceTruth)} · ${escapeHtml(gates.latest_url || "No hosted URL")}</p>
        </div>
        <div class="daily-guide-header-actions">
          <span class="pill ${tone}">${escapeHtml(labelize(gates.production_gate || gates.status))}</span>
          ${gates.reports?.readiness ? `<a class="text-button action-link" href="${escapeHtml(gates.reports.readiness)}" target="_blank" rel="noreferrer">Readiness</a>` : ""}
          ${gates.reports?.remaining_packet ? `<a class="text-button action-link" href="${escapeHtml(gates.reports.remaining_packet)}" target="_blank" rel="noreferrer">Inputs</a>` : ""}
          ${gates.reports?.owner_intake ? `<a class="text-button action-link" href="${escapeHtml(gates.reports.owner_intake)}" target="_blank" rel="noreferrer">Owner Intake</a>` : ""}
        </div>
      </div>
      <div class="cleanup-detail-signals">
        <div class="signal"><strong>${formatNumber(gates.passed || 0)}</strong><span>Passed</span></div>
        <div class="signal"><strong>${formatNumber(gates.failed || 0)}</strong><span>Failed</span></div>
        <div class="signal"><strong>${formatNumber(gates.input_required || 0)}</strong><span>Inputs</span></div>
        <div class="signal"><strong>${formatNumber(gates.blocking_gates || blockingItems.length)}</strong><span>Blocking</span></div>
      </div>
      ${actionPanel(nextOwnerAction, "Next Owner Action", "production-next-owner-action")}
      ${showOperatorAction ? actionPanel(nextOperatorAction, "Next Operator Action", "production-next-operator-action") : ""}
      ${
        blockingItems.length
          ? `<div class="readiness-list">
              ${blockingItems
                .map(
                  (item) => `
                    <div class="readiness-item attention">
                      <div>
                        ${statusPill(labelize(item.status || "input_required"), "warn")}
                        <strong>${escapeHtml(item.gate || "")}</strong>
                        <p>${escapeHtml(item.next_action || item.evidence || "")}</p>
                      </div>
                      <div class="decision-prep-row-actions">
                        ${reportLinks(item.source_links, item.source_url, "Proof")}
                      </div>
                    </div>
                  `
                )
                .join("")}
            </div>`
          : `<p class="muted">No blocking gates are currently reported.</p>`
      }
      ${
        neededInputs.length
          ? `<div class="decision-prep-list">
              ${neededInputs
                .map(
                  (item) => `
                    <div class="decision-prep-row">
                      <div class="decision-prep-row-main">
                        <span class="step-pill">Input ${escapeHtml(item.order || "")}</span>
                        <span class="pill gold">${escapeHtml(labelize(item.status || "pending"))}</span>
                        <strong>${escapeHtml(item.input || "")}</strong>
                        <p>${escapeHtml(item.secret_handling || "")}</p>
                      </div>
                      <div class="decision-prep-row-actions">
                        ${reportLinks(item.proof_links, item.proof_url, "Proof Report")}
                      </div>
                    </div>
                  `
                )
                .join("")}
            </div>`
          : ""
      }
    </div>
  `;
}

function migrationReadiness(items) {
  if (!items.length) return "";
  return `
    <div class="band">
      <div class="band-header">
        <h3>Readiness Checklist</h3>
        <span class="muted">${formatNumber(items.length)} checks</span>
      </div>
      <div class="readiness-list">
        ${items
          .map((item) => `
            <div class="readiness-item ${escapeHtml(item.status || "")}">
              <div>
                ${statusPill(readinessStatusLabel(item.status), readinessTone(item.status))}
                <strong>${escapeHtml(item.title || "")}</strong>
                <p>${escapeHtml(item.detail || "")}</p>
              </div>
              ${item.view ? `<button class="text-button readiness-jump" data-view="${escapeHtml(item.view)}">${escapeHtml(item.action || "Open")}</button>` : ""}
            </div>
          `)
          .join("")}
      </div>
    </div>
  `;
}

function readinessStatusLabel(status) {
  return {
    complete: "Done",
    attention: "Needs Attention",
    waiting: "Waiting",
  }[status] || labelize(status || "Review");
}

function readinessTone(status) {
  return {
    complete: "ok",
    attention: "bad",
    waiting: "warn",
  }[status] || "";
}

function wireReadinessButtons(root) {
  root.querySelectorAll(".readiness-jump").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
  });
}

function statusPill(label, tone = "") {
  const className = tone === "warn" ? "gold" : tone === "bad" ? "coral" : "";
  return `<span class="pill ${className}">${escapeHtml(label)}</span>`;
}

function statusCountList(counts, title) {
  const entries = Object.entries(counts || {});
  if (!entries.length) return `<p class="muted">${escapeHtml(title)}: none yet.</p>`;
  return `
    <div class="cleanup-record-stats">
      ${entries
        .map(([label, count]) => `<span>${escapeHtml(labelize(label))} ${formatNumber(count)}</span>`)
        .join("")}
    </div>
  `;
}

function linkedKindCount(data, kind) {
  return (data.linked_resources?.kind_counts || []).find((item) => item.value === kind)?.count || 0;
}

function archiveStatusCount(data, itemType) {
  return (data.imported_archive?.type_counts || []).find((item) => item.value === itemType)?.count || 0;
}

function archiveStatusCountList(typeCounts) {
  if (!typeCounts.length) return "";
  return `
    <div class="cleanup-record-stats">
      ${typeCounts.map((item) => `<span>${escapeHtml(archiveItemLabel(item.value))} ${formatNumber(item.count)}</span>`).join("")}
    </div>
  `;
}

function archiveAssociationMiniList(association) {
  const summary = association?.summary || {};
  if (!Object.keys(summary).length) return "";
  const typeRows = association?.type_rows || [];
  return `
    <div class="archive-association-mini">
      <span><strong>${formatNumber(summary.link_coverage_percent || 0)}%</strong> linked coverage</span>
      <span><strong>${formatNumber(summary.linked_documents || 0)}/${formatNumber(summary.document_total || 0)}</strong> document files</span>
      <span><strong>${formatNumber(summary.exact_phone_candidates || 0)}</strong> exact phone candidates</span>
      <span><strong>${formatNumber(summary.unlinked_unreviewed_call_texts || 0)}</strong> unreviewed calls/texts</span>
    </div>
    ${
      typeRows.length
        ? `<div class="cleanup-record-stats archive-association-types">
            ${typeRows
              .map((item) => `<span>${escapeHtml(archiveItemLabel(item.item_type))} ${formatNumber(item.linked || 0)}/${formatNumber(item.total || 0)} linked</span>`)
              .join("")}
          </div>`
        : ""
    }
  `;
}

function currentArchiveSettings() {
  return {
    q: state.archiveQ,
    item_type: state.archiveItemType,
    record_type: state.archiveRecordType,
    preset: state.archivePreset,
    review_status: state.archiveReviewStatus,
    triage_lane: state.archiveTriageLane,
    date_from: state.archiveDateFrom,
    date_to: state.archiveDateTo,
  };
}

function applyArchiveSettings(settings) {
  state.archiveQ = settings.q || "";
  state.archiveItemType = archiveItemTypeOptions().some(([value]) => value === settings.item_type) ? settings.item_type : "";
  state.archiveRecordType = archiveRecordTypeOptions().some(([value]) => value === settings.record_type) ? settings.record_type : "";
  state.archivePreset = settings.preset === "unlinked_communications" ? "unlinked_communications" : "";
  state.archiveReviewStatus = archiveReviewStatusOptions().some(([value]) => value === settings.review_status) ? settings.review_status : "";
  state.archiveTriageLane = archiveTriageLaneOptions().some(([value]) => value === settings.triage_lane) ? settings.triage_lane : "";
  if (state.archiveTriageLane) state.archivePreset = "unlinked_communications";
  state.archiveDateFrom = dateInputValue(settings.date_from || "");
  state.archiveDateTo = dateInputValue(settings.date_to || "");
  state.archivePage = 1;
}

function clearSelectedArchiveSavedView() {
  state.archiveSavedViewId = "";
}

function resetArchiveView() {
  state.archiveQ = "";
  state.archiveItemType = "";
  state.archiveRecordType = "";
  state.archivePreset = "";
  state.archiveReviewStatus = "";
  state.archiveTriageLane = "";
  state.archiveDateFrom = "";
  state.archiveDateTo = "";
  state.archiveSavedViewId = "";
  state.archivePage = 1;
}

function archiveSavedViewControls(savedViews) {
  const selectedId = state.archiveSavedViewId || "";
  return `
    <select id="archiveSavedView" aria-label="Saved archive view">
      <option value="">Saved views</option>
      ${savedViews
        .map((view) => {
          const count = typeof view.record_count === "number" ? ` (${formatNumber(view.record_count)})` : "";
          return `<option value="${view.id}" ${String(view.id) === String(selectedId) ? "selected" : ""}>${escapeHtml(`${view.name}${count}`)}</option>`;
        })
        .join("")}
    </select>
    <button class="text-button" id="saveArchiveViewButton">Save View</button>
    <button class="text-button" id="deleteArchiveViewButton" ${selectedId ? "" : "disabled"}>Delete</button>
    <button class="text-button" id="resetArchiveViewButton">Reset View</button>
  `;
}

function archiveItemTypeOptions() {
  return [
    ["", "All item types"],
    ["call", "Calls"],
    ["document", "Documents"],
    ["text_message", "Text Messages"],
    ["order", "Orders"],
    ["lead_conversion", "Lead Conversions"],
  ];
}

function archiveRecordTypeOptions() {
  return [
    ["", "All records"],
    ["person", "People"],
    ["company", "Companies"],
    ["lead", "Leads"],
    ["deal", "Deals"],
    ["unlinked", "Unlinked"],
  ];
}

function archiveReviewStatusOptions() {
  return [
    ["", "All review statuses"],
    ["unreviewed", "Unreviewed"],
    ["needs_lookup", "Needs Lookup"],
    ["ready_to_link", "Ready to Link"],
    ["archive_only", "Archive-only Reviewed"],
  ];
}

function archiveTriageLaneOptions() {
  return [
    ["", "All triage lanes"],
    ["batch_archive_only", "Likely archive-only"],
    ["needs_lookup", "Needs lookup"],
    ["ready_to_link_candidate", "Ready-to-link candidate"],
    ["manual_review", "Manual review"],
  ];
}

function archiveReviewStatusLabel(status) {
  return {
    unreviewed: "Unreviewed",
    needs_lookup: "Needs Lookup",
    ready_to_link: "Ready to Link",
    archive_only: "Archive-only Reviewed",
  }[status] || "Unreviewed";
}

function linkedResourceKindList(kindCounts) {
  if (!kindCounts.length) return "";
  return `
    <div class="cleanup-record-stats">
      ${kindCounts.map((item) => `<span>${escapeHtml(item.value)} ${formatNumber(item.count)}</span>`).join("")}
    </div>
  `;
}

function currentLinkedResourceSettings() {
  return {
    q: state.linkedResourceQ,
    kind: state.linkedResourceKind,
    record_type: state.linkedResourceRecordType,
  };
}

function applyLinkedResourceSettings(settings) {
  state.linkedResourceQ = settings.q || "";
  state.linkedResourceKind = settings.kind || "";
  const recordType = settings.record_type || "";
  state.linkedResourceRecordType = linkedResourceRecordTypeOptions().some(([value]) => value === recordType) ? recordType : "";
  state.linkedResourcePage = 1;
}

function clearSelectedLinkedResourceSavedView() {
  state.linkedResourceSavedViewId = "";
}

function resetLinkedResourceView() {
  state.linkedResourceQ = "";
  state.linkedResourceKind = "";
  state.linkedResourceRecordType = "";
  state.linkedResourceSavedViewId = "";
  state.linkedResourcePage = 1;
}

function linkedResourceSavedViewControls(savedViews) {
  const selectedId = state.linkedResourceSavedViewId || "";
  return `
    <select id="linkedResourceSavedView" aria-label="Saved linked-resource view">
      <option value="">Saved views</option>
      ${savedViews
        .map((view) => {
          const count = typeof view.record_count === "number" ? ` (${formatNumber(view.record_count)})` : "";
          return `<option value="${view.id}" ${String(view.id) === String(selectedId) ? "selected" : ""}>${escapeHtml(`${view.name}${count}`)}</option>`;
        })
        .join("")}
    </select>
    <button class="text-button" id="saveLinkedResourceViewButton">Save View</button>
    <button class="text-button" id="deleteLinkedResourceViewButton" ${selectedId ? "" : "disabled"}>Delete</button>
    <button class="text-button" id="resetLinkedResourceViewButton">Reset View</button>
  `;
}

function linkedResourceRecordTypeOptions() {
  return [
    ["", "All records"],
    ["person", "People"],
    ["company", "Companies"],
    ["lead", "Leads"],
    ["deal", "Deals"],
  ];
}

function currentTagSettings() {
  return {
    q: state.tagQ,
    record_type: state.tagRecordType,
  };
}

function applyTagSettings(settings) {
  state.tagQ = settings.q || "";
  const recordType = settings.record_type || "";
  state.tagRecordType = tagRecordTypeOptions().some(([value]) => value === recordType) ? recordType : "";
  state.tagPage = 1;
}

function clearSelectedTagSavedView() {
  state.tagSavedViewId = "";
}

function resetTagView() {
  state.tagQ = "";
  state.tagRecordType = "";
  state.tagSavedViewId = "";
  state.tagPage = 1;
}

function tagSavedViewControls(savedViews) {
  const selectedId = state.tagSavedViewId || "";
  return `
    <select id="tagSavedView" aria-label="Saved tag view">
      <option value="">Saved views</option>
      ${savedViews
        .map((view) => {
          const count = typeof view.record_count === "number" ? ` (${formatNumber(view.record_count)})` : "";
          return `<option value="${view.id}" ${String(view.id) === String(selectedId) ? "selected" : ""}>${escapeHtml(`${view.name}${count}`)}</option>`;
        })
        .join("")}
    </select>
    <button class="text-button" id="saveTagViewButton">Save View</button>
    <button class="text-button" id="deleteTagViewButton" ${selectedId ? "" : "disabled"}>Delete</button>
    <button class="text-button" id="resetTagViewButton">Reset View</button>
  `;
}

function tagRecordTypeOptions() {
  return [
    ["", "All records"],
    ["person", "People"],
    ["company", "Companies"],
    ["lead", "Leads"],
    ["deal", "Deals"],
  ];
}

function currentCustomFieldSettings() {
  return {
    q: state.customFieldQ,
    record_type: state.customFieldRecordType,
  };
}

function applyCustomFieldSettings(settings) {
  state.customFieldQ = settings.q || "";
  const recordType = settings.record_type || "";
  state.customFieldRecordType = customFieldRecordTypeOptions().some(([value]) => value === recordType) ? recordType : "";
  state.customFieldPage = 1;
}

function clearSelectedCustomFieldSavedView() {
  state.customFieldSavedViewId = "";
}

function resetCustomFieldView() {
  state.customFieldQ = "";
  state.customFieldRecordType = "";
  state.customFieldSavedViewId = "";
  state.customFieldPage = 1;
}

function customFieldSavedViewControls(savedViews) {
  const selectedId = state.customFieldSavedViewId || "";
  return `
    <select id="customFieldSavedView" aria-label="Saved custom-field view">
      <option value="">Saved views</option>
      ${savedViews
        .map((view) => {
          const count = typeof view.record_count === "number" ? ` (${formatNumber(view.record_count)})` : "";
          return `<option value="${view.id}" ${String(view.id) === String(selectedId) ? "selected" : ""}>${escapeHtml(`${view.name}${count}`)}</option>`;
        })
        .join("")}
    </select>
    <button class="text-button" id="saveCustomFieldViewButton">Save View</button>
    <button class="text-button" id="deleteCustomFieldViewButton" ${selectedId ? "" : "disabled"}>Delete</button>
    <button class="text-button" id="resetCustomFieldViewButton">Reset View</button>
  `;
}

function customFieldRecordTypeOptions() {
  return [
    ["", "All records"],
    ["person", "People"],
    ["company", "Companies"],
    ["lead", "Leads"],
    ["deal", "Deals"],
  ];
}

function savedViewsSection(savedViews) {
  if (!savedViews.length) return "";
  return `
    <div class="band">
      <div class="band-header">
        <h3>Saved Views</h3>
        <span class="muted">${formatNumber(savedViews.length)} recent</span>
      </div>
      <div class="saved-view-grid">
        ${savedViews
          .map((view) => `
            <button class="saved-view-button" data-view-id="${view.id}">
              <strong>${escapeHtml(view.name)}</strong>
              <span>${escapeHtml(savedViewCountLabel(view))}</span>
              <small>${escapeHtml(savedViewSummary(view.settings || {}))}</small>
            </button>
          `)
          .join("")}
      </div>
    </div>
  `;
}

function savedViewSummary(settings) {
  const parts = [];
  if (settings.status) parts.push(statusLabel(settings.status));
  if (settings.q) parts.push(`Search: ${settings.q}`);
  if (settings.activity_type) parts.push(labelize(settings.activity_type));
  if (settings.item_type) parts.push(archiveItemLabel(settings.item_type));
  if (settings.kind) parts.push(settings.kind);
  if (settings.preset === "unlinked_communications") parts.push("Unlinked calls/texts");
  if (settings.record_type) parts.push(settings.record_type === "unlinked" ? "No linked record" : labelize(settings.record_type));
  if (settings.source) parts.push(settings.source === "imported" ? "Imported tasks" : "Local tasks");
  if (settings.date_field) parts.push(`Date: ${labelize(settings.date_field)}`);
  if (settings.date_from) parts.push(`From ${settings.date_from}`);
  if (settings.date_to) parts.push(`To ${settings.date_to}`);
  if (settings.status_value) parts.push(settings.status_value);
  if (settings.profile_value) parts.push(settings.profile_value);
  if (settings.quality_issue) parts.push(`Quality: ${labelize(settings.quality_issue)}`);
  if (settings.provenance) parts.push(provenanceFilterLabel(settings.provenance));
  if (settings.owner_user_id) parts.push(`Owner #${settings.owner_user_id}`);
  if (settings.tag_id) parts.push(`Tag #${settings.tag_id}`);
  if (settings.sort) parts.push(`Sort: ${labelize(settings.sort)} ${settings.direction === "asc" ? "Asc" : "Desc"}`);
  return parts.length ? parts.join(" · ") : "Default list";
}

function savedViewCountLabel(view) {
  const listNames = {
    tasks: "Follow Up",
    activity: "Activity",
    archive: "Archive",
    linked_resources: "Linked Resources",
    tags: "Tags",
    custom_fields: "Custom Fields",
  };
  const nouns = {
    tasks: "tasks",
    activity: "items",
    archive: "items",
    linked_resources: "links",
    tags: "tags",
    custom_fields: "fields",
  };
  const listName = listNames[view.list_type] || listTitles[view.list_type] || labelize(view.list_type);
  const noun = nouns[view.list_type] || "records";
  return typeof view.record_count === "number"
    ? `${listName} · ${formatNumber(view.record_count)} ${noun}`
    : listName;
}

function wireSavedViewButtons(root, savedViews) {
  root.querySelectorAll(".saved-view-button").forEach((button) => {
    button.addEventListener("click", () => {
      const view = savedViews.find((item) => String(item.id) === String(button.dataset.viewId));
      if (!view) return;
      if (view.list_type === "tasks") {
        applyTaskSettings(view.settings || {});
        state.taskSavedViewId = String(view.id);
        setView("followup");
        return;
      }
      if (view.list_type === "activity") {
        applyActivitySettings(view.settings || {});
        state.activitySavedViewId = String(view.id);
        setView("activity");
        return;
      }
      if (view.list_type === "archive") {
        applyArchiveSettings(view.settings || {});
        state.archiveSavedViewId = String(view.id);
        setView("archive");
        return;
      }
      if (view.list_type === "linked_resources") {
        applyLinkedResourceSettings(view.settings || {});
        state.linkedResourceSavedViewId = String(view.id);
        setView("linkedResources");
        return;
      }
      if (view.list_type === "tags") {
        applyTagSettings(view.settings || {});
        state.tagSavedViewId = String(view.id);
        setView("tags");
        return;
      }
      if (view.list_type === "custom_fields") {
        applyCustomFieldSettings(view.settings || {});
        state.customFieldSavedViewId = String(view.id);
        setView("customFields");
        return;
      }
      state.listType = view.list_type;
      applyListSettings(view.settings || {});
      state.listSavedViewId[view.list_type] = String(view.id);
      setView(view.list_type);
    });
  });
}

function applicationSegmentSection(segments) {
  const populated = segments.filter((segment) => segment.values?.length);
  if (!populated.length) return "";
  return `
    <div class="band">
      <div class="band-header">
        <h3>Application Segments</h3>
        <span class="muted">Leads by profile</span>
      </div>
      <div class="profile-segment-grid">
        ${populated
          .map((segment) => {
            const maxCount = Math.max(...segment.values.map((item) => item.count), 1);
            return `
              <div class="profile-segment">
                <h4>${escapeHtml(segment.field_name)}</h4>
                ${segment.values
                  .map((item) => {
                    const width = Math.max(4, Math.round((item.count / maxCount) * 100));
                    return `
                      <button class="profile-segment-button" data-field="${escapeHtml(segment.field_name)}" data-value="${escapeHtml(item.value)}">
                        <span>${escapeHtml(item.value)}</span>
                        <strong>${formatNumber(item.count)}</strong>
                        <i style="width:${width}%"></i>
                      </button>
                    `;
                  })
                  .join("")}
              </div>
            `;
          })
          .join("")}
      </div>
    </div>
  `;
}

function recordTable(records, context) {
  if (!records.length) {
    return `<div class="empty-state"><h3>No records</h3><p>Nothing matched this view.</p></div>`;
  }
  return `
    <table class="data-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Type</th>
          <th>Detail</th>
          <th>Updated</th>
        </tr>
      </thead>
      <tbody>
        ${records
          .map((record) => {
            const detailType = record.type || record.kind || state.listType.slice(0, -1);
            const badge = record.kind || record.type || state.listType;
            const third = record.match_context || record.email || record.stage_name || record.organization_name || record.phone || "";
            return `
              <tr>
                <td>
                  <button class="record-button" data-type="${detailType}" data-id="${record.source_id}">
                    ${escapeHtml(record.name || "(blank)")}
                  </button>
                </td>
                <td><span class="pill">${escapeHtml(badge)}</span></td>
                <td class="muted">${escapeHtml(third)}</td>
                <td class="muted">${formatDate(record.updated_at)}</td>
              </tr>
            `;
          })
          .join("")}
      </tbody>
    </table>
  `;
}

function profileFilterSupported(listType) {
  return ["people", "leads"].includes(listType);
}

function ownerFilterSupported(listType) {
  return ["people", "companies", "leads"].includes(listType);
}

function ownerFilterControls(ownerOptions = []) {
  if (!ownerFilterSupported(state.listType) || !ownerOptions.length) return "";
  return `
    <select id="listOwnerFilter" aria-label="Filter by owner">
      <option value="">All owners</option>
      ${ownerOptions
        .map((item) => `<option value="${escapeHtml(item.value)}" ${String(item.value) === String(state.listOwnerUserId) ? "selected" : ""}>${escapeHtml(item.label)} (${formatNumber(item.count)})</option>`)
        .join("")}
    </select>
  `;
}

function profileFilterControls(profileData) {
  if (!profileData.fields?.length) return "";
  const selectedField = profileData.fields.find((field) => field.field_name === state.listProfileField);
  return `
    <select id="listProfileField" aria-label="Filter by Application Profile field">
      <option value="">All profile fields</option>
      ${profileData.fields
        .map((field) => `<option value="${escapeHtml(field.field_name)}" ${field.field_name === state.listProfileField ? "selected" : ""}>${escapeHtml(field.field_name)}</option>`)
        .join("")}
    </select>
    <select id="listProfileValue" aria-label="Filter by Application Profile value" ${selectedField ? "" : "disabled"}>
      <option value="">All profile values</option>
      ${(selectedField?.values || [])
        .map((item) => `<option value="${escapeHtml(item.value)}" ${item.value === state.listProfileValue ? "selected" : ""}>${escapeHtml(item.value)} (${formatNumber(item.count)})</option>`)
        .join("")}
    </select>
  `;
}

function currentListSort() {
  const options = listSortOptions[state.listType] || listSortOptions.people;
  const current = state.listSort[state.listType] || { field: "updated_at", direction: "desc" };
  const validField = options.some(([field]) => field === current.field) ? current.field : "updated_at";
  const validDirection = current.direction === "asc" ? "asc" : "desc";
  state.listSort[state.listType] = { field: validField, direction: validDirection };
  return state.listSort[state.listType];
}

function listSortControls() {
  const sort = currentListSort();
  const options = listSortOptions[state.listType] || listSortOptions.people;
  return `
    <div class="sort-control-group" aria-label="List sorting">
      <span class="tool-label">Sort</span>
      <select id="listSortField" aria-label="Sort by field">
        ${options
          .map(([field, label]) => `<option value="${escapeHtml(field)}" ${field === sort.field ? "selected" : ""}>${escapeHtml(label)}</option>`)
          .join("")}
      </select>
      <select id="listSortDirection" aria-label="Sort direction">
        <option value="asc" ${sort.direction === "asc" ? "selected" : ""}>Ascending</option>
        <option value="desc" ${sort.direction === "desc" ? "selected" : ""}>Descending</option>
      </select>
    </div>
  `;
}

function defaultListSortDirection(field) {
  return ["created_at", "updated_at", "estimated_close_date", "value"].includes(field) ? "desc" : "asc";
}

function setListSort(field, direction = null) {
  const current = currentListSort();
  const options = listSortOptions[state.listType] || listSortOptions.people;
  if (!options.some(([optionField]) => optionField === field)) return;
  const nextDirection = direction || (current.field === field ? (current.direction === "asc" ? "desc" : "asc") : defaultListSortDirection(field));
  clearSelectedSavedView();
  state.listSort[state.listType] = {
    field,
    direction: nextDirection === "asc" ? "asc" : "desc",
  };
  state.page = 1;
  renderList();
}

function currentListStatusFilter(statusOptions = null) {
  const current = state.listStatusFilters[state.listType] || { field: "", value: "" };
  if (statusOptions) {
    const validField = statusOptions.find((item) => item.field === current.field);
    if (!validField) {
      current.field = "";
      current.value = "";
    } else if (!validField.values.some((item) => item.value === current.value)) {
      current.value = "";
    }
  }
  state.listStatusFilters[state.listType] = current;
  return current;
}

function listStatusFilterControls(statusOptions) {
  if (!statusOptions.length) return "";
  const current = currentListStatusFilter(statusOptions);
  const selectedField = statusOptions.find((item) => item.field === current.field);
  return `
    <select id="listStatusField" aria-label="Filter by status field">
      <option value="">All statuses/stages</option>
      ${statusOptions
        .map((item) => `<option value="${escapeHtml(item.field)}" ${item.field === current.field ? "selected" : ""}>${escapeHtml(item.label)}</option>`)
        .join("")}
    </select>
    <select id="listStatusValue" aria-label="Filter by status value" ${selectedField ? "" : "disabled"}>
      <option value="">All values</option>
      ${(selectedField?.values || [])
        .map((item) => `<option value="${escapeHtml(item.value)}" ${item.value === current.value ? "selected" : ""}>${escapeHtml(item.value)} (${formatNumber(item.count)})</option>`)
        .join("")}
    </select>
  `;
}

function currentListDateFilter(dateOptions = null) {
  const current = state.listDateFilters[state.listType] || { field: "", from: "", to: "" };
  if (dateOptions) {
    const validField = dateOptions.find((item) => item.field === current.field);
    if (!validField) {
      current.field = "";
      current.from = "";
      current.to = "";
    }
  }
  state.listDateFilters[state.listType] = current;
  return current;
}

function listDateFilterControls(dateOptions = []) {
  if (!dateOptions.length) return "";
  const current = currentListDateFilter(dateOptions);
  const selectedField = dateOptions.find((item) => item.field === current.field);
  return `
    <div class="compact-date-filter">
      <select id="listDateField" aria-label="Filter by date field">
        <option value="">All dates</option>
        ${dateOptions
          .map((item) => `<option value="${escapeHtml(item.field)}" ${item.field === current.field ? "selected" : ""}>${escapeHtml(item.label)}</option>`)
          .join("")}
      </select>
      <input id="listDateFrom" type="date" value="${escapeHtml(current.from)}" aria-label="From date" ${selectedField ? "" : "disabled"}>
      <input id="listDateTo" type="date" value="${escapeHtml(current.to)}" aria-label="To date" ${selectedField ? "" : "disabled"}>
    </div>
  `;
}

function currentListQualityIssue(qualityOptions = null) {
  const current = state.listQualityIssues[state.listType] || "";
  const validIssues = qualityOptions
    ? qualityOptions.map((item) => item.issue)
    : Object.keys(listQualityIssueLabels[state.listType] || {});
  const validIssue = validIssues.includes(current) ? current : "";
  state.listQualityIssues[state.listType] = validIssue;
  return validIssue;
}

function currentListProvenanceFilter(options = null) {
  const current = state.listProvenanceFilters[state.listType] || "";
  const validValues = options ? options.map((item) => item.value) : ["imported", "local", "changed"];
  const validValue = validValues.includes(current) ? current : "";
  state.listProvenanceFilters[state.listType] = validValue;
  return validValue;
}

function provenanceFilterLabel(value) {
  return {
    imported: "Imported from Zendesk",
    local: "Local only",
    changed: "Has local changes",
  }[value] || "";
}

function listProvenanceFilterControls(options = []) {
  if (!options.length) return "";
  const current = currentListProvenanceFilter(options);
  return `
    <select id="listProvenanceFilter" aria-label="Filter by source">
      <option value="">All sources</option>
      ${options
        .map((item) => `<option value="${escapeHtml(item.value)}" ${item.value === current ? "selected" : ""}>${escapeHtml(item.label)} (${formatNumber(item.count)})</option>`)
        .join("")}
    </select>
  `;
}

function listQualityFilterControls(qualityOptions = []) {
  if (!qualityOptions.length) return "";
  const current = currentListQualityIssue(qualityOptions);
  return `
    <select id="listQualityIssue" aria-label="Filter by data quality issue">
      <option value="">All quality</option>
      ${qualityOptions
        .map((item) => `<option value="${escapeHtml(item.issue)}" ${item.issue === current ? "selected" : ""}>${escapeHtml(item.label)} (${formatNumber(item.count)})</option>`)
        .join("")}
    </select>
  `;
}

function currentListSettings() {
  const sort = currentListSort();
  const statusFilter = currentListStatusFilter();
  const dateFilter = currentListDateFilter();
  const qualityIssue = currentListQualityIssue();
  const provenance = currentListProvenanceFilter();
  return {
    q: state.q,
    tag_id: state.listTagId,
    status_field: statusFilter.field,
    status_value: statusFilter.value,
    owner_user_id: ownerFilterSupported(state.listType) ? state.listOwnerUserId : "",
    profile_field: state.listProfileField,
    profile_value: state.listProfileValue,
    quality_issue: qualityIssue,
    provenance,
    date_field: dateFilter.field,
    date_from: dateFilter.from,
    date_to: dateFilter.to,
    sort: sort.field,
    direction: sort.direction,
  };
}

function applyListSettings(settings = {}) {
  state.q = settings.q || "";
  state.listTagId = settings.tag_id || "";
  state.listStatusFilters[state.listType] = {
    field: settings.status_field || "",
    value: settings.status_value || "",
  };
  state.listDateFilters[state.listType] = {
    field: settings.date_field || "",
    from: settings.date_from || "",
    to: settings.date_to || "",
  };
  state.listQualityIssues[state.listType] = settings.quality_issue || "";
  state.listProvenanceFilters[state.listType] = settings.provenance || "";
  state.listOwnerUserId = ownerFilterSupported(state.listType) ? settings.owner_user_id || "" : "";
  if (profileFilterSupported(state.listType)) {
    state.listProfileField = settings.profile_field || "";
    state.listProfileValue = settings.profile_value || "";
  } else {
    state.listProfileField = "";
    state.listProfileValue = "";
  }
  state.listSort[state.listType] = {
    field: settings.sort || "updated_at",
    direction: settings.direction === "asc" ? "asc" : "desc",
  };
  state.page = 1;
}

function clearSelectedSavedView() {
  state.listSavedViewId[state.listType] = "";
}

function resetCurrentListView() {
  state.q = "";
  els.search.value = "";
  state.listTagId = "";
  state.listOwnerUserId = "";
  state.listProfileField = "";
  state.listProfileValue = "";
  state.listStatusFilters[state.listType] = { field: "", value: "" };
  state.listDateFilters[state.listType] = { field: "", from: "", to: "" };
  state.listQualityIssues[state.listType] = "";
  state.listProvenanceFilters[state.listType] = "";
  state.listSort[state.listType] = { field: "updated_at", direction: "desc" };
  state.listSavedViewId[state.listType] = "";
  state.page = 1;
}

function currentTaskSettings() {
  return {
    status: state.taskStatus,
    q: state.taskQ,
    record_type: state.taskRecordType,
    source: state.taskSource,
    sort: state.taskSort,
    direction: state.taskDirection,
  };
}

function applyTaskSettings(settings = {}) {
  const status = settings.status || "open";
  state.taskStatus = ["open", "overdue", "due_soon", "completed", "all"].includes(status) ? status : "open";
  state.taskQ = settings.q || "";
  const recordType = settings.record_type || "";
  state.taskRecordType = ["", "person", "company", "lead", "deal", "unlinked"].includes(recordType) ? recordType : "";
  const source = settings.source || "";
  state.taskSource = ["", "imported", "local"].includes(source) ? source : "";
  const sortFields = taskSortOptions().map(([field]) => field);
  state.taskSort = sortFields.includes(settings.sort) ? settings.sort : "due_date";
  state.taskDirection = settings.direction === "desc" ? "desc" : "asc";
  state.taskPage = 1;
}

function clearSelectedTaskSavedView() {
  state.taskSavedViewId = "";
}

function resetTaskView() {
  state.taskStatus = "open";
  state.taskQ = "";
  state.taskRecordType = "";
  state.taskSource = "";
  state.taskSort = "due_date";
  state.taskDirection = "asc";
  state.taskSavedViewId = "";
  state.taskPage = 1;
}

function taskSavedViewControls(savedViews) {
  const selectedId = state.taskSavedViewId || "";
  return `
    <select id="taskSavedView" aria-label="Saved follow-up view">
      <option value="">Saved views</option>
      ${savedViews
        .map((view) => {
          const count = typeof view.record_count === "number" ? ` (${formatNumber(view.record_count)})` : "";
          return `<option value="${view.id}" ${String(view.id) === String(selectedId) ? "selected" : ""}>${escapeHtml(`${view.name}${count}`)}</option>`;
        })
        .join("")}
    </select>
    <button class="text-button" id="saveTaskViewButton">Save View</button>
    <button class="text-button" id="deleteTaskViewButton" ${selectedId ? "" : "disabled"}>Delete</button>
    <button class="text-button" id="resetTaskViewButton">Reset View</button>
  `;
}

function savedViewControls(savedViews) {
  const selectedId = state.listSavedViewId[state.listType] || "";
  return `
    <select id="listSavedView" aria-label="Saved list view">
      <option value="">Saved views</option>
      ${savedViews
        .map((view) => {
          const count = typeof view.record_count === "number" ? ` (${formatNumber(view.record_count)})` : "";
          return `<option value="${view.id}" ${String(view.id) === String(selectedId) ? "selected" : ""}>${escapeHtml(`${view.name}${count}`)}</option>`;
        })
        .join("")}
    </select>
    <button class="text-button" id="saveListViewButton">Save View</button>
    <button class="text-button" id="deleteListViewButton" ${selectedId ? "" : "disabled"}>Delete</button>
    <button class="text-button" id="resetListViewButton">Reset View</button>
  `;
}

async function renderList() {
  setStatus(`Loading ${listTitles[state.listType]}`);
  const sort = currentListSort();
  const statusFilter = currentListStatusFilter();
  const dateFilter = currentListDateFilter();
  const qualityIssue = currentListQualityIssue();
  const provenance = currentListProvenanceFilter();
  const params = new URLSearchParams({
    type: state.listType,
    page: String(state.page),
    page_size: "50",
    q: state.q,
    sort: sort.field,
    direction: sort.direction,
  });
  if (state.listTagId) params.set("tag_id", state.listTagId);
  if (statusFilter.field && statusFilter.value) {
    params.set("status_field", statusFilter.field);
    params.set("status_value", statusFilter.value);
  }
  if (ownerFilterSupported(state.listType) && state.listOwnerUserId) {
    params.set("owner_user_id", state.listOwnerUserId);
  }
  if (qualityIssue) {
    params.set("quality_issue", qualityIssue);
  }
  if (provenance) {
    params.set("provenance", provenance);
  }
  if (profileFilterSupported(state.listType) && state.listProfileField && state.listProfileValue) {
    params.set("profile_field", state.listProfileField);
    params.set("profile_value", state.listProfileValue);
  }
  if (dateFilter.field && (dateFilter.from || dateFilter.to)) {
    params.set("date_field", dateFilter.field);
    if (dateFilter.from) params.set("date_from", dateFilter.from);
    if (dateFilter.to) params.set("date_to", dateFilter.to);
  }
  const exportUrl = `/api/export_list?${params.toString()}`;
  const [data, tagData, profileData, savedViewData] = await Promise.all([
    fetchJson(`/api/list?${params.toString()}`),
    fetchJson("/api/tags?page_size=100"),
    profileFilterSupported(state.listType)
      ? fetchJson(`/api/profile_filters?type=${encodeURIComponent(state.listType)}`)
      : Promise.resolve({ fields: [] }),
    fetchJson(`/api/saved_views?type=${encodeURIComponent(state.listType)}`),
  ]);
  const savedViews = savedViewData.views || [];
  if (state.listSavedViewId[state.listType] && !savedViews.some((view) => String(view.id) === String(state.listSavedViewId[state.listType]))) {
    state.listSavedViewId[state.listType] = "";
  }
  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));
  const selectedTag = tagData.tags.find((tag) => String(tag.source_id) === String(state.listTagId));
  const selectedStatusField = (data.status_options || []).find((item) => item.field === data.status_field);
  const selectedStatusValue = selectedStatusField?.values.find((item) => item.value === data.status_value);
  const selectedOwner = (data.owner_options || []).find((item) => String(item.value) === String(data.owner_user_id));
  const selectedProfileField = profileData.fields.find((field) => field.field_name === state.listProfileField);
  const selectedProfileValue = selectedProfileField?.values.find((item) => item.value === state.listProfileValue);
  const selectedQualityIssue = (data.quality_options || []).find((item) => item.issue === data.quality_issue);
  const selectedProvenance = (data.provenance_options || []).find((item) => item.value === data.provenance);
  const selectedDateField = (data.date_options || []).find((item) => item.field === data.date_field);
  const dateRangeText = data.date_from && data.date_to
    ? `${data.date_from} to ${data.date_to}`
    : data.date_from
      ? `from ${data.date_from}`
      : data.date_to
        ? `through ${data.date_to}`
        : "";
  const dateSummary = selectedDateField && dateRangeText ? ` · ${escapeHtml(selectedDateField.label)} ${escapeHtml(dateRangeText)}` : "";
  els.list.innerHTML = `
    <div class="section-header">
      <div>
        <h2>${escapeHtml(listTitles[state.listType])}</h2>
        <p>${formatNumber(data.total)} records${selectedTag ? ` tagged ${escapeHtml(selectedTag.display_name)}` : ""}${selectedOwner ? ` · Owner: ${escapeHtml(selectedOwner.label)}` : ""}${selectedQualityIssue ? ` · Quality: ${escapeHtml(selectedQualityIssue.label)}` : ""}${selectedProvenance ? ` · Source: ${escapeHtml(selectedProvenance.label)}` : ""}${selectedStatusValue ? ` · ${escapeHtml(selectedStatusField.label)}: ${escapeHtml(selectedStatusValue.value)}` : ""}${selectedProfileValue ? ` · ${escapeHtml(state.listProfileField)}: ${escapeHtml(selectedProfileValue.value)}` : ""}${dateSummary}</p>
      </div>
      <button class="text-button" id="newRecordButton">New</button>
    </div>
    <div class="table-tools">
      <div class="filter-row">
        ${savedViewControls(savedViews)}
        <input id="listSearch" type="search" value="${escapeHtml(state.q)}" placeholder="Filter ${escapeHtml(listTitles[state.listType].toLowerCase())}">
        <select id="listTagFilter" aria-label="Filter by tag">
          <option value="">All tags</option>
          ${tagData.tags
            .map((tag) => `<option value="${tag.source_id}" ${String(tag.source_id) === String(state.listTagId) ? "selected" : ""}>${escapeHtml(tag.display_name || "(blank tag)")}</option>`)
            .join("")}
        </select>
        ${ownerFilterControls(data.owner_options || [])}
        ${listProvenanceFilterControls(data.provenance_options || [])}
        ${listQualityFilterControls(data.quality_options || [])}
        ${listStatusFilterControls(data.status_options || [])}
        ${profileFilterControls(profileData)}
        ${listDateFilterControls(data.date_options || [])}
        ${listSortControls()}
      </div>
      <div class="pager">
        <a class="text-button action-link" href="${escapeHtml(exportUrl)}">Export CSV</a>
        <button class="icon-button" id="prevPage" title="Previous page" ${state.page <= 1 ? "disabled" : ""}>‹</button>
        <span class="muted">Page ${state.page} of ${totalPages}</span>
        <button class="icon-button" id="nextPage" title="Next page" ${state.page >= totalPages ? "disabled" : ""}>›</button>
      </div>
    </div>
    <div class="table-scroll">
      ${listTable(data.records)}
    </div>
  `;
  const listSearch = document.querySelector("#listSearch");
  const listSavedView = document.querySelector("#listSavedView");
  const saveListViewButton = document.querySelector("#saveListViewButton");
  const deleteListViewButton = document.querySelector("#deleteListViewButton");
  const resetListViewButton = document.querySelector("#resetListViewButton");
  const listTagFilter = document.querySelector("#listTagFilter");
  const listOwnerFilter = document.querySelector("#listOwnerFilter");
  const listProvenanceFilter = document.querySelector("#listProvenanceFilter");
  const listQualityIssue = document.querySelector("#listQualityIssue");
  const listStatusField = document.querySelector("#listStatusField");
  const listStatusValue = document.querySelector("#listStatusValue");
  const listProfileField = document.querySelector("#listProfileField");
  const listProfileValue = document.querySelector("#listProfileValue");
  const listDateField = document.querySelector("#listDateField");
  const listDateFrom = document.querySelector("#listDateFrom");
  const listDateTo = document.querySelector("#listDateTo");
  const listSortField = document.querySelector("#listSortField");
  const listSortDirection = document.querySelector("#listSortDirection");
  document.querySelector("#newRecordButton").addEventListener("click", () => {
    renderCreateForm(state.listType).catch((error) => {
      setStatus("Error");
      els.detail.innerHTML = `<div class="empty-detail"><h2>Could not open create form</h2><p>${escapeHtml(error.message)}</p></div>`;
    });
  });
  listSavedView.addEventListener("change", () => {
    const selectedId = listSavedView.value;
    state.listSavedViewId[state.listType] = selectedId;
    if (!selectedId) {
      renderList();
      return;
    }
    const view = savedViews.find((item) => String(item.id) === String(selectedId));
    if (view) {
      applyListSettings(view.settings);
      state.listSavedViewId[state.listType] = selectedId;
    }
    renderList();
  });
  saveListViewButton.addEventListener("click", async () => {
    const name = window.prompt("Save this view as");
    if (!name?.trim()) return;
    setStatus("Saving view");
    const saved = await postJson("/api/save_view", {
      type: state.listType,
      name: name.trim(),
      settings: currentListSettings(),
    });
    state.listSavedViewId[state.listType] = saved.view?.id ? String(saved.view.id) : "";
    await renderList();
    setStatus("View saved");
  });
  deleteListViewButton.addEventListener("click", async () => {
    const viewId = state.listSavedViewId[state.listType];
    if (!viewId) return;
    const ok = window.confirm("Delete this saved view?");
    if (!ok) return;
    setStatus("Deleting view");
    await postJson("/api/delete_view", { id: Number(viewId) });
    state.listSavedViewId[state.listType] = "";
    await renderList();
    setStatus("View deleted");
  });
  resetListViewButton.addEventListener("click", () => {
    resetCurrentListView();
    renderList();
  });
  listSearch.addEventListener("input", () => {
    window.clearTimeout(state.debounce);
    state.debounce = window.setTimeout(() => {
      clearSelectedSavedView();
      state.q = listSearch.value.trim();
      state.page = 1;
      renderList();
    }, 220);
  });
  listTagFilter.addEventListener("change", () => {
    clearSelectedSavedView();
    state.listTagId = listTagFilter.value;
    state.page = 1;
    renderList();
  });
  if (listOwnerFilter) {
    listOwnerFilter.addEventListener("change", () => {
      clearSelectedSavedView();
      state.listOwnerUserId = listOwnerFilter.value;
      state.page = 1;
      renderList();
    });
  }
  if (listProvenanceFilter) {
    listProvenanceFilter.addEventListener("change", () => {
      clearSelectedSavedView();
      state.listProvenanceFilters[state.listType] = listProvenanceFilter.value;
      state.page = 1;
      renderList();
    });
  }
  if (listQualityIssue) {
    listQualityIssue.addEventListener("change", () => {
      clearSelectedSavedView();
      state.listQualityIssues[state.listType] = listQualityIssue.value;
      state.page = 1;
      renderList();
    });
  }
  if (listStatusField) {
    listStatusField.addEventListener("change", () => {
      clearSelectedSavedView();
      state.listStatusFilters[state.listType].field = listStatusField.value;
      state.listStatusFilters[state.listType].value = "";
      state.page = 1;
      renderList();
    });
  }
  if (listStatusValue) {
    listStatusValue.addEventListener("change", () => {
      clearSelectedSavedView();
      state.listStatusFilters[state.listType].value = listStatusValue.value;
      state.page = 1;
      renderList();
    });
  }
  if (listProfileField) {
    listProfileField.addEventListener("change", () => {
      clearSelectedSavedView();
      state.listProfileField = listProfileField.value;
      state.listProfileValue = "";
      state.page = 1;
      renderList();
    });
  }
  if (listProfileValue) {
    listProfileValue.addEventListener("change", () => {
      clearSelectedSavedView();
      state.listProfileValue = listProfileValue.value;
      state.page = 1;
      renderList();
    });
  }
  if (listDateField) {
    listDateField.addEventListener("change", () => {
      clearSelectedSavedView();
      state.listDateFilters[state.listType].field = listDateField.value;
      state.listDateFilters[state.listType].from = "";
      state.listDateFilters[state.listType].to = "";
      state.page = 1;
      renderList();
    });
  }
  if (listDateFrom) {
    listDateFrom.addEventListener("change", () => {
      clearSelectedSavedView();
      state.listDateFilters[state.listType].from = listDateFrom.value;
      state.page = 1;
      renderList();
    });
  }
  if (listDateTo) {
    listDateTo.addEventListener("change", () => {
      clearSelectedSavedView();
      state.listDateFilters[state.listType].to = listDateTo.value;
      state.page = 1;
      renderList();
    });
  }
  listSortField.addEventListener("change", () => {
    setListSort(listSortField.value, defaultListSortDirection(listSortField.value));
  });
  listSortDirection.addEventListener("change", () => {
    setListSort(currentListSort().field, listSortDirection.value);
  });
  document.querySelector("#prevPage").addEventListener("click", () => {
    state.page = Math.max(1, state.page - 1);
    renderList();
  });
  document.querySelector("#nextPage").addEventListener("click", () => {
    state.page += 1;
    renderList();
  });
  wireRecordButtons(els.list);
  wireSortHeaderButtons(els.list);
  setStatus("Ready");
}

async function renderCreateForm(listType) {
  setStatus("Loading create form");
  const type = listType === "people" ? "person" : listType === "companies" ? "company" : listType === "leads" ? "lead" : "deal";
  const fields = createFields(type);
  const options = await fetchJson(`/api/create_options?type=${encodeURIComponent(type)}`);
  const createDetail = { type, record: {}, edit_options: options.edit_options || {} };
  els.detail.innerHTML = `
    <div class="detail-content">
      ${detailHeader(`New ${labelize(type)}`, "Local CRM record")}
      <div class="detail-section">
        <div class="inline-header">
          <h3>Create</h3>
          <button class="text-button" id="createRecordButton">Create</button>
        </div>
        <form id="createRecordForm" class="edit-grid">
          ${fields.map((field) => editFieldControl(createDetail, field)).join("")}
        </form>
        <div id="detailFormError" class="form-error" hidden></div>
      </div>
    </div>
  `;
  const createButton = document.querySelector("#createRecordButton");
  createButton.addEventListener("click", async () => {
    const form = document.querySelector("#createRecordForm");
    const fields = {};
    new FormData(form).forEach((value, key) => {
      fields[key] = value.toString().trim() || null;
    });
    clearDetailFormError();
    createButton.disabled = true;
    try {
      setStatus("Creating");
      const created = await postJson("/api/create_record", { type, fields });
      renderDetail(created.detail);
      await renderList();
      setStatus("Created");
    } catch (error) {
      showDetailFormError(error.message);
      setStatus("Create failed");
    } finally {
      createButton.disabled = false;
    }
  });
  setStatus("Ready");
}

function createFields(type) {
  if (type === "person") return ["name", "first_name", "last_name", "email", "phone", "mobile", "company_id", "title", "owner_user_id", "customer_status", "prospect_status"];
  if (type === "company") return ["name", "email", "phone", "website", "owner_user_id", "customer_status", "prospect_status"];
  if (type === "lead") return ["name", "first_name", "last_name", "organization_name", "email", "phone", "mobile", "status", "owner_user_id"];
  if (type === "deal") return ["name", "person_id", "company_id", "stage_id", "value", "currency", "hot", "estimated_close_date"];
  return [];
}

function listTable(records) {
  if (state.listType === "deals") {
    return `
      <table class="data-table">
        <thead>
          <tr>
            ${sortHeader("name", "Deal")}
            ${sortHeader("stage", "Stage")}
            ${sortHeader("value", "Value")}
            ${sortHeader("contact", "Contact")}
            <th>Source</th>
            <th>Quality</th>
            ${sortHeader("estimated_close_date", "Close Date")}
            ${sortHeader("updated_at", "Updated")}
          </tr>
        </thead>
        <tbody>
          ${records
            .map((record) => `
              <tr ${listRowAttributes("deal", record.source_id)}>
                <td><button class="record-button" data-type="deal" data-id="${record.source_id}">${escapeHtml(record.name || "(blank)")}</button></td>
                <td><span class="pill gold">${escapeHtml(record.stage_name || "")}</span></td>
                <td>${formatMoney(record.value, record.currency || "USD")}</td>
                <td class="muted">${escapeHtml(record.contact_name || record.organization_name || "")}</td>
                <td>${provenanceChips(record)}</td>
                <td>${qualityIssueChips(record.quality_issues || [])}</td>
                <td class="muted">${formatDate(record.estimated_close_date)}</td>
                <td class="muted">${formatDate(record.updated_at)}</td>
              </tr>
            `)
            .join("")}
        </tbody>
      </table>
    `;
  }
  const type = state.listType === "leads" ? "lead" : state.listType === "companies" ? "company" : "person";
  const showProfile = profileFilterSupported(state.listType);
  const showOwner = ownerFilterSupported(state.listType);
  return `
    <table class="data-table">
      <thead>
        <tr>
          ${sortHeader("name", "Name")}
          ${sortHeader("email", "Email")}
          ${sortHeader("phone", "Phone")}
          ${sortHeader(state.listType === "leads" ? "status" : "status", "Status")}
          ${showOwner ? sortHeader("owner", "Owner") : ""}
          <th>Source</th>
          <th>Quality</th>
          ${showProfile ? "<th>Profile</th>" : ""}
          ${sortHeader("updated_at", "Updated")}
        </tr>
      </thead>
      <tbody>
        ${records
          .map((record) => `
            <tr ${listRowAttributes(type, record.source_id)}>
              <td><button class="record-button" data-type="${type}" data-id="${record.source_id}">${escapeHtml(record.name || "(blank)")}</button></td>
              <td class="muted">${escapeHtml(record.email || "")}</td>
              <td class="muted">${escapeHtml(record.phone || record.mobile || "")}</td>
              <td>${record.status ? `<span class="pill">${escapeHtml(record.status)}</span>` : ""}</td>
              ${showOwner ? `<td class="muted">${escapeHtml(record.owner_name || "")}</td>` : ""}
              <td>${provenanceChips(record)}</td>
              <td>${qualityIssueChips(record.quality_issues || [])}</td>
              ${showProfile ? `<td>${profileSummary(record.profile_summary || [])}</td>` : ""}
              <td class="muted">${formatDate(record.updated_at)}</td>
            </tr>
          `)
          .join("")}
      </tbody>
    </table>
  `;
}

function provenanceChips(record) {
  const chips = [];
  if (record.provenance_label) {
    chips.push(`<span class="pill ${record.provenance_source === "local" ? "green" : ""}">${escapeHtml(record.provenance_label)}</span>`);
  }
  if (Number(record.local_change_count || 0)) {
    chips.push(`<span class="pill gold">${formatNumber(record.local_change_count)} local</span>`);
  }
  return chips.length ? `<div class="quality-chip-list">${chips.join("")}</div>` : "";
}

function listRowAttributes(recordType, sourceId) {
  if (!recordIsCurrentDetail(recordType, sourceId)) return "";
  return `class="active-record-row" aria-current="true"`;
}

function recordIsCurrentDetail(recordType, sourceId) {
  return Boolean(
    state.currentDetail &&
      state.currentDetail.type === recordType &&
      String(state.currentDetail.record?.source_id || "") === String(sourceId || "")
  );
}

function syncActiveListRows() {
  els.list.querySelectorAll(".active-record-row").forEach((row) => {
    row.classList.remove("active-record-row");
    row.removeAttribute("aria-current");
  });
  if (!state.currentDetail?.record?.source_id) return;
  const type = cssEscapeValue(state.currentDetail.type);
  const id = cssEscapeValue(state.currentDetail.record.source_id);
  const button = els.list.querySelector(`.record-button[data-type="${type}"][data-id="${id}"]`);
  const row = button?.closest("tr");
  if (!row) return;
  row.classList.add("active-record-row");
  row.setAttribute("aria-current", "true");
}

function cssEscapeValue(value) {
  if (window.CSS?.escape) return window.CSS.escape(String(value || ""));
  return String(value || "").replace(/["\\]/g, "\\$&");
}

function qualityIssueChips(issues) {
  if (!issues.length) return "";
  return `
    <div class="quality-chip-list">
      ${issues
        .map((issue) => `<span class="pill ${escapeHtml(issue.tone || "gold")}">${escapeHtml(issue.label || labelize(issue.issue || ""))}</span>`)
        .join("")}
    </div>
  `;
}

function sortHeader(field, label) {
  const sort = currentListSort();
  const isActive = sort.field === field;
  const ariaSort = isActive ? (sort.direction === "asc" ? "ascending" : "descending") : "none";
  const indicator = isActive ? `<span class="sort-indicator">${sort.direction === "asc" ? "Asc" : "Desc"}</span>` : "";
  return `
    <th aria-sort="${ariaSort}">
      <button class="sort-header-button ${isActive ? "active" : ""}" data-sort-field="${escapeHtml(field)}" type="button">
        <span>${escapeHtml(label)}</span>
        ${indicator}
      </button>
    </th>
  `;
}

function profileSummary(items) {
  if (!items.length) return `<span class="muted">No profile</span>`;
  return `
    <div class="profile-chip-list">
      ${items
        .map((item) => `<span class="profile-chip" title="${escapeHtml(item.field_name)}">${escapeHtml(item.field_value)}</span>`)
        .join("")}
    </div>
  `;
}

function cleanupProfileSummary(items) {
  return items.length ? profileSummary(items) : "";
}

function wireRecordButtons(root) {
  root.querySelectorAll(".record-button").forEach((button) => {
    button.addEventListener("click", () => showDetail(button.dataset.type, button.dataset.id));
  });
}

function wireArchiveButtons(root) {
  root.querySelectorAll(".archive-detail-button").forEach((button) => {
    button.addEventListener("click", () => showArchiveItem(button.dataset.id));
  });
}

function wireSortHeaderButtons(root) {
  root.querySelectorAll(".sort-header-button").forEach((button) => {
    button.addEventListener("click", () => setListSort(button.dataset.sortField));
  });
}

function wireTagButtons(root) {
  root.querySelectorAll(".tag-detail-button").forEach((button) => {
    button.addEventListener("click", () => showTagDetail(button.dataset.id));
  });
}

function wireCustomFieldButtons(root) {
  root.querySelectorAll(".custom-field-button").forEach((button) => {
    button.addEventListener("click", () => showCustomFieldDetail(button.dataset.recordType, button.dataset.fieldName));
  });
}

function wireCleanupGroupButtons(root) {
  root.querySelectorAll(".cleanup-group-button").forEach((button) => {
    button.addEventListener("click", () => showCleanupGroup(button.dataset.type, button.dataset.key));
  });
}

function wireCleanupSummaryButtons(root) {
  root.querySelectorAll(".cleanup-summary-button").forEach((button) => {
    button.addEventListener("click", () => {
      state.cleanupGroupType = button.dataset.type;
      state.cleanupStatus = "open";
      state.cleanupPriority = "";
      state.cleanupPolicyLane = "";
      state.cleanupDecision = "";
      state.cleanupSort = "priority";
      state.cleanupGroupPage = 1;
      state.cleanupGroupQ = "";
      state.currentCleanupGroup = null;
      setView("cleanup");
    });
  });
}

function wireNavJumps(root) {
  root.querySelectorAll(".nav-jump").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
  });
}

function wireProfileSegmentButtons(root) {
  root.querySelectorAll(".profile-segment-button").forEach((button) => {
    button.addEventListener("click", () => {
      state.q = "";
      state.listTagId = "";
      state.listOwnerUserId = "";
      state.listProfileField = button.dataset.field;
      state.listProfileValue = button.dataset.value;
      setView("leads");
    });
  });
}

function wireTaskButtons(root) {
  root.querySelectorAll(".save-task-button").forEach((button) => {
    button.addEventListener("click", async () => {
      const task = button.closest(".task-edit-card");
      const content = task?.querySelector(".task-edit-content")?.value.trim() || "";
      const dueDate = task?.querySelector(".task-edit-due")?.value.trim() || "";
      if (!content) return;
      setStatus("Saving task");
      const updated = await postJson("/api/update_task", {
        id: Number(button.dataset.id),
        content,
        due_date: dueDate || null,
      });
      if (updated.detail && detailMatchesCurrent(updated.detail)) renderDetail(updated.detail);
      if (state.view === "followup") renderFollowup();
      if (state.view === "dashboard") renderDashboard();
      if (state.view === "migrationStatus") renderMigrationStatus();
      setStatus("Task saved");
    });
  });

  root.querySelectorAll(".complete-task-button").forEach((button) => {
    button.addEventListener("click", async () => {
      const completed = button.dataset.completed !== "false";
      setStatus(completed ? "Completing task" : "Reopening task");
      const updated = await postJson("/api/complete_task", { id: Number(button.dataset.id), completed });
      if (updated.detail && detailMatchesCurrent(updated.detail)) renderDetail(updated.detail);
      if (state.view === "followup") renderFollowup();
      if (state.view === "dashboard") renderDashboard();
      if (state.view === "migrationStatus") renderMigrationStatus();
      setStatus(completed ? "Task completed" : "Task reopened");
    });
  });

  root.querySelectorAll(".copy-imported-task-button").forEach((button) => {
    button.addEventListener("click", async () => {
      const dueDate = window.prompt("Optional local due date for this copied follow-up (YYYY-MM-DD). Leave blank for no due date.", "");
      if (dueDate === null) return;
      setStatus("Creating local follow-up");
      const updated = await postJson("/api/copy_imported_task_to_local", {
        id: Number(button.dataset.id),
        due_date: dueDate.trim() || null,
      });
      if (updated.detail && detailMatchesCurrent(updated.detail)) renderDetail(updated.detail);
      if (state.view === "followup") renderFollowup();
      if (state.view === "dashboard") renderDashboard();
      if (state.view === "migrationStatus") renderMigrationStatus();
      setStatus("Local follow-up created");
    });
  });
}

function detailMatchesCurrent(detail) {
  return Boolean(
    state.currentDetail &&
      state.currentDetail.type === detail.type &&
      state.currentDetail.record?.source_id === detail.record?.source_id
  );
}

function listTypeForDetailType(type) {
  return {
    person: "people",
    company: "companies",
    lead: "leads",
    deal: "deals",
  }[type] || "";
}

function detailBelongsToCurrentList(detail) {
  return Boolean(detail?.type && state.view === listTypeForDetailType(detail.type));
}

async function refreshCurrentListForDetail(detail) {
  if (!detailBelongsToCurrentList(detail)) return;
  await renderList();
}

function wireCleanupFlagButtons(root) {
  root.querySelectorAll(".cleanup-flag-action").forEach((button) => {
    button.addEventListener("click", async () => {
      const status = button.dataset.status;
      const note = cleanupPromptNote(status, "queue");
      if (note === null) return;
      setStatus(cleanupActionProgress(status));
      await postJson("/api/resolve_flag", {
        id: Number(button.dataset.id),
        status,
        note,
      });
      await renderCleanup();
      if (state.currentCleanupGroup) {
        await showCleanupGroup(state.currentCleanupGroup.type, state.currentCleanupGroup.key);
      }
      setStatus(cleanupActionComplete(status));
    });
  });
}

async function showDetail(type, id) {
  setStatus("Loading details");
  const detail = await fetchJson(`/api/detail?type=${encodeURIComponent(type)}&id=${encodeURIComponent(id)}`);
  if (detail.error) {
    els.detail.innerHTML = `<div class="empty-detail"><h2>${escapeHtml(detail.error)}</h2></div>`;
    return;
  }
  renderDetail(detail);
  setStatus("Ready");
}

async function showArchiveItem(id) {
  setStatus("Loading archive item");
  const detail = await fetchJson(`/api/archive_item?id=${encodeURIComponent(id)}`);
  if (detail.error) {
    els.detail.innerHTML = `<div class="empty-detail"><h2>${escapeHtml(detail.error)}</h2></div>`;
    return;
  }
  renderArchiveItemDetail(detail);
  setStatus("Ready");
}

function renderArchiveItemDetail(detail) {
  const item = detail.item || {};
  state.currentDetail = null;
  state.currentArchiveItem = item;
  const title = item.title || item.label || "Archive Item";
  els.detail.innerHTML = `
    <div class="detail-content">
      ${detailHeader(title, `${item.label || archiveItemLabel(item.item_type)} · Archive #${item.id || ""}`)}
      <div id="detailActionError" class="form-error" hidden></div>
      ${archiveItemSnapshot(item)}
      ${archiveReviewPanel(item)}
      ${archiveItemLinkPanel(item)}
      ${archiveItemFacts(item)}
    </div>
  `;
  wireRecordButtons(els.detail);
  wireArchiveReviewForm(els.detail, item);
  wireArchiveLinkForm(els.detail, item);
}

function archiveItemSnapshot(item) {
  const linked = item.record_type && item.record_id;
  const recordName = item.record_name || (linked ? `${labelize(item.record_type)} #${item.record_id}` : "Unlinked");
  const values = [
    ["Type", item.label || archiveItemLabel(item.item_type)],
    ["When", formatDate(item.occurred_at) || "Unknown"],
    ["Phone", item.phone_number || "None"],
    ["Owner", item.user_name || "None"],
    ["Link", recordName],
  ];
  return `
    <div class="record-snapshot">
      ${values
        .map(([label, value]) => `
          <div class="record-snapshot-item">
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(value)}</strong>
          </div>
        `)
        .join("")}
    </div>
  `;
}

function archiveItemLinkPanel(item) {
  const linked = item.record_type && item.record_id && detailTypeSupported(item.record_type);
  if (linked) {
    const label = item.record_name || `${labelize(item.record_type)} #${item.record_id}`;
    return `
      <div class="detail-section archive-link-panel">
        <div class="inline-header">
          <h3>Linked Record</h3>
          <span class="pill green">Linked</span>
        </div>
        <button class="text-button record-button" data-type="${escapeHtml(item.record_type)}" data-id="${item.record_id}">
          ${escapeHtml(label)}
        </button>
      </div>
    `;
  }
  return `
    <div class="detail-section archive-link-panel">
      <div class="inline-header">
        <h3>Link to Record</h3>
        <span class="pill gold">Manual</span>
      </div>
      <p class="muted detail-note">Attach this item only when you are sure which local record owns it. The app creates a backup and audit entry before linking.</p>
      <div class="archive-target-search">
        <input id="archiveTargetSearch" type="search" placeholder="Search clients, companies, leads, or deals">
        <button class="text-button" id="archiveFindTargetButton" type="button">Find</button>
      </div>
      <div id="archiveTargetResults" class="archive-target-results" aria-live="polite"></div>
      <form id="archiveLinkForm" class="edit-grid archive-link-form">
        <label>
          <span>Record Type</span>
          <select id="archiveLinkRecordType" name="record_type">
            <option value="person">Person</option>
            <option value="company">Company</option>
            <option value="lead">Lead</option>
            <option value="deal">Deal</option>
          </select>
        </label>
        <label>
          <span>Record ID</span>
          <input id="archiveLinkRecordId" name="record_id" type="number" min="1" inputmode="numeric">
        </label>
      </form>
      <button class="text-button" id="linkArchiveItemButton" type="button" data-id="${item.id || ""}">Link Archive Item</button>
    </div>
  `;
}

function archiveReviewPanel(item) {
  const isReviewable = !item.record_id && ["call", "text_message"].includes(item.item_type);
  if (!isReviewable) return "";
  const status = item.review_status || "";
  return `
    <div class="detail-section archive-review-detail-panel">
      <div class="inline-header">
        <h3>Review Status</h3>
        ${status ? `<span class="pill ${status === "archive_only" ? "green" : "gold"}">${escapeHtml(archiveReviewStatusLabel(status))}</span>` : `<span class="pill gold">Unreviewed</span>`}
      </div>
      <form id="archiveReviewForm" class="archive-review-form">
        <label>
          <span>Status</span>
          <select id="archiveReviewStatus" name="status">
            <option value="" ${status ? "" : "selected"}>Choose review status</option>
            <option value="archive_only" ${status === "archive_only" ? "selected" : ""}>Archive-only reviewed</option>
            <option value="needs_lookup" ${status === "needs_lookup" ? "selected" : ""}>Needs lookup</option>
            <option value="ready_to_link" ${status === "ready_to_link" ? "selected" : ""}>Ready to link</option>
          </select>
        </label>
        <label>
          <span>Review Note</span>
          <textarea id="archiveReviewNote" class="note-input" rows="3">${escapeHtml(item.review_note || "")}</textarea>
        </label>
      </form>
      <div class="archive-review-actions">
        <button class="text-button save-archive-review-button" id="saveArchiveReviewButton" type="button" data-id="${item.id || ""}" data-next="false">Save Review</button>
        <button class="text-button save-archive-review-button" id="saveArchiveReviewNextButton" type="button" data-id="${item.id || ""}" data-next="true">Save & Next</button>
      </div>
    </div>
  `;
}

function wireArchiveReviewForm(root, item) {
  root.querySelectorAll(".save-archive-review-button").forEach((button) => {
    button.addEventListener("click", async () => {
      const status = root.querySelector("#archiveReviewStatus")?.value || "";
      const note = root.querySelector("#archiveReviewNote")?.value.trim() || "";
      const openNext = button.dataset.next === "true";
      if (!status) {
        showDetailActionError("Choose a review status before saving.");
        return;
      }
      await runDetailAction(
        button,
        {
          progress: "Saving archive review",
          success: openNext ? "Archive review saved; next item opened" : "Archive review saved",
          failure: "Archive review failed",
        },
        async () => {
          const updated = await postJson("/api/save_archive_review", {
            id: Number(item.id || button.dataset.id),
            status,
            note,
          });
          let refreshed = null;
          if (state.view === "archive") refreshed = await renderArchive();
          if (openNext) {
            const nextId = nextArchiveItemAfterReview(refreshed?.items || state.archiveLastItems, item.id);
            if (nextId) {
              await showArchiveItem(nextId);
              return;
            }
          }
          renderArchiveItemDetail({ item: updated.archive_item });
        }
      );
    });
  });
}

function nextArchiveItemAfterReview(items, currentId) {
  const current = Number(currentId);
  const archiveItems = (items || []).filter((item) => item?.id);
  const currentIndex = archiveItems.findIndex((item) => Number(item.id) === current);
  if (currentIndex >= 0 && currentIndex + 1 < archiveItems.length) {
    return archiveItems[currentIndex + 1].id;
  }
  const fallback = archiveItems.find((item) => Number(item.id) !== current);
  return fallback?.id || null;
}

function archiveItemFacts(item) {
  const externalLink = item.file_url
    ? `<a href="${escapeHtml(item.file_url)}" target="_blank" rel="noreferrer">${escapeHtml(item.title || item.label)}</a>`
    : item.url
      ? `<a href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${escapeHtml(item.title || item.label)}</a>`
      : "";
  const fields = [
    ["Archive ID", item.id],
    ["Zendesk ID", item.zendesk_record_id],
    ["Source", item.source_collection],
    ["Status", item.status],
    ["Direction", item.direction],
    ["Duration", item.duration_seconds ? `${formatNumber(item.duration_seconds)} seconds` : ""],
    ["Size", item.size_label],
    ["Related", item.related_record_type && item.related_record_id ? `${labelize(item.related_record_type)} #${item.related_record_id}` : ""],
    ["Original Resource", item.original_resource_type && item.original_resource_id ? `${labelize(item.original_resource_type)} #${item.original_resource_id}` : ""],
  ].filter(([, value]) => value !== null && value !== undefined && value !== "");
  return `
    <div class="detail-section">
      <h3>Archive Details</h3>
      ${item.body ? `<p>${escapeHtml(item.body)}</p>` : ""}
      ${externalLink ? `<p>${externalLink}</p>` : ""}
      <dl class="kv">
        ${fields
          .map(([label, value]) => `
            <dt>${escapeHtml(label)}</dt>
            <dd>${escapeHtml(value)}</dd>
          `)
          .join("")}
      </dl>
    </div>
  `;
}

function wireArchiveLinkForm(root, item) {
  const findButton = root.querySelector("#archiveFindTargetButton");
  const searchInput = root.querySelector("#archiveTargetSearch");
  const results = root.querySelector("#archiveTargetResults");
  if (findButton && searchInput && results) {
    const runTargetSearch = async () => {
      const query = searchInput.value.trim();
      if (query.length < 2) {
        results.innerHTML = `<div class="muted">Enter at least two characters.</div>`;
        return;
      }
      findButton.disabled = true;
      results.innerHTML = `<div class="muted">Searching...</div>`;
      try {
        const data = await fetchJson(`/api/search?q=${encodeURIComponent(query)}`);
        const targets = (data.results || []).filter((row) => detailTypeSupported(row.type)).slice(0, 8);
        results.innerHTML = targets.length
          ? targets.map(archiveTargetResultButton).join("")
          : `<div class="muted">No matching local records found.</div>`;
        wireArchiveTargetButtons(results);
      } catch (error) {
        results.innerHTML = `<div class="form-error">${escapeHtml(error.message)}</div>`;
      } finally {
        findButton.disabled = false;
      }
    };
    findButton.addEventListener("click", runTargetSearch);
    searchInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        runTargetSearch();
      }
    });
  }

  const linkButton = root.querySelector("#linkArchiveItemButton");
  if (linkButton) {
    linkButton.addEventListener("click", async () => {
      const recordType = root.querySelector("#archiveLinkRecordType")?.value || "";
      const recordId = Number(root.querySelector("#archiveLinkRecordId")?.value || 0);
      if (!recordType || !recordId) {
        showDetailActionError("Choose a target record before linking.");
        return;
      }
      const ok = window.confirm(`Link archive item #${item.id} to ${labelize(recordType)} #${recordId}?`);
      if (!ok) return;
      await runDetailAction(linkButton, { progress: "Linking archive item", success: "Archive item linked", failure: "Archive link failed" }, async () => {
        const updated = await postJson("/api/link_archive_item", {
          id: Number(linkButton.dataset.id),
          record_type: recordType,
          record_id: recordId,
        });
        if (state.view === "archive") await renderArchive();
        renderArchiveItemDetail({ item: updated.archive_item });
      });
    });
  }
}

function archiveTargetResultButton(row) {
  const detail = [labelize(row.type), `#${row.source_id}`, row.email, row.phone, row.match_context].filter(Boolean).join(" · ");
  return `
    <button class="archive-target-button" type="button" data-type="${escapeHtml(row.type)}" data-id="${row.source_id}">
      <strong>${escapeHtml(row.name || `${labelize(row.type)} #${row.source_id}`)}</strong>
      <span>${escapeHtml(detail)}</span>
    </button>
  `;
}

function wireArchiveTargetButtons(root) {
  root.querySelectorAll(".archive-target-button").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelector("#archiveLinkRecordType").value = button.dataset.type || "person";
      document.querySelector("#archiveLinkRecordId").value = button.dataset.id || "";
      root.querySelectorAll(".archive-target-button").forEach((item) => item.classList.remove("selected"));
      button.classList.add("selected");
    });
  });
}

async function showTagDetail(id) {
  setStatus("Loading tag");
  const params = new URLSearchParams({
    id: String(id),
    page_size: "100",
    record_type: state.tagRecordType,
  });
  const detail = await fetchJson(`/api/tags?${params.toString()}`);
  if (detail.error) {
    els.detail.innerHTML = `<div class="empty-detail"><h2>${escapeHtml(detail.error)}</h2></div>`;
    return;
  }
  renderTagDetail(detail);
  setStatus("Ready");
}

async function showCustomFieldDetail(recordType, fieldName) {
  setStatus("Loading custom field");
  const params = new URLSearchParams({
    record_type: recordType,
    field_name: fieldName,
    page_size: "100",
  });
  const detail = await fetchJson(`/api/custom_fields?${params.toString()}`);
  if (detail.error) {
    els.detail.innerHTML = `<div class="empty-detail"><h2>${escapeHtml(detail.error)}</h2></div>`;
    return;
  }
  renderCustomFieldDetail(detail);
  setStatus("Ready");
}

async function showCleanupGroup(type, key) {
  setStatus("Loading cleanup group");
  const params = new URLSearchParams({ type, key, status: state.cleanupStatus });
  const detail = await fetchJson(`/api/cleanup_groups?${params.toString()}`);
  if (detail.error) {
    els.detail.innerHTML = `<div class="empty-detail"><h2>${escapeHtml(detail.error)}</h2></div>`;
    return;
  }
  renderCleanupGroupDetail(detail);
  setStatus("Ready");
}

async function nextCleanupReviewGroup(detail) {
  const params = new URLSearchParams({
    type: detail.type,
    status: detail.status || "open",
    decision: "review_remaining",
    sort: "policy",
    page: "1",
    page_size: "50",
  });
  if (detail.type === "lead_person_overlap") params.set("policy_lane", "policy_review_overlap");
  const data = await fetchJson(`/api/cleanup_groups?${params.toString()}`);
  const nextGroup = (data.groups || []).find((group) => group.group_key !== detail.group_key);
  return nextGroup ? { type: data.type, key: nextGroup.group_key } : null;
}

function renderDetail(detail) {
  state.currentDetail = detail;
  state.currentArchiveItem = null;
  state.currentCleanupGroup = null;
  const record = detail.record;
  const subtitle = [record.email, record.phone, record.mobile, record.stage_name].filter(Boolean).join(" · ");
  els.detail.innerHTML = `
    <div class="detail-content">
      ${detailHeader(record.name || "(blank)", subtitle || detail.type)}
      <div id="detailActionError" class="form-error" hidden></div>
      ${recordSnapshot(detail)}
      ${detailQualityPanel(detail)}
      ${contactActions(detail)}
      ${editForm(detail)}
      ${reviewFlagsSection(detail.review_flags || [])}
      ${ownerSection(detail.owner)}
      ${addressSection(detail)}
      ${detailTags(detail.tags || [])}
      ${applicationProfile(detail.application_profile || [])}
      ${keyValues(record)}
      ${detail.company ? linkSection("Company", [detail.company], "company") : ""}
      ${detail.possible_person ? linkSection("Possible Match", [detail.possible_person], "person") : ""}
      ${detail.contact ? linkSection("Contact", [detail.contact], "person") : ""}
      ${detail.organization ? linkSection("Organization", [detail.organization], "company") : ""}
      ${detail.people?.length ? linkSection("People", detail.people, "person") : ""}
      ${detail.deals?.length ? linkSection("Deals", detail.deals, "deal") : ""}
      ${linkedResources(detail.linked_resources || [])}
      ${archiveItems(detail.archive_items || [])}
      ${customFields(detail.custom_fields || [], detail.application_profile || [])}
      ${activitySection(detail.activity || [])}
      ${addNoteForm(detail)}
      ${notesSection(detail.notes || [])}
      ${addTaskForm(detail)}
      ${tasksSection(detail.tasks || [])}
    </div>
  `;
  wireRecordButtons(els.detail);
  wireDetailForms(detail);
  syncActiveListRows();
}

function detailHeader(title, subtitle) {
  return `
    <div class="detail-masthead">
      <h2 class="detail-title">${escapeHtml(title || "")}</h2>
      <div class="detail-subtitle">${escapeHtml(subtitle || "")}</div>
    </div>
  `;
}

function recordSnapshot(detail) {
  const record = detail.record || {};
  const provenance = detail.provenance || {};
  const status = recordSnapshotStatus(detail);
  const openTasks = (detail.tasks || []).filter((task) => !task.completed).length;
  const reviewFlags = (detail.review_flags || []).length;
  const tags = (detail.tags || []).length;
  const links = (detail.linked_resources || []).length;
  const archiveItems = (detail.archive_items || []).length;
  const owner = detail.owner?.name || record.owner_name || "";
  const updated = record.updated_at ? formatDate(record.updated_at) : "";
  const localChanges = Number(provenance.local_change_count || 0);
  const lastLocalChange = provenance.last_local_change_at ? formatDate(provenance.last_local_change_at) : "";
  const items = [
    ["Type", labelize(detail.type || "record")],
    provenance.label ? ["Source", provenance.label] : null,
    status ? ["Status", status] : null,
    owner ? ["Owner", owner] : null,
    updated ? ["Updated", updated] : null,
    localChanges ? ["Local Changes", formatNumber(localChanges)] : null,
    lastLocalChange ? ["Last Local", lastLocalChange] : null,
    openTasks ? ["Open Tasks", formatNumber(openTasks)] : null,
    reviewFlags ? ["Review Flags", formatNumber(reviewFlags)] : null,
    tags ? ["Tags", formatNumber(tags)] : null,
    links ? ["Links", formatNumber(links)] : null,
    archiveItems ? ["Archive", formatNumber(archiveItems)] : null,
  ].filter(Boolean);
  if (!items.length) return "";
  return `
    <div class="record-snapshot" aria-label="Record snapshot">
      ${items
        .map(
          ([label, value]) => `
            <div class="record-snapshot-item">
              <span>${escapeHtml(label)}</span>
              <strong>${escapeHtml(value)}</strong>
            </div>
          `
        )
        .join("")}
    </div>
  `;
}

function recordSnapshotStatus(detail) {
  const record = detail.record || {};
  if (record.stage_name) return record.stage_name;
  if (record.status) return record.status;
  const statuses = [record.customer_status, record.prospect_status].filter(Boolean);
  if (!statuses.length) return "";
  return [...new Set(statuses)].join(" / ");
}

function detailQualityPanel(detail) {
  const issues = detail.record?.quality_issues || [];
  if (!issues.length) return "";
  return `
    <div class="detail-section data-quality-detail">
      <div class="inline-header">
        <h3>Data Quality</h3>
        ${qualityIssueChips(issues)}
      </div>
      <div class="quality-guidance-list">
        ${issues
          .map(
            (issue) => `
              <div class="quality-guidance-row">
                <strong>${escapeHtml(issue.label || labelize(issue.issue || ""))}</strong>
                <span>${escapeHtml(qualityGuidanceText(issue.issue))}</span>
              </div>
            `
          )
          .join("")}
      </div>
    </div>
  `;
}

function qualityGuidanceText(issue) {
  const guidance = {
    missing_contact: "Email, phone, or mobile needed.",
    missing_email: "Email needed when known.",
    missing_phone: "Phone or mobile needed when known.",
    missing_owner: "Owner needed when known.",
    missing_value: "Deal value needed when known.",
    missing_stage: "Deal stage needed when known.",
    missing_relationship: "Contact or company link needed when known.",
  };
  return guidance[issue] || "Review when known.";
}

function contactActions(detail) {
  const sources = [{ prefix: "", record: detail.record || {} }];
  if (detail.type === "deal") {
    if (detail.contact) sources.push({ prefix: "Contact", record: detail.contact });
    if (detail.organization) sources.push({ prefix: "Organization", record: detail.organization });
  }
  const rows = [];
  const seen = new Set();
  const addRow = (source, key, label, value, href, actionLabel) => {
    const text = String(value || "").trim();
    if (!text) return;
    const identity = `${key}:${text.toLowerCase()}`;
    if (seen.has(identity)) return;
    seen.add(identity);
    rows.push({
      label: source.prefix ? `${source.prefix} ${label}` : label,
      value: text,
      href,
      actionLabel,
    });
  };
  sources.forEach((source) => {
    addRow(source, "email", "Email", source.record.email, contactEmailHref(source.record.email), "Mail");
    addRow(source, "phone", "Phone", source.record.phone, contactPhoneHref(source.record.phone), "Call");
    addRow(source, "mobile", "Mobile", source.record.mobile, contactPhoneHref(source.record.mobile), "Call");
    addRow(source, "website", "Website", source.record.website, contactWebsiteHref(source.record.website), "Open");
  });
  if (!rows.length) return "";
  return `
    <div class="detail-section contact-actions">
      <h3>Contact Actions</h3>
      <div class="contact-action-list">
        ${rows
          .map((row) => `
            <div class="contact-action-row">
              <div>
                <strong>${escapeHtml(row.label)}</strong>
                <span>${escapeHtml(row.value)}</span>
              </div>
              <div class="contact-action-buttons">
                ${row.href ? `<a class="text-button action-link" href="${escapeHtml(row.href)}">${escapeHtml(row.actionLabel)}</a>` : ""}
                <button class="text-button contact-copy-button" type="button" data-copy-label="${escapeHtml(row.label)}" data-copy-value="${escapeHtml(row.value)}">Copy</button>
              </div>
            </div>
          `)
          .join("")}
      </div>
    </div>
  `;
}

function contactEmailHref(value) {
  const text = String(value || "").trim();
  return text ? `mailto:${encodeURIComponent(text)}` : "";
}

function contactPhoneHref(value) {
  const text = String(value || "").trim();
  const phone = text.replace(/[^\d+]/g, "");
  return phone ? `tel:${phone}` : "";
}

function contactWebsiteHref(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  if (/^https?:\/\//i.test(text)) return text;
  return `https://${text}`;
}

function renderTagDetail(detail) {
  state.currentDetail = null;
  state.currentCleanupGroup = null;
  const tag = detail.tag;
  const detailRecordType = detail.record_type ? labelize(detail.record_type) : "";
  els.detail.innerHTML = `
    <div class="detail-content">
      ${detailHeader(tag.display_name || "(blank tag)", `${formatNumber(detail.total)} assigned ${detailRecordType ? detailRecordType.toLowerCase() : "records"}`)}
      <div class="detail-section">
        <h3>Tag</h3>
        <dl class="kv">
          <dt>Definitions</dt>
          <dd>${formatNumber(tag.definition_count)}</dd>
          <dt>Normalized</dt>
          <dd>${escapeHtml(tag.normalized_name || "")}</dd>
        </dl>
      </div>
      <div class="detail-section">
        <h3>Records</h3>
        <div class="mini-list tag-record-list">
          ${
            detail.records.length
              ? detail.records
                  .map((record) => `
                    <button class="text-button record-button" data-type="${escapeHtml(record.record_type)}" data-id="${record.source_id}">
                      ${escapeHtml(record.name || `${labelize(record.record_type)} #${record.source_id}`)}
                      <span>${escapeHtml(record.secondary || labelize(record.record_type))}</span>
                    </button>
                  `)
                  .join("")
              : `<div class="empty-state"><h3>No records</h3><p>This tag is not assigned to a record.</p></div>`
          }
        </div>
        ${detail.total > detail.records.length ? `<p class="muted">Showing first ${formatNumber(detail.records.length)} records.</p>` : ""}
      </div>
    </div>
  `;
  wireRecordButtons(els.detail);
}

function renderCustomFieldDetail(detail) {
  state.currentDetail = null;
  state.currentCleanupGroup = null;
  const field = detail.field;
  els.detail.innerHTML = `
    <div class="detail-content">
      ${detailHeader(field.field_name || "(blank field)", `${labelize(field.record_type || "record")} custom field`)}
      <div class="cleanup-detail-signals">
        <div class="signal"><strong>${formatNumber(field.record_count)}</strong><span>Records</span></div>
        <div class="signal"><strong>${formatNumber(field.value_count)}</strong><span>Values</span></div>
        <div class="signal"><strong>${formatNumber(field.distinct_values)}</strong><span>Unique</span></div>
      </div>
      <div class="detail-section">
        <h3>Samples</h3>
        ${sampleValues(field.sample_values || [])}
      </div>
      <div class="detail-section">
        <h3>Records</h3>
        <div class="custom-field-record-list">
          ${detail.records
            .map((record) => `
              <div class="custom-field-record">
                <button class="record-button" data-type="${escapeHtml(record.record_type)}" data-id="${record.source_id}">
                  ${escapeHtml(record.name || `${labelize(record.record_type)} #${record.source_id}`)}
                </button>
                <div class="muted">${escapeHtml(record.secondary || "")}</div>
                <p>${escapeHtml(record.field_value || "Not saved")}</p>
              </div>
            `)
            .join("")}
        </div>
        ${detail.total > detail.records.length ? `<p class="muted">Showing first ${formatNumber(detail.records.length)} records.</p>` : ""}
      </div>
    </div>
  `;
  wireRecordButtons(els.detail);
}

function renderCleanupGroupDetail(detail) {
  state.currentDetail = null;
  state.currentCleanupGroup = { type: detail.type, key: detail.group_key };
  const isTagGroup = detail.type === "duplicate_tags";
  const detailTitle = isTagGroup ? detail.counts?.display_name || detail.group_key : detail.group_key;
  const detailSubtitle = isTagGroup
    ? `${detail.label} · ${formatNumber(detail.counts?.definition_count || 0)} definitions · ${formatNumber(detail.flags.length)} ${cleanupStatusLabel(detail.status).toLowerCase()} flags`
    : `${detail.label} · ${formatNumber(detail.flags.length)} ${cleanupStatusLabel(detail.status).toLowerCase()} flags`;
  els.detail.innerHTML = `
    <div class="detail-content">
      ${detailHeader(detailTitle || "(blank group)", detailSubtitle)}
      <div class="cleanup-detail-signals">
        ${
          isTagGroup
            ? `
              <div class="signal"><strong>${formatNumber(detail.counts.record_count)}</strong><span>Assigned records</span></div>
              <div class="signal"><strong>${formatNumber(detail.counts.definition_count)}</strong><span>Definitions</span></div>
              <div class="signal"><strong>${escapeHtml(detail.counts.resource_types || "None")}</strong><span>Record types</span></div>
            `
            : `
              <div class="signal"><strong>${formatNumber(detail.counts.record_count)}</strong><span>Total records</span></div>
              <div class="signal"><strong>${formatNumber(detail.counts.people_count)}</strong><span>People</span></div>
              <div class="signal"><strong>${formatNumber(detail.counts.lead_count)}</strong><span>Leads</span></div>
            `
        }
        <div class="signal"><strong>${escapeHtml(detail.guidance?.priority || "Review")}</strong><span>Priority</span></div>
      </div>
      <div class="detail-section cleanup-guidance">
        <div class="inline-header">
          <h3>${escapeHtml(detail.guidance?.headline || "Review Guidance")}</h3>
          ${cleanupPriorityPill(detail.guidance?.priority)}
        </div>
        <p>${escapeHtml(detail.guidance?.action || "Review the related records before resolving.")}</p>
        <div class="cleanup-guidance-list">
          ${(detail.guidance?.reasons || []).map((reason) => `<span>${escapeHtml(reason)}</span>`).join("")}
        </div>
      </div>
      ${cleanupDecisionSection(detail)}
      ${cleanupMergeDraft(detail.merge_draft)}
      ${
        isTagGroup
          ? `<div class="detail-section">
              <h3>Tag Definitions</h3>
              <div class="cleanup-field-list">
                ${(detail.aliases || [])
                  .map((alias) => `
                    <div class="cleanup-field-diff">
                      <div class="cleanup-field-header">
                        <strong>${escapeHtml(alias.source_name || "(blank tag)")}</strong>
                        <span class="muted">${escapeHtml(alias.resource_type || "unknown")}</span>
                      </div>
                      <div class="muted">Zendesk tag #${escapeHtml(alias.zendesk_tag_id || "")}</div>
                    </div>
                  `)
                  .join("")}
              </div>
            </div>`
          : ""
      }
      <div class="detail-section">
        <h3>${isTagGroup ? "Assigned Records" : "Records"}</h3>
        <div class="cleanup-record-list">
          ${detail.records
            .map((record) => `
              <div class="cleanup-record">
                <div>
                  <div class="cleanup-record-title">
                    <button class="record-button" data-type="${escapeHtml(record.record_type)}" data-id="${record.source_id}">
                      ${escapeHtml(record.name || `${labelize(record.record_type)} #${record.source_id}`)}
                    </button>
                    ${(record.badges || []).map((badge) => `<span class="pill">${escapeHtml(badge)}</span>`).join("")}
                  </div>
                  <div class="muted">${escapeHtml([record.email, record.phone || record.mobile, record.detail].filter(Boolean).join(" · "))}</div>
                  ${cleanupProfileSummary(record.profile_summary || [])}
                  ${cleanupRecordStats(record)}
                </div>
                <span class="pill ${record.role === "Primary" ? "" : "gold"}">${escapeHtml(record.role || "Related")}</span>
              </div>
            `)
            .join("")}
        </div>
        ${detail.counts.record_count > detail.records.length ? `<p class="muted">Showing first ${formatNumber(detail.records.length)} records.</p>` : ""}
      </div>
      ${cleanupFieldComparison(detail.field_comparison || [])}
      <div class="detail-section">
        <div class="inline-header">
          <h3>${cleanupStatusLabel(detail.status)} Flags</h3>
          ${detail.flags.length ? cleanupGroupActions(detail.status) : ""}
        </div>
        ${
          detail.flags.length
            ? detail.flags
                .map((flag) => `
                  <div class="review-flag">
                    <div>
                      <strong>${escapeHtml(labelize(flag.flag_type))}</strong>
                      <p>${escapeHtml(flag.description)}</p>
                      ${cleanupResolutionNote(flag)}
                    </div>
                    ${cleanupFlagActions(flag)}
                  </div>
                `)
                .join("")
            : `<div class="muted">No ${cleanupStatusLabel(detail.status).toLowerCase()} flags for this group.</div>`
        }
      </div>
    </div>
  `;
  wireRecordButtons(els.detail);
  wireCleanupFlagButtons(els.detail);
  const saveCleanupDecision = async (openNext = false) => {
    const decision = document.querySelector("#cleanupDecisionSelect").value;
    const note = document.querySelector("#cleanupDecisionNote").value.trim();
    setStatus(openNext ? "Saving and opening next" : "Saving cleanup decision");
    const saved = await postJson("/api/save_cleanup_decision", {
      type: detail.type,
      key: detail.group_key,
      status: detail.status,
      decision,
      note,
    });
    const nextGroup = openNext ? await nextCleanupReviewGroup(detail) : null;
    state.cleanupGroupType = detail.type;
    state.cleanupStatus = detail.status;
    state.cleanupDecision = openNext ? "review_remaining" : state.cleanupDecision;
    state.cleanupSort = openNext ? "policy" : state.cleanupSort;
    if (openNext && detail.type === "lead_person_overlap") state.cleanupPolicyLane = "policy_review_overlap";
    if (openNext && detail.type !== "lead_person_overlap") state.cleanupPolicyLane = "";
    if (openNext) {
      state.cleanupPriority = "";
      state.cleanupGroupQ = "";
      state.cleanupGroupPage = 1;
    }
    await renderCleanup();
    if (nextGroup) {
      await showCleanupGroup(nextGroup.type, nextGroup.key);
      setStatus("Cleanup decision saved; next group opened");
    } else {
      renderCleanupGroupDetail(saved.detail);
      setStatus(openNext ? "Cleanup decision saved; no next group found" : "Cleanup decision saved");
    }
  };
  document.querySelector("#saveCleanupDecisionButton")?.addEventListener("click", () => saveCleanupDecision(false));
  document.querySelector("#saveCleanupDecisionNextButton")?.addEventListener("click", () => saveCleanupDecision(true));
  document.querySelectorAll(".cleanup-group-status-button").forEach((button) => {
    button.addEventListener("click", async () => {
      const nextStatus = button.dataset.status;
      const ok = window.confirm(`Mark ${detail.flags.length} ${cleanupStatusLabel(detail.status).toLowerCase()} cleanup flags ${cleanupStatusLabel(nextStatus).toLowerCase()} for ${detailTitle}? This does not merge records.`);
      if (!ok) return;
      const note = cleanupPromptNote(nextStatus, "group", detailTitle);
      if (note === null) return;
      setStatus(cleanupActionProgress(nextStatus));
      for (const flag of detail.flags) {
        await postJson("/api/resolve_flag", { id: flag.id, status: nextStatus, note });
      }
      await renderCleanup();
      await showCleanupGroup(detail.type, detail.group_key);
      setStatus(cleanupActionComplete(nextStatus));
    });
  });
}

function editForm(detail) {
  const record = detail.record;
  const fields = editableFields(detail.type);
  if (!fields.length) return "";
  return `
    <div class="detail-section">
      <div class="inline-header">
        <h3>Edit</h3>
        <button class="text-button" id="saveRecordButton">Save</button>
      </div>
      <form id="editRecordForm" class="edit-grid">
        ${fields.map((field) => editFieldControl(detail, field)).join("")}
      </form>
      <div id="detailFormError" class="form-error" hidden></div>
    </div>
  `;
}

function editableFields(type) {
  if (type === "person") return ["name", "first_name", "last_name", "email", "phone", "mobile", "company_id", "title", "owner_user_id", "customer_status", "prospect_status"];
  if (type === "company") return ["name", "email", "phone", "website", "owner_user_id", "customer_status", "prospect_status"];
  if (type === "lead") return ["name", "first_name", "last_name", "organization_name", "email", "phone", "mobile", "status", "owner_user_id"];
  if (type === "deal") return ["name", "person_id", "company_id", "stage_id", "value", "currency", "hot", "estimated_close_date"];
  return [];
}

function editFieldControl(detail, field) {
  const record = detail.record || {};
  const value = record[field] ?? "";
  const label = editFieldLabel(field);
  if (field === "owner_user_id") {
    return `
      <label>
        <span>${escapeHtml(label)}</span>
        <select name="${field}">
          <option value="">No owner</option>
          ${editOptions(detail, "owners", value)}
        </select>
      </label>
    `;
  }
  if (field === "stage_id") {
    return `
      <label>
        <span>${escapeHtml(label)}</span>
        <select name="${field}">
          <option value="">No stage</option>
          ${editOptions(detail, "stages", value)}
        </select>
      </label>
    `;
  }
  if (field === "hot") {
    return `
      <label class="checkbox-field">
        <span>${escapeHtml(label)}</span>
        <input type="hidden" name="hot" value="0">
        <input name="hot" type="checkbox" value="1" ${Number(value || 0) ? "checked" : ""}>
      </label>
    `;
  }
  if (["person_id", "company_id"].includes(field)) {
    const optionKey = field === "person_id" ? "people" : "companies";
    const listId = `${detail.type}-${field}-options`;
    const current = linkedRecordHint(detail, field);
    return `
      <label>
        <span>${escapeHtml(label)}</span>
        <input name="${escapeHtml(field)}" type="number" list="${escapeHtml(listId)}" value="${escapeHtml(value)}">
        ${relationshipDatalist(detail, optionKey, listId)}
        <small class="muted">${escapeHtml(current || "Choose from suggestions or enter an ID.")}</small>
      </label>
    `;
  }
  const type = field === "value" ? "number" : field.endsWith("_date") ? "date" : ["person_id", "company_id"].includes(field) ? "number" : "text";
  const step = field === "value" ? ` step="0.01"` : "";
  const current = linkedRecordHint(detail, field);
  return `
    <label>
      <span>${escapeHtml(label)}</span>
      <input name="${escapeHtml(field)}" type="${type}"${step} value="${escapeHtml(field.endsWith("_date") ? taskDateInputValue(value) : value)}">
      ${current ? `<small class="muted">${escapeHtml(current)}</small>` : ""}
    </label>
  `;
}

function editOptions(detail, key, selectedValue) {
  return (detail.edit_options?.[key] || [])
    .map((option) => {
      const value = String(option.value ?? "");
      const label = optionDisplayLabel(option);
      return `<option value="${escapeHtml(value)}" ${String(selectedValue ?? "") === value ? "selected" : ""}>${escapeHtml(label)}</option>`;
    })
    .join("");
}

function relationshipDatalist(detail, key, listId) {
  const options = detail.edit_options?.[key] || [];
  if (!options.length) return "";
  return `
    <datalist id="${escapeHtml(listId)}">
      ${options
        .map((option) => `<option value="${escapeHtml(String(option.value ?? ""))}" label="${escapeHtml(optionDisplayLabel(option))}"></option>`)
        .join("")}
    </datalist>
  `;
}

function optionDisplayLabel(option) {
  const detail = [option.email, option.phone].filter(Boolean).join(" · ");
  if (option.pipeline_name) return `${option.pipeline_name} · ${option.label}`;
  return detail ? `${option.label} · ${detail}` : option.label;
}

function editFieldLabel(field) {
  return {
    owner_user_id: "Owner",
    person_id: "Contact ID",
    company_id: "Organization ID",
    stage_id: "Stage",
    hot: "Hot Deal",
  }[field] || labelize(field);
}

function linkedRecordHint(detail, field) {
  if (field === "person_id" && detail.contact) return `Current contact: ${detail.contact.name || `#${detail.contact.source_id}`}`;
  if (field === "company_id") {
    if (detail.organization) return `Current organization: ${detail.organization.name || `#${detail.organization.source_id}`}`;
    if (detail.company) return `Current company: ${detail.company.name || `#${detail.company.source_id}`}`;
  }
  return "";
}

function detailTypeSupported(type) {
  return ["person", "company", "lead", "deal"].includes(type);
}

function reviewFlagsSection(flags) {
  if (!flags.length) return "";
  return `
    <div class="detail-section">
      <h3>Review Flags</h3>
      ${flags
        .map((flag) => `
          <div class="review-flag">
            <div>
              <strong>${escapeHtml(labelize(flag.flag_type))}</strong>
              <p>${escapeHtml(flag.description)}</p>
              ${cleanupResolutionNote(flag)}
            </div>
            <button class="text-button resolve-flag-button" data-id="${flag.id || ""}">Resolve</button>
          </div>
        `)
        .join("")}
    </div>
  `;
}

function addNoteForm(detail) {
  if (!["person", "company", "lead", "deal"].includes(detail.type)) return "";
  return `
    <div class="detail-section">
      <div class="inline-header">
        <h3>Add Note</h3>
        <button class="text-button" id="addNoteButton">Add</button>
      </div>
      <textarea id="noteContent" class="note-input" rows="4"></textarea>
    </div>
  `;
}

function addTaskForm(detail) {
  if (!["person", "company", "lead", "deal"].includes(detail.type)) return "";
  return `
    <div class="detail-section">
      <div class="inline-header">
        <h3>Add Task</h3>
        <button class="text-button" id="addTaskButton">Add</button>
      </div>
      <form id="taskForm" class="task-form">
        <textarea name="content" class="note-input" rows="3"></textarea>
        <input name="due_date" type="date">
      </form>
    </div>
  `;
}

function wireDetailForms(detail) {
  document.querySelectorAll(".contact-copy-button").forEach((button) => {
    button.addEventListener("click", async () => {
      const label = button.dataset.copyLabel || "Value";
      await runDetailAction(button, { progress: "Copying", success: `${label} copied`, failure: "Copy failed" }, async () => {
        await copyTextToClipboard(button.dataset.copyValue || "");
      });
    });
  });

  const saveButton = document.querySelector("#saveRecordButton");
  if (saveButton) {
    saveButton.addEventListener("click", async () => {
      const form = document.querySelector("#editRecordForm");
      const fields = {};
      new FormData(form).forEach((value, key) => {
        fields[key] = value.toString().trim() || null;
      });
      clearDetailFormError();
      saveButton.disabled = true;
      try {
        setStatus("Saving");
        const updated = await postJson("/api/update_record", {
          type: detail.type,
          id: detail.record.source_id,
          fields,
        });
        renderDetail(updated.detail);
        if (state.view === "dashboard") await renderDashboard();
        await refreshCurrentListForDetail(updated.detail);
        setStatus("Saved");
      } catch (error) {
        showDetailFormError(error.message);
        setStatus("Save failed");
      } finally {
        saveButton.disabled = false;
      }
    });
  }

  const addressButton = document.querySelector("#saveAddressesButton");
  if (addressButton) {
    addressButton.addEventListener("click", async () => {
      const addresses = Array.from(document.querySelectorAll("#addressForm .address-card")).map((card) => {
        const address = { address_key: card.dataset.addressKey };
        card.querySelectorAll("input[data-field]").forEach((input) => {
          address[input.dataset.field] = input.value.trim() || null;
        });
        return address;
      });
      await runDetailAction(addressButton, { progress: "Saving address", success: "Address saved", failure: "Address save failed" }, async () => {
        const updated = await postJson("/api/update_addresses", {
          type: detail.type,
          id: detail.record.source_id,
          addresses,
        });
        renderDetail(updated.detail);
        if (state.view === "dashboard") await renderDashboard();
        await refreshCurrentListForDetail(updated.detail);
      });
    });
  }

  const tagsButton = document.querySelector("#saveTagsButton");
  if (tagsButton) {
    tagsButton.addEventListener("click", async () => {
      const editor = document.querySelector("#tagEditor");
      await runDetailAction(tagsButton, { progress: "Saving tags", success: "Tags saved", failure: "Tag save failed" }, async () => {
        const updated = await postJson("/api/update_tags", {
          type: detail.type,
          id: detail.record.source_id,
          tags: editor.value,
        });
        renderDetail(updated.detail);
        if (state.view === "dashboard") await renderDashboard();
        if (state.view === "tags") await renderTags();
        if (state.view === "cleanup") await renderCleanup();
        await refreshCurrentListForDetail(updated.detail);
      });
    });
  }

  const noteButton = document.querySelector("#addNoteButton");
  if (noteButton) {
    noteButton.addEventListener("click", async () => {
      const textarea = document.querySelector("#noteContent");
      const content = textarea.value.trim();
      if (!content) return;
      await runDetailAction(noteButton, { progress: "Adding note", success: "Note added", failure: "Note add failed" }, async () => {
        const updated = await postJson("/api/add_note", {
          type: detail.type,
          id: detail.record.source_id,
          content,
        });
        renderDetail(updated.detail);
      });
    });
  }

  document.querySelectorAll(".save-note-button").forEach((button) => {
    button.addEventListener("click", async () => {
      const note = button.closest(".note");
      const textarea = note?.querySelector(".note-edit-input");
      const content = textarea?.value.trim() || "";
      if (!content) return;
      await runDetailAction(button, { progress: "Saving note", success: "Note saved", failure: "Note save failed" }, async () => {
        const updated = await postJson("/api/update_note", {
          id: Number(button.dataset.id),
          content,
        });
        renderDetail(updated.detail);
        if (state.view === "dashboard") renderDashboard();
        if (state.view === "activity") renderActivity();
      });
    });
  });

  const taskButton = document.querySelector("#addTaskButton");
  if (taskButton) {
    taskButton.addEventListener("click", async () => {
      const form = document.querySelector("#taskForm");
      const formData = new FormData(form);
      const content = String(formData.get("content") || "").trim();
      const dueDate = String(formData.get("due_date") || "").trim();
      if (!content) return;
      await runDetailAction(taskButton, { progress: "Adding task", success: "Task added", failure: "Task add failed" }, async () => {
        const updated = await postJson("/api/add_task", {
          type: detail.type,
          id: detail.record.source_id,
          content,
          due_date: dueDate || null,
        });
        renderDetail(updated.detail);
      });
    });
  }

  document.querySelectorAll(".save-task-button").forEach((button) => {
    button.addEventListener("click", async () => {
      const task = button.closest(".task-edit-card");
      const content = task?.querySelector(".task-edit-content")?.value.trim() || "";
      const dueDate = task?.querySelector(".task-edit-due")?.value.trim() || "";
      if (!content) return;
      await runDetailAction(button, { progress: "Saving task", success: "Task saved", failure: "Task save failed" }, async () => {
        const updated = await postJson("/api/update_task", {
          id: Number(button.dataset.id),
          content,
          due_date: dueDate || null,
        });
        if (updated.detail) renderDetail(updated.detail);
        if (state.view === "followup") renderFollowup();
        if (state.view === "dashboard") renderDashboard();
      });
    });
  });

  document.querySelectorAll(".complete-task-button").forEach((button) => {
    button.addEventListener("click", async () => {
      const completed = button.dataset.completed !== "false";
      await runDetailAction(
        button,
        {
          progress: completed ? "Completing task" : "Reopening task",
          success: completed ? "Task completed" : "Task reopened",
          failure: completed ? "Task completion failed" : "Task reopen failed",
        },
        async () => {
          const updated = await postJson("/api/complete_task", { id: Number(button.dataset.id), completed });
          if (updated.detail) renderDetail(updated.detail);
        }
      );
    });
  });

  document.querySelectorAll(".resolve-flag-button").forEach((button) => {
    button.addEventListener("click", async () => {
      const flagId = Number(button.dataset.id);
      if (!flagId) return;
      const note = cleanupPromptNote("resolved", "record");
      if (note === null) return;
      await runDetailAction(button, { progress: "Resolving flag", success: "Flag resolved", failure: "Flag resolve failed" }, async () => {
        await postJson("/api/resolve_flag", { id: flagId, status: "resolved", note });
        const refreshed = await fetchJson(`/api/detail?type=${encodeURIComponent(detail.type)}&id=${encodeURIComponent(detail.record.source_id)}`);
        renderDetail(refreshed);
        if (state.view === "cleanup") renderCleanup();
      });
    });
  });
}

async function renderFollowup() {
  setStatus("Loading follow up");
  const params = new URLSearchParams({
    status: state.taskStatus,
    q: state.taskQ,
    record_type: state.taskRecordType,
    source: state.taskSource,
    sort: state.taskSort,
    direction: state.taskDirection,
    page: String(state.taskPage),
    page_size: "50",
  });
  const exportParams = new URLSearchParams({
    type: "tasks",
    status: state.taskStatus,
    q: state.taskQ,
    record_type: state.taskRecordType,
    source: state.taskSource,
    sort: state.taskSort,
    direction: state.taskDirection,
  });
  const [data, savedViewData] = await Promise.all([
    fetchJson(`/api/tasks?${params.toString()}`),
    fetchJson("/api/saved_views?type=tasks"),
  ]);
  const savedViews = savedViewData.views || [];
  if (state.taskSavedViewId && !savedViews.some((view) => String(view.id) === String(state.taskSavedViewId))) {
    state.taskSavedViewId = "";
  }
  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));
  const sourceCounts = data.source_counts || {};
  els.followup.innerHTML = `
    <div class="section-header">
      <div>
        <h2>Follow Up</h2>
        <p>${formatNumber(data.total)} ${escapeHtml(statusLabel(state.taskStatus).toLowerCase())} · ${formatNumber(sourceCounts.imported || 0)} imported · ${formatNumber(sourceCounts.local || 0)} local</p>
      </div>
    </div>
    <div class="segmented">
      ${["open", "overdue", "due_soon", "completed", "all"]
        .map((status) => `<button class="segment-button ${state.taskStatus === status ? "active" : ""}" data-status="${status}">${escapeHtml(statusLabel(status))}</button>`)
        .join("")}
    </div>
    ${followupTransitionPanel(data.transition_plan)}
    <div class="table-tools">
      <div class="filter-row">
        <input id="taskSearch" type="search" value="${escapeHtml(state.taskQ)}" placeholder="Filter tasks or records">
        <select id="taskRecordType" aria-label="Filter follow-up tasks by related record type">
          ${taskRecordTypeOptions()
            .map(([value, label]) => `<option value="${escapeHtml(value)}" ${state.taskRecordType === value ? "selected" : ""}>${escapeHtml(label)}</option>`)
            .join("")}
        </select>
        <select id="taskSource" aria-label="Filter follow-up tasks by source">
          ${taskSourceOptions()
            .map(([value, label]) => `<option value="${escapeHtml(value)}" ${state.taskSource === value ? "selected" : ""}>${escapeHtml(label)}</option>`)
            .join("")}
        </select>
        <div class="sort-control-group" aria-label="Task sorting">
          <span class="tool-label">Sort</span>
          <select id="taskSortField" aria-label="Sort follow-up tasks by field">
            ${taskSortOptions()
              .map(([field, label]) => `<option value="${escapeHtml(field)}" ${state.taskSort === field ? "selected" : ""}>${escapeHtml(label)}</option>`)
              .join("")}
          </select>
          <select id="taskSortDirection" aria-label="Sort follow-up tasks direction">
            <option value="asc" ${state.taskDirection === "asc" ? "selected" : ""}>Ascending</option>
            <option value="desc" ${state.taskDirection === "desc" ? "selected" : ""}>Descending</option>
          </select>
        </div>
        ${taskSavedViewControls(savedViews)}
      </div>
      <div class="pager">
        <button class="icon-button" id="prevTaskPage" title="Previous page" ${state.taskPage <= 1 ? "disabled" : ""}>‹</button>
        <span class="muted">Page ${state.taskPage} of ${totalPages}</span>
        <button class="icon-button" id="nextTaskPage" title="Next page" ${state.taskPage >= totalPages ? "disabled" : ""}>›</button>
      </div>
      <a class="text-button action-link" href="/api/export?${escapeHtml(exportParams.toString())}">Export CSV</a>
    </div>
    ${taskTable(data.tasks, false)}
  `;
  document.querySelectorAll(".segment-button").forEach((button) => {
    button.addEventListener("click", () => {
      clearSelectedTaskSavedView();
      state.taskStatus = button.dataset.status;
      state.taskPage = 1;
      renderFollowup();
    });
  });
  const taskSavedView = document.querySelector("#taskSavedView");
  taskSavedView.addEventListener("change", () => {
    const selectedId = taskSavedView.value;
    state.taskSavedViewId = selectedId;
    if (!selectedId) {
      renderFollowup();
      return;
    }
    const view = savedViews.find((item) => String(item.id) === String(selectedId));
    if (view) {
      applyTaskSettings(view.settings || {});
      state.taskSavedViewId = selectedId;
    }
    renderFollowup();
  });
  document.querySelector("#saveTaskViewButton").addEventListener("click", async () => {
    const name = window.prompt("Save this follow-up view as");
    if (!name?.trim()) return;
    setStatus("Saving view");
    const saved = await postJson("/api/save_view", {
      type: "tasks",
      name: name.trim(),
      settings: currentTaskSettings(),
    });
    state.taskSavedViewId = saved.view?.id ? String(saved.view.id) : "";
    await renderFollowup();
    setStatus("View saved");
  });
  document.querySelector("#deleteTaskViewButton").addEventListener("click", async () => {
    const viewId = state.taskSavedViewId;
    if (!viewId) return;
    const ok = window.confirm("Delete this saved follow-up view?");
    if (!ok) return;
    setStatus("Deleting view");
    await postJson("/api/delete_view", { id: Number(viewId) });
    state.taskSavedViewId = "";
    await renderFollowup();
    setStatus("View deleted");
  });
  document.querySelector("#resetTaskViewButton").addEventListener("click", () => {
    resetTaskView();
    renderFollowup();
  });
  document.querySelector("#taskSearch").addEventListener("input", (event) => {
    window.clearTimeout(state.debounce);
    state.debounce = window.setTimeout(() => {
      clearSelectedTaskSavedView();
      state.taskQ = event.target.value.trim();
      state.taskPage = 1;
      renderFollowup();
    }, 250);
  });
  document.querySelector("#taskRecordType").addEventListener("change", (event) => {
    clearSelectedTaskSavedView();
    state.taskRecordType = event.target.value;
    state.taskPage = 1;
    renderFollowup();
  });
  document.querySelector("#taskSource").addEventListener("change", (event) => {
    clearSelectedTaskSavedView();
    state.taskSource = event.target.value;
    state.taskPage = 1;
    renderFollowup();
  });
  document.querySelector("#taskSortField").addEventListener("change", (event) => {
    clearSelectedTaskSavedView();
    state.taskSort = event.target.value;
    state.taskPage = 1;
    renderFollowup();
  });
  document.querySelector("#taskSortDirection").addEventListener("change", (event) => {
    clearSelectedTaskSavedView();
    state.taskDirection = event.target.value === "desc" ? "desc" : "asc";
    state.taskPage = 1;
    renderFollowup();
  });
  document.querySelector("#prevTaskPage").addEventListener("click", () => {
    state.taskPage = Math.max(1, state.taskPage - 1);
    renderFollowup();
  });
  document.querySelector("#nextTaskPage").addEventListener("click", () => {
    state.taskPage += 1;
    renderFollowup();
  });
  wireRecordButtons(els.followup);
  wireTaskButtons(els.followup);
  wireWorkQueuePresets(els.followup);
  setStatus("Ready");
}

function followupTransitionPanel(plan) {
  if (!plan?.title) return "";
  const counts = plan.counts || {};
  const steps = plan.steps || [];
  const tone = plan.status === "ready" ? "green" : plan.status === "attention" ? "coral" : "gold";
  return `
    <div class="band followup-transition-panel ${escapeHtml(plan.status || "")}">
      <div class="band-header">
        <div>
          <h3>${escapeHtml(plan.title || "Follow Up Transition Plan")}</h3>
          <p>${escapeHtml(plan.message || "")}</p>
        </div>
        <div class="followup-transition-actions">
          <span class="pill ${tone}">${escapeHtml(labelize(plan.status || "waiting"))}</span>
          ${plan.report ? `<a class="text-button action-link" href="${escapeHtml(plan.report)}" target="_blank" rel="noreferrer">Open Plan</a>` : ""}
          ${plan.export_url ? `<a class="text-button action-link" href="${escapeHtml(plan.export_url)}">Export Plan</a>` : ""}
        </div>
      </div>
      <div class="followup-transition-body">
        <div class="followup-transition-counts">
          <span><strong>${formatNumber(counts.open_imported || 0)}</strong>imported open</span>
          <span><strong>${formatNumber(counts.overdue_imported || 0)}</strong>overdue imported</span>
          <span><strong>${formatNumber(counts.open_local || 0)}</strong>local open</span>
          <span><strong>${formatNumber(counts.imported_without_due || 0)}</strong>without due date</span>
        </div>
        <div class="followup-transition-steps">
          ${steps.map((step) => followupTransitionStep(step)).join("")}
        </div>
        ${plan.safety ? `<p class="followup-transition-safety">${escapeHtml(plan.safety)}</p>` : ""}
      </div>
    </div>
  `;
}

function followupTransitionStep(step) {
  const tone = step.status === "ready" || step.status === "complete" ? "green" : step.status === "attention" ? "coral" : "gold";
  return `
    <div class="followup-transition-step ${escapeHtml(step.status || "")}">
      <div>
        <span class="pill ${tone}">${escapeHtml(labelize(step.status || "waiting"))}</span>
        <strong>${escapeHtml(step.title || "")}</strong>
        <p>${escapeHtml(step.description || "")}</p>
      </div>
      <div class="followup-transition-step-action">
        <span class="muted">${formatNumber(step.count || 0)} items</span>
        ${step.preset ? `<button type="button" class="text-button work-queue-preset" data-preset="${escapeHtml(step.preset)}">${escapeHtml(step.action || "Open")}</button>` : ""}
      </div>
    </div>
  `;
}

function taskRecordTypeOptions() {
  return [
    ["", "All record types"],
    ["person", "People"],
    ["company", "Companies"],
    ["lead", "Leads"],
    ["deal", "Deals"],
    ["unlinked", "No linked record"],
  ];
}

function taskSourceOptions() {
  return [
    ["", "All sources"],
    ["imported", "Imported from Zendesk"],
    ["local", "Local only"],
  ];
}

function taskSortOptions() {
  return [
    ["due_date", "Due Date"],
    ["task", "Task"],
    ["record", "Record"],
    ["status", "Status"],
    ["created_at", "Created"],
    ["updated_at", "Updated"],
  ];
}

function currentActivitySettings() {
  return {
    q: state.activityQ,
    activity_type: state.activityType,
    record_type: state.activityRecordType,
    date_from: state.activityDateFrom,
    date_to: state.activityDateTo,
  };
}

function applyActivitySettings(settings) {
  state.activityQ = settings.q || "";
  const activityType = settings.activity_type || "";
  state.activityType = activityTypeOptions().some(([value]) => value === activityType) ? activityType : "";
  const recordType = settings.record_type || "";
  state.activityRecordType = activityRecordTypeOptions().some(([value]) => value === recordType) ? recordType : "";
  state.activityDateFrom = dateInputValue(settings.date_from || "");
  state.activityDateTo = dateInputValue(settings.date_to || "");
}

function dateInputValue(value) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value || "") ? value : "";
}

function clearSelectedActivitySavedView() {
  state.activitySavedViewId = "";
}

function resetActivityView() {
  state.activityQ = "";
  state.activityType = "";
  state.activityRecordType = "";
  state.activityDateFrom = "";
  state.activityDateTo = "";
  state.activitySavedViewId = "";
}

function activitySavedViewControls(savedViews) {
  const selectedId = state.activitySavedViewId || "";
  return `
    <select id="activitySavedView" aria-label="Saved activity view">
      <option value="">Saved views</option>
      ${savedViews
        .map((view) => {
          const count = typeof view.record_count === "number" ? ` (${formatNumber(view.record_count)})` : "";
          return `<option value="${view.id}" ${String(view.id) === String(selectedId) ? "selected" : ""}>${escapeHtml(`${view.name}${count}`)}</option>`;
        })
        .join("")}
    </select>
    <button class="text-button" id="saveActivityViewButton">Save View</button>
    <button class="text-button" id="deleteActivityViewButton" ${selectedId ? "" : "disabled"}>Delete</button>
    <button class="text-button" id="resetActivityViewButton">Reset View</button>
  `;
}

async function renderActivity() {
  setStatus("Loading activity");
  const params = new URLSearchParams({
    limit: "100",
    q: state.activityQ,
    activity_type: state.activityType,
    record_type: state.activityRecordType,
    date_from: state.activityDateFrom,
    date_to: state.activityDateTo,
  });
  const exportParams = new URLSearchParams({
    type: "activity",
    q: state.activityQ,
    activity_type: state.activityType,
    record_type: state.activityRecordType,
    date_from: state.activityDateFrom,
    date_to: state.activityDateTo,
  });
  const [data, savedViewData] = await Promise.all([
    fetchJson(`/api/activity?${params.toString()}`),
    fetchJson("/api/saved_views?type=activity"),
  ]);
  const savedViews = savedViewData.views || [];
  if (state.activitySavedViewId && !savedViews.some((view) => String(view.id) === String(state.activitySavedViewId))) {
    state.activitySavedViewId = "";
  }
  els.activity.innerHTML = `
    <div class="section-header">
      <div>
        <h2>Activity</h2>
        <p>${formatNumber(data.total ?? data.activity.length)} matching items</p>
      </div>
    </div>
    <div class="table-tools">
      <div class="filter-row">
        <input id="activitySearch" type="search" value="${escapeHtml(state.activityQ)}" placeholder="Filter activity text or records">
        <select id="activityTypeFilter" aria-label="Filter activity by type">
          ${activityTypeOptions()
            .map(([value, label]) => `<option value="${escapeHtml(value)}" ${state.activityType === value ? "selected" : ""}>${escapeHtml(label)}</option>`)
            .join("")}
        </select>
        <select id="activityRecordTypeFilter" aria-label="Filter activity by related record type">
          ${activityRecordTypeOptions()
            .map(([value, label]) => `<option value="${escapeHtml(value)}" ${state.activityRecordType === value ? "selected" : ""}>${escapeHtml(label)}</option>`)
            .join("")}
        </select>
        <label class="compact-date-filter">
          <span>From</span>
          <input id="activityDateFrom" type="date" value="${escapeHtml(state.activityDateFrom)}" aria-label="Filter activity from date">
        </label>
        <label class="compact-date-filter">
          <span>To</span>
          <input id="activityDateTo" type="date" value="${escapeHtml(state.activityDateTo)}" aria-label="Filter activity to date">
        </label>
        ${activitySavedViewControls(savedViews)}
      </div>
      <a class="text-button action-link" href="/api/export?${escapeHtml(exportParams.toString())}">Export CSV</a>
    </div>
    <div class="band">
      <div class="band-header"><h3>Timeline</h3></div>
      <div class="timeline">
        ${data.activity.length ? data.activity.map(globalActivityItem).join("") : `<div class="empty-state"><h3>No activity</h3><p>No notes, tasks, or local changes yet.</p></div>`}
      </div>
    </div>
  `;
  const activitySavedView = document.querySelector("#activitySavedView");
  activitySavedView.addEventListener("change", () => {
    const selectedId = activitySavedView.value;
    state.activitySavedViewId = selectedId;
    if (!selectedId) {
      renderActivity();
      return;
    }
    const view = savedViews.find((item) => String(item.id) === String(selectedId));
    if (view) {
      applyActivitySettings(view.settings || {});
      state.activitySavedViewId = selectedId;
    }
    renderActivity();
  });
  document.querySelector("#saveActivityViewButton").addEventListener("click", async () => {
    const name = window.prompt("Save this activity view as");
    if (!name?.trim()) return;
    setStatus("Saving view");
    const saved = await postJson("/api/save_view", {
      type: "activity",
      name: name.trim(),
      settings: currentActivitySettings(),
    });
    state.activitySavedViewId = saved.view?.id ? String(saved.view.id) : "";
    await renderActivity();
    setStatus("View saved");
  });
  document.querySelector("#deleteActivityViewButton").addEventListener("click", async () => {
    const viewId = state.activitySavedViewId;
    if (!viewId) return;
    const ok = window.confirm("Delete this saved activity view?");
    if (!ok) return;
    setStatus("Deleting view");
    await postJson("/api/delete_view", { id: Number(viewId) });
    state.activitySavedViewId = "";
    await renderActivity();
    setStatus("View deleted");
  });
  document.querySelector("#resetActivityViewButton").addEventListener("click", () => {
    resetActivityView();
    renderActivity();
  });
  const activitySearch = document.querySelector("#activitySearch");
  activitySearch.addEventListener("input", () => {
    state.activityQ = activitySearch.value;
    window.clearTimeout(state.debounce);
    state.debounce = window.setTimeout(() => {
      clearSelectedActivitySavedView();
      renderActivity();
    }, 250);
  });
  document.querySelector("#activityTypeFilter").addEventListener("change", (event) => {
    clearSelectedActivitySavedView();
    state.activityType = event.target.value;
    renderActivity();
  });
  document.querySelector("#activityRecordTypeFilter").addEventListener("change", (event) => {
    clearSelectedActivitySavedView();
    state.activityRecordType = event.target.value;
    renderActivity();
  });
  document.querySelector("#activityDateFrom").addEventListener("change", (event) => {
    clearSelectedActivitySavedView();
    state.activityDateFrom = event.target.value;
    renderActivity();
  });
  document.querySelector("#activityDateTo").addEventListener("change", (event) => {
    clearSelectedActivitySavedView();
    state.activityDateTo = event.target.value;
    renderActivity();
  });
  wireRecordButtons(els.activity);
  setStatus("Ready");
}

function activityTypeOptions() {
  return [
    ["", "All activity"],
    ["note", "Notes"],
    ["task", "Open Tasks"],
    ["task_completed", "Completed Tasks"],
    ["archive", "Archive"],
    ["local_change", "Local Changes"],
    ["cleanup_decision", "Cleanup Decisions"],
    ["project_decision", "Project Decisions"],
    ["deal", "Deals"],
  ];
}

function activityRecordTypeOptions() {
  return [
    ["", "All records"],
    ["person", "People"],
    ["company", "Companies"],
    ["lead", "Leads"],
    ["deal", "Deals"],
    ["cleanup_group", "Cleanup Groups"],
    ["unlinked", "No linked record"],
  ];
}

function globalActivityItem(item) {
  const linked = item.record_id && detailTypeSupported(item.record_type);
  return `
    <div class="activity-row">
      <div class="activity-dot"></div>
      <div class="activity-main">
        <strong>${escapeHtml(labelize(item.activity_type || "activity"))}</strong>
        <p>${escapeHtml(item.summary || "")}</p>
        <div class="muted">${formatDate(item.occurred_at)}</div>
      </div>
      <div>
        ${linked
          ? `<button class="text-button record-button" data-type="${escapeHtml(item.record_type)}" data-id="${item.record_id}">${escapeHtml(item.record_name || `${item.record_type} #${item.record_id}`)}</button>`
          : `<span class="muted">${escapeHtml(item.record_name || item.record_type || "")}</span>`}
      </div>
    </div>
  `;
}

async function renderExports() {
  setStatus("Loading exports");
  const data = await fetchJson("/api/export_manifest");
  const packageInfo = data.package || {};
  const documentPackage = data.document_package || {};
  const packageEnabled = packageInfo.enabled !== false;
  const documentPackageEnabled = documentPackage.enabled !== false;
  els.exports.innerHTML = `
    <div class="section-header">
      <div>
        <h2>Exports</h2>
        <p>Download local CRM data, reports, and portable backup artifacts</p>
      </div>
    </div>
    <div class="band export-package-band">
      <div class="band-header">
        <div>
          <h3>${escapeHtml(packageInfo.label || "Complete Local CRM Package")}</h3>
          <p>${escapeHtml(packageInfo.description || "Download the current local CRM package as one zip file.")}</p>
        </div>
        ${
          packageEnabled
            ? `<a class="text-button action-link" href="${escapeHtml(packageInfo.url || "/api/export_package")}">Download Package</a>`
            : `<button class="text-button" type="button" disabled title="${escapeHtml(packageInfo.locked_message || "Package export locked")}">Package Locked</button>`
        }
      </div>
      <div class="package-content-list">
        ${(packageInfo.contents || ["SQLite database", "CSV exports", "reports", "project docs"])
          .map((item) => `<span>${escapeHtml(item)}</span>`)
          .join("")}
      </div>
    </div>
    <div class="band export-package-band">
      <div class="band-header">
        <div>
          <h3>${escapeHtml(documentPackage.label || "Downloaded Document Files")}</h3>
          <p>${escapeHtml(documentPackage.description || "Download recovered Zendesk document files as one zip file.")}</p>
        </div>
        ${
          documentPackage.available && documentPackageEnabled
            ? `<a class="text-button action-link" href="${escapeHtml(documentPackage.url || "/api/export_document_files_package")}">Download Documents</a>`
            : documentPackage.available
              ? `<button class="text-button" type="button" disabled title="${escapeHtml(documentPackage.locked_message || "Document export locked")}">Documents Locked</button>`
            : `<button class="text-button" type="button" disabled>No Documents</button>`
        }
      </div>
      <div class="package-content-list">
        <span>${formatNumber(documentPackage.file_count || 0)} files</span>
        <span>${escapeHtml(formatBytes(documentPackage.bytes || 0))}</span>
        <span>document manifest</span>
      </div>
    </div>
    <div class="band">
      <div class="band-header"><h3>CSV Downloads</h3></div>
      <div class="export-grid">
        ${data.exports
          .map((item) => `
            <a class="export-link" href="${escapeHtml(item.url)}">
              <strong>${escapeHtml(item.label)}</strong>
              <span>${escapeHtml(item.type)}.csv</span>
            </a>
          `)
          .join("")}
      </div>
    </div>
  `;
  setStatus("Ready");
}

async function renderTags() {
  setStatus("Loading tags");
  const params = new URLSearchParams({
    page: String(state.tagPage),
    page_size: "50",
    q: state.tagQ,
    record_type: state.tagRecordType,
  });
  const [data, savedViewData] = await Promise.all([
    fetchJson(`/api/tags?${params.toString()}`),
    fetchJson("/api/saved_views?type=tags"),
  ]);
  const savedViews = savedViewData.views || [];
  if (state.tagSavedViewId && !savedViews.some((view) => String(view.id) === String(state.tagSavedViewId))) {
    state.tagSavedViewId = "";
  }
  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));
  const exportParams = new URLSearchParams({
    type: "tags",
    q: state.tagQ,
    record_type: state.tagRecordType,
  });
  const tagRecordTypeCounts = Object.fromEntries((data.record_type_counts || []).map((item) => [item.value, item.count]));
  els.tags.innerHTML = `
    <div class="section-header">
      <div>
        <h2>Tags</h2>
        <p>${formatNumber(data.total)} tags, ${formatNumber(data.total_assignments)} record assignments</p>
      </div>
      <a class="text-button action-link" href="/api/export?${escapeHtml(exportParams.toString())}">Export CSV</a>
    </div>
    <div class="table-tools">
      <input id="tagSearch" type="search" value="${escapeHtml(state.tagQ)}" placeholder="Filter tags">
      <select id="tagRecordTypeFilter" aria-label="Tag record type">
        ${tagRecordTypeOptions()
          .map(([value, label]) => {
            const count = value ? tagRecordTypeCounts[value] || 0 : null;
            return `<option value="${escapeHtml(value)}" ${state.tagRecordType === value ? "selected" : ""}>${escapeHtml(count === null ? label : `${label} (${formatNumber(count)})`)}</option>`;
          })
          .join("")}
      </select>
      ${tagSavedViewControls(savedViews)}
      <div class="pager">
        <button class="icon-button" id="prevTagPage" title="Previous page" ${state.tagPage <= 1 ? "disabled" : ""}>‹</button>
        <span class="muted">Page ${state.tagPage} of ${totalPages}</span>
        <button class="icon-button" id="nextTagPage" title="Next page" ${state.tagPage >= totalPages ? "disabled" : ""}>›</button>
      </div>
    </div>
    ${
      data.tags.length
        ? `<table class="data-table">
            <thead>
              <tr>
                <th>Tag</th>
                <th>Assignments</th>
                <th>Definitions</th>
                <th>Used On</th>
              </tr>
            </thead>
            <tbody>
              ${data.tags
                .map((tag) => `
                  <tr>
                    <td>
                      <button class="record-button tag-detail-button" data-id="${tag.source_id}">
                        ${escapeHtml(tag.display_name || "(blank tag)")}
                      </button>
                    </td>
                    <td>${formatNumber(tag.assignment_count)}</td>
                    <td class="muted">${formatNumber(tag.definition_count)}</td>
                    <td>
                      <div class="tag-list compact-tags">
                        ${
                          tag.record_types.length
                            ? tag.record_types.map((type) => `<span class="tag">${escapeHtml(labelize(type))}</span>`).join("")
                            : `<span class="muted">Unassigned</span>`
                        }
                      </div>
                    </td>
                  </tr>
                `)
                .join("")}
            </tbody>
          </table>`
        : `<div class="empty-state"><h3>No tags</h3><p>No tags matched this filter.</p></div>`
    }
  `;
  const tagSavedView = document.querySelector("#tagSavedView");
  tagSavedView.addEventListener("change", () => {
    const selectedId = tagSavedView.value;
    state.tagSavedViewId = selectedId;
    if (!selectedId) {
      renderTags();
      return;
    }
    const view = savedViews.find((item) => String(item.id) === String(selectedId));
    if (view) {
      applyTagSettings(view.settings || {});
      state.tagSavedViewId = selectedId;
    }
    renderTags();
  });
  document.querySelector("#saveTagViewButton").addEventListener("click", async () => {
    const name = window.prompt("Save this tag view as");
    if (!name?.trim()) return;
    setStatus("Saving view");
    const saved = await postJson("/api/save_view", {
      type: "tags",
      name: name.trim(),
      settings: currentTagSettings(),
    });
    state.tagSavedViewId = saved.view?.id ? String(saved.view.id) : "";
    await renderTags();
    setStatus("View saved");
  });
  document.querySelector("#deleteTagViewButton").addEventListener("click", async () => {
    const viewId = state.tagSavedViewId;
    if (!viewId) return;
    const ok = window.confirm("Delete this saved tag view?");
    if (!ok) return;
    setStatus("Deleting view");
    await postJson("/api/delete_view", { id: Number(viewId) });
    state.tagSavedViewId = "";
    await renderTags();
    setStatus("View deleted");
  });
  document.querySelector("#resetTagViewButton").addEventListener("click", () => {
    resetTagView();
    renderTags();
  });
  const tagSearch = document.querySelector("#tagSearch");
  tagSearch.addEventListener("input", () => {
    window.clearTimeout(state.debounce);
    state.debounce = window.setTimeout(() => {
      clearSelectedTagSavedView();
      state.tagQ = tagSearch.value.trim();
      state.tagPage = 1;
      renderTags();
    }, 220);
  });
  document.querySelector("#tagRecordTypeFilter").addEventListener("change", (event) => {
    clearSelectedTagSavedView();
    state.tagRecordType = event.target.value;
    state.tagPage = 1;
    renderTags();
  });
  document.querySelector("#prevTagPage").addEventListener("click", () => {
    state.tagPage = Math.max(1, state.tagPage - 1);
    renderTags();
  });
  document.querySelector("#nextTagPage").addEventListener("click", () => {
    state.tagPage += 1;
    renderTags();
  });
  wireTagButtons(els.tags);
  setStatus("Ready");
}

async function renderLinkedResources() {
  setStatus("Loading linked resources");
  const params = new URLSearchParams({
    page: String(state.linkedResourcePage),
    page_size: "50",
    q: state.linkedResourceQ,
    kind: state.linkedResourceKind,
    record_type: state.linkedResourceRecordType,
  });
  const [data, savedViewData] = await Promise.all([
    fetchJson(`/api/linked_resources?${params.toString()}`),
    fetchJson("/api/saved_views?type=linked_resources"),
  ]);
  const savedViews = savedViewData.views || [];
  if (state.linkedResourceSavedViewId && !savedViews.some((view) => String(view.id) === String(state.linkedResourceSavedViewId))) {
    state.linkedResourceSavedViewId = "";
  }
  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));
  const exportParams = new URLSearchParams({
    type: "linked_resources",
    q: state.linkedResourceQ,
    kind: state.linkedResourceKind,
    record_type: state.linkedResourceRecordType,
  });
  els.linkedResources.innerHTML = `
    <div class="section-header">
      <div>
        <h2>Linked Resources</h2>
        <p>${formatNumber(data.total)} matching links · ${formatNumber(data.total_all)} total</p>
      </div>
      <a class="text-button action-link" href="/api/export?${escapeHtml(exportParams.toString())}">Export CSV</a>
    </div>
    <div class="cleanup-grid linked-resource-summary-grid">
      ${linkedResourceSummaryCards(data)}
    </div>
    <div class="table-tools">
      <input id="linkedResourceSearch" type="search" value="${escapeHtml(state.linkedResourceQ)}" placeholder="Filter links, records, sources, or URLs">
      <select id="linkedResourceKindFilter" aria-label="Linked resource kind">
        <option value="" ${state.linkedResourceKind ? "" : "selected"}>All link types</option>
        ${(data.kind_counts || [])
          .map((item) => `<option value="${escapeHtml(item.value)}" ${state.linkedResourceKind === item.value ? "selected" : ""}>${escapeHtml(item.value)} (${formatNumber(item.count)})</option>`)
          .join("")}
      </select>
      <select id="linkedResourceRecordTypeFilter" aria-label="Linked resource record type">
        <option value="" ${state.linkedResourceRecordType ? "" : "selected"}>All records</option>
        ${(data.record_type_counts || [])
          .map((item) => `<option value="${escapeHtml(item.value)}" ${state.linkedResourceRecordType === item.value ? "selected" : ""}>${escapeHtml(labelize(item.value))} (${formatNumber(item.count)})</option>`)
          .join("")}
      </select>
      ${linkedResourceSavedViewControls(savedViews)}
      <div class="pager">
        <button class="icon-button" id="prevLinkedResourcePage" title="Previous page" ${state.linkedResourcePage <= 1 ? "disabled" : ""}>‹</button>
        <span class="muted">Page ${state.linkedResourcePage} of ${totalPages}</span>
        <button class="icon-button" id="nextLinkedResourcePage" title="Next page" ${state.linkedResourcePage >= totalPages ? "disabled" : ""}>›</button>
      </div>
    </div>
    ${
      data.resources.length
        ? `<table class="data-table linked-resource-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Record</th>
                <th>Source</th>
                <th>Link</th>
              </tr>
            </thead>
            <tbody>
              ${data.resources.map(linkedResourceRow).join("")}
            </tbody>
          </table>`
        : `<div class="empty-state"><h3>No links</h3><p>No linked resources matched this filter.</p></div>`
    }
  `;
  const linkedResourceSavedView = document.querySelector("#linkedResourceSavedView");
  linkedResourceSavedView.addEventListener("change", () => {
    const selectedId = linkedResourceSavedView.value;
    state.linkedResourceSavedViewId = selectedId;
    if (!selectedId) {
      renderLinkedResources();
      return;
    }
    const view = savedViews.find((item) => String(item.id) === String(selectedId));
    if (view) {
      applyLinkedResourceSettings(view.settings || {});
      state.linkedResourceSavedViewId = selectedId;
    }
    renderLinkedResources();
  });
  document.querySelector("#saveLinkedResourceViewButton").addEventListener("click", async () => {
    const name = window.prompt("Save this linked-resource view as");
    if (!name?.trim()) return;
    setStatus("Saving view");
    const saved = await postJson("/api/save_view", {
      type: "linked_resources",
      name: name.trim(),
      settings: currentLinkedResourceSettings(),
    });
    state.linkedResourceSavedViewId = saved.view?.id ? String(saved.view.id) : "";
    await renderLinkedResources();
    setStatus("View saved");
  });
  document.querySelector("#deleteLinkedResourceViewButton").addEventListener("click", async () => {
    const viewId = state.linkedResourceSavedViewId;
    if (!viewId) return;
    const ok = window.confirm("Delete this saved linked-resource view?");
    if (!ok) return;
    setStatus("Deleting view");
    await postJson("/api/delete_view", { id: Number(viewId) });
    state.linkedResourceSavedViewId = "";
    await renderLinkedResources();
    setStatus("View deleted");
  });
  document.querySelector("#resetLinkedResourceViewButton").addEventListener("click", () => {
    resetLinkedResourceView();
    renderLinkedResources();
  });
  const linkedResourceSearch = document.querySelector("#linkedResourceSearch");
  linkedResourceSearch.addEventListener("input", () => {
    window.clearTimeout(state.debounce);
    state.debounce = window.setTimeout(() => {
      clearSelectedLinkedResourceSavedView();
      state.linkedResourceQ = linkedResourceSearch.value.trim();
      state.linkedResourcePage = 1;
      renderLinkedResources();
    }, 220);
  });
  document.querySelector("#linkedResourceKindFilter").addEventListener("change", (event) => {
    clearSelectedLinkedResourceSavedView();
    state.linkedResourceKind = event.target.value;
    state.linkedResourcePage = 1;
    renderLinkedResources();
  });
  document.querySelector("#linkedResourceRecordTypeFilter").addEventListener("change", (event) => {
    clearSelectedLinkedResourceSavedView();
    state.linkedResourceRecordType = event.target.value;
    state.linkedResourcePage = 1;
    renderLinkedResources();
  });
  document.querySelector("#prevLinkedResourcePage").addEventListener("click", () => {
    state.linkedResourcePage = Math.max(1, state.linkedResourcePage - 1);
    renderLinkedResources();
  });
  document.querySelector("#nextLinkedResourcePage").addEventListener("click", () => {
    state.linkedResourcePage += 1;
    renderLinkedResources();
  });
  wireRecordButtons(els.linkedResources);
  setStatus("Ready");
}

function linkedResourceSummaryCards(data) {
  const cards = (data.kind_counts || []).slice(0, 5);
  if (!cards.length) {
    return `<div class="signal"><strong>0</strong><span>Links</span></div>`;
  }
  return cards
    .map((item) => `<div class="signal"><strong>${formatNumber(item.count)}</strong><span>${escapeHtml(item.value)}</span></div>`)
    .join("");
}

function linkedResourceRow(resource) {
  const recordLabel = `${labelize(resource.record_type)} #${resource.record_id}`;
  return `
    <tr>
      <td><span class="pill">${escapeHtml(resource.kind || "Web Link")}</span></td>
      <td>
        <button class="record-button" data-type="${escapeHtml(resource.record_type)}" data-id="${resource.record_id}">
          ${escapeHtml(resource.record_name || recordLabel)}
        </button>
        <div class="muted">${escapeHtml(recordLabel)}</div>
      </td>
      <td>
        <strong>${escapeHtml(resource.source_label || labelize(resource.source_type || "source"))}</strong>
        <div class="muted">${escapeHtml(labelize(resource.source_type || "source"))}</div>
      </td>
      <td>
        <a href="${escapeHtml(resource.url)}" target="_blank" rel="noreferrer">${escapeHtml(resource.url)}</a>
        ${resource.context ? `<div class="muted linked-resource-context">${escapeHtml(resource.context)}</div>` : ""}
      </td>
    </tr>
  `;
}

async function renderArchive() {
  setStatus("Loading archive");
  const params = new URLSearchParams({
    page: String(state.archivePage),
    page_size: "50",
    q: state.archiveQ,
    item_type: state.archiveItemType,
    record_type: state.archiveRecordType,
    preset: state.archivePreset,
    review_status: state.archiveReviewStatus,
    triage_lane: state.archiveTriageLane,
    date_from: state.archiveDateFrom,
    date_to: state.archiveDateTo,
  });
  const [data, savedViewData] = await Promise.all([
    fetchJson(`/api/archive?${params.toString()}`),
    fetchJson("/api/saved_views?type=archive"),
  ]);
  const savedViews = savedViewData.views || [];
  if (state.archiveSavedViewId && !savedViews.some((view) => String(view.id) === String(state.archiveSavedViewId))) {
    state.archiveSavedViewId = "";
  }
  state.archiveLastItems = data.items || [];
  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));
  const exportParams = new URLSearchParams({
    type: "imported_archive",
    q: state.archiveQ,
    item_type: state.archiveItemType,
    record_type: state.archiveRecordType,
    preset: state.archivePreset,
    review_status: state.archiveReviewStatus,
    triage_lane: state.archiveTriageLane,
    date_from: state.archiveDateFrom,
    date_to: state.archiveDateTo,
  });
  els.archive.innerHTML = `
    <div class="section-header">
      <div>
        <h2>Archive</h2>
        <p>${formatNumber(data.total)} matching items · calls, texts, documents, orders, and conversions</p>
      </div>
      <a class="text-button action-link" href="/api/export?${escapeHtml(exportParams.toString())}">Export CSV</a>
    </div>
    <div class="cleanup-grid linked-resource-summary-grid">
      ${archiveSummaryCards(data)}
    </div>
    ${archiveAssociationCoveragePanel(data.association)}
    ${archiveDecisionEvidencePanel(data.unlinked_communications, data.preset)}
    ${archiveReviewQueuePanel(data.unlinked_communications, data.review_status)}
    ${archiveReviewTriagePanel(data.archive_triage, data.triage_lane)}
    <div class="table-tools">
      <input id="archiveSearch" type="search" value="${escapeHtml(state.archiveQ)}" placeholder="Filter archive text, files, phones, or records">
      <select id="archiveItemTypeFilter" aria-label="Archive item type">
        <option value="" ${state.archiveItemType ? "" : "selected"}>All item types</option>
        ${(data.item_type_counts || [])
          .map((item) => `<option value="${escapeHtml(item.value)}" ${state.archiveItemType === item.value ? "selected" : ""}>${escapeHtml(archiveItemLabel(item.value))} (${formatNumber(item.count)})</option>`)
          .join("")}
      </select>
      <select id="archiveRecordTypeFilter" aria-label="Archive record type">
        <option value="" ${state.archiveRecordType ? "" : "selected"}>All records</option>
        ${(data.record_type_counts || [])
          .map((item) => `<option value="${escapeHtml(item.value)}" ${state.archiveRecordType === item.value ? "selected" : ""}>${escapeHtml(item.value === "unlinked" ? "Unlinked" : labelize(item.value))} (${formatNumber(item.count)})</option>`)
          .join("")}
      </select>
      <select id="archiveReviewStatusFilter" aria-label="Archive review status">
        ${archiveReviewStatusOptions()
          .map(([value, label]) => {
            const count = (data.review_status_counts || []).find((item) => item.value === value)?.count;
            const countText = value && typeof count === "number" ? ` (${formatNumber(count)})` : "";
            return `<option value="${escapeHtml(value)}" ${state.archiveReviewStatus === value ? "selected" : ""}>${escapeHtml(label + countText)}</option>`;
          })
          .join("")}
      </select>
      <select id="archiveTriageLaneFilter" aria-label="Archive triage lane">
        ${archiveTriageLaneOptions()
          .map(([value, label]) => {
            const count = (data.archive_triage?.lane_counts || []).find((item) => item.triage_lane === value)?.count;
            const countText = value && typeof count === "number" ? ` (${formatNumber(count)})` : "";
            return `<option value="${escapeHtml(value)}" ${state.archiveTriageLane === value ? "selected" : ""}>${escapeHtml(label + countText)}</option>`;
          })
          .join("")}
      </select>
      <label class="compact-date-filter">
        <span>From</span>
        <input id="archiveDateFrom" type="date" value="${escapeHtml(state.archiveDateFrom)}" aria-label="Filter archive from date">
      </label>
      <label class="compact-date-filter">
        <span>To</span>
        <input id="archiveDateTo" type="date" value="${escapeHtml(state.archiveDateTo)}" aria-label="Filter archive to date">
      </label>
      ${archiveSavedViewControls(savedViews)}
      <div class="pager">
        <button class="icon-button" id="prevArchivePage" title="Previous page" ${state.archivePage <= 1 ? "disabled" : ""}>‹</button>
        <span class="muted">Page ${state.archivePage} of ${totalPages}</span>
        <button class="icon-button" id="nextArchivePage" title="Next page" ${state.archivePage >= totalPages ? "disabled" : ""}>›</button>
      </div>
    </div>
    ${
      data.items.length
        ? `<table class="data-table archive-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Record</th>
                <th>Item</th>
                <th>When</th>
                <th>Owner</th>
                <th>Review</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>${data.items.map(archiveRow).join("")}</tbody>
          </table>`
        : `<div class="empty-state"><h3>No archive items</h3><p>No imported archive items matched this filter.</p></div>`
    }
  `;
  const archiveSavedView = document.querySelector("#archiveSavedView");
  archiveSavedView.addEventListener("change", () => {
    const selectedId = archiveSavedView.value;
    state.archiveSavedViewId = selectedId;
    if (!selectedId) {
      renderArchive();
      return;
    }
    const view = savedViews.find((item) => String(item.id) === String(selectedId));
    if (view) {
      applyArchiveSettings(view.settings || {});
      state.archiveSavedViewId = selectedId;
    }
    renderArchive();
  });
  document.querySelector("#saveArchiveViewButton").addEventListener("click", async () => {
    const name = window.prompt("Save this archive view as");
    if (!name?.trim()) return;
    setStatus("Saving view");
    const saved = await postJson("/api/save_view", {
      type: "archive",
      name: name.trim(),
      settings: currentArchiveSettings(),
    });
    state.archiveSavedViewId = saved.view?.id ? String(saved.view.id) : "";
    await renderArchive();
    setStatus("View saved");
  });
  document.querySelector("#deleteArchiveViewButton").addEventListener("click", async () => {
    const viewId = state.archiveSavedViewId;
    if (!viewId) return;
    const ok = window.confirm("Delete this saved archive view?");
    if (!ok) return;
    setStatus("Deleting view");
    await postJson("/api/delete_view", { id: Number(viewId) });
    state.archiveSavedViewId = "";
    await renderArchive();
    setStatus("View deleted");
  });
  document.querySelector("#resetArchiveViewButton").addEventListener("click", () => {
    resetArchiveView();
    renderArchive();
  });
  const archiveSearch = document.querySelector("#archiveSearch");
  archiveSearch.addEventListener("input", () => {
    window.clearTimeout(state.debounce);
    state.debounce = window.setTimeout(() => {
      clearSelectedArchiveSavedView();
      state.archiveQ = archiveSearch.value.trim();
      state.archivePage = 1;
      renderArchive();
    }, 220);
  });
  document.querySelector("#archiveItemTypeFilter").addEventListener("change", (event) => {
    clearSelectedArchiveSavedView();
    state.archiveItemType = event.target.value;
    state.archivePreset = "";
    state.archiveTriageLane = "";
    state.archivePage = 1;
    renderArchive();
  });
  document.querySelector("#archiveRecordTypeFilter").addEventListener("change", (event) => {
    clearSelectedArchiveSavedView();
    state.archiveRecordType = event.target.value;
    state.archivePreset = "";
    state.archiveTriageLane = "";
    state.archivePage = 1;
    renderArchive();
  });
  document.querySelector("#archiveReviewStatusFilter").addEventListener("change", (event) => {
    clearSelectedArchiveSavedView();
    state.archiveReviewStatus = event.target.value;
    state.archivePage = 1;
    renderArchive();
  });
  document.querySelector("#archiveTriageLaneFilter").addEventListener("change", (event) => {
    clearSelectedArchiveSavedView();
    state.archiveTriageLane = event.target.value;
    if (state.archiveTriageLane) {
      state.archivePreset = "unlinked_communications";
      state.archiveItemType = "";
      state.archiveRecordType = "";
    }
    state.archivePage = 1;
    renderArchive();
  });
  document.querySelector("#archiveDateFrom").addEventListener("change", (event) => {
    clearSelectedArchiveSavedView();
    state.archiveDateFrom = dateInputValue(event.target.value);
    state.archivePage = 1;
    renderArchive();
  });
  document.querySelector("#archiveDateTo").addEventListener("change", (event) => {
    clearSelectedArchiveSavedView();
    state.archiveDateTo = dateInputValue(event.target.value);
    state.archivePage = 1;
    renderArchive();
  });
  document.querySelectorAll(".archive-preset-button").forEach((button) => {
    button.addEventListener("click", () => {
      clearSelectedArchiveSavedView();
      state.archivePreset = button.dataset.preset || "";
      state.archiveItemType = "";
      state.archiveRecordType = "";
      state.archiveTriageLane = "";
      state.archivePage = 1;
      renderArchive();
    });
  });
  document.querySelectorAll(".archive-review-filter-button").forEach((button) => {
    button.addEventListener("click", () => {
      clearSelectedArchiveSavedView();
      state.archiveReviewStatus = button.dataset.reviewStatus || "";
      state.archivePreset = "unlinked_communications";
      state.archiveItemType = "";
      state.archiveRecordType = "";
      state.archivePage = 1;
      renderArchive();
    });
  });
  document.querySelectorAll(".archive-triage-filter-button").forEach((button) => {
    button.addEventListener("click", () => {
      clearSelectedArchiveSavedView();
      state.archiveTriageLane = button.dataset.triageLane || "";
      state.archivePreset = "unlinked_communications";
      state.archiveItemType = "";
      state.archiveRecordType = "";
      state.archivePage = 1;
      renderArchive();
    });
  });
  document.querySelectorAll(".archive-number-review-button").forEach((button) => {
    button.addEventListener("click", () => {
      clearSelectedArchiveSavedView();
      state.archiveQ = button.dataset.phone || "";
      state.archivePreset = "unlinked_communications";
      state.archiveItemType = "";
      state.archiveRecordType = "";
      state.archiveReviewStatus = "";
      state.archiveTriageLane = button.dataset.triageLane || "";
      state.archivePage = 1;
      renderArchive();
    });
  });
  document.querySelector("#prevArchivePage").addEventListener("click", () => {
    state.archivePage = Math.max(1, state.archivePage - 1);
    renderArchive();
  });
  document.querySelector("#nextArchivePage").addEventListener("click", () => {
    state.archivePage += 1;
    renderArchive();
  });
  wireNextAction(els.archive);
  wireRecordButtons(els.archive);
  wireArchiveButtons(els.archive);
  setStatus("Ready");
  return data;
}

function archiveDecisionEvidencePanel(summary, activePreset) {
  if (!summary) return "";
  const typeCounts = summary.type_counts || {};
  const classCounts = summary.classification_counts || {};
  const active = activePreset === summary.preset;
  return `
    <div class="band archive-decision-panel ${active ? "active" : ""}">
      <div class="band-header">
        <div>
          <h3>Unlinked Calls/Texts Evidence</h3>
          <p>${escapeHtml(summary.reason || "")}</p>
        </div>
        <span class="pill ${Number(classCounts.exact_unique_candidate || 0) ? "gold" : "green"}">${escapeHtml(summary.recommendation || "Review")}</span>
      </div>
      <div class="archive-decision-body">
        <div class="archive-decision-metrics">
          <span><strong>${formatNumber(summary.total || 0)}</strong>Reviewed</span>
          <span><strong>${formatNumber(typeCounts.call || 0)}</strong>Calls</span>
          <span><strong>${formatNumber(typeCounts.text_message || 0)}</strong>Texts</span>
          <span><strong>${formatNumber(classCounts.exact_unique_candidate || 0)}</strong>Exact candidates</span>
          <span><strong>${formatNumber(classCounts.no_crm_phone_match || 0)}</strong>No phone match</span>
          <span><strong>${formatNumber(classCounts.short_or_non_contact_number || 0)}</strong>Short-code</span>
        </div>
        <div class="archive-decision-actions">
          <button class="text-button archive-preset-button" type="button" data-preset="${active ? "" : escapeHtml(summary.preset || "")}">
            ${active ? "Show All Archive" : "Show Evidence Set"}
          </button>
          <button class="text-button next-action-decision" type="button" data-key="unlinked_archive_matching">Open Decision</button>
          <button class="text-button next-action-fill" type="button" data-key="unlinked_archive_matching">Fill Recommended</button>
          <a class="text-button action-link" href="${escapeHtml(summary.report || "/reports/unlinked_archive_matching_candidates.md")}" target="_blank" rel="noreferrer">Open Report</a>
        </div>
      </div>
      ${
        summary.top_numbers?.length
          ? `<div class="archive-top-numbers">
              ${summary.top_numbers
                .map((item) => `<span>${escapeHtml(archiveItemLabel(item.item_type))} · ${escapeHtml(item.phone_number || "(blank)")} · ${formatNumber(item.count)}</span>`)
                .join("")}
            </div>`
          : ""
      }
    </div>
  `;
}

function archiveReviewQueuePanel(summary, activeReviewStatus) {
  if (!summary) return "";
  const reviewCounts = summary.review_status_counts || [];
  const countFor = (value) => reviewCounts.find((item) => item.value === value)?.count || 0;
  const topNumbers = summary.top_numbers || [];
  return `
    <div class="band archive-review-panel">
      <div class="band-header">
        <div>
          <h3>Manual Archive Review Queue</h3>
          <p>Track unlinked calls/texts without forcing weak matches. Mark items as archive-only, needs lookup, or ready to link from the sidebar inspector.</p>
        </div>
        <span class="pill ${countFor("unreviewed") ? "gold" : "green"}">${formatNumber(countFor("unreviewed"))} unreviewed</span>
      </div>
      <div class="archive-review-counts">
        ${archiveReviewStatusOptions()
          .filter(([value]) => value)
          .map(([value, label]) => `
            <button class="archive-review-filter-button ${activeReviewStatus === value ? "active" : ""}" type="button" data-review-status="${escapeHtml(value)}">
              <strong>${formatNumber(countFor(value))}</strong>
              <span>${escapeHtml(label)}</span>
            </button>
          `)
          .join("")}
      </div>
      ${
        topNumbers.length
          ? `<div class="archive-review-groups">
              ${topNumbers
                .map((item) => `
                  <button class="archive-number-review-button" type="button" data-phone="${escapeHtml(item.phone_number || "")}">
                    <strong>${escapeHtml(archiveItemLabel(item.item_type))} · ${escapeHtml(item.phone_number || "(blank)")}</strong>
                    <span>${formatNumber(item.count)} items · ${formatNumber(item.reviewed_count || 0)} reviewed · ${escapeHtml(labelize(item.classification || ""))}</span>
                    <small>${escapeHtml([formatDate(item.first_at), formatDate(item.last_at)].filter(Boolean).join(" to "))}</small>
                  </button>
                `)
                .join("")}
            </div>`
          : ""
      }
    </div>
  `;
}

function archiveReviewTriagePanel(triage, activeTriageLane = "") {
  if (!triage?.total) return "";
  const lanes = triage.lane_counts || [];
  const statuses = triage.suggested_status_counts || [];
  const topGroups = triage.top_groups || [];
  const statusCount = (value) => statuses.find((item) => item.suggested_status === value)?.count || 0;
  return `
    <div class="band archive-triage-panel">
      <div class="band-header">
        <div>
          <h3>${escapeHtml(triage.title || "Archive Review Triage")}</h3>
          <p>${escapeHtml(triage.message || "Suggested review lanes for unlinked calls/texts.")}</p>
        </div>
        <span class="pill ${Number(triage.unreviewed || 0) ? "gold" : "green"}">${formatNumber(triage.unreviewed || 0)} unreviewed</span>
      </div>
      <div class="archive-decision-body">
        <div class="archive-decision-metrics archive-triage-metrics">
          <span><strong>${formatNumber(triage.total || 0)}</strong>Total</span>
          <span><strong>${formatNumber(statusCount("archive_only"))}</strong>Likely archive-only</span>
          <span><strong>${formatNumber(statusCount("needs_lookup"))}</strong>Needs lookup</span>
          <span><strong>${formatNumber(statusCount("ready_to_link"))}</strong>Ready candidates</span>
        </div>
        <div class="archive-decision-actions">
          ${triage.report ? `<a class="text-button action-link" href="${escapeHtml(triage.report)}" target="_blank" rel="noreferrer">Open Triage</a>` : ""}
          ${triage.export_url ? `<a class="text-button action-link" href="${escapeHtml(triage.export_url)}">Triage CSV</a>` : ""}
          <button class="text-button archive-review-filter-button" type="button" data-review-status="unreviewed">Open Unreviewed</button>
        </div>
      </div>
      ${
        lanes.length
          ? `<div class="archive-triage-lanes">
              ${lanes
                .filter((lane) => Number(lane.count || 0) > 0)
                .map((lane) => `
                  <button class="archive-review-mini-row archive-triage-filter-button ${activeTriageLane === lane.triage_lane ? "active" : ""}" type="button" data-triage-lane="${escapeHtml(lane.triage_lane || "")}">
                    <strong>${escapeHtml(lane.triage_lane_label || "")}</strong>
                    <span>${formatNumber(lane.count || 0)} items · ${escapeHtml(lane.suggested_action || "")}</span>
                  </button>
                `)
                .join("")}
            </div>`
          : ""
      }
      ${
        topGroups.length
          ? `<div class="archive-review-groups">
              ${topGroups.slice(0, 8)
                .map((group) => `
                  <button class="archive-number-review-button" type="button" data-phone="${escapeHtml(group.phone_number || "")}" data-triage-lane="${escapeHtml(group.triage_lane || "")}">
                    <strong>${escapeHtml(group.triage_lane_label || "")} · ${escapeHtml(group.phone_number || "(blank)")}</strong>
                    <span>${formatNumber(group.count || 0)} items · ${escapeHtml(group.suggested_status_label || "")} · ${escapeHtml(labelize(group.classification || ""))}</span>
                    <small>${escapeHtml(group.reason || "")}</small>
                  </button>
                `)
                .join("")}
            </div>`
          : ""
      }
    </div>
  `;
}

function archiveSummaryCards(data) {
  const cards = (data.item_type_counts || []).slice(0, 5);
  if (!cards.length) return `<div class="signal"><strong>0</strong><span>Archive Items</span></div>`;
  return cards
    .map((item) => `<div class="signal"><strong>${formatNumber(item.count)}</strong><span>${escapeHtml(archiveItemLabel(item.value))}</span></div>`)
    .join("");
}

function archiveAssociationCoveragePanel(association) {
  const summary = association?.summary || {};
  if (!Object.keys(summary).length) return "";
  const exactCandidates = Number(summary.exact_phone_candidates || 0);
  return `
    <div class="band archive-association-panel">
      <div class="band-header">
        <div>
          <h3>Association Coverage</h3>
          <p>${escapeHtml(summary.reason || "Archive items are preserved locally with their current record associations.")}</p>
        </div>
        <span class="pill ${exactCandidates ? "gold" : "green"}">${exactCandidates ? `${formatNumber(exactCandidates)} phone candidates` : "No auto-link candidates"}</span>
      </div>
      <div class="archive-decision-body">
        <div class="archive-decision-metrics archive-association-metrics">
          <span><strong>${formatNumber(summary.link_coverage_percent || 0)}%</strong>Linked coverage</span>
          <span><strong>${formatNumber(summary.linked_archive_items || 0)}</strong>Linked archive</span>
          <span><strong>${formatNumber(summary.unlinked_archive_items || 0)}</strong>Unlinked archive</span>
          <span><strong>${formatNumber(summary.linked_documents || 0)}/${formatNumber(summary.document_total || 0)}</strong>Document files</span>
          <span><strong>${formatNumber(summary.unlinked_call_recording_urls || 0)}</strong>Recording URLs</span>
          <span><strong>${formatNumber(summary.unlinked_unreviewed_call_texts || 0)}</strong>Unreviewed calls/texts</span>
        </div>
        <div class="archive-decision-actions">
          <button class="text-button archive-review-filter-button" type="button" data-review-status="unreviewed">Open Unreviewed</button>
          <a class="text-button action-link" href="${escapeHtml(association.report || "/reports/archive_association_audit.md")}" target="_blank" rel="noreferrer">Audit</a>
          <a class="text-button action-link" href="${escapeHtml(association.export_url || "/api/export?type=archive_association_audit")}">CSV</a>
        </div>
      </div>
      ${archiveAssociationMiniList(association)}
    </div>
  `;
}

function archiveRow(item) {
  const recordLabel = item.record_type && item.record_id ? `${labelize(item.record_type)} #${item.record_id}` : "Unlinked";
  const recordButton =
    item.record_type && item.record_id
      ? `<button class="record-button" data-type="${escapeHtml(item.record_type)}" data-id="${item.record_id}">${escapeHtml(item.record_name || recordLabel)}</button>`
      : `<span class="muted">Unlinked</span>`;
  const itemLink = item.file_url
    ? `<a href="${escapeHtml(item.file_url)}" target="_blank" rel="noreferrer">${escapeHtml(item.title || item.label)}</a>`
    : item.url
      ? `<a href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${escapeHtml(item.title || item.label)}</a>`
      : `<strong>${escapeHtml(item.title || item.label)}</strong>`;
  return `
    <tr>
      <td><span class="pill">${escapeHtml(item.label || archiveItemLabel(item.item_type))}</span></td>
      <td>
        ${recordButton}
        <div class="muted">${escapeHtml(recordLabel)}</div>
      </td>
      <td>
        ${itemLink}
        <div class="muted archive-context">${escapeHtml([item.body, item.phone_number, item.size_label].filter(Boolean).join(" · "))}</div>
      </td>
      <td class="muted">${formatDate(item.occurred_at)}</td>
      <td class="muted">${escapeHtml(item.user_name || "")}</td>
      <td>${archiveReviewPill(item)}</td>
      <td><button class="text-button archive-detail-button" type="button" data-id="${item.id}">Inspect</button></td>
    </tr>
  `;
}

function archiveReviewPill(item) {
  const status = item.review_status || "unreviewed";
  const className = status === "archive_only" ? "green" : status === "ready_to_link" ? "coral" : "gold";
  const triageHint = item.triage_lane_label
    ? `<div class="muted archive-triage-row-hint">${escapeHtml(item.triage_lane_label)} · ${escapeHtml(item.suggested_status_label || "")}</div>`
    : "";
  return `<span class="pill ${className}">${escapeHtml(archiveReviewStatusLabel(status))}</span>${triageHint}`;
}

function archiveItemLabel(itemType) {
  return {
    call: "Calls",
    text_message: "Text Messages",
    document: "Documents",
    order: "Orders",
    lead_conversion: "Lead Conversions",
  }[itemType] || labelize(itemType || "Archive");
}

async function renderCustomFields() {
  setStatus("Loading custom fields");
  const params = new URLSearchParams({
    page: String(state.customFieldPage),
    page_size: "50",
    q: state.customFieldQ,
    record_type: state.customFieldRecordType,
  });
  const [data, savedViewData] = await Promise.all([
    fetchJson(`/api/custom_fields?${params.toString()}`),
    fetchJson("/api/saved_views?type=custom_fields"),
  ]);
  const savedViews = savedViewData.views || [];
  if (state.customFieldSavedViewId && !savedViews.some((view) => String(view.id) === String(state.customFieldSavedViewId))) {
    state.customFieldSavedViewId = "";
  }
  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));
  const exportSummaryParams = new URLSearchParams({
    type: "custom_field_summary",
    q: state.customFieldQ,
    record_type: state.customFieldRecordType,
  });
  const customFieldRecordTypeCounts = Object.fromEntries((data.record_type_counts || []).map((item) => [item.value, item.count]));
  els.customFields.innerHTML = `
    <div class="section-header">
      <div>
        <h2>Custom Fields</h2>
        <p>${formatNumber(data.total)} field groups</p>
      </div>
      <div class="header-actions">
        <a class="text-button action-link" href="/reports/application_profile_editability_review.md" target="_blank" rel="noreferrer">Application Profile Report</a>
        <a class="text-button action-link" href="/reports/custom_field_promotion_recommendations.md" target="_blank" rel="noreferrer">Promotion Report</a>
        <a class="text-button action-link" href="/api/export?type=application_profiles">Export Profiles</a>
        <a class="text-button action-link" href="/api/export?${escapeHtml(exportSummaryParams.toString())}">Export Summary</a>
        <a class="text-button action-link" href="/api/export?type=custom_field_values">Export Values</a>
      </div>
    </div>
    ${applicationProfileDecisionPanel(data.application_profile_decision)}
    <div class="table-tools">
      <input id="customFieldSearch" type="search" value="${escapeHtml(state.customFieldQ)}" placeholder="Filter custom fields">
      <select id="customFieldRecordTypeFilter" aria-label="Custom field record type">
        ${customFieldRecordTypeOptions()
          .map(([value, label]) => {
            const count = value ? customFieldRecordTypeCounts[value] || 0 : null;
            return `<option value="${escapeHtml(value)}" ${state.customFieldRecordType === value ? "selected" : ""}>${escapeHtml(count === null ? label : `${label} (${formatNumber(count)})`)}</option>`;
          })
          .join("")}
      </select>
      ${customFieldSavedViewControls(savedViews)}
      <div class="pager">
        <button class="icon-button" id="prevCustomFieldPage" title="Previous page" ${state.customFieldPage <= 1 ? "disabled" : ""}>‹</button>
        <span class="muted">Page ${state.customFieldPage} of ${totalPages}</span>
        <button class="icon-button" id="nextCustomFieldPage" title="Next page" ${state.customFieldPage >= totalPages ? "disabled" : ""}>›</button>
      </div>
    </div>
    ${
      data.fields.length
        ? `<table class="data-table custom-field-table">
            <thead>
              <tr>
                <th>Field</th>
                <th>Type</th>
                <th>Records</th>
                <th>Unique</th>
                <th>Samples</th>
              </tr>
            </thead>
            <tbody>
              ${data.fields
                .map((field) => `
                  <tr>
                    <td>
                      <button class="record-button custom-field-button" data-record-type="${escapeHtml(field.record_type)}" data-field-name="${escapeHtml(field.field_name)}">
                        ${escapeHtml(field.field_name)}
                      </button>
                    </td>
                    <td><span class="pill">${escapeHtml(labelize(field.record_type))}</span></td>
                    <td>${formatNumber(field.record_count)}</td>
                    <td>${formatNumber(field.distinct_values)}</td>
                    <td>${sampleValues(field.sample_values || [])}</td>
                  </tr>
                `)
                .join("")}
            </tbody>
          </table>`
        : `<div class="empty-state"><h3>No custom fields</h3><p>No custom fields matched this filter.</p></div>`
    }
  `;
  const customFieldSavedView = document.querySelector("#customFieldSavedView");
  customFieldSavedView.addEventListener("change", () => {
    const selectedId = customFieldSavedView.value;
    state.customFieldSavedViewId = selectedId;
    if (!selectedId) {
      renderCustomFields();
      return;
    }
    const view = savedViews.find((item) => String(item.id) === String(selectedId));
    if (view) {
      applyCustomFieldSettings(view.settings || {});
      state.customFieldSavedViewId = selectedId;
    }
    renderCustomFields();
  });
  document.querySelector("#saveCustomFieldViewButton").addEventListener("click", async () => {
    const name = window.prompt("Save this custom-field view as");
    if (!name?.trim()) return;
    setStatus("Saving view");
    const saved = await postJson("/api/save_view", {
      type: "custom_fields",
      name: name.trim(),
      settings: currentCustomFieldSettings(),
    });
    state.customFieldSavedViewId = saved.view?.id ? String(saved.view.id) : "";
    await renderCustomFields();
    setStatus("View saved");
  });
  document.querySelector("#deleteCustomFieldViewButton").addEventListener("click", async () => {
    const viewId = state.customFieldSavedViewId;
    if (!viewId) return;
    const ok = window.confirm("Delete this saved custom-field view?");
    if (!ok) return;
    setStatus("Deleting view");
    await postJson("/api/delete_view", { id: Number(viewId) });
    state.customFieldSavedViewId = "";
    await renderCustomFields();
    setStatus("View deleted");
  });
  document.querySelector("#resetCustomFieldViewButton").addEventListener("click", () => {
    resetCustomFieldView();
    renderCustomFields();
  });
  const customFieldSearch = document.querySelector("#customFieldSearch");
  customFieldSearch.addEventListener("input", () => {
    window.clearTimeout(state.debounce);
    state.debounce = window.setTimeout(() => {
      clearSelectedCustomFieldSavedView();
      state.customFieldQ = customFieldSearch.value.trim();
      state.customFieldPage = 1;
      renderCustomFields();
    }, 220);
  });
  document.querySelector("#customFieldRecordTypeFilter").addEventListener("change", (event) => {
    clearSelectedCustomFieldSavedView();
    state.customFieldRecordType = event.target.value;
    state.customFieldPage = 1;
    renderCustomFields();
  });
  document.querySelector("#prevCustomFieldPage").addEventListener("click", () => {
    state.customFieldPage = Math.max(1, state.customFieldPage - 1);
    renderCustomFields();
  });
  document.querySelector("#nextCustomFieldPage").addEventListener("click", () => {
    state.customFieldPage += 1;
    renderCustomFields();
  });
  wireNextAction(els.customFields);
  wireCustomFieldButtons(els.customFields);
  setStatus("Ready");
}

function applicationProfileDecisionPanel(summary) {
  if (!summary) return "";
  const editableFields = summary.editable_after_cleanup_fields || [];
  const historyFields = summary.read_only_history_fields || [];
  return `
    <div class="band archive-decision-panel profile-decision-panel">
      <div class="band-header">
        <div>
          <h3>Application Profile Evidence</h3>
          <p>${escapeHtml(summary.reason || "")}</p>
        </div>
        <span class="pill green">${escapeHtml(summary.recommendation || "Review")}</span>
      </div>
      <div class="archive-decision-body">
        <div class="archive-decision-metrics profile-decision-metrics">
          <span><strong>${formatNumber(summary.lead_profile_records || 0)}</strong>Lead profiles</span>
          <span><strong>${formatNumber(summary.person_profile_records || 0)}</strong>Person profiles</span>
          <span><strong>${formatNumber(summary.value_rows || 0)}</strong>Profile values</span>
          <span><strong>${formatNumber(editableFields.length)}</strong>Editable later</span>
          <span><strong>${formatNumber(historyFields.length)}</strong>History fields</span>
          <span><strong>${formatNumber(summary.cleanup_conflict_groups || 0)}</strong>Conflict groups</span>
          <span><strong>${formatNumber(summary.cleanup_fill_gap_groups || 0)}</strong>Fill-gap groups</span>
        </div>
        <div class="archive-decision-actions">
          <button class="text-button next-action-decision" type="button" data-key="application_profile_editability">Open Decision</button>
          <button class="text-button next-action-fill" type="button" data-key="application_profile_editability">Fill Recommended</button>
          <a class="text-button action-link" href="${escapeHtml(summary.report || "/reports/application_profile_editability_review.md")}" target="_blank" rel="noreferrer">Open Report</a>
        </div>
      </div>
      <div class="archive-top-numbers">
        ${editableFields.map((field) => `<span>Editable later · ${escapeHtml(field)}</span>`).join("")}
        ${historyFields.slice(0, 4).map((field) => `<span>Read-only history · ${escapeHtml(field)}</span>`).join("")}
      </div>
    </div>
  `;
}

function sampleValues(values) {
  if (!values.length) return `<span class="muted">No values</span>`;
  return `
    <div class="sample-list">
      ${values
        .map((item) => `<span class="tag" title="${escapeHtml(item.field_value || "")}">${escapeHtml(item.field_value || "Not saved")} <strong>${formatNumber(item.count)}</strong></span>`)
        .join("")}
    </div>
  `;
}

function statusLabel(status) {
  return {
    open: "Open",
    overdue: "Overdue",
    due_soon: "Due Soon",
    completed: "Completed",
    all: "All",
  }[status] || "Open";
}

function taskTable(tasks, compact) {
  if (!tasks.length) {
    return `<div class="empty-state"><h3>No tasks</h3><p>No follow-ups in this view.</p></div>`;
  }
  return `
    <table class="data-table task-table">
      <thead>
        <tr>
          <th>Task</th>
          <th>Record</th>
          <th>Due</th>
          <th>Source</th>
          <th>Status</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        ${tasks
          .map((task) => `
            <tr class="${compact ? "" : "task-edit-card task-table-edit-row"}">
              <td>${
                compact
                  ? escapeHtml(task.content || "")
                  : `<textarea class="task-edit-content task-table-textarea" rows="2">${escapeHtml(task.content || "")}</textarea>`
              }</td>
              <td>
                ${task.record_id && detailTypeSupported(task.record_type)
                  ? `<button class="record-button" data-type="${escapeHtml(task.record_type)}" data-id="${task.record_id}">${escapeHtml(task.record_name || `${task.record_type} #${task.record_id}`)}</button>`
                  : escapeHtml(task.record_name || task.record_type || "")}
              </td>
              <td>${
                compact
                  ? `<span class="muted">${task.due_date ? formatDate(task.due_date) : ""}</span>`
                  : `<input class="task-edit-due task-table-due" type="date" value="${escapeHtml(taskDateInputValue(task.due_date))}">`
              }</td>
              <td><span class="pill ${task.task_source === "local" ? "green" : ""}">${escapeHtml(task.task_source_label || "Imported")}</span></td>
              <td><span class="pill ${task.completed ? "" : "gold"}">${task.completed ? "Completed" : "Open"}</span></td>
              <td>
                <div class="task-table-actions">
                  ${compact ? "" : `<button class="text-button save-task-button" data-id="${task.source_id}">Save</button>`}
                  ${compact ? "" : taskLocalCopyButton(task)}
                  ${taskActionButton(task)}
                </div>
              </td>
            </tr>
          `)
          .join("")}
      </tbody>
    </table>
  `;
}

function taskActionButton(task) {
  const completed = Boolean(task.completed);
  const label = completed ? "Reopen" : "Complete";
  return `<button class="text-button complete-task-button" data-id="${task.source_id}" data-completed="${completed ? "false" : "true"}">${label}</button>`;
}

function taskLocalCopyButton(task) {
  if (task.completed || task.task_source !== "imported" || !task.record_id || !detailTypeSupported(task.record_type)) return "";
  return `<button class="text-button copy-imported-task-button" data-id="${task.source_id}" data-task="${escapeHtml(task.content || "")}">Copy Local</button>`;
}

function taskDateInputValue(value) {
  return value ? String(value).slice(0, 10) : "";
}

function detailTags(tags) {
  return `
    <div class="detail-section">
      <div class="inline-header">
        <h3>Tags</h3>
        <button class="text-button" id="saveTagsButton">Save</button>
      </div>
      <div class="tag-list">${tags.length ? tags.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("") : `<span class="muted">No tags saved.</span>`}</div>
      <textarea id="tagEditor" class="note-input compact-input" rows="2">${escapeHtml(tags.join(", "))}</textarea>
    </div>
  `;
}

function addressSection(detail) {
  const addresses = detail.addresses || [];
  if (!detail.address_fields_available) return "";
  const editable = detail.address_editable !== false;
  return `
    <div class="detail-section">
      <div class="inline-header">
        <h3>Address</h3>
        ${editable ? `<button class="text-button" id="saveAddressesButton">Save</button>` : ""}
      </div>
      ${detail.address_note ? `<div class="muted detail-note">${escapeHtml(detail.address_note)}</div>` : ""}
      <form id="addressForm" class="address-form">
        ${addresses.length ? addresses.map((address) => addressBlock(address, editable)).join("") : `<div class="muted">No address saved.</div>`}
      </form>
    </div>
  `;
}

function addressBlock(address, editable) {
  const rows = [
    ["Street", address.line1],
    ["Street 2", address.line2],
    ["City", address.city],
    ["State", address.state],
    ["Postal Code", address.postal_code],
    ["Country", address.country],
  ];
  return `
    <div class="address-card" data-address-key="${escapeHtml(address.address_key || "address")}">
      <div class="address-card-header">
        <strong>${escapeHtml(address.label || "Address")}</strong>
        <span class="muted">${escapeHtml(address.source === "local" ? "Local" : "Zendesk")}</span>
      </div>
      <div class="address-fields">
        ${rows
          .map(([label, value]) => `
            <label>
              <span>${escapeHtml(label)}</span>
              <input data-field="${escapeHtml(addressFieldName(label))}" value="${escapeHtml(value || "")}" ${editable ? "" : "readonly"}>
            </label>
          `)
          .join("")}
      </div>
    </div>
  `;
}

function addressFieldName(label) {
  return {
    Street: "line1",
    "Street 2": "line2",
    City: "city",
    State: "state",
    "Postal Code": "postal_code",
    Country: "country",
  }[label];
}

function keyValues(record) {
  const skip = new Set([
    "source_id",
    "kind",
    "name",
    "first_name",
    "last_name",
    "normalized_email",
    "stage_id",
    "pipeline_id",
    "contact_id",
    "organization_id",
    "owner_user_id",
    "owner_name",
    "owner_email",
  ]);
  const rows = Object.entries(record)
    .filter(([key, value]) => !skip.has(key) && value !== null && value !== "")
    .slice(0, 18);
  if (!rows.length) return "";
  return `
    <div class="detail-section">
      <h3>Fields</h3>
      <dl class="kv">
        ${rows
          .map(([key, value]) => `
            <dt>${escapeHtml(labelize(key))}</dt>
            <dd>${escapeHtml(key.endsWith("_at") || key.endsWith("_date") ? formatDate(value) : value)}</dd>
          `)
          .join("")}
      </dl>
    </div>
  `;
}

function ownerSection(owner) {
  if (!owner) return "";
  return `
    <div class="detail-section">
      <h3>Owner</h3>
      <dl class="kv">
        <dt>Name</dt><dd>${escapeHtml(owner.name || `Owner #${owner.source_id}`)}</dd>
        ${owner.email ? `<dt>Email</dt><dd>${escapeHtml(owner.email)}</dd>` : ""}
        ${owner.role ? `<dt>Role</dt><dd>${escapeHtml(labelize(owner.role))}</dd>` : ""}
        ${owner.status ? `<dt>Status</dt><dd>${escapeHtml(labelize(owner.status))}</dd>` : ""}
      </dl>
    </div>
  `;
}

function applicationProfile(fields) {
  if (!fields.length) return "";
  const longFields = new Set(["Skills", "Success Is", "Why Waiting", "Why a Fit"]);
  const compactFields = fields.filter((field) => !longFields.has(field.field_name));
  const narrativeFields = fields.filter((field) => longFields.has(field.field_name));
  return `
    <div class="detail-section application-profile">
      <h3>Application Profile</h3>
      ${
        compactFields.length
          ? `<dl class="app-profile-grid">
              ${compactFields
                .map((field) => `
                  <dt>${escapeHtml(field.field_name)}</dt>
                  <dd>${escapeHtml(formatProfileValue(field))}</dd>
                `)
                .join("")}
            </dl>`
          : ""
      }
      ${
        narrativeFields.length
          ? `<div class="app-profile-notes">
              ${narrativeFields
                .map((field) => `
                  <div>
                    <strong>${escapeHtml(field.field_name)}</strong>
                    <p>${escapeHtml(field.field_value)}</p>
                  </div>
                `)
                .join("")}
            </div>`
          : ""
      }
    </div>
  `;
}

function formatProfileValue(field) {
  if (field.field_name === "Date Created") return formatDate(field.field_value);
  return field.field_value;
}

function customFields(fields, applicationFields = []) {
  const promoted = new Set(applicationFields.map((field) => field.field_name));
  const remaining = fields.filter((field) => !promoted.has(field.field_name));
  if (!remaining.length) return "";
  return `
    <div class="detail-section">
      <h3>Custom Fields</h3>
      <dl class="kv">
        ${remaining
          .map((field) => `
            <dt>${escapeHtml(field.field_name)}</dt>
            <dd>${escapeHtml(field.field_value)}</dd>
          `)
          .join("")}
      </dl>
    </div>
  `;
}

function linkedResources(resources) {
  if (!resources.length) return "";
  return `
    <div class="detail-section linked-resources">
      <div class="inline-header">
        <h3>Linked Resources</h3>
        <span class="muted">${formatNumber(resources.length)} links</span>
      </div>
      <div class="linked-resource-list">
        ${resources
          .map((resource) => `
            <a class="linked-resource" href="${escapeHtml(resource.url)}" target="_blank" rel="noreferrer">
              <strong>${escapeHtml(resource.kind || "Web Link")}</strong>
              <span>${escapeHtml(resource.source_label || labelize(resource.source_type || "source"))}</span>
              ${resource.context ? `<small>${escapeHtml(resource.context)}</small>` : ""}
            </a>
          `)
          .join("")}
      </div>
    </div>
  `;
}

function archiveItems(items) {
  if (!items.length) return "";
  return `
    <div class="detail-section archive-items">
      <div class="inline-header">
        <h3>Archive</h3>
        <span class="muted">${formatNumber(items.length)} items</span>
      </div>
      <div class="archive-item-list">
        ${items
          .map((item) => {
            const title = item.file_url
              ? `<a href="${escapeHtml(item.file_url)}" target="_blank" rel="noreferrer">${escapeHtml(item.title || item.label)}</a>`
              : item.url
                ? `<a href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${escapeHtml(item.title || item.label)}</a>`
                : `<strong>${escapeHtml(item.title || item.label)}</strong>`;
            return `
              <div class="archive-item">
                <span class="pill">${escapeHtml(item.label || archiveItemLabel(item.item_type))}</span>
                ${title}
                <small>${escapeHtml([formatDate(item.occurred_at), item.body, item.phone_number, item.size_label].filter(Boolean).join(" · "))}</small>
              </div>
            `;
          })
          .join("")}
      </div>
    </div>
  `;
}

function activitySection(activity) {
  if (!activity.length) return "";
  return `
    <div class="detail-section">
      <h3>Activity</h3>
      <div class="activity-list">
        ${activity.map(activityItem).join("")}
      </div>
    </div>
  `;
}

function activityItem(item) {
  const target = activityRecordLink(item, state.currentDetail);
  return `
    <div class="activity-item">
      <div class="activity-dot"></div>
      <div>
        <strong>${escapeHtml(labelize(item.activity_type || "activity"))}</strong>
        <p>${escapeHtml(item.summary || "")}</p>
        <div class="muted activity-meta">
          <span>${formatDate(item.occurred_at)}</span>
          ${target ? `<span aria-hidden="true">·</span>${target}` : ""}
        </div>
      </div>
    </div>
  `;
}

function activityRecordLink(item, currentDetail) {
  const recordType = item.record_type || "";
  const recordId = Number(item.record_id || 0);
  const linked = recordId && detailTypeSupported(recordType);
  const label = item.record_name || (linked ? `${labelize(recordType)} #${recordId}` : recordType);
  if (!label) return "";
  const sameRecord =
    currentDetail &&
    currentDetail.type === recordType &&
    Number(currentDetail.record?.source_id || 0) === recordId;
  if (!linked || sameRecord) return `<span>${escapeHtml(label)}</span>`;
  return `
    <button class="text-button record-button activity-target" data-type="${escapeHtml(recordType)}" data-id="${recordId}">
      ${escapeHtml(label)}
    </button>
  `;
}

function linkSection(title, records, type) {
  return `
    <div class="detail-section">
      <h3>${escapeHtml(title)}</h3>
      <div class="mini-list">
        ${records
          .map((record) => `
            <button class="text-button record-button" data-type="${type}" data-id="${record.source_id}">
              ${escapeHtml(record.name || "(blank)")}
            </button>
          `)
          .join("")}
      </div>
    </div>
  `;
}

function notesSection(notes) {
  if (!notes.length) return "";
  return `
    <div class="detail-section">
      <h3>Notes</h3>
      ${notes
        .map((note) => `
          <div class="note">
            ${
              note.editable
                ? `<textarea class="note-edit-input note-input compact-input" rows="4">${escapeHtml(note.content || "")}</textarea>`
                : `<p>${escapeHtml(note.content || "")}</p>`
            }
            <div class="task-line">
              <div class="muted">${formatDate(note.created_at)}${note.updated_at && note.updated_at !== note.created_at ? ` · Updated ${formatDate(note.updated_at)}` : ""}</div>
              ${note.editable ? `<button class="text-button save-note-button" data-id="${note.source_id}">Save</button>` : `<span class="pill">Imported</span>`}
            </div>
          </div>
        `)
        .join("")}
    </div>
  `;
}

function tasksSection(tasks) {
  if (!tasks.length) return "";
  return `
    <div class="detail-section">
      <h3>Tasks</h3>
      ${tasks
        .map((task) => `
          <div class="note task-edit-card">
            <textarea class="task-edit-content note-input compact-input" rows="3">${escapeHtml(task.content || "")}</textarea>
            <div class="task-edit-row">
              <label>
                <span>Due</span>
                <input class="task-edit-due" type="date" value="${escapeHtml(taskDateInputValue(task.due_date))}">
              </label>
              <div class="task-line">
                <div class="muted">${task.completed ? "Completed" : "Open"} · ${escapeHtml(task.task_source_label || "Imported")} ${task.due_date ? `· ${formatDate(task.due_date)}` : ""}</div>
                <button class="text-button save-task-button" data-id="${task.source_id}">Save</button>
                ${taskActionButton(task)}
              </div>
            </div>
          </div>
        `)
        .join("")}
    </div>
  `;
}

function labelize(key) {
  return key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function cleanupStatusLabel(status) {
  return cleanupStatuses.find((item) => item.status === status)?.label || labelize(status || "open");
}

function cleanupDecisionLabel(decision) {
  return cleanupDecisionOptions.find((item) => item.value === decision)?.label || labelize(decision || "No decision");
}

function cleanupDecisionBadge(decision) {
  if (!decision) return `<span class="muted">No decision</span>`;
  const decisionClass = {
    needs_review: "gold",
    merge_later: "gold",
    keep_separate: "",
    already_handled: "",
    false_positive: "coral",
  }[decision] || "";
  return `<span class="pill ${decisionClass}">${escapeHtml(cleanupDecisionLabel(decision))}</span>`;
}

function cleanupGroupDecisionSummary(decision) {
  if (!decision) return `<span class="muted">No decision</span>`;
  return `
    <div class="cleanup-decision-summary">
      ${cleanupDecisionBadge(decision.decision)}
      ${decision.note ? `<small>${escapeHtml(decision.note)}</small>` : ""}
    </div>
  `;
}

function cleanupActionProgress(status) {
  return {
    resolved: "Resolving flag",
    ignored: "Ignoring flag",
    open: "Reopening flag",
  }[status] || "Updating flag";
}

function cleanupActionComplete(status) {
  return {
    resolved: "Flag resolved",
    ignored: "Flag ignored",
    open: "Flag reopened",
  }[status] || "Flag updated";
}

function cleanupActionNote(status, source) {
  const place = source === "group" ? "cleanup group" : "cleanup queue";
  return {
    resolved: `Reviewed from ${place}`,
    ignored: `Ignored from ${place}`,
    open: `Reopened from ${place}`,
  }[status] || `Updated from ${place}`;
}

function cleanupPromptNote(status, source, subject = "") {
  const fallback = cleanupActionNote(status, source);
  const action = cleanupStatusLabel(status).toLowerCase();
  const context = subject ? ` for ${subject}` : "";
  const note = window.prompt(`Optional cleanup note to ${action}${context}:`, fallback);
  if (note === null) return null;
  return note.trim() || fallback;
}

function cleanupResolutionNote(flag) {
  return flag.resolution_note ? `<p class="cleanup-resolution-note">Note: ${escapeHtml(flag.resolution_note)}</p>` : "";
}

function cleanupDecisionSection(detail) {
  const decision = detail.decision || {};
  const selectedDecision = decision.decision || "needs_review";
  return `
    <div class="detail-section cleanup-decision-panel">
      <div class="inline-header">
        <h3>Cleanup Decision</h3>
        ${cleanupDecisionBadge(decision.decision)}
      </div>
      <div class="cleanup-decision-form">
        <label>
          Decision
          <select id="cleanupDecisionSelect">
            ${cleanupDecisionOptions
              .map((item) => `<option value="${item.value}" ${selectedDecision === item.value ? "selected" : ""}>${escapeHtml(item.label)}</option>`)
              .join("")}
          </select>
        </label>
        <label>
          Note
          <textarea id="cleanupDecisionNote" rows="3">${escapeHtml(decision.note || "")}</textarea>
        </label>
        <div class="cleanup-decision-actions">
          <button class="text-button" id="saveCleanupDecisionButton">Save Decision</button>
          <button class="text-button" id="saveCleanupDecisionNextButton">Save & Next</button>
        </div>
      </div>
      ${
        decision.updated_at
          ? `<p class="muted">Saved ${escapeHtml(formatDate(decision.updated_at))}</p>`
          : ""
      }
    </div>
  `;
}

function cleanupFlagActions(flag) {
  const actions = flag.status === "open" ? [["resolved", "Resolve"], ["ignored", "Ignore"]] : [["open", "Reopen"]];
  return `
    <div class="review-actions">
      ${actions
        .map(([status, label]) => `<button class="text-button cleanup-flag-action" data-id="${flag.id}" data-status="${status}">${label}</button>`)
        .join("")}
    </div>
  `;
}

function cleanupGroupActions(status) {
  const actions = status === "open" ? [["resolved", "Resolve"], ["ignored", "Ignore"]] : [["open", "Reopen"]];
  return `
    <div class="review-actions">
      ${actions
        .map(([nextStatus, label]) => `<button class="text-button cleanup-group-status-button" data-status="${nextStatus}">${label}</button>`)
        .join("")}
    </div>
  `;
}

function cleanupPriorityPill(priority) {
  const label = priority || "Review";
  const priorityClass = label === "High" ? "coral" : label === "Medium" ? "gold" : "";
  return `<span class="pill ${priorityClass}">${escapeHtml(label)}</span>`;
}

function cleanupPolicyLaneLabel(lane) {
  return cleanupPolicyLanes.find((item) => item.value === lane)?.label || labelize(lane || "No lane");
}

function cleanupPolicyLaneBadge(policyLane) {
  const lane = policyLane?.lane || policyLane;
  if (!lane) return `<span class="muted">No lane</span>`;
  const laneClass = {
    policy_review_overlap: "coral",
    priority_review: "coral",
    conflict_heavy_review: "gold",
    multi_record_review: "gold",
    short_guided_review: "",
    tag_batch_candidate: "green",
  }[lane] || "";
  return `<span class="pill ${laneClass}">${escapeHtml(policyLane?.label || cleanupPolicyLaneLabel(lane))}</span>`;
}

function duplicateTagDecisionPanel(summary) {
  if (!summary) return "";
  const priority = summary.priority_counts || {};
  const active = state.cleanupGroupType === "duplicate_tags" && state.cleanupPolicyLane === "tag_batch_candidate";
  return `
    <div class="band archive-decision-panel tag-decision-panel ${active ? "active" : ""}">
      <div class="band-header">
        <div>
          <h3>Duplicate Tag Evidence</h3>
          <p>${escapeHtml(summary.reason || "")}</p>
        </div>
        <span class="pill green">${escapeHtml(summary.recommendation || "Review")}</span>
      </div>
      <div class="archive-decision-body">
        <div class="archive-decision-metrics tag-decision-metrics">
          <span><strong>${formatNumber(summary.open_groups || 0)}</strong>Open groups</span>
          <span><strong>${formatNumber(summary.affected_assignments || 0)}</strong>Assignments</span>
          <span><strong>${formatNumber(summary.definition_count || 0)}</strong>Definitions</span>
          <span><strong>${formatNumber(priority.Medium || 0)}</strong>Medium</span>
          <span><strong>${formatNumber(priority.Low || 0)}</strong>Low</span>
          <span><strong>${formatNumber(summary.exact_alias_groups || 0)}</strong>Exact aliases</span>
          <span><strong>${formatNumber(summary.cross_resource_same_alias_groups || 0)}</strong>Cross-resource</span>
          <span><strong>${formatNumber(summary.alias_drift_groups || 0)}</strong>Alias drift</span>
        </div>
        <div class="archive-decision-actions">
          <button class="text-button duplicate-tag-evidence-button" type="button">${active ? "Refresh Evidence Set" : "Show Tag Batch Candidates"}</button>
          <button class="text-button next-action-decision" type="button" data-key="duplicate_tag_policy">Open Decision</button>
          <button class="text-button next-action-fill" type="button" data-key="duplicate_tag_policy">Fill Recommended</button>
          <a class="text-button action-link" href="${escapeHtml(summary.report || "/reports/duplicate_tag_spot_check.md")}" target="_blank" rel="noreferrer">Open Report</a>
          <a class="text-button action-link" href="${escapeHtml(summary.export_url || "/api/export_cleanup_groups?type=duplicate_tags")}">Export Evidence</a>
        </div>
      </div>
      <div class="archive-top-numbers">
        <span>Recommended simulation · ${escapeHtml(labelize(summary.recommended_simulated_status || "waiting"))}</span>
        <span>${formatNumber(summary.recommended_simulated_groups || 0)} eligible groups</span>
        <span>${formatNumber(summary.recommended_simulated_records || 0)} eligible assignments</span>
        <span>Spot-check CSV ready</span>
      </div>
    </div>
  `;
}

function leadPersonOverlapDecisionPanel(summary) {
  if (!summary) return "";
  const active = state.cleanupGroupType === "lead_person_overlap" && state.cleanupPolicyLane === "policy_review_overlap";
  const topGroup = (summary.top_groups || [])[0];
  return `
    <div class="band archive-decision-panel overlap-decision-panel ${active ? "active" : ""}">
      <div class="band-header">
        <div>
          <h3>Lead/Person Overlap Evidence</h3>
          <p>${escapeHtml(summary.reason || "")}</p>
        </div>
        <span class="pill coral">${escapeHtml(summary.recommendation || "Review")}</span>
      </div>
      <div class="archive-decision-body">
        <div class="archive-decision-metrics overlap-decision-metrics">
          <span><strong>${formatNumber(summary.open_groups || 0)}</strong>Open groups</span>
          <span><strong>${formatNumber(summary.record_count || 0)}</strong>Records</span>
          <span><strong>${formatNumber(summary.people_count || 0)}</strong>People</span>
          <span><strong>${formatNumber(summary.lead_count || 0)}</strong>Leads</span>
          <span><strong>${formatNumber(summary.high_priority_groups || 0)}</strong>High priority</span>
          <span><strong>${formatNumber(summary.manual_review_fields || 0)}</strong>Manual fields</span>
          <span><strong>${formatNumber(summary.blank_field_suggestions || 0)}</strong>Blank fills</span>
          <span><strong>${formatNumber(summary.history_signals || 0)}</strong>History signals</span>
          <span><strong>${formatNumber(summary.person_keeper_drafts || 0)}</strong>Person keepers</span>
        </div>
        <div class="archive-decision-actions">
          <button class="text-button overlap-evidence-button" type="button">${active ? "Refresh Overlap Review" : "Show Overlap Review"}</button>
          <button class="text-button next-action-decision" type="button" data-key="lead_person_overlap_policy">Open Decision</button>
          <button class="text-button next-action-fill" type="button" data-key="lead_person_overlap_policy">Fill Recommended</button>
          <a class="text-button action-link" href="${escapeHtml(summary.report || "/reports/cleanup_merge_review_pack.md")}" target="_blank" rel="noreferrer">Open Report</a>
          <a class="text-button action-link" href="${escapeHtml(summary.export_url || "/api/export_cleanup_groups?type=lead_person_overlap")}">Export Evidence</a>
        </div>
      </div>
      <div class="archive-top-numbers">
        <span>Recommended simulation · ${escapeHtml(labelize(summary.recommended_simulated_status || "waiting"))}</span>
        <span>${formatNumber(summary.recommended_simulated_groups || 0)} eligible groups</span>
        <span>${formatNumber(summary.recommended_simulated_records || 0)} eligible records</span>
        <span>${formatNumber(summary.person_keeper_drafts || 0)} person draft keepers</span>
        ${topGroup ? `<span>Start with ${escapeHtml(topGroup.group_key || topGroup.draft_keeper || "first overlap")}</span>` : ""}
      </div>
    </div>
  `;
}

function mergeCleanupDecisionPanel(summary, options) {
  if (!summary) return "";
  const topGroup = (summary.top_groups || [])[0];
  const keeperCount = options.groupType === "duplicate_leads" ? summary.lead_keeper_drafts : summary.person_keeper_drafts;
  const active = state.cleanupGroupType === options.groupType && state.cleanupStatus === "open" && !state.cleanupPolicyLane;
  return `
    <div class="band archive-decision-panel merge-decision-panel ${active ? "active" : ""}">
      <div class="band-header">
        <div>
          <h3>${escapeHtml(options.title)}</h3>
          <p>${escapeHtml(summary.reason || "")}</p>
        </div>
        <span class="pill ${escapeHtml(options.pillClass || "gold")}">${escapeHtml(summary.recommendation || "Review")}</span>
      </div>
      <div class="archive-decision-body">
        <div class="archive-decision-metrics merge-decision-metrics">
          <span><strong>${formatNumber(summary.open_groups || 0)}</strong>Open groups</span>
          <span><strong>${formatNumber(summary.record_count || 0)}</strong>${escapeHtml(options.recordLabel || "Records")}</span>
          <span><strong>${formatNumber(summary.high_priority_groups || 0)}</strong>High priority</span>
          <span><strong>${formatNumber(summary.medium_priority_groups || 0)}</strong>Medium</span>
          <span><strong>${formatNumber(summary.manual_review_fields || 0)}</strong>Manual fields</span>
          <span><strong>${formatNumber(summary.blank_field_suggestions || 0)}</strong>Blank fills</span>
          <span><strong>${formatNumber(summary.history_signals || 0)}</strong>History signals</span>
          <span><strong>${formatNumber(summary.history_records || 0)}</strong>History records</span>
          <span><strong>${formatNumber(keeperCount || 0)}</strong>Draft keepers</span>
        </div>
        <div class="archive-decision-actions">
          <button class="text-button merge-evidence-button" type="button" data-type="${escapeHtml(options.groupType)}">${active ? escapeHtml(options.refreshLabel) : escapeHtml(options.showLabel)}</button>
          <button class="text-button next-action-decision" type="button" data-key="${escapeHtml(options.decisionKey)}">Open Decision</button>
          <button class="text-button next-action-fill" type="button" data-key="${escapeHtml(options.decisionKey)}">Fill Recommended</button>
          ${summary.worksheet_report ? `<a class="text-button action-link" href="${escapeHtml(summary.worksheet_report)}" target="_blank" rel="noreferrer">Open Worksheet</a>` : ""}
          ${summary.worksheet_export_url ? `<a class="text-button action-link" href="${escapeHtml(summary.worksheet_export_url)}">Worksheet CSV</a>` : ""}
          <a class="text-button action-link" href="${escapeHtml(summary.report || "/reports/cleanup_merge_review_pack.md")}" target="_blank" rel="noreferrer">Open Report</a>
          <a class="text-button action-link" href="${escapeHtml(summary.export_url || "/api/export_cleanup_groups")}">Export Evidence</a>
        </div>
      </div>
      <div class="archive-top-numbers">
        <span>Recommended simulation · ${escapeHtml(labelize(summary.recommended_simulated_status || "waiting"))}</span>
        <span>${formatNumber(summary.recommended_simulated_groups || 0)} eligible groups</span>
        <span>${formatNumber(summary.recommended_simulated_records || 0)} eligible records</span>
        ${topGroup ? `<span>Start with ${escapeHtml(topGroup.group_key || topGroup.draft_keeper || "first group")}</span>` : ""}
      </div>
    </div>
  `;
}

function guidedReviewQueuePanel(summary) {
  if (!summary) return "";
  const totals = summary.totals || {};
  const queues = summary.queues || [];
  return `
    <div class="band guided-review-panel">
      <div class="band-header">
        <div>
          <h3>${escapeHtml(summary.title || "Guided Review Queue")}</h3>
          <p>${escapeHtml(summary.message || "")}</p>
        </div>
        <div class="archive-decision-actions">
          <a class="text-button action-link" href="${escapeHtml(summary.report || "/reports/cleanup_merge_review_pack.md")}" target="_blank" rel="noreferrer">Open Report</a>
          <a class="text-button action-link" href="${escapeHtml(summary.export_url || "/api/export?type=cleanup_merge_drafts&status=open")}">Export Drafts</a>
        </div>
      </div>
      <div class="guided-review-metrics">
        <div class="signal"><strong>${formatNumber(totals.open_groups || 0)}</strong><span>Review groups</span></div>
        <div class="signal"><strong>${formatNumber(totals.review_remaining || 0)}</strong><span>Still needs review</span></div>
        <div class="signal"><strong>${formatNumber(totals.concrete_decisions || 0)}</strong><span>Concrete decisions</span></div>
        <div class="signal"><strong>${formatNumber(totals.merge_later || 0)}</strong><span>Merge Later</span></div>
        <div class="signal"><strong>${formatNumber(totals.keep_separate || 0)}</strong><span>Keep Separate</span></div>
        <div class="signal"><strong>${formatNumber(totals.high_remaining || 0)}</strong><span>High remaining</span></div>
        <div class="signal"><strong>${formatNumber(totals.manual_review_fields || 0)}</strong><span>Manual fields</span></div>
        <div class="signal"><strong>${formatNumber(totals.history_signals || 0)}</strong><span>History signals</span></div>
      </div>
      <div class="guided-review-queues">
        ${queues.map((queue) => guidedReviewQueueCard(queue)).join("")}
      </div>
    </div>
  `;
}

function cleanupStarterPacketPanel(packet) {
  if (!packet?.message) return "";
  const groups = packet.groups || [];
  const queueSummaries = packet.queue_summaries || [];
  return `
    <div class="band cleanup-starter-panel ${escapeHtml(packet.status || "")}">
      <div class="band-header">
        <div>
          <h3>${escapeHtml(packet.title || "Cleanup Starter Packet")}</h3>
          <p>${escapeHtml(packet.message || "")}</p>
        </div>
        <div class="archive-decision-actions">
          <button type="button" class="text-button nav-jump" data-view="cleanup">Open Cleanup</button>
          ${packet.report ? `<a class="text-button action-link" href="${escapeHtml(packet.report)}" target="_blank" rel="noreferrer">Open Report</a>` : ""}
          ${packet.export_url ? `<a class="text-button action-link" href="${escapeHtml(packet.export_url)}">Export Packet</a>` : ""}
        </div>
      </div>
      <div class="cleanup-starter-summary">
        ${queueSummaries
          .map((queue) => `
            <div class="cleanup-starter-queue">
              <strong>${escapeHtml(queue.queue_label || "")}</strong>
              <span>${formatNumber(queue.review_remaining || 0)} remaining · ${formatNumber(queue.high_priority || 0)} high</span>
            </div>
          `)
          .join("")}
      </div>
      ${
        groups.length
          ? `<div class="cleanup-starter-list">
              ${groups.map((group) => cleanupStarterRow(group)).join("")}
            </div>`
          : ""
      }
    </div>
  `;
}

function cleanupStarterRow(group) {
  return `
    <div class="cleanup-starter-row">
      <div class="cleanup-starter-main">
        <span class="step-pill">${formatNumber(group.review_order || 0)}</span>
        ${cleanupPriorityPill(group.priority)}
        <strong>${escapeHtml(group.group_label || group.group_key || "")}</strong>
        <p>${escapeHtml(group.phase || "")}</p>
        ${group.draft_keeper ? `<small>Draft keeper: ${escapeHtml(group.draft_keeper)} · ${escapeHtml(group.draft_keeper_type || "")}</small>` : ""}
      </div>
      <div class="cleanup-starter-facts">
        <span><strong>${formatNumber(group.record_count || 0)}</strong>Records</span>
        <span><strong>${formatNumber(group.draft_manual_review_fields || 0)}</strong>Manual fields</span>
        <span><strong>${formatNumber(group.draft_history_signals || 0)}</strong>History signals</span>
      </div>
      <div class="cleanup-starter-actions">
        <button class="text-button cleanup-group-button" data-type="${escapeHtml(group.group_type || "")}" data-key="${escapeHtml(group.group_key || "")}">Review</button>
      </div>
    </div>
  `;
}

function guidedReviewQueueCard(queue) {
  const nextGroup = queue.next_group || {};
  const active = state.cleanupGroupType === queue.group_type && state.cleanupStatus === "open";
  const lane = queue.policy_lane || "";
  const decisionStatus = queue.project_decision_status === "decided" ? "Decided" : "Policy pending";
  const decisionClass = queue.project_decision_status === "decided" ? "green" : "gold";
  const counts = queue.decision_counts || {};
  return `
    <div class="guided-review-queue-card ${active ? "active" : ""}">
      <div class="guided-review-queue-head">
        <div>
          <strong>${escapeHtml(queue.label || "")}</strong>
          <p>${escapeHtml(queue.reason || "")}</p>
        </div>
        <span class="pill ${decisionClass}">${escapeHtml(decisionStatus)}</span>
      </div>
      <div class="guided-review-queue-numbers">
        <span><strong>${formatNumber(queue.review_remaining || 0)}</strong> remaining</span>
        <span><strong>${formatNumber(queue.concrete_decisions || 0)}</strong> decided</span>
        <span><strong>${formatNumber(counts.merge_later || 0)}</strong> merge later</span>
        <span><strong>${formatNumber(queue.high_remaining || 0)}</strong> high left</span>
      </div>
      ${
        nextGroup.group_key
          ? `<button class="cleanup-group-button guided-next-group" data-type="${escapeHtml(queue.group_type || "")}" data-key="${escapeHtml(nextGroup.group_key)}">
              <span>Next group</span>
              <strong>${escapeHtml(nextGroup.group_label || nextGroup.group_key)}</strong>
              <small>${escapeHtml(nextGroup.priority || "Review")} · ${formatNumber(nextGroup.record_count || 0)} records · ${formatNumber(nextGroup.manual_review_fields || 0)} manual fields</small>
            </button>`
          : `<div class="muted">No open groups in this queue.</div>`
      }
      <div class="archive-decision-actions guided-review-actions">
        <button class="text-button queue-review-button" type="button" data-type="${escapeHtml(queue.group_type || "")}" data-lane="${escapeHtml(lane)}">${active ? "Refresh Queue" : `Open ${escapeHtml(queue.short_label || "Queue")}`}</button>
        <button class="text-button next-action-decision" type="button" data-key="${escapeHtml(queue.decision_key || "")}">Open Policy</button>
        ${queue.worksheet_report ? `<a class="text-button action-link" href="${escapeHtml(queue.worksheet_report)}" target="_blank" rel="noreferrer">Worksheet</a>` : ""}
        ${queue.worksheet_export_url ? `<a class="text-button action-link" href="${escapeHtml(queue.worksheet_export_url)}">Worksheet CSV</a>` : ""}
        <a class="text-button action-link" href="${escapeHtml(queue.export_url || "/api/export_cleanup_groups")}">Export Queue</a>
      </div>
    </div>
  `;
}

function cleanupPolicyPanel(policy) {
  if (!policy) return "";
  const totals = policy.totals || {};
  const lanes = policy.lanes || [];
  const topGroups = policy.top_groups || [];
  return `
    <div class="band cleanup-policy-panel">
      <div class="band-header">
        <div>
          <h3>Guided Cleanup Policy</h3>
          <p>${escapeHtml(policy.message || "")}</p>
        </div>
        <a class="text-button action-link" href="/reports/merge_policy_options.md" target="_blank" rel="noreferrer">Open Report</a>
      </div>
      <div class="cleanup-policy-totals">
        <div class="signal"><strong>${formatNumber(totals.open_groups || 0)}</strong><span>Open groups</span></div>
        <div class="signal"><strong>${formatNumber(totals.manual_first || 0)}</strong><span>Manual first</span></div>
        <div class="signal"><strong>${formatNumber(totals.short_guided || 0)}</strong><span>Short guided</span></div>
        <div class="signal"><strong>${formatNumber(totals.batch_tag_candidates || 0)}</strong><span>Tag batch candidates</span></div>
        <div class="signal"><strong>${formatNumber(totals.auto_merge_recommended || 0)}</strong><span>Auto-merge today</span></div>
      </div>
      <div class="cleanup-policy-lanes">
        ${lanes
          .map(
            (lane) => `
              <button class="cleanup-policy-lane-button" data-lane="${escapeHtml(lane.lane)}" data-type="${escapeHtml(lane.default_group_type || state.cleanupGroupType)}">
                <strong>${formatNumber(lane.groups || 0)}</strong>
                <span>${escapeHtml(lane.label)}</span>
                <small>${formatNumber(lane.high || 0)} high · ${formatNumber(lane.medium || 0)} medium · ${formatNumber(lane.low || 0)} low</small>
              </button>
            `,
          )
          .join("")}
      </div>
      ${
        topGroups.length
          ? `<div class="cleanup-policy-top-list">
              ${topGroups
                .slice(0, 5)
                .map(
                  (group) => `
                    <button class="cleanup-group-button cleanup-policy-top-button" data-type="${escapeHtml(group.group_type)}" data-key="${escapeHtml(group.group_key)}">
                      <span>${escapeHtml(group.queue_label)}</span>
                      <strong>${escapeHtml(group.group_label || group.group_key)}</strong>
                      <small>${escapeHtml(group.policy_lane_label || "")} · ${escapeHtml(group.priority || "")} · ${formatNumber(group.record_count || 0)} records</small>
                    </button>
                  `,
                )
                .join("")}
            </div>`
          : ""
      }
    </div>
  `;
}

function cleanupGroupPrimaryLabel(groupType) {
  return groupType === "duplicate_tags" ? "Tag" : "Email";
}

function cleanupGroupSearchPlaceholder(groupType) {
  return groupType === "duplicate_tags" ? "Filter by tag name or type" : "Filter by email, name, or phone";
}

function cleanupGroupDisplayValue(group) {
  return group.display_name || group.group_key;
}

function cleanupGroupMergeDraftSummary(summary) {
  if (!summary) return `<span class="muted">Not applicable</span>`;
  const keeper = summary.keeper_name || `${labelize(summary.keeper_record_type || "record")} #${summary.keeper_record_id || ""}`;
  const parts = [`Keeper: ${keeper}`];
  if (Number(summary.conflict_count || 0)) parts.push(`${formatNumber(summary.conflict_count)} review fields`);
  if (Number(summary.fill_suggestion_count || 0)) parts.push(`${formatNumber(summary.fill_suggestion_count)} fills`);
  if (Number(summary.preserve_record_count || 0)) parts.push(`${formatNumber(summary.preserve_record_count)} history records`);
  return `<span class="merge-draft-summary">${escapeHtml(parts.join(" · "))}</span>`;
}

function cleanupFieldComparison(comparisons) {
  if (!comparisons.length) return "";
  return `
    <div class="detail-section">
      <h3>Field Differences</h3>
      <div class="cleanup-field-list">
        ${comparisons
          .map((comparison) => `
            <div class="cleanup-field-diff">
              <div class="cleanup-field-header">
                <strong>${escapeHtml(comparison.field_name)}</strong>
                <span class="muted">${formatNumber(comparison.distinct_count)} values</span>
              </div>
              <div class="cleanup-field-values">
                ${(comparison.values || [])
                  .map((item) => `
                    <div class="cleanup-field-value">
                      <span class="muted" title="${escapeHtml(item.record_name || item.record_label)}">${escapeHtml(item.record_label)}</span>
                      <strong class="${item.is_blank ? "muted" : ""}">${escapeHtml(cleanupComparisonValue(comparison, item))}</strong>
                    </div>
                  `)
                  .join("")}
              </div>
            </div>
          `)
          .join("")}
      </div>
    </div>
  `;
}

function cleanupMergeDraft(draft) {
  if (!draft) return "";
  const keeper = draft.keeper || {};
  return `
    <div class="detail-section merge-draft">
      <div class="inline-header">
        <h3>Merge Draft</h3>
        <span class="pill gold">Review only</span>
      </div>
      <div class="merge-draft-keeper">
        <span class="muted">Draft keeper</span>
        <button class="record-button" data-type="${escapeHtml(keeper.record_type || "")}" data-id="${escapeHtml(keeper.record_id || "")}">
          ${escapeHtml(keeper.record_name || `${labelize(keeper.record_type || "record")} #${keeper.record_id || ""}`)}
        </button>
        <p>${escapeHtml(keeper.reason || "")}</p>
      </div>
      ${draft.warnings?.length ? `<div class="cleanup-guidance-list">${draft.warnings.map((warning) => `<span>${escapeHtml(warning)}</span>`).join("")}</div>` : ""}
      ${mergeDraftSuggestions(draft.fill_suggestions || [])}
      ${mergeDraftConflicts(draft.conflicts || [])}
      ${mergeDraftPreserveSignals(draft.preserve_signals || [])}
    </div>
  `;
}

function mergeDraftSuggestions(items) {
  if (!items.length) return "";
  return `
    <div class="merge-draft-block">
      <h4>Blank Field Suggestions</h4>
      <div class="cleanup-field-list">
        ${items
          .map((item) => `
            <div class="cleanup-field-diff">
              <div class="cleanup-field-header">
                <strong>${escapeHtml(item.field_name || "")}</strong>
                <span class="muted">from ${escapeHtml(item.from_record_name || item.from_record_label || "")}</span>
              </div>
              <p>${escapeHtml(mergeDraftValue(item.field_key, item.value))}</p>
            </div>
          `)
          .join("")}
      </div>
    </div>
  `;
}

function mergeDraftConflicts(items) {
  if (!items.length) return "";
  return `
    <div class="merge-draft-block">
      <h4>Manual Review Fields</h4>
      <div class="cleanup-field-list">
        ${items
          .map((item) => `
            <div class="cleanup-field-diff">
              <div class="cleanup-field-header">
                <strong>${escapeHtml(item.field_name || "")}</strong>
                <span class="muted">keeper has ${escapeHtml(mergeDraftValue(item.field_key, item.keeper_value) || "(blank)")}</span>
              </div>
              <div class="cleanup-field-values">
                ${(item.alternatives || [])
                  .map((alternative) => `
                    <div class="cleanup-field-value">
                      <span>${escapeHtml(alternative.record_name || alternative.record_label || "")}</span>
                      <strong>${escapeHtml(mergeDraftValue(item.field_key, alternative.value))}</strong>
                    </div>
                  `)
                  .join("")}
              </div>
            </div>
          `)
          .join("")}
      </div>
    </div>
  `;
}

function mergeDraftPreserveSignals(items) {
  if (!items.length) return "";
  return `
    <div class="merge-draft-block">
      <h4>History To Preserve</h4>
      <div class="cleanup-field-list">
        ${items
          .map((item) => `
            <div class="cleanup-field-diff">
              <div class="cleanup-field-header">
                <strong>${escapeHtml(item.record_name || item.record_label || "")}</strong>
                <span class="muted">${escapeHtml(item.record_label || "")}</span>
              </div>
              <div class="cleanup-record-stats">
                ${(item.signals || []).map((signal) => `<span>${formatNumber(signal.count)} ${escapeHtml(signal.label)}</span>`).join("")}
              </div>
            </div>
          `)
          .join("")}
      </div>
    </div>
  `;
}

function mergeDraftValue(fieldKey, value) {
  if (!value) return "";
  if (fieldKey?.endsWith("_at")) return formatDate(value);
  return value;
}

function cleanupComparisonValue(comparison, item) {
  if (item.is_blank) return "Missing";
  if (comparison.field_key?.endsWith("_at")) return formatDate(item.value);
  return item.value;
}

function cleanupRecordStats(record) {
  const stats = record.stats || {};
  const items = [
    ["Score", record.completeness_score],
    ["Tags", stats.tag_count],
    ["Notes", stats.note_count],
    ["Tasks", stats.task_count],
    ["Deals", stats.deal_count],
    ["Addresses", stats.address_count],
    ["Fields", stats.custom_field_count],
  ].filter(([, value], index) => index === 0 || Number(value || 0) > 0);
  return `
    <div class="cleanup-record-stats">
      ${items.map(([label, value]) => `<span>${escapeHtml(label)} ${formatNumber(value || 0)}</span>`).join("")}
      ${record.updated_at ? `<span>${escapeHtml(formatDate(record.updated_at))}</span>` : ""}
    </div>
  `;
}

async function renderCleanup() {
  setStatus("Loading cleanup");
  const groupParams = new URLSearchParams({
    type: state.cleanupGroupType,
    status: state.cleanupStatus,
    page: String(state.cleanupGroupPage),
    page_size: "25",
    q: state.cleanupGroupQ,
    priority: state.cleanupPriority,
    policy_lane: state.cleanupPolicyLane,
    decision: state.cleanupDecision,
    sort: state.cleanupSort,
  });
  const [data, reviewData, backupData, groupData] = await Promise.all([
    fetchJson("/api/cleanup"),
    fetchJson(`/api/review_flags?status=${encodeURIComponent(state.cleanupStatus)}&page_size=50`),
    fetchJson("/api/backups"),
    fetchJson(`/api/cleanup_groups?${groupParams.toString()}`),
  ]);
  const latestBackup = backupData.backups[0];
  const totalGroupPages = Math.max(1, Math.ceil(groupData.total / groupData.page_size));
  const cleanupExportParams = new URLSearchParams(groupParams);
  cleanupExportParams.delete("page");
  cleanupExportParams.delete("page_size");
  const cleanupExportUrl = `/api/export_cleanup_groups?${cleanupExportParams.toString()}`;
  els.cleanup.innerHTML = `
    <div class="section-header">
      <div>
        <h2>Cleanup</h2>
        <p>${formatNumber(reviewData.total)} ${cleanupStatusLabel(state.cleanupStatus).toLowerCase()} review flags</p>
      </div>
      <button class="text-button" id="createBackupButton">Backup</button>
    </div>
    <div class="segmented cleanup-status-tabs">
      ${cleanupStatuses
        .map((item) => {
          const count = data.status_counts?.[item.status];
          const label = count === undefined ? item.label : `${item.label} ${formatNumber(count)}`;
          return `<button class="segment-button cleanup-status-tab ${state.cleanupStatus === item.status ? "active" : ""}" data-status="${item.status}">${escapeHtml(label)}</button>`;
        })
        .join("")}
    </div>
    <div class="cleanup-grid">
      <div class="signal"><strong>${formatNumber(data.totals.duplicate_contact_email_groups)}</strong><span>Duplicate person email flags</span></div>
      <div class="signal"><strong>${formatNumber(data.totals.duplicate_lead_email_groups)}</strong><span>Duplicate lead email flags</span></div>
      <div class="signal"><strong>${formatNumber(data.totals.contact_lead_overlap_groups)}</strong><span>Lead/person email flags</span></div>
      <div class="signal"><strong>${formatNumber(data.totals.duplicate_tag_groups)}</strong><span>Duplicate tag definition flags</span></div>
      <div class="signal"><strong>${formatNumber(data.totals.relationship_issues)}</strong><span>Relationship issues</span></div>
    </div>
    ${nextActionPanel(data.next_action)}
    ${leadPersonOverlapDecisionPanel(data.lead_person_overlap_decision)}
    ${mergeCleanupDecisionPanel(data.duplicate_people_decision, {
      title: "Duplicate People Evidence",
      groupType: "duplicate_people",
      decisionKey: "duplicate_people_merge_policy",
      recordLabel: "People records",
      showLabel: "Show People Review",
      refreshLabel: "Refresh People Review",
      pillClass: "gold",
    })}
    ${mergeCleanupDecisionPanel(data.duplicate_leads_decision, {
      title: "Duplicate Leads Evidence",
      groupType: "duplicate_leads",
      decisionKey: "duplicate_leads_merge_policy",
      recordLabel: "Lead records",
      showLabel: "Show Leads Review",
      refreshLabel: "Refresh Leads Review",
      pillClass: "gold",
    })}
    ${duplicateTagDecisionPanel(data.duplicate_tag_decision)}
    ${cleanupPolicyPanel(data.merge_policy)}
    ${guidedReviewQueuePanel(data.guided_review_queue)}
    ${cleanupStarterPacketPanel(data.cleanup_starter)}
    ${cleanupExecutionPreviewPanel(data.execution_preview)}
    ${cleanupExecutionPreviewPanel(data.recommended_execution_preview, "Recommended Path Simulation")}
    <div class="band">
      <div class="band-header">
        <h3>Grouped Review</h3>
        <span class="muted">${formatNumber(groupData.total)} ${cleanupStatusLabel(state.cleanupStatus).toLowerCase()} groups</span>
      </div>
      <div class="cleanup-group-tools">
        <div class="segmented">
          ${cleanupGroupTypes
            .map((item) => `<button class="segment-button cleanup-group-tab ${state.cleanupGroupType === item.type ? "active" : ""}" data-type="${item.type}">${escapeHtml(item.label)}</button>`)
            .join("")}
        </div>
        <div class="table-tools">
          <input id="cleanupGroupSearch" type="search" value="${escapeHtml(state.cleanupGroupQ)}" placeholder="${escapeHtml(cleanupGroupSearchPlaceholder(state.cleanupGroupType))}">
          <select id="cleanupPriorityFilter" aria-label="Cleanup priority">
            ${cleanupPriorities
              .map((item) => `<option value="${item.value}" ${state.cleanupPriority === item.value ? "selected" : ""}>${escapeHtml(item.label)}</option>`)
              .join("")}
          </select>
          <select id="cleanupPolicyLaneFilter" aria-label="Cleanup guided lane">
            ${cleanupPolicyLanes
              .map((item) => `<option value="${item.value}" ${state.cleanupPolicyLane === item.value ? "selected" : ""}>${escapeHtml(item.label)}</option>`)
              .join("")}
          </select>
          <select id="cleanupDecisionFilter" aria-label="Cleanup decision">
            ${cleanupDecisionFilters
              .map((item) => `<option value="${item.value}" ${state.cleanupDecision === item.value ? "selected" : ""}>${escapeHtml(item.label)}</option>`)
              .join("")}
          </select>
          <select id="cleanupGroupSort" aria-label="Cleanup group sort">
            ${cleanupSortOptions
              .map((item) => `<option value="${item.value}" ${state.cleanupSort === item.value ? "selected" : ""}>${escapeHtml(item.label)}</option>`)
              .join("")}
          </select>
          <a class="text-button action-link" href="${escapeHtml(cleanupExportUrl)}">Export CSV</a>
          <div class="pager">
            <button class="icon-button" id="prevCleanupGroupPage" title="Previous page" ${state.cleanupGroupPage <= 1 ? "disabled" : ""}>‹</button>
            <span class="muted">Page ${state.cleanupGroupPage} of ${totalGroupPages}</span>
            <button class="icon-button" id="nextCleanupGroupPage" title="Next page" ${state.cleanupGroupPage >= totalGroupPages ? "disabled" : ""}>›</button>
          </div>
        </div>
      </div>
      ${
        groupData.groups.length
          ? `<table class="data-table cleanup-group-table">
              <thead><tr><th>${escapeHtml(cleanupGroupPrimaryLabel(groupData.type))}</th><th>Priority</th><th>Lane</th><th>Decision</th><th>Records</th><th>${escapeHtml(cleanupStatusLabel(state.cleanupStatus))} Flags</th><th>Merge Draft</th><th>Names</th><th></th></tr></thead>
              <tbody>
                ${groupData.groups
                  .map((group) => `
                    <tr>
                      <td>${escapeHtml(cleanupGroupDisplayValue(group))}</td>
                      <td>${cleanupPriorityPill(group.guidance?.priority)}</td>
                      <td>${cleanupPolicyLaneBadge(group.policy_lane)}</td>
                      <td>${cleanupGroupDecisionSummary(group.decision)}</td>
                      <td>${formatNumber(group.record_count)}</td>
                      <td><span class="pill ${group.open_flags > 1 ? "gold" : ""}">${formatNumber(group.open_flags)}</span></td>
                      <td>${cleanupGroupMergeDraftSummary(group.merge_draft_summary)}</td>
                      <td class="muted">${escapeHtml(group.sample_names || "")}</td>
                      <td>
                        <button class="text-button cleanup-group-button" data-type="${escapeHtml(groupData.type)}" data-key="${escapeHtml(group.group_key)}">Review</button>
                      </td>
                    </tr>
                  `)
                  .join("")}
              </tbody>
            </table>`
          : `<div class="empty-state"><h3>No groups</h3><p>No ${cleanupStatusLabel(state.cleanupStatus).toLowerCase()} cleanup groups matched this filter.</p></div>`
      }
    </div>
    <div class="band">
      <div class="band-header">
        <h3>Review Queue</h3>
        <span class="muted">${formatNumber(reviewData.total)} ${cleanupStatusLabel(state.cleanupStatus).toLowerCase()}</span>
      </div>
      <table class="data-table">
        <thead><tr><th>Type</th><th>Severity</th><th>Record</th><th>Flag</th><th></th></tr></thead>
        <tbody>
          ${reviewData.flags
            .map((flag) => `
              <tr>
                <td>${escapeHtml(labelize(flag.flag_type))}</td>
                <td><span class="pill ${flag.severity === "medium" ? "gold" : ""}">${escapeHtml(flag.severity)}</span></td>
                <td>
                  ${flag.record_id && detailTypeSupported(flag.record_type)
                    ? `<button class="record-button" data-type="${escapeHtml(flag.record_type)}" data-id="${flag.record_id}">${escapeHtml(flag.record_type)} #${flag.record_id}</button>`
                    : escapeHtml(flag.record_type || "")}
                </td>
                <td class="muted">${escapeHtml(flag.description)}${cleanupResolutionNote(flag)}</td>
                <td>${cleanupFlagActions(flag)}</td>
              </tr>
            `)
            .join("")}
        </tbody>
      </table>
    </div>
    <div class="band">
      <div class="band-header"><h3>Duplicate Tags</h3></div>
      <table class="data-table">
        <thead><tr><th>Tag</th><th>Definitions</th><th>Types</th></tr></thead>
        <tbody>
          ${data.duplicate_tags
            .map((row) => `
              <tr>
                <td>${escapeHtml(row.tag)}</td>
                <td>${formatNumber(row.count)}</td>
                <td class="muted">${escapeHtml(row.resource_types)}</td>
              </tr>
            `)
            .join("")}
        </tbody>
      </table>
    </div>
    <div class="band">
      <div class="band-header">
        <h3>Local Reports</h3>
        <span class="muted">${latestBackup ? `Latest backup: ${escapeHtml(latestBackup.name)}` : "No backups yet"}</span>
      </div>
      <div class="detail-content report-links">
        ${data.report_links.map((link) => `<a href="${link}" target="_blank" rel="noreferrer">${escapeHtml(link.split("/").pop())}</a>`).join("")}
      </div>
    </div>
    <div class="band">
      <div class="band-header">
        <h3>Backups</h3>
        <span class="muted">${formatNumber(backupData.backups.length)} saved</span>
      </div>
      <table class="data-table">
        <thead><tr><th>Backup</th><th>Size</th><th>Modified</th><th></th></tr></thead>
        <tbody>
          ${backupData.backups.slice(0, 12)
            .map((backup) => `
              <tr>
                <td>${escapeHtml(backup.name)}</td>
                <td class="muted">${formatNumber(Math.round((backup.bytes || 0) / 1024))} KB</td>
                <td class="muted">${formatDate(backup.modified_at)}</td>
                <td><button class="text-button restore-backup-button" data-name="${escapeHtml(backup.name)}">Restore</button></td>
              </tr>
            `)
            .join("")}
        </tbody>
      </table>
    </div>
  `;
  wireRecordButtons(els.cleanup);
  wireNextAction(els.cleanup);
  wireNavJumps(els.cleanup);
  wireCleanupGroupButtons(els.cleanup);
  wireCleanupFlagButtons(els.cleanup);
  document.querySelectorAll(".cleanup-status-tab").forEach((button) => {
    button.addEventListener("click", () => {
      state.cleanupStatus = button.dataset.status;
      state.cleanupGroupPage = 1;
      state.cleanupGroupQ = "";
      state.cleanupPriority = "";
      state.cleanupPolicyLane = "";
      state.cleanupDecision = "";
      state.currentCleanupGroup = null;
      renderCleanup();
    });
  });
  document.querySelectorAll(".cleanup-group-tab").forEach((button) => {
    button.addEventListener("click", () => {
      state.cleanupGroupType = button.dataset.type;
      state.cleanupGroupPage = 1;
      state.cleanupGroupQ = "";
      state.cleanupPriority = "";
      state.cleanupPolicyLane = "";
      state.cleanupDecision = "";
      renderCleanup();
    });
  });
  document.querySelectorAll(".cleanup-policy-lane-button").forEach((button) => {
    button.addEventListener("click", () => {
      state.cleanupGroupType = button.dataset.type || state.cleanupGroupType;
      state.cleanupPolicyLane = button.dataset.lane || "";
      state.cleanupStatus = "open";
      state.cleanupPriority = "";
      state.cleanupDecision = "";
      state.cleanupSort = "policy";
      state.cleanupGroupQ = "";
      state.cleanupGroupPage = 1;
      renderCleanup();
    });
  });
  document.querySelectorAll(".duplicate-tag-evidence-button").forEach((button) => {
    button.addEventListener("click", () => {
      state.cleanupGroupType = "duplicate_tags";
      state.cleanupStatus = "open";
      state.cleanupPolicyLane = "tag_batch_candidate";
      state.cleanupPriority = "";
      state.cleanupDecision = "";
      state.cleanupSort = "policy";
      state.cleanupGroupQ = "";
      state.cleanupGroupPage = 1;
      renderCleanup();
    });
  });
  document.querySelectorAll(".overlap-evidence-button").forEach((button) => {
    button.addEventListener("click", () => {
      state.cleanupGroupType = "lead_person_overlap";
      state.cleanupStatus = "open";
      state.cleanupPolicyLane = "policy_review_overlap";
      state.cleanupPriority = "";
      state.cleanupDecision = "";
      state.cleanupSort = "policy";
      state.cleanupGroupQ = "";
      state.cleanupGroupPage = 1;
      renderCleanup();
    });
  });
  document.querySelectorAll(".merge-evidence-button").forEach((button) => {
    button.addEventListener("click", () => {
      state.cleanupGroupType = button.dataset.type || "duplicate_people";
      state.cleanupStatus = "open";
      state.cleanupPolicyLane = "";
      state.cleanupPriority = "";
      state.cleanupDecision = "";
      state.cleanupSort = "policy";
      state.cleanupGroupQ = "";
      state.cleanupGroupPage = 1;
      renderCleanup();
    });
  });
  document.querySelectorAll(".queue-review-button").forEach((button) => {
    button.addEventListener("click", () => {
      state.cleanupGroupType = button.dataset.type || "duplicate_people";
      state.cleanupStatus = "open";
      state.cleanupPolicyLane = button.dataset.lane || "";
      state.cleanupPriority = "";
      state.cleanupDecision = "";
      state.cleanupSort = "policy";
      state.cleanupGroupQ = "";
      state.cleanupGroupPage = 1;
      renderCleanup();
    });
  });
  document.querySelector("#cleanupPriorityFilter").addEventListener("change", (event) => {
    state.cleanupPriority = event.target.value;
    state.cleanupGroupPage = 1;
    renderCleanup();
  });
  document.querySelector("#cleanupPolicyLaneFilter").addEventListener("change", (event) => {
    state.cleanupPolicyLane = event.target.value;
    state.cleanupGroupPage = 1;
    renderCleanup();
  });
  document.querySelector("#cleanupDecisionFilter").addEventListener("change", (event) => {
    state.cleanupDecision = event.target.value;
    state.cleanupGroupPage = 1;
    renderCleanup();
  });
  document.querySelector("#cleanupGroupSort").addEventListener("change", (event) => {
    state.cleanupSort = event.target.value;
    state.cleanupGroupPage = 1;
    renderCleanup();
  });
  const cleanupGroupSearch = document.querySelector("#cleanupGroupSearch");
  cleanupGroupSearch.addEventListener("input", () => {
    window.clearTimeout(state.debounce);
    state.debounce = window.setTimeout(() => {
      state.cleanupGroupQ = cleanupGroupSearch.value.trim();
      state.cleanupGroupPage = 1;
      renderCleanup();
    }, 220);
  });
  document.querySelector("#prevCleanupGroupPage").addEventListener("click", () => {
    state.cleanupGroupPage = Math.max(1, state.cleanupGroupPage - 1);
    renderCleanup();
  });
  document.querySelector("#nextCleanupGroupPage").addEventListener("click", () => {
    state.cleanupGroupPage += 1;
    renderCleanup();
  });
  document.querySelector("#createBackupButton").addEventListener("click", async () => {
    setStatus("Backing up");
    await postJson("/api/backup", {});
    await renderCleanup();
    setStatus("Backup created");
  });
  document.querySelectorAll(".restore-backup-button").forEach((button) => {
    button.addEventListener("click", async () => {
      const name = button.dataset.name;
      const ok = window.confirm(`Restore ${name}? A pre-restore backup will be created first.`);
      if (!ok) return;
      setStatus("Restoring backup");
      await postJson("/api/restore_backup", { name });
      await renderDashboard();
      await renderCleanup();
      els.detail.innerHTML = `
        <div class="empty-detail">
          <div class="empty-mark">OK</div>
          <h2>Backup restored</h2>
          <p>${escapeHtml(name)}</p>
        </div>
      `;
      setStatus("Backup restored");
    });
  });
  setStatus("Ready");
}

async function runSearch(query) {
  if (!query) {
    setView(state.view);
    return;
  }
  setStatus("Searching");
  const data = await fetchJson(`/api/search?q=${encodeURIComponent(query)}`);
  els.dashboard.classList.remove("active-view");
  els.tags.classList.remove("active-view");
  els.customFields.classList.remove("active-view");
  els.archive.classList.remove("active-view");
  els.followup.classList.remove("active-view");
  els.activity.classList.remove("active-view");
  els.exports.classList.remove("active-view");
  els.users.classList.remove("active-view");
  els.cleanup.classList.remove("active-view");
  els.list.classList.add("active-view");
  els.list.innerHTML = `
    <div class="section-header">
      <div>
        <h2>Search</h2>
        <p>${formatNumber(data.results.length)} quick results</p>
      </div>
    </div>
    ${recordTable(data.results, "search")}
  `;
  wireRecordButtons(els.list);
  setStatus("Ready");
}

els.navButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.q = "";
    els.search.value = "";
    setView(button.dataset.view);
  });
});

els.search.addEventListener("input", () => {
  window.clearTimeout(state.debounce);
  state.debounce = window.setTimeout(() => {
    runSearch(els.search.value.trim());
  }, 220);
});

els.authLoginForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(els.authLoginForm);
  if (els.authMessage) els.authMessage.textContent = "";
  setStatus("Signing in");
  try {
    const result = await postJson("/api/auth/login", {
      email: form.get("email"),
      password: form.get("password"),
    });
    state.auth = result.auth;
    renderAuthControl();
    showAuthOverlay(state.auth);
    await renderDashboard();
    setStatus("Ready");
  } catch (error) {
    if (els.authMessage) els.authMessage.textContent = error.message;
    setStatus("Sign in needed");
  }
});

els.ownerRecoveryOpen?.addEventListener("click", () => {
  showOwnerRecoveryOverlay(true);
});

els.ownerRecoveryForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await submitOwnerRecovery(event.currentTarget, event.submitter);
});

document.querySelector("#cancelOwnerRecovery")?.addEventListener("click", () => {
  showOwnerRecoveryOverlay(false);
});

els.passwordChangeForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await submitPasswordChange(event.currentTarget, event.submitter);
});

document.querySelector("#cancelPasswordChange")?.addEventListener("click", () => {
  showPasswordOverlay(false);
});

initializeAuth()
  .then((ready) => {
    if (!ready) {
      setStatus("Sign in needed");
      return null;
    }
    return renderDashboard();
  })
  .catch((error) => {
    setStatus("Error");
    els.dashboard.innerHTML = `<div class="empty-state"><h3>Could not load CRM</h3><p>${escapeHtml(error.message)}</p></div>`;
  });
