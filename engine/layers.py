"""Effect layer data structures for the v5 layer stack."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EffectLayer:
    effect_id: str
    enabled:   bool  = True
    opacity:   float = 1.0
    params:    dict[str, Any] = field(default_factory=dict)


@dataclass
class LayerStack:
    layers: list[EffectLayer] = field(default_factory=list)

    def enabled_layers(self) -> list[EffectLayer]:
        return [l for l in self.layers if l.enabled]

    def find(self, effect_id: str) -> EffectLayer | None:
        for l in self.layers:
            if l.effect_id == effect_id:
                return l
        return None
