import MetaTrader5 as mt5, numpy as np
from datetime import datetime
mt5.initialize()
r=mt5.copy_rates_from('EURUSD', mt5.TIMEFRAME_M5, datetime.now(), 500)
mt5.shutdown()
assert r is not None and len(r)>=200, 'not enough data'
h=r['high'].astype(float); l=r['low'].astype(float); c=r['close'].astype(float)
# ATR(14)
tr=np.maximum(h-l, np.maximum(abs(h-np.roll(c,1)), abs(l-np.roll(c,1))))
tr[0]=h[0]-l[0]
atr=np.empty_like(tr); n=14
atr[0]=tr[0]
for i in range(1,len(tr)):
    atr[i]=(atr[i-1]*(n-1)+tr[i])/n
# RSI(14)
delta=np.diff(c, prepend=c[0])
g=np.where(delta>0, delta, 0.0); l_ =np.where(delta<0, -delta, 0.0)
avg_g=np.zeros_like(g); avg_l=np.zeros_like(l_)
avg_g[0]=g[0]; avg_l[0]=l_[0]
for i in range(1,len(g)):
    avg_g[i]=(avg_g[i-1]*(n-1)+g[i])/n
    avg_l[i]=(avg_l[i-1]*(n-1)+l_[i])/n
rs=np.where(avg_l==0, np.inf, avg_g/avg_l)
rsi=100-(100/(1+rs))
print('ATR_M5_LAST', float(atr[-1]))
print('RSI_M5_LAST', float(rsi[-1]))
