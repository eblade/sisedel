import os
import logging
import argparse
import configparser

from samtt import init

from . import web
from . import token
from . import records
from . import testcase


if __name__ == '__main__':
    # Options
    parser = argparse.ArgumentParser(usage="sisedel")
    parser.add_argument(
        '-c', '--config', default='sisedel.ini',
        help='specify what config file to run with')
    parser.add_argument(
        '-g', '--debug', action="store_true",
        help='show debug messages')
    parser.add_argument(
        '-t', '--create-token',
        help='create a new token for name:run')

    args = parser.parse_args()

    # Logging
    FORMAT = '%(asctime)s [%(threadName)s] %(filename)s +%(levelno)s ' + \
             '%(funcName)s %(levelname)s %(message)s'
    logging.basicConfig(
        format=FORMAT,
        level=(logging.DEBUG if args.debug else logging.INFO),
    )

    # Config file
    config = configparser.ConfigParser()
    config.read(args.config)
    testcase.ROOT = config['Database']['test case folder']
    logging.info("Test case folder is %s", testcase.ROOT)
    token.BASE_URI = config['Server']['base uri']
    logging.info("Base URI is %s", token.BASE_URI)
    logging.info("Config read from %s", args.config)

    # Database
    sql_path = config['Database']['path']
    logging.info("SQL Path: %s", sql_path)
    logging.info("Setting up database...")
    db = init(sql_path)
    db.create_all()
    logging.info("Done setting up database.")

    # Create token mode
    if args.create_token is not None:
        name, run = args.create_token.split(':')
        new_token = token.create_token(name, run)
        logging.info("Token created: %s" % new_token.link)
        exit(0)

    # Web Server settings
    server_host = config['Server']['host']
    server_port = int(config['Server']['port'])
    logging.info("Setting up Web-Apps...")
    app = web.App.create()
    for module in (token, records, testcase):
        logging.info(
            "Setting up %s on %s..." % (module.__name__, module.App.BASE)
        )
        app.mount(module.App.BASE, module.App.create())
    logging.info("Done setting up Web-apps.")

    # Serve the Web-App
    app.run(
        host=server_host,
        port=server_port,
    )
