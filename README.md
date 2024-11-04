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
1. For historical data: `python bot.py 30 15 24 --analysis_start_time="2024-10-15 16:00:00" --analysis_end_time="2024-10-15 20:00:00"`
2. For real-time: `python bot.py 30 15 24 --real_time`         
3. Running with graphic `python bot.py 30 15 24 --analysis_start_time="2024-10-15 16:00:00" --analysis_end_time="2024-10-15 20:00:00" --plot_graphic`

### Running the script for data uploading
`python fetch_klines_script.py "2017-06-15 00:00:00" "2019-10-15 0:00:00"`
