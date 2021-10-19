import yaml
import logging.config

with open("logconfig.yaml") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)
    logging.config.dictConfig(cfg)
log = logging.getLogger("api")

with open("dbconfig.yaml") as f:
    dbcfg = yaml.load(f, Loader=yaml.FullLoader)