#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 18 12:11:27 2022

@author: josevans
"""

import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import websocket
import json
import collections

@st.cache(ttl=2592000)
def get_instruments():
    st.write('Getting Instrument Data')
    ws = websocket.create_connection('wss://www.deribit.com/ws/api/v2/public/subscribe')
    

    expiries = []
    eth_strikes = []
    btc_strikes = []
    btc_instruments = []
    eth_instruments = []
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
        btc_instruments.append(d['instrument_name'])
    
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
        eth_instruments.append(d['instrument_name'])
    
    timestamps = expiries
    expiries = [datetime.fromtimestamp(x).strftime('%d%b%y').upper() for x in expiries]
    eth_strikes_exp = {datetime.fromtimestamp(x).strftime('%d%b%y').upper():v for x, v in eth_strikes_exp.items()}
    btc_strikes_exp = {datetime.fromtimestamp(x).strftime('%d%b%y').upper():v for x, v in btc_strikes_exp.items()}
    ES = list(set(eth_strikes))
    BS = list(set(btc_strikes))
    
    times_dic = dict(zip(expiries, timestamps))
    
    
    st.write('Finished Getting Instrument Data')
    return ES, BS, expiries, eth_strikes_exp, btc_strikes_exp, times_dic, btc_instruments, eth_instruments

ES, BS, xs, eth_strikes_per, btc_strikes_per, times_dic, btc_instruments, eth_instruments = get_instruments()

def get_prices(btc_instruments, eth_instruments):
    
    print(datetime.now())
    
    eth_calls=pd.DataFrame(columns=xs, index=ES, data=0).sort_index()
    eth_puts=pd.DataFrame(columns=xs, index=ES, data=0).sort_index()
    btc_calls =pd.DataFrame(columns=xs, index=BS, data=0).sort_index()
    btc_puts =pd.DataFrame(columns=xs, index=BS, data=0).sort_index()
    
    ws = websocket.create_connection('wss://www.deribit.com/ws/api/v2/public/subscribe')
    count=0
    for ins in btc_instruments + eth_instruments:
        count+=1
        if count%50==0:
            print(count)
            ws = websocket.create_connection('wss://www.deribit.com/ws/api/v2/public/subscribe')
        print(ins)

        ticker = ins.split('-')[0]
        exp = ins.split('-')[1]
        strike = int(ins.split('-')[2])
        option = ins.split('-')[3]
        
        msg = \
            {
          "jsonrpc" : "2.0",
          "id" : 8106,
          "method" : "public/ticker",
          "params" : {
            "instrument_name" : ins
          }
        }
        
        ws.send(json.dumps(msg))
        try:
            result = ws.recv()
        except Exception as e:
            print(e)
        
        prices = pd.read_json(result)
        
        mark = prices.loc['mark_iv']['result']
        underlying = prices.loc['underlying_price']['result']
        
        if ticker == 'BTC':
            if option == 'P':
                btc_puts.loc[btc_puts.index == strike, exp] = [{'mark':mark, 'underlying':underlying}]
            else:
                btc_calls.loc[btc_calls.index == strike, exp] = [{'mark':mark, 'underlying':underlying}]
        else:
            if option == 'P':
                eth_puts.loc[eth_puts.index == strike, exp] = [{'mark':mark, 'underlying':underlying}]
            else:
                eth_calls.loc[eth_calls.index == strike, exp] = [{'mark':mark, 'underlying':underlying}]
                
    print(datetime.now())    
    
    eth_calls.to_csv('eth_calls.csv')
    eth_puts.to_csv('eth_puts.csv')
    btc_calls.to_csv('btc_calls.csv')
    btc_puts.to_csv('btc_puts.csv')
    
    st.write(eth_calls)
    return eth_calls, eth_puts, btc_calls, btc_puts

eth_calls, eth_puts, btc_calls, btc_puts = get_prices(btc_instruments, eth_instruments)
