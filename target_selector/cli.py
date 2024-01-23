import argparse
import sys

from target_selector.selector import Selector
from target_selector.logger import set_logger

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
    parser.add_argument('--pointing_channel',
                        type = str,
                        default = 'target-selector:pointings',
                        help = 'Name of the channel from which information about new pointings will be received.')
    parser.add_argument('--targets_channel',
                        type = str,
                        default = 'target-selector:targets',
                        help = 'Name of the channel to which targets information will be published.')
    parser.add_argument('--processing_channel',
                        type = str,
                        default = 'target-selector:processing',
                        help = 'Name of the channel to which targets information will be published.')
    parser.add_argument('--config',
                        type = str,
                        default = 'config.yml',
                        help = 'Database configuration file.')
    parser.add_argument('--diameter',
                        type = float,
                        default = 13.5,
                        help = 'Diameter of antenna for generic FoV estimate.')
    if(len(sys.argv[1:]) == 0):
        parser.print_help()
        parser.exit()
    args = parser.parse_args()
    main(redis_endpoint = args.redis_endpoint,
         pointing_chan = args.pointing_channel,
         targets_chan = args.targets_channel,
         proc_chan = args.processing_channel,
         config = args.config,
         d = args.diameter)

def main(redis_endpoint, pointing_chan, targets_chan, proc_chan, config, d):
    """Starts the minimal target selector.

    Args:
        redis_endpoint (str): Redis endpoint (of the form <host IP
        address>:<port>)
        pointing_channel (str): Name of the channel from which the minimal target
        selector will receive new pointing information.
        targets_channel (str): Name of the channel to which the minimal target
        selector will publish target information.
        config_file (str): Location of the database config file (yml).

    Returns:
        None
    """
    set_logger('DEBUG')
    TargetSelector = Selector(redis_endpoint, pointing_chan, targets_chan,
                              proc_chan, config, d)
    TargetSelector.start()

if(__name__ == '__main__'):
    cli()
