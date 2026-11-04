/* Email workspace: plain text drafts, explicit audience review and activation. */
const emailWorkspace = { tab: "broadcasts", query: "", notice: "", preview: null };

async function renderEmail() {
  const root = document.querySelector("#emailView");
  if (!root) return;
  root.innerHTML = '<div class="email-workspace"><h2>Email</h2><p role="status">Loading email workspace…</p></div>';
  try {
    const data = await fetchJson(`/api/email/status?q=${encodeURIComponent(emailWorkspace.query)}`);
    const e = escapeHtml;
    const live = data.enabled && data.provider_configured && data.sender_configured && data.webhook_configured;
    const tabs = [["broadcasts", "Broadcasts"], ["autoresponders", "Autoresponders"], ["contacts", "Contacts"], ["history", "History"]];
    root.innerHTML = `<div class="email-workspace">
      <div class="email-heading"><div><h2>Email</h2><p>Broadcasts and follow-up sequences connected to your CRM.</p></div>
        <span class="pill">${live ? (data.customer_sends_enabled ? "Customer sending enabled" : "Test mode · approved recipients only") : "Draft mode · sending disabled"}</span></div>
      ${!data.customer_sends_enabled ? '<p class="email-notice">Customer sends are disabled. Broadcast audiences and autoresponder enrollments are limited to the approved test addresses.</p>' : ''}
      <nav class="email-tabs" aria-label="Email sections">${tabs.map(([key, label]) => `<button type="button" class="${emailWorkspace.tab === key ? "" : "secondary"}" data-email-tab="${key}" aria-pressed="${emailWorkspace.tab === key}">${label}</button>`).join("")}</nav>
      <p class="email-notice" role="status">${e(emailWorkspace.notice)}</p>
      ${!data.installed ? '<div class="email-card"><h3>Email setup needed</h3><p>The email database setup must be applied before drafting campaigns or importing subscribers.</p></div>' : `
      <div class="email-counts">${(data.counts || []).map(c => `<span><strong>${Number(c.total).toLocaleString()}</strong> ${e(c.status)}</span>`).join("") || "No subscribers imported yet."}</div>
      <div id="emailTabContent"></div>`}
    </div>`;
    root.querySelectorAll("[data-email-tab]").forEach(button => button.addEventListener("click", () => {
      emailWorkspace.tab = button.dataset.emailTab; emailWorkspace.preview = null; renderEmail();
    }));
    if (!data.installed) return;
    const content = root.querySelector("#emailTabContent");
    const tagOptions = `<option value="">All subscribed contacts</option>${(data.tag_options || []).map(tag => `<option value="${e(tag)}">${e(tag)}</option>`).join("")}`;
    if (emailWorkspace.tab === "broadcasts") {
      content.innerHTML = `<div class="email-columns"><form id="emailDraftForm" class="email-card email-form">
        <h3>New broadcast</h3><label>Name<input name="name" maxlength="200" required></label>
        <label>Subject<input name="subject" maxlength="998" required></label>
        <label>Audience<select name="tag">${tagOptions}</select></label>
        <label>Message<textarea name="body" rows="9" maxlength="100000" required placeholder="Write your message. An unsubscribe link is added automatically."></textarea></label>
        <button>Save draft</button><p>Saving a draft does not send email.</p></form>
        <div class="email-card"><h3>Broadcasts</h3><div class="email-items">${data.campaigns.map(c => `<article class="email-item">
          <h4>${e(c.name)}</h4><p>${e(c.subject)}</p><span class="pill">${e(c.state)}</span>
          <p>${e(c.tag_filter || "All subscribed contacts")}</p>
          ${c.state === "draft" ? `<form data-email-test="${e(c.id)}" class="email-test"><label>Test recipient<input type="email" name="email" required placeholder="Approved test address"></label><button class="secondary" ${!live ? "disabled" : ""}>Send test</button></form>
          <button class="secondary" data-email-review="${e(c.id)}" ${!live ? "disabled" : ""}>Review audience & send</button>` : ""}
          ${!["sent", "cancelled"].includes(c.state) ? `<button class="secondary" data-email-cancel="${e(c.id)}">Cancel broadcast</button>` : ""}
        </article>`).join("") || '<p>No broadcasts yet.</p>'}</div></div></div><div id="emailSendReview"></div>`;
      root.querySelector("#emailDraftForm").addEventListener("submit", async event => {
        event.preventDefault(); await emailControl({action: "campaign", ...Object.fromEntries(new FormData(event.currentTarget))}, "Draft saved.");
      });
      root.querySelectorAll("[data-email-test]").forEach(form => form.addEventListener("submit", async event => {
        event.preventDefault(); await emailControl({action: "test", id: form.dataset.emailTest, email: new FormData(form).get("email")}, "Test queued. Review it in your inbox before sending the broadcast.");
      }));
      root.querySelectorAll("[data-email-review]").forEach(button => button.addEventListener("click", async () => {
        const campaign = data.campaigns.find(c => c.id === button.dataset.emailReview);
        try {
          const preview = await postJson("/api/email/action", {action: "preview", tag: campaign.tag_filter});
          const box = root.querySelector("#emailSendReview");
          box.innerHTML = `<form class="email-card email-form"><h3>Review ${e(campaign.name)}</h3><p><strong>${Number(preview.count).toLocaleString()} eligible recipients</strong></p>
            <p>Excluded: ${Object.entries(preview.excluded).map(([k,v]) => `${Number(v)} ${e(k.replaceAll("_", " "))}`).join(" · ")}</p>
            <p class="email-sample">Sample: ${preview.sample.map(e).join(", ") || "No eligible contacts"}</p>
            <label>Schedule (optional, your local time)<input name="schedule" type="datetime-local"></label>
            <label class="email-check"><input name="confirmed" type="checkbox" required> I reviewed the test email and this audience.</label>
            <button ${!preview.count ? "disabled" : ""}>Queue broadcast</button></form>`;
          box.scrollIntoView({behavior: "smooth", block: "nearest"});
          box.querySelector("form").addEventListener("submit", async event => {
            event.preventDefault(); const value = new FormData(event.currentTarget).get("schedule");
            await emailControl({action: "queue_campaign", id: campaign.id, fingerprint: preview.fingerprint,
              scheduled_at: value ? new Date(value).toISOString() : ""}, "Broadcast queued. Delivery progress will appear in History.");
          });
        } catch (error) { emailWorkspace.notice = error.message; await renderEmail(); }
      }));
      root.querySelectorAll("[data-email-cancel]").forEach(button => button.addEventListener("click", () => emailControl({action: "cancel_campaign", id: button.dataset.emailCancel}, "Cancellation requested. Check History for provider confirmation.")));
    } else if (emailWorkspace.tab === "autoresponders") {
      content.innerHTML = `<div class="email-columns"><form id="emailAutomationForm" class="email-card email-form">
        <h3>Connect an autoresponder</h3><p>Create the sequence and its delays in <a href="https://resend.com/automations" target="_blank" rel="noopener noreferrer">Resend</a>, then connect its ID here.</p>
        <label>Name<input name="name" maxlength="200" required></label><label>Resend automation ID<input name="provider_id" required></label>
        <label>Start when<select name="trigger_kind"><option value="tag_added">A tag is added to a person</option><option value="purchase">A new purchase is recorded</option></select></label>
        <label>Tag (for tag triggers)<input name="tag" list="emailKnownTags"></label><datalist id="emailKnownTags">${(data.tag_options || []).map(t => `<option value="${e(t)}">`).join("")}</datalist>
        <button>Save connection</button><p>Connections start paused. Imports never enroll contacts. One enrollment per contact and connection.</p></form>
        <div class="email-card"><h3>Autoresponders</h3>${data.automations.map(a => `<article class="email-item"><h4>${e(a.name)}</h4>
          <p>${e(a.trigger_kind === "purchase" ? "New purchase" : "Tag added: " + a.tag_name)} · ${a.enabled ? "Accepting new enrollments" : "New enrollments paused"}</p>
          <label>Set this trigger event in Resend<input readonly value="${e(a.event_name)}" aria-label="Resend trigger event for ${e(a.name)}"></label>
          <div class="email-actions"><button class="secondary" data-email-toggle="${e(a.id)}" ${!a.enabled && (!live || !data.automations_enabled) ? "disabled" : ""}>${a.enabled ? "Pause new enrollments" : "Enable new enrollments"}</button>
          <button class="secondary" data-email-stop="${e(a.id)}" ${!live ? "disabled" : ""}>Request stop in Resend</button></div>
          <p>Existing runs follow the sequence rules in Resend. Unsubscribed contacts skip remaining email steps.</p></article>`).join("") || '<p>No autoresponders connected.</p>'}</div></div>`;
      root.querySelector("#emailAutomationForm").addEventListener("submit", async event => {
        event.preventDefault(); await emailControl({action: "automation", ...Object.fromEntries(new FormData(event.currentTarget))}, "Connection saved paused. Copy its trigger event into the Resend sequence before enabling it.");
      });
      root.querySelectorAll("[data-email-toggle]").forEach(button => button.addEventListener("click", () => {
        const rule = data.automations.find(a => a.id === button.dataset.emailToggle);
        emailControl({action: "automation_toggle", id: rule.id, enabled: !rule.enabled}, rule.enabled ? "New enrollments paused." : "New enrollments enabled.");
      }));
      root.querySelectorAll("[data-email-stop]").forEach(button => button.addEventListener("click", () => emailControl({action: "stop_automation", id: button.dataset.emailStop}, "Stop requested; check History for confirmation.")));
    } else if (emailWorkspace.tab === "contacts") {
      content.innerHTML = `<div class="email-card"><h3>Marketing contacts</h3><form id="emailContactSearch" class="email-actions"><label>Search<input name="q" type="search" value="${e(emailWorkspace.query)}" placeholder="Name or email"></label><button>Search</button></form>
        <p>Showing up to 100 matches. Only subscribed contacts are eligible for marketing.</p>
        <div class="email-table-wrap"><table><thead><tr><th>Contact</th><th>Status</th><th>Tags</th><th>Action</th></tr></thead><tbody>${data.contacts.map(c => `<tr><td>${e([c.first_name, c.last_name].filter(Boolean).join(" "))}<br>${e(c.email)}</td><td>${e(c.status)}</td><td>${JSON.parse(c.tags_json).map(e).join(", ")}</td><td>${c.status === "subscribed" ? `<button class="secondary" data-email-unsubscribe="${e(c.email)}">Unsubscribe</button>` : "—"}</td></tr>`).join("")}</tbody></table></div></div>`;
      root.querySelector("#emailContactSearch").addEventListener("submit", event => { event.preventDefault(); emailWorkspace.query = new FormData(event.currentTarget).get("q"); renderEmail(); });
      root.querySelectorAll("[data-email-unsubscribe]").forEach(button => button.addEventListener("click", () => emailControl({action: "contact", email: button.dataset.emailUnsubscribe, status: "unsubscribed", evidence: "Owner/admin unsubscribe request"}, "Contact unsubscribed locally; provider suppression queued.")));
    } else {
      content.innerHTML = `<div class="email-card"><h3>Dispatch history</h3><p>Processing or needs-review items require checking Resend before retrying. Duplicate submissions are not retried automatically.</p>
        <div class="email-table-wrap"><table><thead><tr><th>When</th><th>Action</th><th>Contact</th><th>Status</th><th>Details</th></tr></thead><tbody>${data.outbox.map(j => `<tr><td>${e(j.updated_at)}</td><td>${e(j.kind)}</td><td>${e(j.email || "Broadcast / automation")}</td><td>${e(j.state)}</td><td>${e(j.error || "")}</td></tr>`).join("")}</tbody></table></div>
        <h3>Provider activity</h3><div class="email-items">${data.events.map(v => `<p>${e(v.event_type)} · ${e(v.email || "Provider update")} · ${e(v.occurred_at)}</p>`).join("") || '<p>No signed delivery events received yet.</p>'}</div></div>`;
    }
  } catch (error) { root.innerHTML = `<div class="email-workspace"><h2>Email</h2><p role="alert">${escapeHtml(error.message)}</p></div>`; }
}

async function emailControl(payload, notice) {
  const root = document.querySelector("#emailView");
  root.querySelectorAll("button").forEach(button => { button.disabled = true; });
  try { await postJson("/api/email/action", payload); emailWorkspace.notice = notice; }
  catch (error) { emailWorkspace.notice = error.message; }
  await renderEmail();
}
