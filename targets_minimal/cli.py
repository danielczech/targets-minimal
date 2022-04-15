import argparse 
import sys

from targets_minimal import TargetsMinimal
from logger import log, set_logger

def cli(args = sys.argv[0]):
    """Command line interface for the automator. 
    """
    usage = '{} [options]'.format(args)
    description = 'Start the Commensal Automator'
    parser = argparse.ArgumentParser(prog = 'automator', 
                                     usage = usage, 
                                     description = description)
    parser.add_argument('--redis_endpoint', 
                        type = str,
                        default = '127.0.0.1:6379', 
                        help = 'Local Redis endpoint')
    parser.add_argument('--redis_channel',
                        type = str,
                        default = 'target-selector', 
                        help = 'Name of the target selector channel.')
    parser.add_argument('--config_file',
                        type = str,
                        default = 'db_config.yml', 
                        help = 'Database configuration file.')
    if(len(sys.argv[1:]) == 0):
        parser.print_help()
        parser.exit()
    args = parser.parse_args()
    main(redis_endpoint = args.redis_endpoint, 
         redis_channel = args.redis_channel,
         config_file = args.config_file)

def main(redis_endpoint, redis_channel, config_file):
    """Starts the minimal target selector.
  
    Args: 
        redis_endpoint (str): Redis endpoint (of the form <host IP
        address>:<port>) 
        redis_chan (str): Name of the target selector Redis channel. 
        config_file (str): Location of the database config file (yml).
    
    Returns:
        None
    """
    set_logger('DEBUG')
    MinimalTargetSelector = TargetsMinimal(redis_endpoint, 
                          redis_channel, config_file)
    MinimalTargetSelector.start()

if(__name__ == '__main__'):
    cli() 
