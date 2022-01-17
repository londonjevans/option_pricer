#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 17 12:02:52 2022

@author: josevans
"""
import pandas as pd
import streamlit as st
import time 
import numpy as np
import requests
import matplotlib.pyplot as plt
from math import log, sqrt, pi, exp
from scipy.stats import norm
from datetime import datetime, date, timedelta
from pandas import DataFrame
import seaborn as sns
import websocket
import json
import collections

def get_cbs(asset):
    now = datetime.now()
    ticker = asset+'-USD'
    start = str(now.date()-timedelta(days=1))
    gran = 60 # in seconds, {60, 300, 900, 3600, 21600, 86400} , 1 second --> 1 day
    r = f"https://api.pro.coinbase.com/products/{ticker}/candles?start={start}T00:00:00&granularity={gran}"
    j = requests.get(r).json()

    df = pd.DataFrame(j)
    price = df.iloc[0, 4]
    return price

eth = get_cbs('ETH')
btc = get_cbs('BTC')


def get_instruments():
    
    ws = websocket.create_connection('wss://www.deribit.com/ws/api/v2/public/subscribe')
    

    expiries = []
    eth_strikes = []
    btc_strikes = []
    btc_strikes_exp = collections.defaultdict(list)
    eth_strikes_exp = collections.defaultdict(list)
    
    msg = \
        {
  "jsonrpc" : "2.0",
  "id" : 7617,
  "method" : "public/get_instruments",
  "params" : {
      
    "currency" : "BTC",
    "kind" : "option",
    "expired" : False
    }
      }
    
    ws.send(json.dumps(msg))
    try:
        result = ws.recv()
    except Exception as e:
        print(e)
    
    data = pd.read_json(result).reset_index()
    
    for d in data.result:
        btc_strikes_exp[d['expiration_timestamp']/1000].append(int(d['strike']))
        btc_strikes.append(int(d['strike']))
        expiries.append(d['expiration_timestamp']/1000)
    
    expiries = list(dict.fromkeys(expiries))
    expiries = [n for n in expiries]
    
    
    
    msg = \
        {
  "jsonrpc" : "2.0",
  "id" : 7617,
  "method" : "public/get_instruments",
  "params" : {
    "currency" : "ETH",
    "kind" : "option",
    "expired" : False
    }
      }
    
    ws.send(json.dumps(msg))
    try:
        result = ws.recv()
    except Exception as e:
        print(e)
    
    data = pd.read_json(result).reset_index()
    
    for d in data.result:
        eth_strikes_exp[d['expiration_timestamp']/1000].append(int(d['strike']))
        eth_strikes.append(int(d['strike']))
    
    expiries = [datetime.fromtimestamp(x).strftime('%d%b%y').upper() for x in expiries]
    eth_strikes_exp = {datetime.fromtimestamp(x).strftime('%d%b%y').upper():v for x, v in eth_strikes_exp.items()}
    btc_strikes_exp = {datetime.fromtimestamp(x).strftime('%d%b%y').upper():v for x, v in btc_strikes_exp.items()}
    ES = list(set(eth_strikes))
    BS = list(set(btc_strikes))
    
    return ES, BS, expiries, eth_strikes_exp, btc_strikes_exp

ES, BS, xs, eth_strikes_per, btc_strikes_per = get_instruments()

eth_calls=pd.DataFrame(columns=xs, index=ES).sort_index()
eth_puts=pd.DataFrame(columns=xs, index=ES).sort_index()
btc_calls =pd.DataFrame(columns=xs, index=BS).sort_index()
btc_puts =pd.DataFrame(columns=xs, index=BS).sort_index()

def get_data():
    
    try:
        ws = websocket.create_connection('wss://www.deribit.com/ws/api/v2/public/subscribe', timeout=5)
    except Exception as e:
        print(e)
        time.sleep(5)
    
    msg = \
    {
      "jsonrpc" : "2.0",
      "id" : 9344,
      "method" : "public/get_book_summary_by_currency",
      "params" : {
        "currency" : "BTC",
        "kind" : "option"
      }
    }
    
    ws.send(json.dumps(msg))

    
    try:
        result = ws.recv()
        time.sleep(0.5)
        result = ws.recv()
        time.sleep(0.5)
        result = ws.recv()
    except Exception as e:
        print(e)
        
    btc_data = pd.read_json(result)

    msg = \
    {
      "jsonrpc" : "2.0",
      "id" : 9344,
      "method" : "public/get_book_summary_by_currency",
      "params" : {
        "currency" : "ETH",
        "kind" : "option"
      }
    }
    
    ws.send(json.dumps(msg))

    
    try:
        result = ws.recv()
        time.sleep(0.5)
        result = ws.recv()
        time.sleep(0.5)
        result = ws.recv()
    except Exception as e:
        print(e)
        
    eth_data = pd.read_json(result)
    
    return eth_data, btc_data

eth_data, btc_data = get_data()

def parse_data(df):
    
    for i in range(len(df)):
        
        ticker = df.iloc[i].result['instrument_name'].split('-')[0]
        exp = df.iloc[i].result['instrument_name'].split('-')[1]
        if len(exp) == 6:
            exp = '0'+exp
        strk = pd.to_numeric(df.iloc[i].result['instrument_name'].split('-')[2])
        option = df.iloc[i].result['instrument_name'].split('-')[3]
        
        if ticker == 'BTC':
            if option == 'P':
                btc_puts.loc[btc_puts.index==strk, exp] = round(df.iloc[i].result['mark_price']*btc, 2)
            else:
                btc_calls.loc[btc_calls.index==strk, exp] = round(df.iloc[i].result['mark_price']*btc, 2)
        else:
            if option == 'P':
                eth_puts.loc[eth_puts.index==strk, exp] = round(df.iloc[i].result['mark_price']*eth, 2)
            else:
                eth_calls.loc[eth_calls.index==strk, exp] = round(df.iloc[i].result['mark_price']*eth, 2)
                
    return btc_puts, btc_calls, eth_calls, eth_puts

for df in [btc_data, eth_data]:
    parse_data(df)
    

eth_puts.to_csv('/Users/josevans/Downloads/option_pricer/option_pricer/eth_puts.csv')
eth_calls.to_csv('/Users/josevans/Downloads/option_pricer/option_pricer/eth_calls.csv')
btc_puts.to_csv('/Users/josevans/Downloads/option_pricer/option_pricer/btc_puts.csv')
btc_calls.to_csv('/Users/josevans/Downloads/option_pricer/option_pricer/btc_calls.csv')
                
# def mid_vols():
    
#     for strike in BS:
#         try:
#             ws = websocket.create_connection('wss://www.deribit.com/ws/api/v2/public/subscribe', timeout=5)
#         except Exception as e:
#             print(e)
#             time.sleep(5)

#         for ex in xs:
#             if strike in btc_strikes_per[ex]:
#                 print(strike)
#                 vol_df = pd.DataFrame()
                
        
        
#                 msg = \
#             {"jsonrpc": "2.0",
#              "method": "public/subscribe",
#              "id": 2,
#              "params": {
#                 "channels": ["ticker.BTC-{}-{}-P.100ms".format(ex, strike)]}
#             }
        
#                 ws.send(json.dumps(msg))
        
                
#                 try:
#                     result = ws.recv()
#                     time.sleep(0.5)
#                     result = ws.recv()
#                     time.sleep(0.5)
#                     result = ws.recv()
                    
#                     vol_df = pd.read_json(result).reset_index()
#                 except Exception as e:
#                     print(e)
#                 if len(vol_df) > 1:            
#                     btc_puts.loc[btc_puts.index==strike, ex] = pd.to_numeric(vol_df.iloc[1].params['mark_price'])*btc
#                 else:
#                     continue

#     for strike in BS:
#         try:
#             ws = websocket.create_connection('wss://www.deribit.com/ws/api/v2/public/subscribe', timeout=5)
#         except Exception as e:
#             print(e)
#             time.sleep(5)

#         for ex in xs:
#             if strike in btc_strikes_per[ex]:
#                 print(strike)
#                 vol_df = pd.DataFrame()
                
        
        
#                 msg = \
#             {"jsonrpc": "2.0",
#              "method": "public/subscribe",
#              "id": 2,
#              "params": {
#                 "channels": ["ticker.BTC-{}-{}-C.100ms".format(ex, strike)]}
#             }
        
#                 ws.send(json.dumps(msg))
        
                
#                 try:
#                     result = ws.recv()
#                     time.sleep(0.5)
#                     result = ws.recv()
#                     time.sleep(0.5)
#                     result = ws.recv()
                    
#                     vol_df = pd.read_json(result).reset_index()
#                 except Exception as e:
#                     print(e)
#                 if len(vol_df) > 1:            
#                     btc_calls.loc[btc_calls.index==strike, ex] = pd.to_numeric(vol_df.iloc[1].params['mark_price'])*btc
#                 else:
#                     continue     
                
#     for strike in ES:
#         try:
#             ws = websocket.create_connection('wss://www.deribit.com/ws/api/v2/public/subscribe', timeout=5)
#         except Exception as e:
#             print(e)
#             time.sleep(5)

#         for ex in xs:
#             if strike in eth_strikes_per[ex]:
#                 print(strike)
#                 vol_df = pd.DataFrame()
                
        
        
#                 msg = \
#             {"jsonrpc": "2.0",
#              "method": "public/subscribe",
#              "id": 2,
#              "params": {
#                 "channels": ["ticker.ETH-{}-{}-P.100ms".format(ex, strike)]}
#             }
        
#                 ws.send(json.dumps(msg))
        
                
#                 try:
#                     result = ws.recv()
#                     time.sleep(0.5)
#                     result = ws.recv()
#                     time.sleep(0.5)
#                     result = ws.recv()
                    
#                     vol_df = pd.read_json(result).reset_index()
#                 except Exception as e:
#                     print(e)
#                 if len(vol_df) > 1:            
#                     eth_puts.loc[eth_puts.index==strike, ex] = pd.to_numeric(vol_df.iloc[1].params['mark_price'])*eth
#                 else:
#                     continue 
                
#     for strike in ES:
#         try:
#             ws = websocket.create_connection('wss://www.deribit.com/ws/api/v2/public/subscribe', timeout=5)
#         except Exception as e:
#             print(e)
#             time.sleep(5)

#         for ex in xs:
#             if strike in eth_strikes_per[ex]:
#                 print(strike)
#                 vol_df = pd.DataFrame()
                
        
        
#                 msg = \
#             {"jsonrpc": "2.0",
#              "method": "public/subscribe",
#              "id": 2,
#              "params": {
#                 "channels": ["ticker.ETH-{}-{}-C.100ms".format(ex, strike)]}
#             }
        
#                 ws.send(json.dumps(msg))
        
                
#                 try:
#                     result = ws.recv()
#                     time.sleep(0.5)
#                     result = ws.recv()
#                     time.sleep(0.5)
#                     result = ws.recv()
                    
#                     vol_df = pd.read_json(result).reset_index()
#                 except Exception as e:
#                     print(e)
#                 if len(vol_df) > 1:            
#                     eth_calls.loc[eth_calls.index==strike, ex] = pd.to_numeric(vol_df.iloc[1].params['mark_price'])*eth
#                 else:
#                     continue   
                
#     return btc_calls, btc_puts, eth_calls, eth_puts

# btc_calls, btc_puts, eth_calls, eth_puts = mid_vols()

# columns = ['25MAR22', '24JUN22', '30SEP22', '30DEC22']

# print('Spot Reference Price BTC: ${:,}'.format(btc))
# for column in columns:
    
#     for i in range(len(btc_calls)):
#         if np.isnan(btc_calls[column].iloc[i]):
#             continue
#         else:
#             print('BTC {} calls for {} expiry are ${}/${}'.format(btc_calls.index[i], column, round(btc_calls.iloc[i][column]*.99, 2), round(btc_calls.iloc[i][column]*1.01, 2)))

# for column in columns:
#     for i in range(len(btc_puts)):
#         if np.isnan(btc_puts.iloc[i][column]):
#             continue
#         else:
#             print('BTC {} puts for {} expiry are ${}/${}'.format(btc_puts.index[i], column, round(btc_puts.iloc[i][column]*.99, 2), round(btc_puts.iloc[i][column]*1.01, 2)))
            
# print('Spot Reference Price ETH: ${:,}'.format(eth))            
# for column in columns:
    
#     for i in range(len(eth_calls)):
#         if np.isnan(eth_calls[column].iloc[i]):
#             continue
#         else:
#             print('ETH {} calls for {} expiry are ${}/${}'.format(eth_calls.index[i], column, round(eth_calls.iloc[i][column]*.99, 2), round(eth_calls.iloc[i][column]*1.01, 2)))

# for column in columns:
#     for i in range(len(eth_puts)):
#         if np.isnan(eth_puts.iloc[i][column]):
#             continue
#         else:
#             print('ETH {} puts for {} expiry are ${}/${}'.format(eth_puts.index[i], column, round(eth_puts.iloc[i][column]*.99, 2), round(eth_puts.iloc[i][column]*1.01, 2)))
