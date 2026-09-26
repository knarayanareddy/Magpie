"""COSTS — honest per-run cost tracking and unit economics (Darko improvement #3).
Art IV.3: report what we measured, not what we wish.
Sim runs report 'unmeasured (sim run)'; live runs report actual incurred spend."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class RunCosts:
    apify_calls: int = 0
    apify_cost_eur: float = 0.0
    llm_observe_calls: int = 0
    llm_judge_calls: int = 0
    llm_cost_eur: float = 0.0
    browser_actions: int = 0

    # Unit costs based on production tier pricing (Token Factory / Nebius / Apify)
    APIFY_PER_ITEM: float = 0.002       # €0.002 per scraped listing
    LLM_PER_OBSERVE: float = 0.002      # €0.002 per multimodal vision call
    LLM_PER_JUDGE: float = 0.001        # €0.001 per strict JSON judge call

    def add_apify(self, n_items: int) -> None:
        self.apify_calls += 1
        self.apify_cost_eur += n_items * self.APIFY_PER_ITEM

    def add_observe(self) -> None:
        self.llm_observe_calls += 1
        self.llm_cost_eur += self.LLM_PER_OBSERVE

    def add_judge(self) -> None:
        self.llm_judge_calls += 1
        self.llm_cost_eur += self.LLM_PER_JUDGE

    def add_browser(self) -> None:
        self.browser_actions += 1

    @property
    def total_eur(self) -> float:
        return round(self.apify_cost_eur + self.llm_cost_eur, 4)

    def cost_per_pursue(self, n_pursued: int) -> float | None:
        if n_pursued <= 0:
            return None
        return round(self.total_eur / n_pursued, 3)

    def summary_line(self, n_scanned: int, n_pursued: int, mode: str = "sim") -> str:
        if mode != "live":
            return "cost: unmeasured (sim run — live rates: Apify ~€0.002/item, TF ~€0.001/judge)"
        cpp = self.cost_per_pursue(n_pursued)
        cpp_str = f"€{cpp:.3f}/deal" if cpp is not None else "no deals yet"
        return (f"cost: €{self.total_eur:.3f} total "
                f"(Apify €{self.apify_cost_eur:.3f} + LLM €{self.llm_cost_eur:.3f}) · {cpp_str}")
