## Cryptocurrency Trading Bot

This is a proof of concept for a cryptocurrency trading bot that I wanted to try out. 

The main idea was this:

1. You would do a quick research on your own to look for the most promising coins at the moment. 
2. Then you would create a list of these coins and feed it to the trading bot as a 'coin list'. 
3. You would then run the bot. 
4. The bot would get the historical data about these coins using the Binance API. 
5. It would then calculate the SMA (Simple Moving Average) and the RSI (Relative Strength Index); the bot uses these two indicators for all its decisions, and it calculates them several times during the process. 
6. Based on a defined set of rules, it would decide if the coin should be added to a 'watch list', which would mean that the coin is at a low point, and might start rising. 
7. After there are coins in the 'watch list', it would switch its attention to this list, and get the historical data for these coins. 
8. Based on other set of rules, it would decide if the coin should be bought or not, usually when the coins shows signs of starting to rise. 
9. Once a coin is bought, it is added to a 'bought list', and the bot switches its attention to this list. 
10. It will start continuously looking at this coin, and decide when to sell, based on other set of rules. 
11. When it sells the coin, it adds the transaction to a PostgreSQL database for further analysis of the user, then it goes back to step 4. 

**Disclaimer**: I am no expert in trading, and created this bot out of curiosity. I tried several simple strategies, but the good and bad trades were mostly equal throughout the several strategies.
