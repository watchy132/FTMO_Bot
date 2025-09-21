from datetime import datetime
import argparse
p=argparse.ArgumentParser(); p.add_argument('--now'); args=p.parse_args()
now=datetime.fromisoformat(args.now) if args.now else datetime.now()
h=now.hour*60+now.minute
lon_on=8*60; lon_off=12*60    # 08:00-12:00 Africa/Casablanca
ny_on=13*60+30; ny_off=20*60  # 13:30-20:00
active=(lon_on<=h<lon_off) or (ny_on<=h<ny_off)
print('ACTIVE', active)
