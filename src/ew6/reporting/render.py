from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

from ew6.run.batch import JobResult
from ew6.run.rank import RankedItem


def _fmt_cfg(cfg: Dict[str, Any]) -> str:
    parts = []
    parts.append(f"market={cfg.get('market')} data={cfg.get('data')}")
    lb = cfg.get("lookback_hours")
    if lb is not None:
        parts.append(f"lookback={lb}h")
    parts.append(f"zigzag={cfg.get('zigzag_pct')}")
    if cfg.get("backtest"):
        parts.append(f"bt entry={cfg.get('entry_mode')} fee={cfg.get('fee_bps')}bps slip={cfg.get('slippage_bps')}bps")
    if cfg.get("walk_forward"):
        parts.append(f"wf mode={cfg.get('wf_mode')} splits={cfg.get('wf_splits')} min_bars={cfg.get('wf_min_bars')}")
    return " | ".join(parts)


def _compact_lines(results: List[JobResult], ranked: List[RankedItem], cfg: Dict[str, Any], max_jobs: int) -> List[str]:
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines: List[str] = []
    lines.append(f"EW6 {ts}")
    lines.append(_fmt_cfg(cfg))
    if ranked:
        top = ", ".join([f"{r.symbol}:{r.timeframe}:{r.score:.3f}" for r in ranked[:5]])
        lines.append(f"reco={top}")
    # Keep short summary for jobs
    show = results[:max_jobs]
    agg = f"jobs={len(results)} shown={len(show)}"
    lines.append(agg)
    if show:
        j0 = show[0]
        lines.append(f"sample={j0.symbol}:{j0.timeframe} bt_ret={getattr(j0,'bt_totalret',0.0):.2f} wf={getattr(j0,'wf_score',0.0):.2f}")
    return lines


def _pretty_lines(results: List[JobResult], ranked: List[RankedItem], cfg: Dict[str, Any], max_jobs: int, markdown: bool) -> List[str]:
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    b1 = "**" if markdown else ""
    b0 = "**" if markdown else ""
    lines: List[str] = []
    lines.append(f"{b1}EW6 summary{b0} ({ts})")
    lines.append(_fmt_cfg(cfg))
    lines.append("")
    if ranked:
        lines.append(f"{b1}Top recommendations{b0}:")
        for i, r in enumerate(ranked, 1):
            lines.append(f" {i}) {r.symbol} {r.timeframe} score={r.score:.3f}")
        lines.append("")
    lines.append(f"{b1}Jobs{b0}:")
    for jr in results[:max_jobs]:
        wf = ""
        if getattr(jr, "wf_splits", 0):
            wf = f" wf={jr.wf_score:.2f} pos={jr.wf_pos_frac:.2f}"
        bt = ""
        if getattr(jr, "bt_trades", 0):
            bt = f" ret={jr.bt_totalret:.2f} mdd={jr.bt_mdd:.2f} pf={jr.bt_pf:.2f}"
        lines.append(f"- {jr.symbol} {jr.timeframe} bars={jr.bars} patterns={jr.patterns}{bt}{wf}")
    if len(results) > max_jobs:
        lines.append(f"... ({len(results) - max_jobs} more jobs truncated)")
    return lines


def render_run_report(
    results: List[JobResult],
    ranked: List[RankedItem],
    cfg: Dict[str, Any],
    *,
    max_jobs: int = 25,
    fmt: str = "compact",
    markdown: bool = False,
) -> str:
    """Render report text.

    fmt:
      - compact: tek satırlık / kısa özet (default)
      - pretty : okunur çok satır

    markdown:
      - Telegram için basit bold kullanımı (parse_mode yok, sadece görsel).
    """
    fmt = (fmt or "compact").strip().lower()
    if fmt not in ("compact", "pretty"):
        fmt = "compact"
    if fmt == "compact":
        lines = _compact_lines(results, ranked, cfg, max_jobs=max_jobs)
    else:
        lines = _pretty_lines(results, ranked, cfg, max_jobs=max_jobs, markdown=markdown)
    return "\n".join(lines)
