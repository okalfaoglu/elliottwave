from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ew6.swing.zigzag import SwingPoint, SwingType


@dataclass(frozen=True)
class ImpulseRules:
    """Pragmatic impulse rules (v1).

    These are intentionally *conservative* and meant for early filtering:
    - Alternation of swing types (LOW/HIGH/LOW/HIGH/LOW/HIGH for upward)
    - Wave2 does not retrace past wave1 start
    - Wave3 is not the shortest among (1,3,5)
    - Wave4 does not overlap wave1 price territory (basic form)

    We'll extend/parameterize these later when we port the full P5 rule set.
    """

    enforce_wave4_overlap: bool = True


def _is_alt_types(sw: Sequence[SwingPoint]) -> bool:
    for a, b in zip(sw, sw[1:]):
        if a.kind == b.kind:
            return False
    return True


def is_upward_impulse(sw: Sequence[SwingPoint], rules: ImpulseRules) -> bool:
    if len(sw) != 6:
        return False
    if not _is_alt_types(sw):
        return False
    if sw[0].kind != SwingType.LOW or sw[1].kind != SwingType.HIGH:
        return False
    p0, p1, p2, p3, p4, p5 = [float(s.price) for s in sw]

    # Direction sanity: successive highs/lows should progress.
    if not (p1 > p0 and p3 > p2 and p5 > p4):
        return False

    # Wave2 should not retrace below start of wave1.
    if p2 <= p0:
        return False

    # Wave3 should exceed wave1 high (common impulse property).
    if p3 <= p1:
        return False

    w1 = abs(p1 - p0)
    w3 = abs(p3 - p2)
    w5 = abs(p5 - p4)

    if w3 < min(w1, w5):
        return False

    # Basic non-overlap rule: wave4 low should not fall into wave1 range.
    # Common simplified constraint: p4 > p1.
    if rules.enforce_wave4_overlap and p4 <= p1:
        return False

    return True


def is_downward_impulse(sw: Sequence[SwingPoint], rules: ImpulseRules) -> bool:
    if len(sw) != 6:
        return False
    if not _is_alt_types(sw):
        return False
    if sw[0].kind != SwingType.HIGH or sw[1].kind != SwingType.LOW:
        return False
    p0, p1, p2, p3, p4, p5 = [float(s.price) for s in sw]

    if not (p1 < p0 and p3 < p2 and p5 < p4):
        return False

    # Wave2 up should not retrace above start of wave1.
    if p2 >= p0:
        return False

    # Wave3 should go below wave1 low.
    if p3 >= p1:
        return False

    w1 = abs(p1 - p0)
    w3 = abs(p3 - p2)
    w5 = abs(p5 - p4)
    if w3 < min(w1, w5):
        return False

    # Non-overlap analogue: wave4 high should not rise into wave1 range.
    if rules.enforce_wave4_overlap and p4 >= p1:
        return False

    return True
