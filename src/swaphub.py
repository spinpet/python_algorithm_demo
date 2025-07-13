import threading
import time
from shortswapv1pool import ShortSwapV1Pool
from swap_utils import get_current_price,get_amount_in_reserve1_for_amount0_out,get_amount_in_reserve0_for_amount1_out, get_amount_out_reserve0_to_reserve1, get_amount_out_reserve1_to_reserve0, get_reserves_at_price

# This class is equivalent to frontend code, no need to write as contract
class SwapHub:
    def __init__(self, pool: ShortSwapV1Pool):
        self.pool = pool
        self.price_history = []
        self.current_price = None
        self.lock = threading.Lock()
        

    def get_info(self):
        """
        Get all attribute information of current pool.
        """
        with self.lock:
            return self.pool.getInfo()

    def get_reserves(self):
        """
        Get reserve information of current pool.
        """
        with self.lock:
            return self.pool.getReserves()

    def get_price(self):
        """
        Get current price.
        """
        with self.lock:
            return self.pool.getPrice()

    def buy(self, caller_address, amount1):
        """
        Execute buy operation.
        :param caller_address: Caller address
        :param amount1: Amount of tokens to buy
        """
        with self.lock:
            result = self.pool.use(caller_address).buy(amount1)
            self._update_price_history()
            return result

    def sell(self, caller_address, amount0):
        """
        Execute sell operation.
        :param caller_address: Caller address
        :param amount0: Amount of tokens to sell
        """
        with self.lock:
            result = self.pool.use(caller_address).sell(amount0)
            self._update_price_history()
            return result

    def short_open(self, caller_address, baseAmount, lendAmount, forcedClosePrice, insterOrderID):
        """
        Execute short operation.
        :param caller_address: Caller address
        :param baseAmount: User provided base token amount
        :param lendAmount: User desired borrowed token amount
        :param forcedClosePrice: Forced liquidation price
        :param insterOrderID: Insert to liquidation order queue ID
        """
        with self.lock:
            result = self.pool.use(caller_address).shortOpen(baseAmount, lendAmount, forcedClosePrice, insterOrderID)
            self._update_price_history()
            return result

    def short_close(self, caller_address, orderID, closeAmount0,isThirdParty=False):
        """
        Execute user liquidation operation.
        :param caller_address: Caller address
        :param orderID: Order ID
        :param closeAmount0: Liquidation amount
        """
        with self.lock:
            result = self.pool.use(caller_address).shortClose(orderID, closeAmount0,isThirdParty)
            self._update_price_history()
            return result



    def long_open(self, caller_address, baseAmount, lendAmount1, forcedClosePrice, insterOrderID):
        """
        Execute long operation.
        :param caller_address: Caller address
        :param baseAmount: User provided base token amount
        :param lendAmount1: User desired borrowed base token amount
        :param buyAmount0: Amount of tokens to purchase
        :param forcedClosePrice: Forced liquidation price
        :param insterOrderID: Insert to liquidation order queue ID
        """
        with self.lock:
            result = self.pool.use(caller_address).longOpen(baseAmount, lendAmount1, forcedClosePrice, insterOrderID)
            self._update_price_history()
            return result

    def long_close(self, caller_address, orderID, closeAmount0, isThirdParty=False):
        """
        Execute long liquidation operation.
        :param caller_address: Caller address
        :param orderID: Order ID
        :param closeAmount0: Liquidation amount
        """
        with self.lock:
            result = self.pool.use(caller_address).longClose(orderID, float(closeAmount0),isThirdParty)
            self._update_price_history()
            return result



    def get_price_history(self):
        """
        Return price history.
        """
        with self.lock:
            return self.price_history

    def _update_price_history(self):
        """
        Check price changes and update price history.
        """
        new_price = self.pool.getPrice()
        if new_price != self.current_price:
            self.current_price = new_price
            self.price_history.append(new_price)
            if len(self.price_history) > 100:
                self.price_history.pop(0)


    def get_address_history_orders(self, address):
        """
        Get historical orders for specified address.
        :param address: User address
        :return: Historical order list for the address
        """
        with self.lock:
            return self.pool.getAddressHistoryOrders(address)

    def get_short_order(self, num):
        """
        Get short order data.
        :param num: Number of nodes to retrieve
        :return: List containing data of specified number of nodes
        """
        with self.lock:
            return self.pool.getShortOrder(self.pool.nearShortNode, num)

    def get_long_order(self, num):
        """
        Get long order data.
        :param num: Number of nodes to retrieve
        :return: List containing data of specified number of nodes
        """
        with self.lock:
            return self.pool.getLongOrder(self.pool.nearLongNode, num)
        
    
    def short_fast_open(self, caller_address, baseAmount, levMult):
        """
        Fast short open operation.

        :param caller_address: Caller address
        :param baseAmount: User provided base token amount (USDT)
        :param levMult: Leverage multiplier
        :return: (bool, str) Whether operation was successful and corresponding message
        """
        print(f"Starting fast short open operation: address={caller_address}, base amount={baseAmount}, leverage multiplier={levMult}")

        # 1. Calculate total available amount
        total_amount = baseAmount * levMult
        print(f"1. Calculate available total amount: {total_amount}")

        # 2. Get current price and initial forced close price
        current_price = self.get_price()
        initial_forced_close_price = current_price * (1 + 1 / levMult)
        print(f"2. Current price: {current_price}, initial forced close price: {initial_forced_close_price}")

        # 3. Get current reserves
        reserve0, reserve1 = self.get_reserves()
        print(f"3. Current reserves: reserve0={reserve0}, reserve1={reserve1}")

        # 4. Loop to adjust forced close price to a value where pool won't lose money
        forced_close_price = initial_forced_close_price
        lendAmount = total_amount / current_price
        max_iterations = 10000
        for i in range(max_iterations):
            is_valid, result = self.calculate_short_open(reserve0, reserve1, baseAmount, lendAmount, forced_close_price)
            print(f"4. Attempt {i+1}: forced close price={forced_close_price}, is valid={is_valid}")
            
            if is_valid:
                break
            
            forced_close_price *= 0.998  # Decrease forced close price by 1%
            
            if forced_close_price <= current_price:
                return False, "Unable to find suitable forced close price"

        if not is_valid:
            return False, "Reached maximum iterations, still unable to find suitable forced close price"

        print(f"5. Found suitable forced close price: {forced_close_price}")

        # 5. Get short order data
        short_orders = self.get_short_order(10000)
        print(f"6. Retrieved {len(short_orders)} short orders")

        # 6. Check for intersections and adjust forced close price
        forced_initial_low_price = result['forced_initial_low_price']
        forced_final_height_price = result['forced_final_height_price']
        max_iterations = 10000  # Set maximum iterations to prevent infinite loop
        iteration = 0
        
        print("6.1 Forced liquidation range:", forced_initial_low_price, forced_final_height_price) 

        while iteration < max_iterations:
            has_intersection = False
            for order in short_orders:
                # Check for any overlap
                if not (forced_initial_low_price > order['hightPrice'] or forced_final_height_price < order['lowPrice']):
                    # Has intersection, need to adjust forced close price
                    forced_close_price = forced_close_price * 0.998
                    print(f"7. Found intersection, adjusting forced close price to: {forced_close_price}")
                    print(f"   Intersecting order: low price {order['lowPrice']}, high price {order['hightPrice']}")
                    print(f"   Current range: low price {forced_initial_low_price}, high price {forced_final_height_price}")
                    # Recalculate
                    is_valid, result = self.calculate_short_open(reserve0, reserve1, baseAmount, lendAmount, forced_close_price)
                    if not is_valid:
                        return False, "Adjusted forced close price is invalid"
                    forced_final_height_price = result['forced_final_height_price']
                    forced_initial_low_price = result['forced_initial_low_price']
                    print("8. Found new price range:", forced_final_height_price, forced_initial_low_price)
                    
                    has_intersection = True
                    break  # Break inner loop, recheck all orders
            
            if not has_intersection:
                break  # If no intersection, break outer loop
            
            iteration += 1

        if iteration == max_iterations:
            return False, "Reached maximum iterations, unable to find suitable forced close price"
        
        
        print(f"8. Found suitable forced close price: {forced_close_price}")

        # 7. Find insertion position
        insert_position = len(short_orders)  # Default insert at end
        insert_order_id = ""  # Default empty string

        for i, order in enumerate(short_orders):
            if forced_close_price < order['lowPrice']:
                insert_position = i
                if i > 0:
                    insert_order_id = short_orders[i-1]['orderID']
                break

        print(f"9. Found insertion position: {insert_position}, insert order ID: {insert_order_id}")

        # 8. Return result
        current_price = self.get_price()
        forced_close_price_moved = forced_close_price * (1 - self.pool.forceMoveRate)
        price_difference_percentage = ((forced_close_price_moved - current_price) / current_price) * 100

        return True, {
            "baseAmount": baseAmount,  # User provided base token amount (USDT)
            "lendAmount": lendAmount,  # User borrowed token amount
            "forcedClosePrice": forced_close_price,  # Initial forced liquidation price
            "insterOrderID": insert_order_id,  # Insert order ID
            "forcedClosePriceMoved": forced_close_price_moved,  # Moved down forced liquidation price
            "priceDifferencePercentage": price_difference_percentage  # Price difference percentage between moved forced close price and current price
        }

    def long_fast_open(self, caller_address, baseAmount, levMult):
        """
        Fast long open operation.

        :param caller_address: Caller address
        :param baseAmount: User provided base token amount (USDT)
        :param levMult: Leverage multiplier
        :return: (bool, str) Whether operation was successful and corresponding message
        """
        print(f"Starting fast long open operation: address={caller_address}, base amount={baseAmount}, leverage multiplier={levMult}")

        # 1. Calculate total available amount
        total_amount = baseAmount * levMult
        print(f"1. Calculate available total amount: {total_amount}")

        # 2. Get current price and initial forced close price
        current_price = self.get_price()
        initial_forced_close_price = max(current_price * (1 - 1 / levMult), current_price * 0.1)
        print(f"2. Current price: {current_price}, initial forced close price: {initial_forced_close_price}")

        # 3. Get current reserves
        reserve0, reserve1 = self.get_reserves()
        print(f"3. Current reserves: reserve0={reserve0}, reserve1={reserve1}")

        # 4. Loop to adjust forced close price to a value where pool won't lose money
        forced_close_price = initial_forced_close_price
        lendAmount1 = total_amount - baseAmount

        print("Collateral funds:",baseAmount, "borrowed funds:", lendAmount1, "forced close price:", forced_close_price)
        max_iterations = 1000
        for i in range(max_iterations):
            is_valid, result = self.calculate_long_open(reserve0, reserve1, baseAmount, lendAmount1, forced_close_price)
            print(f"4. Attempt {i+1}: forced close price={forced_close_price}, is valid={is_valid}")
            if is_valid:
                break
            
            forced_close_price *= 1.02  # Increase forced close price by 0.2%
            
            if forced_close_price >= current_price:
                return False, "Unable to find suitable forced close price"

        if not is_valid:
            return False, "Reached maximum iterations, still unable to find suitable forced close price"

        print(f"5. Found suitable forced close price: {forced_close_price}")

        # 5. Get long order data
        long_orders = self.get_long_order(10000)
        print(f"6. Retrieved {len(long_orders)} long orders")

            
        # 6. Check for intersections and adjust forced close price
        forced_initial_height_price = result['forced_initial_height_price']
        forced_final_low_price = result['forced_final_low_price']
        amount0_out = result['amount0_out']
        max_iterations = 10000  # Set maximum iterations to prevent infinite loop
        iteration = 0

        while iteration < max_iterations:
            has_intersection = False
            for order in long_orders:
                # Check for all possible intersections
                if (forced_final_low_price <= order['hightPrice'] and forced_initial_height_price >= order['lowPrice']) or \
                (forced_final_low_price >= order['lowPrice'] and forced_final_low_price <= order['hightPrice']) or \
                (forced_initial_height_price >= order['lowPrice'] and forced_initial_height_price <= order['hightPrice']) or \
                (forced_final_low_price <= order['lowPrice'] and forced_initial_height_price >= order['hightPrice']):
                    # Has intersection, need to adjust forced close price
                    forced_close_price = forced_close_price * 1.02
                    print(f"7. Found intersection, adjusting forced close price to: {forced_close_price}")
                    print(f"   Intersecting order: low price {order['lowPrice']}, high price {order['hightPrice']}")
                    print(f"   Current range: low price {forced_final_low_price}, high price {forced_initial_height_price}")
                    # Recalculate
                    is_valid, result = self.calculate_long_open(reserve0, reserve1, baseAmount, lendAmount1, forced_close_price)
                    if not is_valid:
                        return False, "Adjusted forced close price is invalid"
                    forced_initial_height_price = result['forced_initial_height_price']
                    forced_final_low_price = result['forced_final_low_price']
                    has_intersection = True
                    break  # Break inner loop, recheck all orders
            
            if not has_intersection:
                break  # If no intersection, break outer loop
            
            iteration += 1

        if iteration == max_iterations:
            return False, "Unable to find suitable forced close price, reached maximum iterations"

        print(f"8. Found suitable forced close price: {forced_close_price}")

        # 7. Find insertion position
        insert_position = len(long_orders)  # Default insert at end
        insert_order_id = ""  # Default empty string

        for i, order in enumerate(long_orders):
            if forced_close_price > order['hightPrice']:
                insert_position = i
                if i > 0:
                    insert_order_id = long_orders[i-1]['orderID']
                break

        print(f"9. Found insertion position: {insert_position}, insert order ID: {insert_order_id}")

        # 8. Return result
        current_price = self.get_price()
        forced_close_price_moved = forced_close_price * (1 + self.pool.forceMoveRate)
        price_difference_percentage = ((current_price - forced_close_price_moved) / current_price) * 100

        return True, {
            "baseAmount": baseAmount,  # User provided base token amount (USDT)
            "lendAmount1": lendAmount1,  # User borrowed base token amount (USDT)
            "amount0_out": amount0_out,  # Leveraged purchased token amount (token0)
            "forcedClosePrice": forced_close_price,  # Initial forced liquidation price
            "insterOrderID": insert_order_id,  # Insert order ID
            "forcedClosePriceMoved": forced_close_price_moved,  # Moved up forced liquidation price
            "priceDifferencePercentage": price_difference_percentage  # Price difference percentage between moved forced close price and current price
        }

    def calculate_short_open(self, reserve0, reserve1, baseAmount, lendAmount, forcedClosePrice):
        """
        Calculate short open related parameters, check if forced close price is reasonable.

        :param reserve0: Token0 reserve amount
        :param reserve1: Token1 reserve amount
        :param baseAmount: User provided base token amount
        :param lendAmount: User desired borrowed token amount
        :param forcedClosePrice: Forced liquidation price
        :return: (bool, dict) Whether reasonable and related calculation results
        """
        print("b--------Calculate short open calculate_short_open---------")
        print(f"Parameters: reserve0: {reserve0}, reserve1: {reserve1}, base amount: {baseAmount}, borrow amount: {lendAmount}, forced close price: {forcedClosePrice}")

        # Simulate selling borrowed tokens
        sell_amount1_out, sell_fee_amount0, sell_new_reserve0, sell_new_reserve1, sell_initial_price, sell_final_price = get_amount_out_reserve0_to_reserve1(
            lendAmount, reserve0, reserve1, self.pool.fee
        )

        # Calculate all fees
        loan_fee = sell_amount1_out * (1.0 - self.pool.loanFee)  # Loan fee
        loan_day_fee = sell_amount1_out * (1.0 - self.pool.loanDayFee)  # Loan daily interest fee
        forced_close_fee = sell_amount1_out * (1.0 - self.pool.forcedCloseFee)  # Forced liquidation fee
        total_fees = loan_fee + loan_day_fee + forced_close_fee + self.pool.forcedCloseBaseAmount  # Total loan fees

        #realLendAmount = lendAmount - sell_fee_amount0  # Actual borrowed token amount
        print(f"1.Simulate borrowing and selling to get USDT: {sell_amount1_out}, simulate trading fee: {sell_fee_amount0}, borrowed token amount: {lendAmount}, loan fee: {loan_fee}USDT")

        loanReserveAmount = sell_amount1_out + total_fees  # Minimum loan reserve
        
        print(f"2.Daily interest: {loan_day_fee} USDT, liquidation(third party benefit fee): {forced_close_fee} USDT, third party fixed fee: {self.pool.forcedCloseBaseAmount} USDT, total borrowing fee: {total_fees}USDT minimum loan reserve{loanReserveAmount}")
 
        # if baseAmount < loanReserveAmount:
        #     return False, {"message": "Insufficient base tokens to pay all fees"}

        # Move liquidity pool to forced close price (for calculation only, cannot change real liquidity pool)
        forced_reserve0, forced_reserve1 = get_reserves_at_price(forcedClosePrice, reserve0, reserve1)

        # Simulate forced liquidation trade
        forced_amount_in, forced_fee_amount, forced_new_reserve0, forced_new_reserve1, forced_initial_low_price, forced_final_height_price = get_amount_in_reserve1_for_amount0_out(
            lendAmount, forced_reserve0, forced_reserve1, self.pool.fee
        )

        print(f"3. Minimum loan reserve funds: {loanReserveAmount}USDT, liquidation at price: {forcedClosePrice}, buy back needs: {forced_amount_in}USDT, includes fee: {forced_fee_amount}USDT")
        print(f"4. Total funds needed for liquidation: {forced_amount_in + total_fees}, sell coins + collateral: {sell_amount1_out + baseAmount}")

        # Check if liquidation will result in loss
        if forced_amount_in + total_fees >= sell_amount1_out + baseAmount:
            return False, {"message": "Will lose money after liquidation"}

        return True, {
            "sell_amount1_out": sell_amount1_out,
            "total_fees": total_fees,
            "loanReserveAmount": loanReserveAmount,
            "forced_amount_in": forced_amount_in,
            "forced_initial_low_price": forced_initial_low_price,
            "forced_final_height_price": forced_final_height_price
        }
        
        
        
    def calculate_long_open(self, reserve0, reserve1, baseAmount, lendAmount1, forcedClosePrice):
        """
        Calculate long open related parameters, check if forced close price is reasonable.

        :param reserve0: Token0 reserve amount
        :param reserve1: Token1 reserve amount
        :param baseAmount: User provided base token amount (USDT)
        :param lendAmount1: User desired borrowed base token amount (USDT)
        :param forcedClosePrice: Forced liquidation price
        :return: (bool, dict) Whether reasonable and related calculation results
        """
        print("Parameters: use", baseAmount, "USDT as collateral", "borrow", lendAmount1, "USDT", "forced liquidation price", forcedClosePrice)
        if forcedClosePrice >= self.pool.getPrice():
            return False, "Forced liquidation price cannot be greater than current price"
        if forcedClosePrice <= 0:
            return False, "Forced liquidation price cannot equal 0"

        # 2. Check if loan pool has enough lendAmount1 tokens
        if self.pool.loanReserve1 < lendAmount1:
            return False, "Insufficient base tokens in loan pool"

        # 3. Total available base token amount
        total_base_amount = baseAmount + lendAmount1

        # Calculate all fees (based on lendAmount1 borrowed amount)
        loan_fee = lendAmount1 * (1.0 - self.pool.loanFee)  # Loan fee
        loan_day_fee = lendAmount1 * (1.0 - self.pool.loanDayFee)  # Loan daily interest fee
        forced_close_fee = lendAmount1 * (1.0 - self.pool.forcedCloseFee)  # Forced liquidation fee
        total_fees = loan_fee + loan_day_fee + forced_close_fee + self.pool.forcedCloseBaseAmount  # Total loan fees USDT
        # Print fees
        print("1.Loan fee:", loan_fee, "USDT", "daily interest:", loan_day_fee, "USDT", "liquidation(third party benefit fee):", forced_close_fee, "USDT", "third party fixed fee:", self.pool.forcedCloseBaseAmount, "USDT", "total borrowing fee:", total_fees, "USDT")
        
        # 4. Simulate purchase with total_base_amount USDT to get how many tokens
        amount0_out, fee_amount1, new_reserve0, new_reserve1, initial_price, final_price = get_amount_out_reserve1_to_reserve0(
            total_base_amount,self.pool.reserve0, self.pool.reserve1, self.pool.fee
        )
        print("2.Collateral + borrowed:" ,total_base_amount, "USDT can buy tokens (including fee):", amount0_out ,"T" )
        
        # Move liquidity pool to forcedClosePrice (for calculation only, cannot change real liquidity pool)
        forced_reserve0, forced_reserve1 = get_reserves_at_price(forcedClosePrice, self.pool.reserve0, self.pool.reserve1)
        # 5. Simulate forced liquidation trade (sell amount0_out tokens, get forced_amount1_out base tokens)
        forced_amount1_out, forced_fee_amount0, forced_new_reserve0, forced_new_reserve1, forced_initial_height_price, forced_final_low_price = get_amount_out_reserve0_to_reserve1(
            amount0_out, forced_reserve0, forced_reserve1, self.pool.fee
        )
        print("3.Liquidation at price:", forcedClosePrice, "sell tokens get (fee included):", forced_amount1_out, "USDT", "fee:", forced_fee_amount0, "T","no loss after liquidation needs at least:", lendAmount1+total_fees," borrowed USDT+fees")
        # Check if liquidation will result in loss
        if forced_amount1_out + forced_amount1_out < lendAmount1+total_fees:
            return False, {"message": "Will lose money after liquidation"}
        
        return True, {
            "total_base_amount": total_base_amount,  # Total base amount (user provided base tokens + borrowed tokens)
            "total_fees": total_fees,  # Total fees (including loan fees, interest, etc.)
            "amount0_out": amount0_out,  # Amount of token0 user can purchase
            "forced_amount_out": forced_amount1_out,  # Amount of token1 that can be obtained during forced liquidation
            "forced_initial_height_price": forced_initial_height_price,  # Initial price during forced liquidation
            "forced_final_low_price": forced_final_low_price  # Final price after forced liquidation
        }
                
        
    def calculate_profit_loss(self, the_type, baseAmount1, lendAmount1, lendAmount0):
        """
        Calculate profit/loss value
        :param the_type: Trade type, "short" for short, "long" for long
        :param baseAmount1: User provided base token amount (USDT)
        :param lendAmount1: User borrowed base token amount (USDT)
        :param lendAmount0: Token amount
        :return: Profit or loss percentage value
        """
        with self.lock:
            reserve0, reserve1 = self.pool.getReserves()
            current_price = self.pool.getPrice()

            if the_type == "short":
                # Short case
                # Contract buys back lendAmount0 tokens, calculate how much USDT needed
                amount1_in, fee_amount1, new_reserve0, new_reserve1, initial_low_price, final_height_price = get_amount_in_reserve1_for_amount0_out(
                    lendAmount0, reserve0, reserve1, self.pool.fee
                )
                # 3. Calculate profit/loss
                profit_loss =  lendAmount1 - amount1_in
            elif the_type == "long":
                # 2. Simulate selling all tokens
                sell_amount1_out, _, _, _, _, _ = get_amount_out_reserve0_to_reserve1(
                    lendAmount0, reserve0, reserve1, self.pool.fee
                )
                # 3. Calculate profit/loss
                profit_loss =  sell_amount1_out - (baseAmount1 + lendAmount1)
            else:
                raise ValueError("Invalid trade type. Must be 'short' or 'long'.")

            # Calculate profit/loss percentage
            initial_investment = baseAmount1
            profit_loss_percentage = (profit_loss / initial_investment) * 100
            
            return profit_loss_percentage
        