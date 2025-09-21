import math, argparse
p=argparse.ArgumentParser()
p.add_argument('--equity', type=float, default=200000)
p.add_argument('--risk', type=float, default=0.01)
p.add_argument('--sl_pips', type=float, default=20)
p.add_argument('--tp_rr', type=float, default=2)
p.add_argument('--spread_pips', type=float, default=1.0)
p.add_argument('--commission_per_lot', type=float, default=7.0)
p.add_argument('--slippage_pips', type=float, default=0.2)
p.add_argument('--pip_value', type=float, default=10.0) # EURUSD 1 lot ≈ $10/pip
args=p.parse_args()
risk_usd=args.equity*args.risk
lot=risk_usd/(args.sl_pips*args.pip_value)
comm_pips=args.commission_per_lot/(args.pip_value*max(lot,1e-9))
sl_eff=args.sl_pips+args.slippage_pips
tp_pips=args.tp_rr*args.sl_pips
tp_eff=max(tp_pips-args.spread_pips-args.slippage_pips-comm_pips, 0.0)
rr_eff=(tp_eff/sl_eff) if sl_eff>0 else 0
print('LOT', round(lot,2))
print('RR_EFF', round(rr_eff,3))
