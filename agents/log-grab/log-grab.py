
import os
import time
import csv
import shutil
import datetime
import copy
import logging.config
import yaml
import cli.i4c

robot_actions = {
    "Darab beérkezett": "spotted",
    "Darab felvéve a szalagról (Nyers)": "pickup",
    "Darab lerakva a GOM-ra (Nyers)": "place_gom",
    "GOM mérés OK (Nyers)": "gom_good",
    "GOM mérés NOK (Nyers)": "gom_bad",
    "Darab felvéve a GOM-ról (Nyers)": "takeout_gom",
    "Darab lerakva Esztergába": "place_lathe",
    "Darab felvéve Esztergából": "takeout_lathe",
    "Darab lerakva Maróba": "place_mill",
    "Darab felvéve Maróból": "takeout_mill",
    "Darab lerakva fordítóra": "place_table",
    "Darab felvéve fordítóról": "pickup_table",
    "Darab lerakva a GOM-ra (Kész)": "place_gom",
    "GOM mérés OK (Kész)": "gom_good",
    "GOM mérés NOK (Kész)": "gom_bad",
    "Darab felvéve a GOM-ról (Kész)": "pickout_gom",
    "Darab jelölve": "marking",
    "Darab lefújatva": "cleaning",
    "Darab lerakva szalagra": "place_good_out",
    "Darab lerakva minta fiókba": "place_sample_out",
    "Darab lerakva NOK tárolóba": "place_bad_out",
    "Folyamat megszakítva": "stopped"}  # TODO add gom repair statuses

with open("log-grab.yaml") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)
    if "log" in cfg:
        logging.config.dictConfig(cfg["log"])

log = logging.getLogger()

profile = cfg.get("profile", None)
conn = cli.i4c.I4CConnection(profile=profile)


def check_params(paths):
    result = {"source-path": None, "archive-path": None, "OK": False}
    if "source-path" not in paths:
        log.error("missing source-path")
        return result
    else:
        result["source-path"] = paths["source-path"]
        log.debug("source path: %s", result["source-path"])
    if "archive-path" not in paths:
        log.error("missing archive-path")
        return result
    else:
        result["archive-path"] = paths["archive-path"]
        log.debug("archive path: %s", result["archive-path"])

    result["OK"] = True
    return result


def process_robot(section):
    log.info("processing ROBOT files")

    api_params = {
        "timestamp": None,
        "sequence": -1,
        "device": "robot",
        "instance": 0,
        "data_id": '',
        "value": '',
        "value_num": 0,
        "value_text": '',
        "value_extra": '',
        "value_add": None
    }

    params = check_params(section)
    if not params["OK"]:
        return

    src_path = params["source-path"]

    files = [entry for entry in os.listdir(src_path) if
             os.path.isfile(os.path.join(src_path, entry)) and entry.upper().endswith("FINISH.CSV")]
    if len(files) == 0:
        log.debug("No files to load")
        return
    for currentfile in files:
        wkpcid = None
        progid = None
        api_params_array = []
        log.debug("Processing file %s", currentfile)
        with open(os.path.join(src_path, currentfile)) as csvfile:
            csvreader = csv.reader(csvfile, delimiter=";", quotechar=None)
            for lines in csvreader:
                if len(lines) != 2:
                    if lines[0].upper() == "Naplózott események".upper():
                        continue
                    log.error("Line %d in rong format!", [csvreader.line_num])
                    return

                if lines[0].upper() == "Munkadarab azonosítója".upper():
                    wkpcid = lines[1]
                elif lines[0].upper() == "Program neve".upper():
                    progid = lines[1]
                elif csvreader.line_num >= 5:
                    if csvreader.line_num == 5:
                        if wkpcid is None:
                            log.error("Workpiece id is not set!", [csvreader.line_num])
                            return
                        if progid is None:
                            log.error("Program id is not set!", [csvreader.line_num])
                            return
                        api_params["sequence"] = 0
                        api_params["timestamp"] = datetime.datetime.strptime(lines[0], "%Y.%m.%d %H:%M:%S").strftime(
                            "%Y-%m-%dT%H:%M:%SZ")
                        api_params["data_id"] = "wkpcid"
                        api_params["value_text"] = wkpcid
                        api_params_array.append(copy.deepcopy(api_params))
                        api_params["sequence"] += 1
                        api_params["data_id"] = "pgm"
                        api_params["value_text"] = progid
                        api_params_array.append(copy.deepcopy(api_params))

                    api_params["sequence"] += 1
                    api_params["timestamp"] = datetime.datetime.strptime(lines[0], "%Y.%m.%d %H:%M:%S").strftime(
                            "%Y-%m-%dT%H:%M:%SZ")
                    api_params["data_id"] = robot_actions.get(lines[1], "other")
                    if api_params["data_id"] == "other":
                        api_params["value_text"] = lines[1]
                    else:
                        api_params["value_text"] = None
                    api_params_array.append(copy.deepcopy(api_params))

            csvfile.close()
        conn.invoke_url("log", "POST", api_params_array)
        log.debug("Archiving file...")
        shutil.move(os.path.join(src_path, currentfile), os.path.join(params["archive-path"], currentfile))


def process_GOM(section):
    log.info("Processing GOM files...")

    api_params = {
        "timestamp": "2021-12-07T11:20:20.405Z",
        "sequence": None,
        "device": "GOM",
        "instance": 0,
        "data_id": '',
        "value": None,
        "value_num": None,
        "value_text": None,
        "value_extra": None,
        "value_add": None
    }

    params = check_params(section)
    if not params["OK"]:
        return

    src_path = params["source-path"]

    files = [entry for entry in os.listdir(src_path) if os.path.isfile(os.path.join(src_path, entry))
             and any(entry.upper().endswith(ext) for ext in (".CSV", ".ATOS" ".PDF"))]
    if len(files) == 0:
        log.debug("no files to load")
        return

    for currentfile in files:
        log.debug("processing file %s", currentfile)
        fname, fext = os.path.splitext(currentfile)
        if fext.upper() == ".CSV":
            if not os.path.exists(os.path.join(src_path, fname + '.LOG')):
                log.error("No log file found")
                continue
            api_params_array = []

            with open(os.path.join(src_path, fname + ".log")) as csvfile:
                api_params["sequence"] = 0
                api_params["data_id"] = "GOM_log"
                for (line_no, lines) in enumerate(csvfile):
                    (part1, part2, part3, part4) = lines.split(' ', 3)
                    if part3 == "*" : api_params["data_id"] = "WARNING"
                    elif part3 == "!" : api_params["data_id"] = "ERROR"
                    else: api_params["data_id"] = "INFO"

                    api_params["timestamp"] = datetime.datetime.strptime(part1 + ' ' + part2, "%Y-%m-%d %H:%M:%S.%f").strftime(
                            "%Y-%m-%dT%H:%M:%SZ.%f")

                    if line_no == 0:
                        first_time = api_params["timestamp"]

                    api_params["value_text"] = part4.strip()
                    api_params_array.append(copy.deepcopy(api_params))
                    api_params["sequence"] += 1
                csvfile.close()

            api_params["value_text"] = '_'.join(fname.split('_')[0:2])
            api_params["data_id"] = "pgm"
            api_params["timestamp"] = first_time
            api_params_array.append(copy.deepcopy(api_params))
            api_params["value_text"] = None

            with open(os.path.join(src_path, currentfile)) as csvfile:
                csvreader = csv.reader(csvfile, delimiter=";", quotechar=None)
                for lines in csvreader:
                    if csvreader.line_num == 1:
                        idxElement = lines.index("Element")  # -> data_id
                        idxDev = lines.index("Dev")  # -> value_num
                        idxActual = lines.index("Actual")  # -> value_extra
                    else:
                        api_params["sequence"] += 1
                        api_params["data_id"] = lines[idxElement]
                        api_params["value_num"] = float(lines[idxDev].replace(",", "."))
                        api_params["value_extra"] = lines[idxActual].replace(",", ".")
                        api_params_array.append(copy.deepcopy(api_params))
                csvfile.close()

            conn.invoke_url("log", "POST", api_params_array)
        else:
            with open(os.path.join(src_path, f), "rb") as datafile:
                conn.invoke_url("intfiles/v/1/" + f, "PUT", datafile)
                datafile.close()
            pass

        log.debug("archiving file")
        shutil.move(os.path.join(src_path, currentfile), os.path.join(params["archive-path"], currentfile))
        if fext.upper() == ".CSV":
            shutil.move(os.path.join(src_path, fname + '.log'), os.path.join(params["archive-path"], fname + '.log'))

        for newext in ['.ok', '.error', '.bad', '.good']:
            fnew = fname + newext
            if os.path.exists(os.path.join(src_path, fnew)):
                log.debug("archiving additional file {}".format(fnew))
                shutil.move(os.path.join(src_path, fnew), os.path.join(params["archive-path"], fnew))

def process_Alarms(section):
    log.info("Processing ALARM files...")

    api_params = {
        "timestamp": "2021-12-07T11:20:20.405Z",
        "sequence": None,
        "device": "ROBOT",
        "instance": 0,
        "data_id": '',
        "value": None,
        "value_num": None,
        "value_text": None,
        "value_extra": None,
        "value_add": None
    }
    params = check_params(section)
    if not params["OK"]:
        return

    src_path = params["source-path"]

    files = [entry for entry in os.listdir(src_path) if os.path.isfile(os.path.join(src_path, entry))
             and any(entry.upper().endswith(ext) for ext in (".CSV"))
             and os.path.splitext(entry)[0] < datetime.date.today().strftime("%Y.%m.%d")]
    if len(files) == 0:
        log.debug("no files to load")
        return

    for currentfile in files:
        log.debug("processing file %s", currentfile)
        with open(os.path.join(src_path, currentfile)) as csvfile:
            csvreader = csv.reader(csvfile, delimiter=";", quotechar=None)
            api_params_array = []
            api_params["sequence"] = 0
            for lines in csvreader:
                api_params["timestamp"] = datetime.datetime.strptime(lines[0], "%Y.%m.%d %H:%M:%S").strftime(
                    "%Y-%m-%dT%H:%M:%SZ.%f")
                api_params["data_id"] = robot_actions.get(lines[1], "other")
                if api_params["data_id"] == "other":
                    api_params["value_text"] = lines[1]
                else:
                    api_params["value_text"] = None
                api_params_array.append(copy.deepcopy(api_params))
                api_params["sequence"] += 1
            csvfile.close()
        conn.invoke_url("log", "POST", api_params_array)
        log.debug("archiving file")
        shutil.move(os.path.join(src_path, currentfile), os.path.join(params["archive-path"], currentfile))



log.info("start")
if "robot" in cfg:
    process_robot(cfg["robot"])
if "GOM" in cfg:
    process_GOM(cfg["GOM"])
if "Alarms" in cfg:
    process_Alarms(cfg["Alarms"])

log.info("finish")
