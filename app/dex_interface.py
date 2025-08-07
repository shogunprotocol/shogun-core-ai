"""
CoreDAO DEX Interface - Real price fetching from on-chain
Connects to IceCreamSwap and other CoreDAO DEXes
"""

from web3 import Web3
from typing import Dict, List, Tuple, Optional
import json
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# Uniswap V2 style Router ABI (works with most forks)
ROUTER_ABI = [
    {
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "path", "type": "address[]"}
        ],
        "name": "getAmountsOut",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "factory",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Factory ABI for getting pairs
FACTORY_ABI = [
    {
        "inputs": [
            {"name": "tokenA", "type": "address"},
            {"name": "tokenB", "type": "address"}
        ],
        "name": "getPair",
        "outputs": [{"name": "pair", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "allPairsLength",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "", "type": "uint256"}],
        "name": "allPairs",
        "outputs": [{"name": "pair", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Pair ABI for getting reserves
PAIR_ABI = [
    {
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {"name": "_reserve0", "type": "uint112"},
            {"name": "_reserve1", "type": "uint112"},
            {"name": "_blockTimestampLast", "type": "uint32"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token0",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token1",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# ERC20 ABI for token info
ERC20_ABI = [
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

class CoreDAODEX:
    """Interface for interacting with CoreDAO DEXes"""
    
    def __init__(self, w3: Web3, router_address: str, factory_address: str, name: str = "DEX"):
        self.w3 = w3
        self.name = name
        self.router_address = Web3.to_checksum_address(router_address)
        self.factory_address = Web3.to_checksum_address(factory_address)
        
        # Initialize contracts
        self.router = w3.eth.contract(address=self.router_address, abi=ROUTER_ABI)
        self.factory = w3.eth.contract(address=self.factory_address, abi=FACTORY_ABI)
        
        # Cache for token decimals
        self.decimals_cache = {}
        
    def get_pair_address(self, token0: str, token1: str) -> Optional[str]:
        """Get the pair address for two tokens"""
        try:
            token0 = Web3.to_checksum_address(token0)
            token1 = Web3.to_checksum_address(token1)
            pair_address = self.factory.functions.getPair(token0, token1).call()
            
            if pair_address == "0x0000000000000000000000000000000000000000":
                return None
                
            return pair_address
        except Exception as e:
            logger.error(f"Failed to get pair address: {e}")
            return None
    
    def get_reserves(self, pair_address: str) -> Optional[Tuple[int, int]]:
        """Get reserves for a pair"""
        try:
            pair_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(pair_address), 
                abi=PAIR_ABI
            )
            reserves = pair_contract.functions.getReserves().call()
            return (reserves[0], reserves[1])
        except Exception as e:
            logger.error(f"Failed to get reserves: {e}")
            return None
    
    def get_token_decimals(self, token_address: str) -> int:
        """Get token decimals (cached)"""
        if token_address in self.decimals_cache:
            return self.decimals_cache[token_address]
        
        try:
            token = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )
            decimals = token.functions.decimals().call()
            self.decimals_cache[token_address] = decimals
            return decimals
        except:
            # Default to 18 if can't fetch
            return 18
    
    def get_price(self, token_in: str, token_out: str, amount_in: float = 1.0) -> Optional[float]:
        """Get price for swapping token_in to token_out"""
        try:
            token_in = Web3.to_checksum_address(token_in)
            token_out = Web3.to_checksum_address(token_out)
            
            # Get decimals
            decimals_in = self.get_token_decimals(token_in)
            decimals_out = self.get_token_decimals(token_out)
            
            # Convert amount to wei
            amount_in_wei = int(amount_in * 10**decimals_in)
            
            # Get amounts out from router
            amounts = self.router.functions.getAmountsOut(
                amount_in_wei,
                [token_in, token_out]
            ).call()
            
            # Convert back to human readable
            amount_out = amounts[1] / 10**decimals_out
            
            return amount_out
            
        except Exception as e:
            logger.error(f"Failed to get price on {self.name}: {e}")
            return None
    
    def get_price_impact(self, token_in: str, token_out: str, amount_in: float) -> Optional[float]:
        """Calculate price impact for a trade"""
        try:
            # Get price for small amount (no impact)
            small_price = self.get_price(token_in, token_out, 0.001)
            if not small_price:
                return None
            
            # Get price for actual amount
            actual_price = self.get_price(token_in, token_out, amount_in)
            if not actual_price:
                return None
            
            # Calculate impact
            impact = abs(1 - (actual_price / amount_in) / (small_price / 0.001))
            return impact
            
        except Exception as e:
            logger.error(f"Failed to calculate price impact: {e}")
            return None

class IceCreamSwap(CoreDAODEX):
    """IceCreamSwap specific implementation"""
    
    def __init__(self, w3: Web3):
        super().__init__(
            w3,
            router_address="0xBb5e1777A331ED93E07cF043363e48d320eb96c4",
            factory_address="0x9E6d21E759A7A288b80eef94E4737D313D31c13f",
            name="IceCreamSwap"
        )
        
        # IceCreamSwap specific tokens
        self.tokens = {
            "ICE": "0xc0E49f8C615d3d4c245970F6Dc528E4A47d69a44",
            "SCORE": "0xA20b3B97df3a02f9185175760300a06B4e0A2C05",
            "WCORE": "0x40375C92d9FAf44d2f9db9Bd9ba41a3317a2404f"
        }
    
    def get_ice_pools(self) -> List[Dict]:
        """Get all ICE token pools"""
        pools = []
        try:
            ice_address = self.tokens["ICE"]
            
            # Check ICE pairs with major tokens
            for token_name, token_address in self.tokens.items():
                if token_name == "ICE":
                    continue
                    
                pair_address = self.get_pair_address(ice_address, token_address)
                if pair_address:
                    reserves = self.get_reserves(pair_address)
                    if reserves:
                        pools.append({
                            "pair": f"ICE/{token_name}",
                            "address": pair_address,
                            "reserves": reserves,
                            "dex": "IceCreamSwap"
                        })
                        
        except Exception as e:
            logger.error(f"Failed to get ICE pools: {e}")
            
        return pools

class ArbitrageScanner:
    """Scans for arbitrage opportunities across CoreDAO DEXes"""
    
    def __init__(self, w3: Web3):
        self.w3 = w3
        self.dexes = {}
        
        # Initialize IceCreamSwap (only verified DEX for now)
        self.dexes["icecreamswap"] = IceCreamSwap(w3)
        
    def find_triangular_arbitrage(self, tokens: List[str], dex_name: str = "icecreamswap") -> List[Dict]:
        """Find triangular arbitrage opportunities"""
        opportunities = []
        dex = self.dexes.get(dex_name)
        
        if not dex:
            logger.error(f"DEX {dex_name} not found")
            return opportunities
        
        # Check all triangular paths
        for i in range(len(tokens)):
            for j in range(len(tokens)):
                if i == j:
                    continue
                for k in range(len(tokens)):
                    if k == i or k == j:
                        continue
                    
                    # Path: token[i] -> token[j] -> token[k] -> token[i]
                    path = [tokens[i], tokens[j], tokens[k], tokens[i]]
                    
                    try:
                        # Calculate prices for each leg
                        price1 = dex.get_price(tokens[i], tokens[j], 1.0)
                        if not price1:
                            continue
                            
                        price2 = dex.get_price(tokens[j], tokens[k], price1)
                        if not price2:
                            continue
                            
                        price3 = dex.get_price(tokens[k], tokens[i], price2)
                        if not price3:
                            continue
                        
                        # Calculate profit
                        profit = price3 - 1.0
                        profit_pct = profit * 100
                        
                        if profit_pct > 0.1:  # Only log if > 0.1% profit
                            opportunities.append({
                                "type": "triangular",
                                "dex": dex_name,
                                "path": path,
                                "profit_pct": profit_pct,
                                "input_amount": 1.0,
                                "output_amount": price3,
                                "profitable": profit_pct > 0.3  # 0.3% threshold
                            })
                            
                    except Exception as e:
                        logger.debug(f"Failed to calculate path {path}: {e}")
                        
        return opportunities
    
    def find_cross_dex_arbitrage(self, token_in: str, token_out: str) -> List[Dict]:
        """Find arbitrage between different DEXes"""
        opportunities = []
        
        # Get prices from all DEXes
        prices = {}
        for dex_name, dex in self.dexes.items():
            price = dex.get_price(token_in, token_out)
            if price:
                prices[dex_name] = price
        
        # Find price differences
        if len(prices) >= 2:
            dex_names = list(prices.keys())
            for i in range(len(dex_names)):
                for j in range(i+1, len(dex_names)):
                    dex1, dex2 = dex_names[i], dex_names[j]
                    price1, price2 = prices[dex1], prices[dex2]
                    
                    # Calculate arbitrage opportunity
                    if price1 > price2:
                        # Buy on dex2, sell on dex1
                        profit_pct = ((price1 / price2) - 1) * 100
                        if profit_pct > 0.1:
                            opportunities.append({
                                "type": "cross_dex",
                                "buy_dex": dex2,
                                "sell_dex": dex1,
                                "token_in": token_in,
                                "token_out": token_out,
                                "buy_price": price2,
                                "sell_price": price1,
                                "profit_pct": profit_pct,
                                "profitable": profit_pct > 0.3
                            })
                    else:
                        # Buy on dex1, sell on dex2
                        profit_pct = ((price2 / price1) - 1) * 100
                        if profit_pct > 0.1:
                            opportunities.append({
                                "type": "cross_dex",
                                "buy_dex": dex1,
                                "sell_dex": dex2,
                                "token_in": token_in,
                                "token_out": token_out,
                                "buy_price": price1,
                                "sell_price": price2,
                                "profit_pct": profit_pct,
                                "profitable": profit_pct > 0.3
                            })
                            
        return opportunities

def get_pool_analytics(w3: Web3) -> Dict:
    """Get analytics for all pools on CoreDAO"""
    analytics = {
        "dexes": {},
        "top_pools": [],
        "total_tvl": 0
    }
    
    try:
        # Initialize IceCreamSwap
        ice_dex = IceCreamSwap(w3)
        
        # Get ICE pools
        ice_pools = ice_dex.get_ice_pools()
        
        analytics["dexes"]["icecreamswap"] = {
            "pools_found": len(ice_pools),
            "pools": ice_pools
        }
        
        # Get top pools by reserves
        for pool in ice_pools:
            analytics["top_pools"].append({
                "pair": pool["pair"],
                "dex": pool["dex"],
                "reserves": pool["reserves"]
            })
            
    except Exception as e:
        logger.error(f"Failed to get pool analytics: {e}")
        
    return analytics