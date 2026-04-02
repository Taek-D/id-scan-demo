document.addEventListener("DOMContentLoaded", async () => {
  await Promise.all([loadSecurity(), loadNotice(), loadSubmissions()]);
  document.getElementById("refresh-submissions").addEventListener("click", loadSubmissions);
});

async function loadSecurity() {
  const response = await fetch("/api/security");
  const security = await response.json();
  const panel = document.getElementById("admin-security");
  panel.innerHTML = "";
  [
    ["전송 구간", security.transport_encryption],
    ["저장 암호화", security.at_rest_encryption],
    ["보관 정책", security.retention_policy],
    ["접근 범위", security.access_scope],
  ].forEach(([label, value]) => {
    panel.append(renderInfoCard(label, value));
  });
}

async function loadNotice() {
  const response = await fetch("/api/notices");
  const notice = await response.json();
  const panel = document.getElementById("admin-notice");
  panel.innerHTML = "";
  panel.append(renderInfoCard(notice.title, notice.body, notice.updated_at));
}

async function loadSubmissions() {
  const response = await fetch("/api/submissions");
  const submissions = await response.json();
  renderMetrics(submissions);
  renderSubmissionList(submissions);
}

function renderMetrics(submissions) {
  const metrics = document.getElementById("admin-metrics");
  const readyCount = submissions.filter((item) => item.capture_status === "ready").length;
  const reviewCount = submissions.filter((item) => item.capture_status === "review_recommended").length;
  const retryCount = submissions.filter((item) => item.capture_status === "retry_required").length;
  metrics.innerHTML = "";
  [
    ["누적 제출", submissions.length],
    ["제출 가능", readyCount],
    ["주의 필요", reviewCount],
    ["재촬영 필요", retryCount],
  ].forEach(([label, value]) => {
    const card = document.createElement("article");
    card.className = "metric-card";
    card.innerHTML = `<span>${label}</span><strong>${value}</strong>`;
    metrics.append(card);
  });
}

function renderSubmissionList(submissions) {
  const list = document.getElementById("submission-list");
  list.innerHTML = "";

  if (!submissions.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "아직 제출된 신분증 이미지가 없습니다. 촬영 화면에서 샘플을 먼저 업로드해 주세요.";
    list.append(empty);
    return;
  }

  submissions.forEach((submission) => {
    const item = document.createElement("article");
    item.className = "submission-item";
    item.innerHTML = `
      <div class="submission-topline">
        <div>
          <div class="submission-title">${submission.original_filename}</div>
          <div class="submission-meta">${formatDate(submission.created_at)} · ${submission.document_type}</div>
        </div>
        <span class="${chipClass(submission.capture_status)}">${submission.capture_status_label}</span>
      </div>
      <div class="submission-metrics">
        <span class="metric-pill">Glare ${(submission.glare_ratio * 100).toFixed(1)}%</span>
        <span class="metric-pill">Blur ${submission.blur_score.toFixed(1)}</span>
        <span class="metric-pill">Fill ${(submission.frame_fill_ratio * 100).toFixed(1)}%</span>
        <span class="metric-pill">Tilt ${submission.tilt_angle == null ? "-" : `${submission.tilt_angle}°`}</span>
        <span class="metric-pill">Codes ${submission.admin_codes.join(", ") || "NONE"}</span>
      </div>
      <p class="lead compact">${submission.capture_summary}</p>
      <div class="submission-actions">
        <a class="button button-secondary" href="/api/submissions/${submission.id}/download?variant=original">원본 다운로드</a>
        <a class="button button-secondary" href="/api/submissions/${submission.id}/download?variant=glare">글레어 단계</a>
        <a class="button button-secondary" href="/api/submissions/${submission.id}/download?variant=detect">크롭 단계</a>
        <a class="button button-primary" href="/api/submissions/${submission.id}/download?variant=final">최종본 다운로드</a>
      </div>
    `;
    list.append(item);
  });
}

function renderInfoCard(label, value, secondary = "") {
  const article = document.createElement("article");
  article.innerHTML = `
    <span>${label}</span>
    <strong>${value}</strong>
    ${secondary ? `<small>${secondary}</small>` : ""}
  `;
  return article;
}

function chipClass(status) {
  if (status === "ready") return "chip chip-ready";
  if (status === "review_recommended") return "chip chip-review";
  return "chip chip-retry";
}

function formatDate(value) {
  return new Date(value).toLocaleString("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
