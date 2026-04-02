const QA_DOCUMENT_LABELS = {
  resident_id: "주민등록증",
  alien_registration: "외국인등록증",
  passport: "여권",
};

const QA_STATUS_LABELS = {
  ready: "정상",
  review_recommended: "주의",
  retry_required: "실패",
};

document.addEventListener("DOMContentLoaded", async () => {
  document.getElementById("refresh-qa").addEventListener("click", loadQAGallery);
  await loadQAGallery();
});

async function loadQAGallery() {
  const button = document.getElementById("refresh-qa");
  button.disabled = true;
  button.textContent = "계산 중...";

  try {
    const response = await fetch("/api/qa/samples");
    const samples = await response.json();
    renderQAGallery(samples);
  } finally {
    button.disabled = false;
    button.textContent = "QA 다시 계산";
  }
}

function renderQAGallery(samples) {
  const gallery = document.getElementById("qa-gallery");
  gallery.innerHTML = "";

  if (!samples.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "QA 샘플이 아직 준비되지 않았습니다.";
    gallery.append(empty);
    return;
  }

  samples.forEach((sample) => {
    const card = document.createElement("article");
    card.className = "qa-card";

    const qualityCode = sample.quality.admin_codes?.length ? sample.quality.admin_codes.join(", ") : "이상 없음";
    card.innerHTML = `
      <div class="qa-card-header">
        <div>
          <p class="section-label">${sample.group_label}</p>
          <h3>${sample.filename}</h3>
          <p class="lead compact">${formatDocumentType(sample.document_type)} · ${sample.quality.summary}</p>
        </div>
        <div class="qa-status-stack">
          <span class="chip chip-neutral">기대 ${formatExpected(sample.expected_status)}</span>
          <span class="${chipClass(sample.quality.status)}">실제 ${sample.quality.status_label}</span>
        </div>
      </div>
      <div class="qa-meta-row">
        <span class="metric-pill">문서 검출 ${sample.card_detected ? "성공" : "실패"}</span>
        <span class="metric-pill">점검 코드 ${qualityCode}</span>
      </div>
      <div class="qa-preview-grid">
        <figure class="qa-preview-card">
          <span>원본</span>
          <img src="data:image/jpeg;base64,${sample.original_b64}" alt="${sample.filename} 원본" />
        </figure>
        <figure class="qa-preview-card">
          <span>반사광 단계</span>
          <img src="data:image/jpeg;base64,${sample.after_glare_b64}" alt="${sample.filename} 반사광 단계" />
        </figure>
        <figure class="qa-preview-card">
          <span>검출 단계</span>
          <img src="data:image/jpeg;base64,${sample.after_detect_b64}" alt="${sample.filename} 검출 단계" />
        </figure>
        <figure class="qa-preview-card">
          <span>최종 보정</span>
          <img src="data:image/jpeg;base64,${sample.final_b64}" alt="${sample.filename} 최종 보정" />
        </figure>
      </div>
    `;

    gallery.append(card);
  });
}

function chipClass(status) {
  if (status === "ready") return "chip chip-ready";
  if (status === "review_recommended") return "chip chip-review";
  return "chip chip-retry";
}

function formatDocumentType(value) {
  return QA_DOCUMENT_LABELS[value] ?? value;
}

function formatExpected(value) {
  return QA_STATUS_LABELS[value] ?? value;
}
