"""Pruning / candidate budget control for EW scanning.

M1 goal: prevent combinatorial explosion and keep best candidates.
We implement a simple beam search over partial wave legs and an NMS filter over final patterns.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Sequence, Tuple, TypeVar

from ew6.logging import get_logger

log = get_logger("ew6.pruner")

T = TypeVar("T")


@dataclass(frozen=True)
class BeamConfig:
    beam_width: int = 256
    max_candidates: int = 5000  # hard cap for generated candidates
    max_patterns: int = 50      # final kept patterns


def beam_search(
    layers: Sequence[Sequence[T]],
    score_fn: Callable[[Tuple[T, ...]], float],
    cfg: BeamConfig,
) -> List[Tuple[Tuple[T, ...], float]]:
    """Generic beam search selecting best tuples across multiple layers."""
    beam: List[Tuple[Tuple[T, ...], float]] = [(tuple(), 0.0)]
    generated = 0
    try:
        log.debug("beam start", extra={"layers": len(layers), "beam_width": cfg.beam_width, "max_candidates": cfg.max_candidates, "max_patterns": cfg.max_patterns})
    except Exception:
        pass

    for li, layer in enumerate(layers):
        try:
            log.debug("beam layer", extra={"i": li, "layer_size": len(layer), "beam_in": len(beam)})
        except Exception:
            pass
        next_beam: List[Tuple[Tuple[T, ...], float]] = []
        for prefix, _ in beam:
            for item in layer:
                cand = prefix + (item,)
                s = float(score_fn(cand))
                next_beam.append((cand, s))
                generated += 1
                if generated >= cfg.max_candidates:
                    break
            if generated >= cfg.max_candidates:
                break

        next_beam.sort(key=lambda x: x[1], reverse=True)
        beam = next_beam[: max(1, cfg.beam_width)]
        try:
            log.debug("beam kept", extra={"i": li, "beam_out": len(beam), "generated": generated})
        except Exception:
            pass
        if generated >= cfg.max_candidates:
            break

    beam.sort(key=lambda x: x[1], reverse=True)
    out = beam[: cfg.max_patterns]
    try:
        log.debug("beam done", extra={"out": len(out), "generated": generated})
    except Exception:
        pass
    return out


def overlap_ratio(a_span: Tuple[int, int], b_span: Tuple[int, int]) -> float:
    """Overlap ratio on index spans [start,end)."""
    a0, a1 = a_span
    b0, b1 = b_span
    inter = max(0, min(a1, b1) - max(a0, b0))
    union = max(a1, b1) - min(a0, b0)
    if union <= 0:
        return 0.0
    return inter / union


def nms_by_span(
    items: Sequence[T],
    span_fn: Callable[[T], Tuple[int, int]],
    score_fn: Callable[[T], float],
    overlap_thresh: float = 0.7,
    max_keep: int = 50,
) -> List[T]:
    """Non-maximum suppression by span overlap, keeping highest scoring items."""
    ordered = sorted(items, key=score_fn, reverse=True)
    kept: List[T] = []
    try:
        log.debug("nms start", extra={"items": len(items), "overlap_thresh": overlap_thresh, "max_keep": max_keep})
    except Exception:
        pass
    for it in ordered:
        sp = span_fn(it)
        ok = True
        for kt in kept:
            if overlap_ratio(sp, span_fn(kt)) >= overlap_thresh:
                ok = False
                break
        if ok:
            kept.append(it)
            if len(kept) >= max_keep:
                break
    try:
        log.debug("nms done", extra={"kept": len(kept)})
    except Exception:
        pass
    return kept
