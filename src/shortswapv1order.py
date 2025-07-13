import shortuuid

class ShortSwapV1Order:
    def __init__(self):
        # Maximum order length per address
        self.ORDER_MAX_LENGTH = 50
        
        self.orderShortMap = {}
        self.nearShortNode = ""
        
        self.orderLongMap = {}
        self.nearLongNode = ""
        
        self.addressNodeMap = {}   
        self.addressHistoryMap = {}   
        
        self.orderCount = 0   
          
    def generateOrderID(self,head):
        #return shortuuid.uuid()[:8]  # Generate 8-character short ID
        self.orderCount += 1
        return head+ str(self.orderCount)



    def insterShortOrder(self, node, nodeOrderID):
        """
        Insert a new short order node into the linked list

        :param node: The node to insert, containing order ID, highest price, lowest price, address and data etc.
        :param nodeOrderID: The specified node ID, indicating that the new node should be inserted after this node. If empty string, insert at the bottom of the list
        :return: (bool, str) Whether the insertion was successful and corresponding message
        """
        # Add new validation
        if node['hightPrice'] <= node['lowPrice']:
            return False, "Highest price must be greater than lowest price"

        #print("insterShortOrder =",node['lowPrice'],node['hightPrice'] )
        if not self.nearShortNode:
            # List is empty, insert directly
            self.orderShortMap[node['orderID']] = node
            self.nearShortNode = node['orderID']
            self._addOrderToAddressMap(node['address'], node['orderID'])
            return True, "Successfully inserted first node"

        if nodeOrderID == "":
            # Insert at the bottom
            
            lowest_node = self.orderShortMap[self.nearShortNode]
            print("New node:", node['lowPrice'], node['hightPrice'])
            print("Old node:",lowest_node['lowPrice'],lowest_node['hightPrice'])
            if node['hightPrice'] <= lowest_node['lowPrice']:
                node['hightNode'] = self.nearShortNode
                lowest_node['lowNode'] = node['orderID']
                self.orderShortMap[node['orderID']] = node
                self.orderShortMap[self.nearShortNode] = lowest_node
                self.nearShortNode = node['orderID']
                self._addOrderToAddressMap(node['address'], node['orderID'])
                return True, "Successfully inserted at bottom"
            return False, "New node overlaps with lowest node"

        if nodeOrderID not in self.orderShortMap:
            return False, "Specified nodeOrderID does not exist"

        current_node = self.orderShortMap[nodeOrderID]
        if node['lowPrice'] >= current_node['hightPrice']:
            if current_node['hightNode']:
                upper_node = self.orderShortMap[current_node['hightNode']]
                if node['hightPrice'] <= upper_node['lowPrice']:
                    node['hightNode'] = current_node['hightNode']
                    node['lowNode'] = current_node['orderID']
                    current_node['hightNode'] = node['orderID']
                    upper_node['lowNode'] = node['orderID']
                    self.orderShortMap[node['orderID']] = node
                    self.orderShortMap[current_node['orderID']] = current_node
                    self.orderShortMap[upper_node['orderID']] = upper_node
                    self._addOrderToAddressMap(node['address'], node['orderID'])
                    return True, "Successfully inserted new node"
                return False, "New node overlaps with upper node"
            else:
                node['hightNode'] = current_node['hightNode']
                node['lowNode'] = current_node['orderID']
                current_node['hightNode'] = node['orderID']
                self.orderShortMap[node['orderID']] = node
                self.orderShortMap[current_node['orderID']] = current_node
                self._addOrderToAddressMap(node['address'], node['orderID'])
                return True, "Successfully inserted at top"
        return False, "New node overlaps with current node"


    def printOrderShort(self):
        print("Order linked list (from bottom to top):")
        current_id = self.nearShortNode
        while current_id:
            node = self.orderShortMap[current_id]
            print(f"Order ID: {node['orderID']}, Highest price: {node['hightPrice']}, Lowest price: {node['lowPrice']}, Data: {node['data']}")
            current_id = node['hightNode']
        print()

    def insterLongOrder(self, node, nodeOrderID):
        """
        Insert a new long order node into the linked list

        :param node: The node to insert, containing order ID, highest price, lowest price, address and data etc.
        :param nodeOrderID: The specified node ID, indicating that the new node should be inserted after this node. If empty string, insert at the top of the list
        :return: (bool, str) Whether the insertion was successful and corresponding message
        """
        # Add new validation
        if node['hightPrice'] <= node['lowPrice']:
            return False, "Highest price must be greater than lowest price"
        
        if not self.nearLongNode:
            # List is empty, insert directly
            self.orderLongMap[node['orderID']] = node
            self.nearLongNode = node['orderID']
            self._addOrderToAddressMap(node['address'], node['orderID'])
            return True, "Successfully inserted first node"

        if nodeOrderID == "":
            # Insert at the top
            highest_node = self.orderLongMap[self.nearLongNode]
            if node['lowPrice'] >= highest_node['hightPrice']:
                node['lowNode'] = self.nearLongNode
                highest_node['hightNode'] = node['orderID']
                self.orderLongMap[node['orderID']] = node
                self.orderLongMap[self.nearLongNode] = highest_node
                self.nearLongNode = node['orderID']
                self._addOrderToAddressMap(node['address'], node['orderID'])
                return True, "Successfully inserted at top"
            return False, "New node overlaps with highest node"

        if nodeOrderID not in self.orderLongMap:
            return False, "Specified nodeOrderID does not exist"

        current_node = self.orderLongMap[nodeOrderID]
        if node['hightPrice'] <= current_node['lowPrice']:
            if current_node['lowNode']:
                lower_node = self.orderLongMap[current_node['lowNode']]
                if node['lowPrice'] >= lower_node['hightPrice']:
                    node['lowNode'] = current_node['lowNode']
                    node['hightNode'] = current_node['orderID']
                    current_node['lowNode'] = node['orderID']
                    lower_node['hightNode'] = node['orderID']
                    self.orderLongMap[node['orderID']] = node
                    self.orderLongMap[current_node['orderID']] = current_node
                    self.orderLongMap[lower_node['orderID']] = lower_node
                    self._addOrderToAddressMap(node['address'], node['orderID'])
                    return True, "Successfully inserted new node"
                return False, "New node overlaps with lower node"
            else:
                node['lowNode'] = current_node['lowNode']
                node['hightNode'] = current_node['orderID']
                current_node['lowNode'] = node['orderID']
                self.orderLongMap[node['orderID']] = node
                self.orderLongMap[current_node['orderID']] = current_node
                self._addOrderToAddressMap(node['address'], node['orderID'])
                return True, "Successfully inserted at bottom"
        return False, "New node overlaps with current node"


    def printOrderLong(self):
        print("Order linked list (from top to bottom):")
        current_id = self.nearLongNode
        while current_id:
            node = self.orderLongMap[current_id]
            print(f"Order ID: {node['orderID']}, Highest price: {node['hightPrice']}, Lowest price: {node['lowPrice']}, Data: {node['data']}")
            current_id = node['lowNode']
        print()
        
    def getShortOrder(self, nodeOrderID, num):
        """
        Get short order linked list data in sequence
        :param nodeOrderID: Starting node ID, if empty string then start from lowest price node
        :param num: Number of nodes to retrieve
        :return: List containing data of specified number of nodes
        """
        result = []
        current_id = nodeOrderID if nodeOrderID else self.nearShortNode
        
        while current_id and len(result) < num:
            if current_id in self.orderShortMap:
                node = self.orderShortMap[current_id]
                result.append(node)
                current_id = node['hightNode']
            else:
                break
        
        return result

    def getLongOrder(self, nodeOrderID, num):
        """
        Get long order linked list data in sequence
        :param nodeOrderID: Starting node ID, if empty string then start from highest price node
        :param num: Number of nodes to retrieve
        :return: List containing data of specified number of nodes
        """
        result = []
        current_id = nodeOrderID if nodeOrderID else self.nearLongNode
        
        while current_id and len(result) < num:
            if current_id in self.orderLongMap:
                node = self.orderLongMap[current_id]
                result.append(node)
                current_id = node['lowNode']
            else:
                break
        
        return result
    
    def deleteShortOrder(self, nodeOrderID):
        if nodeOrderID not in self.orderShortMap:
            return False, "Specified nodeOrderID does not exist"

        node = self.orderShortMap[nodeOrderID]
        
        if node['hightNode']:
            upper_node = self.orderShortMap[node['hightNode']]
            upper_node['lowNode'] = node['lowNode']
            self.orderShortMap[node['hightNode']] = upper_node
        else:
            # If it's the top node, no need to update upper node
            pass

        if node['lowNode']:
            lower_node = self.orderShortMap[node['lowNode']]
            lower_node['hightNode'] = node['hightNode']
            self.orderShortMap[node['lowNode']] = lower_node
        else:
            # If it's the bottom node, update nearShortNode
            self.nearShortNode = node['hightNode']

        del self.orderShortMap[nodeOrderID]
        self._removeOrderFromAddressMap(node['address'], nodeOrderID, node)
        return True, "Successfully deleted node"


    def deleteLongOrder(self, nodeOrderID):
        if nodeOrderID not in self.orderLongMap:
            return False, "Specified nodeOrderID does not exist"

        node = self.orderLongMap[nodeOrderID]
        
        if node['lowNode']:
            lower_node = self.orderLongMap[node['lowNode']]
            lower_node['hightNode'] = node['hightNode']
            self.orderLongMap[node['lowNode']] = lower_node
        else:
            # If it's the bottom node, no need to update lower node
            pass

        if node['hightNode']:
            upper_node = self.orderLongMap[node['hightNode']]
            upper_node['lowNode'] = node['lowNode']
            self.orderLongMap[node['hightNode']] = upper_node
        else:
            # If it's the top node, update nearLongNode
            self.nearLongNode = node['lowNode']

        del self.orderLongMap[nodeOrderID]
        self._removeOrderFromAddressMap(node['address'], nodeOrderID, node)
        return True, "Successfully deleted node"


    def _addOrderToAddressMap(self, address, orderID):
        if address not in self.addressNodeMap:
            self.addressNodeMap[address] = []
        if len(self.addressNodeMap[address]) < self.ORDER_MAX_LENGTH:
            self.addressNodeMap[address].append(orderID)
        else:
            raise ValueError(f"Address {address} has reached maximum order limit {self.ORDER_MAX_LENGTH}")

    def _removeOrderFromAddressMap(self, address, orderID, order_data):
        # print(f"Starting to remove order: address={address}, orderID={orderID}")
        # print("self.addressNodeMap =",self.addressNodeMap)
        if address in self.addressNodeMap:
            if orderID in self.addressNodeMap[address]:
                # Remove from current order list
                self.addressNodeMap[address].remove(orderID)
                
                # Add to history
                if address not in self.addressHistoryMap:
                    self.addressHistoryMap[address] = []
                self.addressHistoryMap[address].append(order_data)
                #print(f"Order added to history: {order_data}")
                
                if not self.addressNodeMap[address]:
                    del self.addressNodeMap[address]
        #print(f"History after removing order: {self.addressHistoryMap}")

    def getOrderIDsByAddress(self, address):
        """
        Get all order IDs for a specified address

        :param address: User address
        :return: List of order IDs

        Order data content description:
        1. Short orders (shortOpen):
            - orderID: Unique order identifier
            - orderType: "short"
            - address: User address
            - baseAmount: User provided base token amount (USDT)
            - sell_amount1_out: USDT amount obtained from selling borrowed tokens
            - lendAmount: Amount of borrowed tokens
            - forcedClosePrice: Forced liquidation price
            - loan_fee: Basic loan fee
            - loan_day_fee: Daily loan interest fee
            - forced_close_fee: Forced liquidation fee
            - forcedCloseBaseAmount: Base token amount charged for forced liquidation
            - forceMoveRate: Forced liquidation line movement ratio
            - loan_time: Short trade timestamp
            - hightPrice: Highest price after forced liquidation
            - lowPrice: Lowest price after forced liquidation
            - hightNode: Previous node
            - lowNode: Next node

        2. Long orders (longOpen):
            - orderID: Unique order identifier
            - orderType: "long"
            - address: User address
            - baseAmount: User provided base token amount (USDT)
            - lendAmount1: Borrowed base token amount (USDT)
            - buyAmount0: Amount of tokens purchased
            - postBuyAmount1: Remaining margin
            - forcedClosePrice: Forced liquidation price
            - loan_fee: Basic loan fee
            - loan_day_fee: Daily loan interest fee
            - forced_close_fee: Forced liquidation fee
            - forcedCloseBaseAmount: Base token amount charged for forced liquidation
            - forceMoveRate: Forced liquidation line movement ratio
            - loan_time: Long trade timestamp
            - hightPrice: Highest price after forced liquidation
            - lowPrice: Lowest price after forced liquidation
            - hightNode: Previous node
            - lowNode: Next node

        Note: These data fields are set when orders are created and may be updated during the order lifecycle.
        """
        return self.addressNodeMap.get(address, [])

    def checkShortOrderRange(self,hightPrice, lowPrice,orderID=""):
        """
        Check if the given price range intersects with existing short orders

        :param hightPrice: Highest price of new order
        :param lowPrice: Lowest price of new order
        :return: (bool, str) Whether there is intersection and corresponding message
        """
        if not self.nearShortNode:
            return True, "Short order table is empty"
        if orderID == self.nearShortNode:
            return True, "Given range has only one short order (itself), no intersection"

        current_id = self.nearShortNode
        while current_id:
            node = self.orderShortMap[current_id]
            
            # Check for intersection
            if (lowPrice <= node['hightPrice'] and hightPrice >= node['lowPrice']) or \
               (lowPrice >= node['lowPrice'] and lowPrice <= node['hightPrice']) or \
               (hightPrice >= node['lowPrice'] and hightPrice <= node['hightPrice']):
                return False, f"Given range intersects with short order {current_id}"
            
            # If the highest price of current range is lower than node's lowest price, 
            # later nodes definitely have no intersection, can exit loop directly
            if hightPrice < node['lowPrice']:
                break
            
            current_id = node['hightNode']

        return True, "Given range has no intersection with short orders"

    def checkLongOrderRange(self,hightPrice, lowPrice,orderID=""):
        """
        Check if the given price range intersects with long orders

        :param hightPrice: Highest price
        :param lowPrice: Lowest price
        :return: (bool, str) Whether there is intersection and corresponding message
        """
        if not self.nearLongNode:
            return True, "Long order table is empty"
        if orderID == self.nearLongNode:
            return True, "Given range has only one long order (itself), no intersection"

        current_id = self.nearLongNode
        while current_id:
            node = self.orderLongMap[current_id]
            if (lowPrice <= node['hightPrice'] and hightPrice >= node['lowPrice']) or \
               (lowPrice >= node['lowPrice'] and lowPrice <= node['hightPrice']) or \
               (hightPrice >= node['lowPrice'] and hightPrice <= node['hightPrice']):
                return False, f"Given range intersects with long order {current_id}"
            
            # If the lowest price of current range is higher than node's highest price,
            # later nodes definitely have no intersection, can exit loop directly
            if lowPrice > node['hightPrice']:
                break
            
            current_id = node['lowNode']

        return True, "Given range has no intersection with long orders"

    def getOrderByID(self, orderID):
        """
        Query data in self.orderShortMap and self.orderLongMap by orderID

        :param orderID: Order ID
        :return: Order data, returns None if not found
        """
        if orderID in self.orderShortMap:
            return self.orderShortMap[orderID]
        elif orderID in self.orderLongMap:
            return self.orderLongMap[orderID]
        else:
            return None

    def getOrdersByAddress(self, address):
        """
        Get detailed information of all orders for a specified address
        
        :param address: User address
        :return: List containing detailed information of all orders
        """
        order_ids = self.getOrderIDsByAddress(address)
        orders = []
        
        for order_id in order_ids:
            order = self.getOrderByID(order_id)
            if order:
                orders.append(order)
        
        return orders

    def getAddressHistoryOrders(self, address):
        """
        Get historical order list for a specified address

        :param address: User address
        :return: Historical order list for the address, returns empty list if address doesn't exist
        """
        return self.addressHistoryMap.get(address, [])

    def updateOrderByID(self, orderID, node):
        """
        Update order data by orderID and node parameters

        :param orderID: Order ID
        :param node: Dictionary containing update data
        :return: (bool, str) Whether update was successful and corresponding message
        """
        if orderID in self.orderShortMap:
            current_order = self.orderShortMap[orderID]
            current_order.update(node)
            self.orderShortMap[orderID] = current_order
            return True, "Short order updated successfully"
        elif orderID in self.orderLongMap:
            current_order = self.orderLongMap[orderID]
            current_order.update(node)
            self.orderLongMap[orderID] = current_order
            return True, "Long order updated successfully"
        else:
            return False, "Order ID not found"