# -*- coding: utf-8 -*-
"""Option_Pricer (1).ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1ewVBAGzdGYN3Odk5VifdibP0o7ERSFU4
"""

import pandas as pd
import streamlit as st
import time 
import numpy as np
import requests
from math import log, sqrt, exp
from scipy.stats import norm
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import websocket
import json
import collections


st.write("""
         
# Option Pricer

Enter the required fields

""")
@st.cache(ttl=2592000)
def get_instruments():
    
    ws = websocket.create_connection('wss://www.deribit.com/ws/api/v2/public/subscribe')
    

    expiries = []
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
        st.write(e)
    
    data = pd.read_json(result).reset_index()
    
    for d in data.result:
        btc_strikes_exp[d['expiration_timestamp']/1000].append(int(d['strike']))
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
        st.write(e)
    
    data = pd.read_json(result).reset_index()
    
    for d in data.result:
        eth_strikes_exp[d['expiration_timestamp']/1000].append(int(d['strike']))
    

    
    return eth_strikes_exp, btc_strikes_exp, expiries

@st.cache(ttl=3600)
def get_futs(asset, price):
    
    
    ws = websocket.create_connection('wss://www.deribit.com/ws/api/v2/public/subscribe')
    
    msg = \
    {
      "jsonrpc" : "2.0",
      "id" : 9344,
      "method" : "public/get_book_summary_by_currency",
      "params" : {
        "currency" : asset,
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


eth_strikes, btc_strikes, expiries = get_instruments()

str_expiries = [datetime.fromtimestamp(x).strftime('%d%b%y').upper() for x in expiries]

def get_vols(asset, d_expiry, d_strike, option):
    
    try:
        vol_df = pd.DataFrame()
        
        ws = websocket.create_connection('wss://www.deribit.com/ws/api/v2/public/subscribe')
       
        msg = \
            {"jsonrpc": "2.0",
             "method": "public/subscribe",
             "id": 42,
             "params": {
                "channels": ["ticker.{}-{}-{}-{}.raw".format(asset, d_expiry, d_strike, option)]}
            }
        
        ws.send(json.dumps(msg))
        
        while len(vol_df) < 2:
            try:
                result = ws.recv()
                
                vol_df = pd.read_json(result).reset_index()
            except Exception as e:
                print(e)
                st.write(e)
    
            
        vol_df = pd.DataFrame(vol_df.iloc[1].params).iloc[0]
        bid = vol_df['bid_iv'] 
        offer = vol_df['ask_iv']
        
        return bid, offer
    except Exception as e:
        st.write(e)

def d1(S,K,T,r,sigma):
    return(log(S/K)+(r+sigma**2/2.)*T)/(sigma*sqrt(T))
def d2(S,K,T,r,sigma):
    return d1(S,K,T,r,sigma)-sigma*sqrt(T)

def bs_call(S,K,T,r,sigma):
    return S*norm.cdf(d1(S,K,T,r,sigma))-K*exp(-r*T)*norm.cdf(d2(S,K,T,r,sigma))
  
def bs_put(S,K,T,r,sigma):
    return K*exp(-r*T)-S+bs_call(S,K,T,r,sigma)


def call_delta(S,K,T,r,sigma):
    return norm.cdf(d1(S,K,T,r,sigma))

def put_delta(S,K,T,r,sigma):
    return -norm.cdf(-d1(S,K,T,r,sigma))

def get_pk(price_data, window=30, trading_periods=365, clean=True):

    rs = (1.0 / (4.0 * log(2.0))) * ((price_data['high'] / price_data['low']).apply(np.log))**2.0

    def f(v):
        return (trading_periods * v.mean())**0.5
    
    result = rs.rolling(
        window=window,
        center=False
    ).apply(func=f)
    
    if clean:
        return result.dropna()
    else:
        return result

tickers = list(pd.read_csv('digital_currency_list.csv')['currency code'])

price = 0

def reset_price():
    price=0
    return price

def update_first():
    st.session_state.second = round(st.session_state.first/price*100, 2)

def update_second():
    st.session_state.first = round(st.session_state.second/100*price, 2)
    
def update_third():
    st.session_state.fourth = round(st.session_state.third/round(price*moneyness, 2), 2)


def update_fourth():
    st.session_state.third = round(st.session_state.fourth*round(price*moneyness, 2), 2)

asset = st.sidebar.selectbox("Asset - e.g. ETH", options=tickers, index=tickers.index('ETH'), on_change=reset_price)



def get_spot(asset):
    url = 'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={}&to_currency=USD&apikey=W7Y4ZQP4R37OFPRO'.format(asset)
    r = requests.get(url)
    
    df = pd.DataFrame(r.json()).T
    
    price = pd.to_numeric(df.iloc[0, 4])

    return price

@st.cache(suppress_st_warning=True, allow_output_mutation=True, ttl=86400)
def get_hist(asset):
    url = 'https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol={}&market=USD&apikey=W7Y4ZQP4R37OFPRO'.format(asset)
    r = requests.get(url)
    
    df_hist = pd.DataFrame(r.json()['Time Series (Digital Currency Daily)']).T.iloc[:, [0, 2, 4, 6]]
    
    df_hist = df_hist.rename(columns={'1a. open (USD)':'open', '2a. high (USD)':'high', '3a. low (USD)':'low', '4a. close (USD)':'close'})
    
    df_hist = df_hist.apply(pd.to_numeric).sort_index()
    
    return df_hist

@st.cache(suppress_st_warning=True, ttl=86400)
def get_alt_vol(asset, str_dbt_expi, dbt_strike,option_type):
    
    assets = [asset, 'ETH']
    
    vols = pd.DataFrame()
        
    for a in assets:
        for i in range(10):     
          try:        
            source = get_hist(a)
          except:
            st.write('Error getting data, trying again')
            time.sleep(5)
            continue
          break
        
        if len(source) > 0:
            
            data = source.copy() 
            data['pk_returns'] = np.log(data.high/data.low)
            
            
            vols['{}'.format(a)] = get_pk(data, window=30)
            chart_data = vols.iloc[-365:]
            
        st.write('Current {} day realised vol for {} is {}%'.format(30, a, round(vols['{}'.format(a)].iloc[-2]*100, 2)))
    
    eth_vol = get_vols('ETH', str_dbt_expi, dbt_strike, option_type)
    
    alt_30d = vols['{}'.format(asset)].iloc[-2]
    eth_30d = vols['ETH'].iloc[-2]
    
    premium = round(((eth_vol[0]+eth_vol[1])/2-eth_30d*100)*max(alt_30d/eth_30d, 1), 2)
    
    alt_mid = round(premium+alt_30d*100, 2)
    
    st.write('''Based on current IV Premium/DIscount for ETH in relevant strike/expiry, 
             Mid Price IV for {} is {}%'''.format(asset, alt_mid))
    
    return alt_mid

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

if asset:
  
  
  while price == 0:
    try:
      price = get_cbs(asset)
    except:
      price = get_spot(asset)
    if price == None:
      st.write('fetching AV price')
      price = get_spot(asset)

   
  st.write('Spot price of {} is {}'.format(asset, price))
  
  now = datetime.now()
  

  
  spread = st.sidebar.number_input("Spread each side", value=3)/100
  


  days_to_expiry = st.sidebar.number_input("Days to Expiry", value=7)
  
  custom_expiry = st.sidebar.date_input("Custom Expiry Date - N.B. Do NOT need both this and Expiry days, BUT you do need to make sure the UTC hour of expiry is correct", (now-timedelta(days=1)))

  hour_of_expiry_utc = st.sidebar.number_input("UTC Hour of Expiry", value=15)
  
  
  if custom_expiry > now.date():
      dt_custom_expiry = datetime(custom_expiry.year, custom_expiry.month, custom_expiry.day, hour_of_expiry_utc, 0)
  
  option_type = st.sidebar.selectbox("Call or Put", options=('C', 'P'), index=1)

  expiry = now+timedelta(days=days_to_expiry)

  expiry = expiry.replace(hour=hour_of_expiry_utc, minute=00, second=00, microsecond=0)

  fraction_of_year = (expiry-now).total_seconds()/60/60/24/365
  
  if expiries:
      if now.date() > custom_expiry:
        dbt_expiry = min(expiries, key=lambda x:abs(x-expiry.timestamp()))
      else:
        dbt_expiry = min(expiries, key=lambda x:abs(x-dt_custom_expiry.timestamp()))
    
      str_dbt_expi = datetime.fromtimestamp(dbt_expiry).strftime('%d%b%y').upper()

  custom_strike = st.sidebar.number_input("Custom Strike", key='first', on_change=update_first)
  
  if custom_strike == 0: 
    
    default_moneyness = 95
  else: 
    default_moneyness = round(custom_strike/price*100,2)
  
  if asset in ['BTC', 'ETH']:
      
      futs_data = get_futs(asset, price)

      if asset == 'BTC':
          strikes = btc_strikes[dbt_expiry]
      else:
          strikes = eth_strikes[dbt_expiry]
          
      dbt_strike = min(strikes, key=lambda x:abs(x-(default_moneyness/100*price)))
      
      fwd_yield = futs_data.loc[futs_data['instrument_name'].str.contains(str_dbt_expi)].annualised_yield.values[0]
      
      if len(expiries) > 5:
          try:
              b_vol, o_vol = get_vols(asset, str_dbt_expi, dbt_strike, option_type)
              
          except Exception as e:
              st.write(e)
              b_vol=70
              o_vol = 70
      else:
          st.write('No Data From Deribit Available')
          b_vol=70
          o_vol = 70
        
  else:
      if len(expiries) > 5:
          eth_price=get_cbs('ETH')
          strikes = eth_strikes[dbt_expiry]
          dbt_strike = min(strikes, key=lambda x:abs(x-(default_moneyness/100*eth_price)))
          alt_vol = get_alt_vol(asset, str_dbt_expi, dbt_strike,option_type)
          b_vol = alt_vol
          o_vol = alt_vol
          futs_data = get_futs('ETH', get_cbs('ETH'))
          fwd_yield = futs_data.loc[futs_data['instrument_name'].str.contains(str_dbt_expi)].annualised_yield.values[0]
      else:
          b_vol = 70
          o_vol = 70
  
  forward_yield = st.sidebar.number_input("Forward Yield - e.g. for 5% input 5", value=fwd_yield)/100    
  
  forward_price = price*fraction_of_year*forward_yield
  
  bid_vol = st.sidebar.number_input("Bid IV - e.g. if 80% input 80", value=b_vol)/100

  offer_vol = st.sidebar.number_input("Offer IV - e.g. if 80% input 80", value=o_vol)/100
  
  moneyness = st.sidebar.number_input("% moneyness e.g. 95", value=default_moneyness,key='second', on_change=update_second)/100
    
  notional = st.sidebar.number_input("Notional $", value=5000000,key='third', on_change=update_third)
    
  notional_coin_default = round(notional/(price*moneyness), 0)
  
  notional_coin = st.sidebar.number_input("Notional coins", key='fourth', value=notional_coin_default, on_change=update_fourth)
  
  client = st.sidebar.text_input('Client Name', value='Rovida')
  
  
  if st.button('Calculate price'):

    if custom_expiry > now.date():
      expiry = datetime(custom_expiry.year, custom_expiry.month, custom_expiry.day, hour_of_expiry_utc)
      fraction_of_year = (expiry-now).total_seconds()/60/60/24/365

    if custom_strike:
      if option_type == 'C':
        cdelta = round(call_delta(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=bid_vol-spread)*100, 2)
        if price > 100:  
            c = round(price*moneyness, 0)
            bid = round(bs_call(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=bid_vol-spread), 2)
            offer = round(bs_call(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=offer_vol+spread), 2)
        elif price > 1 and price < 100:
            c = round(price*moneyness, 2)
            bid = round(bs_call(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=bid_vol-spread), 4)
            offer = round(bs_call(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=offer_vol+spread), 4)
        else:
            c = price*moneyness
            bid = bs_call(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=bid_vol-spread)
            offer = bs_call(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=offer_vol+spread)
    
        st.write('Expiry  = {}. {} Spot = **{}** -----    **{}** strike calls - moneyness {}% ----       **${}/${}**,      vols = **{}%/{}%**, delta = {}%'.format(expiry, asset, price,  custom_strike, round(custom_strike/price*100), bid, offer, round((bid_vol-spread)*100, 2), round((offer_vol+spread)*100, 2), cdelta))
        st.write('Notional = ${:,}, Notional Coin = {:,}, $ Delta = ${:,}, Coin Delta = {:,},     (note {:,} coin delta if selling the option)'.format(notional, notional_coin, round(notional*cdelta/100, 2), round(notional_coin*cdelta/100, 2), round(notional_coin*cdelta/100, 2)*-1))
        st.write('')
        st.write('If Client Sells:') 
        st.write('{} sells, Blockchain.com buys {} {} ${:,} calls expiring {} for ${:,} per {}, total premium ${:,}. IM owed by {} to Blockchain.com is ${:,},  net of premium = ${:,}'.format(client, notional_coin, asset, custom_strike, expiry,bid, asset, round(bid*notional_coin), client, round(.3*notional_coin*custom_strike), round((.3*notional_coin*custom_strike)-(bid*notional_coin))))
        st.write('') 
        st.write('') 
        st.write('') 
        st.write('If Client Buys:') 
        st.write('Blockchain.com sells, {} buys {} {} ${:,} calls expiring {} for ${:,} per {}, total premium owed by {} to Blockchain.com ${:,}.'.format(client, notional_coin, asset, custom_strike, expiry,offer, asset, client, round(offer*notional_coin)))

      else:
          if price > 100:  
              c = round(price*moneyness, 0)
              bid = round(bs_put(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=bid_vol-spread), 2)
              offer = round(bs_put(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=offer_vol+spread), 2)
          elif price > 1:
              c = round(price*moneyness, 2)
              bid = round(bs_put(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=bid_vol-spread), 4)
              offer = round(bs_put(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=offer_vol+spread), 4)
          else:
              c = price*moneyness
              bid = bs_put(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=bid_vol-spread)
              offer = bs_put(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=offer_vol+spread)          
          pdelta = round(put_delta(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=bid_vol-spread)*100, 2)
    
          st.write('Expiry  = {}. {} Spot = **{}** -----    **{}** strike puts - moneyness {}%  ----        **${}/${}**,      vols = **{}%/{}%**, delta = {}%'.format(expiry, asset, price,  custom_strike, round(custom_strike/price*100), bid, offer, round((bid_vol-spread)*100, 2), round((offer_vol+spread)*100, 2), pdelta))
          st.write('Notional = ${:,}, Notional Coin = {:,}, $ Delta = ${:,}, Coin Delta = {:,},       (note {:,} coin delta if selling the option)'.format(notional, notional_coin, round(notional*pdelta/100, 2), round(notional_coin*pdelta/100, 2), round(notional_coin*pdelta/100, 2)*-1))
          st.write('')
          
          st.write('{} sells, Blockchain.com buys {} {} ${:,} puts expiring {} for ${:,}, total premium ${:,}. IM owed by Rovida to Blockchain.com is ${:,},  net of premium = ${:,}'.format(client, notional_coin, asset, custom_strike, expiry,bid, round(bid*notional_coin), round(.3*notional_coin*custom_strike), round((.3*notional_coin*custom_strike)-(bid*notional_coin))))
          st.write('') 
          st.write('') 
          st.write('') 
          st.write('If Client Buys:') 
          st.write('Blockchain.com sells, {} buys {} {} ${:,} puts expiring {} for ${:,} per {}, total premium owed by {} to Blockchain.com ${:,}.'.format(client, notional_coin, asset, custom_strike, expiry,offer, asset, client, round(offer*notional_coin)))


    else:
      if option_type == 'C':
        if price > 100:  
            c = round(price*moneyness, 0)
            bid = round(bs_call(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=bid_vol-spread), 2)
            offer = round(bs_call(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=offer_vol+spread), 2)
        elif price > 1 and price < 100:
            c = round(price*moneyness, 2)
            bid = round(bs_call(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=bid_vol-spread), 4)
            offer = round(bs_call(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=offer_vol+spread), 4)
        else:
            c = price*moneyness
            bid = bs_call(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=bid_vol-spread)
            offer = bs_call(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=offer_vol+spread)

        cdelta = round(call_delta(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=bid_vol-spread)*100, 2)

        st.write('Expiry  = {}. {} Spot = **{}** -----    **{}** strike calls - moneyness {}% ----       **${}/${}**,      vols = **{}%/{}%**, delta = {}%'.format(expiry, asset, price,  c, round(c/price*100), bid, offer, round((bid_vol-spread)*100, 2), round((offer_vol+spread)*100, 2), cdelta))
        st.write('Notional = ${:,}, Notional Coin = {:,}, $ Delta = ${:,}, Coin Delta = {:,}, (note    {:,} coin delta if selling the option)'.format(notional, notional_coin, round(notional*cdelta/100, 2), round(notional_coin*cdelta/100, 2), round(notional_coin*cdelta/100*-1, 2)))
        st.write('') 
        st.write('If Client Sells:') 
        st.write('{} sells, Blockchain.com buys {} {} ${:,} calls expiring {} for ${:,} per {}, total premium ${:,}. IM owed by {} to Blockchain.com is ${:,}, net of premium = ${:,}'.format(client, notional_coin, asset, c, expiry,bid, asset, round(bid*notional_coin), client, round(.3*notional_coin*c), round((.3*notional_coin*c)-(bid*notional_coin))))
        st.write('') 
        st.write('') 
        st.write('') 
        st.write('If Client Buys:') 
        st.write('Blockchain.com sells, {} buys {} {} ${:,} calls expiring {} for ${:,} per {}, total premium owed by {} to Blockchain.com ${:,}.'.format(client, notional_coin, asset, c, expiry,offer, asset, client, round(offer*notional_coin)))

      else:
        if price > 100:  
            c = round(price*moneyness, 0)
            bid = round(bs_put(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=bid_vol-spread), 2)
            offer = round(bs_put(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=offer_vol+spread), 2)
        elif price > 1:
            c = round(price*moneyness, 2)
            bid = round(bs_put(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=bid_vol-spread), 4)
            offer = round(bs_put(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=offer_vol+spread), 4)
        else:
            c = price*moneyness
            bid = bs_put(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=bid_vol-spread)
            offer = bs_put(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=offer_vol+spread)
            
        pdelta = round(put_delta(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=bid_vol-spread)*100, 2)

        st.write('Expiry  = {}. {} Spot = **{}** -----    **{}** strike puts - moneyness {}%  ----       **${}/${}**,      vols = **{}%/{}%**, delta = {}%'.format(expiry, asset, price,  c, round(c/price*100), bid, offer, round((bid_vol-spread)*100, 2), round((offer_vol+spread)*100, 2),pdelta))
        st.write('Notional = ${:,}, Notional Coin = {:,}, $ Delta = ${:,}, Coin Delta = {:,},   (note     {:,} coin delta if selling the option)'.format(notional, notional_coin, round(notional*pdelta/100, 2), round(notional_coin*pdelta/100, 2), round(notional_coin*pdelta/100*-1, 2)))
        st.write('') 
        st.write('') 
        st.write('{} sells, Blockchain.com buys {} {} ${:,} puts expiring {} for ${:,}, total premium ${:,}. IM owed by Rovida to Blockchain.com is ${:,}, net of premium = ${:,}'.format(client, notional_coin, asset, c, expiry,bid, round(bid*notional_coin), round(.3*notional_coin*c), round((.3*notional_coin*c)-(bid*notional_coin))))
        st.write('') 
        st.write('') 
        st.write('') 
        st.write('If Client Buys:') 
        st.write('Blockchain.com sells, {} buys {} {} ${:,} puts expiring {} for ${:,} per {}, total premium owed by {} to Blockchain.com ${:,}.'.format(client, notional_coin, asset, c, expiry,offer, asset, client, round(offer*notional_coin)))

  st.write('')   
  st.write('') 
  st.write('') 
  st.write('') 
  st.write('') 
  st.write('') 
  st.write('')      
  st.write('If you would like to see a realised volatility calculation, use this section')     
  
  N = st.number_input("Realised vol window in days", value=30)
  
  assets = st.multiselect('Asset(s) historical vol to chart', options=tickers)      
  R = st.number_input("Lookback window", value=365)
  
  if st.button('Click for a realised vol calculation on asset'):
    vols = pd.DataFrame()
    if len(assets) == 0:
        assets = [asset]
    for a in assets:
        for i in range(10):     
          try:        
            source = get_hist(a)
          except:
            st.write('Error getting data, trying again')
            time.sleep(5)
            continue
          break
      
        if len(source) > 0:
            
            data = source.copy() 
            data['pk_returns'] = np.log(data.high/data.low)
            
            
            vols['{}'.format(a)] = get_pk(data, window=N)
            chart_data = vols.iloc[-R:]
            st.write('Current {} day realised vol for {} is {}%'.format(N, a, round(vols['{}'.format(a)].iloc[-2]*100, 2)))
            
            
        else:
            st.write('No Data')
            
    fig = plt.figure()
    sns.set_theme()
    sns.set_context('paper')
    # ax = sns.lineplot(data=chart_data, x=pd.to_datetime(chart_data.index))
    ax = chart_data.plot()
    ax.set_ylabel('Parkinson Historical Volatility')
    ax.set_title('{} day Parkinson Realised Vol'.format(N))
    ax.set_xlabel('Date')
    plt.xticks(rotation=45)
    plt.show()
    st.pyplot(plt)            
            
        
        