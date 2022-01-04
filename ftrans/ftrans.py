# TODO name could be something clearer than ftrans

import os
import csv
import shutil
import datetime
import copy
import logging.config
import yaml
import cli.i4c

robot_actions = [{'program_start': "1",
                 'program_end': "2",
                  'other': "####"}]

if os.path.exists("logconfig.yaml"):
    with open("logconfig.yaml") as f:
      cfg = yaml.load(f, Loader=yaml.FullLoader)
      logging.config.dictConfig(cfg)
    log = logging.getLogger("ftrans")
else:
    log = logging.getLogger()
    log.disabled = True

with open("ftrans.yaml") as f:
    ftranscfg = yaml.load(f, Loader=yaml.FullLoader)

if "Profile" not in ftranscfg:
    Connection = cli.i4c.i4CConnection()
else:
    Connection = cli.i4c.I4CConnection(
        profile=ftranscfg["Profile"])


def check_params(paths):
    result = {'SourcePath': None, 'ArchivePath': None, 'OK': False}
    if (not 'SourcePath' in paths):
        log.error('No SourcePath is set!!!')
        return result
    else:
        result['SourcePath'] = paths['SourcePath']
        log.debug('Source path is: %s', result['SourcePath'])
    if (not 'ArchivePath' in paths):
        log.error('No ArchivePath is set!!!')
        return result
    else:
        result['ArchivePath'] = paths['ArchivePath']
        log.debug('Archive path is: %s', result['ArchivePath'])

    result['OK'] = True
    return result


def process_robot(section):
    log.info('Processing ROBOT files...')

    api_params = {
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

    params = check_params(section)
    if (params['OK'] == False):
        return

    files = [f for f in os.listdir(params['SourcePath']) if
             os.path.isfile(os.path.join(params['SourcePath'], f)) and f.upper().endswith('.CSV')]
    if len(files) == 0:
        log.debug('No files to load')
        return
    for f in files:
        wkpcid = None
        progid = None
        api_params_array = []
        log.debug('Processing file %s', f)
        with open(os.path.join(params['SourcePath'], f)) as csvfile:
            csvreader = csv.reader(csvfile, delimiter=';', quotechar=None)
            for lines in csvreader:
                if len(lines) != 2:
                    log.error('Line %d in rong format!', [csvreader.line_num])
                    return

                if lines[0].upper() == 'Munkadarab azonosítója'.upper():
                    wkpcid = lines[1]
                elif lines[0].upper() == 'Kiválasztott program neve'.upper():
                    progid = lines[1]
                elif csvreader.line_num >= 5:
                    if csvreader.line_num == 5:
                        if wkpcid is None:
                            log.error('Workpiece id is not set!', [csvreader.line_num])
                            return
                        if progid is None:
                            log.error('Program id is not set!', [csvreader.line_num])
                            return
                        api_params['sequence'] = 0
                        api_params['timestamp'] = datetime.datetime.strptime(lines[0], '%Y.%m.%d %H:%M:%S').strftime(
                            '%Y-%m-%dT%H:%M:%SZ')
                        api_params['data_id'] = 'wkpcid'
                        api_params['value_text'] = wkpcid
                        api_params_array.append(copy.deepcopy(api_params))
                        api_params['sequence'] += 1
                        api_params['data_id'] = 'pgm'
                        api_params['value_text'] = progid
                        api_params_array.append(copy.deepcopy(
                            api_params))  # TODO maybe this is a little too clever. just make a new dict, and fill in

                    api_params['sequence'] += 1
                    api_params['timestamp'] = datetime.datetime.strptime(lines[0], '%Y.%m.%d %H:%M:%S').strftime(
                        '%Y-%m-%dT%H:%M:%SZ')
                    if lines[1] in robot_actions:
                        api_params['data_id'] = robot_actions[lines[1]]
                    else:
                        api_params['data_id'] = robot_actions['other']
                    api_params['value_text'] = lines[1]
                    api_params_array.append(copy.deepcopy(api_params))

            csvfile.close()
        Connection.invoke_url('log', 'POST', api_params_array)
        log.debug('Archiving file...')
        shutil.move(os.path.join(params['SourcePath'], f), os.path.join(params['ArchivePath'], f))


def process_GOM(section):
    log.info('Processing GOM files...')

    api_params = {
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

    params = check_params(section)
    if (params['OK'] == False):
        return

    files = [f for f in os.listdir(params['SourcePath']) if os.path.isfile(os.path.join(params['SourcePath'], f))
             and (f.upper().endswith('.CSV')
                  or f.upper().endswith('.ATOS')
                  or f.upper().endswith('.PDF'))]
    if len(files) == 0:
        log.debug('No files to load')
        return

    for f in files:
        log.debug('Processing file %s', f)
        fname = os.path.splitext(f)[0]

        if f.upper().endswith('.CSV'):
            api_params_array = []
            api_params['sequence'] = 0
            api_params['timestamp'] = datetime.datetime.strptime(fname[-14:], '%Y%m%d%H%M%S').strftime(
                '%Y-%m-%dT%H:%M:%SZ')
            api_params['data_id'] = 'pgm'
            api_params['value_text'] = fname[:-15]
            api_params_array.append(copy.deepcopy(api_params))
            api_params['value_text'] = ''

            with open(os.path.join(params['SourcePath'], f)) as csvfile:
                csvreader = csv.reader(csvfile, delimiter=';', quotechar=None)
                for lines in csvreader:
                    if csvreader.line_num == 1:
                        idxElement = lines.index('Element')  # -> data_id
                        idxDev = lines.index('Dev')  # -> value_num
                        idxActual = lines.index('Actual')  # -> value_extra
                    else:
                        api_params['sequence'] += 1
                        api_params['data_id'] = lines[idxElement]
                        api_params['value_num'] = float(lines[idxDev].replace(',', '.'))
                        api_params['value_extra'] = lines[idxActual].replace(',', '.')
                        api_params_array.append(copy.deepcopy(api_params))
                csvfile.close()

            Connection.invoke_url('log', 'POST', api_params_array)
        else:
            with open(os.path.join(params['SourcePath'], f), 'rb') as datafile:
                Connection.invoke_url('intfiles/v/1/' + f, 'PUT', datafile)
                datafile.close()

        log.debug('Archiving file...')
        shutil.move(os.path.join(params['SourcePath'], f), os.path.join(params['ArchivePath'], f))


log.info('FTRANS started.')
if ('Robot' in ftranscfg):
    process_robot(ftranscfg['Robot'])
if ('GOM' in ftranscfg):
    process_GOM(ftranscfg['GOM'])
log.info('FTRANS finished.')
