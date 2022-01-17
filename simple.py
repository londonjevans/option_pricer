#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 11 13:13:51 2022

@author: josevans
"""

import streamlit as st
import json
import websocket
import time
import pandas as pd
import ast
import datetime

strikes = []
expiries = []


asset = st.selectbox(label='Select Asset', options=['BTC', 'ETH'])
expiry = st.text_input('Expiry', value='28JAN22')
strike = st.text_input('Strike', value='45000')
option = st.selectbox(label='Call/Put', options=['C', 'P'])

def get_futs():
    
    
    ws = websocket.create_connection('wss://www.deribit.com/ws/api/v2/public/subscribe')
    
    msg = \
    {
      "jsonrpc" : "2.0",
      "id" : 9344,
      "method" : "public/get_book_summary_by_currency",
      "params" : {
        "currency" : "BTC",
        "kind" : "future"
      }
    }
    
        
    
        
    ws.send(json.dumps(msg))
    
    futures_result = json.loads(ws.recv())
        
    futs_data = pd.DataFrame(futures_result['result'])[['instrument_name', 'mid_price']]
    
    futs_data['timestamp_of_exp'] = 0
    futs_data['annualised_yield'] = 0
    
    pairs = {x:[datetime.fromtimestamp(x).strftime('%d%b%y').upper()] for x in expiries}
    
    for k, v in pairs.items():
        for i in range(len(futs_data)):
            if pairs[k][0] in futs_data.iloc[i]['instrument_name']:
                futs_data.loc[futs_data.index == i, 'timestamp_of_exp'] = k
                futs_data.loc[futs_data.index == i,'annualised_yield'] = (futs_data.iloc[i]['mid_price'] - price)/price/ ((k-datetime.now().timestamp())/31536000)*100
    
    return futs_data

