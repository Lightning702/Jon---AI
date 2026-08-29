from __future__ import annotations

from dataclasses import dataclass

CHARS_PER_TOKEN = 3.0
MIN_KEEP = 2
DIGEST_PER_MESSAGE = 180
DIGEST_LIMIT = 2000
SINGLE_MESSAGE_SHARE = 0.4
CUT_MARK = "\n\n[... Mitte gekuerzt ...]\n\n"


@dataclass
class TrimResult:
    messages: list
    dropped: int
    shortened: int


def budget_chars(tokens: int) -> int:
    return int(max(tokens, 1000) * CHARS_PER_TOKEN)


def shorten_middle(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    keep = max(limit - len(CUT_MARK), 200)
    head = keep * 2 // 3
    tail = keep - head
    return text[:head] + CUT_MARK + text[-tail:]


def _digest(dropped: list) -> str:
    parts: list[str] = []
    used = 0
    for message in dropped:
        label = "Du" if message.role == "assistant" else "Nutzer"
        body = " ".join(str(message.content).split())
        if len(body) > DIGEST_PER_MESSAGE:
            body = body[: DIGEST_PER_MESSAGE - 1] + "…"
        line = f"{label}: {body}"
        if used + len(line) > DIGEST_LIMIT:
            break
        parts.append(line)
        used += len(line)
    if not parts:
        return ""
    return (
        "Frueher in diesem Gespraech (gekuerzt, damit der Verlauf ins Modell passt):\n"
        + "\n".join(parts)
    )


def trim_history(messages: list, tokens: int, make_message) -> TrimResult:
    limit = budget_chars(tokens)
    system = [m for m in messages if m.role == "system"]
    rest = [m for m in messages if m.role != "system"]
    used = sum(len(str(m.content)) for m in system)

    single_limit = int(limit * SINGLE_MESSAGE_SHARE)
    shortened = 0
    normalised = []
    for message in rest:
        content = str(message.content)
        if len(content) > single_limit:
            content = shorten_middle(content, single_limit)
            shortened += 1
            message = make_message(message.role, content)
        normalised.append(message)

    kept: list = []
    for message in reversed(normalised):
        size = len(str(message.content))
        if kept and len(kept) >= MIN_KEEP and used + size > limit:
            break
        used += size
        kept.append(message)
    kept.reverse()

    dropped = normalised[: len(normalised) - len(kept)]
    result = list(system)
    if dropped:
        text = _digest(dropped)
        if text:
            result.append(make_message("system", text))
    result.extend(kept)
    return TrimResult(messages=result, dropped=len(dropped), shortened=shortened)
