const modeRadios = document.querySelectorAll('input[name="selfie_mode"]');
const uploadContainer = document.querySelector('.selfie-upload');
const captureContainer = document.querySelector('.selfie-capture');
const startButton = document.getElementById('start-camera');
const captureButton = document.getElementById('capture-photo');
const recordButton = document.getElementById('record-video');
const stopRecordButton = document.getElementById('stop-recording');
const videoEl = document.getElementById('selfie-video');
const canvasEl = document.getElementById('selfie-canvas');
const recordedPreview = document.getElementById('recorded-preview');
const captureInput = document.getElementById('selfie-capture-data');
const videoInput = document.getElementById('selfie-video-data');
const uploadInput = document.querySelector('input[name="selfie_file"]');
let mediaStream;
let mediaRecorder;
let recordedChunks = [];
let recordingTimeout;

function updateMode() {
  const selected = document.querySelector('input[name="selfie_mode"]:checked');
  if (!selected) return;
  if (selected.value === 'capture') {
    uploadContainer.hidden = true;
    captureContainer.hidden = false;
    clearFileUpload();
  } else {
    uploadContainer.hidden = false;
    captureContainer.hidden = true;
    stopCamera();
    clearCaptureArtifacts();
    if (uploadInput) {
      if (selected.value === 'photo') {
        uploadInput.accept = 'image/*';
      } else if (selected.value === 'video') {
        uploadInput.accept = 'video/*';
      } else {
        uploadInput.accept = 'image/*,video/*';
      }
    }
  }
}

function stopCamera() {
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = undefined;
  }
  resetRecordingState();
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
  videoInput.value = '';
  hideRecordedPreview();
  clearFileUpload();
  alert('Photo captured. Submit the form to upload securely.');
}

function startRecording() {
  if (!mediaStream) {
    alert('Start the camera first.');
    return;
  }
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    return;
  }
  recordedChunks = [];
  const options = { mimeType: 'video/webm;codecs=vp8' };
  try {
    mediaRecorder = new MediaRecorder(mediaStream, options);
  } catch (err) {
    mediaRecorder = new MediaRecorder(mediaStream);
  }

  mediaRecorder.ondataavailable = (event) => {
    if (event.data && event.data.size > 0) {
      recordedChunks.push(event.data);
    }
  };

  mediaRecorder.onstop = () => {
    if (recordingTimeout) {
      clearTimeout(recordingTimeout);
      recordingTimeout = undefined;
    }
    if (recordButton) {
      recordButton.disabled = false;
    }
    if (stopRecordButton) {
      stopRecordButton.disabled = true;
    }
    const chunks = recordedChunks.slice();
    recordedChunks = [];
    const mimeType = mediaRecorder ? mediaRecorder.mimeType : 'video/webm';
    mediaRecorder = undefined;
    if (!chunks.length) {
      return;
    }
    const blob = new Blob(chunks, { type: mimeType || 'video/webm' });
    if (!blob.size) {
      return;
    }
    const reader = new FileReader();
    reader.onloadend = () => {
      videoInput.value = reader.result;
      captureInput.value = '';
      if (canvasEl) {
        canvasEl.hidden = true;
      }
      if (recordedPreview) {
        recordedPreview.src = reader.result;
        recordedPreview.hidden = false;
        recordedPreview.controls = true;
      }
      clearFileUpload();
      alert('Video recorded. Submit the form to upload securely.');
    };
    reader.readAsDataURL(blob);
  };

  try {
    mediaRecorder.start();
    if (recordButton) {
      recordButton.disabled = true;
    }
    if (stopRecordButton) {
      stopRecordButton.disabled = false;
    }
    recordingTimeout = setTimeout(() => {
      if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        alert('Recording stopped after 30 seconds.');
      }
    }, 30000);
  } catch (error) {
    alert('Recording could not be started. Please try again or upload a video instead.');
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop();
  }
}

function resetRecordingState() {
  if (mediaRecorder) {
    if (mediaRecorder.state === 'recording') {
      mediaRecorder.stop();
      return;
    }
    mediaRecorder = undefined;
  }
  if (recordingTimeout) {
    clearTimeout(recordingTimeout);
    recordingTimeout = undefined;
  }
  if (recordButton) {
    recordButton.disabled = false;
  }
  if (stopRecordButton) {
    stopRecordButton.disabled = true;
  }
}

function hideRecordedPreview() {
  if (recordedPreview) {
    recordedPreview.pause();
    recordedPreview.removeAttribute('src');
    recordedPreview.load();
    recordedPreview.hidden = true;
  }
}

function clearCaptureArtifacts() {
  captureInput.value = '';
  videoInput.value = '';
  if (canvasEl) {
    canvasEl.hidden = true;
  }
  hideRecordedPreview();
}

function clearFileUpload() {
  if (uploadInput) {
    uploadInput.value = '';
  }
}

modeRadios.forEach((radio) => radio.addEventListener('change', updateMode));
if (startButton) {
  startButton.addEventListener('click', startCamera);
}
if (captureButton) {
  captureButton.addEventListener('click', capturePhoto);
}
if (recordButton) {
  recordButton.addEventListener('click', startRecording);
}
if (stopRecordButton) {
  stopRecordButton.addEventListener('click', stopRecording);
}

window.addEventListener('beforeunload', stopCamera);
updateMode();
