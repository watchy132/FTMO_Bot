# check_env.py
import os, sys, csv
from datetime import datetime, timezone

# ===== MT5 =====
try:
    import MetaTrader5 as mt5
except Exception as e:
    print(f"[ERREUR] MetaTrader5 non importable: {e}")
    sys.exit(1)

CSV_PATH = "journal_ftmo.csv"


def check_openai_key() -> bool:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        print("[X] OPENAI_API_KEY manquante (\n  export OPENAI_API_KEY=...\n)")
        return False
    print("[OK] OPENAI_API_KEY chargée")
    return True


def check_mt5() -> bool:
    if not mt5.initialize():
        err = mt5.last_error()
        print(f"[X] MT5 initialize() a échoué: {err}")
        return False
    info = mt5.terminal_info()
    vers = getattr(info, "version", None)
    print(f"[OK] MT5 connecté • version={vers}")
    mt5.shutdown()
    return True


def check_csv_write() -> bool:
    header = [
        "ts",
        "symbol",
        "direction",
        "entry",
        "sl",
        "tp",
        "risk_pct",
        "lot",
        "rrr_planned",
        "action",
        "reason",
        "pnl",
        "equity",
    ]
    exists = os.path.exists(CSV_PATH)
    try:
        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(header)
            w.writerow(
                [datetime.now(timezone.utc).isoformat(), "ENV_CHECK", "-", 0, 0, 0, 0, 0, 0, "CHECK", "init", 0, 0]
            )
        print(f"[OK] Écriture CSV → {CSV_PATH}")
        return True
    except Exception as e:
        print(f"[X] Écriture CSV impossible: {e}")
        return False


def main():
    ok = True
    ok &= check_openai_key()
    ok &= check_mt5()
    ok &= check_csv_write()
    print("\n=== RÉSUMÉ ===")
    print("OK" if ok else "ERREURS détectées")
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
