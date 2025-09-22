#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import os, sys, json, time, argparse
from typing import Any, Dict, List
from gpt_bridge import decide

# ENTRY_OS_WRAP
import os as _os, subprocess as _sp, shlex as _shlex, inspect as _inspect


def _caller_locals():
    f = _inspect.currentframe().f_back
    best = None
    for _ in range(40):
        if not f:
            break
        loc = f.f_locals if isinstance(f.f_locals, dict) else {}
        if loc and best is None:
            best = loc
        if "s" in loc or "setups" in loc:
            return loc
        f = f.f_back
    return best or {}


def _extract_symbol_from_tokens(tokens):
    try:
        for i, v in enumerate(tokens):
            if v == "--symbol" and i + 1 < len(tokens):
                return tokens[i + 1]
    except Exception:
        pass
    return None


def _find_entry(loc, symbol=None):
    def it(o):
        if isinstance(o, dict):
            yield o
            for v in o.values():
                yield from it(v)
        elif isinstance(o, (list, tuple, set)):
            for v in o:
                yield from it(v)

    sym = None if symbol is None else str(symbol).upper()
    found_any = None
    for d in it(loc):
        try:
            if d.get("entry") is not None:
                if found_any is None:
                    found_any = d["entry"]
                dsym = d.get("symbol")
                if sym is None or dsym is None or str(dsym).upper() == sym:
                    return d["entry"]
        except Exception:
            pass
    try:
        g = globals().get("_ENTRY")
        if g is not None:
            return g
    except Exception:
        pass
    return found_any  # dernier fallback: 1er entry trouvé sans match symbole


def _ensure_entry_tokens(tokens, loc):
    try:
        if not isinstance(tokens, list):
            print("[ENTRYDBG] tokens non-liste")
            return tokens
        if "--entry" in tokens:
            print("[ENTRYDBG] déjà présent")
            return tokens
        ts = globals().get("TRADER_SCRIPT")
        if (
            ts
            and ts not in tokens
            and all("FTMO_GPT_Trader_MAIN.py" not in str(x) for x in tokens)
        ):
            print("[ENTRYDBG] autre commande, ignore")
            return tokens
        sym = _extract_symbol_from_tokens(tokens)
        e = _find_entry(loc, sym)
        print(f"[ENTRYDBG] sym={sym} e={e} loc_keys={list(loc.keys())[:6]}")
        if e is None:
            return tokens
        try:
            i = tokens.index("--sl")
        except ValueError:
            i = len(tokens)
        tokens[i:i] = ["--entry", str(e)]
        print(f"[ENTRYDBG] inject -> --entry {e}")
    except Exception as ex:
        print("[ENTRYDBG] exception", ex)
    finally:
        return tokens


def _ensure_entry_in_cmd_str(cmd, loc):
    try:
        if not isinstance(cmd, str):
            return cmd
        if "FTMO_GPT_Trader_MAIN.py" not in cmd:
            ts = globals().get("TRADER_SCRIPT")
            if not ts or ts not in cmd:
                return cmd
        toks = _shlex.split(cmd)
        toks = _ensure_entry_tokens(toks, loc)
        return " ".join(_shlex.quote(t) for t in toks)
    except Exception:
        return cmd


def _entrywrap_run(*a, **kw):
    if a and isinstance(a[0], list):
        loc = _caller_locals()
        a = (_ensure_entry_tokens(list(a[0]), loc),) + a[1:]
        try:
            print("[EXEC]", " ".join(str(x) for x in a[0]))
        except Exception:
            pass
    return _ORIG_RUN(*a, **kw)


_ORIG_SYSTEM = _os.system


def _entrywrap_system(cmd):
    loc = _caller_locals()
    new = _ensure_entry_in_cmd_str(cmd, loc)
    try:
        print("[EXEC]", new)
    except Exception:
        pass
    return _ORIG_SYSTEM(new)


_sp.run = _entrywrap_run
_os.system = _entrywrap_system

# SUBPROCESS_ENTRY_WRAPPER
import subprocess as _sp, inspect as _inspect

_ORIG_RUN = _sp.run


def _caller_locals():
    f = _inspect.currentframe().f_back
    best = None
    for _ in range(40):
        if not f:
            break
        loc = f.f_locals if isinstance(f.f_locals, dict) else {}
        if loc and best is None:
            best = loc
        if "s" in loc or "setups" in loc:
            return loc
        f = f.f_back
    return best or {}


def _extract_symbol(args):
    try:
        for i, v in enumerate(args):
            if v == "--symbol" and i + 1 < len(args):
                return args[i + 1]
    except Exception:
        pass
    return None


def _find_entry(loc, symbol=None):
    def it(o):
        if isinstance(o, dict):
            yield o
            for v in o.values():
                yield from it(v)
        elif isinstance(o, (list, tuple, set)):
            for v in o:
                yield from it(v)

    sym = None if symbol is None else str(symbol).upper()
    found_any = None
    for d in it(loc):
        try:
            if d.get("entry") is not None:
                if found_any is None:
                    found_any = d["entry"]
                dsym = d.get("symbol")
                if sym is None or dsym is None or str(dsym).upper() == sym:
                    return d["entry"]
        except Exception:
            pass
    try:
        g = globals().get("_ENTRY")
        if g is not None:
            return g
    except Exception:
        pass
    return found_any  # dernier fallback: 1er entry trouvé sans match symbole


def _maybe_add_entry(args, loc):
    try:
        if not isinstance(args, list):
            return args
        if "--entry" in args:
            return args
        # touchez seulement l'appel qui exécute TRADER_SCRIPT
        try:
            ts = globals().get("TRADER_SCRIPT")
            if ts and ts not in args:
                return args
        except Exception:
            pass
        sym = _extract_symbol(args)
        e = _find_entry(loc, sym)
        if e is None:
            try:
                e = globals().get("_ENTRY") or globals().get("__ENTRY__")
            except Exception:
                e = None
        if e is None:
            return args
        try:
            idx = args.index("--sl")
        except ValueError:
            idx = len(args)
        args[idx:idx] = ["--entry", str(e)]
    finally:
        return args


def _patched_run(*a, **kw):
    if a and isinstance(a[0], list):
        loc = _caller_locals()
        new0 = _maybe_add_entry(list(a[0]), loc)
        a = (new0,) + a[1:]
        try:

            # ENTRY_BEFORE_EXEC
            try:
                _lv = locals()
                _args = _lv.get("argv") or _lv.get("cmd") or _lv.get("args")
                _sym = None
                if isinstance(_args, list):
                    for _i, _v in enumerate(_args):
                        if _v == "--symbol" and _i + 1 < len(_args):
                            _sym = _args[_i + 1]
                            break
                _entry = None
                for _name in ("s", "setup"):
                    _obj = _lv.get(_name)
                    if isinstance(_obj, dict) and _obj.get("entry") is not None:
                        if not _sym or _obj.get("symbol") in (None, _sym):
                            _entry = _obj["entry"]
                            break
                if _entry is None:
                    for _st in _lv.get("setups") or []:
                        if isinstance(_st, dict) and _st.get("entry") is not None:
                            if not _sym or _st.get("symbol") in (None, _sym):
                                _entry = _st["entry"]
                                break
                if _entry is None:
                    _entry = globals().get("_ENTRY")
                if (
                    isinstance(_args, list)
                    and _entry is not None
                    and "--entry" not in _args
                ):
                    try:
                        _idx = _args.index("--sl")
                    except ValueError:
                        _idx = len(_args)
                    _args[_idx:_idx] = ["--entry", str(_entry)]
            except Exception:
                pass
            # END ENTRY_BEFORE_EXEC
            print("[EXEC]", " ".join(str(x) for x in new0))
        except Exception:
            pass
    return _ORIG_RUN(*a, **kw)


_sp.run = _patched_run


TIMEOUT = float(os.getenv("BRIDGE_TIMEOUT", "60"))
PYWIN = os.getenv("PYWIN_BIN", "/Users/ayoubzahour/pywin")
ROOT = os.path.dirname(os.path.abspath(__file__))
TRADER_SCRIPT = os.path.join(ROOT, "scripts", "FTMO_GPT_Trader_MAIN.py")


def _print(x: Any) -> None:
    print(json.dumps(x, ensure_ascii=False, indent=2))


def _first(resp: Dict[str, Any]) -> Dict[str, Any]:
    ds = resp.get("decisions") or []
    return ds[0] if isinstance(ds, list) and ds else {}


def _run_trader(
    symbol: str,
    side: str,
    lots: float,
    sl: float | None,
    tp: float | None,
    dry: bool = False,
) -> int:
    # entry calculée depuis setups pour le symbole courant
    try:
        _entry_for_symbol = next(
            (
                st.get("entry")
                for st in (setups or [])
                if isinstance(st, dict)
                and (st.get("symbol") in (None, symbol))
                and st.get("entry") is not None
            ),
            None,
        )
    except Exception:
        _entry_for_symbol = None
    argv = [
        PYWIN,
        "-u",
        TRADER_SCRIPT,
        "--symbol",
        symbol,
        "--side",
        side,
        "--lots",
        f"{lots}",
        "--sl",
        f"{sl or 0}",
        "--tp",
        f"{tp or 0}",
    ]
    # ajouter --entry si disponible
    if _entry_for_symbol is not None and "--entry" not in argv:
        argv += ["--entry", str(_entry_for_symbol)]

    # --- ENTRY PATCH (auto) ---
    try:
        _lv = locals()
        _args = argv
        _sym = None
        for _i, _v in enumerate(_args):
            if _v == "--symbol" and _i + 1 < len(_args):
                _sym = _args[_i + 1]
                break
        _setups = _lv.get("setups") or []
        _e = None
        for _s in _setups:
            if not isinstance(_s, dict):
                continue
            if _sym and _s.get("symbol") and _s.get("symbol") != _sym:
                continue
            if _s.get("entry") is not None:
                _e = _s["entry"]
                break
        if _e is not None and "--entry" not in _args:
            argv += ["--entry", str(_e)]
    except Exception:
        pass
    # --- END ENTRY PATCH ---
    print("[EXEC]", " ".join(argv))
    if dry:
        return 0
    rc = os.spawnv(os.P_WAIT, PYWIN, argv)
    return int(rc)


def parse_args(a: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Runner FTMO bridge->MT5")
    p.add_argument("--symbol", required=True)
    p.add_argument("--minutes", type=int, default=5)
    p.add_argument("--max-trades", type=int, default=1)
    p.add_argument("--lots", type=float, default=0.01)
    p.add_argument("--sl", type=float, default=0.0)
    p.add_argument("--tp", type=float, default=0.0)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--debug-force", choices=["buy", "sell", "skip"], default=None)
    return p.parse_args(a)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    payload: Dict[str, Any] = {
        "symbols": [args.symbol],
        "window_minutes": int(args.minutes),
        "max_trades": int(args.max_trades),
    }
    dbg = args.debug_force or os.getenv("DEBUG_FORCE")
    if dbg in ("buy", "sell", "skip"):
        payload["debug_force"] = dbg

    print("[Bridge] payload:")
    _print(payload)
    t0 = time.time()
    resp = decide(payload, timeout=TIMEOUT)
    dt = int((time.time() - t0) * 1000)
    print(f"[Bridge] response ({dt} ms):")
    _print(resp)

    d = _first(resp)
    action = (d.get("action") or "skip").lower()
    reason = d.get("reason")

    # 🔹 Corrigé : chercher sl/tp dans setups
    sl = None
    tp = None
    setups = d.get("setups") or []
    if setups and isinstance(setups, list) and isinstance(setups[0], dict):
        sl = setups[0].get("sl")
        tp = setups[0].get("tp")
    else:
        sl = d.get("sl")
        tp = d.get("tp")

    if action not in ("buy", "sell"):
        print(f"[Runner] action={action.upper()} -> aucun ordre. reason={reason}")
        return 0

    print(
        f"[Runner] PLACE {action.upper()} {args.symbol} lots={args.lots} sl={sl or args.sl} tp={tp or args.tp}"
    )

    # ENTRY_GLOBAL_AFTER_PLACE
    try:
        _lv = locals()
        _entry = None
        if (
            "s" in _lv
            and isinstance(_lv["s"], dict)
            and _lv["s"].get("entry") is not None
        ):
            _entry = _lv["s"]["entry"]
        if _entry is None:
            for _st in _lv.get("setups") or []:
                if isinstance(_st, dict) and _st.get("entry") is not None:
                    _entry = _st["entry"]
                    break
        globals()["_ENTRY"] = _entry
    except Exception:
        pass
    # END ENTRY_GLOBAL_AFTER_PLACE

    # ENTRY_PATCH_AFTER_PLACE
    try:
        _lv = locals()
        _entry = None
        # cas 1: setup courant 's'
        if "s" in _lv and isinstance(_lv["s"], dict):
            _entry = _lv["s"].get("entry")
        # cas 2: chercher dans 'setups' si non trouvé
        if _entry is None:
            for _st in _lv.get("setups") or []:
                if isinstance(_st, dict) and _st.get("entry") is not None:
                    _entry = _st["entry"]
                    break
        # ajouter --entry à la première liste d'args trouvée
        if _entry is not None:
            for _name in ("argv", "cmd", "args"):
                _lst = _lv.get(_name)
                if isinstance(_lst, list) and "--entry" not in _lst:
                    _lst += ["--entry", str(_entry)]
                    break
    except Exception:
        pass
    # END_ENTRY_PATCH_AFTER_PLACE
    rc = _run_trader(
        args.symbol,
        action,
        float(args.lots),
        float(sl or args.sl or 0.0),
        float(tp or args.tp or 0.0),
        bool(args.dry_run),
    )
    print(f"[Runner] trader exit={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
