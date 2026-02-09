from __future__ import annotations

from typing import Any, Dict, List


def _fmt_float(x: Any, nd: int = 2) -> str:
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return str(x)


def format_compact(*, results: List[Dict[str, Any]], ranked: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    if ranked:
        top = ", ".join([f"{r.get('symbol')}:{r.get('timeframe')}:{_fmt_float(r.get('score'), 3)}" for r in ranked[:10]])
        lines.append(f"reco: {top}")
    for r in results[:10]:
        sym = r.get("symbol")
        tf = r.get("timeframe")
        bt = ""
        if r.get("bt_trades") is not None and r.get("bt_trades", 0) > 0:
            bt = f" bt_trades={r.get('bt_trades')} ret={_fmt_float(r.get('bt_totalret'))} pf={_fmt_float(r.get('bt_pf'))}"
        wf = ""
        if r.get("wf_score") is not None and float(r.get("wf_score") or 0) > 0:
            wf = f" wf={_fmt_float(r.get('wf_score'), 2)}"
        lines.append(f"{sym} {tf}{bt}{wf}")
    if len(results) > 10:
        lines.append(f"... +{len(results)-10} more")
    return "\n".join(lines).strip() + "\n"


def format_pretty(*, results: List[Dict[str, Any]], ranked: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    if ranked:
        lines.append("Top recommendations:")
        for r in ranked[:10]:
            lines.append(f"- {r.get('symbol')} {r.get('timeframe')} score={_fmt_float(r.get('score'), 3)}")
        lines.append("")
    lines.append("Runs:")
    for r in results:
        sym = r.get("symbol")
        tf = r.get("timeframe")
        bars = r.get("bars")
        pats = r.get("patterns")
        conf = _fmt_float(r.get("best_conf"), 2)
        score = _fmt_float(r.get("best_score"), 2)
        line = f"- {sym} {tf} bars={bars} patterns={pats} best_score={score} best_conf={conf}"
        if r.get("bt_trades", 0) > 0:
            line += f" | BT trades={r.get('bt_trades')} win={_fmt_float(r.get('bt_winrate'),2)} ret={_fmt_float(r.get('bt_totalret'),2)} mdd={_fmt_float(r.get('bt_mdd'),2)} pf={_fmt_float(r.get('bt_pf'),2)}"
        if float(r.get("wf_score") or 0) > 0:
            line += f" | WF mode={r.get('wf_mode')} score={_fmt_float(r.get('wf_score'),2)} pos={_fmt_float(r.get('wf_pos'),2)}"
        lines.append(line)
    return "\n".join(lines).strip() + "\n"
