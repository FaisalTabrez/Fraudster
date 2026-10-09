from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit

from ..models import CoverageStatus, Evidence, ModuleResult, Severity, Verdict


SCAM_TEXT = re.compile(r"\b(share|send|confirm|verify)\b.{0,45}\b(otp|password|pin|cvv|account)\b", re.I)
SPAM_TEXT = re.compile(r"\b(sale|discount|promotion|limited offer|unsubscribe)\b", re.I)
OTP_NOTICE = re.compile(r"\b(otp|one[- ]time password|verification code)\b", re.I)


def _id(module: str, value: str, indicator: str) -> str:
    digest = hashlib.sha256(f"{module}:{indicator}:{value}".encode()).hexdigest()[:12]
    return f"fixture-{module}-{digest}"


def fixture_text_result(text: str) -> ModuleResult:
    scam_match = SCAM_TEXT.search(text)
    if scam_match:
        quote = scam_match.group(0)
        return ModuleResult(
            status=CoverageStatus.COMPLETE,
            version="fixture-text-0.1.0",
            raw_score_type="fixture_rule_hits",
            verdict=Verdict.SUSPECTED_SCAM,
            severity=Severity.HIGH,
            score=1,
            fixture_generated=True,
            evidence=[
                Evidence(
                    id=_id("text", quote, "secret_request"),
                    indicator_type="secret_request",
                    source_module="text",
                    quote=quote,
                    explanation="Fixture rule matched a request to disclose or verify a secret.",
                )
            ],
        )

    spam_match = SPAM_TEXT.search(text)
    if spam_match:
        quote = spam_match.group(0)
        return ModuleResult(
            status=CoverageStatus.COMPLETE,
            version="fixture-text-0.1.0",
            raw_score_type="fixture_rule_hits",
            verdict=Verdict.SPAM,
            severity=Severity.LOW,
            score=1,
            fixture_generated=True,
            evidence=[
                Evidence(
                    id=_id("text", quote, "promotion"),
                    indicator_type="promotional_language",
                    source_module="text",
                    quote=quote,
                    explanation="Fixture rule matched promotional language.",
                )
            ],
        )

    indicator = "otp_notification" if OTP_NOTICE.search(text) else "neutral_fixture"
    quote = OTP_NOTICE.search(text).group(0) if OTP_NOTICE.search(text) else text[:120]
    return ModuleResult(
        status=CoverageStatus.COMPLETE,
        version="fixture-text-0.1.0",
        raw_score_type="fixture_rule_hits",
        verdict=Verdict.LEGITIMATE,
        severity=Severity.LOW,
        score=0,
        fixture_generated=True,
        evidence=[
            Evidence(
                id=_id("text", quote, indicator),
                indicator_type=indicator,
                source_module="text",
                quote=quote,
                explanation="Fixture data selected the authored benign example path; this is not a live prediction.",
            )
        ],
    )


def fixture_url_result(urls: list[str]) -> ModuleResult:
    evidence: list[Evidence] = []
    score = 0
    for url in urls:
        parsed = urlsplit(url if "://" in url else f"http://{url}")
        hostname = parsed.hostname or ""
        observations: list[tuple[str, str | int | bool, str]] = []
        if parsed.username:
            observations.append(("userinfo_in_url", True, "The URL contains user-info before the host."))
            score += 3
        if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", hostname):
            observations.append(("ip_address_host", hostname, "The host is written as an IP address."))
            score += 3
        if hostname.startswith("xn--") or ".xn--" in hostname:
            observations.append(("punycode_host", hostname, "The host uses an internationalized punycode label."))
            score += 2
        if hostname.count("-") >= 3:
            observations.append(("many_host_hyphens", hostname.count("-"), "The host contains several hyphens."))
            score += 1
        for indicator, value, explanation in observations:
            evidence.append(
                Evidence(
                    id=_id("url", url, indicator),
                    indicator_type=indicator,
                    source_module="url",
                    quote=url,
                    observed_value=value,
                    explanation=explanation,
                )
            )

    if score >= 3:
        verdict, severity = Verdict.SUSPECTED_SCAM, Severity.HIGH
    elif score:
        verdict, severity = Verdict.UNKNOWN, Severity.MEDIUM
    else:
        verdict, severity = Verdict.LEGITIMATE, Severity.LOW
        url = urls[0]
        evidence.append(
            Evidence(
                id=_id("url", url, "no_fixture_indicator"),
                indicator_type="no_fixture_indicator",
                source_module="url",
                quote=url,
                observed_value=0,
                explanation="No authored fixture URL indicator matched; this does not guarantee safety.",
            )
        )

    return ModuleResult(
        status=CoverageStatus.COMPLETE,
        version="fixture-url-policy-0.1.0",
        raw_score_type="fixture_policy_points",
        verdict=verdict,
        severity=severity,
        score=score,
        evidence=evidence,
        fixture_generated=True,
    )
