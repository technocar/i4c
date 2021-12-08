import logging.config
import yaml
import cli;

with open("logconfig.yaml") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)
    logging.config.dictConfig(cfg)
log = logging.getLogger("ftrans")

with open("ftrans.yaml") as f:
    ftranscfg = yaml.load(f, Loader=yaml.FullLoader)

Connection = cli.conn.I4CConnection();