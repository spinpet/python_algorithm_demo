import gradio as gr
from urllib.parse import urlparse, parse_qs
from swaphub import SwapHub
from shortswapv1factory import ShortSwapV1Factory
import matplotlib.pyplot as plt
from erc20factory import erc20_factory_instance
from datetime import datetime
import json

# Create ShortSwapV1Factory instance
factory = ShortSwapV1Factory()
# Create a new pool
pool_address = factory.createPool(
    address="0xYourAddress",
    name="TestToken",
    symbol="TTK",
    decimals=18,
    totalSupply=1500000,
    shortSupply=500000,
    tokenBase="0xUSDToken",
    tokenBaseAmount=100000
)

print("Pool address:", pool_address)
pool = factory.getPool(pool_address)

print("Wallet balance:", erc20_factory_instance.allBalanceOf("0xYourAddress"))

# Create a new token USDT 
erc20_factory_instance.createErc20Test('b', "BaseToken", "USDT", 18, 100000, "0xUSDToken")  

erc20_factory_instance.airdrop(pool.token1,{pool.poolAddress:1})
erc20_factory_instance.airdrop(pool.token1,{'a':5000000})

# Airdrop records
ariMap = {}

# Create global TokenSwapHub object
hub = SwapHub(pool)

# Disable Gradio analytics
gr.analytics_enabled = False


def get_swap_hub_info():
    info = json.loads(hub.get_info())
    formatted_info = ""
    for key, value in info.items():
        if isinstance(value, float):
            formatted_value = f"{value:.18f}".rstrip('0').rstrip('.')
        elif isinstance(value, int):
            formatted_value = f"{value:,}"
        else:
            formatted_value = str(value)
        
        # Translate keys to English
        key_translation = {
            "token0": "Token0 Address",
            "token1": "Token1 Address",
            "poolAddress": "Pool Contract Address",
            "token0TotalSupply": "Token0 Total Supply",
            "token0ShortSupply": "Token0 Short Pool Total",
            "token0InitialAmount": "Token0 Initial Amount",
            "reserve0": "Token0 Liquidity Pool Amount",
            "reserve1": "Token1 Liquidity Pool Amount",
            "loanReserve0": "Token0 Loan Reserve Amount",
            "loanReserve1": "Token1 Loan Reserve Amount",
            "loanFee": "Base Loan Fee",
            "loanDayFee": "Base Loan Daily Interest Fee",
            "forcedCloseFee": "Forced Close Fee",
            "forcedCloseBaseAmount": "Forced Close Base Token Amount",
            "collateralShortAmount1": "Short Collateral Total",
            "collateralLongAmount1": "Long Collateral Total",
            "fee": "Fee",
            "feeAddress": "Fee Address",
            "leverageLimit": "Max Leverage",
            "lendingDaysLimit": "Max Lending Days",
            "forceMoveRate": "Forced Close Line Move Rate",
            "current_address": "Current Address"
        }
        
        formatted_key = key_translation.get(key, key)
        formatted_info += f"{formatted_key}: {formatted_value}\n"
    
    # Add price information
    price = hub.get_price()
    formatted_info = f"Price: {price:.18f}\n" + formatted_info
    
    return formatted_info

def get_user_info(addr):
    ttk_balance = f"{erc20_factory_instance.balanceOf(pool.token0, addr):.18f}"
    usdt_balance = f"{erc20_factory_instance.balanceOf(pool.token1, addr):.18f}"
    return f"TTK Balance: {ttk_balance}\nUSDT Balance: {usdt_balance}"

import matplotlib
matplotlib.use('Agg')

def process_price_history():
    y_values = hub.get_price_history() or [0]  # Handle possible empty list return
    if len(y_values) > 100:
        y_values = y_values[-100:]  # Keep only last 100 values
    x_values = list(range(1, len(y_values) + 1))  # Generate x-axis values
    
    plt.figure()
    plt.plot(x_values, y_values)
    plt.title('Price Curve')
    plt.xlabel('Time')
    plt.ylabel('Price')
    fig = plt.gcf()
    plt.close()
    
    return fig

with gr.Blocks(title="Spin.pet Math Model Demo") as demo:
    user_addr = gr.State("")  # Ensure initial value

    with gr.Row():
        with gr.Column():
            # Left options
            line_plot = gr.Plot(label="Price History")
            demo.load(fn=process_price_history, inputs=None, outputs=line_plot, every=3)  # Update chart every 3 seconds

        with gr.Column():
            # Right options
            with gr.Tabs():
                with gr.TabItem("Spot Buy"):
                    gr.Markdown("Buy tokens with USDT")
                    buy_amount = gr.Number(label="USDT Amount to Buy")
                    buy_button = gr.Button("Buy")
                    buy_result = gr.Textbox(label="Buy Result", interactive=False)

                    def perform_buy(amount, addr):
                        if not addr:
                            return "Please enter user address first"
                        success, message = hub.buy(addr, amount)
                        if success:
                            return f"Buy successful: {message}"
                        else:
                            return f"Buy failed: {message}"

                    buy_button.click(
                        perform_buy,
                        inputs=[buy_amount, user_addr],
                        outputs=buy_result
                    )

                with gr.TabItem("Spot Sell"):
                    gr.Markdown("Sell TTK tokens for USDT")
                    sell_amount = gr.Number(label="TTK Amount to Sell")
                    sell_button = gr.Button("Sell")
                    sell_result = gr.Textbox(label="Sell Result", interactive=False)

                    def perform_sell(amount, addr):
                        if not addr:
                            return "Please enter user address first"
                        success, message = hub.sell(addr, amount)
                        if success:
                            return f"Sell successful: {message}"
                        else:
                            return f"Sell failed: {message}"

                    sell_button.click(
                        perform_sell,
                        inputs=[sell_amount, user_addr],
                        outputs=sell_result
                    )


                    
                with gr.TabItem("Leverage Long"):
                    gr.Markdown("Open long position with USDT leverage")
                    long_fast_base_amount = gr.Number(label="USDT Collateral Amount")
                    long_fast_lev_mult = gr.Dropdown(choices=["1", "1.5", "2", "3", "5", "10", "20", "50"], label="Leverage Multiple")
                    long_fast_calc_button = gr.Button("1. Calculate Parameters")
                    long_fast_open_button = gr.Button("2. Execute Long")
                    long_fast_result = gr.Textbox(label="Leverage Long Result", interactive=False)

                    # Store calculated parameters
                    long_fast_params = gr.State(value={})

                    def calculate_long_fast_params(base_amount, lev_mult, addr):
                        if not addr:
                            return "Please enter user address first", {}
                        success, result = hub.long_fast_open(addr, base_amount, float(lev_mult))
                        if success:
                            # Parse JSON and format display
                            formatted_result = "Parameter calculation successful:\n"
                            formatted_result += f"Collateral Amount: {result['baseAmount']:.2f} USDT\n"
                            formatted_result += f"Borrow Amount: {result['lendAmount1']:.2f} USDT\n"
                            formatted_result += f"Purchase Amount: {result['amount0_out']:.4f} TTK\n"
                            formatted_result += f"Limit Liquidation Price: {result['forcedClosePrice']:.4f}\n"
                            formatted_result += f"Insert Order ID: {result['insterOrderID']}\n"
                            formatted_result += f"Actual Forced Close Price: {result['forcedClosePriceMoved']:.4f}\n"
                            formatted_result += f"Price Difference Percentage: {result['priceDifferencePercentage']:.2f}%"
                            return formatted_result, result
                        else:
                            return f"Parameter calculation failed: {result}", {}

                    def execute_long_fast_open(params, addr):
                        if not addr:
                            return "Please enter user address first"
                        if not params:
                            return "Please calculate parameters first"
                        success, message = hub.long_open(addr, params["baseAmount"], params["lendAmount1"], params["forcedClosePrice"], params["insterOrderID"])
                        if success:
                            return f"Leverage long successful: {message}"
                        else:
                            return f"Leverage long failed: {message}"

                    long_fast_calc_button.click(
                        calculate_long_fast_params,
                        inputs=[long_fast_base_amount, long_fast_lev_mult, user_addr],
                        outputs=[long_fast_result, long_fast_params]
                    )

                    long_fast_open_button.click(
                        execute_long_fast_open,
                        inputs=[long_fast_params, user_addr],
                        outputs=long_fast_result
                    )

                with gr.TabItem("Leverage Short"):
                    gr.Markdown("Open short position with USDT leverage")
                    short_fast_base_amount = gr.Number(label="USDT Collateral Amount")
                    short_fast_lev_mult = gr.Dropdown(choices=["1", "1.5", "2", "3", "5", "10", "20", "50"], label="Leverage Multiple")
                    short_fast_calc_button = gr.Button("1. Calculate Parameters")
                    short_fast_open_button = gr.Button("2. Execute Short")
                    short_fast_result = gr.Textbox(label="Leverage Short Result", interactive=False)

                    # Store calculated parameters
                    short_fast_params = gr.State(value={})

                    def calculate_short_fast_params(base_amount, lev_mult, addr):
                        if not addr:
                            return "Please enter user address first", {}
                        success, result = hub.short_fast_open(addr, base_amount, float(lev_mult))
                        if success:
                            # Parse JSON and format display
                            formatted_result = "Parameter calculation successful:\n"
                            formatted_result += f"Collateral Amount: {result['baseAmount']:.2f} USDT\n"
                            formatted_result += f"Borrow Amount: {result['lendAmount']:.4f} TTK\n"
                            formatted_result += f"Limit Liquidation Price: {result['forcedClosePrice']:.4f}\n"
                            formatted_result += f"Insert Order ID: {result['insterOrderID']}\n"
                            formatted_result += f"Actual Forced Close Price: {result['forcedClosePriceMoved']:.4f}\n"
                            formatted_result += f"Price Difference Percentage: {result['priceDifferencePercentage']:.2f}%"
                            return formatted_result, result
                        else:
                            return f"Parameter calculation failed: {result}", {}

                    def execute_short_fast_open(params, addr):
                        if not addr:
                            return "Please enter user address first"
                        if not params:
                            return "Please calculate parameters first"
                        success, message = hub.short_open(addr, params["baseAmount"], params["lendAmount"], params["forcedClosePrice"], params["insterOrderID"])
                        if success:
                            return f"Leverage short successful: {message}"
                        else:
                            return f"Leverage short failed: {message}"

                    short_fast_calc_button.click(
                        calculate_short_fast_params,
                        inputs=[short_fast_base_amount, short_fast_lev_mult, user_addr],
                        outputs=[short_fast_result, short_fast_params]
                    )

                    short_fast_open_button.click(
                        execute_short_fast_open,
                        inputs=[short_fast_params, user_addr],
                        outputs=short_fast_result
                    )
             
                # with gr.TabItem("Debug Long"):
                #     gr.Markdown("Technical debug - open long position with USDT (users should not use)")
                #     long_base_amount = gr.Number(label="USDT Collateral Amount")
                #     long_lend_amount = gr.Number(label="USDT Borrow Amount")
                #     long_forced_close_price = gr.Number(label="Forced Close Price")
                #     long_inster_order_id = gr.Textbox(label="Insert Order ID (optional)")
                #     long_button = gr.Button("Open Long")
                #     long_result = gr.Textbox(label="Long Result", interactive=False)

                #     def perform_long(base_amount, lend_amount, forced_close_price, inster_order_id, addr):
                #         if not addr:
                #             return "Please enter user address first"
                #         success, message = hub.long_open(addr, base_amount, lend_amount, forced_close_price, inster_order_id)
                #         if success:
                #             return f"Long successful: {message}"
                #         else:
                #             return f"Long failed: {message}"

                #     long_button.click(
                #         perform_long,
                #         inputs=[long_base_amount, long_lend_amount, long_forced_close_price, long_inster_order_id, user_addr],
                #         outputs=long_result
                #     )

                # with gr.TabItem("Debug Short"):
                #     gr.Markdown("Technical debug - open short position with USDT (users should not use)")
                #     short_base_amount = gr.Number(label="USDT Collateral Amount")
                #     short_lend_amount = gr.Number(label="TTK Borrow Amount")
                #     short_forced_close_price = gr.Number(label="Forced Close Price")
                #     short_inster_order_id = gr.Textbox(label="Insert Order ID (optional)")
                #     short_button = gr.Button("Open Short")
                #     short_result = gr.Textbox(label="Short Result", interactive=False)

                #     def perform_short(base_amount, lend_amount, forced_close_price, inster_order_id, addr):
                #         if not addr:
                #             return "Please enter user address first"
                #         success, message = hub.short_open(addr, base_amount, lend_amount, forced_close_price, inster_order_id)
                #         if success:
                #             return f"Short successful: {message}"
                #         else:
                #             return f"Short failed: {message}"

                #     short_button.click(
                #         perform_short,
                #         inputs=[short_base_amount, short_lend_amount, short_forced_close_price, short_inster_order_id, user_addr],
                #         outputs=short_result
                #     )
             
             
    with gr.Row():
        # Bottom tabs
        with gr.Tabs():
            with gr.TabItem("Current Account"):
                addr_input = gr.Textbox(label="User Address (enter any address to start trading)")
                user_info = gr.Textbox(label="User Info", interactive=False)
                addr_input.change(fn=lambda addr: (addr, get_user_info(addr)), inputs=addr_input, outputs=[user_addr, user_info])
                demo.load(fn=lambda addr: get_user_info(addr) if addr else "", inputs=[user_addr], outputs=user_info, every=3)  # Add auto refresh

            with gr.TabItem("Current Price"):
                swap_hub_info = gr.Textbox(label="Current Pool Info", interactive=False, lines=27)
                demo.load(fn=get_swap_hub_info, inputs=None, outputs=swap_hub_info, every=3)

            with gr.TabItem("Token Airdrop"):
                #airdrop_token = gr.Dropdown(choices=["TTK", "USDT"], label="Select Airdrop Token")
                airdrop_token = gr.Dropdown(choices=["USDT"], label="Select Airdrop Token")
                airdrop_amount = gr.Number(label="Airdrop Amount")
                airdrop_addresses = gr.TextArea(label="Recipient Addresses (one per line)")
                airdrop_button = gr.Button("Execute Airdrop")
                airdrop_result = gr.Textbox(label="Airdrop Result", interactive=False)

                def perform_airdrop(token, amount, addresses):
                    if token == "TTK":
                        contract_address = pool.token0
                    elif token == "USDT":
                        contract_address = pool.token1
                    else:
                        return "Invalid token selection"

                    address_list = [addr.strip() for addr in addresses.split('\n') if addr.strip()]
                    recipients = {addr: amount for addr in address_list}
                    
                    success, message = erc20_factory_instance.airdrop(contract_address, recipients)
                    if success:
                        return f"Airdrop successful: {message}"
                    else:
                        return f"Airdrop failed: {message}"

                airdrop_button.click(
                    perform_airdrop,
                    inputs=[airdrop_token, airdrop_amount, airdrop_addresses],
                    outputs=airdrop_result
                )
                
            with gr.TabItem("My Leverage Positions"):
                leverage_order_buttons = []
                max_leverage_orders = 50  # Maximum number of orders to display
                leverage_order_ids_state = gr.State([])  # Store order ID list
                with gr.Column():
                    leverage_trade_result = gr.Markdown()  # Display close result
                    manual_close_amount = gr.Textbox(
                        label="Manual Close Amount (optional)",
                        placeholder="Enter amount",
                        value=""
                    )
                    for i in range(max_leverage_orders):
                        btn = gr.Button(visible=False)
                        leverage_order_buttons.append(btn)

                # Function to get current leverage orders
                def get_current_leverage_orders(addr):
                    if addr:
                        short_orders = hub.pool.getShortOrder("", 100)  # Get all short orders
                        long_orders = hub.pool.getLongOrder("", 100)  # Get all long orders
                        all_orders = short_orders + long_orders
                        return [order for order in all_orders if order['address'] == addr]
                    else:
                        return []

                # Function to update buttons
                def update_leverage_order_buttons(addr):
                    orders = get_current_leverage_orders(addr)
                    order_ids = []
                    btn_updates = []
                    current_price = hub.get_price()
                    for i in range(max_leverage_orders):
                        if i < len(orders):
                            order = orders[i]
                            order_id = order['orderID']
                            order_type = "Long" if order['orderType'] == "long" else "Short"
                            open_price = order['openPrice']
                            liquidation_price = order['forcedClosePrice']
                            collateral = order['baseAmount1']
                            
                            # Get borrowed amount - all in TTK
                            borrowed_amount = order['lendAmount0'] if order['orderType'] == "short" else order['buy_amount0']
                            
                            # Calculate profit/loss percentage
                            if order['orderType'] == "long":
                                profit_loss_percentage = hub.calculate_profit_loss(
                                    "long", 
                                    order['baseAmount1'], 
                                    order['lendAmount1'], 
                                    order['buy_amount0']
                                )
                            else:  # short
                                profit_loss_percentage = hub.calculate_profit_loss(
                                    "short", 
                                    order['baseAmount1'], 
                                    order['sell_amount1'], 
                                    order['lendAmount0']
                                )
                            
                            order_ids.append(order_id)
                            btn_text = (f"Order {order_id}\n"
                                        f"Direction: {order_type}\n"
                                        f"Open Price: {open_price:.4f}\n"
                                        f"Liquidation Price: {liquidation_price:.4f}\n"
                                        f"Collateral: {collateral:.2f} USDT\n"
                                        f"Borrowed TTK: {borrowed_amount:.2f}\n"
                                        f"P&L: {profit_loss_percentage:.2f}%\n"
                                        
                                        )
                            btn_updates.append(gr.update(visible=True, value=btn_text))
                        else:
                            btn_updates.append(gr.update(visible=False))
                    return btn_updates + [order_ids]

                # Close position function
                def close_leverage_order(i, addr, order_ids, manual_amount):
                    if i < len(order_ids):
                        order_id = order_ids[i]
                        order = hub.pool.getOrderByID(order_id)
                        is_loop = False
                        if manual_amount in (None, ""):
                            manual_amount = None
                            is_loop = True
                        if order['orderType'] == "long":
                            close_amount = manual_amount if manual_amount is not None else order["buy_amount0"]
                            close_func = hub.long_close
                        else:
                            close_amount = manual_amount if manual_amount is not None else order["lendAmount0"]
                            close_func = hub.short_close
                            
                        close_amount = float(close_amount)

                        if is_loop:
                            max_attempts = 10
                            for attempt in range(max_attempts):
                                success, message = close_func(addr, order_id, close_amount)
                                if success:
                                    return f"Order {order_id} closed successfully. {message}"
                                elif attempt < max_attempts - 1:
                                    close_amount /= 2
                                    continue
                                else:
                                    return f"Order {order_id} close failed. {message}"
                        else:
                            success, message = close_func(addr, order_id, close_amount)
                            if success:
                                return f"Order {order_id} closed successfully. {message}"
                            else:
                                return f"Order {order_id} close failed. {message}"
                            
                    else:
                        return "No orders to close."   

                # Set up events
                demo.load(fn=update_leverage_order_buttons, inputs=[user_addr], outputs=leverage_order_buttons + [leverage_order_ids_state], every=3)

                # Set click events for each button
                for i in range(max_leverage_orders):
                    leverage_order_buttons[i].click(
                        fn=lambda addr, order_ids, manual_amount, i=i: close_leverage_order(i, addr, order_ids, manual_amount),
                        inputs=[user_addr, leverage_order_ids_state, manual_close_amount],
                        outputs=leverage_trade_result
                    )

            with gr.TabItem("My Position History"):
                history_positions = gr.Dataframe(
                    label="Position History",
                    headers=[
                        "Order ID", "Order Type", "Open Price", "Close Price", "Borrowed Amount", 
                        "Collateral Amount", "Liquidation Price", "Open Time", "Close Time", "Close Type", "P&L", "Percentage"
                    ],
                    interactive=False
                )

                def format_history_orders(orders):
                    formatted_orders = []
                    for order in orders:
                        formatted_order = [
                            order.get('orderID', ''),
                            order.get('orderType', ''),
                            f"{order.get('openPrice', 0):.4f}",
                            f"{order.get('closePrice', 0):.4f}",
                            f"{order.get('lendAmount0', order.get('lendAmount1', 0)):.2f}",
                            f"{order.get('baseAmount1', 0):.2f}",
                            f"{order.get('forcedClosePrice', 0):.4f}",
                            datetime.fromtimestamp(order.get('loan_time', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                            datetime.fromtimestamp(order.get('closeTimestamp', 0)).strftime('%Y-%m-%d %H:%M:%S') if order.get('closeTimestamp') else '',
                            order.get('closeType', ''),
                            f"{order.get('profitLoss', 0):.2f}",
                            f"{order.get('petLoss', 0):.2f}%"
                        ]
                        formatted_orders.append(formatted_order)
                    return formatted_orders

                def get_history_orders(addr):
                    if addr:
                        history_orders = hub.pool.getAddressHistoryOrders(addr)
                        return format_history_orders(history_orders)
                    else:
                        return []

                demo.load(
                    fn=get_history_orders,
                    inputs=[user_addr],
                    outputs=history_positions,
                    every=3
                )
                
            with gr.TabItem("Third-party Liquidation"):
                gr.Markdown("When approaching liquidation price, any third party can liquidate orders and receive benefits, keeping trades flowing smoothly.")
                with gr.Row():
                    near_long_node = gr.Textbox(label="Nearest Long Order ID", interactive=False)
                    near_short_node = gr.Textbox(label="Nearest Short Order ID", interactive=False)

                def update_near_nodes():
                    return hub.pool.nearLongNode, hub.pool.nearShortNode

                demo.load(fn=update_near_nodes, inputs=None, outputs=[near_long_node, near_short_node], every=3)

                liquidate_button = gr.Button("Liquidate Long/Short Stop Orders")
                liquidate_result = gr.Textbox(label="Liquidation Result", interactive=False)

                def liquidate_orders(user_addr):
                    long_result = False, "No long orders to liquidate"
                    short_result = False, "No short orders to liquidate"

                    if hub.pool.nearLongNode:
                        long_order = hub.pool.getOrderByID(hub.pool.nearLongNode)
                        if long_order:
                            long_result = hub.long_close(user_addr, hub.pool.nearLongNode, long_order['buy_amount0'], isThirdParty=True)

                    if hub.pool.nearShortNode:
                        short_order = hub.pool.getOrderByID(hub.pool.nearShortNode)
                        if short_order:
                            short_result = hub.short_close(user_addr, hub.pool.nearShortNode, short_order['lendAmount0'], isThirdParty=True)

                    return f"Long liquidation result: {long_result[1]}\nShort liquidation result: {short_result[1]}"

                liquidate_button.click(
                    fn=liquidate_orders,
                    inputs=[user_addr],
                    outputs=liquidate_result
                )
                
                
            with gr.TabItem("Global Orders"):
                with gr.Row():
                    with gr.Column():
                        short_orders_display = gr.Dataframe(
                            label="Short Orders",
                            headers=[
                                "Order ID", "Address", "Open Price", "Liquidation Price", "Borrowed Amount", 
                                "Collateral Amount", "Liquidation High", "Liquidation Low"
                            ],
                            interactive=False
                        )
                    with gr.Column():
                        long_orders_display = gr.Dataframe(
                            label="Long Orders",
                            headers=[
                                "Order ID", "Address", "Open Price", "Liquidation Price", "Borrowed Amount", 
                                "Collateral Amount", "Liquidation High", "Liquidation Low"
                            ],
                            interactive=False
                        )

                def format_orders(orders):
                    return [
                        [
                            order.get('orderID', ''),
                            order.get('address', '')[:10] + '...',  # Show only first 10 characters of address
                            f"{order.get('openPrice', 0):.4f}",
                            f"{order.get('forcedClosePrice', 0):.4f}",
                            f"{order.get('lendAmount0', order.get('buy_amount0', 0)):.2f}",
                            f"{order.get('baseAmount1', 0):.2f}",
                            f"{order.get('hightPrice', 0):.4f}",
                            f"{order.get('lowPrice', 0):.4f}"
                        ]
                        for order in orders
                    ]

                def update_global_orders(request: gr.Request):
                    short_orders = hub.get_short_order(100)
                    long_orders = hub.get_long_order(100)
                    
                    # Get complete URL from headers
                    referer = request.headers.get("referer", "")
                    parsed_url = urlparse(referer)
                    query_params = parse_qs(parsed_url.query)
                    # Get parameters
                    address = query_params.get('address', ['Address parameter not found'])[0]
                    coin = query_params.get('coin', ['Coin parameter not found'])[0]
                    name = query_params.get('name', ['Name parameter not found'])[0]
                    
                    print(f"Address parameter: {address}\nCoin parameter: {coin}\nToken name: {name}")
                    
                    # Airdrop for new users
                    if address not in ariMap:
                        ariMap[address] = 1
                        erc20_factory_instance.airdrop("0xUSDToken",{address:500000})
                    
                    
                    return format_orders(short_orders), format_orders(long_orders),address

                demo.load(
                    fn=update_global_orders,
                    inputs=None,
                    outputs=[short_orders_display, long_orders_display,addr_input],
                    every=3
                )



demo.launch(server_name="0.0.0.0", server_port=777)