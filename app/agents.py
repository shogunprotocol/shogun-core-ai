from crewai import Agent, Crew
from yaml import safe_load
import numpy as np
from typing import Dict, List, Any
from .tools import DefiLlamaTool, CryptoNewsTool, VaultTxTool, VaultStateTool, load_config
from .db import AllocationSnapshot
from .arbitrage import get_iwbtc_analytics, get_arbitrage_opportunities
from .iwbtc_vault import perform_ai_rebalance
import json
from web3 import Web3

with open("config/pools.yaml") as f:
    CFG = safe_load(f)
    
# Load CoreDAO config
with open("config/coredao.yaml") as f:
    COREDAO_CFG = safe_load(f)

class ApyScoutAgent(Agent):
    """Agent responsible for gathering APY data from DeFi protocols"""
    
    def __init__(self):
        super().__init__(
            role="APY Data Scout",
            goal="Gather accurate APY data from DeFi protocols to inform rebalancing decisions",
            backstory="""You are an expert DeFi analyst specializing in yield farming opportunities. 
            You have deep knowledge of various lending protocols and their risk profiles.""",
            verbose=True,
            allow_delegation=False,
            tools=[DefiLlamaTool()]
        )
    
    def scout_apy_data(self) -> Dict[str, Any]:
        """Scout APY data for configured strategies"""
        apy_data = {}
        
        # Get IWBTC vault analytics
        iwbtc_data = get_iwbtc_analytics()
        
        # Add CoreDAO specific strategies
        apy_data["iwbtc_vault"] = iwbtc_data["apy"]
        apy_data["arbitrage"] = 0.12  # 12% APY from arbitrage
        apy_data["yield_farming"] = 0.065  # 6.5% from yield farming
        
        # Original strategies
        for strategy in CFG["strategies"]:
            strategy_id = strategy["id"]
            if strategy_id not in apy_data:
                apy_data[strategy_id] = np.random.uniform(0.03, 0.08)
        
        return apy_data

class NewsSentimentAgent(Agent):
    """Agent responsible for analyzing crypto news sentiment"""
    
    def __init__(self):
        super().__init__(
            role="Crypto News Analyst",
            goal="Analyze crypto news sentiment to assess market conditions",
            backstory="""You are a seasoned crypto market analyst with expertise in sentiment analysis. 
            You understand how news events impact DeFi protocols and market dynamics.""",
            verbose=True,
            allow_delegation=False,
            tools=[CryptoNewsTool()]
        )
    
    def analyze_sentiment(self, tokens: List[str] = None) -> Dict[str, Any]:
        """Analyze sentiment for specified tokens"""
        if not tokens:
            tokens = ["USDC", "WETH"]  # Default tokens
        
        sentiment_data = self.tools[0]._run(tokens)
        return sentiment_data

class PortfolioOptimizerAgent(Agent):
    """Agent responsible for portfolio optimization decisions"""
    
    def __init__(self):
        super().__init__(
            role="Portfolio Optimizer",
            goal="Optimize portfolio allocations based on APY data and sentiment",
            backstory="""You are a quantitative portfolio manager specializing in DeFi yield optimization. 
            You use mathematical models to maximize risk-adjusted returns.""",
            verbose=True,
            allow_delegation=False
        )
    
    def run(self, apy_data: dict, sentiment: float, current_alloc: dict):
        """
        Return dict {strategy_id: new_weight}. Very dumb greedy for now.
        """
        deltas = {sid: apy_data[sid] - sum(
            apy_data[s]*current_alloc.get(s, 0) for s in apy_data)
                  for sid in apy_data}
        # sort by delta desc, cap by max_allocation
        target = current_alloc.copy()
        for sid, _ in sorted(deltas.items(), key=lambda x: x[1], reverse=True):
            cap = next(s['max_allocation'] for s in CFG['strategies'] if s['id']==sid)
            target[sid] = cap
        # normalize to 1.0
        total = sum(target.values()) or 1
        target = {k: round(v/total, 4) for k,v in target.items()}
        AllocationSnapshot.save(target)
        return {"action": "REBALANCE", "target_allocs": target}

class VaultManagerAgent(Agent):
    """Agent responsible for executing vault transactions"""
    
    def __init__(self):
        super().__init__(
            role="Vault Transaction Manager",
            goal="Execute vault rebalancing transactions safely and efficiently",
            backstory="""You are a blockchain transaction specialist with deep knowledge of DeFi vaults. 
            You ensure transactions are executed with proper gas optimization and security checks.""",
            verbose=True,
            allow_delegation=False,
            tools=[VaultTxTool()]
        )
    
    def run(self, allocs: dict):
        """Execute vault rebalance transaction"""
        # TODO: Implement actual vault contract interaction
        # This would typically involve:
        # 1. Loading vault ABI
        # 2. Creating contract instance
        # 3. Building transaction
        # 4. Signing and sending
        
        # Mock transaction for development
        mock_tx_hash = "0x" + "0" * 64
        
        return {"tx_hash": mock_tx_hash}

class ArbitrageAgent(Agent):
    """Agent responsible for finding and executing arbitrage opportunities on CoreDAO"""
    
    def __init__(self):
        super().__init__(
            role="CoreDAO Arbitrage Hunter",
            goal="Find and execute profitable arbitrage opportunities for IWBTC",
            backstory="""You are a specialized arbitrage trader focusing on CoreDAO's DeFi ecosystem. 
            You monitor IWBTC/wBTC price differentials and triangular arbitrage paths.""",
            verbose=True,
            allow_delegation=False
        )
    
    def find_opportunities(self) -> Dict[str, Any]:
        """Find current arbitrage opportunities"""
        opportunities = get_arbitrage_opportunities()
        
        # Filter for profitable opportunities
        profitable = [
            opp for opp in opportunities 
            if opp.get("profit_pct", 0) > 0.5 or opp.get("premium_pct", 0) > 0.3
        ]
        
        return {
            "total_opportunities": len(opportunities),
            "profitable": len(profitable),
            "best_opportunity": profitable[0] if profitable else None,
            "opportunities": profitable[:3]  # Top 3 opportunities
        }

def create_rebalance_crew():
    """Create the rebalance crew with all agents"""
    apy_agent = ApyScoutAgent()
    news_agent = NewsSentimentAgent()
    optimizer_agent = PortfolioOptimizerAgent()
    vault_agent = VaultManagerAgent()
    arbitrage_agent = ArbitrageAgent()  # New CoreDAO arbitrage agent
    
    crew = Crew(
        agents=[apy_agent, news_agent, optimizer_agent, vault_agent, arbitrage_agent],
        verbose=True
    )
    
    return crew 