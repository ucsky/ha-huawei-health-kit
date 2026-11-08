#!/usr/bin/env python3
"""First live test of the Health Kit cloud API, outside Home Assistant.

Runs the HUAWEI ID OAuth flow by hand, calls dailyPolymerize for each data type and saves the
raw responses (redacted) so the parsing in healthkit.py can be checked against real data.

Standard library only. Usage:

    python3 -I tools/probe.py --cred /path/to/cred.yml [--categories activity,weight]

cred.yml (same format as the other sira credentials):

    - ClientID: <App ID>
      Secret: <App secret>

Flow:
 1. the script prints the HUAWEI authorization URL: open it, sign in, accept;
 2. the browser lands on https://my.home-assistant.io/redirect/oauth?code=...: do NOT click
    "Open link", copy the whole URL from the address bar and paste it into the script;
 3. the script exchanges the code, tests the refresh token, calls the API and writes
    probe-output/<timestamp>/ (summary.md, one JSON file per call).

Tokens, the user id and device identifiers are never written: collector ids are hashed.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import re
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("healthkit", ROOT / "custom_components/huawei_health_kit/healthkit.py")
hk = importlib.util.module_from_spec(_spec)
sys.modules["healthkit"] = hk
_spec.loader.exec_module(hk)

REDIRECT_URI = "https://my.home-assistant.io/redirect/oauth"
X_VERSION = "ha_huawei_health_kit_probe"


def read_cred(path: Path) -> tuple[str, str]:
    """ClientID and Secret from a "- Key: value" file (parsed by hand: no PyYAML needed)."""
    c = dict(m.groups() for m in re.finditer(r"^[-\s]*(\w+):\s*(\S+)\s*$", path.read_text(), re.M))
    missing = [k for k in ("ClientID", "Secret") if k not in c]
    if missing:
        sys.exit(f"{path}: missing {', '.join(missing)}")
    return c["ClientID"], c["Secret"]


def http(method: str, url: str, *, data: bytes | None = None, headers: dict | None = None) -> tuple[int, dict, str]:
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, dict(r.headers), r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode()


def token_request(fields: dict) -> tuple[int, dict]:
    status, _, body = http(
        "POST", hk.OAUTH2_TOKEN,
        data=urllib.parse.urlencode(fields).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        return status, json.loads(body)
    except ValueError:
        return status, {"raw": body[:500]}


def describe_token(tok: dict) -> dict:
    """What the token response contains, without any secret value."""
    out = {k: ("<present>" if k in ("access_token", "refresh_token", "id_token") else v) for k, v in tok.items()}
    if "id_token" in tok:
        try:
            payload = tok["id_token"].split(".")[1]
            claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
            out["id_token_claims"] = sorted(claims)
            out["id_token_has_sub"] = bool(claims.get("sub"))
        except (IndexError, ValueError) as err:
            out["id_token_error"] = str(err)
    return out


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:10]


def redact(obj):
    """Keep the structure and data types, hash device-specific parts of collector ids."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in ("dataCollectorId", "originalDataCollectorId") and isinstance(v, str):
                parts = v.split(":")
                out[k] = ":".join(parts[:2] + [_hash(p) for p in parts[2:]])
            elif k in ("deviceId", "deviceUniqueId", "uniqueId", "userId", "openId", "unionId") and isinstance(v, str):
                out[k] = _hash(v)
            else:
                out[k] = redact(v)
        return out
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    return obj


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cred", type=Path, required=True, help="cred.yml with ClientID and Secret")
    ap.add_argument("--categories", default="activity,weight",
                    help=f"comma-separated, among {','.join(hk.CATEGORIES)} (default: activity,weight)")
    ap.add_argument("--tz", default="Europe/Paris")
    ap.add_argument("--out", type=Path, default=ROOT / "probe-output")
    args = ap.parse_args()

    categories = [c for c in args.categories.split(",") if c]
    unknown = [c for c in categories if c not in hk.CATEGORIES]
    if unknown:
        sys.exit(f"unknown categories: {unknown}")
    client_id, secret = read_cred(args.cred)
    tz = ZoneInfo(args.tz)
    out = args.out / datetime.now().strftime("%Y%m%d-%H%M%S")
    summary: list[str] = [f"# Health Kit probe {out.name}", "", f"Categories: {', '.join(categories)}", ""]

    def save(name: str, content) -> None:
        (out / f"{name}.json").write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n")

    # 1. Authorization
    state = secrets.token_urlsafe(16)
    scopes = hk.scopes_for(categories)
    url = hk.OAUTH2_AUTHORIZE + "?" + urllib.parse.urlencode({
        "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT_URI,
        "scope": " ".join(scopes), "access_type": "offline", "state": state,
    })
    print("\n1. Open this URL, sign in with your HUAWEI ID and accept:\n\n" + url + "\n")
    print("2. On the my.home-assistant.io page, do NOT click 'Open link'.")
    print("   Copy the whole URL from the address bar and paste it here.\n")
    pasted = input("URL> ").strip()
    query = urllib.parse.parse_qs(urllib.parse.urlparse(pasted).query)
    if "error" in query:
        sys.exit(f"authorization refused: {query}")
    code = (query.get("code") or [pasted if "://" not in pasted else ""])[0]
    if not code:
        sys.exit("no code= in the pasted URL")
    if query.get("state") and query["state"][0] != state:
        sys.exit("state mismatch: paste the URL of THIS authorization")

    # 2. Token exchange and refresh
    out.mkdir(parents=True, exist_ok=True)
    status, tok = token_request({"grant_type": "authorization_code", "code": code, "client_id": client_id,
                                 "client_secret": secret, "redirect_uri": REDIRECT_URI})
    save("token_exchange", {"status": status, "response": describe_token(tok)})
    summary += ["## OAuth", "", f"- token exchange: HTTP {status}", f"- scopes requested: {' '.join(scopes)}"]
    if status != 200 or "access_token" not in tok:
        summary.append(f"- error: {tok}")
        (out / "summary.md").write_text("\n".join(summary) + "\n")
        sys.exit(f"token exchange failed (HTTP {status}): {tok}")
    summary += [f"- scope granted: {tok.get('scope')}", f"- expires_in: {tok.get('expires_in')}",
                f"- refresh_token: {'yes' if tok.get('refresh_token') else 'NO'}",
                f"- id_token with sub: {describe_token(tok).get('id_token_has_sub')}"]
    access = tok["access_token"]
    if tok.get("refresh_token"):
        rstatus, rtok = token_request({"grant_type": "refresh_token", "refresh_token": tok["refresh_token"],
                                       "client_id": client_id, "client_secret": secret})
        save("token_refresh", {"status": rstatus, "response": describe_token(rtok)})
        summary.append(f"- refresh: HTTP {rstatus}, new refresh_token: {'yes' if rtok.get('refresh_token') else 'no'}")
        access = rtok.get("access_token", access)
    summary.append("")

    # 3. API calls
    def daily(types: list[str], start: date, end: date) -> tuple[int, dict, dict]:
        status, headers, body = http(
            "POST", hk.API_BASE + hk.DAILY_POLYMERIZE,
            data=json.dumps(hk.daily_body(types, start, end, tz)).encode(),
            headers={"Authorization": f"Bearer {access}", "Content-Type": "application/json; charset=UTF-8",
                     "x-client-id": client_id, "x-version": X_VERSION, "x-caller-trace-id": uuid4().hex},
        )
        try:
            data = json.loads(body) if body else {}
        except ValueError:
            data = {"raw": body[:2000]}
        meta = {k.lower(): v for k, v in headers.items() if k.lower().startswith("x-health")}
        return status, meta, data

    metrics = hk.metrics_for(categories)
    today = datetime.now(tz).date()
    calls = [(t, today - timedelta(days=6), today, "last 7 days") for t in hk.data_types(metrics)]
    first = hk.data_types(metrics)[0]
    calls += [(first, today - timedelta(days=29), today, "30-day window"),
              (first, today - timedelta(days=365 + 29), today - timedelta(days=365), "one year ago"),
              (first, date(2020, 1, 1), date(2020, 1, 30), "January 2020")]
    summary += ["## dailyPolymerize", "", "| data type | period | HTTP | groups | parsed days | x-health-* |",
                "|---|---|---|---|---|---|"]
    for i, (dtype, start, end, label) in enumerate(calls):
        status, meta, data = daily([dtype], start, end)
        parsed = hk.parse_daily(data, [m for m in metrics if m.data_type == dtype], tz) if status == 200 else {}
        save(f"{i:02d}_{dtype}_{start:%Y%m%d}", {"request": hk.daily_body([dtype], start, end, tz), "status": status,
                                                 "headers": meta, "response": redact(data), "parsed": parsed})
        days = {k: len(v) for k, v in parsed.items()}
        summary.append(f"| {dtype} | {label} | {status} | {len(data.get('group') or [])} | {days or '-'} | {meta or '-'} |")
        print(f"{dtype} ({label}): HTTP {status}")
    (out / "summary.md").write_text("\n".join(summary) + "\n")
    print(f"\nDone: {out}\nSend summary.md and the JSON files (no token or identifier inside).")


if __name__ == "__main__":
    main()
