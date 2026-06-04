/** 语音录制服务 —— 麦克风采集 → Blob → Base64 */

let mediaRecorder: MediaRecorder | null = null;
let audioChunks: Blob[] = [];

export function isVoiceSupported(): boolean {
  return !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== 'undefined';
}

export async function startRecording(): Promise<void> {
  if (mediaRecorder?.state === 'recording') return;

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];

    mediaRecorder = new MediaRecorder(stream, {
      mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm',
    });

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) audioChunks.push(event.data);
    };

    mediaRecorder.start(250); // 每 250ms 采集一块
  } catch (err) {
    mediaRecorder = null;
    audioChunks = [];
    throw err; // 由调用方统一处理提示
  }
}

export function stopRecording(): Promise<{ blob: Blob; base64: string }> {
  return new Promise((resolve, reject) => {
    if (!mediaRecorder || mediaRecorder.state === 'inactive') {
      reject(new Error('没有正在进行的录制'));
      return;
    }

    mediaRecorder.onstop = () => {
      // 停止所有音轨
      mediaRecorder!.stream.getTracks().forEach((t) => t.stop());

      const blob = new Blob(audioChunks, { type: mediaRecorder!.mimeType });
      const reader = new FileReader();

      reader.onload = () => {
        const base64 = (reader.result as string).split(',')[1];
        resolve({ blob, base64 });
        audioChunks = [];
        mediaRecorder = null;
      };

      reader.onerror = () => {
        reject(new Error('音频编码失败'));
        audioChunks = [];
        mediaRecorder = null;
      };

      reader.readAsDataURL(blob);
    };

    mediaRecorder.onerror = () => {
      mediaRecorder?.stream.getTracks().forEach((t) => t.stop());
      reject(new Error('录音失败'));
      mediaRecorder = null;
    };

    mediaRecorder.stop();
  });
}
