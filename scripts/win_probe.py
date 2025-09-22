import sys, inspect
from pathlib import Path

sys.path.append("scripts")
import trade_mts_auto as t  # importe le module patché

dst = Path("logs/win_probe.txt")
dst.parent.mkdir(parents=True, exist_ok=True)
dst.write_text(
    f"WIN_FILE={inspect.getsourcefile(t)}\nLOGP={t._LOGP}\n", encoding="utf-8"
)
t.log("probe-from-win")  # écrit dans logs/guardrails.log
