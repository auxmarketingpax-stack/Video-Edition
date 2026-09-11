const state = {
  clips: [],
  intro: null,
  outro: null,
  music: null,
  exporting: false
};

const $ = (id) => document.getElementById(id);
const els = {
  status: $("statusPill"),
  videoInput: $("videoInput"),
  introInput: $("introInput"),
  outroInput: $("outroInput"),
  musicInput: $("musicInput"),
  clipList: $("clipList"),
  trimSilence: $("trimSilence"),
  filters: $("filters"),
  keepOriginalAudio: $("keepOriginalAudio"),
  musicVolume: $("musicVolume"),
  resolution: $("resolution"),
  captionText: $("captionText"),
  preview: $("preview"),
  exportButton: $("exportButton"),
  downloadLink: $("downloadLink"),
  logOutput: $("logOutput")
};

function log(message) {
  els.logOutput.textContent += `${message}\n`;
  els.logOutput.scrollTop = els.logOutput.scrollHeight;
}

function setStatus(value) {
  els.status.textContent = value;
}

function objectUrl(file) {
  return URL.createObjectURL(file);
}

function formatSeconds(value) {
  if (!Number.isFinite(value)) return "--";
  const minutes = Math.floor(value / 60);
  const seconds = Math.round(value % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function normalizeCaptionText(text) {
  return String(text || "")
    .split(/\r?\n/)
    .flatMap((line) => line.trim().split(/\s+/).filter(Boolean))
    .reduce((rows, word) => {
      const current = rows[rows.length - 1] || [];
      if (current.length >= 3) rows.push([word]);
      else if (current.length === 0) rows[rows.length - 1] = [word];
      else current.push(word);
      return rows;
    }, [[]])
    .filter((row) => row.length)
    .map((row) => row.join(" "));
}

async function durationFromVideo(file) {
  return new Promise((resolve) => {
    const video = document.createElement("video");
    video.preload = "metadata";
    video.muted = true;
    video.src = objectUrl(file);
    video.onloadedmetadata = () => {
      const duration = video.duration || 0;
      URL.revokeObjectURL(video.src);
      resolve(duration);
    };
    video.onerror = () => resolve(0);
  });
}

async function detectSpeechTrim(file, duration) {
  if (!duration) return { start: 0, end: duration };
  try {
    const context = new AudioContext();
    const buffer = await context.decodeAudioData(await file.arrayBuffer());
    const channel = buffer.getChannelData(0);
    const sampleRate = buffer.sampleRate;
    const windowSize = Math.max(1024, Math.floor(sampleRate * 0.05));
    const threshold = 0.015;
    let first = 0;
    let last = channel.length - 1;

    for (let i = 0; i < channel.length; i += windowSize) {
      if (rms(channel, i, windowSize) > threshold) {
        first = i;
        break;
      }
    }
    for (let i = channel.length - windowSize; i >= 0; i -= windowSize) {
      if (rms(channel, i, windowSize) > threshold) {
        last = Math.min(channel.length - 1, i + windowSize);
        break;
      }
    }
    await context.close();

    return {
      start: Math.max(0, first / sampleRate - 0.04),
      end: Math.min(duration, last / sampleRate + 0.22)
    };
  } catch {
    return { start: 0, end: duration };
  }
}

function rms(samples, start, size) {
  let sum = 0;
  let count = 0;
  for (let i = start; i < Math.min(samples.length, start + size); i += 1) {
    sum += samples[i] * samples[i];
    count += 1;
  }
  return Math.sqrt(sum / Math.max(1, count));
}

async function makeClip(file) {
  const duration = await durationFromVideo(file);
  const trim = await detectSpeechTrim(file, duration);
  return {
    id: crypto.randomUUID(),
    file,
    url: objectUrl(file),
    name: file.name,
    duration,
    trimStart: trim.start,
    trimEnd: trim.end
  };
}

function renderClips() {
  els.clipList.innerHTML = "";
  if (!state.clips.length) {
    els.clipList.innerHTML = "<p class=\"empty\">Nenhum vídeo selecionado.</p>";
    return;
  }

  state.clips.forEach((clip, index) => {
    const row = document.createElement("div");
    row.className = "clip";
    row.innerHTML = `
      <div>
        <strong>${index + 1}. ${clip.name}</strong>
        <small>${formatSeconds(clip.trimStart)} - ${formatSeconds(clip.trimEnd)} de ${formatSeconds(clip.duration)}</small>
      </div>
      <button type="button" data-action="up" data-id="${clip.id}">↑</button>
      <button type="button" data-action="down" data-id="${clip.id}">↓</button>
      <button type="button" data-action="remove" data-id="${clip.id}">×</button>
    `;
    els.clipList.appendChild(row);
  });
}

function moveClip(id, direction) {
  const index = state.clips.findIndex((clip) => clip.id === id);
  const target = index + direction;
  if (index < 0 || target < 0 || target >= state.clips.length) return;
  [state.clips[index], state.clips[target]] = [state.clips[target], state.clips[index]];
  renderClips();
}

function removeClip(id) {
  const index = state.clips.findIndex((clip) => clip.id === id);
  if (index < 0) return;
  URL.revokeObjectURL(state.clips[index].url);
  state.clips.splice(index, 1);
  renderClips();
}

async function setMediaSlot(slot, file) {
  if (state[slot]?.url) URL.revokeObjectURL(state[slot].url);
  state[slot] = file
    ? {
        file,
        url: objectUrl(file),
        name: file.name,
        type: file.type.startsWith("image/") ? "image" : "video",
        duration: file.type.startsWith("image/") ? 3 : await durationFromVideo(file)
      }
    : null;
  log(`${slot === "intro" ? "Capa inicial" : slot === "outro" ? "Capa final" : "Música"}: ${file?.name || "removida"}`);
}

function resizeCanvas() {
  const [width, height] = els.resolution.value.split("x").map(Number);
  els.preview.width = width;
  els.preview.height = height;
}

function drawFrame(ctx, source, captions, progress) {
  const canvas = els.preview;
  ctx.save();
  ctx.fillStyle = "#0b1210";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  if (els.filters.checked) {
    ctx.filter = "brightness(1.05) contrast(1.03) saturate(1.34)";
  } else {
    ctx.filter = "none";
  }

  const sw = source.videoWidth || source.naturalWidth || canvas.width;
  const sh = source.videoHeight || source.naturalHeight || canvas.height;
  const scale = Math.max(canvas.width / sw, canvas.height / sh);
  const dw = sw * scale;
  const dh = sh * scale;
  const dx = (canvas.width - dw) / 2;
  const dy = (canvas.height - dh) / 2;
  ctx.drawImage(source, dx, dy, dw, dh);
  ctx.restore();

  if (captions.length) {
    const caption = captions[Math.floor(progress * captions.length) % captions.length];
    if (caption) drawCaption(ctx, caption);
  }
}

function drawCaption(ctx, text) {
  const canvas = els.preview;
  ctx.save();
  ctx.font = `700 ${Math.round(canvas.width * 0.046)}px -apple-system, BlinkMacSystemFont, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.shadowColor = "rgba(0,0,0,0.5)";
  ctx.shadowBlur = 12;
  ctx.shadowOffsetY = 4;
  ctx.fillStyle = "#fff";
  ctx.fillText(text, canvas.width / 2, canvas.height * 0.72);
  ctx.restore();
}

async function waitForVideoReady(video) {
  if (video.readyState >= 2) return;
  await new Promise((resolve, reject) => {
    video.onloadeddata = resolve;
    video.onerror = reject;
  });
}

async function playClip({ clip, ctx, video, captions, audioGain }) {
  video.src = clip.url;
  video.muted = !els.keepOriginalAudio.checked;
  await waitForVideoReady(video);
  const start = els.trimSilence.checked ? clip.trimStart : 0;
  const end = els.trimSilence.checked ? clip.trimEnd : clip.duration;
  video.currentTime = start;
  await video.play();

  if (audioGain) audioGain.gain.value = els.keepOriginalAudio.checked ? 1 : 0;

  const clipDuration = Math.max(0.1, end - start);
  const exportStart = performance.now();
  await new Promise((resolve) => {
    function frame() {
      const elapsed = (performance.now() - exportStart) / 1000;
      const progress = elapsed / clipDuration;
      if (video.currentTime >= end || progress >= 1) {
        video.pause();
        resolve();
        return;
      }
      drawFrame(ctx, video, captions, progress);
      requestAnimationFrame(frame);
    }
    frame();
  });
}

async function playStill({ media, ctx, captions }) {
  if (!media) return;
  if (media.type === "video") {
    await playClip({
      clip: {
        url: media.url,
        duration: media.duration,
        trimStart: 0,
        trimEnd: Math.max(0.1, media.duration)
      },
      ctx,
      video: document.createElement("video"),
      captions,
      audioGain: null
    });
    return;
  }

  const image = new Image();
  image.src = media.url;
  await image.decode();
  const start = performance.now();
  await new Promise((resolve) => {
    function frame() {
      const elapsed = (performance.now() - start) / 1000;
      drawFrame(ctx, image, captions, elapsed / 3);
      if (elapsed >= 3) resolve();
      else requestAnimationFrame(frame);
    }
    frame();
  });
}

async function exportVideo() {
  if (!state.clips.length || state.exporting) return;
  state.exporting = true;
  els.exportButton.disabled = true;
  els.downloadLink.classList.add("hidden");
  els.logOutput.textContent = "";
  setStatus("Exportando");
  resizeCanvas();

  const ctx = els.preview.getContext("2d");
  const captions = normalizeCaptionText(els.captionText.value);
  const audioContext = new AudioContext();
  const destination = audioContext.createMediaStreamDestination();
  const video = document.createElement("video");
  video.playsInline = true;
  video.crossOrigin = "anonymous";
  const videoSource = audioContext.createMediaElementSource(video);
  const videoGain = audioContext.createGain();
  videoSource.connect(videoGain).connect(destination);

  let musicElement = null;
  if (state.music) {
    musicElement = new Audio(state.music.url);
    musicElement.loop = true;
    musicElement.crossOrigin = "anonymous";
    const musicSource = audioContext.createMediaElementSource(musicElement);
    const musicGain = audioContext.createGain();
    musicGain.gain.value = Number(els.musicVolume.value || 0.08);
    musicSource.connect(musicGain).connect(destination);
  }

  const canvasStream = els.preview.captureStream(30);
  const finalStream = new MediaStream([
    ...canvasStream.getVideoTracks(),
    ...destination.stream.getAudioTracks()
  ]);
  const mimeType = MediaRecorder.isTypeSupported("video/mp4")
    ? "video/mp4"
    : MediaRecorder.isTypeSupported("video/webm;codecs=vp9,opus")
      ? "video/webm;codecs=vp9,opus"
      : "video/webm";
  const chunks = [];
  const recorder = new MediaRecorder(finalStream, { mimeType });
  recorder.ondataavailable = (event) => {
    if (event.data.size) chunks.push(event.data);
  };

  recorder.start(1000);
  if (musicElement) await musicElement.play();
  await audioContext.resume();

  try {
    log("Exportando capa inicial...");
    await playStill({ media: state.intro, ctx, captions: [] });
    for (const [index, clip] of state.clips.entries()) {
      log(`Exportando ${index + 1}/${state.clips.length}: ${clip.name}`);
      await playClip({ clip, ctx, video, captions, audioGain: videoGain });
    }
    log("Exportando capa final...");
    await playStill({ media: state.outro, ctx, captions: [] });
  } finally {
    if (musicElement) musicElement.pause();
    recorder.stop();
  }

  await new Promise((resolve) => {
    recorder.onstop = resolve;
  });
  finalStream.getTracks().forEach((track) => track.stop());
  await audioContext.close();

  const blob = new Blob(chunks, { type: mimeType });
  const url = URL.createObjectURL(blob);
  els.downloadLink.href = url;
  els.downloadLink.download = mimeType.includes("mp4") ? "video-edition.mp4" : "video-edition.webm";
  els.downloadLink.classList.remove("hidden");
  log(`Pronto: ${(blob.size / 1024 / 1024).toFixed(1)} MB`);
  setStatus("Pronto");
  els.exportButton.disabled = false;
  state.exporting = false;
}

els.videoInput.addEventListener("change", async () => {
  setStatus("Analisando");
  for (const file of [...els.videoInput.files]) {
    log(`Carregando: ${file.name}`);
    state.clips.push(await makeClip(file));
  }
  renderClips();
  setStatus("Pronto");
});

els.introInput.addEventListener("change", () => setMediaSlot("intro", els.introInput.files[0]));
els.outroInput.addEventListener("change", () => setMediaSlot("outro", els.outroInput.files[0]));
els.musicInput.addEventListener("change", () => setMediaSlot("music", els.musicInput.files[0]));

els.clipList.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  const { action, id } = button.dataset;
  if (action === "up") moveClip(id, -1);
  if (action === "down") moveClip(id, 1);
  if (action === "remove") removeClip(id);
});

els.resolution.addEventListener("change", resizeCanvas);
els.exportButton.addEventListener("click", exportVideo);

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("./sw.js").catch(() => {});
}

resizeCanvas();
renderClips();
