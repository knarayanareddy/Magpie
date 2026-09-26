"""Market memory (US-10): SQLite price store, DB-first comps, verdict cache, learned fetch cadence, feedback.
Read paths are safe to call from anywhere; write paths are append-mostly. No seller/buyer fields (Art III)."""
