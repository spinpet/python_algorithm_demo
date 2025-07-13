# File name: shortswapv1pool.py

import random
import string
from erc20factory import erc20_factory_instance
from swap_utils import get_current_price,get_amount_in_reserve1_for_amount0_out,get_amount_in_reserve0_for_amount1_out, get_amount_out_reserve0_to_reserve1, get_amount_out_reserve1_to_reserve0, get_reserves_at_price
from shortswapv1order import ShortSwapV1Order
import time

class ShortSwapV1Pool(ShortSwapV1Order):
    def __init__(self, factory, token0, token1, token0TotalSupply, token0ShortSupply, token1Amount,  poolAddress):
        """
        Initialize ShortSwapV1Pool instance.
        """
        ShortSwapV1Order.__init__(self)  # Call parent class initialization method
        self.factory = factory  # Factory
        self.token0 = token0    # Token0 address
        self.token1 = token1    # Token1 USDT address
        self.poolAddress = poolAddress # Pool contract address (not needed in contract environment)
    
        self.token0TotalSupply = token0TotalSupply # Token total supply  (recorded only, not used)
        self.token0ShortSupply = token0ShortSupply # Short pool total supply  (recorded only, not used)
        self.token0InitialAmount = token0TotalSupply - token0ShortSupply # Token0 initial amount  (recorded only, not used)
        
        self.reserve0 = self.token0InitialAmount # Token0 amount in liquidity pool
        self.reserve1 = token1Amount  # Token1 amount in liquidity pool
        
        self.loanReserve0 = token0ShortSupply # Token0 loan reserve amount
        self.loanReserve1 = 100000 # Token1 loan reserve amount (USDT)
        self.loanFee = 0.99 #  Basic loan fee
        self.loanDayFee = 0.9995 #  Basic loan daily interest fee
        self.forcedCloseFee = 0.995 #  Forced liquidation fee (third party benefit fee)
        self.forcedCloseBaseAmount = 5 # Forced liquidation base token amount charged (third party benefit fee)
        
        self.collateralShortAmount1 = 0 # Short collateral total amount (USDT)    
        self.collateralLongAmount1 = 0 # Long collateral total amount (USDT)   
        
        self.fee = 0.997 # Trading fee
        self.feeAddress = "0xFeeAddress" # Fee address
        
        self.leverageLimit = 5 # Maximum leverage ratio
        self.lendingSecondLimit = 60*15 # Maximum lending time (seconds) after which third party liquidation is allowed
        
        # Liquidation movement ratio - this value is crucial, relates to maximum position size per trade
        self.forceMoveRate = 0.10 # Forced liquidation line movement ratio (this value can be appropriately reduced when pool grows)
        self.forceMoveSlack = self.forceMoveRate*0.5  # Minimum price requirement for partial liquidation (prevents users from liquidating one token at a time)
        
        self.current_address = ""  # Current address (not needed in contract environment)
        
    def use(self, address):
        self.current_address = address
        return self
    
    def getInfo(self):
        """
        Get all attribute information of current pool and return in JSON format.
        """
        import json  # Import JSON module
        
        # Create a dictionary containing all attributes (except self.factory)
        info = {
            "token0": self.token0,  # Token0 address
            "token1": self.token1,  # Token1 address
            "poolAddress": self.poolAddress,  # Pool contract address
            "token0TotalSupply": self.token0TotalSupply,  # Token total supply
            "token0ShortSupply": self.token0ShortSupply,  # Short pool total supply
            "token0InitialAmount": self.token0InitialAmount,  # Token0 initial amount
            "reserve0": self.reserve0,  # Token0 amount in liquidity pool
            "reserve1": self.reserve1,  # Token1 amount in liquidity pool
            "loanReserve0": self.loanReserve0,  # Token0 loan reserve amount
            "loanReserve1": self.loanReserve1,  # Token1 loan reserve amount
            "loanFee": self.loanFee,  # Basic loan fee
            "loanDayFee": self.loanDayFee,  # Basic loan daily interest fee
            "forcedCloseFee": self.forcedCloseFee,  # Forced liquidation fee
            "forcedCloseBaseAmount": self.forcedCloseBaseAmount,  # Forced liquidation base token amount charged
            "collateralShortAmount1": self.collateralShortAmount1,  # Short collateral total amount
            "collateralLongAmount1": self.collateralLongAmount1,  # Long collateral total amount
            "fee": self.fee,  # Trading fee
            "feeAddress": self.feeAddress,  # Fee address
            "leverageLimit": self.leverageLimit,  # Maximum leverage ratio
            "forceMoveRate": self.forceMoveRate,  # Forced liquidation line movement ratio
            "current_address": self.current_address  # Current address
        }
        
        # Return JSON format string
        return json.dumps(info, ensure_ascii=False)  # Ensure Chinese characters display properly
        
    def getReserves(self):
        return self.reserve0, self.reserve1
    

    def getPrice(self):
        """
        Get current price
        """
        return get_current_price(self.reserve0, self.reserve1)
    
    def buy(self, amount1):
        """
        Buy operation
        """
        print("---------------buy------------------Current price:", self.getPrice())
        # Check if user has enough token1 (USDT)
        user_balance = erc20_factory_instance.balanceOf(self.token1, self.current_address)
        if user_balance < amount1:
            return False, "Insufficient USDT balance"

        # Calculate price movement range
        amount0_out, fee_amount1, new_reserve0, new_reserve1, initial_low_price, final_height_price = get_amount_out_reserve1_to_reserve0(
            amount1, self.reserve0, self.reserve1, self.fee
        )
        
        # Check if price movement range exceeds self.forceMoveRate
        price_change_rate = (final_height_price - initial_low_price) / initial_low_price
        print(f"1.Calculate buy impact on price range {initial_low_price} to {final_height_price} price movement: {price_change_rate:.3%}")
        if price_change_rate > self.forceMoveRate:
            return False, f"Price movement {price_change_rate:.3%} exceeds maximum single trade volatility {self.forceMoveRate:.3%}"

        # Check if price range intersects with liquidation orders
        is_valid, message = self.checkShortOrderRange(final_height_price, initial_low_price)
        print("2.Calculate buy impact on price range",initial_low_price, "to",final_height_price,"no intersection with short liquidation:",is_valid)
        if is_valid == False:
            return False, "Intersects with short liquidation, please liquidate first"
        
        # Start buying
        self.reserve0 = new_reserve0
        self.reserve1 = new_reserve1

        # Send purchased tokens to user address
        success, message = erc20_factory_instance.use(self.poolAddress).transfer(self.token0, self.current_address, amount0_out)
        if not success:
            return False, message
        # Send USDT to contract address
        success, message = erc20_factory_instance.use(self.current_address).transfer(self.token1, self.poolAddress, amount1)
        if not success:
            return False, message
        # 3. Send fee_amount1 to self.feeAddress
        success, message = erc20_factory_instance.use(self.poolAddress).transfer(self.token1, self.feeAddress, fee_amount1)
        if not success:
            return False, message

        print("3.Use USDT amount:",amount1, "buy", amount0_out, "tokens", "fee:", fee_amount1, "USDT", "price after buy:", self.getPrice())
        # Return check result
        return is_valid, message
    
    
    
    def sell(self, amount0):
        """
        Sell operation
        """
        print("---------------sell------------------Current price:", self.getPrice())
        
        # Check if user has enough token0
        user_balance = erc20_factory_instance.balanceOf(self.token0, self.current_address)
        if user_balance < amount0:
            return False, "Insufficient token balance"

        # Calculate price movement range
        amount_out, fee_amount0, new_reserve0, new_reserve1, initial_height_price, final_low_price = get_amount_out_reserve0_to_reserve1(
            amount0, self.reserve0, self.reserve1, self.fee
        )
        # Check if price movement range exceeds self.forceMoveRate
        price_change_rate = (initial_height_price - final_low_price) / initial_height_price
        print(f"1.Calculate sell impact on price range {initial_height_price} to {final_low_price} price movement: {price_change_rate:.3%}")
        if price_change_rate > self.forceMoveRate:
            return False, f"Price movement {price_change_rate:.3%} exceeds maximum single trade volatility {self.forceMoveRate:.3%}"
        
        # Check if price range intersects with liquidation orders
        is_valid, message = self.checkLongOrderRange(initial_height_price, final_low_price)
        print("1.Calculate sell impact on price range", initial_height_price, "to", final_low_price, "no intersection with long liquidation:", is_valid)
        if not is_valid:
            return False, "Intersects with long liquidation, please liquidate first"
        
        # Start selling
        self.reserve0 = new_reserve0
        self.reserve1 = new_reserve1
        # 3. Send fee_amount to self.feeAddress
        success, message = erc20_factory_instance.use(self.poolAddress).transfer(self.token0, self.feeAddress, fee_amount0)
        if not success:
            return False, message
        # Send sold tokens to user address
        success, message = erc20_factory_instance.use(self.poolAddress).transfer(self.token1, self.current_address, amount_out)
        if not success:
            return False, message
        # Send token0 to contract address
        success, message = erc20_factory_instance.use(self.current_address).transfer(self.token0, self.poolAddress, amount0)
        if not success:
            return False, message
        print("2.Use token amount:", amount0, "sell for", amount_out, "USDT", "fee:", fee_amount0, "T", "price after sell:", self.getPrice())
        # Return check result
        return is_valid, message
    

    def shortOpen(self, baseAmount1, lendAmount0, forcedClosePrice, insterOrderID):
        """
        Short operation
        :param baseAmount1: User provided base token amount
        :param lendAmount0: User desired borrowed token amount
        :param forcedClosePrice: Forced liquidation price
        :param insterOrderID: Insert to liquidation order queue ID (needs to be obtained off-chain)
        """
        print("---------Short open shortOpen--------- Current price:", self.getPrice())
        # ------------Pre-check section----------------
        print("Parameters: use",baseAmount1,"USDT as collateral", "borrow", lendAmount0, "tokens", "forced liquidation price", forcedClosePrice, "insert liquidation order linked list position:", insterOrderID)
        
        if forcedClosePrice <= self.getPrice():
            return False, "Forced liquidation price cannot be less than current price"

        # 1. Check if user address has enough baseAmount token1 tokens
        user_balance = erc20_factory_instance.balanceOf(self.token1, self.current_address)
        if user_balance < baseAmount1:
            return False, "Insufficient wallet balance"

        # 2. Check if loan pool has enough lendAmount0 tokens
        if self.loanReserve0 < lendAmount0:
            return False, "Insufficient tokens in loan pool"

        # 3. Simulate selling borrowed coins (if conditions not met, don't actually sell) use get_amount_out_reserve0_to_reserve1 to calculate how much USDT can be obtained by selling lendAmount0 coins (this serves as the base price for this order, used to calculate fees, equivalent to calculating how much USDT can be obtained by immediately selling after borrowing)
        sell_amount1, sell_fee_amount0, sell_new_reserve0, sell_new_reserve1, initial_height_price, final_low_price = get_amount_out_reserve0_to_reserve1(
            lendAmount0, self.reserve0, self.reserve1, self.fee # fee is 0
        )
        
        # Check if price movement range exceeds self.forceMoveRate
        price_change_rate = (initial_height_price - final_low_price) / initial_height_price
        print(f"1.Calculate sell impact on price range {initial_height_price} to {final_low_price} price movement: {price_change_rate:.3%}")
        if price_change_rate > self.forceMoveRate:
            return False, f"Price movement {price_change_rate:.3%} exceeds maximum single trade volatility {self.forceMoveRate:.3%}"

        # Check if price range intersects with liquidation orders
        is_valid, message = self.checkLongOrderRange(initial_height_price, final_low_price)
        print("1.Calculate sell impact on price range", initial_height_price, "to", final_low_price, "no intersection with short liquidation:", is_valid)
        if not is_valid:
            return False, "Intersects with long liquidation, please liquidate first"

        # Calculate all fees
        loan_fee = sell_amount1 * (1.0 - self.loanFee)  # Loan fee
        loan_day_fee = sell_amount1 * (1.0 - self.loanDayFee)  # Loan daily interest fee
        forced_close_fee = sell_amount1 * (1.0 - self.forcedCloseFee)  # Third party liquidation ratio fee
        third_fee = forced_close_fee + self.forcedCloseBaseAmount  # Total third party liquidation fee
        total_fees = loan_fee + loan_day_fee + third_fee  # Total loan fees

        #realLendAmount = lendAmount0 - sell_fee_amount0  # Actual borrowed token amount
        # Print fees
        print("2.Simulate borrowing and selling to get USDT:", sell_amount1, "simulate trading fee:", sell_fee_amount0,"T actual borrowed token amount:", lendAmount0,"loan fee:",loan_fee,"USDT")
        loanReserveAmount = sell_amount1 + total_fees # Minimum loan reserve
        print(f"3.Daily interest: {loan_day_fee} USDT, liquidation(third party benefit fee): {forced_close_fee} USDT, third party total fee: {third_fee} USDT, total borrowing fee: {total_fees}USDT minimum loan reserve{loanReserveAmount}USDT")

        # Move liquidity pool to liquidation price (for calculation only, cannot change real liquidity pool)
        forced_reserve0, forced_reserve1 = get_reserves_at_price(forcedClosePrice, self.reserve0, self.reserve1)
        # Simulate liquidation trade
        forced_amount_in, forced_fee_amount, forced_new_reserve0, forced_new_reserve1, forced_initial_low_price, forced_final_height_price = get_amount_in_reserve1_for_amount0_out(
            lendAmount0, forced_reserve0, forced_reserve1, self.fee
        )
        
        print("4.Minimum loan reserve fund:"+ str(loanReserveAmount) +"USDT", "liquidation at price:",forcedClosePrice,"buy back needs:" ,forced_amount_in,"USDT" " includes fee:", forced_fee_amount,"USDT")
        print("5.Total funds needed for liquidation:", forced_amount_in + total_fees, "USDT from selling coins + collateral:", sell_amount1+baseAmount1)
        
        # Check if liquidation will result in loss
        if forced_amount_in + total_fees >= sell_amount1+baseAmount1:
            return False, "Will lose money after liquidation"
        
        # ------------Check section successful, actual trading section begins----------------
        # Create orderNode and insert
        orderNode = {
            # Linked list section
            'orderID': self.generateOrderID("short"),
            'hightPrice': forced_final_height_price,  # Highest price after forced liquidation
            'lowPrice': forced_initial_low_price,  # Lowest price after forced liquidation
            'address': self.current_address,  # Current user address
            'hightNode': "",  # Previous node
            'lowNode': "",  # Next node
            # Data section
            'orderType': "short",
            'baseAmount1': baseAmount1,  # User collateral base token amount
            'sell_amount1': sell_amount1,  # USDT obtained from selling borrowed coins
            'lendAmount0': lendAmount0,  # User borrowed token amount
            'forcedClosePrice': forcedClosePrice,  # Forced liquidation price
            'loan_fee': loan_fee,  # Basic loan fee
            'loan_day_fee': loan_day_fee,  # Loan daily interest fee
            'third_fee': third_fee,  # Third party liquidation benefit fee (total)
            'loan_time': int(time.time()),  # Opening timestamp
            'openPrice': self.getPrice(),  # Opening price
            #Debug section
            'insterOrderID': insterOrderID  # Insert liquidation order queue ID (for debugging)
        }

        # Insert liquidation order
        success, message = self.insterShortOrder(orderNode, insterOrderID)
        if not success:
            return False, message

        # 1. Subtract lendAmount0 borrowed coins from self.loanReserve0
        self.loanReserve0 -= lendAmount0

        # Directly use simulated selling of borrowed coins data to update liquidity pool
        self.reserve0 = sell_new_reserve0
        self.reserve1 = sell_new_reserve1
        

        # Send collateral baseAmount1 to self.poolAddress
        success, message = erc20_factory_instance.use(self.current_address).transfer(self.token1, self.poolAddress, baseAmount1)
        if not success:
            return False, message
        
        # 3. Send fee_amount to self.feeAddress
        success, message = erc20_factory_instance.use(self.poolAddress).transfer(self.token0, self.feeAddress, sell_fee_amount0)
        if not success:
            return False, message
        
        print("6.Real trading begins, deduct borrowed coins from loan pool loanReserve0 and sell:",lendAmount0," remaining:",self.loanReserve0, "fee transfer:",sell_fee_amount0,"T"  )
       
        
        
        #  Update collateral variable (user's + borrowed coin sales proceeds)
        self.collateralShortAmount1 += baseAmount1 + sell_amount1
        #print('shortOpen hightPrice=', forced_final_price,'lowPrice', forced_initial_price)
        print("7.Collateral transferred to loan pool:",baseAmount1,"USDT", "collateral in lending increased to:",self.collateralShortAmount1, "USDT", "all orders for this address:", self.getOrderIDsByAddress(self.current_address))
        return True, "Short operation successful"

                
    def shortClose(self, orderID, closeAmount0, isThirdParty=False):
        """
        User liquidation operation (including third party liquidation)
        """
        print("---------User short position liquidation shortClose--------- Current price:", self.getPrice(),"calling address:",self.current_address)
        if closeAmount0 == 0:
            return False, "Liquidation amount cannot be 0"
        # 1. Check if orderID exists in self.orderShortMap
        if orderID not in self.orderShortMap:
            return False, "Order ID does not exist"
        order = self.orderShortMap[orderID]
        
        if isThirdParty:
            # Need to check if liquidation line reached or lending time exceeded limit
            current_price = self.getPrice()
            current_time = int(time.time())
            threshold_price = order['forcedClosePrice'] * (1 - self.forceMoveRate)
            time_exceeded = (current_time - order['loan_time']) > self.lendingSecondLimit
            if current_price < threshold_price and not time_exceeded:
                return False, "Liquidation price conditions not met and lending time not exceeded"
            if current_price >= threshold_price:
                print(f"1.Liquidation line reached  price: {current_price}, liquidation order price{order['forcedClosePrice']}  liquidation threshold (will float down): {threshold_price}")
            if time_exceeded:
                print(f"1.Lending time exceeded limit  current time: {current_time}, opening time: {order['loan_time']}, lending time limit: {self.lendingSecondLimit}seconds")
        else:
            # Check if address in data matches self.current_address
            if order['address'] != self.current_address:
                return False, "Order address does not match current address"
        
        # 2. Check if orderID orderType is short
        if order['orderType'] != "short":
            return False, "Order type is not short"
        
        # 3. Execute buy operation buy lendAmount0 amount of tokens
        lendAmount0 = order['lendAmount0']   # Amount of tokens to buy for repayment
        if lendAmount0 < closeAmount0:
            return False, "Liquidation amount cannot exceed borrowed token amount"
        
        # For partial liquidation, need to check if full liquidation exceeds maximum liquidation range, if not, can only fully liquidate
        if closeAmount0 != lendAmount0:
            # Contract buys back order['lendAmount0'] tokens, calculate price movement
            _, _, _, _, check_initial_low_price, check_final_height_price = get_amount_in_reserve1_for_amount0_out(
                order['lendAmount0'], self.reserve0, self.reserve1, self.fee
            )
            price_change_rate = (check_final_height_price - check_initial_low_price) / check_initial_low_price
            print(f"1.1.Calculate buy impact on price range {check_initial_low_price} to {check_final_height_price} price movement: {price_change_rate:.3%}")
            if price_change_rate <= self.forceMoveRate:
                return False, f"Full liquidation price movement {price_change_rate:.3%} does not exceed maximum single trade volatility {self.forceMoveRate:.3%}, this order cannot be partially liquidated"

            _, _, _, _, check_close_initial_low_price, check_close_final_height_price = get_amount_in_reserve1_for_amount0_out(
                closeAmount0, self.reserve0, self.reserve1, self.fee
            )
            price_close_change_rate = (check_close_final_height_price - check_close_initial_low_price) / check_close_initial_low_price
            print(f"1.2.Calculate buy impact on price range {check_close_initial_low_price} to {check_close_final_height_price} price movement: {price_close_change_rate:.3%}")
            if price_close_change_rate < self.forceMoveSlack:
                return False, f"Partial liquidation range cannot be too small {price_close_change_rate:.3%} does not meet partial liquidation requirement {self.forceMoveSlack:.3%}"


        
        # Calculate batch liquidation ratio
        close_rate = closeAmount0 / lendAmount0
        print("0.Batch liquidation ratio:",close_rate)
        
        
        # Reduce various parameters proportionally
        closeBaseAmount = order['baseAmount1'] * close_rate # User collateral base token amount
        close_sell_amount1 =  order['sell_amount1'] * close_rate      # USDT obtained from selling borrowed coins
        close_loan_fee = order['loan_fee'] * close_rate  # Loan fee
        close_loan_day_fee = order['loan_day_fee'] * close_rate  # Loan daily interest
        close_third_fee = 0 # Total third party liquidation fee
        if isThirdParty:
            close_third_fee = order['third_fee'] * close_rate # Total third party liquidation fee


        # Contract buys back lendAmount0 tokens, calculate how much USDT needed
        amount1_in, fee_amount1, new_reserve0, new_reserve1, initial_low_price, final_height_price = get_amount_in_reserve1_for_amount0_out(
            closeAmount0, self.reserve0, self.reserve1, self.fee
        )
        
        print("1.Repurchase:",closeAmount0,"tokens cost",amount1_in,"USDT(fee included)", "fee:", fee_amount1,"USDT")
        
        # Check partial liquidation, price movement cannot be too small
        if closeAmount0 != lendAmount0:
            price_change_rate = (final_height_price - initial_low_price) / initial_low_price
            if price_change_rate < self.forceMoveSlack:
                return False, f"Partial liquidation range cannot be too small {price_change_rate:.3%} does not meet partial liquidation requirement {self.forceMoveSlack:.3%}"
            
        
        # Check if price range intersects with liquidation orders
        is_valid, message = self.checkShortOrderRange(final_height_price, initial_low_price,orderID)
        print("2.Calculate buy impact on price range", initial_low_price, "to", final_height_price, "no intersection with short liquidation:", is_valid)
        if not is_valid:
            return False, "Intersects with short liquidation, please liquidate first"
        
        
        # Start buying
        self.reserve0 = new_reserve0
        self.reserve1 = new_reserve1

        print("3.User's collateral + borrowed coin sales proceeds:", closeBaseAmount ,"USDT +", close_sell_amount1 ,"USDT =", closeBaseAmount +  close_sell_amount1 ,"USDT")
        closeAmount1 = (closeBaseAmount + close_sell_amount1) - amount1_in
        loanFeeAmount = close_loan_fee + close_loan_day_fee  # Loan fee + daily interest
        refundAmount = closeAmount1 - loanFeeAmount - close_third_fee
        
        
        # # 3. Send fee_amount1 to self.feeAddress (transfer from contract address)
        all_fee_amount1 = fee_amount1 + loanFeeAmount
        success, message = erc20_factory_instance.use(self.poolAddress).transfer(self.token1, self.feeAddress, all_fee_amount1)
        if not success:
            return False, message
        
        print("4.User's balance after liquidation:", closeAmount1,"USDT", "actual refund:",refundAmount,"USDT","interest collected:",loanFeeAmount,"USDT")
        # Return borrowed tokens
        self.loanReserve0 += closeAmount0
        print("5.Return borrowed tokens:",closeAmount0,"USDT", "loan pool loanReserve0 increased to:",self.loanReserve0,"USDT","user profit/loss%: {:.2f}%".format((closeAmount1 - closeBaseAmount)/closeBaseAmount*100))
        # Return remaining USDT to user
        success, message = erc20_factory_instance.use(self.poolAddress).transfer(self.token1, order['address'], refundAmount)
        if not success:
            return False, message
        if isThirdParty:
            # Third party liquidation benefit fee to third party
            success, message = erc20_factory_instance.use(self.poolAddress).transfer(self.token1, self.current_address, close_third_fee)
            if not success:
                return False, message

        # Decide whether to delete order or modify order
        if closeAmount0 == lendAmount0:
            # Delete order
            
            # Add closing data
            order['closePrice'] = self.getPrice()
            order['closeTimestamp'] = int(time.time())
            closeType = ""
            if isThirdParty:
                closeType = "Third party liquidation"
            else:
                closeType = "User active liquidation"
            order['closeType'] = closeType
            order['profitLoss'] = refundAmount - order['baseAmount1']
            order['petLoss'] = (refundAmount - order['baseAmount1']) / order['baseAmount1']
            
            success, message =  self.deleteShortOrder(orderID)
            if not success:
                return False, message
            print("6.Return remaining USDT to user:",refundAmount,"USDT","and delete order:",orderID,"all orders for this address:", self.getOrderIDsByAddress(self.current_address))

    
    
        else:
            # Modify order - subtract liquidated portion
            order['baseAmount1'] =  order['baseAmount1'] - closeBaseAmount   #Here need to add back third party liquidation benefit fee
            order['sell_amount1'] = order['sell_amount1'] - close_sell_amount1
            order['third_fee'] = order['third_fee'] - close_third_fee
            order['loan_fee'] = order['loan_fee'] - close_loan_fee
            order['loan_day_fee'] = order['loan_day_fee'] - close_loan_day_fee
            order['lendAmount0'] = order['lendAmount0'] - closeAmount0
            # Move liquidity pool to liquidation price (for calculation only, cannot change real liquidity pool)
            forced_reserve0, forced_reserve1 = get_reserves_at_price(order['forcedClosePrice'], self.reserve0, self.reserve1)
            # Simulate liquidation trade
            forced_amount_in, forced_fee_amount, forced_new_reserve0, forced_new_reserve1, forced_initial_low_price, forced_final_height_price = get_amount_in_reserve1_for_amount0_out(
                order['lendAmount0'], forced_reserve0, forced_reserve1, self.fee
            )
            # Release liquidation required locked liquidity
            order['hightPrice'] = forced_final_height_price
            order['lowPrice'] = forced_initial_low_price
            
            print("6.Return remaining USDT to user:",refundAmount,"USDT","modify order:",orderID,"all orders for this address:", self.getOrderIDsByAddress(self.current_address))

        return True, "Liquidation successful"
                
    

    def longOpen(self, baseAmount1, lendAmount1, forcedClosePrice, insterOrderID):
        """
        Long operation
        :param baseAmount1: User provided base token amount (USDT)
        :param lendAmount1: User desired borrowed base token amount (USDT)
        :param forcedClosePrice: Forced liquidation price
        :param insterOrderID: Insert to liquidation order queue ID (needs to be obtained off-chain)
        """
        print("---------Long open longOpen--------- Current price:", self.getPrice())
        # ------------Pre-check section----------------
        print("Parameters: use", baseAmount1, "USDT as collateral", "borrow", lendAmount1, "USDT", "forced liquidation price", forcedClosePrice, "insert liquidation order linked list position:", insterOrderID)
        if forcedClosePrice >= self.getPrice():
            return False, "Forced liquidation price cannot be greater than current price"
        if forcedClosePrice <= 0:
            return False, "Forced liquidation price cannot equal 0"
        # 1. Check if user address has enough baseAmount1 token1 tokens
        user_balance = erc20_factory_instance.balanceOf(self.token1, self.current_address)
        if user_balance < baseAmount1:
            return False, "Insufficient wallet balance"

        # 2. Check if loan pool has enough lendAmount1 tokens
        if self.loanReserve1 < lendAmount1:
            return False, "Insufficient base tokens in loan pool"

        # 3. Total available base token amount
        total_base_amount = baseAmount1 + lendAmount1

        # Calculate all fees (based on lendAmount1 borrowed amount)
        loan_fee = lendAmount1 * (1.0 - self.loanFee)  # Loan fee
        loan_day_fee = lendAmount1 * (1.0 - self.loanDayFee)  # Loan daily interest fee       
        forced_close_fee = lendAmount1 * (1.0 - self.forcedCloseFee)  # Forced liquidation fee
        third_fee = forced_close_fee + self.forcedCloseBaseAmount  # Total third party liquidation fee
        total_fees = loan_fee + loan_day_fee + third_fee  # Total loan fees USDT
        # Print fees
        print("1.Loan fee:", loan_fee, "USDT", "daily interest:", loan_day_fee, "USDT", "liquidation(third party benefit fee):", forced_close_fee, "USDT", "third party total fee:", third_fee, "USDT", "total borrowing fee:", total_fees, "USDT")
        
        # 4. Simulate purchase to get how many tokens
        buy_amount0, fee_amount1, new_reserve0, new_reserve1, initial_low_price, final_height_price = get_amount_out_reserve1_to_reserve0(
            total_base_amount,self.reserve0, self.reserve1, self.fee
        )
        print("2.Collateral + borrowed:" ,total_base_amount, "USDT can buy tokens (including fee):", buy_amount0 ,"T" )
        
        # Check if price movement range exceeds self.forceMoveRate
        price_change_rate = (final_height_price - initial_low_price) / initial_low_price
        print(f"1.Calculate buy impact on price range {initial_low_price} to {final_height_price} price movement: {price_change_rate:.3%}")
        if price_change_rate > self.forceMoveRate:
            return False, f"Price movement {price_change_rate:.3%} exceeds maximum single trade volatility {self.forceMoveRate:.3%}"

        print("3.1 Buy price range:", initial_low_price, "to", final_height_price)
        # Check if price range intersects with liquidation orders
        is_valid, message = self.checkShortOrderRange(final_height_price, initial_low_price )
        print("4.Calculate buy impact on price range", initial_low_price, "to", final_height_price, "no intersection with short liquidation:", is_valid)
        if not is_valid:
            return False, "Intersects with short liquidation, please liquidate first"


        # Move liquidity pool to forcedClosePrice (for calculation only, cannot change real liquidity pool)
        forced_reserve0, forced_reserve1 = get_reserves_at_price(forcedClosePrice, self.reserve0, self.reserve1)
        # 5. Simulate liquidation trade (sell buy_amount0 tokens, get forced_amount1_out base tokens)
        forced_amount1_out, forced_fee_amount0, forced_new_reserve0, forced_new_reserve1, forced_initial_height_price, forced_final_low_price = get_amount_out_reserve0_to_reserve1(
            buy_amount0, forced_reserve0, forced_reserve1, self.fee
        )
        print("3.Liquidation at price:", forcedClosePrice, "sell tokens get (fee included):", forced_amount1_out, "USDT", "fee:", forced_fee_amount0, "T","no loss after liquidation needs at least:", lendAmount1+total_fees," borrowed USDT + fees")
        # Calculate whether liquidation will result in loss
        if forced_amount1_out + forced_amount1_out < lendAmount1+total_fees:
            return False, "Will lose money after liquidation"
        

        
        # ------------Check section successful, actual trading section begins----------------
        # Create orderNode and insert
        orderNode = {
            'orderID': self.generateOrderID("long"),  # Generate order ID
            'hightPrice': forced_initial_height_price,  # Highest price after forced liquidation
            'lowPrice': forced_final_low_price,  # Lowest price after forced liquidation
            'address': self.current_address,  # Current user address
            'hightNode': "",  # Previous node
            'lowNode': "",  # Next node
            'orderType': "long",  # Order type is long
            'baseAmount1': baseAmount1,  # User provided base token amount (USDT)
            'lendAmount1': lendAmount1,  # User borrowed base token amount (USDT)
            'buy_amount0': buy_amount0, # Purchased token amount (important data)
            'forcedClosePrice': forcedClosePrice,  # Forced liquidation price
            'loan_fee': loan_fee,  # Basic loan fee
            'loan_day_fee': loan_day_fee,  # Loan daily interest fee
            'third_fee': third_fee,  # Total third party liquidation fee
            'loan_time': int(time.time()),  # Opening timestamp
            'openPrice': self.getPrice(),  # Opening price
            'insterOrderID': insterOrderID  # Insert liquidation order queue ID (for debugging)
        }
        # Insert liquidation order
        success, message = self.insterLongOrder(orderNode, insterOrderID)
        if not success:
            return False, message
        
        # 1. Subtract lendAmount1 borrowed coins from self.loanReserve1
        self.loanReserve1 -= lendAmount1

        # 2. Update liquidity pool (use simulated purchase operation data above)
        self.reserve0 = new_reserve0
        self.reserve1 = new_reserve1



        # Send collateral baseAmount1 to self.poolAddress
        success, message = erc20_factory_instance.use(self.current_address).transfer(self.token1, self.poolAddress, baseAmount1)
        if not success:
            return False, message
        
        # 3. Send fee_amount1 to self.feeAddress
        success, message = erc20_factory_instance.use(self.poolAddress).transfer(self.token1, self.feeAddress, fee_amount1)
        if not success:
            return False, message
        
        print("6.Real trading completed, collateral buy tokens:", buy_amount0, "pieces", "collateral base tokens:", baseAmount1, "USDT", "trading fee:", fee_amount1, "USDT")
        
        
        # Update collateral variable
        self.collateralLongAmount1 += baseAmount1

        print("7.Collateral transferred to loan pool:", baseAmount1, "USDT", "collateral in lending increased to:", self.collateralLongAmount1, "USDT", "all orders for this address:", self.getOrderIDsByAddress(self.current_address))

        return True, "Long operation successful"



    def longClose(self, orderID,closeAmount0,isThirdParty=False):
        """
        Long liquidation operation
        """
        print("---------User long position liquidation longClose--------- Current price:", self.getPrice(),"orderID:",orderID,"calling address:",self.current_address)
        if closeAmount0 == 0:
            return False, "Liquidation amount cannot be 0"
        
        # 1. Check if orderID exists in self.orderLongMap
        if orderID not in self.orderLongMap:
            return False, "Order ID does not exist"
        order = self.orderLongMap[orderID]
        
        if isThirdParty:
            # Need to check if liquidation line reached or lending time exceeded limit
            current_price = self.getPrice()
            current_time = int(time.time())
            threshold_price = order['forcedClosePrice'] * (1 + self.forceMoveRate)
            time_exceeded = (current_time - order['loan_time']) > self.lendingSecondLimit
            #print(current_price , threshold_price)
            if current_price > threshold_price and not time_exceeded:
                return False, "Liquidation price conditions not met and lending time not exceeded"
            if current_price <= threshold_price:
                print(f"1.Liquidation line reached  price: {current_price}, liquidation order price{order['forcedClosePrice']}  liquidation threshold (will float up): {threshold_price}")
            if time_exceeded:
                print(f"1.Lending time exceeded limit  current time: {current_time}, opening time: {order['loan_time']}, lending time limit: {self.lendingSecondLimit}seconds")
        else:
            # Check if address in data matches self.current_address
            if order['address'] != self.current_address:
                return False, "Order address does not match current address"

        # 3. Execute sell operation sell buy_amount0 amount of tokens
        buy_amount0 = order['buy_amount0']  # Amount of tokens to sell
        if buy_amount0 < closeAmount0:
            return False, "Liquidation amount exceeds order amount"
        
        # For partial liquidation, need to check if full liquidation exceeds maximum liquidation range, if not, can only fully liquidate
        if closeAmount0 != buy_amount0:
            # Calculate price movement for selling all
            _, _, _, _, check_initial_height_price, check_final_low_price = get_amount_out_reserve0_to_reserve1(
                buy_amount0, self.reserve0, self.reserve1, self.fee
            )
            price_change_rate = (check_initial_height_price - check_final_low_price) / check_initial_height_price
            print(f"1.2.Calculate sell impact on price range {check_initial_height_price} to {check_final_low_price} price movement: {price_change_rate:.3%}")
            if price_change_rate <= self.forceMoveRate:
                return False, f"Full liquidation price movement {price_change_rate:.3%} does not exceed maximum single trade volatility {self.forceMoveRate:.3%}, this order cannot be partially liquidated"

        close_rate = closeAmount0 / buy_amount0
        print("0.Batch liquidation ratio:",close_rate)
        # Reduce various parameters proportionally
        close_loan_fee = order['loan_fee'] * close_rate
        close_loan_day_fee = order['loan_day_fee'] * close_rate
        close_lendAmount1 = order['lendAmount1'] * close_rate
        close_third_fee = 0 # Total third party liquidation fee
        if isThirdParty:
            close_third_fee = order['third_fee'] * close_rate # Total third party liquidation fee
        
        # Calculate selling closeAmount0 tokens to get how much USDT
        amount1_out, fee_amount1, new_reserve0, new_reserve1, initial_height_price, final_low_price = get_amount_out_reserve0_to_reserve1(
            closeAmount0, self.reserve0, self.reserve1, self.fee
        )
        print("1.Repurchase:", closeAmount0, "tokens get", amount1_out, "USDT(fee included)", "fee:", fee_amount1, "T")
        
        if closeAmount0 != buy_amount0:
            price_close_change_rate = (initial_height_price - final_low_price) / initial_height_price
            print(f"1.3.Calculate sell impact on price range {initial_height_price} to {final_low_price} price movement: {price_close_change_rate:.3%}")
            if price_close_change_rate < self.forceMoveSlack:
                return False, f"Partial liquidation price movement {price_close_change_rate:.3%} too small, price volatility must be greater than {self.forceMoveSlack:.3%}"

        # Check if price range intersects with liquidation orders
        is_valid, message = self.checkLongOrderRange(initial_height_price,final_low_price,orderID)
        print("2.Calculate sell impact on price range", initial_height_price, "to", final_low_price, "no intersection with long liquidation:", is_valid)
        if not is_valid:
            return False, "Intersects with other long liquidations, please liquidate first"
        
        # Start selling
        self.reserve0 = new_reserve0
        self.reserve1 = new_reserve1
        
        # Send fee_amount1 to self.feeAddress (transfer from contract address)
        success, message = erc20_factory_instance.use(self.poolAddress).transfer(self.token0, self.feeAddress, fee_amount1)
        if not success:
            return False, message
        

        #print("3.Remaining collateral + sales proceeds:", amount1_out, "USDT initial total funds =", order['baseAmount1'] + order['lendAmount1'], "USDT", "earned:",closeAmount - (order['baseAmount'] + order['lendAmount1']) )
        loanFeeAmount = close_loan_fee + close_loan_day_fee  # Loan fee + interest
        refundAmount = amount1_out - loanFeeAmount - close_lendAmount1 - close_third_fee
        
        print("3.User's total balance after liquidation:", amount1_out, "USDT", "actual refund:", refundAmount, "USDT", "interest etc. collected:", loanFeeAmount, "USDT")
        
        # Send loanFeeAmount fee to self.feeAddress (transfer from contract address)
        success, message = erc20_factory_instance.use(self.poolAddress).transfer(self.token1, self.feeAddress, loanFeeAmount)
        if not success:
            return False, message
        
        # Return borrowed coins
        self.loanReserve1 += close_lendAmount1
        print("4.Return borrowed coins:", close_lendAmount1, "USDT", "loan pool loanReserve1 increased to:", self.loanReserve1, "USDT")

        # Return remaining USDT to user
        success, message = erc20_factory_instance.use(self.poolAddress).transfer(self.token1, order['address'], refundAmount)
        if not success:
            return False, message

        if isThirdParty:
            # Third party liquidation benefit fee to third party
            success, message = erc20_factory_instance.use(self.poolAddress).transfer(self.token1, self.current_address, close_third_fee)
            if not success:
                return False, message


        # Decide whether to delete order or modify order
        if closeAmount0 == buy_amount0:
            # Delete order
            
            # Add closing data
            order['closePrice'] = self.getPrice()
            order['closeTimestamp'] = int(time.time())
            closeType = ""
            if isThirdParty:
                closeType = "Third party liquidation"
            else:
                closeType = "User active liquidation"
            order['closeType'] = closeType
            order['profitLoss'] = refundAmount - order['baseAmount1']
            order['petLoss'] = (refundAmount - order['baseAmount1']) / order['baseAmount1']
            
            success, message = self.deleteLongOrder(orderID)
            if not success:
                return False, message
            print("5.Return remaining USDT to user:", refundAmount, "USDT", "and delete order:", orderID, "all orders for this address:", self.getOrderIDsByAddress(self.current_address))

        else:
            # Modify order - subtract liquidated portion
            order['loan_fee'] = order['loan_fee'] - close_loan_fee
            order['loan_day_fee'] = order['loan_day_fee'] - close_loan_day_fee
            order['lendAmount1'] = order['lendAmount1'] - close_lendAmount1
            order['buy_amount0'] = order['buy_amount0'] - closeAmount0
            order['third_fee'] = order['third_fee'] - close_third_fee
            
            # Move liquidity pool to forcedClosePrice (for calculation only, cannot change real liquidity pool)
            forced_reserve0, forced_reserve1 = get_reserves_at_price(order['forcedClosePrice'], self.reserve0, self.reserve1)
            # 5. Simulate liquidation trade (sell buy_amount0 tokens, get forced_amount1_out base tokens)
            forced_amount1_out, forced_fee_amount0, forced_new_reserve0, forced_new_reserve1, forced_initial_height_price, forced_final_low_price = get_amount_out_reserve0_to_reserve1(
                order['buy_amount0'], forced_reserve0, forced_reserve1, self.fee
            )
            order['hightPrice'] = forced_initial_height_price
            order['lowPrice'] = forced_final_low_price
            print("5.Return remaining USDT to user:", refundAmount, "USDT", "and modify order:", orderID, "all orders for this address:", self.getOrderIDsByAddress(self.current_address))

        return True, "Liquidation successful"
