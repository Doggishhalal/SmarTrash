import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

CONFIG_PATH = Path(__file__).with_name("training_config.json")


def _load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_config(path: Path, config: Dict[str, Any]) -> None:
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def run_if_due(config_path: Path | None = None, db=None) -> Dict[str, Any]:
    path = config_path or CONFIG_PATH
    config = _load_config(path)

    enabled = bool(config.get("enabled", False))
    if not enabled:
        return {"status": "disabled"}

    interval_days = int(config.get("interval_days", 7) or 7)
    last_run_at = _parse_timestamp(str(config.get("last_run_at", "") or ""))
    if last_run_at and (datetime.utcnow() - last_run_at) < timedelta(days=interval_days):
        return {"status": "not_due"}

    dataset_dir = str(config.get("dataset_dir", "")).strip()
    train_command = config.get("train_command", [])
    export_feedback = bool(config.get("export_verified_feedback", False))

    if not dataset_dir or not isinstance(train_command, list) or not train_command:
        config["last_status"] = "not_configured"
        _save_config(path, config)
        return {"status": "not_configured"}

    if not os.path.isdir(dataset_dir):
        config["last_status"] = "dataset_dir_missing"
        _save_config(path, config)
        return {"status": "dataset_dir_missing"}

    if export_feedback:
        try:
            from sample_memory import export_training_dataset

            export_training_dataset(train_ratio=0.8)
        except Exception:
            pass

    started_at = _now_iso()
    config["last_run_at"] = started_at
    config["last_status"] = "started"
    _save_config(path, config)

    try:
        result = subprocess.run(train_command, cwd=str(Path(__file__).parent), check=False)
        exit_code = int(result.returncode)
    except Exception as exc:
        exit_code = 1
        config["last_status"] = f"error:{exc}"
    else:
        config["last_status"] = "success" if exit_code == 0 else f"exit_code:{exit_code}"

    config["last_exit_code"] = exit_code
    _save_config(path, config)

    if db is not None:
        try:
            db.add_self_improvement_run(
                event_type="auto_retrain",
                status=config.get("last_status", "unknown"),
                report={"config": {"dataset_dir": dataset_dir, "train_command": train_command}},
            )
        except Exception:
            pass

    return {"status": "started", "exit_code": exit_code}
