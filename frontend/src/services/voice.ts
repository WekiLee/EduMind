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


// ── 语音唤醒模式（连续监听） ──

let _activationStream: MediaStream | null = null;
let _activationCtx: AudioContext | null = null;
let _activationAnalyser: AnalyserNode | null = null;
let _activationAnimId: number | null = null;
let _activationFloor: number | null = null;
let _activationCallback: ((base64: string) => void) | null = null;
let _activationRunning = false;

/** 检查语音唤醒是否正在运行 */
export function isVoiceActivationActive(): boolean {
  return _activationRunning;
}

/** 启动语音唤醒模式 —— 连续监听，有语音时自动录制/发送 */
export async function startVoiceActivation(onTranscribe: (base64: string) => void): Promise<void> {
  if (_activationRunning) return;
  _activationRunning = true;
  _activationCallback = onTranscribe;

  try {
    _activationStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    _activationCtx = new AudioContext();
    _activationAnalyser = _activationCtx.createAnalyser();
    _activationAnalyser.fftSize = 256;
    const sourceNode = _activationCtx.createMediaStreamSource(_activationStream);
    sourceNode.connect(_activationAnalyser);
    _activationFloor = null;

    _listenLoop();
  } catch (err) {
    _activationRunning = false;
    throw err;
  }
}

/** 监听循环：检测说话 → 触发录音 → 录音完成 → 回到监听 */
function _listenLoop() {
  if (!_activationRunning) return;

  // 先做短时间的 VAD 监听 (最多等 30s 无人说话则重启)
  _vadDetectSpeech((base64) => {
    // 检测到语音结束 → 回调发送
    _activationCallback?.(base64);
    // 继续监听下一轮
    _listenLoop();
  }, 30000);
}

/** VAD 监听直到有人说话结束 */
function _vadDetectSpeech(onDone: (base64: string) => void, timeoutMs: number) {
  if (!_activationAnalyser || !_activationRunning) return;

  const dataArray = new Uint8Array(_activationAnalyser.frequencyBinCount);
  const startTime = Date.now();
  let speaking = false;
  let localRecorder: MediaRecorder | null = null;
  let localChunks: Blob[] = [];
  let adapted = false;

  function _waitForSpeech() {
    if (!_activationAnalyser || !_activationRunning) { _cleanupActivation(); return; }

    _activationAnalyser.getByteFrequencyData(dataArray);
    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) { const val = dataArray[i] / 255; sum += val * val; }
    const rms = Math.sqrt(sum / dataArray.length);

    // 自适应底噪（前 500ms）
    if (!adapted && Date.now() - startTime < 500) {
      if (_activationFloor === null || rms < _activationFloor) { _activationFloor = rms; }
      _activationAnimId = requestAnimationFrame(_waitForSpeech);
      return;
    }
    adapted = true;

    const threshold = (_activationFloor ?? 0.03) + VAD_THRESHOLD_OFFSET;

    if (rms > threshold && !speaking) {
      // 检测到说话 — 开始录音
      speaking = true;
      localChunks = [];
      localRecorder = new MediaRecorder(_activationStream!, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm',
      });
      localRecorder.ondataavailable = (e) => { if (e.data.size > 0) localChunks.push(e.data); };
      localRecorder.start(250);

      // 继续监听静音
      let silenceStartMark: number | null = null;
      function _waitForSilence() {
        if (!localRecorder || !_activationAnalyser) return;
        _activationAnalyser.getByteFrequencyData(dataArray);
        let s = 0;
        for (let i = 0; i < dataArray.length; i++) { const v = dataArray[i] / 255; s += v * v; }
        const rms2 = Math.sqrt(s / dataArray.length);

        if (rms2 > threshold) {
          silenceStartMark = null;
          _activationAnimId = requestAnimationFrame(_waitForSilence);
        } else {
          if (silenceStartMark === null) {
            silenceStartMark = Date.now();
          } else if (Date.now() - silenceStartMark > VAD_SILENCE_MS) {
            // 静音超过阈值 → 停止录音
            if (localRecorder && localRecorder.state !== 'inactive') {
              localRecorder.stop();
              localRecorder.onstop = () => {
                const blob = new Blob(localChunks, { type: localRecorder!.mimeType });
                const reader = new FileReader();
                reader.onload = () => {
                  const base64 = (reader.result as string).split(',')[1];
                  onDone(base64);
                };
                reader.readAsDataURL(blob);
              };
            }
            return;
          }
          _activationAnimId = requestAnimationFrame(_waitForSilence);
        }
      }
      _activationAnimId = requestAnimationFrame(_waitForSilence);
      return;
    }

    // 超时检查
    if (Date.now() - startTime > timeoutMs) {
      _activationAnimId = requestAnimationFrame(_waitForSpeech);
      return;
    }

    _activationAnimId = requestAnimationFrame(_waitForSpeech);
  }

  _activationAnimId = requestAnimationFrame(_waitForSpeech);
}

function _cleanupActivation() {
  _activationRunning = false;
  if (_activationAnimId) { cancelAnimationFrame(_activationAnimId); _activationAnimId = null; }
  if (_activationCtx) { _activationCtx.close().catch(() => {}); _activationCtx = null; }
  if (_activationStream) { _activationStream.getTracks().forEach((t) => t.stop()); _activationStream = null; }
  _activationAnalyser = null;
  _activationFloor = null;
}

/** 停止语音唤醒模式 */
export function stopVoiceActivation() {
  _activationRunning = false;
  _activationCallback = null;
  _cleanupActivation();
}





