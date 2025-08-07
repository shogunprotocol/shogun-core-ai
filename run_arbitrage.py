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
from app.iwbtc_vault import IWBTCVault
from app.agents import ShogunAIAgents
from web3 import Web3
from decimal import Decimal

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

async def run_vault_demo():
    """Run IWBTC Vault demonstration"""
    logger.info("=" * 50)
    logger.info("Starting IWBTC Vault Demo")
    logger.info("=" * 50)
    
    try:
        # Initialize vault
        vault = IWBTCVault()
        
        # Simulate institutional deposit
        logger.info("Simulating institutional deposit of 5 BTC...")
        deposit_result = await vault.deposit_btc(
            Decimal('5.0'), 
            '0x1234567890abcdef1234567890abcdef12345678',
            'institutional'
        )
        
        if deposit_result['success']:
            logger.info(f"✓ Deposit successful: {deposit_result['iwbtc_minted']:.4f} IWBTC minted")
            logger.info(f"  NAV per share: {deposit_result['nav_per_share']:.6f}")
            logger.info(f"  Expected annual yield: {deposit_result['estimated_annual_yield']}")
        
        # Get vault status
        logger.info("\nVault Status:")
        status = await vault.get_institutional_vault_status()
        for key, value in status['vault_overview'].items():
            logger.info(f"  {key}: {value}")
            
        # Generate institutional report
        logger.info("\nGenerating institutional compliance report...")
        report = await vault.generate_compliance_report()
        logger.info(f"✓ Report generated for {report.get('report_metadata', {}).get('report_period', 'N/A')}")
        
        return {
            'vault_status': status,
            'deposit_result': deposit_result,
            'compliance_report': report
        }
        
    except Exception as e:
        logger.error(f"Vault demo failed: {e}")
        return {'error': str(e)}

async def run_ai_analysis():
    """Run Shogun AI agents analysis"""
    logger.info("=" * 50)
    logger.info("Starting Shogun AI Multi-Agent Analysis")
    logger.info("=" * 50)
    
    try:
        ai_agents = ShogunAIAgents()
        
        # Sample market data
        market_data = {
            'protocols': {
                'archerswap': {'apy': 14.2, 'tvl': 25000000, 'risk_score': 7.8},
                'icecreamswap': {'apy': 12.4, 'tvl': 15000000, 'risk_score': 8.1},
                'lfgswap': {'apy': 9.8, 'tvl': 8200000, 'risk_score': 7.5}
            },
            'prices': {
                'WCORE/WBTC': {'archerswap': 0.000123, 'icecreamswap': 0.000124},
                'WCORE/USDT': {'archerswap': 2.45, 'icecreamswap': 2.47}
            },
            'news': [
                'CoreDAO TVL reaches $300M milestone',
                'Bitcoin institutional adoption accelerating',
                'DeFi yields stabilizing across major protocols'
            ]
        }
        
        # Client profile for institutional analysis
        client_profile = {
            'type': 'family_office',
            'volume': 10.0,  # 10 BTC
            'risk_profile': 'moderate'
        }
        
        # Run comprehensive analysis
        result = await ai_agents.coordinate_institutional_analysis(market_data, client_profile)
        
        logger.info("✓ AI Analysis completed")
        logger.info(f"  Status: {result.get('status', 'unknown')}")
        logger.info(f"  Client type: {result.get('client_type', 'unknown')}")
        
        return result
        
    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        return {'error': str(e)}

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
        choices=["arbitrage", "vault", "ai", "status", "demo", "pools"],
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
            
        elif args.mode == "vault":
            if args.dry_run:
                logger.info("Running in DRY RUN mode - no actual vault operations will occur")
                os.environ["DRY_RUN"] = "true"
            import asyncio
            result = asyncio.run(run_vault_demo())
            logger.info(f"Vault demo result: {result.get('vault_status', {}).get('operational_status', {})}")
            
        elif args.mode == "ai":
            import asyncio
            result = asyncio.run(run_ai_analysis())
            logger.info(f"AI analysis completed with status: {result.get('status', 'unknown')}")
            
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
            
            # 5. Demonstrate IWBTC vault
            logger.info("\n5. IWBTC Vault Demo:")
            import asyncio
            vault_demo = asyncio.run(run_vault_demo())
            if vault_demo.get('vault_status'):
                vault_overview = vault_demo['vault_status']['vault_overview']
                logger.info(f"   Vault NAV: {vault_overview.get('vault_nav', 0):.4f} BTC")
                logger.info(f"   NAV per share: {vault_overview.get('nav_per_share', 1.0):.6f}")
                logger.info(f"   Expected yield: {vault_demo['vault_status']['performance_metrics'].get('current_annual_yield', 'N/A')}")
            
            # 6. AI Analysis Demo
            logger.info("\n6. AI Analysis Demo:")
            ai_demo = asyncio.run(run_ai_analysis())
            if ai_demo.get('status') == 'success':
                logger.info("   ✓ Multi-agent analysis successful")
                logger.info("   ✓ Institutional portfolio optimization complete")
                logger.info("   ✓ Market sentiment and arbitrage analysis done")
            elif ai_demo.get('status') == 'simulation_success':
                logger.info("   ✓ AI analysis running in simulation mode (no OpenAI key)")
                logger.info("   ✓ Institutional features demonstrated successfully")
            
            logger.info("\n" + "=" * 50)
            logger.info("Demo complete!")
            logger.info("Next steps:")
            logger.info("  --mode=pools     : Analyze all CoreDAO pools")
            logger.info("  --mode=arbitrage : Start real arbitrage scanning") 
            logger.info("  --mode=vault     : Run IWBTC vault operations")
            logger.info("  --mode=ai        : Run AI multi-agent analysis")
            logger.info("  --mode=arbitrage --dry-run : Safe simulation mode")
            
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()