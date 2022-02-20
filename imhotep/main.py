import json
import logging
import os
import sys

from imhotep import app
from imhotep.errors import NoCommitInfo, UnknownTools
from imhotep.http_client import NoGithubCredentials


log = logging.getLogger(__name__)


def load_config(filename):
    config = {}
    if filename is not None:
        config_path = os.path.abspath(filename)
        try:
            with open(config_path) as f:
                config = json.loads(f.read())
        except IOError:
            log.error("Could not open config file %s", config_path)
        except ValueError:
            log.error("Could not parse config file %s", config_path)
    return config


def main():
    """
    Main entrypoint for the command-line app.
    """
    args = app.parse_args(sys.argv[1:])
    params = args.__dict__
    params.update(**load_config(args.config_file))

    if params['debug']:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig()

    try:
        imhotep = app.gen_imhotep(**params)
    except NoGithubCredentials:
        log.error("You must specify a GitHub username or password.")
        return False
    except NoCommitInfo:
        log.error("You must specify a commit or PR number")
        return False
    except UnknownTools as e:
        log.error("Didn't find any of the specified linters.")
        log.error("Known linters: %s", ', '.join(e.known))
        return False

    imhotep.invoke()


if __name__ == '__main__':
    main()
