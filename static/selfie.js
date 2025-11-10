const modeRadios = document.querySelectorAll('input[name="selfie_mode"]');
const uploadContainer = document.querySelector('.selfie-upload');
const captureContainer = document.querySelector('.selfie-capture');
const startButton = document.getElementById('start-camera');
const captureButton = document.getElementById('capture-photo');
const videoEl = document.getElementById('selfie-video');
const canvasEl = document.getElementById('selfie-canvas');
const captureInput = document.getElementById('selfie-capture-data');
let mediaStream;

function updateMode() {
  const selected = document.querySelector('input[name="selfie_mode"]:checked');
  if (!selected) return;
  if (selected.value === 'capture') {
    uploadContainer.hidden = true;
    captureContainer.hidden = false;
  } else {
    uploadContainer.hidden = false;
    captureContainer.hidden = true;
    stopCamera();
  }
}

function stopCamera() {
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = undefined;
  }
}

async function startCamera() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } });
    videoEl.srcObject = mediaStream;
  } catch (error) {
    alert('Unable to access your camera. Please allow camera permissions or upload a file instead.');
  }
}

function capturePhoto() {
  if (!mediaStream) {
    alert('Start the camera first.');
    return;
  }
  const width = videoEl.videoWidth;
  const height = videoEl.videoHeight;
  if (!width || !height) {
    alert('Camera is still loading, please try again.');
    return;
  }
  canvasEl.width = width;
  canvasEl.height = height;
  const ctx = canvasEl.getContext('2d');
  ctx.drawImage(videoEl, 0, 0, width, height);
  canvasEl.hidden = false;
  canvasEl.classList.add('preview');
  canvasEl.style.maxWidth = '280px';
  const dataUrl = canvasEl.toDataURL('image/png');
  captureInput.value = dataUrl;
  alert('Photo captured. Submit the form to upload securely.');
}

modeRadios.forEach((radio) => radio.addEventListener('change', updateMode));
if (startButton) {
  startButton.addEventListener('click', startCamera);
}
if (captureButton) {
  captureButton.addEventListener('click', capturePhoto);
}

window.addEventListener('beforeunload', stopCamera);
updateMode();
