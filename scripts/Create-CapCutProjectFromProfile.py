#!/usr/bin/env python
import argparse
import copy
import fnmatch
import importlib.util
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path


def bundled_tool(name: str) -> str:
    tool_path = Path(__file__).resolve().parent.parent / "runtime" / "ffmpeg" / "bin" / f"{name}.exe"
    return str(tool_path) if tool_path.exists() else name


def load_apply_module(script_root: Path):
    module_path = script_root / "Apply-CapCutDraftProfile.py"
    spec = importlib.util.spec_from_file_location("apply_capcut_draft_profile", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, payload):
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")


def ensure_empty_directory(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_file() or child.is_symlink():
            child.unlink()
        else:
            shutil.rmtree(child)


def safe_file_stem(text: str) -> str:
    invalid_chars = set('<>:"/\\|?*')
    cleaned = "".join("_" if char in invalid_chars else char for char in text.strip())
    return re.sub(r"\s+", " ", cleaned).strip()


def is_excluded_source(path: Path, source_folder: Path, profile: dict) -> bool:
    patterns = profile.get("excludeFiles", [])
    if not patterns:
        return False

    try:
        relative_path = path.relative_to(source_folder).as_posix()
    except ValueError:
        relative_path = path.as_posix()

    candidates = {
        path.name.lower(),
        path.stem.lower(),
        relative_path.lower(),
        path.as_posix().lower(),
    }
    for pattern in patterns:
        normalized = str(pattern).replace("\\", "/").lower()
        if any(fnmatch.fnmatchcase(candidate, normalized) for candidate in candidates):
            return True
    return False


def get_source_files(profile: dict):
    source_folder = Path(profile["sourceFolder"])
    recursive = profile["preparation"].get("recursive", False)
    patterns = {extension.lower() for extension in profile["videoExtensions"]}
    candidates = source_folder.rglob("*") if recursive else source_folder.iterdir()
    files = [
        path
        for path in candidates
        if path.is_file()
        and path.suffix.lower() in patterns
        and not is_excluded_source(path, source_folder, profile)
    ]
    return sorted(files, key=lambda item: (str(item.parent).lower(), item.name.lower()))


def stage_media(profile: dict):
    workspace = Path(profile["workspaceRoot"])
    prepared_folder = workspace / profile["preparation"]["stagingFolder"]
    manifest_folder = workspace / profile["preparation"]["manifestFolder"]
    prepared_folder.mkdir(parents=True, exist_ok=True)
    manifest_folder.mkdir(parents=True, exist_ok=True)
    ensure_empty_directory(prepared_folder)

    prefix_width = int(profile["preparation"].get("prefixWidth", 3))
    staged_files = []
    manifest = []
    for index, source_path in enumerate(get_source_files(profile), start=1):
        prefix = str(index).zfill(prefix_width)
        folder_name = safe_file_stem(source_path.parent.name)
        file_name = safe_file_stem(source_path.stem)
        prepared_name = f"{prefix}_{folder_name}_{file_name}{source_path.suffix}"
        prepared_path = prepared_folder / prepared_name
        shutil.copy2(source_path, prepared_path)
        staged_files.append(prepared_path)
        manifest.append(
            {
                "order": index,
                "sourcePath": str(source_path),
                "preparedPath": str(prepared_path),
                "preparedName": prepared_name,
                "sizeBytes": prepared_path.stat().st_size,
            }
        )

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    write_json(manifest_folder / f"manifest-{timestamp}.json", manifest)
    (manifest_folder / f"import-order-{timestamp}.txt").write_text(
        "\n".join(item["preparedName"] for item in manifest),
        encoding="utf-8",
    )
    return staged_files


def ffprobe_media(path: Path):
    result = subprocess.run(
        [
            bundled_tool("ffprobe"),
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height:format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    stream = payload["streams"][0]
    duration_seconds = float(payload["format"]["duration"])
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "duration_seconds": duration_seconds,
        "duration_us": int(round(duration_seconds * 1_000_000)),
        "size_bytes": path.stat().st_size,
    }


def clone_template_draft(template_dir: Path, target_dir: Path):
    if target_dir.exists():
        return

    def ignore_filter(_directory, names):
        return [name for name in names if name.startswith("codex-backup-")]

    shutil.copytree(template_dir, target_dir, ignore=ignore_filter)


def build_video_material(template: dict, prepared_path: Path, media_info: dict):
    material = copy.deepcopy(template)
    material["id"] = str(uuid.uuid4()).upper()
    material["path"] = prepared_path.as_posix()
    material["material_name"] = prepared_path.name
    material["duration"] = media_info["duration_us"]
    material["width"] = media_info["width"]
    material["height"] = media_info["height"]
    material["local_material_id"] = str(uuid.uuid4()).lower()
    return material


def reset_aux_material(template: dict):
    material = copy.deepcopy(template)
    material["id"] = str(uuid.uuid4()).upper()
    return material


def build_main_segment(template: dict, material_id: str, duration_us: int, start_us: int, extra_refs):
    segment = copy.deepcopy(template)
    segment["id"] = str(uuid.uuid4()).upper()
    segment["material_id"] = material_id
    segment["source_timerange"] = {"start": 0, "duration": duration_us}
    segment["target_timerange"] = {"start": start_us, "duration": duration_us}
    segment["render_timerange"] = {"start": 0, "duration": 0}
    segment["extra_material_refs"] = list(extra_refs)
    segment["volume"] = 1.0
    segment["last_nonzero_volume"] = 1.0
    return segment


def build_meta_material(template: dict, video_material: dict, prepared_path: Path, media_info: dict, now_seconds: int, now_us: int):
    material = copy.deepcopy(template)
    material["id"] = video_material["local_material_id"]
    material["duration"] = media_info["duration_us"]
    material["extra_info"] = prepared_path.name
    material["file_Path"] = prepared_path.as_posix()
    material["height"] = media_info["height"]
    material["width"] = media_info["width"]
    material["create_time"] = now_seconds
    material["import_time"] = now_seconds
    material["import_time_ms"] = now_us
    material["roughcut_time_range"] = {"start": 0, "duration": media_info["duration_us"]}
    return material


def rebuild_main_draft(apply_module, profile: dict, draft_dir: Path, project_name: str, staged_files):
    draft_path = draft_dir / "draft_content.json"
    meta_path = draft_dir / "draft_meta_info.json"
    draft = load_json(draft_path)
    meta = load_json(meta_path)

    template_track = next(track for track in draft["tracks"] if track["type"] == "video")
    template_segment = template_track["segments"][0]
    template_video = draft["materials"]["videos"][0]
    template_speed = draft["materials"]["speeds"][0]
    template_placeholder = draft["materials"]["placeholder_infos"][0]
    template_canvas = draft["materials"]["canvases"][0]
    template_channel = draft["materials"]["sound_channel_mappings"][0]
    template_color = draft["materials"]["material_colors"][0]
    template_vocal = draft["materials"]["vocal_separations"][0]
    template_meta_material_group = meta["draft_materials"][0]
    template_meta_material = template_meta_material_group["value"][0]

    track = copy.deepcopy(template_track)
    track["id"] = apply_module.uuid_str()
    track["segments"] = []

    videos = []
    speeds = []
    placeholders = []
    canvases = []
    channels = []
    colors = []
    vocals = []
    meta_materials = []
    media_items = []

    cursor = 0
    now_seconds = int(time.time())
    now_us = int(time.time() * 1_000_000)

    for prepared_path in staged_files:
        media_info = ffprobe_media(prepared_path)
        video = build_video_material(template_video, prepared_path, media_info)
        speed = reset_aux_material(template_speed)
        placeholder = reset_aux_material(template_placeholder)
        canvas = reset_aux_material(template_canvas)
        channel = reset_aux_material(template_channel)
        color = reset_aux_material(template_color)
        vocal = reset_aux_material(template_vocal)
        extra_refs = [speed["id"], placeholder["id"], canvas["id"], channel["id"], color["id"], vocal["id"]]
        segment = build_main_segment(template_segment, video["id"], media_info["duration_us"], cursor, extra_refs)
        meta_material = build_meta_material(template_meta_material, video, prepared_path, media_info, now_seconds, now_us)

        cursor += media_info["duration_us"]
        track["segments"].append(segment)
        videos.append(video)
        speeds.append(speed)
        placeholders.append(placeholder)
        canvases.append(canvas)
        channels.append(channel)
        colors.append(color)
        vocals.append(vocal)
        meta_materials.append(meta_material)
        media_items.append({"segment": segment, "material": video, "path": prepared_path, "trim": None})

    draft["tracks"] = [track]
    draft["duration"] = cursor
    draft["materials"]["videos"] = videos
    draft["materials"]["speeds"] = speeds
    draft["materials"]["placeholder_infos"] = placeholders
    draft["materials"]["canvases"] = canvases
    draft["materials"]["sound_channel_mappings"] = channels
    draft["materials"]["material_colors"] = colors
    draft["materials"]["vocal_separations"] = vocals
    draft["materials"]["effects"] = []
    draft["materials"]["texts"] = []
    draft["materials"]["material_animations"] = []
    draft["materials"]["transitions"] = []
    draft["materials"]["realtime_denoises"] = []
    draft["materials"]["loudnesses"] = []
    draft["materials"]["placeholders"] = []
    draft["materials"]["hsl"] = []
    draft["name"] = project_name

    meta["draft_name"] = project_name
    meta["draft_fold_path"] = draft_dir.as_posix()
    meta["draft_id"] = meta.get("draft_id") or str(uuid.uuid4()).upper()
    meta["tm_duration"] = cursor
    meta["tm_draft_modified"] = int(time.time() * 1_000_000)
    meta_group = copy.deepcopy(template_meta_material_group)
    meta_group["value"] = meta_materials
    meta["draft_materials"] = [meta_group]

    write_json(draft_path, draft)
    write_json(meta_path, meta)
    for extra_name in ["draft_content.json.bak", "template-2.tmp"]:
        extra_path = draft_dir / extra_name
        if extra_path.exists():
            write_json(extra_path, draft)
    for timeline_path in (draft_dir / "Timelines").glob("**/template-2.tmp"):
        write_json(timeline_path, draft)

    return {
        "draft_path": draft_path,
        "meta_path": meta_path,
        "meta": meta,
        "duration_us": cursor,
        "timeline_size_bytes": sum(item["size_bytes"] for item in (ffprobe_media(path) for path in staged_files)),
        "clip_count": len(staged_files),
    }


def update_root_meta(drafts_root: Path, draft_dir: Path, project_name: str, meta: dict, timeline_size_bytes: int, duration_us: int):
    root_meta_path = drafts_root / "root_meta_info.json"
    root_meta = load_json(root_meta_path)
    entry = None
    for candidate in root_meta["all_draft_store"]:
        if candidate.get("draft_fold_path") == draft_dir.as_posix() or candidate.get("draft_name") == project_name:
            entry = candidate
            break

    now_us = int(time.time() * 1_000_000)
    if entry is None:
        entry = copy.deepcopy(root_meta["all_draft_store"][0])
        entry["tm_draft_create"] = now_us
        root_meta["all_draft_store"].insert(0, entry)

    entry["draft_cover"] = f"{draft_dir.as_posix()}/draft_cover.jpg"
    entry["draft_fold_path"] = draft_dir.as_posix()
    entry["draft_id"] = meta["draft_id"]
    entry["draft_json_file"] = f"{draft_dir.as_posix()}/draft_content.json"
    entry["draft_name"] = project_name
    entry["draft_root_path"] = drafts_root.as_posix()
    entry["draft_timeline_materials_size"] = timeline_size_bytes
    entry["tm_draft_modified"] = now_us
    entry["tm_duration"] = duration_us

    write_json(root_meta_path, root_meta)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    default_drafts_root = Path(os.environ.get("LOCALAPPDATA", "")) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
    parser.add_argument("--drafts-root", default=str(default_drafts_root))
    parser.add_argument("--template-draft", required=True)
    parser.add_argument("--project-name")
    args = parser.parse_args()

    script_root = Path(__file__).resolve().parent
    project_root = script_root.parent
    apply_module = load_apply_module(script_root)

    profile_path = Path(args.profile)
    if not profile_path.is_absolute():
        profile_path = project_root / profile_path
    profile = apply_module.load_profile(project_root, profile_path)
    project_name = args.project_name or profile.get("capcut", {}).get("projectName") or profile.get("name")
    if not project_name:
        raise ValueError("Defina --project-name ou capcut.projectName no perfil.")

    drafts_root = Path(args.drafts_root)
    template_draft = Path(args.template_draft)
    draft_dir = drafts_root / project_name

    staged_files = stage_media(profile)
    clone_template_draft(template_draft, draft_dir)
    rebuild_result = rebuild_main_draft(apply_module, profile, draft_dir, project_name, staged_files)
    patch_result = apply_module.patch_draft(profile, draft_dir)

    update_root_meta(
        drafts_root=drafts_root,
        draft_dir=draft_dir,
        project_name=project_name,
        meta=load_json(rebuild_result["meta_path"]),
        timeline_size_bytes=rebuild_result["timeline_size_bytes"],
        duration_us=patch_result["duration_us"],
    )

    result = {
        "projectName": project_name,
        "draftDirectory": str(draft_dir),
        "clipCount": rebuild_result["clip_count"],
        "durationUs": patch_result["duration_us"],
        "subtitleCount": patch_result["subtitle_count"],
        "endingPreset": patch_result.get("ending_preset", ""),
        "trimmedSegments": patch_result["trimmed_segments"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
