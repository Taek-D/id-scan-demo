const DOCUMENT_TYPE_LABELS = {
  resident_id: "주민등록증",
  alien_registration: "외국인등록증",
  passport: "여권",
};

let submissionsCache = [];

document.addEventListener("DOMContentLoaded", async () => {
  document.getElementById("refresh-submissions").addEventListener("click", loadSubmissions);
  document.getElementById("status-filter").addEventListener("change", applyFilters);
  document.getElementById("document-filter").addEventListener("change", applyFilters);

  await Promise.all([loadSecurity(), loadNotice(), loadSubmissions()]);
});

async function loadSecurity() {
  const response = await fetch("/api/security");
  const security = await response.json();
  const panel = document.getElementById("admin-security");
  panel.innerHTML = "";

  [
    ["전송 구간", security.transport_encryption],
    ["저장소 보호", security.at_rest_encryption],
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
  submissionsCache = await response.json();
  applyFilters();
}

function applyFilters() {
  const statusValue = document.getElementById("status-filter").value;
  const documentValue = document.getElementById("document-filter").value;

  const filtered = submissionsCache.filter((submission) => {
    const statusMatches = statusValue === "all" || submission.capture_status === statusValue;
    const documentMatches = documentValue === "all" || submission.document_type === documentValue;
    return statusMatches && documentMatches;
  });

  renderMetrics(filtered);
  renderSubmissionList(filtered, {
    statusValue,
    documentValue,
  });
}

function renderMetrics(submissions) {
  const metrics = document.getElementById("admin-metrics");
  const readyCount = submissions.filter((item) => item.capture_status === "ready").length;
  const reviewCount = submissions.filter((item) => item.capture_status === "review_recommended").length;
  const retryCount = submissions.filter((item) => item.capture_status === "retry_required").length;

  metrics.innerHTML = "";

  [
    ["현재 목록", submissions.length],
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

function renderSubmissionList(submissions, filters) {
  const list = document.getElementById("submission-list");
  list.innerHTML = "";

  if (!submissions.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent =
      filters.statusValue === "all" && filters.documentValue === "all"
        ? "아직 제출된 신분증 이미지가 없습니다. 촬영 화면에서 샘플을 먼저 업로드해 주세요."
        : "조건에 맞는 제출이 없습니다. 필터를 조정하거나 새로고침해 주세요.";
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
          <div class="submission-meta">${formatDate(submission.created_at)} · ${formatDocumentType(submission.document_type)}</div>
        </div>
        <span class="${chipClass(submission.capture_status)}">${submission.capture_status_label}</span>
      </div>
      <div class="submission-metrics">
        <span class="metric-pill">빛반사 ${(submission.glare_ratio * 100).toFixed(1)}%</span>
        <span class="metric-pill">선명도 ${submission.blur_score.toFixed(1)}</span>
        <span class="metric-pill">프레임 점유 ${(submission.frame_fill_ratio * 100).toFixed(1)}%</span>
        <span class="metric-pill">기울기 ${submission.tilt_angle == null ? "-" : `${submission.tilt_angle}°`}</span>
        <span class="metric-pill">점검 코드 ${formatAdminCodes(submission.admin_codes)}</span>
      </div>
      <p class="lead compact">${submission.capture_summary}</p>
      <div class="submission-actions">
        <a class="button button-secondary" href="/api/submissions/${submission.id}/download?variant=original">원본 다운로드</a>
        <a class="button button-secondary" href="/api/submissions/${submission.id}/download?variant=glare">반사광 단계</a>
        <a class="button button-secondary" href="/api/submissions/${submission.id}/download?variant=detect">검출 단계</a>
        <a class="button button-primary" href="/api/submissions/${submission.id}/download?variant=final">최종 결과 다운로드</a>
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

function formatDocumentType(value) {
  return DOCUMENT_TYPE_LABELS[value] ?? value;
}

function formatAdminCodes(codes) {
  if (!codes?.length) {
    return "이상 없음";
  }

  return codes.join(", ");
}
