# File name: swap_utils.py

# Constant product market maker algorithm calculation functions

def get_current_price(reserve0, reserve1):
    """
    Calculate current price
    :param reserve0: Amount of tokens
    :param reserve1: Amount of base tokens
    :return: Current price
    """
    return reserve1 / reserve0


def get_amount_out_reserve0_to_reserve1(amount0_in, reserve0, reserve1, fee=0.997):
    """
    Calculate how much reserve1 can be exchanged for a certain amount of reserve0 tokens
    Fee is charged on reserve0 tokens
    :param amount0_in: Input amount of reserve0 tokens
    :param reserve0: Amount of tokens
    :param reserve1: Amount of base tokens
    :param fee: Fee ratio (fee charged on reserve0 tokens)
    :return: Amount of reserve1 that can be exchanged, fee amount, updated reserve0, reserve1
    """
    amount0_in_with_fee = amount0_in * fee    # Deduct fee first
    fee_amount0 = amount0_in - amount0_in_with_fee  # Calculate fee amount
    numerator = amount0_in_with_fee * reserve1
    denominator = reserve0 + amount0_in_with_fee
    amount1_out = numerator / denominator
    new_reserve0 = reserve0 + amount0_in_with_fee
    new_reserve1 = reserve1 - amount1_out
    initial_height_price = get_current_price(reserve0, reserve1)
    final_low_price = get_current_price(new_reserve0, new_reserve1)
    return amount1_out, fee_amount0, new_reserve0, new_reserve1, initial_height_price, final_low_price

def get_amount_out_reserve1_to_reserve0(amount1_in, reserve0, reserve1, fee=0.997):
    """
    Calculate how much reserve0 can be exchanged for a certain amount of reserve1 tokens
    Fee is charged on reserve1 tokens
    :param amount1_in: Input amount of reserve1 tokens
    :param reserve0: Amount of tokens
    :param reserve1: Amount of base tokens
    :param fee: Fee ratio (fee charged on reserve1 tokens)
    :return: Amount of reserve0 that can be exchanged, fee amount, updated reserve0, reserve1
    """
    amount1_in_with_fee = amount1_in * fee  # Deduct fee first
    fee_amount1 = amount1_in - amount1_in_with_fee  # Calculate fee amount
    numerator = amount1_in_with_fee * reserve0
    denominator = reserve1 + amount1_in_with_fee
    amount0_out = numerator / denominator
    new_reserve0 = reserve0 - amount0_out
    new_reserve1 = reserve1 + amount1_in_with_fee
    initial_low_price = get_current_price(reserve0, reserve1)
    final_height_price = get_current_price(new_reserve0, new_reserve1)
    return amount0_out, fee_amount1, new_reserve0, new_reserve1, initial_low_price, final_height_price

def get_reserves_at_price(price, reserve0, reserve1):
    """
    Given target price and current reserves, calculate reserves at target price
    :param price: Target price
    :param reserve0: Current reserve0 amount
    :param reserve1: Current reserve1 amount
    :return: New reserve0, reserve1, amount of tokens user needs to buy or sell
    """
    # Calculate constant product k
    k = reserve0 * reserve1

    # Calculate new reserves
    new_reserve0 = (k / price) ** 0.5
    new_reserve1 = (k * price) ** 0.5

    # Calculate amount of tokens to buy or sell
    amount_in_reserve0 = new_reserve0 - reserve0
    amount_in_reserve1 = new_reserve1 - reserve1
    
    return new_reserve0, new_reserve1



def get_amount_in_reserve0_for_amount1_out(amount1_out, reserve0, reserve1, fee=0.997):
    """
    Calculate how much reserve0 tokens are needed to exchange for specified amount of reserve1 tokens
    Fee is charged on reserve0 tokens
    :param amount1_out: Expected output amount of reserve1 tokens
    :param reserve0: Token0 reserve amount
    :param reserve1: Token1 reserve amount
    :param fee: Fee ratio (fee charged on reserve0 tokens)
    :return: Required input amount of reserve0 tokens (fee included), fee amount, updated reserve0, reserve1, pre-exchange price, post-exchange price
    """
    assert amount1_out < reserve1, 'SwapV1: INSUFFICIENT_LIQUIDITY'

    # Calculate pre-exchange price
    initial_height_price = get_current_price(reserve0, reserve1)

    # Calculate required amount0_in_with_fee
    numerator = amount1_out * reserve0
    denominator = (reserve1 - amount1_out) * fee
    amount0_in = numerator / denominator  # Calculate required input amount of reserve0 tokens
    fee_amount0 = amount0_in * (1 - fee)  # Calculate fee amount
    
    # Update reserves
    new_reserve0 = reserve0 + amount0_in
    new_reserve1 = reserve1 - amount1_out

    # Calculate post-exchange price
    final_low_price = get_current_price(new_reserve0, new_reserve1)

    return amount0_in, fee_amount0, new_reserve0, new_reserve1, initial_height_price, final_low_price


def get_amount_in_reserve1_for_amount0_out(amount0_out, reserve0, reserve1, fee=0.997):
    """
    Calculate how much reserve1 tokens are needed to exchange for specified amount of reserve0 tokens
    Fee is charged on reserve1 tokens
    :param amount0_out: Desired amount of reserve0 tokens to obtain
    :param reserve0: Token0 reserve amount
    :param reserve1: Token1 reserve amount
    :param fee: Fee ratio (fee charged on reserve1 tokens)
    :return: Required input amount of reserve1 tokens (fee included), fee amount, updated reserve0, reserve1, initial price, final price
    """
    assert amount0_out < reserve0, 'SwapV1: INSUFFICIENT_LIQUIDITY'

    # Calculate constant product k
    k = reserve0 * reserve1

    # Calculate required input amount of reserve1 tokens
    numerator = reserve1 * amount0_out
    denominator = (reserve0 - amount0_out) * fee
    amount1_in = numerator / denominator

    # Calculate fee amount
    fee_amount1 = amount1_in * (1 - fee)
    amount1_in_with_fee = amount1_in - fee_amount1

    # Update reserves
    new_reserve0 = reserve0 - amount0_out
    new_reserve1 = reserve1 + amount1_in_with_fee  # Fix: only add net input amount

    # Calculate pre and post exchange prices
    initial_low_price = get_current_price(reserve0, reserve1)
    final_height_price = get_current_price(new_reserve0, new_reserve1)

    return amount1_in, fee_amount1, new_reserve0, new_reserve1, initial_low_price, final_height_price