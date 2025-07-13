# File: erc20factory.py

import random
import string

class Erc20Factory:
    def __init__(self):
        self.tokens = {}
        self.balances = {}

    def createErc20(self, address, name, symbol, decimals, totalSupply):
        # Generate a random virtual contract address
        contract_address = "0x" + ''.join(random.choices(string.hexdigits, k=40)).lower()
        self.tokens[contract_address] = {
            "name": name,
            "symbol": symbol,
            "decimals": decimals,
            "totalSupply": totalSupply,
            "balances": {address: totalSupply}
        }
        self.balances[address] = totalSupply
        return contract_address

    def createErc20Test(self, address, name, symbol, decimals, totalSupply, contract_address):
        # Use fixed contract address
        self.tokens[contract_address] = {
            "name": name,
            "symbol": symbol,
            "decimals": decimals,
            "totalSupply": totalSupply,
            "balances": {address: totalSupply}
        }
        self.balances[address] = totalSupply
        return contract_address

    def name(self, contract_address):
        return self.tokens[contract_address]["name"]

    def symbol(self, contract_address):
        return self.tokens[contract_address]["symbol"]

    def decimals(self, contract_address):
        return self.tokens[contract_address]["decimals"]

    def totalSupply(self, contract_address):
        return self.tokens[contract_address]["totalSupply"]

    def balanceOf(self, contract_address, owner):
        if contract_address not in self.tokens:
            return 0
        return self.tokens[contract_address]["balances"].get(owner, 0)

    def transfer(self, contract_address, to, value):
        #print("self.tokens =",self.tokens)
        
        from_address = self.current_address
        print("Address:", from_address[0:8],"Balance:",self.tokens[contract_address]["balances"].get(from_address, 0),  "Transfer to:", to[0:8], "Amount:", value,"Token contract:", contract_address[0:8])
        
        if self.tokens[contract_address]["balances"].get(from_address, 0) >= value:
            # If recipient address doesn't exist, create it and set balance to 0
            if to not in self.tokens[contract_address]["balances"]:
                self.tokens[contract_address]["balances"][to] = 0
            self.tokens[contract_address]["balances"][from_address] -= value
            self.tokens[contract_address]["balances"][to] += value
            return True, "Transfer successful"
        else:
            return False, "Insufficient balance"

    def transferFrom(self, contract_address, from_address, to, value):
        
        if self.tokens[contract_address]["balances"].get(from_address, 0) >= value:
            # If recipient address doesn't exist, create it and set balance to 0
            if to not in self.tokens[contract_address]["balances"]:
                self.tokens[contract_address]["balances"][to] = 0
            self.tokens[contract_address]["balances"][from_address] -= value
            self.tokens[contract_address]["balances"][to] += value
            return True, "Transfer successful"
        else:
            return False, "Insufficient balance"

    def use(self, address):
        self.current_address = address
        return self

    def allBalanceOf(self, owner):
        balances = {}
        for contract_address, token in self.tokens.items():
            balance = token["balances"].get(owner, 0)
            if balance > 0:
                balances[contract_address] = {
                    "name": token["name"],
                    "symbol": token["symbol"],
                    "balance": balance,
                    "contract_address": contract_address
                }
        return balances

    def airdrop(self, contract_address, recipients):
        """
        Airdrop tokens to multiple addresses
        
        :param contract_address: Token contract address
        :param recipients: Dictionary with recipient addresses as keys and airdrop amounts as values
        :return: Boolean indicating success and corresponding message
        """
        if contract_address not in self.tokens:
            
            
            return False, "Token contract does not exist"

        for address, amount in recipients.items():
            if address not in self.tokens[contract_address]["balances"]:
                self.tokens[contract_address]["balances"][address] = 0
            self.tokens[contract_address]["balances"][address] += amount
            self.tokens[contract_address]["totalSupply"] += amount

        return True, "Airdrop completed successfully"

# Example usage
if __name__ == '__main__':
    # Example code demonstrating the usage of Erc20Factory class

    # Create Erc20Factory instance
    factory = Erc20Factory()

    # Create a new ERC20 token
    contract_address = factory.createErc20(
        address="0xYourAddress",
        name="TestToken",
        symbol="TTK",
        decimals=18,
        totalSupply=1000000
    )

    # Use the use method to set current operating address
    factory.use("0xYourAddress")

    print("contract_address:",contract_address)

    # Get token name
    print("Token Name:", factory.name(contract_address))

    # Get token symbol
    print("Token Symbol:", factory.symbol(contract_address))

    # Get token decimals
    print("Token Decimals:", factory.decimals(contract_address))

    # Get token total supply
    print("Total Supply:", factory.totalSupply(contract_address))

    # Get balance of an address
    print("Balance of 0xYourAddress:", factory.balanceOf(contract_address, "0xYourAddress"))

    # Transfer tokens
    success, message = factory.use("0xYourAddress").transfer(contract_address, "0xRecipientAddress", 500)
    print("Transfer Status:", success, "Message:", message)

    # Get recipient address balance
    print("Balance of 0xRecipientAddress:", factory.balanceOf(contract_address, "0xRecipientAddress"))

    # Transfer tokens from one address to another
    success, message = factory.transferFrom(contract_address, "0xYourAddress", "0xAnotherAddress", 200)
    print("TransferFrom Status:", success, "Message:", message)

    # Get address balance after transfer
    print("Balance of 0xAnotherAddress:", factory.balanceOf(contract_address, "0xAnotherAddress"))

    # Get all token information and amounts for an address
    all_balances = factory.allBalanceOf("0xYourAddress")
    print("All Balances of 0xYourAddress:", all_balances)

    # Create a new ERC20 token using fixed contract address
    test_contract_address = "0xFixedContractAddress"
    contract_address = factory.createErc20Test(
        address="0xYourAddress",
        name="TestToken",
        symbol="TTK",
        decimals=18,
        totalSupply=1000000,
        contract_address=test_contract_address
    )

    print("Test contract_address:", contract_address)


# Create global singleton
erc20_factory_instance = Erc20Factory()

