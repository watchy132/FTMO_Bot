#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import os, sys, json, time, argparse
from typing import Any, Dict, List
from gpt_bridge import decide
# ENTRY_ALL_SUBPROC_WRAP
import subprocess as _sp, subprocess as subprocess, inspect as _inspect, shlex as _shlex, os as _os

def _caller_locals():
    f=_inspect.currentframe().f_back
    for _ in range(40):
        if not f: break
        if isinstance(f.f_locals, dict): return f.f_locals
        f=f.f_back
    return {}

def _iterdeep(o):
    if isinstance(o, dict):
        yield o
        for v in o.values(): yield from _iterdeep(v)
    elif isinstance(o, (list,tuple,set)):
        for v in o: yield from _iterdeep(v)

def _extract_symbol(tokens):
    try:
        for i,v in enumerate(tokens):
            if v == "--symbol" and i+1 < len(tokens): return tokens[i+1]
    except Exception: pass
    return None

def _find_entry_from_locals(loc, symbol=None):
    sym=None if symbol is None else str(symbol).upper()
    for d in _iterdeep(loc):
        try:
            if d.get("entry") is not None:
                ds=d.get("symbol")
                if sym is None or ds is None or str(ds).upper()==sym:
                    return d["entry"]
        except Exception: pass
    try:
        g=globals().get("_ENTRY") or globals().get("__ENTRY__")
        if g is not None: return g
    except Exception: pass
    return None

def _is_trader_cmd_tokens(tokens):
    ts=globals().get("TRADER_SCRIPT")
    return any(("FTMO_GPT_Trader_MAIN.py" in str(t)) or (ts and str(t)==str(ts)) for t in tokens)

def _ensure_entry_list(tokens, loc):
    if not isinstance(tokens, list): return tokens
    if "--entry" in tokens: return tokens
    if not _is_trader_cmd_tokens(tokens): return tokens
    e=_find_entry_from_locals(loc, _extract_symbol(tokens))
    if e is None: return tokens
    try: i=tokens.index("--sl")
    except ValueError: i=len(tokens)
    tokens[i:i]=["--entry", str(e)]
    return tokens

def _ensure_entry_str(cmd, loc):
    if not isinstance(cmd, str): return cmd
    ts=globals().get("TRADER_SCRIPT")
    if ("FTMO_GPT_Trader_MAIN.py" not in cmd) and (not ts or str(ts) not in cmd): return cmd
    toks=_shlex.split(cmd)
    toks=_ensure_entry_list(toks, loc)
    return " ".join(_shlex.quote(t) for t in toks)

def _patch_cmd_args(a, kw):
    loc=_caller_locals()
    if a and isinstance(a[0], list):
        new0=_ensure_entry_list(list(a[0]), loc)
        try: print("[EXEC]", " ".join(str(x) for x in new0))
        except Exception: pass
        return (new0,)+a[1:], kw
    if a and isinstance(a[0], str):
        new0=_ensure_entry_str(a[0], loc)
        try: print("[EXEC]", new0)
        except Exception: pass
        return (new0,)+a[1:], kw
    if "args" in kw:
        if isinstance(kw["args"], list):
            kw["args"]=_ensure_entry_list(list(kw["args"]), loc)
            try: print("[EXEC]", " ".join(str(x) for x in kw["args"]))
            except Exception: pass
        elif isinstance(kw["args"], str):
            kw["args"]=_ensure_entry_str(kw["args"], loc)
            try: print("[EXEC]", kw["args"])
            except Exception: pass
    return a, kw

_ORIG_RUN=_sp.run
_ORIG_CALL=_sp.call
_ORIG_POPEN=_sp.Popen
_ORIG_OS_SYSTEM=_os.system

def _wrap_run(*a, **kw):
    a,kw=_patch_cmd_args(a,kw); return _ORIG_RUN(*a, **kw)
def _wrap_call(*a, **kw):
    a,kw=_patch_cmd_args(a,kw); return _ORIG_CALL(*a, **kw)
def _wrap_popen(*a, **kw):
    a,kw=_patch_cmd_args(a,kw); return _ORIG_POPEN(*a, **kw)
def _wrap_system(cmd):
    new=_ensure_entry_str(cmd, _caller_locals())
    try: print("[EXEC]", new)
    except Exception: pass
    return _ORIG_OS_SYSTEM(new)

_sp.run=_wrap_run; subprocess.run=_wrap_run
_sp.call=_wrap_call; subprocess.call=_wrap_call
_sp.Popen=_wrap_popen; subprocess.Popen=_wrap_popen
_os.system=_wrap_system

# ENTRY_OS_WRAP
import os as _os, subprocess as _sp, shlex as _shlex, inspect as _inspect

def _caller_locals():
    f=_inspect.currentframe().f_back
    best=None
    for _ in range(40):
        if not f: break
        loc=f.f_locals if isinstance(f.f_locals,dict) else {}
        if loc and best is None: best=loc
        if 's' in loc or 'setups' in loc: return loc
        f=f.f_back
    return best or {}

def _extract_symbol_from_tokens(tokens):
    try:
        for i,v in enumerate(tokens):
            if v == "--symbol" and i+1 < len(tokens):
                return tokens[i+1]
    except Exception:
        pass
    return None

def _find_entry(loc, symbol=None):
    def it(o):
        if isinstance(o, dict):
            yield o
            for v in o.values(): yield from it(v)
        elif isinstance(o, (list,tuple,set)):
            for v in o: yield from it(v)
    sym = None if symbol is None else str(symbol).upper()
    found_any=None
    for d in it(loc):
        try:
            if d.get('entry') is not None:
                if found_any is None: found_any=d['entry']
                dsym=d.get('symbol')
                if sym is None or dsym is None or str(dsym).upper()==sym:
                    return d['entry']
        except Exception:
            pass
    try:
        g=globals().get('_ENTRY')
        if g is not None: return g
    except Exception:
        pass
    return found_any  # dernier fallback: 1er entry trouvé sans match symbole

def _ensure_entry_tokens(tokens, loc):
    try:
        if not isinstance(tokens, list):
            print("[ENTRYDBG] tokens non-liste"); return tokens
        if "--entry" in tokens:
            print("[ENTRYDBG] déjà présent"); return tokens
        ts = globals().get("TRADER_SCRIPT")
        if ts and ts not in tokens and all("FTMO_GPT_Trader_MAIN.py" not in str(x) for x in tokens):
            print("[ENTRYDBG] autre commande, ignore"); return tokens
        sym=_extract_symbol_from_tokens(tokens)
        e=_find_entry(loc, sym)
        print(f"[ENTRYDBG] sym={sym} e={e} loc_keys={list(loc.keys())[:6]}")
        if e is None: return tokens
        try:
            i=tokens.index("--sl")
        except ValueError:
            i=len(tokens)
        tokens[i:i]=["--entry", str(e)]
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
        loc=_caller_locals()
        a=( _ensure_entry_tokens(list(a[0]), loc), )+a[1:]
        try: print("[EXEC]", " ".join(str(x) for x in a[0]))
        except Exception: pass
    return _ORIG_RUN(*a, **kw)

_ORIG_SYSTEM=_os.system
def _entrywrap_system(cmd):
    loc=_caller_locals()
    new=_ensure_entry_in_cmd_str(cmd, loc)
    try: print("[EXEC]", new)
    except Exception: pass
    return _ORIG_SYSTEM(new)

_sp.run=_entrywrap_run
_os.system=_entrywrap_system

