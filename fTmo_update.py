# -*- coding: utf-8 -*-

"""
FTMO_GPT_Trader_S2.py  —  Version corrigée (Wine + OpenAI v1)

- Charge .env (OPENAI_API_KEY, OPENAI_MODEL)
- Initialise client OpenAI de façon robuste
- Prépare un snapshot marché (mock minimal si MT5 indispo)
- Envoie le snapshot à GPT (json_only) et log la réponse
- Fallback local si GPT KO
- Inclut un test direct sous __main__ pour vérifier l’aller-retour

Prérequis côté shell (dans chaque nouveau terminal macOS) :
  export OPENAI_API_KEY=$(grep OPENAI_API_KEY .env | cut -d '=' -f2)
  export OPENAI_MODEL=gpt-4.1-mini
Ou laisse VS Code/Tasks fournir les variables via tasks.json (options.env).

Exécution sous Wine (pywin est ton wrapper Wine→python.exe) :
  /Users/ayoubzahour/pywin FTMO_GPT_Trader_S2.py
"""

import os
import json
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

# ===================== ENV =====================

load_dotenv()  # charge .env s’il existe

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

print("ENV: OPENAI_API_KEY set?:", bool(OPENAI_KEY))
print("ENV: OPENAI_MODEL:", OPENAI_MODEL)

# ===================== OpenAI client =====================

USE_GPT = True
client = None
try:
    from openai import OpenAI

    if not OPENAI_KEY:
        raise RuntimeError("OPENAI_API_KEY manquante")
    client = OpenAI(api_key=OPENAI_KEY)

    # ping rapide (liste des modèles)
    _ = client.models.list()
except Exception as e:
    print("GPT désactivé:", e)
    USE_GPT = False

# ===================== Schéma & prompt =====================

SCHEMA = {
    "type": "object",
    "properties": {
        "meta": {
            "type": "object",
            "properties": {
                "session_ok": {"type": "boolean"},
                "notes": {"type": "string"},
            },
            "required": ["session_ok"],
        },
        "setups": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "setup_id": {"type": "string"},
                    "side": {"type": "string", "enum": ["buy", "sell"]},
                    "entry_type": {
                        "type": "string",
                        "enum": ["market", "limit", "stop"],
                    },
                    "entry": {"type": "number"},
                    "sl": {"type": "number"},
                    "tp": {"type": "number"},
                    "risk_pct_hint": {"type": "number"},
                    "rr_net_est": {"type": "number"},
                    "confluence_index": {"type": "number"},
                    "confidence_score": {"type": "number"},
                    "comment": {"type": "string"},
                },
                "required": ["symbol", "side", "sl", "tp"],
            },
        },
    },
    "required": ["meta", "setups"],
}

SYSTEM_PROMPT = (
    "Tu es un assistant de trading. Tu reçois un snapshot marché (quotes, spreads, "
    "contexte minimal) et tu proposes des setups simples et mesurables. "
    "Respecte STRICTEMENT le schéma JSON fourni. Ne renvoie QUE du JSON."
)

# ===================== MT5 utils (gracieux si absent) =====================


def _try_import_mt5():
    try:
        import MetaTrader5 as mt5

        return mt5
    except Exception:
        return None


def init_mt5():
    """Init MT5 si dispo. Renvoie True/False."""
    mt5 = _try_import_mt5()
    if not mt5:
        print("MT5 non disponible (module introuvable).")
        return False
    try:
        if not mt5.initialize():
            print("Échec init MT5:", mt5.last_error())
            return False
        print("MT5 initialisé.")
        return True
    except Exception as e:
        print("Erreur init MT5:", e)
        return False


def shutdown_mt5():
    mt5 = _try_import_mt5()
    if mt5:
        try:
            mt5.shutdown()
        except Exception:
            pass


def symbol_spread_pips(symbol: str) -> float:
    """Spread estimé en pips (fallback à 0.0 si MT5 hors service)."""
    mt5 = _try_import_mt5()
    try:
        if mt5:
            tick = mt5.symbol_info_tick(symbol)
            info = mt5.symbol_info(symbol)
            if tick and info:
                # pips = (ask-bid)/point / 10 si 5 digits, ajuste si besoin
                raw = (tick.ask - tick.bid) / info.point
                return float(raw / 10.0 if info.digits in (3, 5) else raw)
    except Exception:
        pass
    return 0.0


# ===================== Snapshot marché =====================


def snapshot_market(symbols):
    """
    Prépare un snapshot minimal pour GPT. Si MT5 indispo, renvoie un mock simple.
    """
    data = {}
    mt5 = _try_import_mt5()
    if not mt5:
        # mock de secours
        for s in symbols:
            data[s] = {"bid": None, "ask": None, "spread_pips": 0.0}
        return data

    for s in symbols:
        try:
            info = mt5.symbol_info(s)
            tick = mt5.symbol_info_tick(s)
            sp = symbol_spread_pips(s)
            data[s] = {
                "digits": info.digits if info else None,
                "point": info.point if info else None,
                "bid": getattr(tick, "bid", None),
                "ask": getattr(tick, "ask", None),
                "spread_pips": sp,
            }
        except Exception as e:
            data[s] = {"error": str(e)}
    return data


# ===================== Appel GPT =====================


def call_gpt_analysis(
    market_snapshot: dict, equity: float, dd_day: float, dd_total: float
) -> dict:
    """
    Envoie le snapshot à GPT. Retourne un dict conforme au SCHEMA.
    Fallback local si USE_GPT=False ou erreur appel.
    """
    # Prépare un prompt utilisateur concis
    user_prompt = {
        "instructions": {
            "require_json_only": True,
            "schema": SCHEMA,
            "account": {"equity": equity, "dd_day": dd_day, "dd_total": dd_total},
        },
        "market": market_snapshot,
    }

    print("GPT model:", OPENAI_MODEL)
    print(">>> Données envoyées à GPT:", (json.dumps(user_prompt)[:500]))

    if not USE_GPT:
        print(">>> GPT OFF, activation du fallback local.")
        return {
            "meta": {"session_ok": True, "notes": "fallback local"},
            "setups": [],
        }

    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0.1,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_prompt)},
            ],
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
        print(">>> Réponse GPT:", content[:500])
        return json.loads(content)
    except Exception as e:
        print("Erreur appel GPT:", e)
        # Fallback très conservateur
        return {
            "meta": {"session_ok": True, "notes": f"fallback après erreur GPT: {e}"},
            "setups": [],
        }


# ===================== Sessions & boucle =====================


def in_session_utc() -> bool:
    """Session Londres/NY simple: 07:00–23:00 UTC."""
    now = datetime.now(timezone.utc).time()
    return 7 <= now.hour < 23


def run_trading_cycle(symbols):
    """
    Exemple minimal d’un cycle:
    - snapshot
    - appel GPT
    - log setups
    """
    equity = 10_000.0
    dd_day = 0.0
    dd_total = 0.0

    snap = snapshot_market(symbols)
    decision = call_gpt_analysis(snap, equity, dd_day, dd_total)

    setups = decision.get("setups", [])
    print(f"Setups GPT reçus: {len(setups)}")
    for s in setups[:3]:
        print("  •", s)


def run_scheduler():
    symbols = ["EURUSD", "XAUUSD", "BTCUSD"]  # adapte si besoin

    ok = init_mt5()
    print("init_mt5():", ok)

    try:
        while True:
            if not in_session_utc():
                # hors session, on attend
                time.sleep(15)
                continue

            try:
                run_trading_cycle(symbols)
            except Exception as e:
                print("Erreur cycle:", e)

            # cadence légère
            time.sleep(10)

    finally:
        shutdown_mt5()


# ===================== Test direct =====================

if __name__ == "__main__":
    print("BOOT FTMO_GPT_Trader_S2", datetime.now())
    print("ENV OK? KEY:", bool(OPENAI_KEY), "MODEL:", OPENAI_MODEL)

    # Test d’appel GPT direct, sans MT5, pour vérifier l’aller-retour:
    test_snapshot = {
        "EURUSD": {"bid": 1.0850, "ask": 1.0852, "spread_pips": 0.2},
        "XAUUSD": {"bid": 1920.5, "ask": 1920.8, "spread_pips": 0.3},
    }
    test_decision = call_gpt_analysis(test_snapshot, equity=10000, dd_day=0, dd_total=0)
    print("=== Décision (test) ===")
    print(json.dumps(test_decision, indent=2))

    # Décommente pour lancer la boucle réelle (sessions, MT5, etc.)
    # run_scheduler()
