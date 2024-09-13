import asyncio
from datetime import datetime, timedelta
from ib_insync import IB, Stock, LimitOrder, util, Contract
from ib_insync.contract import Index as IND
import pytz

# Initialize the IB object and connect
ib = IB()
ib.connect('127.0.0.1', 4002, clientId=1)




contract = Stock(symbol='AAPL', exchange='SMART', currency='USD')
#contract = IND(symbol='NDX', exchange='NASDAQ', currency='USD', localSymbol='NDX', conId=416843)



# Define parameters
deposit_amount = 100000  # Example deposit amount
position_size = deposit_amount * 0.01  # 1% of equity
timezone = pytz.timezone("Europe/Berlin")
entry_time = timezone.localize(datetime.now().replace(hour=15, minute=30, second=0, microsecond=0))
end_time = timezone.localize(datetime.now().replace(hour=21, minute=30, second=0, microsecond=0))

# Helper functions
def get_current_time():
    return datetime.now(tz=timezone)

def get_day_of_week():
    return get_current_time().weekday()

def market_is_open():
    now = get_current_time()
    if now.weekday() >= 5:  # Saturday and Sunday
        return False
    return entry_time.time() <= now.time() <= end_time.time()

# Main trading loop
while True:
    if market_is_open():
        current_time = get_current_time()
        current_day = get_day_of_week()

        # Stream 4-hour candles
        bars = ib.reqHistoricalData(
            contract = contract,
            endDateTime='',
            durationStr='1 D',
            barSizeSetting='4 hours',
            whatToShow='MIDPOINT',
            useRTH=True,
            keepUpToDate=True,
            formatDate=1
        )

        if current_day == 0 and current_time >= entry_time:
            # On Monday, set up orders
            print(bars)
            close_price = bars[-1].close

            if close_price:
                kauf_price = close_price * 0.99
                take_profit_price = close_price * 1.01
                stop_loss_price = close_price * 0.99

                # Place entry order
                entry_order = LimitOrder('BUY', position_size, kauf_price)
                trade = ib.placeOrder(contract, entry_order)

                # Wait for the order to fill
                while not trade.isDone():
                    ib.sleep(1)

                print(f"Entry order filled at {trade.fills[0].execution.price}")

                # Place take profit order
                take_profit_order = LimitOrder('SELL', position_size, take_profit_price)
                ib.placeOrder(contract, take_profit_order)

                # Monitor and manage the position
                while market_is_open():
                    # Check stop loss condition
                    position = ib.positions()
                    if position and position[0].avgCost > stop_loss_price:
                        ib.closePosition(contract)
                        print("Position closed due to stop loss.")

                    if get_day_of_week() == 4 and get_current_time() >= end_time:
                        # On Friday at the end time, close the position
                        ib.closePosition(contract)
                        print("Position closed at end of week.")
                        break

                    ib.sleep(60)  # Sleep for 1 minute

    else:
        print("Market is closed.")
        ib.sleep(60)  # Sleep for 1 minute