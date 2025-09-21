#!/usr/bin/env python3
import os, sys, shlex, subprocess as sp
TARGET = r"/Users/ayoubzahour/FTMO_Bot/scripts/FTMO_GPT_Trader_MAIN.py"
ENTRY  = os.environ.get("ENTRY_HINT")
argv   = sys.argv[1:]
if ENTRY and "--entry" not in argv:
    try:
        i = argv.index("--sl")
    except ValueError:
        i = len(argv)
    argv[i:i] = ["--entry", str(ENTRY)]
cmd = [sys.executable, TARGET] + argv
open("logs/wrap_ping.log","a").write("\nWRAP "+" ".join(argv))
print("[WRAP]", " ".join(shlex.quote(a) for a in cmd))
sys.exit(sp.call(cmd, env=os.environ.copy()))
