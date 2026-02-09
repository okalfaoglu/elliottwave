"""EW analyzer (M1.3): monowaves + budgeted candidate generation.

- Build monowaves from swings (skip/min_move).
- Generate 5-leg impulse candidates with optional gaps between legs.
- Beam search keeps candidate explosion under control.
- Score + confidence + NMS prune.

Requires:
- ew6.ew.core.pruner (beam_search, nms_by_span)
- ew6.ew.core.scorer (score_impulse, confidence_from_score)
- ew6.ew.core.rules_p5 (is_valid_impulse_from_monowaves)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from ew6.logging import get_logger

log = get_logger("ew6.analyzer")

from ew6.ew.core.model import WaveLeg, WavePattern
from ew6.ew.core.monowave import build_monowaves_from_swings, MonoWaveConfig
from ew6.ew.core.rules_p5 import is_valid_impulse_from_monowaves
from ew6.ew.core.scorer import score_impulse, confidence_from_score, ScoreConfig
from ew6.ew.core.pruner import nms_by_span, BeamConfig, beam_search
from ew6.ew.core.options import WaveOptions


@dataclass(frozen=True)
class AnalyzerConfig:
    monowave_skip: int = 1
    min_leg_abs_move: float = 0.0

    max_gap: int = 1
    beam_width: int = 256
    max_candidates: int = 5000

    max_patterns: int = 50
    nms_overlap: float = 0.70

    @staticmethod
    def from_options(opts: WaveOptions) -> "AnalyzerConfig":
        return AnalyzerConfig(
            monowave_skip=opts.monowave_skip,
            min_leg_abs_move=opts.min_leg_abs_move,
            max_gap=opts.max_gap,
            beam_width=opts.beam_width,
            max_candidates=opts.max_candidates,
            max_patterns=opts.max_patterns,
            nms_overlap=opts.nms_overlap,
        )


def _mw_to_leg(mw) -> WaveLeg:
    return WaveLeg(start_idx=mw.start_idx, end_idx=mw.end_idx, start_px=mw.start_px, end_px=mw.end_px)


def _layers(n: int, max_gap: int) -> List[List[int]]:
    layers: List[List[int]] = []
    layers.append(list(range(0, max(0, n - 4))))  # i0
    for _ in range(4):
        layers.append(list(range(1, max_gap + 2)))  # delta
    return layers


def scan_impulses_from_swings(swings, cfg: AnalyzerConfig) -> List[WavePattern]:
    try:
        log.debug("analyzer start", extra={"swings": len(swings) if hasattr(swings,'__len__') else None, "cfg": cfg.__dict__})
    except Exception:
        pass
    mws = build_monowaves_from_swings(swings, MonoWaveConfig(skip=cfg.monowave_skip, min_abs_move=cfg.min_leg_abs_move))
    n = len(mws)
    try:
        log.debug("analyzer monowaves", extra={"monowaves": n})
    except Exception:
        pass
    if n < 5:
        try:
            log.debug("analyzer early exit", extra={"reason": "monowaves<5"})
        except Exception:
            pass
        return []

    layers = _layers(n, cfg.max_gap)

    def score_prefix(tup: Tuple[int, ...]) -> float:
        if not tup:
            return 0.0
        i0 = tup[0]
        idxs = [i0]
        for d in tup[1:]:
            idxs.append(idxs[-1] + int(d))
        if idxs[-1] >= n:
            return -1e9

        if len(idxs) == 5:
            win = [mws[i] for i in idxs]
            ok, meta = is_valid_impulse_from_monowaves(win, return_meta=True)
            if not ok:
                return -1e6
            p = WavePattern(kind="impulse_1_5", legs=[_mw_to_leg(x) for x in win], meta=meta or {})
            sc = float(score_impulse(p, ScoreConfig()))
            gap_pen = 0.05 * sum(int(x) - 1 for x in tup[1:])
            return sc - gap_pen

        # partial alternation check
        if len(idxs) >= 2:
            dirs = [int(getattr(mws[i], "direction", 0)) for i in idxs]
            if 0 in dirs:
                return -1e9
            s = dirs[0]
            for k, dk in enumerate(dirs):
                exp = s if k % 2 == 0 else -s
                if dk != exp:
                    return -1e3
        return 0.0

    tuples_scores = beam_search(
        layers,
        score_prefix,
        BeamConfig(beam_width=cfg.beam_width, max_candidates=cfg.max_candidates, max_patterns=cfg.max_patterns),
    )
    try:
        log.debug("analyzer beam", extra={"kept": len(tuples_scores) if hasattr(tuples_scores,'__len__') else None})
    except Exception:
        pass

    patterns: List[WavePattern] = []
    for tup, _ in tuples_scores:
        if len(tup) != 5:
            continue
        i0 = tup[0]
        idxs = [i0]
        for d in tup[1:]:
            idxs.append(idxs[-1] + int(d))
        if idxs[-1] >= n:
            continue
        win = [mws[i] for i in idxs]
        ok, meta = is_valid_impulse_from_monowaves(win, return_meta=True)
        if not ok:
            continue
        p = WavePattern(kind="impulse_1_5", legs=[_mw_to_leg(x) for x in win], meta=meta or {})
        p.meta["score"] = float(score_impulse(p, ScoreConfig()))
        p.meta["confidence"] = float(confidence_from_score(float(p.meta["score"])))
        patterns.append(p)

    try:
        log.debug("analyzer patterns built", extra={"patterns": len(patterns)})
    except Exception:
        pass
    return nms_by_span(
        patterns,
        span_fn=lambda p: (p.start_idx, p.end_idx),
        score_fn=lambda p: float(p.meta.get("score", 0.0)),
        overlap_thresh=cfg.nms_overlap,
        max_keep=cfg.max_patterns,
    )
