import psycopg2
import pandas as pd
import time
import random
from datetime import datetime
from api_authenticator import APIAuthenticator as auth
from binance.client import Client

class TradingBot: 
    
    def __init__(self, coin_list):
        self.watch_list,self.bought_list = [],[]
        self.coin_list = coin_list
        self.api_key, self.api_secret = auth.get_api_keys()
        self.client = Client(self.api_key,self.api_secret)
        self.buy_time,self.buy_price = None,None
        self.checkpoint,self.max_rsi = 0,0
        self.limit = 0
    
    def get_coin_data(self, coin):
        symbol = '{}BTC'.format(coin)
        while True:
            try:
                coin_data = self.client.get_historical_klines(symbol, 
                            Client.KLINE_INTERVAL_1MINUTE, '1 hour ago UTC')
                break
            except:
                print('Connection Error. Retrying...')
                time.sleep(1)
                continue
        history_df = pd.DataFrame(columns=['time','open','close'])
        for datapoint in coin_data:
            timestamp = int(str(datapoint[0])[:10])
            time_conv = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
            open_val = float(datapoint[1])
            close_val = float(datapoint[4])
            history_df = history_df.append({'time':time_conv,'open':open_val,
                                            'close':close_val},ignore_index=True)
        return history_df.iloc[:-1,:]
    
    def calculate_sma(self, window, coin_data):
        sma = coin_data['close'].rolling(window=window).mean()
        last_sma = sma.iloc[-1]
        return round(last_sma,8)
    
    def calculate_rsi(self, coin_data):
        period = 14
        change = coin_data['close'].diff(1)
        gain = change.mask(change < 0, 0)
        loss = change.mask(change > 0, 0)
        average_gain = gain.ewm(com=period-1,min_periods=period).mean()
        average_loss = loss.ewm(com=period-1,min_periods=period).mean()
        rs = abs(average_gain/average_loss)
        rsi = 100 - (100/(1+rs))
        last_rsi = rsi.iloc[-1]
        return round(last_rsi,2)
            
    def search_coin_list(self):
        print('Looking for coins...')
        for coin in self.coin_list:
            coin_data = self.get_coin_data(coin)
            last_open = coin_data.iloc[-1,1]
            last_close = coin_data.iloc[-1,2]
            sma = self.calculate_sma(50, coin_data)
            if (last_open < sma) and (last_close < sma):
                if coin not in self.watch_list:
                    self.watch_list.append(coin)
        
    def buy_coin(self, coin):
        symbol = '{}BTC'.format(coin) 
        time_now = datetime.now().strftime('%H:%M:%S')
        ticker = self.client.get_symbol_ticker(symbol=symbol)
        current_price = round(float(ticker['price']), 8)
        print('Bought: {} {} {}'.format(coin,time_now,current_price))
        self.bought_list.append(coin)
        self.buy_time = time_now
        self.buy_price = current_price
        self.limit = self.buy_price - (self.buy_price * 0.005)
        
    def sell_coin(self, coin):
        symbol = '{}BTC'.format(coin) 
        time_now = datetime.now().strftime('%H:%M:%S')
        ticker = self.client.get_symbol_ticker(symbol=symbol)
        current_price = round(float(ticker['price']), 8)
        print('Sold: {} {} {}'.format(coin,time_now,current_price))
        self.bought_list.remove(coin)
        sql_data = self.prepare_sql_data(coin,self.buy_time,time_now,
                                         self.buy_price,current_price)  
        self.insert_into_database(sql_data)
        self.checkpoint = 0
        self.max_rsi = 0
        
    def wait_for_next_minute(self):
        while True:
            seconds = datetime.now().second
            if seconds == 5:
                return True
            else:
                time.sleep(1)
    
    def prepare_sql_data(self,coin,buy_time,sell_time,buy_price,sell_price):
        date = datetime.now().strftime('%Y-%m-%d')
        time_diff = (datetime.strptime(sell_time,'%H:%M:%S') - 
                     datetime.strptime(buy_time,'%H:%M:%S'))
        price_diff_percentage = (round(((sell_price - buy_price) / buy_price) 
                                * 100, 2))
        data = [date,coin,buy_time,sell_time,buy_price,sell_price,time_diff,
                price_diff_percentage]
        return data
    
    def insert_into_database(self, data):
        sql = """INSERT INTO order_book VALUES(%s,%s,%s,%s,%s,%s,%s,%s)"""
        conn = None
        try:
            conn = psycopg2.connect(host="localhost",database="postgres", 
                                    user="postgres", password="admin")
            cur = conn.cursor()
            cur.execute(sql,(data[0],data[1],data[2],data[3],data[4],data[5],
                             data[6],data[7]))
            conn.commit()
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
        finally:
            if conn is not None:
                conn.close()
        return True
                    
    def trade(self):
        self.is_coin_bought = False
        while True:
            self.search_coin_list()
            print('Watch List: {}'.format(self.watch_list))
            if len(self.watch_list) > 0:
                random.shuffle(self.watch_list)
                for coin in self.watch_list:
                    coin_data = self.get_coin_data(coin)
                    open_price = coin_data.iloc[-1,1]
                    close_price = coin_data.iloc[-1,2]
                    sma = self.calculate_sma(50, coin_data)
                    print('Coin: {}, Open: {}, Close: {}, SMA: {}'.
                          format(coin,open_price,close_price,sma))
                    if (open_price > sma) and (close_price > sma):
                            self.buy_coin(coin)
                            self.watch_list = []
                    while len(self.bought_list) > 0:
                        time_now = datetime.strptime(datetime.now().
                                   strftime('%H:%M:%S'),('%H:%M:%S'))
                        coin_data = self.get_coin_data(coin)
                        close_price = coin_data.iloc[-1,2]
                        sma = self.calculate_sma(50, coin_data)
                        rsi = self.calculate_rsi(coin_data)
                        print('Close: {}, SMA: {}, RSI: {}'.format(close_price,sma,rsi))
                        if rsi > 50:
                            if rsi > self.max_rsi:
                                self.max_rsi = rsi
                                self.checkpoint = self.max_rsi - 10
                                print('Max RSI: {}, Checkpoint: {}'.
                                      format(self.max_rsi,self.checkpoint))
                        if rsi > 70:
                            self.sell_coin(coin)
                        if rsi < self.checkpoint:
                            self.sell_coin(coin)
                        elif (close_price < sma) and (close_price >= self.buy_price):
                            self.sell_coin(coin)
                        elif close_price < self.limit:
                            self.sell_coin(coin)
                        else:
                            print('Waiting...')
                            time.sleep(5)
                            self.wait_for_next_minute()
                    if len(self.watch_list) == 0:
                        break
            print('Waiting...')
            self.wait_for_next_minute()
            
    

if __name__ == '__main__':
    
    coin_list = ['ETH','BNB','XRP','BCH','XMR','EOS','WRX','LINK','LTC','DASH']
    
    pd.set_option("display.precision", 8)
    
    tb = TradingBot(coin_list)
    tb.trade()