#!/usr/bin/env python
import argparse
import copy
import hashlib
import json
import math
import os
import re
import subprocess
import time
import uuid
from pathlib import Path


FILTER_LIBRARY = {
    "aprimorar": {
        "effect_id": "7289393505166692866",
        "resource_id": "7289393505166692866",
        "third_resource_id": "7289393505166692866",
        "path": "C:/Users/wendller.ferreira/AppData/Local/CapCut/User Data/Cache/effect/7289393505166692866/0cef35f4090468586ca961c4baa51c83",
        "source_platform": 1,
    },
    "4k": {
        "effect_id": "7426678351957332497",
        "resource_id": "7426678351957332497",
        "third_resource_id": "7426678351957332497",
        "path": "C:/Users/wendller.ferreira/AppData/Local/CapCut/User Data/Cache/effect/7426678351957332497/3381cda21304c1eb4664f3bdfe945869",
        "source_platform": 1,
    },
    "retro americano": {
        "effect_id": "7586495550942498065",
        "resource_id": "7586495550942498065",
        "third_resource_id": "0",
        "path": "C:/Users/wendller.ferreira/AppData/Local/CapCut/User Data/Cache/effect/7586495550942498065/4a4457b3d01aa6fbcfbaee01a1d9254d",
        "source_platform": 1,
    },
    "mar sem nuvens": {
        "effect_id": "7586491722008464641",
        "resource_id": "7586491722008464641",
        "third_resource_id": "0",
        "path": "C:/Users/wendller.ferreira/AppData/Local/CapCut/User Data/Cache/effect/7586491722008464641/4fd60974ac9c764dce89084a739fa738",
        "source_platform": 1,
    },
    "calma": {
        "effect_id": "44244487",
        "resource_id": "7252652561759474178",
        "third_resource_id": "0",
        "path": "C:/Users/wendller.ferreira/AppData/Local/CapCut/User Data/Cache/effect/44244487/ec67a0ca2b3d8dd17c31ca17dc6953cf",
        "source_platform": 0,
    },
    "olhar da folha": {
        "effect_id": "7291928991068344833",
        "resource_id": "7291928991068344833",
        "third_resource_id": "7291928991068344833",
        "path": "C:/Users/wendller.ferreira/AppData/Local/CapCut/User Data/Cache/effect/7291928991068344833/99cc2a8b34fd3f87215efd222c7eea2e",
        "source_platform": 1,
    },
    "vivido": {
        "effect_id": "7278664241702244865",
        "resource_id": "7278664241702244865",
        "third_resource_id": "",
        "path": "C:/Users/wendller.ferreira/AppData/Local/CapCut/User Data/Cache/effect/7278664241702244865/c501effb56dfa6116b29474da3487c3b",
        "source_platform": 1,
    },
}

TRANSITION_LIBRARY = {
    "esmaecimento preto": {
        "name": "Esmaecimento preto",
        "effect_id": "6724239388189921806",
        "resource_id": "6724239388189921806",
        "third_resource_id": "6724239388189921806",
        "source_platform": 1,
        "path": "C:/Users/wendller.ferreira/AppData/Local/CapCut/User Data/Cache/effect/6724239388189921806/3bca53e9f3dfa2c184fbee96438ea097",
        "duration": 466666,
        "platform": "all",
        "category_id": "25822",
        "category_name": "Populares",
    }
}
TRANSITION_LIBRARY["combinar"] = {
    "name": "Combinar",
    "effect_id": "6724845717472416269",
    "resource_id": "6724845717472416269",
    "third_resource_id": "6724845717472416269",
    "source_platform": 1,
    "path": "C:/Users/wendller.ferreira/AppData/Local/CapCut/User Data/Cache/effect/6724845717472416269/7b53f4c008c4c684fccf8c7d4d46cc92",
    "duration": 466666,
    "platform": "all",
    "category_id": "100000",
    "category_name": "",
}

ADJUST_PATH_ROOT = "C:/Users/wendller.ferreira/AppData/Local/CapCut/User Data/Cache/effect/7501974767453474064"
ADJUST_EFFECTS = {
    "brightness": {"path": f"{ADJUST_PATH_ROOT}/20cd8db6531c21bf7e4053026d20e395", "version": "v2", "value": 0.0},
    "contrast": {"path": f"{ADJUST_PATH_ROOT}/6821a294141131e7c561ff73480449f7", "version": "v3", "value": 0.0},
    "highlight": {"path": f"{ADJUST_PATH_ROOT}/6821a294141131e7c561ff73480449f7", "version": "v3", "value": 0.0},
    "shadow": {"path": f"{ADJUST_PATH_ROOT}/6821a294141131e7c561ff73480449f7", "version": "v3", "value": -0.0635451505016722},
    "white": {"path": f"{ADJUST_PATH_ROOT}/6821a294141131e7c561ff73480449f7", "version": "", "value": 0.06020066889632103},
    "black": {"path": f"{ADJUST_PATH_ROOT}/6821a294141131e7c561ff73480449f7", "version": "", "value": 0.0},
    "temperature": {"path": f"{ADJUST_PATH_ROOT}/6821a294141131e7c561ff73480449f7", "version": "v3", "value": 0.10367892976588644},
    "tone": {"path": f"{ADJUST_PATH_ROOT}/6821a294141131e7c561ff73480449f7", "version": "v3", "value": -0.06020066889632103},
    "light_sensation": {"path": f"{ADJUST_PATH_ROOT}/6821a294141131e7c561ff73480449f7", "version": "", "value": 0.1070234113712376},
}
ADJUST_HSL_PATH = "C:/Users/wendller.ferreira/AppData/Local/CapCut/Apps/8.9.1.3802/Resources/DefaultAdjustBundle/merge_all_adjust_color"
FONT_PATH = "C:/Users/wendller.ferreira/AppData/Local/Microsoft/Windows/Fonts/neulis-alt-bold.otf"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}


def bundled_tool(name: str) -> str:
    tool_path = Path(__file__).resolve().parent.parent / "runtime" / "ffmpeg" / "bin" / f"{name}.exe"
    return str(tool_path) if tool_path.exists() else name


def normalize_name(value: str) -> str:
    value = value.lower().strip()
    replacements = {
        "á": "a",
        "à": "a",
        "â": "a",
        "ã": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ú": "u",
        "ç": "c",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value

def normalize_name(value: str) -> str:
    value = str(value or "").lower().strip()
    replacements = {
        "Ã¡": "a",
        "Ã ": "a",
        "Ã¢": "a",
        "Ã£": "a",
        "Ã©": "e",
        "Ãª": "e",
        "Ã­": "i",
        "Ã³": "o",
        "Ã´": "o",
        "Ãµ": "o",
        "Ãº": "u",
        "Ã§": "c",
        "´": "",
        "`": "",
        "'": "",
        "’": "",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    unicodedata = __import__("unicodedata")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"\s+", " ", value).strip()
    if value == "retra americano" or re.fullmatch(r"retr\W*a\W*americano", value):
        return "retro americano"
    if value.startswith("retr") and value.endswith(" americano") and len(value.split()) == 2:
        return "retro americano"
    return value


def deep_merge(base, override):
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, payload):
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")


def load_profile(project_root: Path, profile_path: Path):
    default_profile = load_json(project_root / "config" / "profiles" / "default.json")
    specific_profile = load_json(profile_path)
    merged = deep_merge(default_profile, specific_profile)
    source_folder = Path(merged["sourceFolder"])
    workspace_root = Path(merged["workspaceRoot"])
    merged["sourceFolder"] = str(source_folder if source_folder.is_absolute() else (project_root / source_folder).resolve())
    merged["workspaceRoot"] = str(workspace_root if workspace_root.is_absolute() else (project_root / workspace_root).resolve())
    background_music = merged.get("capcut", {}).get("backgroundMusic")
    if isinstance(background_music, dict) and background_music.get("path"):
        music_path = Path(background_music["path"])
        background_music["path"] = str(music_path if music_path.is_absolute() else (project_root / music_path).resolve())
    return merged


def ffprobe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            bundled_tool("ffprobe"),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def ffprobe_visual_info(path: Path, fallback_duration_seconds: float):
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
    duration = payload.get("format", {}).get("duration")
    try:
        duration_seconds = float(duration)
    except (TypeError, ValueError):
        duration_seconds = fallback_duration_seconds
    if duration_seconds <= 0:
        duration_seconds = fallback_duration_seconds
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "duration_us": int(round(duration_seconds * 1_000_000)),
    }


def detect_trim_points(path: Path, silence_cfg: dict):
    duration = ffprobe_duration(path)
    if not silence_cfg.get("enabled", False):
        return {
            "duration_seconds": duration,
            "trim_start_seconds": 0.0,
            "trim_end_seconds": 0.0,
            "source_start_us": 0,
            "source_duration_us": int(round(duration * 1_000_000)),
            "silence_config": copy.deepcopy(silence_cfg),
        }

    noise_db = silence_cfg.get("noiseThresholdDb", -33)
    min_duration = silence_cfg.get("minimumDurationSeconds", 0.18)
    process = subprocess.run(
        [
            bundled_tool("ffmpeg"),
            "-i",
            str(path),
            "-af",
            f"silencedetect=noise={noise_db}dB:d={min_duration}",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    pattern_start = re.compile(r"silence_start: ([0-9.]+)")
    pattern_end = re.compile(r"silence_end: ([0-9.]+) \| silence_duration: ([0-9.]+)")
    starts = [float(match.group(1)) for match in pattern_start.finditer(process.stderr)]
    ends = [(float(match.group(1)), float(match.group(2))) for match in pattern_end.finditer(process.stderr)]

    trim_start = 0.0
    if starts and ends:
        first_start = starts[0]
        first_end = ends[0][0]
        max_head_trim = float(silence_cfg.get("maxHeadTrimSeconds", 3.0))
        if first_start <= 0.35 and first_end <= max_head_trim:
            trim_start = first_end

    trim_end = 0.0
    if ends:
        last_end, last_duration = ends[-1]
        last_start = last_end - last_duration
        max_tail_trim = float(silence_cfg.get("maxTailTrimSeconds", 3.0))
        if duration - last_start <= max_tail_trim and duration - last_start >= min_duration:
            trim_end = duration - last_start

    trim_start += silence_cfg.get("extraHeadTrimSeconds", 0.0)
    trim_end += silence_cfg.get("extraTailTrimSeconds", 0.0)
    trim_start = max(0.0, trim_start - silence_cfg.get("keepHeadPaddingSeconds", 0.0))
    trim_end = max(0.0, trim_end - silence_cfg.get("keepTailPaddingSeconds", 0.0))

    remaining = duration - trim_start - trim_end
    minimum_output = silence_cfg.get("minimumOutputDurationSeconds", 0.75)
    if remaining < minimum_output:
        trim_start = 0.0
        trim_end = 0.0

    return {
        "duration_seconds": duration,
        "trim_start_seconds": trim_start,
        "trim_end_seconds": trim_end,
        "source_start_us": int(round(trim_start * 1_000_000)),
        "source_duration_us": int(round((duration - trim_start - trim_end) * 1_000_000)),
        "silence_config": copy.deepcopy(silence_cfg),
    }


def uuid_str():
    return str(uuid.uuid4()).upper()


def db_to_gain(db_value: float) -> float:
    return 10 ** (db_value / 20.0)


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def collect_segment_material_ids(track: dict):
    ids = set()
    for segment in track.get("segments", []):
        material_id = segment.get("material_id")
        if material_id:
            ids.add(material_id)
        ids.update(ref for ref in segment.get("extra_material_refs", []) if ref)
    return ids


def remove_existing_audio_tracks(draft: dict):
    stale_audio_material_ids = set()
    kept_tracks = []
    for track in draft["tracks"]:
        if track["type"] == "audio":
            stale_audio_material_ids.update(collect_segment_material_ids(track))
            continue
        kept_tracks.append(track)
    draft["tracks"] = kept_tracks

    for key in ["audios", "beats", "speeds", "placeholder_infos", "sound_channel_mappings", "vocal_separations"]:
        draft["materials"][key] = [
            item
            for item in draft["materials"].get(key, [])
            if item.get("id") not in stale_audio_material_ids
        ]


def remove_existing_video_audio_processing(draft: dict):
    stale_ref_ids = set()
    stale_ref_ids.update(item["id"] for item in draft["materials"].get("realtime_denoises", []))
    stale_ref_ids.update(item["id"] for item in draft["materials"].get("loudnesses", []))
    draft["materials"]["realtime_denoises"] = []
    draft["materials"]["loudnesses"] = []
    return stale_ref_ids


def apply_video_audio_processing(draft: dict, media_items: list[dict], profile: dict, stale_ref_ids: set):
    gain = db_to_gain(profile["capcut"]["audio"]["volumeDb"])
    file_hashes = {}

    for item in media_items:
        media_path = item["path"]
        file_hash = file_hashes.setdefault(str(media_path), md5_file(media_path))
        segment = item["segment"]
        trim = item["trim"]
        segment["volume"] = gain
        segment["last_nonzero_volume"] = gain

        denoise = build_realtime_denoise()
        loudness_param = measure_loudness_param(media_path, trim["source_start_us"], trim["source_duration_us"])
        loudness = build_loudness(file_hash, trim["source_start_us"], trim["source_duration_us"], loudness_param)
        draft["materials"]["realtime_denoises"].append(denoise)
        draft["materials"]["loudnesses"].append(loudness)

        segment["extra_material_refs"] = [
            ref for ref in segment.get("extra_material_refs", []) if ref not in stale_ref_ids
        ]
        segment["extra_material_refs"].extend([denoise["id"], loudness["id"]])


def mute_video_segments(media_items: list[dict], stale_ref_ids: set):
    for item in media_items:
        segment = item["segment"]
        segment["volume"] = 0.0
        segment["last_nonzero_volume"] = 1.0
        segment["extra_material_refs"] = [
            ref for ref in segment.get("extra_material_refs", []) if ref not in stale_ref_ids
        ]


def remove_existing_overlay_tracks(draft: dict):
    stale_ref_ids = set()
    stale_ref_ids.update(item["id"] for item in draft["materials"].get("transitions", []))
    stale_ref_ids.update(item["id"] for item in draft["materials"].get("realtime_denoises", []))
    stale_ref_ids.update(item["id"] for item in draft["materials"].get("loudnesses", []))

    stale_audio_material_ids = set()
    main_tracks = []
    for track in draft["tracks"]:
        if track["type"] == "audio":
            stale_audio_material_ids.update(collect_segment_material_ids(track))
            continue
        if track["type"] in {"filter", "adjust", "text"}:
            continue
        main_tracks.append(track)
    draft["tracks"] = main_tracks

    draft["materials"]["effects"] = [
        item
        for item in draft["materials"].get("effects", [])
        if item.get("type") not in {"filter", "brightness", "contrast", "highlight", "shadow", "white", "black", "temperature", "tone", "light_sensation"}
    ]
    draft["materials"]["texts"] = [item for item in draft["materials"].get("texts", []) if item.get("type") != "subtitle"]
    draft["materials"]["material_animations"] = []
    draft["materials"]["transitions"] = []
    draft["materials"]["realtime_denoises"] = []
    draft["materials"]["loudnesses"] = []
    draft["materials"]["placeholders"] = [item for item in draft["materials"].get("placeholders", []) if item.get("type") != "adjust"]
    draft["materials"]["hsl"] = []
    for key in ["audios", "beats", "speeds", "placeholder_infos", "sound_channel_mappings", "vocal_separations"]:
        draft["materials"][key] = [item for item in draft["materials"].get(key, []) if item.get("id") not in stale_audio_material_ids]
    return stale_ref_ids


def build_realtime_denoise():
    current_path = Path(r"C:\Users\wendller.ferreira\AppData\Local\CapCut\Apps\9.1.0.3860\Resources\audiosami\unet_denoise_44k_music_model_v1.0.model")
    fallback_path = Path(r"C:\Users\wendller.ferreira\AppData\Local\CapCut\Apps\8.9.1.3802\Resources\audiosami\unet_denoise_44k_music_model_v1.0.model")
    model_path = current_path if current_path.exists() else fallback_path
    return {
        "id": uuid_str(),
        "type": "realtime_denoise",
        "is_denoise": True,
        "denoise_mode": 1.0,
        "denoise_rate": 0.85,
        "path": model_path.as_posix(),
        "sami_name": "denoise_v2",
        "sami_version": "1.0",
        "sami_type": 2,
        "is_from_hd_sounds": False,
    }


def measure_loudness_param(path: Path, start_us: int, duration_us: int):
    process = subprocess.run(
        [
            bundled_tool("ffmpeg"),
            "-hide_banner",
            "-ss",
            f"{start_us / 1_000_000:.6f}",
            "-t",
            f"{duration_us / 1_000_000:.6f}",
            "-i",
            str(path),
            "-vn",
            "-af",
            "loudnorm=I=-23:TP=-1.5:LRA=11:print_format=json",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    match = re.search(r"\{\s*\"input_i\".*?\}", process.stderr, re.DOTALL)
    if not match:
        return None

    try:
        payload = json.loads(match.group(0))
        return {
            "avg_loudness": float(payload["input_i"]),
            "peak_loudness": float(payload["input_tp"]),
        }
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def build_loudness(file_id: str, start_us: int, duration_us: int, loudness_param=None):
    return {
        "id": uuid_str(),
        "enable": True,
        "time_range": {
            "start": start_us,
            "duration": duration_us,
        },
        "file_id": file_id,
        "target_loudness": -23.0,
        "loudness_param": loudness_param,
    }


def build_audio_material(path: Path, duration_us: int):
    return {
        "id": uuid_str(),
        "unique_id": "",
        "type": "extract_music",
        "name": path.name,
        "duration": duration_us,
        "path": path.as_posix(),
        "category_name": "local",
        "wave_points": [],
        "music_id": "",
        "app_id": 0,
        "text_id": "",
        "tone_type": "",
        "source_platform": 0,
        "video_id": "",
        "effect_id": "",
        "resource_id": "",
        "third_resource_id": "",
        "category_id": "",
        "intensifies_path": "",
        "formula_id": "",
        "check_flag": 1,
        "team_id": "",
        "local_material_id": "",
        "tone_speaker": "",
        "mock_tone_speaker": "",
        "tone_effect_id": "",
        "tone_effect_name": "",
        "tone_platform": "",
        "cloned_model_type": "",
        "tone_category_id": "",
        "tone_category_name": "",
        "tone_second_category_id": "",
        "tone_second_category_name": "",
        "tone_emotion_name_key": "",
        "tone_emotion_style": "",
        "tone_emotion_role": "",
        "tone_emotion_selection": "",
        "tone_emotion_scale": 0.0,
        "moyin_emotion": "",
        "request_id": "",
        "query": "",
        "search_id": "",
        "sound_separate_type": "",
        "is_text_edit_overdub": False,
        "is_ugc": False,
        "is_ai_clone_tone": False,
        "is_ai_clone_tone_post": False,
        "source_from": "",
        "copyright_limit_type": "none",
        "aigc_history_id": "",
        "aigc_item_id": "",
        "music_source": "",
        "pgc_id": "",
        "pgc_name": "",
        "similiar_music_info": {"original_song_id": "", "original_song_name": ""},
        "ai_music_type": 0,
        "ai_music_enter_from": "",
        "lyric_type": 0,
        "tts_task_id": "",
        "tts_generate_scene": "",
        "ai_music_generate_scene": 0,
        "tts_benefit_info": {
            "benefit_type": "none",
            "benefit_log_id": "",
            "benefit_log_extra": "",
            "benefit_amount": -1,
        },
    }


def build_audio_speed():
    return {
        "id": uuid_str(),
        "type": "speed",
        "mode": 0,
        "speed": 1.0,
        "curve_speed": None,
    }


def build_audio_placeholder_info():
    return {
        "id": uuid_str(),
        "type": "placeholder_info",
        "meta_type": "none",
        "res_path": "",
        "res_text": "",
        "error_path": "",
        "error_text": "",
    }


def build_audio_beats():
    return {
        "id": uuid_str(),
        "type": "beats",
        "enable_ai_beats": False,
        "gear": 404,
        "gear_count": 0,
        "mode": 404,
        "user_beats": [],
        "user_delete_ai_beats": None,
        "ai_beats": {
            "melody_url": "",
            "melody_path": "",
            "beats_url": "",
            "beats_path": "",
            "melody_percents": [0.0],
            "beat_speed_infos": [],
        },
    }


def build_audio_sound_channel_mapping():
    return {
        "id": uuid_str(),
        "type": "",
        "audio_channel_mapping": 0,
        "is_config_open": False,
    }


def build_audio_vocal_separation():
    return {
        "id": uuid_str(),
        "type": "vocal_separation",
        "choice": 0,
        "removed_sounds": [],
        "time_range": None,
        "production_path": "",
        "final_algorithm": "",
        "enter_from": "",
    }


def build_audio_segment(material_id: str, extra_refs: list[str], source_start_us: int, duration_us: int, target_start_us: int, volume_gain: float, render_index: int, track_render_index: int):
    return {
        "id": uuid_str(),
        "source_timerange": {"start": source_start_us, "duration": duration_us},
        "target_timerange": {"start": target_start_us, "duration": duration_us},
        "render_timerange": {"start": 0, "duration": 0},
        "desc": "",
        "state": 0,
        "speed": 1.0,
        "is_loop": False,
        "is_tone_modify": False,
        "reverse": False,
        "intensifies_audio": False,
        "cartoon": False,
        "volume": volume_gain,
        "last_nonzero_volume": volume_gain,
        "clip": None,
        "uniform_scale": None,
        "material_id": material_id,
        "extra_material_refs": list(extra_refs),
        "render_index": render_index,
        "keyframe_refs": [],
        "enable_lut": False,
        "enable_adjust": False,
        "enable_hsl": False,
        "visible": True,
        "group_id": "",
        "enable_color_curves": True,
        "enable_hsl_curves": True,
        "track_render_index": track_render_index,
        "hdr_settings": None,
        "enable_color_wheels": True,
        "track_attribute": 0,
        "is_placeholder": False,
        "template_id": "",
        "enable_smart_color_adjust": False,
        "template_scene": "default",
        "common_keyframes": [],
        "caption_info": None,
        "responsive_layout": {
            "enable": False,
            "target_follow": "",
            "size_layout": 0,
            "horizontal_pos_layout": 0,
            "vertical_pos_layout": 0,
        },
        "enable_color_match_adjust": False,
        "enable_color_correct_adjust": False,
        "enable_adjust_mask": False,
        "raw_segment_id": "",
        "lyric_keyframes": None,
        "enable_video_mask": True,
        "digital_human_template_group_id": "",
        "color_correct_alg_result": "",
        "source": "segmentsourcenormal",
        "enable_mask_stroke": False,
        "enable_mask_shadow": False,
        "enable_color_adjust_pro": False,
    }


def build_audio_track(segments: list[dict]):
    return {
        "id": uuid_str(),
        "type": "audio",
        "segments": segments,
        "flag": 0,
        "attribute": 0,
        "name": "",
        "is_default_name": True,
    }


def clone_aux_material(draft: dict, collection_name: str):
    template_items = draft["materials"].get(collection_name, [])
    if not template_items:
        return None
    item = copy.deepcopy(template_items[0])
    item["id"] = uuid_str()
    draft["materials"][collection_name].append(item)
    return item["id"]


def build_cover_material(template: dict, cover_path: Path, duration_us: int, media_info: dict):
    material = copy.deepcopy(template)
    material["id"] = uuid_str()
    material["path"] = cover_path.as_posix()
    material["material_name"] = cover_path.name
    material["duration"] = duration_us
    material["width"] = media_info["width"]
    material["height"] = media_info["height"]
    material["local_material_id"] = str(uuid.uuid4()).lower()
    return material


def build_cover_segment(template: dict, material_id: str, duration_us: int, target_start_us: int, extra_refs: list[str], render_index: int):
    segment = copy.deepcopy(template)
    segment["id"] = uuid_str()
    segment["material_id"] = material_id
    segment["source_timerange"] = {"start": 0, "duration": duration_us}
    segment["target_timerange"] = {"start": target_start_us, "duration": duration_us}
    segment["render_timerange"] = {"start": 0, "duration": 0}
    segment["extra_material_refs"] = list(extra_refs)
    segment["render_index"] = render_index
    segment["volume"] = 1.0
    segment["last_nonzero_volume"] = 1.0
    return segment


def cover_config(profile: dict, key: str):
    cfg = profile.get("capcut", {}).get("covers", {}).get(key, {})
    path_text = str(cfg.get("path", "")).strip()
    if not cfg.get("enabled", False) or not path_text:
        return None
    cover_path = Path(path_text)
    if not cover_path.exists():
        raise FileNotFoundError(f"Capa {key} nao encontrada: {cover_path}")
    is_video = cover_path.suffix.lower() in VIDEO_EXTENSIONS
    duration_seconds = 0.5 if is_video else max(0.5, float(cfg.get("durationSeconds", 3.0)))
    media_info = ffprobe_visual_info(cover_path, duration_seconds)
    duration_us = media_info["duration_us"] if is_video else int(round(duration_seconds * 1_000_000))
    return {"path": cover_path, "duration_us": duration_us, "media_info": media_info}


def add_cover_segments_to_main_track(draft: dict, main_video_track: dict, content_start_us: int, content_duration_us: int, intro_cover, outro_cover):
    if not intro_cover and not outro_cover:
        return 0

    template_segment = main_video_track["segments"][0]
    template_video = draft["materials"]["videos"][0]
    next_render_index = max(segment.get("render_index", 0) for segment in main_video_track["segments"]) + 1

    def build_cover(cover, start_us):
        nonlocal next_render_index
        extra_refs = [
            ref
            for ref in [
                clone_aux_material(draft, "speeds"),
                clone_aux_material(draft, "placeholder_infos"),
                clone_aux_material(draft, "canvases"),
                clone_aux_material(draft, "sound_channel_mappings"),
                clone_aux_material(draft, "material_colors"),
                clone_aux_material(draft, "vocal_separations"),
            ]
            if ref
        ]
        material = build_cover_material(template_video, cover["path"], cover["duration_us"], cover["media_info"])
        draft["materials"]["videos"].append(material)
        segment = build_cover_segment(template_segment, material["id"], cover["duration_us"], start_us, extra_refs, next_render_index)
        next_render_index += 1
        return segment

    if intro_cover:
        intro_segment = build_cover(intro_cover, 0)
        main_video_track["segments"].insert(0, intro_segment)

    if outro_cover:
        outro_segment = build_cover(outro_cover, content_start_us + content_duration_us)
        main_video_track["segments"].append(outro_segment)

    return (intro_cover["duration_us"] if intro_cover else 0) + (outro_cover["duration_us"] if outro_cover else 0)


def pick_music_source_start_us(path: Path, total_duration_us: int, music_cfg: dict, music_duration_us: int):
    source_start_seconds = max(0.0, float(music_cfg.get("sourceStartSeconds", 0.0)))
    start_mode = str(music_cfg.get("startMode", "auto_continuous")).strip().lower()
    max_start_seconds = max(0.0, (music_duration_us - total_duration_us) / 1_000_000)

    if start_mode == "manual":
        return int(round(min(source_start_seconds, max_start_seconds) * 1_000_000))

    try:
        import librosa
        import numpy as np

        y, sr = librosa.load(str(path), sr=22050, mono=True)
        if len(y) == 0:
            return int(round(min(source_start_seconds, max_start_seconds) * 1_000_000))

        analysis_step_seconds = max(0.25, float(music_cfg.get("analysisStepSeconds", 0.5)))
        samples_per_step = max(1, int(round(sr * analysis_step_seconds)))
        chunk_count = len(y) // samples_per_step
        if chunk_count < 4:
            return int(round(min(source_start_seconds, max_start_seconds) * 1_000_000))

        trimmed = y[: chunk_count * samples_per_step]
        chunks = trimmed.reshape(chunk_count, samples_per_step)
        rms = np.sqrt(np.mean(chunks * chunks, axis=1))

        window_steps = max(1, int(round((total_duration_us / 1_000_000) / analysis_step_seconds)))
        if window_steps >= len(rms):
            return int(round(min(source_start_seconds, max_start_seconds) * 1_000_000))

        peak_rms = float(np.max(rms))
        if peak_rms <= 0:
            return int(round(min(source_start_seconds, max_start_seconds) * 1_000_000))

        silence_floor = max(
            peak_rms * float(music_cfg.get("silenceFloorRatio", 0.16)),
            float(music_cfg.get("absoluteSilenceFloor", 0.01)),
        )
        lead_focus_steps = max(1, int(round(float(music_cfg.get("leadFocusSeconds", 3.0)) / analysis_step_seconds)))

        best_index = 0
        best_score = float("-inf")
        for index in range(0, len(rms) - window_steps + 1):
            start_seconds = index * analysis_step_seconds
            if start_seconds > max_start_seconds:
                break

            window = rms[index : index + window_steps]
            mean_rms = float(window.mean())
            low_rms = float(np.percentile(window, 20))
            start_rms = float(window[: min(lead_focus_steps, len(window))].mean())
            silence_ratio = float((window < silence_floor).mean())
            variability = float(window.std())

            score = mean_rms
            score += low_rms * 0.9
            score += start_rms * 1.2
            score -= silence_ratio * 1.6
            score -= variability * 0.2
            score -= start_seconds * 0.0005

            if score > best_score:
                best_score = score
                best_index = index

        return int(round(min(best_index * analysis_step_seconds, max_start_seconds) * 1_000_000))
    except Exception:
        return int(round(min(source_start_seconds, max_start_seconds) * 1_000_000))


def add_background_music(draft: dict, profile: dict, total_duration: int, track_render_index: int):
    music_cfg = profile.get("capcut", {}).get("backgroundMusic", {})
    if not music_cfg.get("enabled") or not music_cfg.get("path"):
        return None

    music_path = Path(music_cfg["path"])
    if not music_path.exists():
        raise FileNotFoundError(f"Faixa de fundo não encontrada: {music_path}")

    music_duration_us = int(round(ffprobe_duration(music_path) * 1_000_000))
    if music_duration_us <= 0:
        raise ValueError(f"Faixa de fundo inválida: {music_path}")

    audio_material = build_audio_material(music_path, music_duration_us)
    speed = build_audio_speed()
    placeholder = build_audio_placeholder_info()
    beats = build_audio_beats()
    channel = build_audio_sound_channel_mapping()
    vocal = build_audio_vocal_separation()
    extra_refs = [speed["id"], placeholder["id"], beats["id"], channel["id"], vocal["id"]]
    gain = db_to_gain(music_cfg.get("volumeDb", -21.0))
    initial_source_start_us = pick_music_source_start_us(music_path, total_duration, music_cfg, music_duration_us)

    segments = []
    cursor = 0
    render_index = 0
    current_source_start_us = initial_source_start_us
    while cursor < total_duration:
        available_duration = max(1, music_duration_us - current_source_start_us)
        segment_duration = min(available_duration, total_duration - cursor)
        segments.append(
            build_audio_segment(
                material_id=audio_material["id"],
                extra_refs=extra_refs,
                source_start_us=current_source_start_us,
                duration_us=segment_duration,
                target_start_us=cursor,
                volume_gain=gain,
                render_index=render_index,
                track_render_index=track_render_index,
            )
        )
        cursor += segment_duration
        render_index += 1
        current_source_start_us = 0

    draft["materials"]["audios"].append(audio_material)
    draft["materials"]["speeds"].append(speed)
    draft["materials"]["placeholder_infos"].append(placeholder)
    draft["materials"]["beats"].append(beats)
    draft["materials"]["sound_channel_mappings"].append(channel)
    draft["materials"]["vocal_separations"].append(vocal)
    return {
        "track": build_audio_track(segments),
        "path": music_path,
        "volume_db": music_cfg.get("volumeDb", -21.0),
        "source_start_seconds": round(initial_source_start_us / 1_000_000, 3),
    }


def build_transition(name: str = "esmaecimento preto"):
    data = copy.deepcopy(TRANSITION_LIBRARY[normalize_name(name)])
    data["id"] = uuid_str()
    data["type"] = "transition"
    data["is_overlap"] = normalize_name(name) == "combinar"
    data["request_id"] = ""
    data["is_ai_transition"] = False
    data["video_path"] = ""
    data["task_id"] = ""
    return data


ENDING_PRESETS = {
    "pax_na_rua": {
        "reference_project": "Beleza",
        "main_file": "Fundo Pax na Rua.mp4",
        "main_asset_key": "paxNaRuaBackground",
        "overlay_file": "PaxNaRua.mp4",
        "overlay_asset_key": "paxNaRuaOverlay",
        "transition": "Combinar",
    },
    "momento_pax_saude": {
        "reference_project": "Oftalmologista",
        "main_file": "Momento Pax Saúde-.mp4",
        "main_asset_key": "momentoPaxSaude",
        "overlay_file": "Momento Pax Saúde-.mp4",
        "overlay_asset_key": "momentoPaxSaude",
        "transition": "Combinar",
    },
    "pax_rio_verde": {
        "reference_project": "Prolab A",
        "main_file": "Design sem nome.mp4",
        "main_asset_key": "paxRioVerde",
        "fallback_file": "Design sem nome.mp4",
        "overlay_file": "",
        "transition": "Esmaecimento preto",
    },
    "pax_montividiu": {
        "reference_project": "Prolab A",
        "main_file": "Design sem nome.mp4",
        "main_asset_key": "paxMontividiu",
        "replacement_file": "C:/Wendller/Final Montividiu.mp4",
        "overlay_file": "",
        "transition": "Esmaecimento preto",
    },
}


def transcribed_items_text(transcribed_items):
    words = []
    for entry in transcribed_items or []:
        for segment in entry.get("segments", []):
            words.extend(word.get("text", "") for word in segment)
    return " ".join(words)


def infer_ending_preset_from_text(text: str):
    normalized = normalize_name(text)
    compact = re.sub(r"[^a-z0-9]+", " ", normalized).strip()
    if "pax na rua" in compact or "pax rua" in compact or "paxnarua" in compact:
        return "pax_na_rua"
    if "pax montividiu" in compact or "montividiu" in compact:
        return "pax_montividiu"

    momento_terms = [
        "momento pax saude",
        "momento da pax saude",
        "momento de pax saude",
        "momento pax",
        "pax saude",
        "paxsaude",
    ]
    if any(term in compact for term in momento_terms):
        return "momento_pax_saude"

    if "pax rio verde" in compact or "rio verde" in compact:
        return "pax_rio_verde"

    return "pax_rio_verde"


def resolve_ending_preset(profile: dict, transcript_text: str = ""):
    ending_cfg = profile.get("capcut", {}).get("ending", {})
    if not ending_cfg.get("enabled", False):
        return ""
    preset = normalize_name(str(ending_cfg.get("preset", "auto"))).replace(" ", "_").replace("-", "_")
    if preset and preset != "auto":
        return preset if preset in ENDING_PRESETS else ""

    return infer_ending_preset_from_text(transcript_text)


def material_index_by_id(draft: dict):
    index = {}
    for key, items in draft.get("materials", {}).items():
        if isinstance(items, list):
            for item in items:
                item_id = item.get("id") if isinstance(item, dict) else None
                if item_id:
                    index[item_id] = (key, item)
    return index


def replace_ids(value, id_map: dict):
    if isinstance(value, dict):
        return {key: replace_ids(item, id_map) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_ids(item, id_map) for item in value]
    if isinstance(value, str):
        return id_map.get(value, value)
    return value


def clone_segment_with_materials(source_draft: dict, target_draft: dict, source_segment: dict):
    source_index = material_index_by_id(source_draft)
    source_ids = [source_segment.get("material_id")] + list(source_segment.get("extra_material_refs", []))
    id_map = {old_id: uuid_str() for old_id in source_ids if old_id}
    cloned_segment = replace_ids(copy.deepcopy(source_segment), id_map)
    cloned_materials = []

    for old_id in source_ids:
        if not old_id or old_id not in source_index:
            continue
        key, source_material = source_index[old_id]
        cloned_material = replace_ids(copy.deepcopy(source_material), id_map)
        cloned_material["id"] = id_map[old_id]
        if key == "videos":
            cloned_material["local_material_id"] = str(uuid.uuid4()).lower()
        target_draft["materials"].setdefault(key, []).append(cloned_material)
        cloned_materials.append((key, cloned_material))

    return cloned_segment, cloned_materials


def apply_replacement_video(cloned_materials, replacement_file: str):
    if not replacement_file:
        return
    replacement_path = Path(replacement_file)
    if not replacement_path.exists():
        raise FileNotFoundError(f"Vídeo de final não encontrado: {replacement_path}")
    replacement_duration_us = int(round(ffprobe_duration(replacement_path) * 1_000_000))
    for key, material in cloned_materials:
        if key != "videos":
            continue
        material["path"] = replacement_path.as_posix()
        material["material_name"] = replacement_path.name
        material["duration"] = replacement_duration_us
        material["extra_info"] = replacement_path.name
        material["file_Path"] = replacement_path.as_posix()


def ending_asset_path(profile: dict, preset: dict, key_name: str, fallback_file: str):
    asset_key = preset.get(key_name)
    assets = profile.get("capcut", {}).get("ending", {}).get("assets", {})
    candidates = []
    if asset_key and assets.get(asset_key):
        candidates.append(Path(assets[asset_key]))
    if preset.get("replacement_file") and key_name == "main_asset_key":
        candidates.append(Path(preset["replacement_file"]))
    if preset.get("fallback_file") and key_name == "main_asset_key":
        candidates.append(Path(r"C:\Wendller") / preset["fallback_file"])
    if fallback_file:
        candidates.append(Path(r"C:\Wendller") / fallback_file)

    for candidate in candidates:
        if candidate.exists():
            return candidate.as_posix()
    return ""


def find_video_segment_by_file(draft: dict, file_name: str, prefer_overlay: bool = False):
    videos = {item["id"]: item for item in draft.get("materials", {}).get("videos", [])}
    matches = []
    for track in draft.get("tracks", []):
        if track.get("type") != "video":
            continue
        is_overlay_track = track is not next((item for item in draft.get("tracks", []) if item.get("type") == "video"), None)
        for segment in track.get("segments", []):
            material = videos.get(segment.get("material_id"))
            if not material:
                continue
            material_name = material.get("material_name") or Path(material.get("path", "")).name
            if material_name.lower() == file_name.lower():
                matches.append((is_overlay_track, track, segment))
    if not matches:
        return None, None
    preferred = [item for item in matches if item[0] == prefer_overlay]
    _is_overlay, track, segment = (preferred or matches)[0]
    return track, segment


def load_reference_draft(project_name: str):
    drafts_root = Path(r"C:\Users\wendller.ferreira\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft")
    return load_json(drafts_root / project_name / "draft_content.json")


def add_ending_to_draft(draft: dict, profile: dict, total_duration: int, next_track_render_index: int, transcript_text: str = ""):
    preset_name = resolve_ending_preset(profile, transcript_text)
    if not preset_name:
        return total_duration, next_track_render_index, None

    preset = ENDING_PRESETS[preset_name]
    source_draft = load_reference_draft(preset["reference_project"])
    main_track = next(track for track in draft["tracks"] if track["type"] == "video")
    _reference_main_track, reference_main_segment = find_video_segment_by_file(source_draft, preset["main_file"], False)
    if not reference_main_segment:
        raise ValueError(f"Final de referência não encontrado: {preset['main_file']}")

    transition = build_transition(preset["transition"])
    draft["materials"]["transitions"].append(transition)
    if main_track.get("segments"):
        main_track["segments"][-1].setdefault("extra_material_refs", []).insert(2, transition["id"])

    main_segment, main_materials = clone_segment_with_materials(source_draft, draft, reference_main_segment)
    apply_replacement_video(main_materials, ending_asset_path(profile, preset, "main_asset_key", preset["main_file"]))
    main_duration = int(reference_main_segment["target_timerange"]["duration"])
    main_segment["target_timerange"]["start"] = total_duration
    main_segment["target_timerange"]["duration"] = main_duration
    main_segment["source_timerange"]["duration"] = int(reference_main_segment["source_timerange"]["duration"])
    main_segment["render_index"] = 0
    main_segment["track_render_index"] = 0
    main_track["segments"].append(main_segment)

    new_total_duration = total_duration + main_duration
    overlay_file = preset.get("overlay_file")
    if overlay_file:
        _reference_overlay_track, reference_overlay_segment = find_video_segment_by_file(source_draft, overlay_file, True)
        if not reference_overlay_segment:
            raise ValueError(f"Final sobreposto de referência não encontrado: {overlay_file}")
        overlay_segment, overlay_materials = clone_segment_with_materials(source_draft, draft, reference_overlay_segment)
        apply_replacement_video(overlay_materials, ending_asset_path(profile, preset, "overlay_asset_key", overlay_file))
        overlay_duration = int(reference_overlay_segment["target_timerange"]["duration"])
        overlay_segment["target_timerange"]["start"] = max(0, new_total_duration - overlay_duration)
        overlay_segment["target_timerange"]["duration"] = overlay_duration
        overlay_segment["source_timerange"]["duration"] = int(reference_overlay_segment["source_timerange"]["duration"])
        overlay_layer_index = max(90000, next_track_render_index)
        overlay_segment["track_render_index"] = overlay_layer_index
        overlay_segment["render_index"] = overlay_layer_index
        draft["tracks"].append(
            {
                "id": uuid_str(),
                "type": "video",
                "segments": [overlay_segment],
                "flag": 0,
                "attribute": 0,
                "name": "__ending_overlay_top__",
                "is_default_name": True,
            }
        )
        next_track_render_index += 1

    draft["duration"] = new_total_duration
    return new_total_duration, next_track_render_index, preset_name


def move_ending_overlay_tracks_to_top(draft: dict):
    ending_tracks = [
        track
        for track in draft.get("tracks", [])
        if track.get("type") == "video" and track.get("name") == "__ending_overlay_top__"
    ]
    if not ending_tracks:
        return
    draft["tracks"] = [
        track
        for track in draft.get("tracks", [])
        if not (track.get("type") == "video" and track.get("name") == "__ending_overlay_top__")
    ] + ending_tracks


def build_filter_effect(name: str, intensity_percent: float):
    normalized = normalize_name(name)
    if normalized not in FILTER_LIBRARY:
        known_filters = ", ".join(sorted(FILTER_LIBRARY))
        raise KeyError(f"Filtro nao configurado: {name!r} normalizado como {normalized!r}. Filtros conhecidos: {known_filters}")
    filter_data = copy.deepcopy(FILTER_LIBRARY[normalized])
    filter_data["id"] = uuid_str()
    filter_data["name"] = name
    filter_data["report_name"] = ""
    filter_data["type"] = "filter"
    filter_data["sub_type"] = "none"
    filter_data["value"] = intensity_percent / 100.0
    filter_data["visible"] = True
    filter_data["item_effect_type"] = 0
    filter_data["category_id"] = "100000"
    filter_data["category_name"] = ""
    filter_data["category_key"] = ""
    filter_data["sub_category_id"] = ""
    filter_data["sub_category_name"] = ""
    filter_data["platform"] = "all"
    filter_data["apply_target_type"] = 0
    filter_data["version"] = ""
    filter_data["adjust_params"] = []
    filter_data["time_range"] = None
    filter_data["formula_id"] = ""
    filter_data["enable_skin_tone_correction"] = False
    filter_data["algorithm_artifact_path"] = ""
    filter_data["intensity_key"] = ""
    filter_data["face_adjust_params"] = []
    filter_data["exclusion_group"] = []
    filter_data["panel_id"] = ""
    filter_data["bloom_params"] = None
    filter_data["request_id"] = ""
    filter_data["color_match_info"] = {
        "target_feature_path": "",
        "source_feature_path": "",
        "target_image_path": "",
    }
    filter_data["multi_language_current"] = ""
    filter_data["lumi_hub_path"] = ""
    filter_data["covering_relation_change"] = 0
    filter_data["beauty_face_auto_preset_id"] = ""
    filter_data["beauty_body_auto_preset_id"] = ""
    filter_data["beauty_face_auto_retouch_info"] = {
        "face_id": [],
        "beauty_face_auto_retouch_id": "",
    }
    filter_data["smart_color_mode"] = 0
    filter_data["is_from_intelligent_quality"] = False
    return filter_data


def build_filter_track_segment(material_id: str, duration_us: int, render_index: int, track_render_index: int, start_us: int = 0):
    return {
        "id": uuid_str(),
        "source_timerange": None,
        "target_timerange": {"start": start_us, "duration": duration_us},
        "render_timerange": {"start": 0, "duration": 0},
        "desc": "",
        "state": 0,
        "speed": 1.0,
        "is_loop": False,
        "is_tone_modify": False,
        "reverse": False,
        "intensifies_audio": False,
        "cartoon": False,
        "volume": 1.0,
        "last_nonzero_volume": 1.0,
        "clip": None,
        "uniform_scale": None,
        "material_id": material_id,
        "extra_material_refs": [],
        "render_index": render_index,
        "keyframe_refs": [],
        "enable_lut": False,
        "enable_adjust": False,
        "enable_hsl": False,
        "visible": True,
        "group_id": "",
        "enable_color_curves": True,
        "enable_hsl_curves": True,
        "track_render_index": track_render_index,
        "hdr_settings": None,
        "enable_color_wheels": True,
        "track_attribute": 0,
        "is_placeholder": False,
        "template_id": "",
        "enable_smart_color_adjust": False,
        "template_scene": "default",
        "common_keyframes": [],
        "caption_info": None,
        "responsive_layout": {
            "enable": False,
            "target_follow": "",
            "size_layout": 0,
            "horizontal_pos_layout": 0,
            "vertical_pos_layout": 0,
        },
        "enable_color_match_adjust": False,
        "enable_color_correct_adjust": False,
        "enable_adjust_mask": False,
        "raw_segment_id": "",
        "lyric_keyframes": None,
        "enable_video_mask": True,
        "digital_human_template_group_id": "",
        "color_correct_alg_result": "",
        "source": "segmentsourcenormal",
        "enable_mask_stroke": False,
        "enable_mask_shadow": False,
        "enable_color_adjust_pro": False,
    }


def build_filter_track(material_id: str, duration_us: int, render_index: int, track_render_index: int, start_us: int = 0):
    return {
        "id": uuid_str(),
        "type": "filter",
        "segments": [build_filter_track_segment(material_id, duration_us, render_index, track_render_index, start_us)],
        "flag": 0,
        "attribute": 0,
        "name": "",
        "is_default_name": True,
    }


def adjustment_value(effect_type: str, adjustments_cfg: dict):
    if not isinstance(adjustments_cfg, dict):
        return ADJUST_EFFECTS[effect_type]["value"]
    if effect_type not in adjustments_cfg:
        return 0.0 if adjustments_cfg else ADJUST_EFFECTS[effect_type]["value"]
    raw_value = float(adjustments_cfg.get(effect_type, 0.0))
    if effect_type in {"brightness", "light_sensation"}:
        return raw_value * 0.02140468227424752
    return raw_value * 0.02006688963210701


def build_adjust_effect(effect_type: str, adjustments_cfg: dict | None = None):
    template = ADJUST_EFFECTS[effect_type]
    return {
        "id": uuid_str(),
        "effect_id": "7501974767453474064",
        "resource_id": "7501974767453474064",
        "third_resource_id": "",
        "name": "",
        "report_name": "",
        "type": effect_type,
        "sub_type": "none",
        "path": template["path"],
        "value": adjustment_value(effect_type, adjustments_cfg or {}),
        "visible": True,
        "item_effect_type": 0,
        "category_id": "",
        "category_name": "",
        "category_key": "",
        "sub_category_id": "",
        "sub_category_name": "",
        "platform": "all",
        "apply_target_type": 0,
        "source_platform": 1,
        "version": template["version"],
        "adjust_params": [],
        "time_range": None,
        "formula_id": "",
        "enable_skin_tone_correction": False,
        "algorithm_artifact_path": "",
        "intensity_key": "",
        "face_adjust_params": [],
        "exclusion_group": [],
        "panel_id": "",
        "bloom_params": None,
        "request_id": "",
        "color_match_info": {"target_feature_path": "", "source_feature_path": "", "target_image_path": ""},
        "multi_language_current": "",
        "lumi_hub_path": f"{template['path']}/lumi_hub_path",
        "covering_relation_change": 0,
        "beauty_face_auto_preset_id": "",
        "beauty_body_auto_preset_id": "",
        "beauty_face_auto_retouch_info": {"face_id": [], "beauty_face_auto_retouch_id": ""},
        "smart_color_mode": 0,
        "is_from_intelligent_quality": False,
    }


def build_adjust_hsl():
    return {
        "id": uuid_str(),
        "constant_material_id": uuid_str(),
        "hsl_color_type": 1,
        "hue": 0,
        "saturation": 0,
        "lightness": 0,
        "interacting": True,
        "version": "1",
        "path": ADJUST_HSL_PATH,
        "type": "hsl",
        "lumi_hub_path": f"{ADJUST_HSL_PATH}/lumi_hub_path",
        "custom_color": "#FFE64444",
        "resource_id": "",
        "source_platform": 0,
    }


def build_adjust_placeholder():
    return {
        "id": uuid_str(),
        "name": "Ajuste1",
        "type": "adjust",
        "material_resource_id": "",
    }


def build_adjust_track(placeholder_id: str, extra_refs: list[str], duration_us: int, track_render_index: int, start_us: int = 0):
    return {
        "id": uuid_str(),
        "type": "adjust",
        "segments": [
            {
                "id": uuid_str(),
                "source_timerange": None,
                "target_timerange": {"start": start_us, "duration": duration_us},
                "render_timerange": {"start": 0, "duration": 0},
                "desc": "",
                "state": 0,
                "speed": 1.0,
                "is_loop": False,
                "is_tone_modify": False,
                "reverse": False,
                "intensifies_audio": False,
                "cartoon": False,
                "volume": 1.0,
                "last_nonzero_volume": 1.0,
                "clip": None,
                "uniform_scale": None,
                "material_id": placeholder_id,
                "extra_material_refs": extra_refs,
                "render_index": 0,
                "keyframe_refs": [],
                "enable_lut": True,
                "enable_adjust": True,
                "enable_hsl": True,
                "visible": True,
                "group_id": "",
                "enable_color_curves": True,
                "enable_hsl_curves": True,
                "track_render_index": track_render_index,
                "hdr_settings": None,
                "enable_color_wheels": True,
                "track_attribute": 0,
                "is_placeholder": False,
                "template_id": "",
                "enable_smart_color_adjust": False,
                "template_scene": "default",
                "common_keyframes": [],
                "caption_info": None,
                "responsive_layout": {
                    "enable": False,
                    "target_follow": "",
                    "size_layout": 0,
                    "horizontal_pos_layout": 0,
                    "vertical_pos_layout": 0,
                },
                "enable_color_match_adjust": False,
                "enable_color_correct_adjust": False,
                "enable_adjust_mask": True,
                "raw_segment_id": "",
                "lyric_keyframes": None,
                "enable_video_mask": True,
                "digital_human_template_group_id": "",
                "color_correct_alg_result": "",
                "source": "segmentsourcenormal",
                "enable_mask_stroke": False,
                "enable_mask_shadow": False,
                "enable_color_adjust_pro": False,
            }
        ],
        "flag": 0,
        "attribute": 0,
        "name": "",
        "is_default_name": True,
    }


def build_subtitle_style_payload(display_text: str, style_mode: str = "styled"):
    if style_mode == "plain":
        style = {
            "text": display_text,
            "styles": [
                {
                    "range": [0, len(display_text)],
                }
            ],
        }
        payload = json.dumps(style, ensure_ascii=False, separators=(",", ":"))
        return payload, payload

    style = {
        "text": display_text,
        "styles": [
            {
                "fill": {
                    "content": {
                        "render_type": "solid",
                        "solid": {"color": [1, 1, 1]},
                    }
                },
                "font": {
                    "path": FONT_PATH,
                    "id": "",
                },
                "size": 10,
                "useLetterColor": True,
                "shadows": [
                    {
                        "thickness_projection_angle": -45,
                        "thickness_projection_enable": False,
                        "diffuse": 0.021666666492819786,
                        "alpha": 0.15999999642372131,
                        "distance": 4.9999995231628418,
                        "content": {
                            "render_type": "solid",
                            "solid": {"color": [0, 0, 0]},
                        },
                        "angle": -45,
                        "thickness_projection_distance": 0,
                    }
                ],
                "range": [0, len(display_text)],
            }
        ],
    }
    base_style = copy.deepcopy(style)
    base_style["styles"][0]["shadows"][0]["diffuse"] = 0.0083333337679505348
    base_style["styles"][0]["shadows"][0]["distance"] = 13.000000953674316
    return json.dumps(style, ensure_ascii=False, separators=(",", ":")), json.dumps(base_style, ensure_ascii=False, separators=(",", ":"))


def build_subtitle_material(display_text: str, raw_text: str, words_payload: dict, group_id: str, style_mode: str = "styled"):
    content, base_content = build_subtitle_style_payload(display_text, style_mode)
    plain_style = style_mode == "plain"
    return {
        "recognize_task_id": "",
        "id": uuid_str(),
        "name": "",
        "recognize_text": raw_text,
        "recognize_model": "",
        "punc_model": "",
        "type": "subtitle",
        "content": content,
        "base_content": base_content,
        "words": words_payload,
        "current_words": {"start_time": [], "end_time": [], "text": []},
        "global_alpha": 1.0,
        "combo_info": {"text_templates": []},
        "caption_template_info": {
            "resource_id": "",
            "third_resource_id": "",
            "resource_name": "",
            "category_id": "",
            "category_name": "",
            "effect_id": "",
            "request_id": "",
            "path": "",
            "is_new": False,
            "source_platform": 0,
        },
        "layer_weight": 1,
        "letter_spacing": 0.0,
        "text_curve": None,
        "text_loop_on_path": False,
        "offset_on_path": 0.0,
        "enable_path_typesetting": False,
        "text_exceeds_path_process_type": 0,
        "text_typesetting_paths": None,
        "text_typesetting_paths_file": "",
        "text_typesetting_path_index": 0,
        "line_spacing": 0.02,
        "has_shadow": False,
        "shadow_color": "#000000",
        "shadow_alpha": 0.0 if plain_style else 0.1599999964237213,
        "shadow_smoothing": 0.0 if plain_style else 0.38999999687075615,
        "shadow_distance": 0.0 if plain_style else 4.999999523162842,
        "shadow_point": {"x": 0.636396042376431, "y": -0.636396042376431},
        "shadow_angle": -45.0,
        "shadow_thickness_projection_enable": False,
        "shadow_thickness_projection_angle": 0.0,
        "shadow_thickness_projection_distance": 0.0,
        "border_alpha": 1.0,
        "border_color": "",
        "border_width": 0.08,
        "border_mode": 0,
        "style_name": "",
        "text_color": "" if plain_style else "#ffffff",
        "text_alpha": 1.0,
        "font_name": "",
        "font_title": "none",
        "font_size": 0.0 if plain_style else 10.0,
        "font_path": "" if plain_style else FONT_PATH,
        "font_id": "",
        "font_resource_id": "",
        "initial_scale": 1.0,
        "font_url": "",
        "typesetting": 0,
        "alignment": 1,
        "line_feed": 1,
        "use_effect_default_color": True,
        "is_rich_text": False,
        "shape_clip_x": False,
        "shape_clip_y": False,
        "ktv_color": "",
        "text_to_audio_ids": [],
        "bold_width": 0.0,
        "italic_degree": 0,
        "underline": False,
        "underline_width": 0.05,
        "underline_offset": 0.22,
        "sub_type": 0,
        "check_flag": 39,
        "text_size": 0 if plain_style else 30,
        "font_category_name": "",
        "font_source_platform": 0,
        "font_third_resource_id": "",
        "font_category_id": "",
        "add_type": 1,
        "operation_type": 2,
        "recognize_type": 0,
        "fonts": [],
        "background_color": "#000000",
        "background_alpha": 1.0,
        "background_style": 0,
        "background_round_radius": 0.0,
        "background_width": 0.14,
        "background_height": 0.14,
        "background_vertical_offset": 0.0,
        "background_horizontal_offset": 0.0,
        "background_fill": "",
        "single_char_bg_enable": False,
        "single_char_bg_color": "",
        "single_char_bg_alpha": 1.0,
        "single_char_bg_round_radius": 0.3,
        "single_char_bg_width": 0.0,
        "single_char_bg_height": 0.0,
        "single_char_bg_vertical_offset": 0.0,
        "single_char_bg_horizontal_offset": 0.0,
        "font_team_id": "",
        "tts_auto_update": False,
        "text_preset_resource_id": "",
        "group_id": group_id,
        "preset_id": "",
        "preset_name": "",
        "preset_category": "",
        "preset_category_id": "",
        "preset_index": 0,
        "preset_has_set_alignment": False,
        "force_apply_line_max_width": False,
        "language": "pt-BR",
        "relevance_segment": [],
        "original_size": [],
        "fixed_width": -1.0,
        "fixed_height": -1.0,
        "line_max_width": 0.82,
        "oneline_cutoff": False,
        "cutoff_postfix": "",
        "subtitle_template_original_fontsize": 0.0,
        "subtitle_keywords": {"range": []},
        "inner_padding": -1.0,
        "multi_language_current": "none",
        "source_from": "",
        "is_lyric_effect": False,
        "lyric_group_id": "",
        "lyrics_template": {
            "resource_id": "",
            "resource_name": "",
            "panel": "",
            "effect_id": "",
            "path": "",
            "category_id": "",
            "category_name": "",
            "request_id": "",
        },
        "is_batch_replace": False,
        "is_words_linear": False,
        "ssml_content": "",
        "subtitle_keywords_config": None,
        "sub_template_id": -1,
        "translate_original_text": "",
    }


def build_text_segment(material_id: str, animation_id: str, start_us: int, duration_us: int, render_index: int, track_render_index: int):
    return {
        "id": uuid_str(),
        "source_timerange": None,
        "target_timerange": {
            "start": start_us,
            "duration": duration_us,
        },
        "render_timerange": {
            "start": 0,
            "duration": 0,
        },
        "desc": "",
        "state": 0,
        "speed": 1.0,
        "is_loop": False,
        "is_tone_modify": False,
        "reverse": False,
        "intensifies_audio": False,
        "cartoon": False,
        "volume": 1.0,
        "last_nonzero_volume": 1.0,
        "clip": {
            "scale": {"x": 1.0, "y": 1.0},
            "rotation": 0.0,
            "transform": {"x": 0.0, "y": -0.3328531855955681},
            "flip": {"vertical": False, "horizontal": False},
            "alpha": 1.0,
        },
        "uniform_scale": {"on": True, "value": 1.0},
        "material_id": material_id,
        "extra_material_refs": [animation_id],
        "render_index": render_index,
        "keyframe_refs": [],
        "enable_lut": False,
        "enable_adjust": False,
        "enable_hsl": False,
        "visible": True,
        "group_id": "",
        "enable_color_curves": True,
        "enable_hsl_curves": True,
        "track_render_index": track_render_index,
        "hdr_settings": None,
        "enable_color_wheels": True,
        "track_attribute": 0,
        "is_placeholder": False,
        "template_id": "",
        "enable_smart_color_adjust": False,
        "template_scene": "default",
        "common_keyframes": [],
        "caption_info": None,
        "responsive_layout": {
            "enable": False,
            "target_follow": "",
            "size_layout": 0,
            "horizontal_pos_layout": 0,
            "vertical_pos_layout": 0,
        },
        "enable_color_match_adjust": False,
        "enable_color_correct_adjust": False,
        "enable_adjust_mask": False,
        "raw_segment_id": "",
        "lyric_keyframes": None,
        "enable_video_mask": True,
        "digital_human_template_group_id": "",
        "color_correct_alg_result": "",
        "source": "segmentsourcenormal",
        "enable_mask_stroke": False,
        "enable_mask_shadow": False,
        "enable_color_adjust_pro": False,
    }


def build_material_animation():
    return {
        "id": uuid_str(),
        "type": "sticker_animation",
        "animations": [],
        "multi_language_current": "none",
    }


def clean_word_token(value: str) -> str:
    return value.strip()


def segment_start_seconds(words):
    return words[0]["start"]


def segment_end_seconds(words):
    return words[-1]["end"]


def should_ignore_leading_segment(current_words, next_words, silence_cfg: dict):
    if not next_words:
        return False

    start_seconds = segment_start_seconds(current_words)
    duration_seconds = segment_end_seconds(current_words) - start_seconds
    gap_to_next_seconds = segment_start_seconds(next_words) - segment_end_seconds(current_words)
    max_words = int(silence_cfg.get("discardLeadingSegmentMaxWords", 1))
    return (
        start_seconds <= float(silence_cfg.get("discardLeadingSegmentBeforeSeconds", 0.35))
        and len(current_words) <= max_words
        and duration_seconds <= float(silence_cfg.get("discardLeadingSegmentMaxDurationSeconds", 0.75))
        and gap_to_next_seconds >= float(silence_cfg.get("discardLeadingSegmentMinGapSeconds", 0.5))
    )


def select_meaningful_speech_segments(item_segments, silence_cfg: dict):
    selected_segments = list(item_segments)
    discarded_leading_segments = 0
    while len(selected_segments) > 1 and should_ignore_leading_segment(selected_segments[0], selected_segments[1], silence_cfg):
        selected_segments = selected_segments[1:]
        discarded_leading_segments += 1
    return selected_segments, discarded_leading_segments


def preferred_group_count(token_count: int) -> int:
    if token_count <= 3:
        return 1
    return max(1, math.ceil(token_count / 2.0))


def caption_break_score(group_tokens, target_length: float, target_words_per_group: int):
    line_text = " ".join(group_tokens)
    score = (len(line_text) - target_length) ** 2
    score += ((len(group_tokens) - target_words_per_group) ** 2) * 2
    if group_tokens and re.match(r"^[,.;:!?)]", group_tokens[0]):
        score += 25
    if group_tokens and re.match(r'^[("]$', group_tokens[-1]):
        score += 10
    for token in group_tokens[:-1]:
        if re.search(r"[,;:]$", token):
            score += 14
    return score


def split_words_into_caption_groups(words, minimum_words: int = 1, maximum_words: int = 3):
    if not words:
        return []
    if len(words) <= maximum_words:
        return [words]

    tokens = [word["text"] for word in words]
    group_count = preferred_group_count(len(tokens))
    target_length = max(4, len(" ".join(tokens)) / max(1, group_count))
    target_words = min(maximum_words, max(minimum_words, round(len(tokens) / max(1, group_count))))
    scores = {len(tokens): 0.0}
    paths = {len(tokens): []}
    for index in range(len(tokens) - 1, -1, -1):
        best_score = float("inf")
        best_path = None
        for size in range(minimum_words, maximum_words + 1):
            next_index = index + size
            if next_index > len(tokens) or next_index not in scores:
                continue
            group_tokens = tokens[index:next_index]
            total_score = caption_break_score(group_tokens, target_length, target_words) + scores[next_index] + 0.35
            if total_score < best_score:
                best_score = total_score
                best_path = [words[index:next_index]] + paths[next_index]
        scores[index] = best_score
        paths[index] = best_path or [words[index:index + minimum_words]]
    return paths[0]


def refine_trim_with_speech(trim: dict, speech_segments, minimum_output: float):
    if not speech_segments:
        return trim

    duration = trim["duration_seconds"]
    silence_cfg = trim.get("silence_config", {})
    speech_head_padding = max(0.0, silence_cfg.get("speechHeadPaddingSeconds", 0.0))
    speech_head_trim_bias = max(0.0, silence_cfg.get("speechHeadTrimBiasSeconds", 0.35))
    if trim.get("discarded_leading_segments", 0) > 0:
        speech_head_trim_bias = max(0.0, float(silence_cfg.get("speechHeadTrimBiasAfterDiscardSeconds", 0.0)))
    speech_tail_padding = max(0.0, silence_cfg.get("speechTailPaddingSeconds", 0.0))
    refined_start = max(0.0, segment_start_seconds(speech_segments[0]) - speech_head_padding + speech_head_trim_bias)
    refined_end_boundary = min(duration, segment_end_seconds(speech_segments[-1]) + speech_tail_padding)
    refined_end = max(0.0, duration - refined_end_boundary)
    refined_end = min(refined_end, trim.get("trim_end_seconds", refined_end))
    remaining = duration - refined_start - refined_end
    if remaining < minimum_output:
        return trim

    updated = copy.deepcopy(trim)
    updated["trim_start_seconds"] = refined_start
    updated["trim_end_seconds"] = refined_end
    updated["source_start_us"] = int(round(refined_start * 1_000_000))
    updated["source_duration_us"] = int(round(remaining * 1_000_000))
    return updated


def transcribe_media_items(media_items, minimum_words: int, maximum_words: int, minimum_output: float):
    from faster_whisper import WhisperModel

    bundled_model = Path(__file__).resolve().parent.parent / "runtime" / "models" / "faster-whisper-small"
    model_source = str(bundled_model) if bundled_model.exists() else "small"
    model = WhisperModel(model_source, device="cpu", compute_type="int8")
    results = []

    for item in media_items:
        path = item["path"]
        segments, _ = model.transcribe(str(path), language="pt", beam_size=1, word_timestamps=True, vad_filter=True)
        item_segments = []
        all_words = []
        for segment in segments:
            words = []
            for word in segment.words or []:
                token = clean_word_token(word.word)
                if not token:
                    continue
                payload = {
                    "text": token,
                    "start": float(word.start),
                    "end": float(word.end),
                }
                words.append(payload)
            if words:
                item_segments.append(words)

        selected_segments, discarded_leading_segments = select_meaningful_speech_segments(
            item_segments,
            item["trim"].get("silence_config", {}),
        )
        if not selected_segments:
            selected_segments = item_segments
            discarded_leading_segments = 0

        item["trim"]["discarded_leading_segments"] = discarded_leading_segments
        item["trim"] = refine_trim_with_speech(item["trim"], selected_segments, minimum_output)
        trim_start = item["trim"]["trim_start_seconds"]
        trim_end_boundary = item["trim"]["duration_seconds"] - item["trim"]["trim_end_seconds"]
        filtered_segments = []
        for words in selected_segments:
            filtered_words = []
            for word in words:
                if word["end"] <= trim_start or word["start"] >= trim_end_boundary:
                    continue
                filtered_words.append(
                    {
                        "text": word["text"],
                        "start": max(word["start"], trim_start),
                        "end": min(word["end"], trim_end_boundary),
                    }
                )
            if filtered_words:
                filtered_segments.append(filtered_words)
        results.append({"item": item, "segments": filtered_segments})
    return results


def build_subtitle_entries(transcribed_items, minimum_words: int, maximum_words: int, style_mode: str = "styled"):
    results = []
    timeline_offset_us = 0
    group_id = f"pt-BR_{int(time.time() * 1000)}"

    for entry in transcribed_items:
        item = entry["item"]
        trim_start = item["trim"]["trim_start_seconds"]
        for segment_words in entry["segments"]:
            for group_words in split_words_into_caption_groups(segment_words, minimum_words, maximum_words):
                abs_start_us = timeline_offset_us + int(round((group_words[0]["start"] - trim_start) * 1_000_000))
                abs_end_us = timeline_offset_us + int(round((group_words[-1]["end"] - trim_start) * 1_000_000))
                raw_text = " ".join(word["text"] for word in group_words).strip()

                relative_starts = []
                relative_ends = []
                relative_text = []
                for index, word in enumerate(group_words):
                    start_ms = int(round((word["start"] - group_words[0]["start"]) * 1000))
                    end_ms = int(round((word["end"] - group_words[0]["start"]) * 1000))
                    relative_starts.append(start_ms)
                    relative_ends.append(end_ms)
                    relative_text.append(word["text"])
                    if index < len(group_words) - 1:
                        relative_starts.append(end_ms)
                        relative_ends.append(end_ms)
                        relative_text.append(" ")

                words_payload = {
                    "start_time": relative_starts,
                    "end_time": relative_ends,
                    "text": relative_text,
                }
                material = build_subtitle_material(raw_text, raw_text, words_payload, group_id, style_mode)
                animation = build_material_animation()
                results.append(
                    {
                        "material": material,
                        "animation": animation,
                        "segment_start_us": abs_start_us,
                        "segment_duration_us": max(1, abs_end_us - abs_start_us),
                    }
                )
        timeline_offset_us += item["trim"]["source_duration_us"]

    return results


def sync_project_duration(video_segments):
    cursor = 0
    for segment in video_segments:
        segment["target_timerange"]["start"] = cursor
        segment["target_timerange"]["duration"] = segment["source_timerange"]["duration"]
        cursor += segment["target_timerange"]["duration"]
    return cursor


def patch_draft(profile: dict, draft_dir: Path):
    draft_path = draft_dir / "draft_content.json"
    draft_meta_path = draft_dir / "draft_meta_info.json"
    draft = load_json(draft_path)
    meta = load_json(draft_meta_path)
    capcut_cfg = profile.get("capcut", {})
    captions_cfg = capcut_cfg.get("captions", {})
    captions_enabled = captions_cfg.get("enabled", True)
    audio_cfg = capcut_cfg.get("audio", {})
    audio_enabled = audio_cfg.get("enabled", True)
    mute_video = audio_cfg.get("muteVideo", False)
    effects_enabled = capcut_cfg.get("effectsEnabled", True)
    adjustments_enabled = capcut_cfg.get("adjustmentsEnabled", True)
    transitions_enabled = capcut_cfg.get("transitions", {}).get("enabled", True)
    silence_cfg = profile.get("silence", {})
    needs_transcription = captions_enabled or (
        silence_cfg.get("enabled", False) and silence_cfg.get("useSpeechBoundaries", True)
    )

    if profile.get("capcut", {}).get("preserveExistingVideoEdits", False):
        stale_ref_ids = remove_existing_video_audio_processing(draft)
        remove_existing_audio_tracks(draft)
        main_video_track = next(track for track in draft["tracks"] if track["type"] == "video")
        video_materials = {item["id"]: item for item in draft["materials"]["videos"]}
        media_items = []
        for segment in main_video_track["segments"]:
            material = video_materials[segment["material_id"]]
            media_path = Path(material["path"])
            source_timerange = segment["source_timerange"]
            media_items.append(
                {
                    "segment": segment,
                    "material": material,
                    "path": media_path,
                    "trim": {
                        "source_start_us": int(source_timerange["start"]),
                        "source_duration_us": int(source_timerange["duration"]),
                    },
                }
            )
        if mute_video:
            mute_video_segments(media_items, stale_ref_ids)
        elif audio_enabled:
            apply_video_audio_processing(draft, media_items, profile, stale_ref_ids)
        else:
            for item in media_items:
                item["segment"]["extra_material_refs"] = [
                    ref for ref in item["segment"].get("extra_material_refs", []) if ref not in stale_ref_ids
                ]
        total_duration = int(draft.get("duration") or meta.get("tm_duration") or 0)
        next_track_render_index = max(
            segment.get("track_render_index", 0)
            for track in draft.get("tracks", [])
            for segment in track.get("segments", [])
        ) + 1
        background_music = add_background_music(draft, profile, total_duration, next_track_render_index)
        if background_music:
            draft["tracks"].append(background_music["track"])

        meta["tm_duration"] = total_duration
        meta["tm_draft_modified"] = int(time.time() * 1_000_000)
        write_json(draft_path, draft)
        write_json(draft_meta_path, meta)
        for extra_name in ["draft_content.json.bak", "template-2.tmp"]:
            extra_path = draft_dir / extra_name
            if extra_path.exists():
                write_json(extra_path, draft)
        for timeline_path in (draft_dir / "Timelines").glob("**/template-2.tmp"):
            write_json(timeline_path, draft)
        return {
            "duration_us": total_duration,
            "subtitle_count": len(draft["materials"].get("texts", [])),
            "background_music_path": "" if not background_music else str(background_music["path"]),
            "background_music_volume_db": None if not background_music else background_music["volume_db"],
            "background_music_source_start_seconds": None if not background_music else background_music["source_start_seconds"],
            "ending_preset": "",
            "trimmed_segments": [],
        }

    stale_ref_ids = remove_existing_overlay_tracks(draft)

    main_video_track = next(track for track in draft["tracks"] if track["type"] == "video")
    media_items = []
    video_materials = {item["id"]: item for item in draft["materials"]["videos"]}
    video_segments = main_video_track["segments"]

    for segment in video_segments:
        material = video_materials[segment["material_id"]]
        media_path = Path(material["path"])
        trim = detect_trim_points(media_path, profile["silence"])
        media_items.append({"segment": segment, "material": material, "path": media_path, "trim": trim})

    if needs_transcription:
        transcribed_items = transcribe_media_items(
            media_items,
            captions_cfg.get("minWordsPerLine", 1),
            captions_cfg.get("maxWordsPerLine", 3),
            profile["silence"].get("minimumOutputDurationSeconds", 0.75),
        )
    else:
        transcribed_items = [{"item": item, "segments": []} for item in media_items]
    transcript_text = transcribed_items_text(transcribed_items)

    for item in media_items:
        segment = item["segment"]
        trim = item["trim"]
        segment["source_timerange"]["start"] = trim["source_start_us"]
        segment["source_timerange"]["duration"] = trim["source_duration_us"]

    content_duration = sync_project_duration(video_segments)
    intro_cover = cover_config(profile, "intro")
    outro_cover = cover_config(profile, "outro")
    content_start = intro_cover["duration_us"] if intro_cover else 0
    if content_start:
        for segment in video_segments:
            segment["target_timerange"]["start"] += content_start
    add_cover_segments_to_main_track(draft, main_video_track, content_start, content_duration, intro_cover, outro_cover)
    total_duration = content_start + content_duration + (outro_cover["duration_us"] if outro_cover else 0)
    draft["duration"] = total_duration

    if mute_video:
        mute_video_segments(media_items, stale_ref_ids)
    elif audio_enabled:
        apply_video_audio_processing(draft, media_items, profile, stale_ref_ids)
    else:
        for item in media_items:
            item["segment"]["extra_material_refs"] = [
                ref for ref in item["segment"].get("extra_material_refs", []) if ref not in stale_ref_ids
            ]
    for index, item in enumerate(media_items):
        segment = item["segment"]
        if transitions_enabled and index < len(media_items) - 1:
            transition = build_transition()
            draft["materials"]["transitions"].append(transition)
            segment["extra_material_refs"].insert(2, transition["id"])

    next_track_render_index = max(track["segments"][0]["track_render_index"] if track.get("segments") else 0 for track in draft["tracks"]) + 1
    total_duration, next_track_render_index, ending_preset = add_ending_to_draft(
        draft,
        profile,
        total_duration,
        next_track_render_index,
        transcript_text,
    )
    background_music = add_background_music(draft, profile, total_duration, next_track_render_index)
    if background_music:
        draft["tracks"].append(background_music["track"])
        next_track_render_index += 1

    next_filter_render_index = 10000
    if effects_enabled:
        for effect in profile["capcut"]["effects"]:
            try:
                filter_effect = build_filter_effect(effect["name"], effect["intensity"])
            except KeyError:
                if effect.get("optional", False):
                    continue
                raise
            draft["materials"]["effects"].append(filter_effect)
            draft["tracks"].append(
                build_filter_track(
                    filter_effect["id"],
                    content_duration,
                    next_filter_render_index,
                    next_track_render_index,
                    content_start,
                )
            )
            next_track_render_index += 1
            next_filter_render_index += 1

    if adjustments_enabled:
        adjust_placeholder = build_adjust_placeholder()
        draft["materials"]["placeholders"].append(adjust_placeholder)
        adjust_effect_ids = []
        adjustments_cfg = profile.get("capcut", {}).get("adjustments", {})
        for effect_type in ["brightness", "contrast", "highlight", "shadow", "white", "black", "temperature", "tone", "light_sensation"]:
            adjust_effect = build_adjust_effect(effect_type, adjustments_cfg)
            draft["materials"]["effects"].append(adjust_effect)
            adjust_effect_ids.append(adjust_effect["id"])
        adjust_hsl = build_adjust_hsl()
        draft["materials"]["hsl"].append(adjust_hsl)
        adjust_effect_ids.append(adjust_hsl["id"])
        draft["tracks"].append(build_adjust_track(adjust_placeholder["id"], adjust_effect_ids, content_duration, next_track_render_index, content_start))
        next_track_render_index += 1

    subtitle_entries = []
    if captions_enabled:
        subtitle_entries = build_subtitle_entries(
            transcribed_items,
            captions_cfg.get("minWordsPerLine", 1),
            captions_cfg.get("maxWordsPerLine", 3),
            captions_cfg.get("style", "styled"),
        )
        if content_start:
            for entry in subtitle_entries:
                entry["segment_start_us"] += content_start
    text_segments = []
    render_index = 14000
    for entry in subtitle_entries:
        draft["materials"]["texts"].append(entry["material"])
        draft["materials"]["material_animations"].append(entry["animation"])
        text_segments.append(
            build_text_segment(
                entry["material"]["id"],
                entry["animation"]["id"],
                entry["segment_start_us"],
                entry["segment_duration_us"],
                render_index,
                next_track_render_index,
            )
        )
        render_index += 1
    if captions_enabled:
        draft["tracks"].append(
            {
                "id": uuid_str(),
                "type": "text",
                "segments": text_segments,
                "flag": 0,
                "attribute": 0,
                "name": "",
                "is_default_name": True,
            }
        )

    move_ending_overlay_tracks_to_top(draft)

    meta["tm_duration"] = total_duration
    meta["tm_draft_modified"] = int(time.time() * 1_000_000)

    write_json(draft_path, draft)
    write_json(draft_meta_path, meta)
    for extra_name in ["draft_content.json.bak", "template-2.tmp"]:
        extra_path = draft_dir / extra_name
        if extra_path.exists():
            write_json(extra_path, draft)
    for timeline_path in (draft_dir / "Timelines").glob("**/template-2.tmp"):
        write_json(timeline_path, draft)

    return {
        "duration_us": total_duration,
        "subtitle_count": len(subtitle_entries),
        "background_music_path": "" if not background_music else str(background_music["path"]),
        "background_music_volume_db": None if not background_music else background_music["volume_db"],
        "background_music_source_start_seconds": None if not background_music else background_music["source_start_seconds"],
        "ending_preset": ending_preset or "",
        "trimmed_segments": [
            {
                "path": item["path"].name,
                "trim_start_seconds": round(item["trim"]["trim_start_seconds"], 3),
                "trim_end_seconds": round(item["trim"]["trim_end_seconds"], 3),
                "output_duration_seconds": round(item["trim"]["source_duration_us"] / 1_000_000, 3),
            }
            for item in media_items
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--draft-dir", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    profile_path = Path(args.profile)
    if not profile_path.is_absolute():
        profile_path = project_root / profile_path
    draft_dir = Path(args.draft_dir)
    profile = load_profile(project_root, profile_path)
    result = patch_draft(profile, draft_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
