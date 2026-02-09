"""Auto-tuning for M1.

Goal: pick a WaveOptions set that yields a small number of *high-confidence* patterns
on the current sample window.

This is intentionally lightweight: we try a small grid and select the best_conf,
breaking ties by fewer patterns (less noise) then higher best_score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple, Optional

import time

from ew6.ew.core.options import WaveOptions
from ew6.ew.detectors.analyzer import scan_impulses_from_swings, AnalyzerConfig

from ew6.logging import get_logger

log = get_logger("ew6.tuner")


@dataclass(frozen=True)
class TuneResult:
    options: WaveOptions
    patterns: int
    best_score: float
    best_conf: float


def _summarize(patterns) -> Tuple[float, float]:
    if not patterns:
        return 0.0, 0.0
    best = max(patterns, key=lambda p: float(p.meta.get("score", 0.0)))
    return float(best.meta.get("score", 0.0)), float(best.meta.get("confidence", 0.0))


def tune_wave_options(
    swings,
    base: WaveOptions,
    monowave_skips: Iterable[int] = (1, 2),
    min_moves: Iterable[float] = (0.0,),
    max_gaps: Iterable[int] = (1, 2),
    beam_widths: Iterable[int] = (128, 256),
    max_patterns: int = 50,
    nms_overlap: float = 0.70,
) -> TuneResult:
    t0 = time.time()
    monowave_skips_l = list(monowave_skips)
    min_moves_l = list(min_moves)
    max_gaps_l = list(max_gaps)
    beam_widths_l = list(beam_widths)
    # grid size (best effort)
    try:
        grid = (len(monowave_skips_l) * len(min_moves_l) * len(max_gaps_l) * len(beam_widths_l))
    except Exception:
        grid = None
    log.debug("tune start", extra={"grid": grid, "max_patterns": max_patterns, "nms_overlap": nms_overlap})
    best: Optional[TuneResult] = None
    checked = 0
    for sk in monowave_skips_l:
        for mm in min_moves_l:
            for mg in max_gaps_l:
                for bw in beam_widths_l:
                    opts = WaveOptions(
                        monowave_skip=sk,
                        min_leg_abs_move=mm,
                        max_gap=mg,
                        beam_width=bw,
                        max_candidates=base.max_candidates,
                        max_patterns=max_patterns,
                        nms_overlap=nms_overlap,
                    )
                    pats = scan_impulses_from_swings(
                        swings,
                        AnalyzerConfig.from_options(opts),
                    )
                    bs, bc = _summarize(pats)
                    tr = TuneResult(opts, len(pats), bs, bc)
                    checked += 1
                    if checked % 25 == 0:
                        log.debug("tune progress", extra={"checked": checked, "best_conf": (best.best_conf if best else None), "best_patterns": (best.patterns if best else None)})
                    if best is None:
                        best = tr
                        log.debug("tune best", extra={"checked": checked, "best_conf": best.best_conf, "patterns": best.patterns, "score": best.best_score, "opts": best.options.__dict__})
                        continue
                    # primary: best_conf, then fewer patterns, then best_score
                    if (tr.best_conf, -tr.patterns, tr.best_score) > (best.best_conf, -best.patterns, best.best_score):
                        best = tr
                        log.debug("tune best", extra={"checked": checked, "best_conf": best.best_conf, "patterns": best.patterns, "score": best.best_score, "opts": best.options.__dict__})
    assert best is not None
    log.debug("tune done", extra={"checked": checked, "elapsed_s": round(time.time()-t0, 3), "best_conf": best.best_conf, "patterns": best.patterns, "score": best.best_score})
    return best
