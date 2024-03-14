import argparse
import sys

from target_selector.selector import Selector
from target_selector.logger import set_logger

def cli(args = sys.argv[0]):
    """Command line interface for the target selector.
    """
    usage = '{} [options]'.format(args)
    description = 'Target selector for commensal beamforming searches.'
    parser = argparse.ArgumentParser(prog = 'targetselector',
                                     usage = usage,
                                     description = description)
    parser.add_argument('--redis_endpoint',
                        type = str,
                        default = '127.0.0.1:6379',
                        help = 'Local Redis endpoint')
    parser.add_argument('--pointing_channel',
                        type = str,
                        default = 'target-selector:pointings',
                        help = 'Channel from which new pointings will be received.')
    parser.add_argument('--targets_channel',
                        type = str,
                        default = 'target-selector:targets',
                        help = 'Channel to which targets will be published.')
    parser.add_argument('--processing_channel',
                        type = str,
                        default = 'target-selector:processing',
                        help = 'Channel from which processing messages will be received.')
    parser.add_argument('--config_file',
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
         config_file = args.config_file,
         diameter = args.diameter)

def main(redis_endpoint, pointing_chan, targets_chan, proc_chan, config_file,
         diameter):
    """Starts the minimal target selector.

    Args:
        redis_endpoint (str): Redis endpoint (< host IP address>:<port>)
        pointing_chan (str): Channel from which the target selector will
        receive new pointing information.
        targets_chan (str): Channel to which the target selector will publish
        new target information.
        proc_chan (str): Channel from which the target selector will receive
        information about completed processing segments.
        config_file (str): Location of the database config file (yml).
        d (float): diameter of telescope antenna (used in generic FoV
        calculation) in meters.
    """
    set_logger('DEBUG')
    TargetSelector = Selector(redis_endpoint, pointing_chan, targets_chan,
                              proc_chan, config_file, diameter)
    TargetSelector.start()

if(__name__ == '__main__'):
    cli()
