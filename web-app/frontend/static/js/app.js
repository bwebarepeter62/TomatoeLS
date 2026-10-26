const form = document.getElementById('scan-form');
const imageInput = document.getElementById('image-input');
const previewPanel = document.getElementById('preview-panel');
const previewImage = document.getElementById('preview-image');
const removeImageButton = document.getElementById('remove-image');
const statusBox = document.getElementById('status-box');
const analyzeButton = document.getElementById('analyze-btn');
const resultPanel = document.getElementById('results');
const resultImage = document.getElementById('result-image');
const resultTitle = document.getElementById('result-title');
const confidenceValue = document.getElementById('confidence-value');
const diseaseName = document.getElementById('disease-name');
const diseaseSummary = document.getElementById('disease-summary');
const diseaseType = document.getElementById('disease-type');
const diseaseCause = document.getElementById('disease-cause');
const stopNowList = document.getElementById('stop-now');
const preventFutureList = document.getElementById('prevent-future');
const preventSpreadList = document.getElementById('prevent-spread');
const treatmentsList = document.getElementById('treatments');
const newScanButton = document.getElementById('new-scan');
const farmSelect = document.getElementById('farm-select');
const viewInHistoryBtn = document.getElementById('view-in-history-btn');

let selectedFile = null;
let currentPreviewUrl = '';

function setStatus(message, variant = 'neutral') {
  if (!statusBox) return;
  statusBox.textContent = message;
  statusBox.className = `status-box ${variant}`;
}

function updatePreview(file) {
  if (!file) {
    if (previewPanel) previewPanel.classList.add('hidden');
    if (previewImage) previewImage.src = '';
    return;
  }

  const objectUrl = URL.createObjectURL(file);
  currentPreviewUrl = objectUrl;
  if (previewImage) previewImage.src = objectUrl;
  if (previewPanel) previewPanel.classList.remove('hidden');
}

function clearSelection() {
  if (imageInput) imageInput.value = '';
  selectedFile = null;
  if (currentPreviewUrl) {
    URL.revokeObjectURL(currentPreviewUrl);
    currentPreviewUrl = '';
  }
  if (previewImage) previewImage.src = '';
  if (previewPanel) previewPanel.classList.add('hidden');
  setStatus('No image selected yet. Please choose a tomato leaf photo to begin.');
}

if (imageInput) {
  imageInput.addEventListener('change', (event) => {
    const file = event.target.files && event.target.files[0];
    if (!file) {
      clearSelection();
      return;
    }

    const valid = ['image/png', 'image/jpeg', 'image/webp'];
    if (!valid.includes(file.type)) {
      setStatus('Unsupported image type. Please upload a JPG, PNG, or WEBP file.', 'error');
      clearSelection();
      return;
    }

    selectedFile = file;
    updatePreview(file);
    setStatus('Image ready. Click “Scan leaf” to run the local disease check.', 'success');
  });
}

if (removeImageButton) {
  removeImageButton.addEventListener('click', () => {
    clearSelection();
  });
}

function writeList(target, items) {
  if (!target) return;
  target.innerHTML = '';
  items.forEach((item) => {
    const li = document.createElement('li');
    li.textContent = item;
    target.appendChild(li);
  });
}

function renderResult(data) {
  if (!resultPanel) return;
  resultPanel.classList.remove('hidden');
  if (resultImage) resultImage.src = data.image_url || currentPreviewUrl || '';
  if (resultTitle) resultTitle.textContent = data.available ? 'Diagnosis complete' : 'No confident match';
  if (confidenceValue) confidenceValue.textContent = `${Math.round(data.confidence || 0)}%`;
  if (diseaseName) diseaseName.textContent = data.disease?.name || data.label || 'Healthy leaf';
  if (diseaseSummary) diseaseSummary.textContent = data.disease?.summary || 'No diagnosis was found.';
  if (diseaseType) diseaseType.textContent = (data.disease?.type || 'unknown').toUpperCase();
  if (diseaseCause) diseaseCause.textContent = data.disease?.cause || 'Not available';

  writeList(stopNowList, data.disease?.stopNow || ['Review the image and try again.']);
  writeList(preventFutureList, data.disease?.preventFuture || ['Check plants regularly.']);
  writeList(preventSpreadList, data.disease?.preventSpread || ['Keep equipment clean.']);
  writeList(treatmentsList, data.disease?.treatments || ['No treatment guidance available.']);

  if (viewInHistoryBtn && data.scan_id) {
    viewInHistoryBtn.href = `/history?scan_id=${data.scan_id}`;
  }

  const downloadReportBtn = document.getElementById('download-report-btn');
  if (downloadReportBtn && data.scan_id) {
    downloadReportBtn.href = `/api/scans/${data.scan_id}/report`;
    downloadReportBtn.style.display = 'inline-flex';
  }

  // Smooth scroll into results view
  resultPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

if (form) {
  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    if (!selectedFile) {
      setStatus('Please select an image before scanning.', 'error');
      return;
    }

    const formData = new FormData();
    formData.append('image', selectedFile);

    if (farmSelect && farmSelect.value) {
      formData.append('farm_id', farmSelect.value);
    }

    if (analyzeButton) {
      analyzeButton.disabled = true;
      analyzeButton.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scanning leaf with AI...';
    }
    setStatus('Processing the leaf image. This may take a few seconds.', 'info');

    try {
      const response = await fetch('/api/predict', {
        method: 'POST',
        body: formData,
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || 'Prediction failed.');
      }

      if (payload && payload.available === false) {
        renderResult(payload);
        setStatus('The model did not find a clear disease match. Try a sharper image and scan again.', 'warning');
        return;
      }

      renderResult(payload);
      setStatus('Prediction complete and saved to Scan History. Review guidance below.', 'success');
      if (typeof showToast === 'function') {
        showToast('Leaf scanned and saved to history!', 'success');
      }
    } catch (error) {
      console.error(error);
      setStatus(error.message || 'The scan could not be completed. Please try a different image.', 'error');
    } finally {
      if (analyzeButton) {
        analyzeButton.disabled = false;
        analyzeButton.innerHTML = '<i class="fa-solid fa-magnifying-glass" style="margin-right:8px;"></i> Scan leaf';
      }
    }
  });
}

if (newScanButton) {
  newScanButton.addEventListener('click', () => {
    clearSelection();
    if (resultPanel) resultPanel.classList.add('hidden');
    const scanElem = document.getElementById('scan') || document.querySelector('.scan-panel');
    if (scanElem) {
      window.scrollTo({ top: scanElem.offsetTop - 30, behavior: 'smooth' });
    }
  });
}

// Load available farms for the optional farm selector on scanner page
async function loadFarmsIntoSelect() {
  if (!farmSelect) return;
  try {
    const res = await fetch('/api/farms');
    const data = await res.json();
    if (!res.ok) return;

    const farms = data.farms || [];
    farmSelect.innerHTML = '<option value="">General / Unassigned Farm</option>' + farms.map(f => {
      return `<option value="${f.id}">${f.name}${f.variety ? ' (' + f.variety + ')' : ''}</option>`;
    }).join('');

    // Preselect if farm_id query param exists
    const urlParams = new URLSearchParams(window.location.search);
    const preselected = urlParams.get('farm_id');
    if (preselected) {
      farmSelect.value = preselected;
    }
  } catch (err) {
    console.warn('Could not populate farms dropdown', err);
  }
}

document.addEventListener('DOMContentLoaded', loadFarmsIntoSelect);
