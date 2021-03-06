#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun  2 05:09:49 2022

@author: jevans
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
import base64

class DeribitOption:
    
    def __init__(self, ticker, strikes_exp=collections.defaultdict(list), expiries=[], instruments=[], times_dict = dict()):
        self.ticker=ticker
        self.strikes_exp = strikes_exp
        self.expiries=expiries
        self.times_dict = times_dict

if 'df' not in st.session_state:
    st.session_state['df'] = pd.DataFrame(columns=['Asset', 'P/C', 'Expiry', 'Strike', 'Bid', 'Offer','Spot', 'Forward', 'Delta', 'PriceTime']) 

if 'count' not in st.session_state:
    st.session_state['count'] = 0
    
def get_table_download_link(df):
    """Generates a link allowing the data in a given panda dataframe to be downloaded
    in:  dataframe
    out: href string
    """
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()  # some strings <-> bytes conversions necessary here
    href = f'<a href="data:file/csv;base64,{b64}">Download csv file</a>'
    
    return href
    
st.write("""
         
# Option Pricer
Enter the required fields
""")

@st.cache(ttl=86400, suppress_st_warning=True)
def get_instruments():
    
    DeribitBtc = DeribitOption("BTC")    
    DeribitEth = DeribitOption("ETH")   
    DeribitSol = DeribitOption("SOL")     

    currentDeribitAssets = [DeribitBtc, DeribitEth, DeribitSol]
        
    st.write('Getting Instrument Data')
    ws = websocket.create_connection('wss://www.deribit.com/ws/api/v2/public/subscribe')
    
    options = currentDeribitAssets
    masterTimestamps = []
      
    for opt in options:
        
        opt.strikes_exp = collections.defaultdict(list)
        expiries = []
        timestamps = []
        
        msg = \
            {
      "jsonrpc" : "2.0",
      "id" : 7617,
      "method" : "public/get_instruments",
      "params" : {
          
        "currency" : opt.ticker,
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
            opt.strikes_exp[d['expiration_timestamp']/1000].append(int(d['strike']))
               
            expiries.append(d['expiration_timestamp']/1000)
            expiries = list(dict.fromkeys(expiries))
            expiries = [n for n in expiries]
    
        timestamps = expiries
        for t in timestamps:
            masterTimestamps.append(t)
        expiries = [datetime.fromtimestamp(x).strftime('%d%b%y').upper() for x in expiries]
        for i in range(len(expiries)):
            if expiries[i][0] == '0':
                expiries[i] = expiries[i][1:]
        opt.expiries = expiries
        
       
        opt.strikes_exp = {datetime.fromtimestamp(x).strftime('%d%b%y').upper():v for x, v in opt.strikes_exp.items()}
        
    
        for k, v in opt.strikes_exp.copy().items():
                    if k[0] == '0':
                        opt.strikes_exp[k[1:]] = opt.strikes_exp.pop(k)
    
        times_dic = dict(zip(expiries, timestamps))
        
        for k, v in times_dic.items():
            opt.times_dict[k]= [v, (datetime.fromtimestamp(v)-datetime.now()).days/365.25]
    
    masterTimestamps = list(set(masterTimestamps))    
    
    st.write('Finished Getting Instrument Data')
    
    return masterTimestamps, DeribitBtc, DeribitEth, DeribitSol

expiries, DeribitBtc, DeribitEth, DeribitSol = get_instruments()

currentDeribitAssets = [DeribitBtc, DeribitEth, DeribitSol]

# def get_vols(asset, d_expiry, d_strike, option):
    
#     try:
#         vol_df = pd.DataFrame()
        
#         ws = websocket.create_connection('wss://www.deribit.com/ws/api/v2/public/subscribe')
       
#         msg = \
#             {"jsonrpc": "2.0",
#              "method": "public/subscribe",
#              "id": 42,
#              "params": {
#                 "channels": ["ticker.{}-{}-{}-{}.raw".format(asset, d_expiry, d_strike, option)]}
#             }
        
#         ws.send(json.dumps(msg))
        
#         while len(vol_df) < 2:
#             try:
#                 result = ws.recv()
                
#                 vol_df = pd.read_json(result).reset_index()
#             except:
#                 continue
    
            
#         vol_df = pd.DataFrame(vol_df.iloc[1].params).iloc[0]
#         bid = vol_df['bid_iv'] 
#         offer = vol_df['ask_iv']
        
#         return bid, offer
#     except:
#         st.write('Error getting data from Deribit, please continue with manual inputs')

def get_single(ins):
    
    ws = websocket.create_connection('wss://www.deribit.com/ws/api/v2/public/subscribe')
    
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
    
    return mark, underlying


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

tickers = list(pd.read_csv('https://raw.githubusercontent.com/londonjevans/option_pricer/main/digital_currency_list.csv')['currency code'])
tickers.append('MIR')
tickers.append('LOOKS')
tickers.append('ICP')
tickers.append('NEAR')


price = 0


def reset_price():
    price=0
    return price

def update_first():
    try:
        st.session_state.second = round(st.session_state.first/price*100, 2)
    except:
        st.write('Error updating related field')

def update_second():
    try:
        st.session_state.first = round(st.session_state.second/100*price, 2)
    except:
        st.write('Error updating related field')
    
def update_third():
    try:
        st.session_state.fourth = round(st.session_state.third/round(price*moneyness, 2), 2)
    except:
        st.write('Error updating related field')


def update_fourth():
    try:
        st.session_state.third = round(st.session_state.fourth*round(price*moneyness, 2), 2)
    except:
        st.write('Error updating related field')

man_ticker = st.sidebar.text_input('Enter manual ticker').upper()

if not man_ticker:
    asset = st.sidebar.selectbox("Asset - e.g. ETH", options=tickers, index=tickers.index('ETH'), on_change=reset_price)

if man_ticker:
    asset = man_ticker
    
@st.cache(suppress_st_warning=True, allow_output_mutation=True, ttl=60)
def get_spot(asset):
    
    try:
        url = 'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={}&to_currency=USD&apikey=W7Y4ZQP4R37OFPRO'.format(asset)
        r = requests.get(url)
        
        df = pd.DataFrame(r.json()).T
        
        price = pd.to_numeric(df.iloc[0, 4])
    
        return price
    except:
        st.write('Error retrieving spot price please enter manually in top left')

        return price

@st.cache(suppress_st_warning=True, allow_output_mutation=True, ttl=86400)
def get_hist(asset):
    
    try:
        url = 'https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol={}&market=USD&apikey=W7Y4ZQP4R37OFPRO'.format(asset)
        r = requests.get(url)
        
        df_hist = pd.DataFrame(r.json()['Time Series (Digital Currency Daily)']).T.iloc[:, [0, 2, 4, 6]]
        
        df_hist = df_hist.rename(columns={'1a. open (USD)':'open', '2a. high (USD)':'high', '3a. low (USD)':'low', '4a. close (USD)':'close'})
        
        df_hist = df_hist.apply(pd.to_numeric).sort_index()
        done = True
    except:
        st.write('No historical price data available for {}'.format(asset))
        done=False
        
    if done:   
        return df_hist


@st.cache(suppress_st_warning=True, ttl=86400)
def get_alt_vol(asset, str_dbt_expi, dbt_strike,option_type, eth_vol, days_to_expiry=30):
    
    try:
        assets = [asset, 'ETH']
        
        vols = pd.DataFrame()
            
        for a in assets:
            for i in range(2):     
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
                
                
                vols['{}'.format(a)] = get_pk(data, window=days_to_expiry)
                
            st.write('Current {} day realised vol for {} is {}%'.format(days_to_expiry, a, round(vols['{}'.format(a)].iloc[-2]*100, 2)))
        
        alt_realised = vols['{}'.format(asset)].iloc[-2]
        eth_realised = vols['ETH'].iloc[-2]
        
        premium = round((eth_vol-eth_realised*100)*max(alt_realised/eth_realised, 1), 2)
        
        alt_mid = round(premium+alt_realised*100, 2)
        
        st.write('''Based on current IV Premium/DIscount for ETH in relevant strike/expiry, 
                 Mid Price IV for {} is {}%'''.format(asset, alt_mid))
        try:
            return alt_mid
        except Exception as e:
            print(e)
            return 70
    except Exception as e:
        print(e)
        st.write('Error getting data from Deribit, please continue with manual inputs')
        try:
            return alt_mid
        except Exception as e:
            print(e)
            return 70

def get_cbs(asset, gran=60):
    now = datetime.now()
    ticker = asset+'-USD'
    start = str(now.date()-timedelta(days=1))
    r = f"https://api.pro.coinbase.com/products/{ticker}/candles?start={start}T00:00:00&granularity={gran}"
    j = requests.get(r).json()

    df = pd.DataFrame(j)
    price = df.iloc[0, 4]
    return price

def get_cbs_hist(asset, gran=86400):

    now = datetime.now()
    ticker = asset+'-USD'
    start = str(now.date()-timedelta(days=1))
    r = f"https://api.pro.coinbase.com/products/{ticker}/candles?start={start}T00:00:00&granularity={gran}"
    j = requests.get(r).json()

    df = pd.DataFrame(j)
    df[0] = pd.to_datetime(df[0], unit='s')
    df.set_index(0, inplace=True)
    df.sort_index(inplace=True)
    df.columns = ('low','high','open','close','volume')
    
    return df

######### BITFINEX
# https://api-pub.bitfinex.com/v2/candles/trade:TimeFrame:Symbol/Section

# Available values: '1m', '5m', '15m', '30m', '1h', '3h', '6h', '12h', '1D', '1W', '14D', '1M'
def get_bfx(symb):
    symb=symb+'USD'
    map_ = {"ALGO":"ALG"}
    for k, v in map_.items():
        if k in symb:
            symb = symb.replace(k, v)
    
    endpoint = f"https://api-pub.bitfinex.com/v2/candles/trade:1D:t{symb.replace('-','')}/hist"
    j = requests.get(endpoint).json()

    df = pd.DataFrame(j)
    df[0] = pd.to_datetime(df[0], unit='ms')
    df.set_index(0, inplace=True)
    df.sort_index(inplace=True)
    df.columns = ('low','high','open','close','volume')
    
    return df

if asset:
  
  while price == 0:
    try:
      price = get_cbs(asset)
    except:
      price = get_spot(asset)
    if price == None:
      st.write('fetching AV price')
      
      price = get_spot(asset)

  man_price = st.sidebar.number_input('Manual Price Entry')
  
  if man_price:
      price = man_price

   
  st.write('Spot price of {} is {}'.format(asset, price))
  
  now = datetime.now()
  
  spread = st.sidebar.number_input("Spread % IV each side", value=3)/100
  
  drift = st.sidebar.number_input("Drift % IV - shift bid & offer up or down, minus for down", value=0)
  
  days_to_expiry = st.sidebar.number_input("Days to Expiry", value=7)
  
  custom_expiry = st.sidebar.date_input("Custom Expiry Date - N.B. Do NOT need both this and Expiry days, BUT you do need to make sure the UTC hour of expiry is correct", (now-timedelta(days=1)))

  hour_of_expiry_utc = st.sidebar.number_input("UTC Hour of Expiry", value=8)
  
  
  if custom_expiry > now.date():
      dt_custom_expiry = datetime(custom_expiry.year, custom_expiry.month, custom_expiry.day, hour_of_expiry_utc, 0)
      days_to_expiry = (dt_custom_expiry.date()-now.date()).days
      
  option_type = st.sidebar.selectbox("Call or Put", options=('C', 'P'), index=1)

  expiry = now+timedelta(days=days_to_expiry)

  expiry = expiry.replace(hour=hour_of_expiry_utc, minute=00, second=00, microsecond=0)

  fraction_of_year = (expiry-now).total_seconds()/60/60/24/365
  
  if now.date() > custom_expiry:
        dbt_expiry = min(expiries, key=lambda x:abs(x-expiry.timestamp()))
  else:
        dbt_expiry = min(expiries, key=lambda x:abs(x-dt_custom_expiry.timestamp()))
    
  str_dbt_expi = datetime.fromtimestamp(dbt_expiry).strftime('%d%b%y').upper()
  
  if str_dbt_expi[0] == '0':
      str_dbt_expi = str_dbt_expi[1:]
  
  fraction_dbit = DeribitBtc.times_dict[str_dbt_expi][1]

  custom_strike = st.sidebar.number_input("Custom Strike", key='first', on_change=update_first)
  
  if custom_strike == 0: 
    
    default_moneyness = 95
  else: 
    default_moneyness = round(custom_strike/price*100,2)
  
  success = False  
    
  if asset in ['BTC', 'ETH', 'SOL']:
      
      for cAsset in currentDeribitAssets:
          if asset == cAsset.ticker:
              try:
                  strikes = cAsset.strikes_exp[str_dbt_expi]
                  dbt_strike = min(strikes, key=lambda x:abs(x-(default_moneyness/100*price)))
      
                  ins = '{}-{}-{}-{}'.format(asset, str_dbt_expi, dbt_strike, option_type)
     
                  try:
                      b_vol, underlying = get_single(ins)
        
                      o_vol=b_vol+spread*100+drift
                      b_vol=b_vol-spread*100+drift
                      fwd_yield = (((underlying-price)/price)/fraction_dbit)*100
                      success = True
                  except:
                      st.write('Error getting Deribit pricing back - input IVs manually')
                      b_vol=70-spread*100+drift
                      o_vol = 70+spread*100+drift
                  
              except:
                  break
    
  if success == False:
      
      eth_price=get_cbs('ETH')
      strikes = DeribitEth.strikes_exp[str_dbt_expi]
      dbt_strike = min(strikes, key=lambda x:abs(x-(default_moneyness/100*eth_price)))
      ins = '{}-{}-{}-{}'.format('ETH', str_dbt_expi, dbt_strike, option_type)
      
      try:
        eth_vol, underlying = get_single(ins)

        fwd_yield = (((underlying-eth_price)/eth_price)/fraction_dbit)*100
        
      except Exception as e:
          st.write(e)
          fwd_yield = 0
          
      alt_vol = get_alt_vol(asset, str_dbt_expi, dbt_strike,option_type, eth_vol, days_to_expiry)
      b_vol = alt_vol-spread*100+drift
      o_vol = alt_vol+spread*100+drift

  
  forward_yield = st.sidebar.number_input("Forward Yield - e.g. for 5% input 5", value=fwd_yield)/100    
  
  forward_price = price*(1+fraction_of_year*forward_yield)
  
  bid_vol = st.sidebar.number_input("Bid IV - e.g. if 80% input 80", value=b_vol)/100

  offer_vol = st.sidebar.number_input("Offer IV - e.g. if 80% input 80", value=o_vol)/100
  
  moneyness = st.sidebar.number_input("% moneyness e.g. 95", value=default_moneyness,key='second', on_change=update_second)/100
    
  notional = st.sidebar.number_input("Notional $", value=5000000,key='third', on_change=update_third)
    
  notional_coin_default = round(notional/(price*moneyness), 0)
  
  notional_coin = st.sidebar.number_input("Notional coins", key='fourth', value=notional_coin_default, on_change=update_fourth)
  
  client = st.sidebar.text_input('Client Name', value='Rovida')
  
  settlement_date = now+timedelta(days=2)
  
  st.sidebar.write('MillMount Entry Section')
  
  st.sidebar.write('-------------------------')
                  
  mid = st.sidebar.number_input('Starting Price', value=price)
  
  desired_vol = st.sidebar.number_input('Desired vol in % (e.g. for 80% choose 80', value=o_vol)/100
  
  strike_increments = st.sidebar.number_input('Strike Increments in % (e.g. 1 for 1%)')/100
  
  max_range = st.sidebar.number_input('Max range in % (e.g. for 20% choose 20')/100
  
  while settlement_date.weekday() > 4:
      settlement_date+=timedelta(days=1)
  
  
  if st.button('Calculate price'):
    st.session_state.count += 1
    if custom_expiry > now.date():
      expiry = datetime(custom_expiry.year, custom_expiry.month, custom_expiry.day, hour_of_expiry_utc)
      fraction_of_year = (expiry-now).total_seconds()/60/60/24/365

    if custom_strike:
      if option_type == 'C':
        cdelta = round(call_delta(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=bid_vol)*100, 2)
        if price > 100:  
            c = round(price*moneyness, 0)
            bid = round(bs_call(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=bid_vol), 2)
            offer = round(bs_call(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=offer_vol), 2)
        elif price > 2 and price < 100:
            c = round(price*moneyness, 2)
            bid = round(bs_call(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=bid_vol), 4)
            offer = round(bs_call(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=offer_vol), 4)
        else:
            c = price*moneyness
            bid = round(bs_call(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=bid_vol), 6)
            offer = round(bs_call(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=offer_vol), 6)
    
        st.write('Expiry  = {}. {} Spot = \${} -----    \${} strike calls - moneyness {}%'.format(expiry, asset, price,  custom_strike, round(custom_strike/price*100)))
        st.write('\${}/\${} ({}/{} {}),      vols = {}%/{}%, delta = {}%'.format(bid, offer, round(bid/forward_price, 4), round(offer/forward_price, 4), asset, round((bid_vol)*100, 2), round((offer_vol)*100, 2), cdelta))
        st.write('Notional = \${:,}, Notional Coin = {:,}, \$ Delta = \${:,}, Coin Delta = {:,},     (note {:,} coin delta if selling the option)'.format(notional, notional_coin, round(notional*cdelta/100, 2), round(notional_coin*cdelta/100, 2), round(notional_coin*cdelta/100, 2)*-1))
        st.write('')
        st.write('If Client Sells:') 
        st.write('{} sells, Blockchain.com buys {} {} \${:,} calls expiring {} for \${:,} per {}, total premium \${:,} ({} {}). IM owed by {} to Blockchain.com is {:,} {}.  Settlement Date: {}'.format(client, notional_coin, asset, custom_strike, expiry,bid, asset, round(bid*notional_coin), round(bid/forward_price, 4)*notional_coin, asset, client, round((.3*notional_coin)), asset, settlement_date))
        st.write('') 
        st.write('') 
        st.write('') 
        st.write('If Client Buys:') 
        st.write('Blockchain.com sells, {} buys {} {} \${:,} calls expiring {} for \${:,} per {}, total premium owed by {} to Blockchain.com \${:,}. Settlement Date: {}'.format(client, notional_coin, asset, custom_strike, expiry,offer, asset, client, round(offer*notional_coin), settlement_date))

      else:
          if price > 100:  
              c = round(price*moneyness, 0)
              bid = round(bs_put(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=bid_vol), 2)
              offer = round(bs_put(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=offer_vol), 2)
          elif price > 2 and price < 100:
              c = round(price*moneyness, 2)
              bid = round(bs_put(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=bid_vol), 4)
              offer = round(bs_put(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=offer_vol), 4)
          else:
              c = price*moneyness
              bid = round(bs_put(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=bid_vol), 6)
              offer = round(bs_put(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=offer_vol)   , 6)       
          pdelta = round(put_delta(S=price, K=custom_strike, T=fraction_of_year, r=forward_yield, sigma=bid_vol)*100, 2)
    
          st.write('Expiry  = {}. {} Spot = \${} -----    \${} strike puts - moneyness {}% '.format(expiry, asset, price,  custom_strike, round(custom_strike/price*100)))
          st.write('\${}/\${} ({}/{} {}),      vols = {}%/{}%, delta = {}%'.format(bid, offer, round(bid/forward_price, 4), round(offer/forward_price, 4), asset, round((bid_vol)*100, 2), round((offer_vol)*100, 2),pdelta))

          st.write('Notional = \${:,}, Notional Coin = {:,}, Delta = \${:,}, Coin Delta = {:,},       (note {:,} coin delta if selling the option)'.format(notional, notional_coin, round(notional*pdelta/100, 2), round(notional_coin*pdelta/100, 2), round(notional_coin*pdelta/100, 2)*-1))
          st.write('')
          
          st.write('{} sells, Blockchain.com buys {} {} \${:,} puts expiring {} for \${:,}, total premium \${:,} ({} {}). IM owed by {} to Blockchain.com is \${:,},  net of premium = \${:,}. Settlement Date: {}'.format(client, notional_coin, asset, custom_strike, expiry,bid, round(bid*notional_coin), round(bid/forward_price, 4)*notional_coin, asset, client,  round(.3*notional_coin*custom_strike), round((.3*notional_coin*custom_strike)-(bid*notional_coin)), settlement_date))
          st.write('') 
          st.write('') 
          st.write('') 
          st.write('If Client Buys:') 
          st.write('Blockchain.com sells, {} buys {} {} \${:,} puts expiring {} for \${:,} per {}, total premium owed by {} to Blockchain.com \${:,}.Settlement Date: {}'.format(client, notional_coin, asset, custom_strike, expiry,offer, asset, client, round(offer*notional_coin), settlement_date))


    else:
      if option_type == 'C':
        if price > 100:  
            c = round(price*moneyness, 0)
            bid = round(bs_call(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=bid_vol), 2)
            offer = round(bs_call(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=offer_vol), 2)
        elif price > 2 and price < 100:
            c = round(price*moneyness, 2)
            bid = round(bs_call(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=bid_vol), 4)
            offer = round(bs_call(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=offer_vol), 4)
        else:
            c = price*moneyness
            bid = round(bs_call(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=bid_vol), 6)
            offer = round(bs_call(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=offer_vol), 6)

        cdelta = round(call_delta(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=bid_vol)*100, 2)

        st.write('Expiry  = {}. {} Spot = \${} -----    \${} strike calls - moneyness {}% '.format(expiry, asset, price,  c, round(c/price*100)))
        st.write(' \${}/\${} ({}/{} {}),      vols = {}%/{}%, delta = {}%'.format(bid, offer, round(bid/forward_price, 4), round(offer/forward_price, 4), asset, round((bid_vol)*100, 2), round((offer_vol)*100, 2), cdelta))
        st.write('Notional = \${:,}, Notional Coin = {:,}, \$ Delta = \${:,}, Coin Delta = {:,}, (note    {:,} coin delta if selling the option)'.format(notional, notional_coin, round(notional*cdelta/100, 2), round(notional_coin*cdelta/100, 2), round(notional_coin*cdelta/100*-1, 2)))
        st.write('') 
        st.write('If Client Sells:') 
        st.write('{} sells, Blockchain.com buys {} {} \${:,} calls expiring {} for \${:,} per {}, total premium \${:,} ({} {}). IM owed by {} to Blockchain.com is {:,} {}. Settlement Date: {}'.format(client, notional_coin, asset, c, expiry,bid, asset, round(bid*notional_coin), round(bid/forward_price, 4)*notional_coin, asset, client, round(.3*notional_coin), asset, settlement_date))
        st.write('') 
        st.write('') 
        st.write('') 
        st.write('If Client Buys:') 
        st.write('Blockchain.com sells, {} buys {} {} \${:,} calls expiring {} for \${:,} per {}, total premium owed by {} to Blockchain.com \${:,}. Settlement Date: {}'.format(client, notional_coin, asset, c, expiry,offer, asset, client, round(offer*notional_coin), settlement_date))

      else:
        if price > 100:  
            c = round(price*moneyness, 0)
            bid = round(bs_put(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=bid_vol), 2)
            offer = round(bs_put(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=offer_vol), 2)
        elif price > 2 and price < 100:
            c = round(price*moneyness, 2)
            bid = round(bs_put(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=bid_vol), 4)
            offer = round(bs_put(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=offer_vol), 4)
        else:
            c = price*moneyness
            bid = round(bs_put(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=bid_vol), 6)
            offer = round(bs_put(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=offer_vol), 6)
            
        pdelta = round(put_delta(S=price, K=c, T=fraction_of_year, r=forward_yield, sigma=bid_vol)*100, 2)

        st.write('Expiry  = {}. {} Spot = \${} -----    \${} strike puts - moneyness {}%'.format(expiry, asset, price,  c, round(c/price*100)))
        st.write('\${}/\${} ({}/{} {}),      vols = {}%/{}%, delta = {}%'.format(bid, offer, round(bid/forward_price, 4), round(offer/forward_price, 4), asset, round((bid_vol)*100, 2), round((offer_vol)*100, 2),pdelta))
        st.write('Notional = \${:,}, Notional Coin = {:,}, \$ Delta = \${:,}, Coin Delta = {:,},   (note     {:,} coin delta if selling the option)'.format(notional, notional_coin, round(notional*pdelta/100, 2), round(notional_coin*pdelta/100, 2), round(notional_coin*pdelta/100*-1, 2)))
        st.write('') 
        st.write('') 
        st.write('{} sells, Blockchain.com buys {} {} \${:,} puts expiring {} for \${:,}, total premium \${:,} ({} {}). IM owed by {} to Blockchain.com is \${:,}, net of premium = \${:,}. Settlement Date: {}'.format(client, notional_coin, asset, c, expiry,bid, round(bid*notional_coin), round(bid/forward_price, 4)*notional_coin, asset, client, round(.3*notional_coin*c), round((.3*notional_coin*c)-(bid*notional_coin)), settlement_date))
        st.write('') 
        st.write('') 
        st.write('') 
        st.write('If Client Buys:') 
        st.write('Blockchain.com sells, {} buys {} {} \${:,} puts expiring {} for \${:,} per {}, total premium owed by {} to Blockchain.com \${:,}. Settlement Date: {}'.format(client, notional_coin, asset, c, expiry,offer, asset, client, round(offer*notional_coin), settlement_date))
  
    st.session_state.df = st.session_state.df.append(pd.DataFrame({'Asset':asset, 'Spot':price, 'Forward':forward_price, 'P/C':option_type, 'Strike':c, 'Expiry':expiry, 'Bid':bid, 'Offer':offer, 'PriceTime':datetime.now()}, index= [st.session_state.count]))
    if option_type == 'C':
        st.session_state.df.loc[st.session_state.df.index == st.session_state.count, 'Delta'] = cdelta
    else:
        st.session_state.df.loc[st.session_state.df.index == st.session_state.count, 'Delta'] = pdelta
    st.write(st.session_state.df)
  
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
  R = st.number_input("Lookback window", value=120)
  
  if st.button('Click for a realised vol calculation on asset'):
    vols = pd.DataFrame()
    if len(assets) == 0:
        assets = [asset]
    for a in assets:

        try:      
            source = get_hist(a)
        except:    
            st.write('No Data for {} from Alpha Vantage, trying Coinbase'.format(a))
      
        if source is None:
            try:
                source = get_cbs_hist(a)
            except:
                try:
                    source = get_bfx(a)
                except:    
                    st.write('No Data for {}'.format(a))
        
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
  
  
  if st.button('Generate Mill Mount Options'):     
      
          
      tenors = [datetime.now()+timedelta(days=1), datetime.now()+timedelta(days=7), datetime.now()+timedelta(days=30), datetime.now()+timedelta(days=90)]
      
      slices = np.arange(0, max_range, strike_increments)
      
      call_strikes = [round((1+x) * mid, 2) for x in slices]
      
      put_strikes = [round((1-x) * mid, 2) for x in slices]
      
      MMdf = pd.DataFrame(columns=tenors, index=sorted(call_strikes, reverse=True)+put_strikes)
      
      MMdf['Moneyness %'] = (MMdf.index/mid)*100
      
      MMdf['IV for pricing %'] = desired_vol*100
   
      for tenor in tenors:
              
              fraction_of_year = (tenor-now).total_seconds()/60/60/24/365
              
              
              for c in call_strikes:
                  MMdf.loc[MMdf.index == c, tenor] = round(bs_call(S=mid, K=c, T=fraction_of_year, r=forward_yield, sigma=desired_vol), 2)
                  
              for p  in put_strikes:
                  MMdf.loc[MMdf.index == p, tenor] = round(bs_put(S=mid, K=p, T=fraction_of_year, r=forward_yield, sigma=desired_vol), 2)
          
      st.write(MMdf)
      
      st.write('Click to Download All Results in Full')
        
      st.markdown(get_table_download_link(MMdf.reset_index()), unsafe_allow_html=True)
          
          
        
