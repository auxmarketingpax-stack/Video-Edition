const state = {
  sourceFolder: "",
  templateDraft: "",
  running: false
};

const $ = (id) => document.getElementById(id);

const els = {
  status: $("statusPill"),
  selectFolder: $("selectFolder"),
  selectFolderPath: $("selectFolderPath"),
  sourceFolderPath: $("sourceFolderPath"),
  folderTitle: $("folderTitle"),
  folderMeta: $("folderMeta"),
  projectName: $("projectName"),
  templateDraft: $("templateDraft"),
  selectTemplate: $("selectTemplate"),
  excludeFiles: $("excludeFiles"),
  selectMusic: $("selectMusic"),
  selectMusicFolder: $("selectMusicFolder"),
  selectIntroCover: $("selectIntroCover"),
  selectOutroCover: $("selectOutroCover"),
  musicFolderPath: $("musicFolderPath"),
  musicPath: $("musicPath"),
  introCoverPath: $("introCoverPath"),
  outroCoverPath: $("outroCoverPath"),
  endingPreset: $("endingPreset"),
  videoVolumeDb: $("videoVolumeDb"),
  musicVolumeDb: $("musicVolumeDb"),
  runButton: $("runButton"),
  stopButton: $("stopButton"),
  clearLog: $("clearLog"),
  logOutput: $("logOutput")
};

const actions = {
  trim: $("actionTrim"),
  audio: $("actionAudio"),
  muteVideo: $("actionMuteVideo"),
  effects: $("actionEffects"),
  adjustments: $("actionAdjustments"),
  captions: $("actionCaptions"),
  transitions: $("actionTransitions"),
  music: $("actionMusic")
};

function setRunning(running) {
  state.running = running;
  els.runButton.disabled = running;
  els.stopButton.disabled = !running;
  els.status.textContent = running ? "Rodando" : "Pronto";
  els.status.classList.toggle("running", running);
}

function appendLog(line, type = "info") {
  const prefix = type === "warn" ? "! " : type === "out" ? "> " : "";
  els.logOutput.textContent += `${prefix}${line}\n`;
  els.logOutput.scrollTop = els.logOutput.scrollHeight;
}

function payload() {
  const sourceFolder = els.sourceFolderPath.value.trim() || state.sourceFolder;
  const workflowMode = document.querySelector("input[name='workflowMode']:checked")?.value || "desktop";
  return {
    sourceFolder,
    workflowMode,
    projectName: els.projectName.value.trim(),
    templateDraft: els.templateDraft.value.trim(),
    excludeFiles: els.excludeFiles.value,
    recursive: $("recursive").checked,
    endingPreset: els.endingPreset.value,
    videoVolumeDb: Number(els.videoVolumeDb.value || 8.9),
    actions: {
      trim: actions.trim.checked,
      audio: actions.audio.checked,
      muteVideo: actions.muteVideo.checked,
      effects: actions.effects.checked,
      adjustments: actions.adjustments.checked,
      captions: actions.captions.checked,
      transitions: actions.transitions.checked,
      music: actions.music.checked
    },
    music: {
      path: els.musicPath.value.trim(),
      folder: els.musicFolderPath.value.trim(),
      volumeDb: Number(els.musicVolumeDb.value || -22)
    },
    covers: {
      introPath: els.introCoverPath.value.trim(),
      outroPath: els.outroCoverPath.value.trim(),
      introDurationSeconds: 3,
      outroDurationSeconds: 3
    }
  };
}

function workflowModeLabel() {
  const mode = document.querySelector("input[name='workflowMode']:checked")?.value || "desktop";
  return mode === "mobile" ? "Celular" : "Desktop";
}

function syncMusicAction() {
  actions.music.checked = Boolean(els.musicPath.value.trim());
}

function applySuggestedMusic(suggestion) {
  if (!suggestion?.path) {
    appendLog("Musica automatica nao encontrada em C:\\Wendller. Selecione uma faixa manualmente.", "warn");
    return;
  }
  els.musicPath.value = suggestion.path;
  els.musicVolumeDb.value = suggestion.volumeDb ?? -22;
  actions.music.checked = true;
  appendLog(`Musica sugerida: ${suggestion.name || suggestion.path}`);
}

async function analyzeMusicFolder() {
  const musicFolder = els.musicFolderPath.value.trim();
  const sourceFolder = els.sourceFolderPath.value.trim() || state.sourceFolder;
  if (!musicFolder) {
    appendLog("Selecione a pasta de musicas para analisar.", "warn");
    return;
  }
  if (!sourceFolder) {
    appendLog("Selecione a pasta dos videos antes de analisar as musicas.", "warn");
    return;
  }

  appendLog("Analisando musicas...");
  try {
    const result = await window.workflow.analyzeMusicFolder({
      sourceFolder,
      musicFolder,
      projectName: els.projectName.value.trim()
    });
    if (!result?.path) {
      appendLog("Nenhuma musica compativel encontrada nessa pasta.", "warn");
      return;
    }
    els.musicPath.value = result.path;
    els.musicVolumeDb.value = result.volumeDb ?? -22;
    actions.music.checked = true;
    appendLog(`Musica escolhida: ${result.name}`);
    appendLog(`Motivo: ${result.reason}`);
  } catch (error) {
    appendLog(error.message || String(error), "warn");
  }
}

async function chooseSourceFolder() {
  const selected = await window.workflow.selectFolder();
  if (!selected) return;
  state.sourceFolder = selected.path;
  els.sourceFolderPath.value = selected.path;
  els.folderTitle.textContent = selected.projectName;
  els.folderMeta.textContent = `${selected.videoCount} videos | ${selected.path}`;
  if (!els.projectName.value.trim()) els.projectName.value = selected.projectName;
  if (els.musicFolderPath.value.trim()) {
    appendLog("A musica sera escolhida depois que o projeto for criado.");
  } else {
    applySuggestedMusic(selected.suggestedMusic);
  }
}

els.selectFolder.addEventListener("click", chooseSourceFolder);
els.selectFolderPath.addEventListener("click", chooseSourceFolder);

els.sourceFolderPath.addEventListener("input", () => {
  state.sourceFolder = els.sourceFolderPath.value.trim();
  els.folderTitle.textContent = state.sourceFolder ? "Pasta informada" : "Selecionar pasta dos videos";
  els.folderMeta.textContent = state.sourceFolder || "Nenhuma pasta selecionada";
});

els.selectTemplate.addEventListener("click", async () => {
  const selected = await window.workflow.selectTemplate();
  if (!selected) return;
  els.templateDraft.value = selected;
});

els.selectMusic.addEventListener("click", async () => {
  const selected = await window.workflow.selectMusic();
  if (!selected) return;
  els.musicPath.value = selected;
  syncMusicAction();
});

els.selectMusicFolder.addEventListener("click", async () => {
  const selected = await window.workflow.selectMusicFolder();
  if (!selected) return;
  els.musicFolderPath.value = selected;
  actions.music.checked = true;
  appendLog(`Pasta de musicas: ${selected}`);
  appendLog("A escolha definitiva da musica acontece depois da criacao do projeto.");
});

els.selectIntroCover.addEventListener("click", async () => {
  const selected = await window.workflow.selectCoverMedia();
  if (!selected) return;
  els.introCoverPath.value = selected;
  appendLog(`Capa inicial: ${selected}`);
});

els.selectOutroCover.addEventListener("click", async () => {
  const selected = await window.workflow.selectCoverMedia();
  if (!selected) return;
  els.outroCoverPath.value = selected;
  appendLog(`Capa final: ${selected}`);
});

els.musicPath.addEventListener("input", syncMusicAction);

els.runButton.addEventListener("click", async () => {
  const data = payload();
  if (!data.sourceFolder) {
    appendLog("Selecione ou cole o caminho da pasta dos videos antes de criar.", "warn");
    return;
  }
  if (data.actions.music && !data.music.path) {
    if (!data.music.folder) {
      appendLog("A opcao Musica esta marcada. Selecione uma pasta de musicas, uma faixa ou desmarque Musica.", "warn");
      return;
    }
    appendLog("A musica sera analisada depois que o projeto for criado.");
  }
  setRunning(true);
  appendLog(`Iniciando fluxo (${workflowModeLabel()})...`);
  try {
    const result = await window.workflow.run(data);
    appendLog("Finalizado.");
    if (result?.project?.endingPreset) appendLog(`Final aplicado: ${result.project.endingPreset}`);
    if (result?.selectedMusic?.name) appendLog(`Musica aplicada: ${result.selectedMusic.name}`);
    if (result?.profilePath) appendLog(`Perfil temporario: ${result.profilePath}`);
  } catch (error) {
    appendLog(error.message || String(error), "warn");
  } finally {
    setRunning(false);
  }
});

els.stopButton.addEventListener("click", async () => {
  await window.workflow.stop();
  appendLog("Execucao interrompida.", "warn");
  setRunning(false);
});

els.clearLog.addEventListener("click", () => {
  els.logOutput.textContent = "";
});

window.workflow.onLog(({ type, line }) => appendLog(line, type));

window.workflow.getDefaults().then((defaults) => {
  state.templateDraft = defaults.templateDraft;
  els.templateDraft.value = defaults.templateDraft;
  if (defaults.musicFolder) els.musicFolderPath.value = defaults.musicFolder;
  appendLog(`Base: ${defaults.repoRoot}`);
  if (defaults.libraryRoot) appendLog(`Biblioteca: ${defaults.libraryRoot}`);
});
