const stepOrder = ["document", "camera", "align", "submit"];

const state = {
  stream: null,
  documentTypes: [],
  selectedDocumentType: null,
  permissionState: "prompt",
  currentSource: null,
  beforeInstallPrompt: null,
  filePreviewUrl: null,
};

const els = {};

document.addEventListener("DOMContentLoaded", async () => {
  bindElements();
  bindEvents();
  registerServiceWorker();
  await Promise.all([loadDocumentTypes(), loadSecurity(), loadNotice(), hydratePermissionState()]);
  updateOrientationHint();
  updateClientReadiness();
  window.addEventListener("resize", () => {
    updateOrientationHint();
    updateClientReadiness();
  });
  window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
  window.addEventListener("appinstalled", handleAppInstalled);
});

function bindElements() {
  els.startCamera = document.getElementById("start-camera");
  els.captureButton = document.getElementById("capture-button");
  els.retakeButton = document.getElementById("retake-button");
  els.installButton = document.getElementById("install-app");
  els.installHint = document.getElementById("install-hint");
  els.fileInput = document.getElementById("file-input");
  els.preview = document.getElementById("camera-preview");
  els.filePreview = document.getElementById("file-preview");
  els.canvas = document.getElementById("capture-canvas");
  els.cameraState = document.getElementById("camera-state");
  els.documentType = document.getElementById("document-type");
  els.overlay = document.getElementById("capture-overlay");
  els.overlayLabel = document.getElementById("overlay-label");
  els.captureTips = document.getElementById("capture-tips");
  els.tipsTitle = document.getElementById("tips-title");
  els.securityPanel = document.getElementById("security-panel");
  els.noticePanel = document.getElementById("notice-panel");
  els.resultSection = document.getElementById("result-section");
  els.qualityTitle = document.getElementById("quality-title");
  els.qualitySummary = document.getElementById("quality-summary");
  els.qualityStatusLabel = document.getElementById("quality-status-label");
  els.qualityGlare = document.getElementById("quality-glare");
  els.qualityBlur = document.getElementById("quality-blur");
  els.qualityTilt = document.getElementById("quality-tilt");
  els.qualityMessages = document.getElementById("quality-messages");
  els.submissionMeta = document.getElementById("submission-meta");
  els.imageOriginal = document.getElementById("image-original");
  els.imageGlare = document.getElementById("image-glare");
  els.imageGlareLabel = document.getElementById("image-glare-label");
  els.imageDetect = document.getElementById("image-detect");
  els.imageFinal = document.getElementById("image-final");
  els.glareThreshold = document.getElementById("glare-threshold");
  els.glareThresholdValue = document.getElementById("glare-threshold-value");
  els.orientationHint = document.getElementById("orientation-hint");
  els.alignmentHint = document.getElementById("alignment-hint");
  els.statusSource = document.getElementById("status-source");
  els.statusPermission = document.getElementById("status-permission");
  els.statusFrame = document.getElementById("status-frame");
  els.statusSubmit = document.getElementById("status-submit");
  els.readinessCopy = document.getElementById("readiness-copy");
  els.stepItems = Array.from(document.querySelectorAll(".step-item"));
  els.decisionBanner = document.getElementById("decision-banner");
  els.resultNextAction = document.getElementById("result-next-action");
}

function bindEvents() {
  els.startCamera.addEventListener("click", startCamera);
  els.captureButton.addEventListener("click", captureCurrentFrame);
  els.retakeButton.addEventListener("click", resetCaptureFlow);
  els.installButton.addEventListener("click", installPwa);
  els.fileInput.addEventListener("change", handleFileSelection);
  els.documentType.addEventListener("change", onDocumentTypeChange);
  els.glareThreshold.addEventListener("input", () => {
    els.glareThresholdValue.textContent = els.glareThreshold.value;
  });
}

async function loadDocumentTypes() {
  const response = await fetch("/api/document-types");
  state.documentTypes = await response.json();
  els.documentType.innerHTML = "";
  state.documentTypes.forEach((documentType) => {
    const option = document.createElement("option");
    option.value = documentType.key;
    option.textContent = documentType.label;
    els.documentType.append(option);
  });
  state.selectedDocumentType = state.documentTypes[0] || null;
  renderDocumentType();
  updateCaptureSteps("document");
}

async function loadSecurity() {
  const response = await fetch("/api/security");
  const security = await response.json();
  els.securityPanel.innerHTML = "";
  [
    ["전송 구간", security.transport_encryption],
    ["저장 정책", security.at_rest_encryption],
    ["보관 정책", security.retention_policy],
    ["접근 범위", security.access_scope],
  ].forEach(([label, value]) => {
    els.securityPanel.append(renderInfoCard(label, value));
  });
}

async function loadNotice() {
  const response = await fetch("/api/notices");
  const notice = await response.json();
  els.noticePanel.innerHTML = "";
  els.noticePanel.append(renderInfoCard(notice.title, notice.body, notice.updated_at));
}

async function hydratePermissionState() {
  if (!navigator.permissions?.query) {
    state.permissionState = "unknown";
    return;
  }

  try {
    const cameraPermission = await navigator.permissions.query({ name: "camera" });
    state.permissionState = cameraPermission.state;
    cameraPermission.onchange = () => {
      state.permissionState = cameraPermission.state;
      updateClientReadiness();
    };
  } catch (error) {
    console.debug("Camera permission lookup is not supported in this browser.", error);
    state.permissionState = "unknown";
  }
}

function renderDocumentType() {
  const docType = state.selectedDocumentType;
  if (!docType) return;
  els.overlay.style.setProperty("--overlay-ratio", String(docType.aspect_ratio));
  els.overlayLabel.textContent = docType.overlay_label;
  els.tipsTitle.textContent = `${docType.label} 촬영 가이드`;
  els.alignmentHint.textContent = `${docType.label} 전체가 프레임 안에 들어오도록 맞춰 주세요.`;
  els.captureTips.innerHTML = "";
  docType.capture_tips.forEach((tip) => {
    const item = document.createElement("li");
    item.textContent = tip;
    els.captureTips.append(item);
  });
  els.readinessCopy.textContent = `${docType.label} 기준 프레임 비율과 촬영 팁을 적용했습니다. 카메라를 시작하고 프레임 안에 맞춘 뒤 촬영하세요.`;
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

function onDocumentTypeChange(event) {
  state.selectedDocumentType = state.documentTypes.find((item) => item.key === event.target.value) || null;
  renderDocumentType();
  updateCaptureSteps("document");
  updateClientReadiness();
}

function updateOrientationHint() {
  const portraitMode = window.innerHeight > window.innerWidth;
  els.orientationHint.textContent = portraitMode
    ? "세로 모드입니다. 가로로 돌리면 프레임 정렬과 수평 확인이 쉬워집니다."
    : "가로 방향이 감지되었습니다. 프레임 안에 카드 모서리가 모두 들어오도록 맞춰 주세요.";
}

function updateCaptureSteps(activeStep) {
  const activeIndex = stepOrder.indexOf(activeStep);
  els.stepItems.forEach((item) => {
    const itemIndex = stepOrder.indexOf(item.dataset.step);
    item.classList.toggle("is-current", itemIndex === activeIndex);
    item.classList.toggle("is-complete", itemIndex < activeIndex);
  });
}

function updateClientReadiness() {
  els.statusSource.textContent = describeInputSource();
  els.statusPermission.textContent = describePermissionState();
  els.statusFrame.textContent =
    window.innerHeight > window.innerWidth
      ? "세로 모드입니다. 가로 방향으로 돌리면 프레임 정렬이 더 안정적입니다."
      : "가로 모드입니다. 카드 모서리와 프레임 여백을 확인해 주세요.";
  els.statusSubmit.textContent = describeSubmitReadiness();
}

function describeInputSource() {
  if (state.currentSource === "camera" && state.stream) {
    return "후면 카메라 연결 상태입니다. 현재 화면을 바로 촬영할 수 있습니다.";
  }
  if (state.currentSource === "file") {
    return "업로드 파일이 준비되었습니다. 같은 흐름으로 품질 판정과 보정을 진행할 수 있습니다.";
  }
  return "카메라를 시작하거나 파일 업로드를 선택해 주세요.";
}

function describePermissionState() {
  if (state.permissionState === "granted") {
    return "카메라 권한이 허용되었습니다.";
  }
  if (state.permissionState === "denied") {
    return "카메라 권한이 차단되었습니다. 브라우저 설정에서 권한을 허용하거나 파일 업로드를 사용해 주세요.";
  }
  if (state.permissionState === "prompt") {
    return "카메라 시작 시 브라우저가 권한을 요청합니다.";
  }
  return "브라우저가 권한 상태 조회를 지원하지 않습니다. 카메라 시작 버튼으로 직접 확인해 주세요.";
}

function describeSubmitReadiness() {
  if (state.currentSource === "camera" && state.stream) {
    return "프레임 정렬을 맞춘 뒤 촬영 버튼을 눌러 제출 준비를 진행하세요.";
  }
  if (state.currentSource === "file") {
    return "업로드된 이미지를 기준으로 품질 판정과 보정을 바로 진행할 수 있습니다.";
  }
  return "문서 선택과 촬영 소스 준비가 끝나면 제출 가능 여부가 갱신됩니다.";
}

async function startCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    setCameraState("카메라 미지원", "chip chip-retry");
    state.permissionState = "unsupported";
    updateClientReadiness();
    return;
  }

  try {
    stopStream();
    state.stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: "environment" },
      },
      audio: false,
    });
    state.currentSource = "camera";
    state.permissionState = "granted";
    els.preview.srcObject = state.stream;
    els.preview.classList.remove("hidden");
    hideFilePreview();
    setCameraState("카메라 연결됨", "chip chip-ready");
    updateCaptureSteps("camera");
    updateClientReadiness();
  } catch (error) {
    console.error(error);
    state.permissionState = "denied";
    setCameraState("카메라 연결 실패", "chip chip-retry");
    updateClientReadiness();
  }
}

function stopStream() {
  if (!state.stream) return;
  state.stream.getTracks().forEach((track) => track.stop());
  state.stream = null;
  els.preview.srcObject = null;
}

async function captureCurrentFrame() {
  if (state.stream) {
    updateCaptureSteps("align");
    const track = state.stream.getVideoTracks()[0];
    const settings = track.getSettings();
    const width = settings.width || els.preview.videoWidth || 1280;
    const height = settings.height || els.preview.videoHeight || 720;
    els.canvas.width = width;
    els.canvas.height = height;
    const context = els.canvas.getContext("2d");
    context.drawImage(els.preview, 0, 0, width, height);
    const blob = await new Promise((resolve) => els.canvas.toBlob(resolve, "image/jpeg", 0.92));
    if (blob) {
      await submitCapture(blob, `capture-${Date.now()}.jpg`);
    }
    return;
  }

  if (els.fileInput.files?.[0]) {
    updateCaptureSteps("align");
    await submitCapture(els.fileInput.files[0], els.fileInput.files[0].name);
    return;
  }

  setCameraState("카메라 또는 파일 필요", "chip chip-review");
  updateClientReadiness();
}

async function handleFileSelection(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  stopStream();
  state.currentSource = "file";
  setCameraState("파일 업로드 준비됨", "chip chip-review");
  showFilePreview(file);
  updateCaptureSteps("camera");
  updateClientReadiness();
}

function showFilePreview(file) {
  if (state.filePreviewUrl) {
    URL.revokeObjectURL(state.filePreviewUrl);
  }
  state.filePreviewUrl = URL.createObjectURL(file);
  els.filePreview.src = state.filePreviewUrl;
  els.filePreview.classList.remove("hidden");
  els.preview.classList.add("hidden");
}

function hideFilePreview() {
  if (state.filePreviewUrl) {
    URL.revokeObjectURL(state.filePreviewUrl);
    state.filePreviewUrl = null;
  }
  els.filePreview.removeAttribute("src");
  els.filePreview.classList.add("hidden");
  els.preview.classList.remove("hidden");
}

function resetCaptureFlow() {
  els.resultSection.classList.add("hidden");
  els.qualityMessages.innerHTML = "";
  els.submissionMeta.innerHTML = "";
  els.fileInput.value = "";
  state.currentSource = state.stream ? "camera" : null;
  if (!state.stream) {
    hideFilePreview();
    setCameraState("카메라 대기", "chip chip-neutral");
  } else {
    setCameraState("재촬영 준비", "chip chip-review");
  }
  updateCaptureSteps(state.stream ? "align" : "document");
  updateClientReadiness();
}

async function submitCapture(blob, filename) {
  const formData = new FormData();
  formData.append("file", blob, filename);
  formData.append("document_type", state.selectedDocumentType?.key || "resident_id");

  els.captureButton.disabled = true;
  els.captureButton.textContent = "품질 판정 및 보정 중...";
  setCameraState("서버 처리 중", "chip chip-review");
  els.statusSubmit.textContent = "서버에서 품질 판정과 보정 파이프라인을 실행하고 있습니다.";

  try {
    const response = await fetch(`/api/process?glare_threshold=${encodeURIComponent(els.glareThreshold.value)}`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      throw new Error("처리 요청에 실패했습니다.");
    }
    renderResult(await response.json());
  } catch (error) {
    console.error(error);
    setCameraState("처리 실패", "chip chip-retry");
    els.statusSubmit.textContent = "처리에 실패했습니다. 파일 형식과 네트워크 상태를 확인한 뒤 다시 시도해 주세요.";
  } finally {
    els.captureButton.disabled = false;
    els.captureButton.textContent = "현재 화면 촬영";
  }
}

function renderResult(payload) {
  const statusClass =
    payload.quality.status === "ready"
      ? "status-ready"
      : payload.quality.status === "review_recommended"
        ? "status-review"
        : "status-retry";

  els.resultSection.classList.remove("hidden");
  els.decisionBanner.className = `decision-banner ${statusClass}`;
  els.qualityTitle.textContent = payload.quality.status_label;
  els.qualitySummary.textContent = payload.quality.summary;
  els.qualityStatusLabel.textContent = payload.quality.status_label;
  els.qualityGlare.textContent = `${(payload.quality.glare_ratio * 100).toFixed(1)}%`;
  els.qualityBlur.textContent = payload.quality.blur_score.toFixed(1);
  els.qualityTilt.textContent = payload.quality.tilt_angle == null ? "-" : `${payload.quality.tilt_angle}°`;
  els.qualityMessages.innerHTML = "";
  payload.quality.user_messages.forEach((message) => {
    const item = document.createElement("li");
    item.textContent = message;
    els.qualityMessages.append(item);
  });

  els.submissionMeta.innerHTML = "";
  [
    ["제출 ID", payload.submission_id],
    ["문서 유형", payload.document_type],
    ["관리 상태", payload.admin_status],
    ["신분증 감지", payload.card_detected ? "성공" : "실패"],
  ].forEach(([label, value]) => {
    els.submissionMeta.append(renderInfoCard(label, value));
  });

  els.imageOriginal.src = `data:image/jpeg;base64,${payload.original_b64}`;
  els.imageGlare.src = `data:image/jpeg;base64,${payload.after_glare_b64}`;
  els.imageDetect.src = `data:image/jpeg;base64,${payload.after_detect_b64}`;
  els.imageFinal.src = `data:image/jpeg;base64,${payload.final_b64}`;
  els.imageGlareLabel.textContent =
    payload.after_glare_b64 === payload.original_b64 ? "원본 유지" : "빛반사 보정";

  els.resultNextAction.textContent =
    payload.quality.status === "retry_required"
      ? "현재 상태는 재촬영이 더 적합합니다. 가이드를 따라 다시 촬영한 뒤 관리자 콘솔에서 저장 이력을 확인하세요."
      : payload.after_glare_b64 === payload.original_b64
        ? "글레어 보정이 과하다고 판단되어 원본을 유지했습니다. 관리자 콘솔에서 원본과 최종 결과를 함께 확인할 수 있습니다."
        : "현재 제출 상태를 유지한 채 관리자 콘솔에서 저장된 원본과 보정본을 내려받을 수 있습니다.";

  setCameraState(payload.quality.status_label, `chip ${chipClass(payload.quality.status)}`);
  els.statusSubmit.textContent =
    payload.quality.status === "retry_required"
      ? "재촬영을 권장합니다. 조명과 프레임 정렬을 다시 맞춰 주세요."
      : "제출 가능한 상태입니다. 관리자 콘솔에서 결과를 확인할 수 있습니다.";
  updateCaptureSteps("submit");
}

function chipClass(status) {
  if (status === "ready") return "chip-ready";
  if (status === "review_recommended") return "chip-review";
  return "chip-retry";
}

function setCameraState(text, className) {
  els.cameraState.textContent = text;
  els.cameraState.className = className;
}

async function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) {
    els.installHint.textContent = "이 브라우저는 서비스 워커를 지원하지 않아 설치형 캐시 기능을 사용할 수 없습니다.";
    return;
  }

  try {
    await navigator.serviceWorker.register("/sw.js");
  } catch (error) {
    console.error("Service worker registration failed", error);
    els.installHint.textContent = "설치형 캐시 초기화에 실패했습니다. 일반 웹 모드로도 데모는 사용할 수 있습니다.";
  }
}

function handleBeforeInstallPrompt(event) {
  event.preventDefault();
  state.beforeInstallPrompt = event;
  els.installButton.hidden = false;
  els.installHint.textContent = "브라우저가 설치 가능 상태를 감지했습니다. 홈 화면에 추가해 앱처럼 시연할 수 있습니다.";
}

async function installPwa() {
  if (!state.beforeInstallPrompt) {
    els.installHint.textContent = "현재 브라우저에서는 설치 프롬프트를 표시할 수 없습니다.";
    return;
  }

  state.beforeInstallPrompt.prompt();
  await state.beforeInstallPrompt.userChoice;
  state.beforeInstallPrompt = null;
  els.installButton.hidden = true;
  els.installHint.textContent = "설치 프롬프트를 처리했습니다. 필요하면 브라우저 메뉴에서도 홈 화면 추가가 가능합니다.";
}

function handleAppInstalled() {
  els.installButton.hidden = true;
  els.installHint.textContent = "앱이 설치되었습니다. 홈 화면에서도 같은 촬영 흐름으로 데모를 실행할 수 있습니다.";
}
