## Binace bot

### Algorithm
- Bot takes data for last HOURS hours
- If price raise was more than RAISE_PERCENT, it remembers high_price, calculates expected_low price and expected_mid_price based on DROP_PERCENT
    - `hight_price = start_price * (1 + RAISE_PERCENT)`
    - `low_price = high_price * (1 - DROP_PERCENT)`
    - `mid_price = sqrt(high_price * low_price)`
- Than bot waits for low_price to be reached (price goes down), and mid_price to be reached (price goes up)
- Once all checkpoints are gone (high, low, mid), bot places orders

### Installation
1. **Install mongodb**: https://www.mongodb.com/docs/manual/installation/
2. **Install tkinter (only for Ubuntu/Debain)** `sudo apt-get install python3-tk`
2. **Install dependencies**: `pip install -r requirements.txt` 

### Implementation details
- The bot takes candles for last HOURS hours, finds start_price, checks if there is high_price
- When new candle available, bot moved analysed snapshot by 1 candle (-1 old candle, +1 new candle) and repeats

### Tech overview
- The bot continuously fetches and processes klines data.
- **Classes**:
  - `KlineManager`: Manages retrieval and filtering of kline data from MongoDB.
  - `PriceMonitoring`: Calculates price movement based on high, low, and midpoint calculations.
  - `RealTimePriceAnalyzer`: Handles real-time price analysis by continually fetching new klines and analyzing them.
  - `HistoricalPriceAnalyzer`: Analyzes historical data for a set time range.
  - `Graphic`: Displays the price data and highlights significant high, low, and midpoint values.
  - `fetch_klines_script`: The main script that fetches klines data between specified times, using `KlineManager` to save them to MongoDB.

### Next tasks
- [ ] Draw grah: show all high, low points, now only last one
- [ ] Handle 1 year for historical analysis (performance issue)


### Running the bot 
- Сommand to run bot for binance data analysis: 
`python bot.py`
- **Parameters**: 
- --growth_percent : int type, minimum percentage increase in price for detecting price growth (default is 30%). Example: `--growth_percent=10`
- --drop_percent : int vaulue, maximum percentage drop from the high price for triggering action (default is 10%). Example: `--drop_percent=5`
- --time_window : int type, the time(hours) for which X% growth will be determined (default is 24 hours). Example: `--time_window=16`
- --analysis_start_time : str type. Start time for the analysis in the format YYYY-MM-DD or YYYY-MM-DD HH:MM:SS (default is datatime when coin started existing in binance). Example: `--analysis_start_time="2019-10-15"` `--analysis_start_time="2019-10-15 14:00:00`
- --analysis_end_time : str type. End time for the analysis in the format YYYY-MM-DD or YYYY-MM-DD HH:MM:SS (default is now).
- --coin_symbol: sring type. The cryptocurrency symbol to analyze (default is BTCUSDT).Example with Ethereum: `--coin_symbol=ETHUSDT`
- --real_time: Flag (no value required). Real-time data analysis. Start from now, analysis_start_time and analysis_end_time will be ignored.
- --draw_graph: Flag (no value required). Draw a graph


### Draw a graph 
To draw a graph with the processed points saved in a file after the bot has finished: `python draw_graph.py "processed_klines/0001_processed_klines_BTCUSDT_2023-11-05_2024-11-05.json"`

### Running the script for data uploading
To get data from binance and upload it to database at the specified time interval at the specified time interval specified in the format YYYY-MM-DD or YYYY-MM-DD HH:MM:SS (no default values):
`python fetch_klines_script.py "2017-06-15" "2019-10-15"` or `python fetch_klines_script.py "2017-06-15 16:00:00" "2019-10-15 16:00:00"`
