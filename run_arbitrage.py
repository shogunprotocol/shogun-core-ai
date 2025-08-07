#!/usr/bin/env python3
"""
Main entry point for CoreDAO IWBTC Arbitrage Bot
Run with: python run_arbitrage.py
"""

import sys
import os
import asyncio
import argparse
import logging
from datetime import datetime
from typing import Optional

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.arbitrage import CoreDAOArbitrageBot
from app.iwbtc_vault import IWBTCVault, IWBTCStrategy, get_iwbtc_vault_interface
from app.agents import create_rebalance_crew
from web3 import Web3

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/arbitrage_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_arbitrage_bot():
    """Run the arbitrage bot in scanning mode"""
    logger.info("=" * 50)
    logger.info("Starting CoreDAO IWBTC Arbitrage Bot")
    logger.info("=" * 50)
    
    bot = CoreDAOArbitrageBot()
    bot.run()

def run_vault_rebalance():
    """Run AI-driven vault rebalancing"""
    logger.info("=" * 50)
    logger.info("Starting IWBTC Vault Rebalance")
    logger.info("=" * 50)
    
    # Setup Web3
    w3 = Web3(Web3.HTTPProvider("https://rpc.coredao.org"))
    
    # Perform rebalance
    result = perform_ai_rebalance(w3)
    logger.info(f"Rebalance result: {result}")
    
    return result

def run_crew_analysis():
    """Run the full CrewAI agent analysis"""
    logger.info("=" * 50)
    logger.info("Starting CrewAI Multi-Agent Analysis")
    logger.info("=" * 50)
    
    crew = create_rebalance_crew()
    result = crew.kickoff()
    
    logger.info(f"Crew analysis complete: {result}")
    return result

def check_system_status():
    """Check system status and connectivity"""
    logger.info("Checking system status...")
    
    # Check Web3 connection
    w3 = Web3(Web3.HTTPProvider("https://rpc.coredao.org"))
    if w3.is_connected():
        logger.info(f"✓ Connected to CoreDAO (Chain ID: {w3.eth.chain_id})")
        logger.info(f"✓ Latest block: {w3.eth.block_number}")
    else:
        logger.error("✗ Failed to connect to CoreDAO")
        return False
    
    # Check wallet
    if os.getenv("PRIVATE_KEY"):
        from eth_account import Account
        account = Account.from_key(os.getenv("PRIVATE_KEY"))
        balance = w3.eth.get_balance(account.address)
        logger.info(f"✓ Wallet configured: {account.address}")
        logger.info(f"  Balance: {w3.from_wei(balance, 'ether')} CORE")
    else:
        logger.warning("⚠ No private key configured - running in read-only mode")
    
    # Check configs
    import yaml
    try:
        with open("config/coredao.yaml", "r") as f:
            config = yaml.safe_load(f)
            logger.info("✓ CoreDAO config loaded")
    except Exception as e:
        logger.error(f"✗ Failed to load config: {e}")
        return False
    
    logger.info("System check complete!")
    return True

def main():
    """Main entry point with CLI arguments"""
    parser = argparse.ArgumentParser(description="CoreDAO IWBTC Arbitrage Bot")
    parser.add_argument(
        "--mode",
        choices=["arbitrage", "rebalance", "crew", "status", "demo", "pools"],
        default="status",
        help="Operation mode"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in simulation mode without executing trades"
    )
    
    args = parser.parse_args()
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    try:
        if args.mode == "status":
            check_system_status()
            
        elif args.mode == "arbitrage":
            if args.dry_run:
                logger.info("Running in DRY RUN mode - no actual trades will be executed")
                os.environ["DRY_RUN"] = "true"
            run_arbitrage_bot()
            
        elif args.mode == "rebalance":
            if args.dry_run:
                logger.info("Running in DRY RUN mode - no actual rebalancing will occur")
                os.environ["DRY_RUN"] = "true"
            run_vault_rebalance()
            
        elif args.mode == "crew":
            run_crew_analysis()
            
        elif args.mode == "pools":
            logger.info("=" * 50)
            logger.info("CoreDAO Pool Analysis")
            logger.info("=" * 50)
            
            from app.arbitrage import CoreDAOArbitrageBot
            bot = CoreDAOArbitrageBot()
            if bot.setup_web3():
                import asyncio
                analytics = asyncio.run(bot.analyze_pools())
                
                logger.info("\n📊 Pool Analysis Results:")
                for dex_name, data in analytics["dexes"].items():
                    logger.info(f"\n{dex_name.upper()}:")
                    logger.info(f"  Status: {'✅ Connected' if data['pools_found'] > 0 else '❌ No pools found'}")
                    logger.info(f"  Pools: {data['pools_found']}")
                    
                    for pool in data.get("pools", [])[:5]:  # Show first 5 pools
                        reserves = pool.get("reserves", (0, 0))
                        logger.info(f"    - {pool['pair']}: Reserves [{reserves[0]}, {reserves[1]}]")
            
        elif args.mode == "demo":
            logger.info("=" * 50)
            logger.info("DEMO MODE - Showing IWBTC System Capabilities")
            logger.info("=" * 50)
            
            # 1. Check status
            logger.info("\n1. System Status Check:")
            check_system_status()
            
            # 2. Analyze pools
            logger.info("\n2. CoreDAO Pool Analysis:")
            from app.arbitrage import CoreDAOArbitrageBot
            bot = CoreDAOArbitrageBot()
            if bot.setup_web3():
                import asyncio
                analytics = asyncio.run(bot.analyze_pools())
                total_pools = sum(dex["pools_found"] for dex in analytics["dexes"].values())
                logger.info(f"   Connected DEXes: {len(analytics['dexes'])}")
                logger.info(f"   Total pools monitored: {total_pools}")
            
            # 3. Find arbitrage opportunities
            logger.info("\n3. Scanning for REAL Arbitrage Opportunities:")
            from app.arbitrage import get_arbitrage_opportunities
            opportunities = get_arbitrage_opportunities()
            if opportunities:
                for i, opp in enumerate(opportunities[:3], 1):
                    profit = opp.get("profit_pct", 0)
                    logger.info(f"   Opportunity {i}: {opp.get('type', 'unknown')} - {profit:.3f}% profit")
            else:
                logger.info("   No profitable opportunities found at this time")
            
            # 4. Show vault analytics
            logger.info("\n4. IWBTC Vault Analytics:")
            from app.arbitrage import get_iwbtc_analytics
            analytics = get_iwbtc_analytics()
            for key, value in analytics.items():
                logger.info(f"   {key}: {value}")
            
            logger.info("\n" + "=" * 50)
            logger.info("Demo complete!")
            logger.info("Next steps:")
            logger.info("  --mode=pools     : Analyze all CoreDAO pools")
            logger.info("  --mode=arbitrage : Start real arbitrage scanning")
            logger.info("  --mode=arbitrage --dry-run : Safe simulation mode")
            
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()