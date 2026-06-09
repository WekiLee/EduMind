/** 语音录制服务 -- 麦克风采集 -> Blob -> Base64，含 VAD 自动停止 */

let mediaRecorder: MediaRecorder | null = null;
let audioChunks: Blob[] = [];
let audioContext: AudioContext | null = null;
let analyserNode: AnalyserNode | null = null;
let animationId: number | null = null;
let sourceNode: MediaStreamAudioSourceNode | null = null;
let silenceStart: number | null = null;
let ambientNoiseFloor: number | null = null;

const VAD_SILENCE_MS = 1500;
const VAD_THRESHOLD_OFFSET = 0.02;
const VAD_ADAPT_MS = 500;

export function isVoiceSupported(): boolean {
  return !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== 'undefined';
}

let _autoStopped = false;
export function wasAutoStopped(): boolean {
  return _autoStopped;
}

function _clearVadState() {
  if (animationId) { cancelAnimationFrame(animationId); animationId = null; }
  if (audioContext) {
    audioContext.close().catch(() => {});
    audioContext = null;
  }
  analyserNode = null;
  sourceNode = null;
  silenceStart = null;
  ambientNoiseFloor = null;
}

function _startVad(stream: MediaStream, onAutoStop: () => void, onLevelChange?: (level: number) => void) {
  audioContext = new AudioContext();
  sourceNode = audioContext.createMediaStreamSource(stream);
  analyserNode = audioContext.createAnalyser();
  analyserNode.fftSize = 256;
  sourceNode.connect(analyserNode);

  const dataArray = new Uint8Array(analyserNode.frequencyBinCount);
  const startTime = Date.now();

  function _analyze() {
    if (!analyserNode) return;
    analyserNode.getByteFrequencyData(dataArray);
    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) {
      const val = dataArray[i] / 255;
      sum += val * val;
    }
    const rms = Math.sqrt(sum / dataArray.length);

    if (Date.now() - startTime < VAD_ADAPT_MS) {
      if (ambientNoiseFloor === null || rms < ambientNoiseFloor) { ambientNoiseFloor = rms; }
      onLevelChange?.(rms);
      animationId = requestAnimationFrame(_analyze);
      return;
    }

    const threshold = (ambientNoiseFloor ?? 0.03) + VAD_THRESHOLD_OFFSET;
    if (rms > threshold) {
      silenceStart = null;
    } else {
      if (silenceStart === null) {
        silenceStart = Date.now();
      } else if (Date.now() - silenceStart > VAD_SILENCE_MS) {
        _autoStopped = true;
        mediaRecorder?.stop();
        _clearVadState();
        return;
      }
    }
    onLevelChange?.(rms);
    animationId = requestAnimationFrame(_analyze);
  }
  animationId = requestAnimationFrame(_analyze);
}

export async function startRecording(onAutoStop?: () => void, onLevelChange?: (level: number) => void): Promise<void> {
  if (mediaRecorder?.state === 'recording') return;
  _autoStopped = false;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream, {
      mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm',
    });
    mediaRecorder.ondataavailable = (event) => { if (event.data.size > 0) audioChunks.push(event.data); };
    mediaRecorder.start(250);
    _startVad(stream, onAutoStop || (() => {}), onLevelChange);
  } catch (err) {
    _clearVadState();
    mediaRecorder = null; audioChunks = [];
    throw err;
  }
}

export function stopRecording(): Promise<{ blob: Blob; base64: string }> {
  return new Promise((resolve, reject) => {
    if (!mediaRecorder || mediaRecorder.state === 'inactive') { reject(new Error('No recording')); return; }
    _clearVadState();
    mediaRecorder.onstop = () => {
      mediaRecorder!.stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(audioChunks, { type: mediaRecorder!.mimeType });
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = (reader.result as string).split(',')[1];
        resolve({ blob, base64 }); audioChunks = []; mediaRecorder = null;
      };
      reader.onerror = () => { reject(new Error('Encode failed')); audioChunks = []; mediaRecorder = null; };
      reader.readAsDataURL(blob);
    };
    mediaRecorder.onerror = () => {
      _clearVadState(); mediaRecorder?.stream.getTracks().forEach((t) => t.stop());
      reject(new Error('Record failed')); mediaRecorder = null;
    };
    if (mediaRecorder.state !== 'inactive') { mediaRecorder.stop(); }
  });
}

export function cancelRecording() {
  _clearVadState();
  if (mediaRecorder?.state === 'recording') { mediaRecorder.stream.getTracks().forEach((t) => t.stop()); }
  mediaRecorder = null; audioChunks = []; _autoStopped = false;
}
