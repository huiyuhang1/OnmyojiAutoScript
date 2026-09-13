"""Parse card income without confusing experience with jade/AP income."""
import re


def income_value(text, label):
    text = re.sub(r'\s+', '', text).replace(',', '').replace('，', '')
    match = re.search(re.escape(label) + r'[:：+＋]*(\d+)', text)
    return int(match.group(1)) if match else None


def experience_allowed(value):
    # Six-star cards give 2800 EXP/h; five-star cards give 2400 EXP/h.
    # Unknown, truncated and unexpected values must never authorize activation.
    return value is not None and 100 <= value <= 2400 and value % 100 == 0


def card_experience(resource, results):
    """Associate income with the EXP line immediately above it on the same card."""
    direct = income_value(resource.ocr_text, '经验')
    if direct is not None:
        return direct
    top = min(p[1] for p in resource.box)
    left = min(p[0] for p in resource.box)
    right = max(p[0] for p in resource.box)
    candidates = []
    for result in results:
        if '经验' not in result.ocr_text:
            continue
        bottom = max(p[1] for p in result.box)
        overlap = min(right, max(p[0] for p in result.box)) - max(left, min(p[0] for p in result.box))
        if overlap > 0 and 0 <= top - bottom <= 60:
            candidates.append(result)
    if len(candidates) != 1:
        return None
    return income_value(candidates[0].ocr_text, '经验')
