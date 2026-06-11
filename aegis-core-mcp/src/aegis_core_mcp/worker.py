from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from . import tools


logger = logging.getLogger(__name__)


class Sender(Protocol):
    def send(self, target: str, message: str) -> "SendResult":
        ...


@dataclass(frozen=True)
class SendResult:
    success: bool
    metadata: dict[str, Any]


class DryRunSender:
    def send(self, target: str, message: str) -> SendResult:
        logger.info("dry-run send target=%s message=%s", target, message)
        return SendResult(True, {"mode": "dry_run", "target": target})


class HermesSendMessageSender:
    def __init__(self, hermes_agent_path: Path | None = None) -> None:
        self.hermes_agent_path = hermes_agent_path or _default_hermes_agent_path()
        self._send_message_tool = None

    def _load(self):
        if self._send_message_tool is not None:
            return self._send_message_tool
        _load_hermes_env()
        if not self.hermes_agent_path.exists():
            raise RuntimeError(f"Hermes agent path not found: {self.hermes_agent_path}")
        sys.path.insert(0, str(self.hermes_agent_path))
        from tools.send_message_tool import send_message_tool

        self._send_message_tool = send_message_tool
        return send_message_tool

    def send(self, target: str, message: str) -> SendResult:
        send_message_tool = self._load()
        raw = send_message_tool(
            {
                "action": "send",
                "target": target,
                "message": message,
            }
        )
        payload = _decode_sender_payload(raw)
        if payload.get("error"):
            return SendResult(False, payload)
        if payload.get("success") is False:
            return SendResult(False, payload)
        return SendResult(True, payload)


def _decode_sender_payload(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            return {"success": True, "raw": raw}
        return loaded if isinstance(loaded, dict) else {"success": True, "raw": loaded}
    return {"success": True, "raw": raw}


def _default_hermes_agent_path() -> Path:
    configured = os.environ.get("AEGIS_HERMES_AGENT_PATH", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[3] / "hermes-agent"


def _hermes_home() -> Path:
    configured = os.environ.get("HERMES_HOME", "").strip()
    return Path(configured).expanduser().resolve() if configured else Path.home() / ".hermes"


def _load_hermes_env() -> None:
    env_path = _hermes_home() / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except Exception as exc:
        logger.warning("failed to load Hermes env file %s: %s", env_path, exc)


def run_once(
    context: tools.CoreContext,
    sender: Sender,
    *,
    now: str | None = None,
    channel: str = "weixin",
    target: str | None = None,
    default_repeat_interval_minutes: int = 15,
    limit: int = 20,
) -> dict[str, Any]:
    result = tools.dispatch_due_reminders(
        context,
        now=now,
        channel=channel,
        target=target,
        default_repeat_interval_minutes=default_repeat_interval_minutes,
        limit=limit,
    )
    if not result["ok"]:
        logger.error("dispatch_due_reminders failed: %s", result["error"])
        return result

    deliveries: list[dict[str, Any]] = []
    for dispatch in result["data"]["dispatches"]:
        try:
            send_result = sender.send(dispatch["target"], dispatch["message"])
        except Exception as exc:
            logger.exception(
                "sender raised for task_id=%s reminder_id=%s target=%s",
                dispatch["task"]["id"],
                dispatch["reminder"]["id"],
                dispatch["target"],
            )
            send_result = SendResult(False, {"error": str(exc)})
        event_result = "reminder_sent" if send_result.success else "reminder_send_failed"
        event = tools.record_intervention_event(
            context,
            task_id=dispatch["task"]["id"],
            reminder_id=dispatch["reminder"]["id"],
            level=dispatch["reminder"]["level"],
            channel=dispatch["channel"],
            result=event_result,
            metadata={
                "source": "aegis_reminder_worker",
                "target": dispatch["target"],
                "attempt": dispatch["attempt"],
                "sender": send_result.metadata,
            },
        )
        delivery = {
            "dispatch": dispatch,
            "send_success": send_result.success,
            "send_metadata": send_result.metadata,
            "intervention_event": event.get("data", {}).get("intervention_event")
            if event.get("ok")
            else None,
            "event_error": event.get("error") if not event.get("ok") else None,
        }
        deliveries.append(delivery)
        if send_result.success:
            logger.info(
                "sent reminder task_id=%s reminder_id=%s target=%s",
                dispatch["task"]["id"],
                dispatch["reminder"]["id"],
                dispatch["target"],
            )
        else:
            logger.warning(
                "failed to send reminder task_id=%s reminder_id=%s target=%s error=%s",
                dispatch["task"]["id"],
                dispatch["reminder"]["id"],
                dispatch["target"],
                send_result.metadata,
            )

    return tools.ok(
        {
            "dispatch_count": len(result["data"]["dispatches"]),
            "delivery_count": len(deliveries),
            "deliveries": deliveries,
        }
    )


def run_loop(
    context: tools.CoreContext,
    sender: Sender,
    *,
    interval_seconds: int,
    channel: str,
    target: str | None,
    default_repeat_interval_minutes: int,
    limit: int,
) -> None:
    stop = False

    def request_stop(signum, frame) -> None:  # noqa: ANN001
        nonlocal stop
        stop = True
        logger.info("received signal %s; stopping after current tick", signum)

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    logger.info("Aegis reminder worker started interval=%ss channel=%s", interval_seconds, channel)
    while not stop:
        started = time.monotonic()
        run_once(
            context,
            sender,
            channel=channel,
            target=target,
            default_repeat_interval_minutes=default_repeat_interval_minutes,
            limit=limit,
        )
        elapsed = time.monotonic() - started
        sleep_for = max(interval_seconds - elapsed, 0)
        if sleep_for:
            time.sleep(sleep_for)
    logger.info("Aegis reminder worker stopped")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Aegis reminder worker that dispatches due reminders to Weixin."
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=tools.default_context().db_path,
        help="Aegis Core SQLite DB path. Defaults to $AEGIS_CORE_DB_PATH or package .data path.",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=30,
        help="Polling interval for daemon mode. Default: 30.",
    )
    parser.add_argument(
        "--channel",
        default="weixin",
        help="Default dispatch channel. Default: weixin.",
    )
    parser.add_argument(
        "--target",
        default=None,
        help="Override send_message target, for example weixin:filehelper.",
    )
    parser.add_argument(
        "--default-repeat-interval-minutes",
        type=int,
        default=15,
        help="Repeat interval when a reminder has no explicit repeat interval. Default: 15.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum due reminders processed per tick. Default: 20.",
    )
    parser.add_argument(
        "--hermes-agent-path",
        type=Path,
        default=None,
        help="Path to hermes-agent for importing tools.send_message_tool.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one tick and exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not send messages; record successful dry-run deliveries.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Python logging level. Default: INFO.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if args.interval_seconds <= 0:
        raise SystemExit("--interval-seconds must be greater than zero")

    context = tools.CoreContext(args.db_path.expanduser().resolve())
    tools.init_core(context)
    sender: Sender
    if args.dry_run:
        sender = DryRunSender()
    else:
        sender = HermesSendMessageSender(args.hermes_agent_path)

    if args.once:
        result = run_once(
            context,
            sender,
            channel=args.channel,
            target=args.target,
            default_repeat_interval_minutes=args.default_repeat_interval_minutes,
            limit=args.limit,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(0 if result["ok"] else 1)

    run_loop(
        context,
        sender,
        interval_seconds=args.interval_seconds,
        channel=args.channel,
        target=args.target,
        default_repeat_interval_minutes=args.default_repeat_interval_minutes,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
