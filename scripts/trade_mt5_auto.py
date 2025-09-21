# -*- coding: utf-8 -*-
from trade_mts_auto import parse, send_order
if __name__=="__main__":
    import sys
    try:
        send_order(parse())
    except Exception as e:
        print(f"ERR {e}")
        sys.exit(1)
