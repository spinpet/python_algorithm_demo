# File: shortswapv1factory.py

import random
import string
from erc20factory import erc20_factory_instance
from shortswapv1pool import ShortSwapV1Pool

class ShortSwapV1Factory:
    def __init__(self):
        self.pools = {}

    def createPool(self, address, name, symbol, decimals, totalSupply, shortSupply, tokenBase, tokenBaseAmount):
        # Create a new ERC20 token
        token0 = erc20_factory_instance.createErc20(address, name, symbol, decimals, totalSupply)
        
        # Generate a random virtual pool address
        pool_address = "0x" + ''.join(random.choices(string.hexdigits, k=40)).lower()
        
        # Create ShortSwapV1Pool object  
        pool = ShortSwapV1Pool(factory=self, token0=token0, token1=tokenBase, token0TotalSupply=totalSupply, token0ShortSupply=shortSupply, token1Amount=tokenBaseAmount, poolAddress=pool_address)
        
        # Send all new tokens to pool address
        success, message = erc20_factory_instance.use(address).transfer(token0, pool_address, totalSupply)
        if not success:
            raise Exception(f"Transfer failed: {message}")
        
        # Store pool object
        self.pools[pool_address] = pool
        
        return pool_address

    def getPool(self, pool_address):
        return self.pools.get(pool_address, None)


if __name__ == '__main__':
    # Create ShortSwapV1Factory instance
    factory = ShortSwapV1Factory()

    # Create a new pool
    pool_address = factory.createPool(
        address="0xYourAddress",
        name="TestToken",
        symbol="TTK",
        decimals=18,
        totalSupply=1000000,
        shortSupply=500000,
        tokenBase="0xBaseTokenAddress",
        tokenBaseAmount=100000
    )

    print("Pool Address:", pool_address)

    # Get pool object
    pool = factory.getPool(pool_address)
    if pool:
        print("Pool Details:")
        print("Factory:", pool.factory)
        print("Token0:", pool.token0)
        print("Token1:", pool.token1)
        print("Short Supply:", pool.shortSupply)
        print("Total Supply:", pool.totalSupply)
        print("Pool Address:", pool.poolAddress)
    else:
        print("Pool not found")

