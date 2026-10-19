import json, os, re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Chicago")
OUT = os.environ.get("ICS_PATH", "calendar/assignments.ics")
STAMP = "20260101T000000Z"


def norm(k):
    return re.sub(r"\s+", " ", str(k)).strip().lower()


def get(item, name):
    for k, v in item.items():
        if norm(k) == name:
            return v
    return None


def parse_time(s):
    m = re.match(r"\s*(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m", str(s or ""), re.I)
    if not m:
        return 23, 59
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3).lower()
    if ap == "p" and h != 12:
        h += 12
    if ap == "a" and h == 12:
        h = 0
    return h, mi


def esc(s):
    return str(s).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def utc(d):
    return d.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


items = json.load(open("items.json")).get("items", [])
lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Wespiseb//Assignments//EN",
    "CALSCALE:GREGORIAN",
    "X-WR-CALNAME:Assignments",
    "X-WR-TIMEZONE:America/Chicago",
    "REFRESH-INTERVAL;VALUE=DURATION:PT1H",
]

for it in items:
    due = get(it, "due date")
    if not due or norm(get(it, "status") or "") == "done":
        continue
    try:
        y, mo, d = map(int, str(due)[:10].split("-"))
    except ValueError:
        continue
    h, mi = parse_time(get(it, "time due"))
    end = datetime(y, mo, d, h, mi, tzinfo=TZ)
    start = end - timedelta(minutes=30)
    content = it.get("content") or {}
    title = it.get("title") or content.get("title") or "Assignment"
    num = content.get("number", it.get("id", title))
    lines += [
        "BEGIN:VEVENT",
        f"UID:issue-{num}@wespiseb",
        f"DTSTAMP:{STAMP}",
        f"DTSTART:{utc(start)}",
        f"DTEND:{utc(end)}",
        f"SUMMARY:{esc(title)}",
        f"DESCRIPTION:{esc('Due ' + end.strftime('%a %b %d, %I:%M %p'))}",
    ]
    if content.get("url"):
        lines.append(f"URL:{content['url']}")
    for trig, label in (("-P1D", "Due tomorrow"), ("-PT2H", "Due in 2 hours")):
        lines += [
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{label}: {esc(title)}",
            f"TRIGGER:{trig}",
            "END:VALARM",
        ]
    lines.append("END:VEVENT")

lines.append("END:VCALENDAR")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", newline="").write("\r\n".join(lines) + "\r\n")
print(f"Wrote {OUT}")
