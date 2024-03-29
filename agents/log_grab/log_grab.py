import os
import csv
import shutil
import datetime
import copy
import logging.config
import yaml
import i4c
import re
import tempfile

robot_actions = {
    "Darab beérkezett": ("state", "spotted"),
    "Darab felvéve a szalagról (Nyers)": ("state", "pickup"),
    "Darab lerakva a GOM-ra (Nyers)": ("state", "place_gom"),
    "GOM mérés OK (Nyers)": ("gom_signal", "gom_good"),
    "GOM mérés NOK (Nyers)": ("gom_signal", "gom_bad"),
    "Darab felvéve a GOM-ról (Nyers)": ("state", "takeout_gom"),
    "Darab lerakva Esztergába": ("state", "place_lathe"),
    "Darab felvéve Esztergából": ("state", "takeout_lathe"),
    "Darab lerakva Maróba": ("state", "place_mill"),
    "Darab felvéve Maróból": ("state", "takeout_mill"),
    "Darab lerakva fordítóra": ("state", "place_table"),
    "Darab felvéve fordítóról": ("state", "pickup_table"),
    "Darab lerakva a GOM-ra (Kész)": ("state", "place_gom"),
    "GOM mérés OK (Kész)": ("gom_signal", "gom_good"),
    "GOM mérés NOK (Kész)": ("gom_signal", "gom_bad"),
    "Darab felvéve a GOM-ról (Kész)": ("state", "takeout_gom"),
    "Darab jelölve": ("state", "marking"),
    "Darab lefújatva": ("state", "cleaning"),
    "Darab lerakva szalagra": ("state", "place_good_out"),
    "Darab lerakva minta fiókba": ("state", "place_sample_out"),
    "Darab lerakva NOK tárolóba": ("state", "place_bad_out"),
    "Folyamat megszakítva": ("state", "stopped")}

robot_alarms = {
    "Esztega Hiba": "error_lathe",
    "Eszterga nem áll készen": "not_ready_lathe",
    "GOM nem áll készen": "not_ready_gom",
    "Kamera nem áll készen": "not_ready_cam",
    "Kihordó szalag indítási Hiba": "start_error_band",
    "Levegõnyomás nincs rendben": "bad_pressure",
    "Maró Hiba": "error_mill",
    "Maró nem áll készen": "not_ready_mill",
    "Nyomtató nem áll készen": "not_ready_printer",
    "PC-PLC kommunikációs hiba": "error_com_plc",
    "Védõkör Hiba": "error_protection_circuit",
    "Vészkör Hiba": "error_emergency_circuit"
}

cfg: dict
conn: i4c.I4CConnection
log: logging.Logger


def init_globals():
    global cfg
    global log
    global conn

    with open("log_grab.conf") as f:
        cfg = yaml.load(f, Loader=yaml.FullLoader)
        if "log" in cfg:
            logging.config.dictConfig(cfg["log"])

    log = logging.getLogger()

    profile = cfg.get("profile", None)
    conn = i4c.I4CConnection(profile=profile)


def check_params(paths):
    result = {"source-path": None, "archive-path": None, "OK": False}
    if "source-path" not in paths:
        log.error("missing source-path")
        return result
    else:
        result["source-path"] = paths["source-path"]
        log.debug("source path: %s", result["source-path"])

    if not os.path.exists(paths["source-path"]):
        log.debug("source path doesn't exist.")
        return result

    if "archive-path" not in paths:
        log.error("missing archive-path")
        return result
    else:
        result["archive-path"] = paths["archive-path"]
        log.debug("archive path: %s", result["archive-path"])

    if not os.path.exists(paths["archive-path"]):
        log.error("archive path doesn't exist.")
        return result

    result["OK"] = True
    return result


def get_datetime(source, format):
    return datetime.datetime.strptime(source, format).strftime("%Y-%m-%dT%H:%M:%S")


def process_robot(section):
    log.debug("processing ROBOT files")

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
             os.path.isfile(os.path.join(src_path, entry))
             and entry.upper().endswith("FINISH.CSV")]
    if len(files) == 0:
        log.debug("No files to load")
        return
    for currentfile in files:
        wkpcid = None
        progid = None
        api_params_array = []
        log.info("Processing file %s", currentfile)
        try:
            with open(os.path.join(src_path, currentfile)) as csvfile:
                csvreader = csv.reader(csvfile, delimiter=";", quotechar=None)
                for lines in csvreader:
                    if len(lines) != 2:
                        if lines[0].upper() == "Naplózott események".upper():
                            continue
                        log.error(f"Line {csvreader.line_num} in wrong format!")
                        return

                    if lines[0].upper() == "Munkadarab azonosítója".upper():
                        wkpcid = lines[1]
                    elif lines[0].upper() == "Program neve".upper():
                        progid = lines[1]
                    elif csvreader.line_num >= 5:
                        if csvreader.line_num == 5:
                            if wkpcid is None:
                                log.error("Workpiece id is not set!")
                                return
                            if progid is None:
                                log.error("Program id is not set!")
                                return
                            api_params["sequence"] = 0
                            api_params["timestamp"] = get_datetime(lines[0], "%Y.%m.%d %H:%M:%S")
                            api_params["data_id"] = "wkpcid"
                            api_params["value_text"] = wkpcid
                            api_params["value_extra"] = None
                            api_params_array.append(copy.deepcopy(api_params))
                            api_params["sequence"] += 1
                            api_params["data_id"] = "pgm"
                            api_params["value_text"] = progid
                            api_params_array.append(copy.deepcopy(api_params))
                            api_params["sequence"] += 1
                            api_params["data_id"] = "robot_control"
                            api_params["value_text"] = "active"
                            api_params_array.append(copy.deepcopy(api_params))

                        api_params["sequence"] += 1
                        api_params["timestamp"] = get_datetime(lines[0], "%Y.%m.%d %H:%M:%S")
                        (did, value) = robot_actions.get(lines[1], ("state", "unknown"))
                        api_params["data_id"] = did
                        api_params["value_text"] = value
                        api_params["value_extra"] = lines[1]
                        api_params_array.append(copy.deepcopy(api_params))
                        api_params["value_extra"] = None

            # reusing last timestamp
            api_params["sequence"] += 1
            api_params["data_id"] = "robot_control"
            api_params["value_text"] = "inactive"
            api_params_array.append(copy.deepcopy(api_params))

            conn.invoke_url("log", "POST", api_params_array)
            process_GOM(cfg["gom"], wkpcid)
            process_ReniShaw(cfg["renishaw"], wkpcid)
            log.debug("Archiving file...")
            shutil.move(os.path.join(src_path, currentfile), os.path.join(params["archive-path"], currentfile))
        except Exception as E:
            log.error(E)


def safe_float(s):
    if s is None:
        return None
    s = s.replace(" ", "")
    if s == "":
        return None
    if s.startswith("?"):
        return None
    s = s.replace(",", ".")
    f = float(s)
    return f


def process_GOM(section, wkpcid):
    log.debug(f"Processing GOM files for {wkpcid}")

    params = check_params(section)
    if not params["OK"]:
        return

    src_path = params["source-path"]

    file_groups = [entry for entry in os.listdir(src_path)
                   if os.path.isfile(os.path.join(src_path, entry))
                   and (entry.upper().endswith(f"_{wkpcid}.OK") or entry.upper().endswith(f"_{wkpcid}.ERROR"))]

    if len(file_groups) == 0:
        log.debug("no file groups to load")
        return

    file_groups = [os.path.splitext(g) for g in file_groups]

    entries = []
    sequence = 0

    for (file_group, marker) in file_groups:
        log.debug(f"processing group {file_group}")

        markfile = os.path.join(src_path, f"{file_group}{marker}")

        logfile = os.path.join(src_path, f"{file_group}.log")
        if os.path.isfile(logfile):
            log.debug("loading log")
            first_time = None
            last_time = None
            with open(logfile) as f:
                for line in f:
                    entry = dict(device="gom", sequence=sequence)
                    sequence += 1

                    (part1, part2, part3, part4) = line.split(' ', 3)

                    if part3 == "*" : entry["data_id"] = "WARNING"
                    elif part3 == "!" : entry["data_id"] = "ERROR"
                    else: entry["data_id"] = "INFO"

                    entry["timestamp"] = get_datetime(part1 + ' ' + part2, "%Y-%m-%d %H:%M:%S.%f")
                    first_time = first_time or entry["timestamp"]
                    last_time = entry["timestamp"]

                    entry["value_text"] = part4.strip()

                    entries.append(entry)
        else:
            log.error(f"no log file found for {file_group}")
            first_time = os.path.getctime(markfile)
            last_time = os.path.getctime(markfile)

        entry = dict(
            device="gom",
            timestamp=first_time,
            sequence=sequence,
            data_id="pgm",
            value_text=file_group.rpartition("_")[0])
        sequence += 1
        entries.append(entry)

        csvfile = os.path.join(src_path, f"{file_group}.csv")
        if os.path.isfile(csvfile):
            log.debug("loading csv")
            with open(csvfile) as f:
                csvreader = csv.reader(f, delimiter=";", quotechar=None)
                for lines in csvreader:
                    if csvreader.line_num == 1:
                        if "Element" in lines:
                            idxElement = lines.index("Element")
                            # this is incorrect, we should combine with the Property column.
                            # however, for backward compatibility, we keep this.
                            # there is a new format anyway that uses Name, and it contains the entire name in one.
                        elif "Name" in lines:
                            idxElement = lines.index("Name")
                        else:
                            raise Exception("GOM CSV header is missing an Element or Name column.")

                        idxActual = lines.index("Actual")
                        if "Dev" in lines:
                            idxDev = lines.index("Dev")
                        else:
                            idxDev = None
                    else:
                        did = lines[idxElement].strip()

                        if idxDev is not None:
                            entry = dict(
                                device="gom",
                                timestamp=last_time,
                                sequence=sequence,
                                data_id=f"{did}-DEV",
                                value_num=safe_float(lines[idxDev]))
                            sequence += 1
                            entries.append(entry)

                        entry = dict(
                            device="gom",
                            timestamp=last_time,
                            sequence=sequence,
                            data_id=f"{did}-ACTUAL",
                            value_num=safe_float(lines[idxActual]))
                        sequence += 1
                        entries.append(entry)
        else:
            log.error(f"csv not found for {file_group}")

        for ext in (".pdf", ".atos"):
            datafilename = f"{file_group}{ext}"
            datafile = os.path.join(src_path, datafilename)
            if os.path.isfile(datafile):
                log.debug(f"uploading {datafilename}")
                with open(datafile, "rb") as f:
                    conn.invoke_url("intfiles/v/1/" + datafilename, "PUT", f)
                entry = dict(
                    device="gom",
                    timestamp=last_time,
                    sequence=sequence,
                    data_id="file",
                    value_text=datafilename)
                sequence += 1
                entries.append(entry)
            else:
                log.error(f"not found {datafilename}")

        log.debug(f"writing log entries: {len(entries)}")
        conn.invoke_url("log", "POST", entries)

        for ext in (".ok", ".error", ".pdf", ".atos", ".log", ".csv", ".bad", ".good"):
            filename = f"{file_group}{ext}"
            sourcefile = os.path.join(src_path, filename)
            if os.path.isfile(sourcefile):
                log.debug(f"archiving file {filename}")
                shutil.move(sourcefile, os.path.join(params["archive-path"], filename))


def process_Alarms(section):
    log.debug("Processing ALARM files...")

    api_params = {
        "timestamp": "2021-12-07T11:20:20.405Z",
        "sequence": None,
        "device": "robot",
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
    ref_date = datetime.date.today().strftime("%Y.%m.%d")

    files = [entry for entry in os.listdir(src_path) if os.path.isfile(os.path.join(src_path, entry))
             and any(entry.upper().endswith(ext) for ext in (".CSV"))
             and os.path.splitext(entry)[0] <= ref_date]
    if len(files) == 0:
        log.debug("no files to load")
        return

    current_file = dict()
    for currentfile in files:
        log.debug(f"found {currentfile}")
        current_file["name"] = currentfile
        current_file["path"] = src_path
        current_file["fullname"] = os.path.join(src_path, currentfile)

        try:
            fname, _ = os.path.splitext(currentfile)
            if fname == ref_date:
                log.debug("processing active file %s", current_file["fullname"])
                tmp_dir = tempfile.gettempdir()
                tmp_file = os.path.join(tmp_dir, current_file["name"])
                log.debug(f"creating temp file {tmp_file}")
                shutil.copyfile(current_file["fullname"], tmp_file)
                current_file["path"] = tmp_dir
                current_file["fullname"] = tmp_file
                current_file["move"] = False
            else:
                log.info("processing final file %s", current_file["fullname"])
                current_file["move"] = True

            log.debug("opening csv")
            with open(current_file["fullname"]) as csvfile:
                csvreader = csv.reader(csvfile, delimiter=";", quotechar=None)
                api_params_array = []
                api_params["sequence"] = 0
                for lines in csvreader:
                    api_params["timestamp"] = get_datetime(lines[0], "%Y.%m.%d %H:%M:%S")
                    api_params["data_id"] = "alarm"
                    api_params["value_text"] = robot_alarms.get(lines[1], "other_alarm")
                    api_params["value_extra"] = lines[1]
                    api_params_array.append(copy.deepcopy(api_params))
                    api_params["sequence"] += 1
                csvfile.close()
            log.debug(f"writing {len(api_params_array)} records")
            conn.invoke_url("log", "POST", api_params_array)
            if current_file["move"]:
                log.debug("archiving file")
                shutil.move(current_file["fullname"], os.path.join(params["archive-path"], current_file["name"]))
            else:
                log.debug("deleting temp file")
                os.remove(current_file["fullname"])
        except Exception as E:
            log.error(E)
    log.debug("alarms done")


def process_ReniShaw(section, wkpcid):
    log.debug(f"Processing ReniShaw files ({wkpcid})...")
    api_params = {
        "timestamp": "2021-12-07T11:20:20.405Z",
        "sequence": 0,
        "device": "renishaw",
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

    src_path = section["source-path"]

    files = [entry for entry in os.listdir(src_path) if os.path.isfile(os.path.join(src_path, entry))
             and re.match(r"^print_" + wkpcid + r".txt", entry, re.IGNORECASE)]

    if len(files) == 0:
        log.debug("no files to load")
        return

    for currentfile in files:
        log.info("processing file %s", currentfile)

        api_params_array = []
        measure = None
        measure2 = None

        with open(os.path.join(src_path, currentfile)) as srcfile:
            for line_no, lines in enumerate(srcfile):
                lines = lines.strip()
                if lines == '%':
                    if len(api_params_array) != 0:
                        conn.invoke_url("log", "POST", api_params_array)
                        api_params_array.clear()

                        measure = None
                        measure2 = None
                        api_params["timestamp"] = None
                        api_params["value_num"] = None
                        api_params["sequence"] = 0
                        api_params['value_extra'] = None
                    continue
                if lines == '':
                    continue
                if lines.startswith("+++++OUT OF TOL"):
                    if measure is None:
                        log.error(f"OUT OF TOL found but no measure is set at line {line_no}")
                        continue
                    if measure2 is None or measure2 == "":
                        log.error(f"OUT OF TOL found but no sub measure is set at line {line_no}")
                        continue
                    mo = re.match(r"[+]*OUT OF TOL/.*ERROR/\D*(?P<error>[-.\d]*).*$", lines)
                    if mo:
                        api_params["data_id"] = measure + measure2 +'-OTOL'
                        api_params["value_num"] = float(mo.group("error"))
                        api_params_array.append(copy.deepcopy(api_params))
                        api_params["sequence"] += 1
                if ' FEATURE ' in lines:
                    api_params['value_extra'] = next((v.strip() for v in lines.split('/ ') if v.strip().startswith('FEATURE')), None)

                mo = re.match(r"^(?P<measure2>[a-zA-Z ]*[ /])(?P<others>.*ACTUAL/[-0-9.]*.*)", lines)
                if mo:
                    if measure is None:
                        log.error(f"Size found but no measure is set at line {line_no}")
                        continue
                    measure2 = mo.group("measure2")
                    if measure2[-1:] == " ":
                        measure2 = measure2.strip()
                        ptrn = mo.group("others")
                    else:
                        ptrn = measure2 + mo.group("others")
                        measure2 = measure2[:-1]

                    for idx, values in enumerate((ptrn).split('/ ')):
                        rslt = values.strip().split('/')
                        s1, s2 = rslt[0:2]
                        if s1 == measure2:
                            s1 = "NOMINAL"

                        api_params["data_id"] = measure + "-" + measure2 + "-" + s1
                        api_params["value_num"] = float(s2)
                        api_params_array.append(copy.deepcopy(api_params))
                        api_params["sequence"] += 1
                    continue

                mo = re.match(r"^ *DATE/(?P<date>.*)/ *TIME/(?P<time>.*)/ *$", lines)
                if mo:
                    api_params["timestamp"] = get_datetime(mo.group("date") + " " + ("0" + mo.group("time"))[-6:],
                                                           "%y%m%d %H%M%S")
                    continue
                mo = re.match("^.*/MEASURE/(?P<measure_name>.*)/.*$", lines)
#               mo = re.match(r"^---- */  (?P<measure_name>.*)  / *----$", lines)    old pattern
                if mo:
                    if api_params["timestamp"] is None:
                        log.error(f"Measure found but no timestamp is set at line {line_no}")
                        continue
                    measure = mo.group("measure_name")
                    continue
            srcfile.close()
        log.debug("archiving file")
        shutil.move(os.path.join(src_path, currentfile), os.path.join(params["archive-path"], currentfile))


def main():
    init_globals()
    log.debug("start")

    if "robot" in cfg:
        process_robot(cfg["robot"])
    if "alarms" in cfg:
        process_Alarms(cfg["alarms"])

    log.debug("finish")

if __name__ == '__main__':
    main()
