import sys
import logging
import argparse
from pathlib import Path
sys.path.insert(0, '.')

def main():
    parser = argparse.ArgumentParser(description='Dark Line Analysis')
    parser.add_argument('-d', '--date', type=str, default=None)
    parser.add_argument('-q', '--quiet', action='store_true')
    args = parser.parse_args()
    
    if args.quiet:
        logging.basicConfig(level=logging.ERROR)
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    
    logger = logging.getLogger(__name__)
    
    if args.date:
        date = args.date
    else:
        from datetime import datetime, timedelta
        date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    logger.info(f'Starting analysis: {date}')
    
    try:
        from config.config_manager import ConfigManager
        from src.agent import DarkLineAgent
        
        config = ConfigManager()
        agent = DarkLineAgent(config)
        
        result = agent.analyze(date=date)
        
        logger.info(f'Limit up stocks: {result.limit_up_count}')
        logger.info(f'Dark lines found: {len(result.dark_lines)}')
        
        for i, dl in enumerate(result.dark_lines, 1):
            if isinstance(dl, dict):
                title = dl.get('title', 'Unknown')
                conf = dl.get('confidence', 0)
            else:
                title = getattr(dl, 'title', 'Unknown')
                conf = getattr(dl, 'confidence', 0)
            logger.info(f'{i}. {title}: confidence={conf:.2f}')
        
    except Exception as e:
        logger.error(f'Error: {e}')
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
