from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from ..models import (
    CoverageStatus,
    Evidence,
    Message,
    ModuleResult,
    Severity,
    Verdict,
)


URGENCY = re.compile(r"\b(urgent|immediately|right now|act fast|expires?|suspend(?:ed)?|last chance)\b", re.I)
SECRET = re.compile(r"\b(send|share|tell|confirm|verify)\b.{0,40}\b(otp|password|pin|cvv|verification code)\b", re.I)
PAYMENT = re.compile(r"\b(pay|payment|transfer|send money|gift card|upi|wallet)\b", re.I)
PROMOTION = re.compile(r"\b(sale|discount|promotion|limited offer|unsubscribe)\b", re.I)


def _evidence_id(sender_id: str, message_id: str, rule: str) -> str:
    digest = hashlib.sha256(f"{sender_id}:{message_id}:{rule}".encode()).hexdigest()[:12]
    return f"conv-{digest}"


def evaluate_conversation(messages: list[Message], protected_sender_id: str | None) -> ModuleResult:
    by_sender: dict[str, list[Message]] = defaultdict(list)
    for message in messages:
        if protected_sender_id is None or message.sender_id != protected_sender_id:
            by_sender[message.sender_id].append(message)

    for sender_id, sender_messages in by_sender.items():
        urgent = [message for message in sender_messages if URGENCY.search(message.text)]
        secrets = [message for message in sender_messages if SECRET.search(message.text)]
        payments = [message for message in sender_messages if PAYMENT.search(message.text)]
        risky = secrets or payments
        if urgent and risky:
            selected: list[tuple[Message, str, str]] = [
                (urgent[0], "urgency", "This sender introduced time pressure."),
                (
                    risky[0],
                    "credential_request" if secrets else "payment_request",
                    "The same sender requested a secret or payment action.",
                ),
            ]
            evidence = [
                Evidence(
                    id=_evidence_id(sender_id, message.id, rule),
                    indicator_type=rule,
                    source_module="conversation",
                    quote=message.text,
                    message_id=message.id,
                    explanation=explanation,
                )
                for message, rule, explanation in selected
            ]
            return ModuleResult(
                status=CoverageStatus.COMPLETE,
                version="conversation-rules-0.1.0",
                raw_score_type="rule_hits",
                verdict=Verdict.SUSPECTED_SCAM,
                severity=Severity.HIGH,
                score=len(evidence),
                evidence=evidence,
            )

    promotional = [message for group in by_sender.values() for message in group if PROMOTION.search(message.text)]
    if promotional:
        message = promotional[0]
        return ModuleResult(
            status=CoverageStatus.COMPLETE,
            version="conversation-rules-0.1.0",
            raw_score_type="rule_hits",
            verdict=Verdict.SPAM,
            severity=Severity.LOW,
            score=1,
            evidence=[
                Evidence(
                    id=_evidence_id(message.sender_id, message.id, "promotion"),
                    indicator_type="promotional_language",
                    source_module="conversation",
                    quote=message.text,
                    message_id=message.id,
                    explanation="This supplied message contains promotional language.",
                )
            ],
        )

    return ModuleResult(
        status=CoverageStatus.COMPLETE,
        version="conversation-rules-0.1.0",
        raw_score_type="rule_hits",
        verdict=Verdict.UNKNOWN,
        severity=Severity.UNKNOWN,
        score=0,
        detail="No authored escalation rule matched within a single sender's messages.",
    )
