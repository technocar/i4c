# TODO name could be something clearer than ftrans

# TODO ; is not needed ever!
import os;
import csv;
import shutil;
import datetime;
import copy;
import logging.config
import yaml
import cli;


# TODO make logconfig optional
with open("logconfig.yaml") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)
    logging.config.dictConfig(cfg)

log = logging.getLogger("ftrans")

with open("ftrans.yaml") as f:
    ftranscfg = yaml.load(f, Loader=yaml.FullLoader)

Connection = cli.conn.I4CConnection(); # TODO we could use a profile name setting, coming from the config yaml


# TODO pascal case is not pythonic. it goes for procedures, parameters and variables too
def CheckParams(Paths):
    result = {'SourcePath': None, 'ArchivePath': None, 'OK': False}
    if (not 'SourcePath' in Paths):
      log.error('No SourcePath is set!!!');
      return result;
    else:
      result['SourcePath'] = Paths['SourcePath']
      log.debug('Source path is: %s', result['SourcePath']);
    if (not 'ArchivePath' in Paths):
      log.error('No ArchivePath is set!!!');
      return result;
    else:
      result['ArchivePath'] = Paths['ArchivePath']
      log.debug('Archive path is: %s', result['ArchivePath']);

    result['OK'] = True;
    return result;

def ProcessRobot(Section):
    log.info('Processing ROBOT files...');

    APIParams = {
        'timestamp': "2021-12-07T11:20:20.405Z",
        'sequence': -1,
        'device': 'robot',
        'instance': 0,
        'data_id': '',
        'value': '',
        'value_num': 0,
        'value_text': '',
        'value_extra': '',
        'value_add': None
    }

    Params = CheckParams(Section);
    if (Params['OK'] == False):
        return;

    files = [f for f in os.listdir(Params['SourcePath']) if os.path.isfile(os.path.join(Params['SourcePath'], f)) and f.upper().endswith('.CSV')]
    if len(files) == 0:
        log.debug('No files to load');
        return;
    for f in files:
        wkpcid = None;
        progid = None;
        ApiParamsArray = [];
        log.debug('Processing file %s', f);
        with open(os.path.join(Params['SourcePath'], f)) as csvfile:
            csvreader = csv.reader(csvfile, delimiter=';', quotechar=None);
            for lines in csvreader:
                if len(lines) != 2:
                  log.error('Line %d in rong format!', [csvreader.line_num]);
                  return;

                if lines[0].upper() == 'Munkadarab azonosítója'.upper():
                    wkpcid = lines[1];
                elif lines[0].upper() == 'Kiválasztott program neve'.upper():
                    progid = lines[1];
                elif csvreader.line_num >= 5:
                    if csvreader.line_num == 5:
                        if wkpcid is None:
                            log.error('Workpiece id is not set!', [csvreader.line_num]);
                            return;
                        if progid is None:
                            log.error('Program id is not set!', [csvreader.line_num]);
                            return;
                        APIParams['sequence'] = 0;
                        APIParams['timestamp'] = datetime.datetime.strptime(lines[0], '%Y.%m.%d %H:%M:%S').strftime('%Y-%m-%dT%H:%M:%SZ');
                        APIParams['data_id'] = 'wkpcid';
                        APIParams['value_text'] = wkpcid;
                        ApiParamsArray.append(copy.deepcopy(APIParams));
                        APIParams['sequence'] += 1;
                        APIParams['data_id'] = 'pgm';
                        APIParams['value_text'] = progid;
                        ApiParamsArray.append(copy.deepcopy(APIParams)); # TODO maybe this is a little too clever. just make a new dict, and fill in

                    APIParams['sequence'] += 1;
                    APIParams['timestamp'] = datetime.datetime.strptime(lines[0], '%Y.%m.%d %H:%M:%S').strftime('%Y-%m-%dT%H:%M:%SZ');
                    APIParams['data_id'] =  lines[1];
                    APIParams['value_text'] = lines[1];
                    ApiParamsArray.append(copy.deepcopy(APIParams));

            csvfile.close();
        Connection.invoke_url('log', 'POST', ApiParamsArray);
        log.debug('Archiving file...');
        shutil.move(os.path.join(Params['SourcePath'], f), os.path.join(Params['ArchivePath'], f));


def ProcessGOM(Section):
    log.info('Processing GOM files...');

    APIParams = {
        'timestamp': "2021-12-07T11:20:20.405Z",
        'sequence': None,
        'device': 'GOM',
        'instance': 0,
        'data_id': '',
        'value': '',
        'value_num': 0,
        'value_text': None,
        'value_extra': None,
        'value_add': None
    }

    Params = CheckParams(Section);
    if (Params['OK'] == False):
      return;

    files = [f for f in os.listdir(Params['SourcePath']) if os.path.isfile(os.path.join(Params['SourcePath'], f))
                                                           and (f.upper().endswith('.CSV')
                                                                or f.upper().endswith('.ATOS')
                                                                or f.upper().endswith('.PDF'))]
    if len(files) == 0:
      log.debug('No files to load');
      return;

    for f in files:
        log.debug('Processing file %s', f);
        fname = os.path.splitext(f)[0];

        if f.upper().endswith('.CSV'):
            ApiParamsArray = [];
            APIParams['sequence'] = 0;
            APIParams['timestamp'] = datetime.datetime.strptime(fname[-14:], '%Y%m%d%H%M%S').strftime('%Y-%m-%dT%H:%M:%SZ');
            APIParams['data_id'] = 'pgm'
            APIParams['value_text'] = fname[:-15];
            ApiParamsArray.append(copy.deepcopy(APIParams));
            APIParams['value_text'] = '';

            with open(os.path.join(Params['SourcePath'], f)) as csvfile:
                csvreader = csv.reader(csvfile, delimiter=';', quotechar=None);
                for lines in csvreader:
                    if csvreader.line_num == 1 :
                        idxElement = lines.index('Element')  # -> data_id
                        idxDev = lines.index('Dev')          # -> value_num
                        idxActual = lines.index('Actual')    # -> value_extra
                    else:
                        APIParams['sequence'] += 1;
                        APIParams['data_id'] = lines[idxElement];
                        APIParams['value_num'] = float(lines[idxDev].replace(',', '.'));
                        APIParams['value_extra'] = lines[idxActual].replace(',', '.');
                        ApiParamsArray.append(copy.deepcopy(APIParams));
                csvfile.close();

            Connection.invoke_url('log', 'POST', ApiParamsArray);
        else:
            with open(os.path.join(Params['SourcePath'], f), 'rb') as datafile:
                Connection.invoke_url('intfiles/v/1/' + f, 'PUT', datafile);
                datafile.close();

        log.debug('Archiving file...');
        shutil.move(os.path.join(Params['SourcePath'], f), os.path.join(Params['ArchivePath'], f));



log.info('FTRANS started.');
if ('Robot' in ftranscfg):
    ProcessRobot(ftranscfg['Robot'])
if ('GOM' in ftranscfg ):
    ProcessGOM(ftranscfg['GOM'])
log.info('FTRANS finished.');
