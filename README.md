## Binace bot

### Algorithm
- Bot takes data for last HOURS hours
- If price raise was more than RAISE_PERCENT, it remembers high_price, calculates expected_low price and expected_mid_price based on DROP_PERCENT
    - `hight_price = start_price * (1 + RAISE_PERCENT)`
    - `low_price = high_price * (1 - DROP_PERCENT)`
    - `mid_price = sqrt(high_price * low_price)`
- Than bot waits for low_price to be reached (price goes down), and mid_price to be reached (price goes up)
- Once all checkpoints are gone (high, low, mid), bot places orders


### Implementation details
- The bot takes candles for last HOURS hours, finds start_price, checks if there is high_price
- When new candle available, bot moved analysed snapshot by 1 candle (-1 old candle, +1 new candle) and repeats

# TODO: Add an overview of how bot works on code level

### Next tasks
- [ ] Draw grah: show all high, low points, now only last one
- [ ] Handle 1 year for historical analysis (performance issue)


### Running the bot 
1. For historical data: `python bot.py 30 15 24 --t1="2024-10-15 16:00:00" --t2="2024-10-15 20:00:00"`
2. For real-time: `python bot.py 30 15 24 --real_time`         
3. Running with graphic `python bot.py 30 15 24 --t1="2024-10-15 16:00:00" --t2="2024-10-15 20:00:00" --plot_graphic`

### Running the script for data uploading
`python fetch_klines_script.py "2017-06-15 00:00:00" "2019-10-15 0:00:00"`
