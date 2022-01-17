#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 11 11:41:31 2022

@author: josevans
"""

import streamlit as st
import json
import websocket
import time
import pandas as pd
import ast

data = {}

def on_open(ws):
    msg = \
    {"jsonrpc": "2.0",
     "method": "public/subscribe",
     "id": 42,
     "params": {
        "channels": ["ticker.{}-{}-{}-{}.raw".format(asset, expiry, strike, option)]}
    }

    ws.send(json.dumps(msg))
    print('opened')

def on_error(ws, msg):
    print('error')
    print(msg)

def on_message(ws, msg):
    d = json.loads(msg)
    ## dt.datetime.fromtimestamp(1641870564016/1000)
    data = pd.read_json(msg).reset_index()
    data = pd.DataFrame(data.iloc[1].params).iloc[0]
    st.write(data[['bid_iv', 'ask_iv']])
    


def on_close(ws):
    print("closed connection")    
    

asset = st.selectbox(label='Select Asset', options=['BTC', 'ETH'])
expiry = st.text_input('Expiry', value='28JAN22')
strike = st.text_input('Strike', value='45000')
option = st.selectbox(label='Call/Put', options=['C', 'P'])

if st.button('Get Option Price'):
    # socket='wss://test.deribit.com/ws/api/v2/public/get_order_book'
    socket='wss://www.deribit.com/ws/api/v2/public/subscribe'
    ws = websocket.WebSocketApp(
        socket, 
        on_error=on_error,
        on_open=on_open, 
        on_message=on_message, 
        on_close=on_close)
    ws.run_forever()

