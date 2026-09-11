const { app, BrowserWindow, dialog, ipcMain } = require("electron");
const path = require("path");
const fs = require("fs");
const { execFileSync, spawn } = require("child_process");

const repoRoot = path.resolve(__dirname, "..");
const draftsRoot = path.join(
  process.env.LOCALAPPDATA || "",
  "CapCut",
  "User Data",
  "Projects",
  "com.lveditor.draft"
);
const bundledLibraryRoot = path.join(__dirname, "library");
const bundledFfprobePath = path.join(repoRoot, "runtime", "ffmpeg", "bin", "ffprobe.exe");

let mainWindow;
let activeProcess = null;
const videoExtensions = new Set([".mp4", ".mov", ".m4v", ".avi", ".mkv"]);
const musicExtensions = new Set([".mp3", ".wav", ".m4a", ".aac", ".mp4", ".mov"]);
const imageExtensions = new Set([".jpg", ".jpeg", ".png", ".webp"]);
const coverExtensions = new Set([...imageExtensions, ...videoExtensions]);

function userLibraryRoot() {
  return path.join(app.getPath("documents"), "Video Edition", "Biblioteca");
}

function copyDirectoryMissingOnly(source, destination) {
  if (!fs.existsSync(source)) return;
  fs.mkdirSync(destination, { recursive: true });
  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    const sourcePath = path.join(source, entry.name);
    const destinationPath = path.join(destination, entry.name);
    if (entry.isDirectory()) {
      copyDirectoryMissingOnly(sourcePath, destinationPath);
    } else if (entry.isFile() && !fs.existsSync(destinationPath)) {
      fs.copyFileSync(sourcePath, destinationPath);
    }
  }
}

function ensureUserLibrary() {
  const target = userLibraryRoot();
  copyDirectoryMissingOnly(bundledLibraryRoot, target);
  for (const folder of ["Musicas", "Finais", path.join("Projetos Base", "Video Edition Base")]) {
    fs.mkdirSync(path.join(target, folder), { recursive: true });
  }
  return target;
}

function libraryPath(...parts) {
  return path.join(ensureUserLibrary(), ...parts);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1180,
    height: 780,
    minWidth: 980,
    minHeight: 680,
    title: "Video Edition",
    icon: path.join(__dirname, "assets", "icon.png"),
    backgroundColor: "#f6f7f3",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));
}

function slugify(value) {
  return String(value || "projeto")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .toLowerCase() || "projeto";
}

function safeProfileName(projectName) {
  return `${slugify(projectName)}-${Date.now()}.json`;
}

function defaultProjectName(folderPath) {
  return folderPath ? path.basename(folderPath) : "";
}

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function countVideos(folderPath) {
  try {
    return fs
      .readdirSync(folderPath, { withFileTypes: true })
      .filter((entry) => entry.isFile() && videoExtensions.has(path.extname(entry.name).toLowerCase()))
      .length;
  } catch {
    return 0;
  }
}

function listMediaFiles(folderPath, extensions, recursive = true, limit = 500) {
  const results = [];
  function walk(currentFolder) {
    if (results.length >= limit) return;
    let entries = [];
    try {
      entries = fs.readdirSync(currentFolder, { withFileTypes: true });
    } catch {
      return;
    }

    for (const entry of entries) {
      if (results.length >= limit) return;
      const fullPath = path.join(currentFolder, entry.name);
      if (entry.isDirectory() && recursive) {
        walk(fullPath);
      } else if (entry.isFile() && extensions.has(path.extname(entry.name).toLowerCase())) {
        results.push(fullPath);
      }
    }
  }
  walk(folderPath);
  return results;
}

function mediaDurationSeconds(filePath) {
  try {
    const output = execFileSync(
      fs.existsSync(bundledFfprobePath) ? bundledFfprobePath : "ffprobe",
      [
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        filePath
      ],
      { encoding: "utf8", windowsHide: true, timeout: 7000 }
    );
    const duration = Number.parseFloat(output.trim());
    return Number.isFinite(duration) ? duration : 0;
  } catch {
    return 0;
  }
}

function estimateVideoDurationSeconds(folderPath) {
  const files = listMediaFiles(folderPath, videoExtensions, false, 200);
  const measured = files.map(mediaDurationSeconds).filter((value) => value > 0);
  if (measured.length) return measured.reduce((sum, value) => sum + value, 0);
  return Math.max(15, files.length * 15);
}

function profileForTheme(sourceFolder, projectName) {
  const text = normalizeText(`${sourceFolder} ${projectName}`);
  if (text.includes("beleza")) {
    return {
      label: "beleza",
      preferred: ["flowers", "beautiful", "sweet", "chic", "good", "paradise", "felicidade"],
      avoid: ["rock", "game", "cars", "misterio", "taping"],
      volumeDb: -22
    };
  }
  if (text.includes("chaveiro")) {
    return {
      label: "chaveiro",
      preferred: ["roadtrip", "fast", "cars", "loaded", "check", "line", "tapping"],
      avoid: ["flowers", "beach", "sweet", "misterio"],
      volumeDb: -24
    };
  }
  if (text.includes("oftalmologista") || text.includes("oftalmo")) {
    return {
      label: "oftalmologista",
      preferred: ["landscapes", "skyline", "paradise", "moment", "calm", "beach"],
      avoid: ["rock", "game", "cars", "misterio"],
      volumeDb: -20
    };
  }
  if (text.includes("prolab")) {
    return {
      label: "prolab",
      preferred: ["feels", "next", "good", "moment", "line", "check", "hollywood"],
      avoid: ["rock", "game", "misterio"],
      volumeDb: -23
    };
  }
  return {
    label: "geral",
    preferred: ["instrumental", "good", "moment", "landscapes", "flowers", "roadtrip"],
    avoid: ["voz", "voice", "depoimento", "whatsapp", "screenrecording", "audio"],
    volumeDb: -22
  };
}

function scoreMusicFile(filePath, context) {
  const fileName = path.basename(filePath);
  const text = normalizeText(fileName);
  const duration = mediaDurationSeconds(filePath);
  const stat = fs.statSync(filePath);
  let score = 0;
  const reasons = [];

  if (text.includes("instrumental")) {
    score += 35;
    reasons.push("instrumental");
  }
  for (const keyword of context.theme.preferred) {
    if (text.includes(keyword)) {
      score += 18;
      reasons.push(`tema ${keyword}`);
    }
  }
  for (const keyword of context.theme.avoid) {
    if (text.includes(keyword)) score -= 25;
  }
  if (/\bfeat\b|voz|voice|depoimento|whatsapp|screenrecording|audio/.test(text)) score -= 30;

  if (duration > 0) {
    if (duration >= context.videoDuration) {
      score += 20;
      reasons.push("cobre o video inteiro");
    } else if (duration >= context.videoDuration * 0.55) {
      score += 8;
      reasons.push("duracao aceitavel");
    } else {
      score -= 12;
    }

    if (duration < 8) score -= 20;
    if (duration > 600) score -= 8;
  } else {
    score += Math.min(8, stat.size / 8_000_000);
  }

  return {
    path: filePath,
    name: fileName,
    score,
    duration,
    reason: reasons.slice(0, 3).join(", ") || "melhor compatibilidade geral"
  };
}

function analyzeMusicFolderForVideo(sourceFolder, musicFolder, projectName, targetDurationSeconds = 0) {
  if (!musicFolder || !fs.existsSync(musicFolder)) {
    throw new Error("Selecione uma pasta de musicas valida.");
  }
  const files = listMediaFiles(musicFolder, musicExtensions, true, 500);
  if (!files.length) return null;

  const theme = profileForTheme(sourceFolder, projectName || defaultProjectName(sourceFolder));
  const videoDuration = targetDurationSeconds > 0 ? targetDurationSeconds : estimateVideoDurationSeconds(sourceFolder);
  const scored = files
    .map((filePath) => scoreMusicFile(filePath, { theme, videoDuration }))
    .sort((a, b) => b.score - a.score);
  const best = scored[0];
  if (!best) return null;
  return {
    path: best.path,
    name: best.name,
    volumeDb: theme.volumeDb,
    durationSeconds: best.duration,
    score: Math.round(best.score),
    reason: `${theme.label}; ${best.reason}`
  };
}

function existingMusicPath(fileName) {
  const candidates = [
    path.join(libraryPath("Musicas"), fileName),
    path.join("C:\\Wendller", fileName)
  ];
  return candidates.find((candidate) => fs.existsSync(candidate)) || "";
}

function suggestMusicForFolder(folderPath) {
  const normalized = normalizeText(folderPath);
  const candidates = [
    { match: ["beleza"], file: "Flowers (Instrumental).mp4", volumeDb: -22 },
    { match: ["chaveiro"], file: "Roadtrip (Instrumental).mp4", volumeDb: -24 },
    { match: ["oftalmologista", "oftalmo"], file: "Landscapes (Instrumental).mp4", volumeDb: -20 },
    { match: ["prolab\\a", "prolab/a", "prolab a"], file: "Feels Good (Instrumental).mp4", volumeDb: -24 },
    { match: ["prolab\\b", "prolab/b", "prolab b"], file: "Next To Me (Instrumental).mp4", volumeDb: -23 }
  ];

  const selected = candidates.find((item) => item.match.some((term) => normalized.includes(term)));
  const fallback = selected || { file: "Landscapes (Instrumental).mp4", volumeDb: -22 };
  const musicPath = existingMusicPath(fallback.file);
  return {
    path: musicPath,
    volumeDb: fallback.volumeDb,
    name: fallback.file
  };
}

function getDefaultTemplateDraft() {
  const libraryTemplate = libraryPath("Projetos Base", "Video Edition Base");
  if (fs.existsSync(path.join(libraryTemplate, "draft_content.json"))) return libraryTemplate;
  const preferred = path.join(draftsRoot, "Oftalmologista");
  if (fs.existsSync(preferred)) return preferred;
  return draftsRoot;
}

function workflowPreset(mode) {
  if (mode === "mobile") {
    return {
      mode: "mobile",
      effects: [
        { name: "4K", intensity: 13 },
        { name: "Vivido", intensity: 34 },
        { name: "Olhar da folha", intensity: 21 }
      ],
      adjustments: {
        brightness: 5,
        temperature: 5,
        black: 3
      },
      captionStyle: "plain"
    };
  }
  return {
    mode: "desktop",
    effects: [
      { name: "Aprimorar", intensity: 42 },
      { name: "4K", intensity: 13 },
      { name: "Retrô americano", intensity: 34 },
      { name: "Mar sem nuvens", intensity: 21 },
      { name: "Calma", intensity: 26 }
    ],
    adjustments: {
      light_sensation: 5,
      temperature: 5,
      tone: -3,
      shadow: -3,
      white: 3
    },
    captionStyle: "styled"
  };
}

function makeProfile(input) {
  const projectName = input.projectName || defaultProjectName(input.sourceFolder);
  const capcut = input.actions || {};
  const preset = workflowPreset(String(input.workflowMode || "desktop").trim().toLowerCase());
  const music = input.music || {};
  const covers = input.covers || {};
  const musicPath = String(music.path || "").trim();
  const introCoverPath = String(covers.introPath || "").trim();
  const outroCoverPath = String(covers.outroPath || "").trim();
  const endingPreset = String(input.endingPreset || "auto").trim();
  const workspaceRoot = path.join(app.getPath("userData"), "automation-work", slugify(projectName));
  const exclusions = String(input.excludeFiles || "")
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);

  return {
    name: slugify(projectName),
    sourceFolder: input.sourceFolder,
    workspaceRoot,
    excludeFiles: exclusions,
    preparation: {
      recursive: Boolean(input.recursive),
      stagingFolder: "prepared",
      manifestFolder: "manifests"
    },
    silence: {
      enabled: Boolean(capcut.trim),
      useSpeechBoundaries: true,
      noiseThresholdDb: -33,
      minimumDurationSeconds: 0.18,
      keepHeadPaddingSeconds: 0.02,
      keepTailPaddingSeconds: 0.18,
      extraHeadTrimSeconds: 0.0,
      extraTailTrimSeconds: 0.0,
      maxHeadTrimSeconds: 2.0,
      maxTailTrimSeconds: 4.0,
      speechHeadPaddingSeconds: 0.02,
      speechHeadTrimBiasSeconds: 0.0,
      speechHeadTrimBiasAfterDiscardSeconds: 0.0,
      speechTailPaddingSeconds: 0.22,
      discardLeadingSegmentBeforeSeconds: 0.2,
      discardLeadingSegmentMaxWords: 1,
      discardLeadingSegmentMaxDurationSeconds: 0.45,
      discardLeadingSegmentMinGapSeconds: 0.8
    },
    capcut: {
      projectName,
      workflowMode: preset.mode,
      effectsEnabled: Boolean(capcut.effects),
      adjustmentsEnabled: Boolean(capcut.adjustments),
      effects: preset.effects,
      adjustments: preset.adjustments,
      audio: {
        enabled: Boolean(capcut.audio),
        muteVideo: Boolean(capcut.muteVideo),
        noiseReduction: true,
        normalizeVolume: true,
        volumeDb: Number(input.videoVolumeDb ?? 8.9)
      },
      captions: {
        enabled: Boolean(capcut.captions),
        minWordsPerLine: 1,
        maxWordsPerLine: 3,
        style: preset.captionStyle
      },
      transitions: {
        enabled: Boolean(capcut.transitions),
        name: "Esmaecimento preto"
      },
      ending: {
        enabled: endingPreset !== "none",
        preset: endingPreset,
        assets: {
          paxNaRuaBackground: libraryPath("Finais", "Fundo Pax na Rua.mp4"),
          paxNaRuaOverlay: libraryPath("Finais", "PaxNaRua.mp4"),
          momentoPaxSaude: libraryPath("Finais", "Momento Pax Saúde-.mp4"),
          paxRioVerde: libraryPath("Finais", "Final Pax Rio Verde.mp4"),
          paxMontividiu: libraryPath("Finais", "Final Montividiu.mp4")
        }
      },
      covers: {
        intro: {
          enabled: Boolean(introCoverPath),
          path: introCoverPath,
          durationSeconds: Number(covers.introDurationSeconds ?? 3)
        },
        outro: {
          enabled: Boolean(outroCoverPath),
          path: outroCoverPath,
          durationSeconds: Number(covers.outroDurationSeconds ?? 3)
        }
      },
      backgroundMusic: {
        enabled: Boolean(capcut.music && musicPath),
        path: musicPath,
        volumeDb: Number(music.volumeDb ?? -22.0),
        startMode: "auto_continuous"
      }
    }
  };
}

function disableBackgroundMusic(profile) {
  profile.capcut.backgroundMusic.enabled = false;
  profile.capcut.backgroundMusic.path = "";
}

function enableBackgroundMusic(profile, musicPath, volumeDb) {
  profile.capcut.preserveExistingVideoEdits = true;
  profile.capcut.backgroundMusic.enabled = true;
  profile.capcut.backgroundMusic.path = musicPath;
  profile.capcut.backgroundMusic.volumeDb = Number(volumeDb ?? -22.0);
  profile.capcut.backgroundMusic.startMode = "auto_continuous";
}

function writeProfile(profileDir, projectName, profile) {
  fs.mkdirSync(profileDir, { recursive: true });
  const profilePath = path.join(profileDir, safeProfileName(projectName));
  fs.writeFileSync(profilePath, JSON.stringify(profile, null, 2), "utf8");
  return profilePath;
}

function parseLastJsonObject(text) {
  const trimmed = String(text || "").trim();
  for (let start = trimmed.indexOf("{"); start >= 0; start = trimmed.indexOf("{", start + 1)) {
    try {
      return JSON.parse(trimmed.slice(start));
    } catch {
      continue;
    }
  }
  return null;
}

function pythonCandidates() {
  return [
    { command: path.join(repoRoot, "python", "python.exe"), prefixArgs: [] },
    { command: path.join(repoRoot, "runtime", "python", "python.exe"), prefixArgs: [] },
    { command: "py", prefixArgs: ["-3"] },
    { command: "python", prefixArgs: [] },
    { command: "python3", prefixArgs: [] }
  ];
}

function resolvePythonCommand() {
  for (const candidate of pythonCandidates()) {
    if (path.isAbsolute(candidate.command) && !fs.existsSync(candidate.command)) continue;
    try {
      execFileSync(candidate.command, [...candidate.prefixArgs, "--version"], {
        encoding: "utf8",
        windowsHide: true,
        timeout: 5000
      });
      return candidate;
    } catch {
      continue;
    }
  }
  throw new Error(
    "Python nao encontrado neste computador. Instale Python 3 pelo site python.org e marque a opcao 'Add python.exe to PATH', ou instale pelo Microsoft Store e abra o Video Edition novamente."
  );
}

function runPythonScript(scriptPath, args) {
  return new Promise((resolve, reject) => {
    const python = resolvePythonCommand();
    activeProcess = spawn(python.command, [...python.prefixArgs, scriptPath, ...args], {
      cwd: repoRoot,
      env: {
        ...process.env,
        PYTHONIOENCODING: "utf-8"
      },
      windowsHide: true
    });

    let output = "";
    let errorOutput = "";

    activeProcess.stdout.on("data", (data) => {
      const text = data.toString();
      output += text;
      text.split(/\r?\n/).filter(Boolean).forEach((line) => sendLog("workflow-log", { type: "out", line }));
    });

    activeProcess.stderr.on("data", (data) => {
      const text = data.toString();
      errorOutput += text;
      text.split(/\r?\n/).filter(Boolean).forEach((line) => sendLog("workflow-log", { type: "warn", line }));
    });

    activeProcess.on("error", (error) => {
      activeProcess = null;
      reject(error);
    });

    activeProcess.on("close", (code) => {
      activeProcess = null;
      if (code !== 0) {
        reject(new Error(errorOutput || `Processo finalizado com codigo ${code}`));
        return;
      }
      resolve({ output, parsed: parseLastJsonObject(output) });
    });
  });
}

function sendLog(channel, payload) {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  mainWindow.webContents.send(channel, payload);
}

ipcMain.handle("select-folder", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ["openDirectory"],
    title: "Selecionar pasta dos videos"
  });
  if (result.canceled || !result.filePaths[0]) return null;
  const folderPath = result.filePaths[0];
  return {
    path: folderPath,
    projectName: defaultProjectName(folderPath),
    videoCount: countVideos(folderPath),
    suggestedMusic: suggestMusicForFolder(folderPath)
  };
});

ipcMain.handle("select-template", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ["openDirectory"],
    title: "Selecionar projeto base do CapCut",
    defaultPath: getDefaultTemplateDraft()
  });
  if (result.canceled || !result.filePaths[0]) return null;
  return result.filePaths[0];
});

ipcMain.handle("select-music", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ["openFile"],
    title: "Selecionar musica",
    filters: [
      { name: "Audio e video", extensions: ["mp3", "wav", "m4a", "aac", "mp4", "mov"] },
      { name: "Todos", extensions: ["*"] }
    ],
    defaultPath: libraryPath("Musicas")
  });
  if (result.canceled || !result.filePaths[0]) return null;
  return result.filePaths[0];
});

ipcMain.handle("select-music-folder", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ["openDirectory"],
    title: "Selecionar pasta de musicas",
    defaultPath: libraryPath("Musicas")
  });
  if (result.canceled || !result.filePaths[0]) return null;
  return result.filePaths[0];
});

ipcMain.handle("select-cover-media", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ["openFile"],
    title: "Selecionar capa",
    filters: [
      { name: "Imagem ou video", extensions: ["jpg", "jpeg", "png", "webp", "mp4", "mov", "m4v", "avi", "mkv"] },
      { name: "Todos", extensions: ["*"] }
    ]
  });
  if (result.canceled || !result.filePaths[0]) return null;
  return result.filePaths[0];
});

ipcMain.handle("analyze-music-folder", async (_event, input) => {
  return analyzeMusicFolderForVideo(input.sourceFolder, input.musicFolder, input.projectName);
});

ipcMain.handle("get-defaults", async () => ({
  templateDraft: getDefaultTemplateDraft(),
  draftsRoot,
  repoRoot,
  libraryRoot: ensureUserLibrary(),
  musicFolder: libraryPath("Musicas"),
  endingsFolder: libraryPath("Finais"),
  baseProjectsFolder: libraryPath("Projetos Base")
}));

ipcMain.handle("run-workflow", async (_event, input) => {
  if (activeProcess) {
    throw new Error("Ja existe uma execucao em andamento.");
  }
  if (!input.sourceFolder || !fs.existsSync(input.sourceFolder)) {
    const receivedPath = input.sourceFolder ? ` Caminho recebido: ${input.sourceFolder}` : "";
    throw new Error(`Selecione uma pasta valida de videos.${receivedPath}`);
  }
  if (!input.templateDraft || !fs.existsSync(input.templateDraft)) {
    throw new Error("Selecione um projeto base valido do CapCut.");
  }
  for (const [label, coverPath] of [
    ["capa inicial", input.covers?.introPath],
    ["capa final", input.covers?.outroPath]
  ]) {
    const cleanedPath = String(coverPath || "").trim();
    if (!cleanedPath) continue;
    const extension = path.extname(cleanedPath).toLowerCase();
    if (!fs.existsSync(cleanedPath) || !coverExtensions.has(extension)) {
      throw new Error(`Selecione uma imagem ou video valido para ${label}. Caminho recebido: ${cleanedPath}`);
    }
  }
  const wantsMusic = Boolean(input.actions?.music);
  const providedMusicPath = String(input.music?.path || "").trim();
  const providedMusicFolder = String(input.music?.folder || "").trim();
  if (wantsMusic && providedMusicPath && !fs.existsSync(providedMusicPath)) {
    throw new Error(`Selecione uma faixa de musica valida ou desmarque Musica. Caminho recebido: ${providedMusicPath}`);
  }
  if (wantsMusic && !providedMusicPath && (!providedMusicFolder || !fs.existsSync(providedMusicFolder))) {
    const receivedPath = providedMusicFolder ? ` Caminho recebido: ${providedMusicFolder}` : "";
    throw new Error(`Selecione uma pasta de musicas valida, uma faixa de musica valida ou desmarque Musica.${receivedPath}`);
  }

  const profile = makeProfile(input);
  const profileDir = path.join(app.getPath("userData"), "profiles");
  if (wantsMusic) disableBackgroundMusic(profile);
  const profilePath = writeProfile(profileDir, profile.capcut.projectName, profile);

  const createScriptPath = path.join(repoRoot, "scripts", "Create-CapCutProjectFromProfile.py");
  const createArgs = [
    "--profile",
    profilePath,
    "--drafts-root",
    draftsRoot,
    "--template-draft",
    input.templateDraft
  ];

  sendLog("workflow-log", { type: "info", line: `Perfil: ${profilePath}` });
  sendLog("workflow-log", { type: "info", line: `Projeto: ${profile.capcut.projectName}` });

  const createResult = await runPythonScript(createScriptPath, createArgs);
  let selectedMusic = null;

  if (wantsMusic) {
    const draftDirectory = createResult.parsed?.draftDirectory;
    const finalDurationSeconds = Number(createResult.parsed?.durationUs || 0) / 1_000_000;
    let musicPath = providedMusicPath;
    let musicVolumeDb = Number(input.music?.volumeDb ?? -22);

    if (!musicPath) {
      selectedMusic = analyzeMusicFolderForVideo(
        input.sourceFolder,
        providedMusicFolder,
        profile.capcut.projectName,
        finalDurationSeconds
      );
      if (!selectedMusic?.path) {
        throw new Error("Nenhuma musica compativel encontrada depois da criacao do projeto.");
      }
      musicPath = selectedMusic.path;
      musicVolumeDb = selectedMusic.volumeDb;
      sendLog("workflow-log", { type: "info", line: `Musica escolhida depois do projeto: ${selectedMusic.name}` });
      sendLog("workflow-log", { type: "info", line: `Motivo: ${selectedMusic.reason}` });
    } else {
      selectedMusic = {
        path: musicPath,
        name: path.basename(musicPath),
        volumeDb: musicVolumeDb,
        reason: "faixa escolhida manualmente"
      };
      sendLog("workflow-log", { type: "info", line: `Musica manual aplicada depois do projeto: ${selectedMusic.name}` });
    }

    if (!draftDirectory || !fs.existsSync(draftDirectory)) {
      throw new Error("Projeto criado, mas nao foi possivel localizar o draft para aplicar musica.");
    }

    const musicProfile = makeProfile(input);
    enableBackgroundMusic(musicProfile, musicPath, musicVolumeDb);
    const musicProfilePath = writeProfile(profileDir, `${musicProfile.capcut.projectName}-musica`, musicProfile);
    const applyScriptPath = path.join(repoRoot, "scripts", "Apply-CapCutDraftProfile.py");
    await runPythonScript(applyScriptPath, ["--profile", musicProfilePath, "--draft-dir", draftDirectory]);
  }

  return { profilePath, output: createResult.output, project: createResult.parsed, selectedMusic };
});

ipcMain.handle("stop-workflow", async () => {
  if (!activeProcess) return false;
  activeProcess.kill();
  activeProcess = null;
  return true;
});

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
