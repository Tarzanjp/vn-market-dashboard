"""Backfill HOSE breadth (tăng/giảm/tham chiếu) into public/data/history/*.jsonl.

Until 2026-09-06 there was no free source for this field, so it was only ever
filled via grok-fill.json — and in practice it froze on 2026-08-07. Once the
dashboard stopped substituting sample numbers, the "90 phiên" table went blank:
of the last 90 sessions exactly one had real breadth.

VNDirect finfo serves per-stock closes for HOSE by date without an API key, so
breadth is *counted* rather than looked up, and can be counted for past
sessions too. This script does that for every history row that has a real
VN-Index but no real breadth.

Idempotent by date, like the rest of the pipeline: rerunning rewrites the same
rows and touches no others. Rows whose count fails its own consistency check
are left exactly as they were.

    py automation/backfill_breadth.py                # all years present
    py automation/backfill_breadth.py --year 2026
    py automation/backfill_breadth.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
import time

from daily_update import (  # reuse the pipeline's own helpers, don't reimplement
    HISTORY_DIR,
    fetch_breadth,
    load_history_year,
    log,
    update_history_index,
    write_history_year,
)


def needs_backfill(row: dict) -> bool:
    """A real trading day whose breadth is absent or not real."""
    if row.get("vnIndex") is None:
        return False                                   # no session / no data
    q = (row.get("quality") or {}).get("breadth")
    # "proxy" is replaced too, not kept. Those rows came from grok-fill, and the
    # one that survived (2026-08-07) was measurably wrong: it recorded u=62 and
    # GTGD 18,141 where counting the constituents gives u=109 and 14,517. It
    # also spans a different universe (365 vs 428 names), so leaving it in place
    # would mix two populations inside the same ADR window.
    return q != "live"


def backfill_year(year: int, *, dry_run: bool = False, pause: float = 0.4) -> tuple[int, int]:
    rows = load_history_year(year)
    targets = [d for d in sorted(rows) if needs_backfill(rows[d])]
    log(f"{year}: {len(targets)} of {len(rows)} rows need breadth")
    done = failed = 0

    for i, date in enumerate(targets):
        if i:
            time.sleep(pause)                          # unauthenticated endpoint
        breadth, quality = fetch_breadth(date, {})
        if quality != "live" or not breadth:
            failed += 1
            continue
        if dry_run:
            done += 1
            continue
        row = rows[date]
        all_ = breadth["all"]
        # history rows carry the compact shape (see history_row_from_live)
        row["breadth"] = {
            "a": all_["a"], "d": all_["d"], "u": all_["u"], "gtgd": breadth["gtgd"],
        }
        row.setdefault("quality", {})["breadth"] = "live"
        done += 1

    if not dry_run and done:
        write_history_year(year, rows)
    return done, failed


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill HOSE breadth into history")
    ap.add_argument("--year", type=int, action="append")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    years = a.year or sorted(
        int(p.stem) for p in HISTORY_DIR.glob("*.jsonl") if p.stem.isdigit()
    )
    total_done = total_failed = 0
    for y in years:
        d, f = backfill_year(y, dry_run=a.dry_run)
        total_done += d
        total_failed += f

    log(f"backfill {'(dry-run) ' if a.dry_run else ''}done: {total_done} filled, "
        f"{total_failed} left unchanged")
    if not a.dry_run and total_done:
        update_history_index(set(years))
    return 0


if __name__ == "__main__":
    sys.exit(main())
