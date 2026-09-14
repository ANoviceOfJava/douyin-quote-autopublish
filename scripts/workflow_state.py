"""Persist and resume the Douyin quote-image publishing workflow."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STAGES = [
    "intake",
    "hot_topic_selected",
    "source_ready",
    "assets_ready",
    "content_ready",
    "browser_ready",
    "login_required",
    "upload_ready",
    "awaiting_schedule_confirmation",
    "submitted",
    "verified",
]

TERMINAL_BEFORE_CONFIRM = {"submitted", "verified"}
SOURCE_ROLES = {"exposure", "commentary", "official", "user_supplied"}
ASSET_MODES = {"event-cover-carousel", "native-subtitle-quote"}
STAGE_INDEX = {stage: index for index, stage in enumerate(STAGES)}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("state root must be a JSON object")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temp, path)


def deep_merge(target: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            deep_merge(target[key], value)
        else:
            target[key] = value
    return target


def load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"state file does not exist: {path}")
    return read_json(path)


def save_state(path: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = now_iso()
    write_json(path, state)


def parse_patch(raw: str) -> dict[str, Any]:
    if raw.startswith("@"):
        with Path(raw[1:]).open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    else:
        value = json.loads(raw)
    if not isinstance(value, dict):
        raise SystemExit("--json must decode to a JSON object")
    return value


def cmd_init(args: argparse.Namespace) -> None:
    state_path = Path(args.state).resolve()
    if state_path.exists() and not args.force:
        raise SystemExit(f"state file already exists: {state_path}")
    state = {
        "version": 1,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "platform": args.platform,
        "workdir": str(Path(args.workdir).resolve()),
        "outputs_dir": str(Path(args.outputs_dir).resolve()),
        "stage": "intake",
        "topic": {},
        "source": {"role": None, "published_at": None, "heat_evidence": None},
        "content": {"angle": None, "must_include": [], "excluded_outcomes": [], "title": None, "tags": [], "caption_mode": None, "template": None},
        "assets": {"mode": "event-cover-carousel", "cover_path": None, "cover_text": None, "content_images": []},
        "images": [],
        "music": {},
        "publish_policy": "confirm",
        "auto_publish": {"eligible": False, "reason": None, "event_fingerprint": None, "published_at": None, "publish_status": None},
        "schedule": {"timezone": "Asia/Shanghai", "requested_at": None, "minimum_allowed_at": None, "actual_at": None, "adjustment_reason": None, "confirmed": False, "status": "unset"},
        "browser": {"type": "iab", "tab_id": None, "url": None, "session_state": "unknown"},
        "fact_sources": [],
        "qa": {},
        "last_error": None,
    }
    save_state(state_path, state)
    print(state_path)


def cmd_show(args: argparse.Namespace) -> None:
    state = load_state(Path(args.state))
    print(json.dumps(state, ensure_ascii=False, indent=2))


def cmd_set_stage(args: argparse.Namespace) -> None:
    if args.stage not in STAGES:
        raise SystemExit(f"unknown stage: {args.stage}")
    path = Path(args.state)
    state = load_state(path)
    autonomous_ready = state.get("publish_policy") == "autonomous" and state.get("auto_publish", {}).get("eligible") is True
    if args.stage in TERMINAL_BEFORE_CONFIRM and not state.get("schedule", {}).get("confirmed") and not autonomous_ready:
        raise SystemExit("cannot enter submitted/verified before schedule confirmation or autonomous eligibility")
    state["stage"] = args.stage
    save_state(path, state)
    print(args.stage)


def cmd_set(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    patch = parse_patch(args.json)
    deep_merge(state, patch)
    save_state(path, state)
    print("updated")


def cmd_confirm_schedule(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load_state(path)
    schedule = state.setdefault("schedule", {})
    if not schedule.get("requested_at") or not schedule.get("actual_at"):
        raise SystemExit("schedule.requested_at and schedule.actual_at are required before confirmation")
    if schedule.get("requested_at") != schedule.get("actual_at") and not schedule.get("adjustment_reason"):
        raise SystemExit("schedule adjusted time requires adjustment_reason")
    schedule["confirmed"] = True
    schedule["confirmed_at"] = now_iso()
    schedule["status"] = "confirmed"
    state["stage"] = "awaiting_schedule_confirmation"
    save_state(path, state)
    print(json.dumps(schedule, ensure_ascii=False, indent=2))


def validate_assets(state: dict[str, Any], stage_index: int) -> list[str]:
    """Validate the selected asset layout before upload."""
    if stage_index < STAGE_INDEX["assets_ready"]:
        return []
    assets = state.get("assets")
    if not isinstance(assets, dict):
        return ["assets must be an object"]
    mode = assets.get("mode")
    if mode not in ASSET_MODES:
        return ["assets.mode must be event-cover-carousel/native-subtitle-quote"]
    if mode == "native-subtitle-quote":
        images = state.get("images")
        if not isinstance(images, list) or not images:
            return ["native-subtitle-quote requires images"]
        return []

    errors: list[str] = []
    cover_path = assets.get("cover_path")
    if not isinstance(cover_path, str) or not cover_path.strip():
        errors.append("event-cover-carousel requires assets.cover_path")
    elif not Path(cover_path).is_file():
        errors.append(f"assets.cover_path does not exist: {cover_path}")
    cover_text = assets.get("cover_text")
    if not isinstance(cover_text, str) or not cover_text.strip():
        errors.append("event-cover-carousel requires assets.cover_text")

    content_images = assets.get("content_images")
    if not isinstance(content_images, list) or len(content_images) != 4:
        errors.append("event-cover-carousel requires exactly 4 assets.content_images")
        return errors

    normalized: list[str] = []
    for index, image_path in enumerate(content_images):
        if not isinstance(image_path, str) or not image_path.strip():
            errors.append(f"assets.content_images[{index}] must be a non-empty path")
            continue
        if not Path(image_path).is_file():
            errors.append(f"assets.content_images[{index}] does not exist: {image_path}")
        normalized.append(os.path.normcase(os.path.abspath(image_path)))
    if len(normalized) == 4 and len(set(normalized)) != 4:
        errors.append("assets.content_images must contain 4 distinct files")
    if isinstance(cover_path, str) and cover_path.strip():
        normalized_cover = os.path.normcase(os.path.abspath(cover_path))
        if normalized_cover in normalized:
            errors.append("assets.cover_path must not appear in assets.content_images")
    return errors


def validate_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if state.get("version") != 1:
        errors.append("version must be 1")
    if state.get("stage") not in STAGES:
        errors.append(f"invalid stage: {state.get('stage')}")
    if not state.get("platform"):
        errors.append("platform is required")
    if not state.get("workdir"):
        errors.append("workdir is required")
    if not state.get("outputs_dir"):
        errors.append("outputs_dir is required")
    topic = state.get("topic")
    if state.get("stage") != "intake":
        if not isinstance(topic, dict) or not topic:
            errors.append("selected stage requires topic metadata")
        else:
            for key in ("title", "discovered_at", "age_hours", "source_urls", "fact_status", "freshness_decision"):
                if topic.get(key) in (None, "", []):
                    errors.append(f"topic.{key} is required")
            if topic.get("fact_status") == "unverified":
                errors.append("unverified topic cannot advance")
            if topic.get("freshness_decision") == "expired":
                errors.append("expired topic cannot advance")
    stage_index = STAGE_INDEX.get(state.get("stage"), -1)
    source = state.get("source")
    if stage_index >= STAGE_INDEX["source_ready"]:
        if not isinstance(source, dict) or source.get("role") not in SOURCE_ROLES:
            errors.append("source.role must be exposure/commentary/official/user_supplied")
    content = state.get("content")
    if stage_index >= STAGE_INDEX["content_ready"]:
        if not isinstance(content, dict) or not content.get("angle"):
            errors.append("content.angle is required before upload")
    errors.extend(validate_assets(state, stage_index))
    schedule = state.get("schedule")
    if not isinstance(schedule, dict):
        errors.append("schedule must be an object")
    else:
        if schedule.get("confirmed") and (not schedule.get("actual_at")):
            errors.append("confirmed schedule requires actual_at")
        if schedule.get("confirmed") and schedule.get("requested_at") != schedule.get("actual_at") and not schedule.get("adjustment_reason"):
            errors.append("adjusted confirmed schedule requires adjustment_reason")
        if schedule.get("confirmed") and not schedule.get("confirmed_at"):
            errors.append("confirmed schedule requires confirmed_at")
    autonomous_ready = state.get("publish_policy") == "autonomous" and state.get("auto_publish", {}).get("eligible") is True
    if state.get("stage") in TERMINAL_BEFORE_CONFIRM and not (schedule or {}).get("confirmed") and not autonomous_ready:
        errors.append("submitted/verified requires schedule confirmation or autonomous eligibility")
    return errors


def cmd_validate(args: argparse.Namespace) -> None:
    state = load_state(Path(args.state))
    errors = validate_state(state)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
    print("valid")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create a new workflow state file")
    init.add_argument("--state", required=True)
    init.add_argument("--workdir", required=True)
    init.add_argument("--outputs-dir", required=True)
    init.add_argument("--platform", default="douyin")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=cmd_init)

    show = sub.add_parser("show", help="print the state file")
    show.add_argument("--state", required=True)
    show.set_defaults(func=cmd_show)

    stage = sub.add_parser("set-stage", help="set the workflow stage")
    stage.add_argument("--state", required=True)
    stage.add_argument("--stage", required=True, choices=STAGES)
    stage.set_defaults(func=cmd_set_stage)

    update = sub.add_parser("set", help="deep-merge a JSON patch into the state")
    update.add_argument("--state", required=True)
    update.add_argument("--json", required=True, help="JSON object or @path/to/patch.json")
    update.set_defaults(func=cmd_set)

    confirm = sub.add_parser("confirm-schedule", help="record explicit user confirmation")
    confirm.add_argument("--state", required=True)
    confirm.set_defaults(func=cmd_confirm_schedule)

    validate = sub.add_parser("validate", help="validate state invariants")
    validate.add_argument("--state", required=True)
    validate.set_defaults(func=cmd_validate)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()