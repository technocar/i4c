CREATE ROLE i4capi WITH
	LOGIN
	NOSUPERUSER
	NOCREATEDB
	NOCREATEROLE
	INHERIT
	NOREPLICATION
	CONNECTION LIMIT -1;
COMMENT ON ROLE i4capi IS 'I4C server API';


CREATE SCHEMA i4c;

GRANT USAGE ON SCHEMA i4c TO i4capi;

ALTER USER i4capi SET search_path to i4c,public;

set search_path = i4c,public;  -- this sets the default schema for the create statements


CREATE TABLE IF NOT EXISTS log
(
    device character varying(200) NOT NULL,
    instance character varying(200),
    "timestamp" timestamp with time zone NOT NULL,
    sequence integer NOT NULL,
    data_id character varying(200) NOT NULL,
    value_num double precision,
    value_text character varying(200),
    value_extra character varying(200),
    value_aux json
);

GRANT ALL ON TABLE log TO i4capi;

CREATE UNIQUE INDEX idx_ts
    ON log USING btree
    (device ASC NULLS LAST, "timestamp" ASC NULLS LAST, sequence ASC NULLS LAST);

CREATE INDEX idx_dts
    ON log USING btree
    (device ASC NULLS LAST, data_id ASC NULLS LAST, "timestamp" ASC NULLS LAST, sequence ASC NULLS LAST);

CREATE INDEX idx_ts_wo_device
    ON log USING btree
    ("timestamp" ASC NULLS LAST, sequence ASC NULLS LAST);

CREATE INDEX idx_dts_wo_device
    ON log USING btree
    (data_id ASC NULLS LAST, "timestamp" ASC NULLS LAST, sequence ASC NULLS LAST);


CREATE TABLE IF NOT EXISTS meta
(
    device character varying(200) NOT NULL,
    data_id character varying(200) NOT NULL,
    name character varying(200) NULL,
    nice_name character varying(200),
    system1 character varying(200),
    system2 character varying(200),
    category character varying(200),
    type character varying(200),
    subtype character varying(200),
    unit character varying(200),
    CONSTRAINT meta_pkey PRIMARY KEY (device, data_id)
);

GRANT SELECT ON TABLE meta TO i4capi;

delete from meta where data_id = 'connect';
insert into meta (device, data_id, name, category, "type") values ('lathe', 'connect', 'connect', 'CONDITION', 'CONDITION');
insert into meta (device, data_id, name, category, "type") values ('mill', 'connect', 'connect', 'CONDITION', 'CONDITION');

insert into meta (device,data_id,name,category) values ('mill','install_tool','install_tool','EVENT');
insert into meta (device,data_id,name,category) values ('mill','remove_tool','install_tool','EVENT');
insert into meta (device,data_id,name,category) values ('lathe','install_tool','install_tool','EVENT');
insert into meta (device,data_id,name,category) values ('lathe','remove_tool','install_tool','EVENT');

-- robot

insert into meta (device,data_id,name,category) values ('robot','wkpcid','serial number','EVENT');
insert into meta (device,data_id,name,category) values ('robot','pgm','program','EVENT');

-- beware of the field order
insert into meta (device,name,data_id,system1,category) values ('robot','Darab beérkezett', 'spotted','log','EVENT');
insert into meta (device,name,data_id,system1,category) values ('robot','Darab felvéve a szalagról (Nyers)', 'pickup','log','EVENT');
insert into meta (device,name,data_id,system1,category) values ('robot','Darab lerakva a GOM-ra', 'place_gom','log','EVENT');
insert into meta (device,name,data_id,system1,category) values ('robot','GOM mérés OK', 'gom_good','log','EVENT');
insert into meta (device,name,data_id,system1,category) values ('robot','GOM mérés NOK', 'gom_bad','log','EVENT');
insert into meta (device,name,data_id,system1,category) values ('robot','Darab felvéve a GOM-ról', 'takeout_gom','log','EVENT');
insert into meta (device,name,data_id,system1,category) values ('robot','Darab lerakva Esztergába', 'place_lathe','log','EVENT');
insert into meta (device,name,data_id,system1,category) values ('robot','Darab felvéve Esztergából', 'takeout_lathe','log','EVENT');
insert into meta (device,name,data_id,system1,category) values ('robot','Darab lerakva Maróba', 'place_mill','log','EVENT');
insert into meta (device,name,data_id,system1,category) values ('robot','Darab felvéve Maróból', 'takeout_mill','log','EVENT');
insert into meta (device,name,data_id,system1,category) values ('robot','Darab lerakva fordítóra', 'place_table','log','EVENT');
insert into meta (device,name,data_id,system1,category) values ('robot','Darab felvéve fordítóról', 'pickup_table','log','EVENT');
insert into meta (device,name,data_id,system1,category) values ('robot','Darab jelölve', 'marking','log','EVENT');
insert into meta (device,name,data_id,system1,category) values ('robot','Darab lefújatva', 'cleaning','log','EVENT');
insert into meta (device,name,data_id,system1,category) values ('robot','Darab lerakva szalagra', 'place_good_out','log','EVENT');
insert into meta (device,name,data_id,system1,category) values ('robot','Darab lerakva minta fiókba', 'place_sample_out','log','EVENT');
insert into meta (device,name,data_id,system1,category) values ('robot','Darab lerakva NOK tárolóba', 'place_bad_out','log','EVENT');
insert into meta (device,name,data_id,system1,category) values ('robot','Folyamat megszakítva', 'stopped','log','EVENT');
insert into meta (device,name,data_id,system1,category) values ('robot','egyéb info', 'other','log','EVENT');

insert into meta (device,name,data_id,system1,category) values ('robot','egyéb hibaesemény','other_alarm', 'alarm','EVENT');

-- gom

insert into meta (device,data_id,name,system1,category) values ('gom','WARNING','log warming','log', 'EVENT');
insert into meta (device,data_id,name,system1,category) values ('gom','ERROR','log error','log', 'EVENT');
insert into meta (device,data_id,name,system1,category) values ('gom','INFO','log info','log', 'EVENT');
insert into meta (device,data_id,name,system1,category) values ('gom','pgm','program','log', 'EVENT');
insert into meta (device,data_id,name,system1,category) values ('gom','d1-DEV', 'd1 dev','metric', 'SAMPLE');
insert into meta (device,data_id,name,system1,category) values ('gom','d1-ACTUAL', 'd1','metric', 'SAMPLE');
insert into meta (device,data_id,name,system1,category) values ('gom','d2-DEV', 'd2 dev','metric', 'SAMPLE');
insert into meta (device,data_id,name,system1,category) values ('gom','d2-ACTUAL', 'd2','metric', 'SAMPLE');

-- renishaw

insert into meta (device,data_id,name,category) values ('renishaw', 'D1 - ATMERO 90-ACTUAL', 'D1 - ATMERO 90-ACTUAL', 'SAMPLE');
insert into meta (device,data_id,name,category) values ('renishaw', 'D1 - ATMERO 90-DEV', 'D1 - ATMERO 90-DEV', 'SAMPLE');
insert into meta (device,data_id,name,category) values ('renishaw', 'D2 - ATMERO 124 -R62-ACTUAL', 'D2 - ATMERO 124 -R62-ACTUAL', 'SAMPLE');
insert into meta (device,data_id,name,category) values ('renishaw', 'D2 - ATMERO 124 -R62-DEV', 'D2 - ATMERO 124 -R62-DEV', 'SAMPLE');
insert into meta (device,data_id,name,category) values ('renishaw', 'D2 - ATMERO 194 -R97-ACTUAL', 'D2 - ATMERO 194 -R97-ACTUAL', 'SAMPLE');
insert into meta (device,data_id,name,category) values ('renishaw', 'D2 - ATMERO 194 -R97-DEV', 'D2 - ATMERO 194 -R97-DEV', 'SAMPLE');
insert into meta (device,data_id,name,category) values ('renishaw', 'S - VASTAGSAG-ACTUAL', 'S - VASTAGSAG-ACTUAL', 'SAMPLE');
insert into meta (device,data_id,name,category) values ('renishaw', 'S - VASTAGSAG-DEV', 'S - VASTAGSAG-DEV', 'SAMPLE');

-- mazak

insert into meta values ('lathe', 'caxisstate', NULL, NULL, 'base', 'C', 'EVENT', 'AXIS_STATE', NULL, NULL);
insert into meta values ('lathe', 'cf', 'Cfrt', 'Cfrt', 'base', 'C', 'SAMPLE', 'ANGULAR_VELOCITY', NULL, 'DEGREE/SECOND');
insert into meta values ('lathe', 'cl', 'Cload', 'Cload', 'base', 'C', 'SAMPLE', 'LOAD', NULL, 'PERCENT');
insert into meta values ('lathe', 'cposm', 'Cabs', 'Cabs', 'base', 'C', 'SAMPLE', 'ANGLE', 'ACTUAL', 'DEGREE');
insert into meta values ('lathe', 'cposw', 'Cpos', 'Cpos', 'base', 'C', 'SAMPLE', 'ANGLE', 'ACTUAL', 'DEGREE');
insert into meta values ('lathe', 'ct', 'Ctravel', 'Ctravel', 'base', 'C', 'CONDITION', 'ANGLE', NULL, NULL);
insert into meta values ('lathe', 'ctemp', 'Stemp', 'Stemp', 'base', 'C', 'SAMPLE', 'TEMPERATURE', NULL, 'CELSIUS');
insert into meta values ('lathe', 'cs', 'Srpm', 'Srpm', 'base', 'C', 'SAMPLE', 'ROTARY_VELOCITY', 'ACTUAL', 'REVOLUTION/MINUTE');
insert into meta values ('lathe', 'rf', 'crfunc', 'crfunc', 'base', 'C', 'EVENT', 'ROTARY_MODE', NULL, NULL);
insert into meta values ('lathe', 'sl', 'Sload', 'Sload', 'base', 'C', 'SAMPLE', 'LOAD', NULL, 'PERCENT');
insert into meta values ('lathe', 'spc', 'Sload_cond', 'Sload_cond', 'base', 'C', 'CONDITION', 'LOAD', NULL, NULL);
insert into meta values ('lathe', 'tmp', 'Stemp_cond', 'Stemp_cond', 'base', 'C', 'CONDITION', 'TEMPERATURE', NULL, NULL);
insert into meta values ('lathe', 'xaxisstate', NULL, NULL, 'base', 'X', 'EVENT', 'AXIS_STATE', NULL, NULL);
insert into meta values ('lathe', 'xf', 'Xfrt', 'Xfrt', 'base', 'X', 'SAMPLE', 'AXIS_FEEDRATE', NULL, 'MILLIMETER/SECOND');
insert into meta values ('lathe', 'xl', 'Xload', 'Xload', 'base', 'X', 'SAMPLE', 'LOAD', NULL, 'PERCENT');
insert into meta values ('lathe', 'xpm', 'Xabs', 'Xabs', 'base', 'X', 'SAMPLE', 'POSITION', 'ACTUAL', 'MILLIMETER');
insert into meta values ('lathe', 'xpw', 'Xpos', 'Xpos', 'base', 'X', 'SAMPLE', 'POSITION', 'ACTUAL', 'MILLIMETER');
insert into meta values ('lathe', 'xt', 'Xtravel', 'Xtravel', 'base', 'X', 'CONDITION', 'POSITION', NULL, NULL);
insert into meta values ('lathe', 'zaxisstate', NULL, NULL, 'base', 'Z', 'EVENT', 'AXIS_STATE', NULL, NULL);
insert into meta values ('lathe', 'zf', 'Zfrt', 'Zfrt', 'base', 'Z', 'SAMPLE', 'AXIS_FEEDRATE', NULL, 'MILLIMETER/SECOND');
insert into meta values ('lathe', 'zl', 'Zload', 'Zload', 'base', 'Z', 'SAMPLE', 'LOAD', NULL, 'PERCENT');
insert into meta values ('lathe', 'zpm', 'Zabs', 'Zabs', 'base', 'Z', 'SAMPLE', 'POSITION', 'ACTUAL', 'MILLIMETER');
insert into meta values ('lathe', 'zpw', 'Zpos', 'Zpos', 'base', 'Z', 'SAMPLE', 'POSITION', 'ACTUAL', 'MILLIMETER');
insert into meta values ('lathe', 'zt', 'Ztravel', 'Ztravel', 'base', 'Z', 'CONDITION', 'POSITION', NULL, NULL);
insert into meta values ('lathe', 'servo', 'servo_cond', 'servo_cond', 'base', NULL, 'CONDITION', 'ACTUATOR', NULL, NULL);
insert into meta values ('lathe', 'spndl', 'spindle_cond', 'spindle_cond', 'base', NULL, 'CONDITION', 'SYSTEM', NULL, NULL);
insert into meta values ('lathe', 'exec', 'execution', 'execution', 'controller', 'path', 'EVENT', 'EXECUTION', NULL, NULL);
insert into meta values ('lathe', 'hd1chuckstate', NULL, NULL, 'controller', 'path', 'EVENT', 'CHUCK_STATE', NULL, NULL);
insert into meta values ('lathe', 'ln', 'line', 'line', 'controller', 'path', 'EVENT', 'LINE', NULL, NULL);
insert into meta values ('lathe', 'mode', 'mode', 'mode', 'controller', 'path', 'EVENT', 'CONTROLLER_MODE', NULL, NULL);
insert into meta values ('lathe', 'motion', 'motion_cond', 'motion_cond', 'controller', 'path', 'CONDITION', 'MOTION_PROGRAM', NULL, NULL);
insert into meta values ('lathe', 'path_system', 'path_system', 'path_system', 'controller', 'path', 'CONDITION', 'SYSTEM', NULL, NULL);
insert into meta values ('lathe', 'pc', 'PartCountAct', 'PartCountAct', 'controller', 'path', 'EVENT', 'PART_COUNT', NULL, NULL);
insert into meta values ('lathe', 'pcmt', 'program_cmt', 'program_cmt', 'controller', 'path', 'EVENT', 'PROGRAM_COMMENT', NULL, NULL);
insert into meta values ('lathe', 'peditmode', NULL, NULL, 'controller', 'path', 'EVENT', 'PROGRAM_EDIT', NULL, NULL);
insert into meta values ('lathe', 'peditname', NULL, NULL, 'controller', 'path', 'EVENT', 'PROGRAM_EDIT_NAME', NULL, NULL);
insert into meta values ('lathe', 'pf', 'Fact', 'Fact', 'controller', 'path', 'SAMPLE', 'PATH_FEEDRATE', 'ACTUAL', 'MILLIMETER/SECOND');
insert into meta values ('lathe', 'pfo', 'Fovr', 'Fovr', 'controller', 'path', 'EVENT', 'PATH_FEEDRATE_OVERRIDE', 'PROGRAMMED', NULL);
insert into meta values ('lathe', 'pfr', 'Frapidovr', 'Frapidovr', 'controller', 'path', 'EVENT', 'PATH_FEEDRATE_OVERRIDE', 'RAPID', NULL);
insert into meta values ('lathe', 'pgm', 'program', 'program', 'controller', 'path', 'EVENT', 'PROGRAM', NULL, NULL);
insert into meta values ('lathe', 'seq', 'sequenceNum', 'sequenceNum', 'controller', 'path', 'EVENT', 'x:SEQUENCE_NUMBER', NULL, NULL);
insert into meta values ('lathe', 'Sovr', 'Sovr', 'Sovr', 'controller', 'path', 'EVENT', 'ROTARY_VELOCITY_OVERRIDE', NULL, NULL);
insert into meta values ('lathe', 'spcmt', 'subprogram_cmt', 'subprogram_cmt', 'controller', 'path', 'EVENT', 'PROGRAM_COMMENT', 'x:SUB', NULL);
insert into meta values ('lathe', 'spgm', 'subprogram', 'subprogram', 'controller', 'path', 'EVENT', 'PROGRAM', 'x:SUB', NULL);
insert into meta values ('lathe', 'tid', 'Tool_number', 'Tool_number', 'controller', 'path', 'EVENT', 'TOOL_NUMBER', NULL, NULL);
insert into meta values ('lathe', 'tid1', 'Tool_group', 'Tool_group', 'controller', 'path', 'EVENT', 'x:TOOL_GROUP', NULL, NULL);
insert into meta values ('lathe', 'tsuf1', 'Tool_suffix', 'Tool_suffix', 'controller', 'path', 'EVENT', 'x:TOOL_SUFFIX', NULL, NULL);
insert into meta values ('lathe', 'unit', 'unitNum', 'unitNum', 'controller', 'path', 'EVENT', 'x:UNIT', NULL, NULL);
insert into meta values ('lathe', 'atime', 'auto_time', 'auto_time', 'controller', NULL, 'SAMPLE', 'ACCUMULATED_TIME', 'x:AUTO', 'SECOND');
insert into meta values ('lathe', 'ccond', 'comms_cond', 'comms_cond', 'controller', NULL, 'CONDITION', 'COMMUNICATIONS', NULL, NULL);
insert into meta values ('lathe', 'ctime', 'cut_time', 'cut_time', 'controller', NULL, 'SAMPLE', 'ACCUMULATED_TIME', 'x:CUT', 'SECOND');
insert into meta values ('lathe', 'estop', 'estop', 'estop', 'controller', NULL, 'EVENT', 'EMERGENCY_STOP', NULL, NULL);
insert into meta values ('lathe', 'logic', 'logic_cond', 'logic_cond', 'controller', NULL, 'CONDITION', 'LOGIC_PROGRAM', NULL, NULL);
insert into meta values ('lathe', 'pltnum', 'pallet_num', 'pallet_num', 'controller', NULL, 'EVENT', 'PALLET_ID', NULL, NULL);
insert into meta values ('lathe', 'system', 'system_cond', 'system_cond', 'controller', NULL, 'CONDITION', 'SYSTEM', NULL, NULL);
insert into meta values ('lathe', 'tcltime', 'total_auto_cut_time', 'total_auto_cut_time', 'controller', NULL, 'SAMPLE', 'ACCUMULATED_TIME', 'x:TOTALCUTTIME', 'SECOND');
insert into meta values ('lathe', 'yltime', 'total_time', 'total_time', 'controller', NULL, 'SAMPLE', 'ACCUMULATED_TIME', 'x:TOTAL', 'SECOND');
insert into meta values ('lathe', 'door', 'doorstate', 'doorstate', 'door', NULL, 'EVENT', 'DOOR_STATE', NULL, NULL);
insert into meta values ('lathe', 'concentration', 'CONCENTRATION', 'CONCENTRATION', 'systems', 'coolant', 'SAMPLE', 'CONCENTRATION', NULL, 'PERCENT');
insert into meta values ('lathe', 'coolhealth', 'coolant_cond', 'coolant_cond', 'systems', 'coolant', 'CONDITION', 'SYSTEM', NULL, NULL);
insert into meta values ('lathe', 'cooltemp', 'cooltemp', 'cooltemp', 'systems', 'coolant', 'SAMPLE', 'TEMPERATURE', NULL, 'CELSIUS');
insert into meta values ('lathe', 'electric', 'electric_cond', 'electric_cond', 'systems', 'electric', 'CONDITION', 'SYSTEM', NULL, NULL);
insert into meta values ('lathe', 'hydhealth', 'hydra_cond', 'hydra_cond', 'systems', 'hydraulic', 'CONDITION', 'SYSTEM', NULL, NULL);
insert into meta values ('lathe', 'lube', 'lubrication_cond', 'lubrication_cond', 'systems', 'lubrication', 'CONDITION', 'SYSTEM', NULL, NULL);
insert into meta values ('lathe', 'pneucond', 'pneu_cond', 'pneu_cond', 'systems', 'pneumatic', 'CONDITION', 'SYSTEM', NULL, NULL);
insert into meta values ('lathe', 'avail', 'avail', 'avail', NULL, NULL, 'EVENT', 'AVAILABILITY', NULL, NULL);
insert into meta values ('lathe', 'd1_asset_chg', NULL, NULL, NULL, NULL, 'EVENT', 'ASSET_CHANGED', NULL, NULL);
insert into meta values ('lathe', 'd1_asset_rem', NULL, NULL, NULL, NULL, 'EVENT', 'ASSET_REMOVED', NULL, NULL);
insert into meta values ('lathe', 'functionalmode', 'functionalmode', 'functionalmode', NULL, NULL, 'EVENT', 'FUNCTIONAL_MODE', NULL, NULL);
insert into meta values ('mill', 'af', 'Bfrt', 'Bfrt', 'base', 'B', 'SAMPLE', 'ANGULAR_VELOCITY', NULL, 'DEGREE/SECOND');
insert into meta values ('mill', 'al', 'Bload', 'Bload', 'base', 'B', 'SAMPLE', 'LOAD', NULL, 'PERCENT');
insert into meta values ('mill', 'aposm', 'Babs', 'Babs', 'base', 'B', 'SAMPLE', 'ANGLE', 'ACTUAL', 'DEGREE');
insert into meta values ('mill', 'aposw', 'Bpos', 'Bpos', 'base', 'B', 'SAMPLE', 'ANGLE', 'ACTUAL', 'DEGREE');
insert into meta values ('mill', 'arf', 'arfunc', 'arfunc', 'base', 'B', 'EVENT', 'ROTARY_MODE', NULL, NULL);
insert into meta values ('mill', 'at', 'Btravel', 'Btravel', 'base', 'B', 'CONDITION', 'ANGLE', NULL, NULL);
insert into meta values ('mill', 'baxisstate', NULL, NULL, 'base', 'B', 'EVENT', 'AXIS_STATE', NULL, NULL);
insert into meta values ('mill', 'caxisstate', NULL, NULL, 'base', 'C', 'EVENT', 'AXIS_STATE', NULL, NULL);
insert into meta values ('mill', 'cf', 'Cfrt', 'Cfrt', 'base', 'C', 'SAMPLE', 'ANGULAR_VELOCITY', NULL, 'DEGREE/SECOND');
insert into meta values ('mill', 'cl', 'Cload', 'Cload', 'base', 'C', 'SAMPLE', 'LOAD', NULL, 'PERCENT');
insert into meta values ('mill', 'cposm', 'Cabs', 'Cabs', 'base', 'C', 'SAMPLE', 'ANGLE', 'ACTUAL', 'DEGREE');
insert into meta values ('mill', 'cposw', 'Cpos', 'Cpos', 'base', 'C', 'SAMPLE', 'ANGLE', 'ACTUAL', 'DEGREE');
insert into meta values ('mill', 'ct', 'Ctravel', 'Ctravel', 'base', 'C', 'CONDITION', 'ANGLE', NULL, NULL);
insert into meta values ('mill', 'ctemp', 'Stemp', 'Stemp', 'base', 'C', 'SAMPLE', 'TEMPERATURE', NULL, 'CELSIUS');
insert into meta values ('mill', 'cs', 'Srpm', 'Srpm', 'base', 'C', 'SAMPLE', 'ROTARY_VELOCITY', 'ACTUAL', 'REVOLUTION/MINUTE');
insert into meta values ('mill', 'rf', 'crfunc', 'crfunc', 'base', 'C', 'EVENT', 'ROTARY_MODE', NULL, NULL);
insert into meta values ('mill', 'sl', 'Sload', 'Sload', 'base', 'C', 'SAMPLE', 'LOAD', NULL, 'PERCENT');
insert into meta values ('mill', 'spc', 'Sload_cond', 'Sload_cond', 'base', 'C', 'CONDITION', 'LOAD', NULL, NULL);
insert into meta values ('mill', 'tmp', 'Stemp_cond', 'Stemp_cond', 'base', 'C', 'CONDITION', 'TEMPERATURE', NULL, NULL);
insert into meta values ('mill', 'xaxisstate', NULL, NULL, 'base', 'X', 'EVENT', 'AXIS_STATE', NULL, NULL);
insert into meta values ('mill', 'xf', 'Xfrt', 'Xfrt', 'base', 'X', 'SAMPLE', 'AXIS_FEEDRATE', NULL, 'MILLIMETER/SECOND');
insert into meta values ('mill', 'xl', 'Xload', 'Xload', 'base', 'X', 'SAMPLE', 'LOAD', NULL, 'PERCENT');
insert into meta values ('mill', 'xpm', 'Xabs', 'Xabs', 'base', 'X', 'SAMPLE', 'POSITION', 'ACTUAL', 'MILLIMETER');
insert into meta values ('mill', 'xpw', 'Xpos', 'Xpos', 'base', 'X', 'SAMPLE', 'POSITION', 'ACTUAL', 'MILLIMETER');
insert into meta values ('mill', 'xt', 'Xtravel', 'Xtravel', 'base', 'X', 'CONDITION', 'POSITION', NULL, NULL);
insert into meta values ('mill', 'yaxisstate', NULL, NULL, 'base', 'Y', 'EVENT', 'AXIS_STATE', NULL, NULL);
insert into meta values ('mill', 'yf', 'Yfrt', 'Yfrt', 'base', 'Y', 'SAMPLE', 'AXIS_FEEDRATE', NULL, 'MILLIMETER/SECOND');
insert into meta values ('mill', 'yl', 'Yload', 'Yload', 'base', 'Y', 'SAMPLE', 'LOAD', NULL, 'PERCENT');
insert into meta values ('mill', 'ypm', 'Yabs', 'Yabs', 'base', 'Y', 'SAMPLE', 'POSITION', 'ACTUAL', 'MILLIMETER');
insert into meta values ('mill', 'ypw', 'Ypos', 'Ypos', 'base', 'Y', 'SAMPLE', 'POSITION', 'ACTUAL', 'MILLIMETER');
insert into meta values ('mill', 'yt', 'Ytravel', 'Ytravel', 'base', 'Y', 'CONDITION', 'POSITION', NULL, NULL);
insert into meta values ('mill', 'zaxisstate', NULL, NULL, 'base', 'Z', 'EVENT', 'AXIS_STATE', NULL, NULL);
insert into meta values ('mill', 'zf', 'Zfrt', 'Zfrt', 'base', 'Z', 'SAMPLE', 'AXIS_FEEDRATE', NULL, 'MILLIMETER/SECOND');
insert into meta values ('mill', 'zl', 'Zload', 'Zload', 'base', 'Z', 'SAMPLE', 'LOAD', NULL, 'PERCENT');
insert into meta values ('mill', 'zpm', 'Zabs', 'Zabs', 'base', 'Z', 'SAMPLE', 'POSITION', 'ACTUAL', 'MILLIMETER');
insert into meta values ('mill', 'zpw', 'Zpos', 'Zpos', 'base', 'Z', 'SAMPLE', 'POSITION', 'ACTUAL', 'MILLIMETER');
insert into meta values ('mill', 'zt', 'Ztravel', 'Ztravel', 'base', 'Z', 'CONDITION', 'POSITION', NULL, NULL);
insert into meta values ('mill', 'servo', 'servo_cond', 'servo_cond', 'base', NULL, 'CONDITION', 'ACTUATOR', NULL, NULL);
insert into meta values ('mill', 'spndl', 'spindle_cond', 'spindle_cond', 'base', NULL, 'CONDITION', 'SYSTEM', NULL, NULL);
insert into meta values ('mill', 'exec', 'execution', 'execution', 'controller', 'path', 'EVENT', 'EXECUTION', NULL, NULL);
insert into meta values ('mill', 'hd1chuckstate', NULL, NULL, 'controller', 'path', 'EVENT', 'CHUCK_STATE', NULL, NULL);
insert into meta values ('mill', 'ln', 'line', 'line', 'controller', 'path', 'EVENT', 'LINE', NULL, NULL);
insert into meta values ('mill', 'mode', 'mode', 'mode', 'controller', 'path', 'EVENT', 'CONTROLLER_MODE', NULL, NULL);
insert into meta values ('mill', 'motion', 'motion_cond', 'motion_cond', 'controller', 'path', 'CONDITION', 'MOTION_PROGRAM', NULL, NULL);
insert into meta values ('mill', 'path_system', 'path_system', 'path_system', 'controller', 'path', 'CONDITION', 'SYSTEM', NULL, NULL);
insert into meta values ('mill', 'pc', 'PartCountAct', 'PartCountAct', 'controller', 'path', 'EVENT', 'PART_COUNT', NULL, NULL);
insert into meta values ('mill', 'pcmt', 'program_cmt', 'program_cmt', 'controller', 'path', 'EVENT', 'PROGRAM_COMMENT', NULL, NULL);
insert into meta values ('mill', 'peditmode', NULL, NULL, 'controller', 'path', 'EVENT', 'PROGRAM_EDIT', NULL, NULL);
insert into meta values ('mill', 'peditname', NULL, NULL, 'controller', 'path', 'EVENT', 'PROGRAM_EDIT_NAME', NULL, NULL);
insert into meta values ('mill', 'pf', 'Fact', 'Fact', 'controller', 'path', 'SAMPLE', 'PATH_FEEDRATE', 'ACTUAL', 'MILLIMETER/SECOND');
insert into meta values ('mill', 'pfo', 'Fovr', 'Fovr', 'controller', 'path', 'EVENT', 'PATH_FEEDRATE_OVERRIDE', 'PROGRAMMED', NULL);
insert into meta values ('mill', 'pfr', 'Frapidovr', 'Frapidovr', 'controller', 'path', 'EVENT', 'PATH_FEEDRATE_OVERRIDE', 'RAPID', NULL);
insert into meta values ('mill', 'pgm', 'program', 'program', 'controller', 'path', 'EVENT', 'PROGRAM', NULL, NULL);
insert into meta values ('mill', 'seq', 'sequenceNum', 'sequenceNum', 'controller', 'path', 'EVENT', 'x:SEQUENCE_NUMBER', NULL, NULL);
insert into meta values ('mill', 'Sovr', 'Sovr', 'Sovr', 'controller', 'path', 'EVENT', 'ROTARY_VELOCITY_OVERRIDE', NULL, NULL);
insert into meta values ('mill', 'spcmt', 'subprogram_cmt', 'subprogram_cmt', 'controller', 'path', 'EVENT', 'PROGRAM_COMMENT', 'x:SUB', NULL);
insert into meta values ('mill', 'spgm', 'subprogram', 'subprogram', 'controller', 'path', 'EVENT', 'PROGRAM', 'x:SUB', NULL);
insert into meta values ('mill', 'tid', 'Tool_number', 'Tool_number', 'controller', 'path', 'EVENT', 'TOOL_NUMBER', NULL, NULL);
insert into meta values ('mill', 'tid2', 'Tool_group', 'Tool_group', 'controller', 'path', 'EVENT', 'x:TOOL_GROUP', NULL, NULL);
insert into meta values ('mill', 'tid3', 'Tool_suffix', 'Tool_suffix', 'controller', 'path', 'EVENT', 'x:TOOL_SUFFIX', NULL, NULL);
insert into meta values ('mill', 'unit', 'unitNum', 'unitNum', 'controller', 'path', 'EVENT', 'x:UNIT', NULL, NULL);
insert into meta values ('mill', 'atime', 'auto_time', 'auto_time', 'controller', NULL, 'SAMPLE', 'ACCUMULATED_TIME', 'x:AUTO', 'SECOND');
insert into meta values ('mill', 'ccond', 'comms_cond', 'comms_cond', 'controller', NULL, 'CONDITION', 'COMMUNICATIONS', NULL, NULL);
insert into meta values ('mill', 'ctime', 'cut_time', 'cut_time', 'controller', NULL, 'SAMPLE', 'ACCUMULATED_TIME', 'x:CUT', 'SECOND');
insert into meta values ('mill', 'estop', 'estop', 'estop', 'controller', NULL, 'EVENT', 'EMERGENCY_STOP', NULL, NULL);
insert into meta values ('mill', 'logic', 'logic_cond', 'logic_cond', 'controller', NULL, 'CONDITION', 'LOGIC_PROGRAM', NULL, NULL);
insert into meta values ('mill', 'pltnum', 'pallet_num', 'pallet_num', 'controller', NULL, 'EVENT', 'PALLET_ID', NULL, NULL);
insert into meta values ('mill', 'system', 'system_cond', 'system_cond', 'controller', NULL, 'CONDITION', 'SYSTEM', NULL, NULL);
insert into meta values ('mill', 'tcltime', 'total_auto_cut_time', 'total_auto_cut_time', 'controller', NULL, 'SAMPLE', 'ACCUMULATED_TIME', 'x:TOTALCUTTIME', 'SECOND');
insert into meta values ('mill', 'yltime', 'total_time', 'total_time', 'controller', NULL, 'SAMPLE', 'ACCUMULATED_TIME', 'x:TOTAL', 'SECOND');
insert into meta values ('mill', 'door', 'doorstate', 'doorstate', 'door', NULL, 'EVENT', 'DOOR_STATE', NULL, NULL);
insert into meta values ('mill', 'concentration', 'CONCENTRATION', 'CONCENTRATION', 'systems', 'coolant', 'SAMPLE', 'CONCENTRATION', NULL, 'PERCENT');
insert into meta values ('mill', 'coolhealth', 'coolant_cond', 'coolant_cond', 'systems', 'coolant', 'CONDITION', 'SYSTEM', NULL, NULL);
insert into meta values ('mill', 'cooltemp', 'cooltemp', 'cooltemp', 'systems', 'coolant', 'SAMPLE', 'TEMPERATURE', NULL, 'CELSIUS');
insert into meta values ('mill', 'electric', 'electric_cond', 'electric_cond', 'systems', 'electric', 'CONDITION', 'SYSTEM', NULL, NULL);
insert into meta values ('mill', 'hydhealth', 'hydra_cond', 'hydra_cond', 'systems', 'hydraulic', 'CONDITION', 'SYSTEM', NULL, NULL);
insert into meta values ('mill', 'lube', 'lubrication_cond', 'lubrication_cond', 'systems', 'lubrication', 'CONDITION', 'SYSTEM', NULL, NULL);
insert into meta values ('mill', 'pneucond', 'pneu_cond', 'pneu_cond', 'systems', 'pneumatic', 'CONDITION', 'SYSTEM', NULL, NULL);
insert into meta values ('mill', 'avail', 'avail', 'avail', NULL, NULL, 'EVENT', 'AVAILABILITY', NULL, NULL);
insert into meta values ('mill', 'd1_asset_chg', NULL, NULL, NULL, NULL, 'EVENT', 'ASSET_CHANGED', NULL, NULL);
insert into meta values ('mill', 'd1_asset_rem', NULL, NULL, NULL, NULL, 'EVENT', 'ASSET_REMOVED', NULL, NULL);
insert into meta values ('mill', 'functionalmode', 'functionalmode', 'functionalmode', NULL, NULL, 'EVENT', 'FUNCTIONAL_MODE', NULL, NULL);


create table "user" (
    id character varying (200) not null primary key,
    name character varying (200) not null,
    status character varying (200) not null,
    login_name character varying (200) null constraint uq_user_login unique,
    password_verifier character varying (200) null,
    public_key character varying (200) null,
    pwd_reset_token VARCHAR(200) null,
    pwd_reset_token_status VARCHAR(200) null,
    pwd_reset_token_created timestamp with time zone NULL,
    customer VARCHAR(200) null,
    email VARCHAR(200) null
);

GRANT ALL ON TABLE "user" TO i4capi;


create table "role" (
    name character varying (200) not null primary key,
    status character varying (200) not null
);

GRANT ALL ON TABLE "role" TO i4capi;


create table "user_role" (
    "user" character varying (200) not null constraint fk_userrole_user references "user",
    "role" character varying (200) not null constraint fk_userrole_role references "role",
    primary key ("user", "role")
);

GRANT ALL ON TABLE "user_role" TO i4capi;


create table "role_subrole" (
    "role" character varying (200) not null constraint fk_rolesub_role references "role",
    "subrole" character varying (200) not null constraint fk_rolesub_sub references "role",
    primary key ("role", "subrole")
);

GRANT ALL ON TABLE "role_subrole" TO i4capi;


create table "role_grant" (
    "role" character varying (200) not null constraint fk_rolegr_role references "role",
    "endpoint" character varying (500) not null,
    "features" character varying (200) [] not null,
    primary key ("role", "endpoint")
);

GRANT ALL ON TABLE "role_grant" TO i4capi;


insert into role values ('admin', 'active');

insert into role_grant values ('admin', 'get/login', array[]::varchar[]);
insert into role_grant values ('admin', 'get/privs', array[]::varchar[]);
insert into role_grant values ('admin', 'get/customers', array[]::varchar[]);
insert into role_grant values ('admin', 'get/files', array[]::varchar[]);
insert into role_grant values ('admin', 'get/log/snapshot', array[]::varchar[]);
insert into role_grant values ('admin', 'get/log/find', array[]::varchar[]);
insert into role_grant values ('admin', 'get/log/meta', array[]::varchar[]);
insert into role_grant values ('admin', 'post/log', array[]::varchar[]);
insert into role_grant values ('admin', 'get/log/last_instance', array[]::varchar[]);
insert into role_grant values ('admin', 'get/users/create_password', array[]::varchar[]);
insert into role_grant values ('admin', 'get/users', array[]::varchar[]);
insert into role_grant values ('admin', 'get/users/{id}', array[]::varchar[]);
insert into role_grant values ('admin', 'put/users/{id}', array['modify others','modify role']::varchar[]);
insert into role_grant values ('admin', 'patch/users/{id}', array['modify others']::varchar[]);
insert into role_grant values ('admin', 'get/roles', array[]::varchar[]);
insert into role_grant values ('admin', 'get/roles/{name}', array[]::varchar[]);
insert into role_grant values ('admin', 'put/roles/{name}', array[]::varchar[]);
insert into role_grant values ('admin', 'get/projects', array[]::varchar[]);
insert into role_grant values ('admin', 'get/projects/{name}', array[]::varchar[]);
insert into role_grant values ('admin', 'post/projects', array[]::varchar[]);
insert into role_grant values ('admin', 'patch/projects/{name}', array[]::varchar[]);
insert into role_grant values ('admin', 'get/projects/{name}/v/{ver}', array[]::varchar[]);
insert into role_grant values ('admin', 'post/projects/{name}/v', array[]::varchar[]);
insert into role_grant values ('admin', 'patch/projects/{name}/v/{ver}', array[]::varchar[]);
insert into role_grant values ('admin', 'post/installations/{project}/{version}', array[]::varchar[]);
insert into role_grant values ('admin', 'get/installations', array[]::varchar[]);
insert into role_grant values ('admin', 'patch/installations/{id}', array[]::varchar[]);
insert into role_grant values ('admin', 'get/installations/{id}/{savepath:path}', array[]::varchar[]);
insert into role_grant values ('admin', 'get/intfiles', array[]::varchar[]);
insert into role_grant values ('admin', 'get/intfiles/v/{ver}/{path:path}', array[]::varchar[]);
insert into role_grant values ('admin', 'put/intfiles/v/{ver}/{path:path}', array[]::varchar[]);
insert into role_grant values ('admin', 'delete/intfiles/v/{ver}/{path:path}', array[]::varchar[]);
insert into role_grant values ('admin', 'get/workpiece/{id}', array[]::varchar[]);
insert into role_grant values ('admin', 'get/workpiece', array[]::varchar[]);
insert into role_grant values ('admin', 'patch/workpiece/{id}', array[]::varchar[]);
insert into role_grant values ('admin', 'put/tools', array[]::varchar[]);
insert into role_grant values ('admin', 'delete/tools', array[]::varchar[]);
insert into role_grant values ('admin', 'patch/tools/{tool_id}', array[]::varchar[]);
insert into role_grant values ('admin', 'get/tools', array[]::varchar[]);
insert into role_grant values ('admin', 'get/tools/list_usage', array[]::varchar[]);
insert into role_grant values ('admin', 'get/batch', array[]::varchar[]);
insert into role_grant values ('admin', 'put/batch/{id}', array[]::varchar[]);
insert into role_grant values ('admin', 'put/alarm/defs/{name}', array[]::varchar[]);
insert into role_grant values ('admin', 'get/alarm/defs/{name}', array[]::varchar[]);
insert into role_grant values ('admin', 'get/alarm/defs', array[]::varchar[]);
insert into role_grant values ('admin', 'get/alarm/subsgroupusage', array['any user']::varchar[]);
insert into role_grant values ('admin', 'get/alarm/subsgroups/{name}', array[]::varchar[]);
insert into role_grant values ('admin', 'get/alarm/subsgroups', array[]::varchar[]);
insert into role_grant values ('admin', 'put/alarm/subsgroups/{name}', array[]::varchar[]);
insert into role_grant values ('admin', 'delete/alarm/subsgroups/{name}', array[]::varchar[]);
insert into role_grant values ('admin', 'get/alarm/subs', array['any user']::varchar[]);
insert into role_grant values ('admin', 'get/alarm/subs/{id}', array['any user']::varchar[]);
insert into role_grant values ('admin', 'post/alarm/subs', array['any user']::varchar[]);
insert into role_grant values ('admin', 'patch/alarm/subs/{id}', array['any user']::varchar[]);
insert into role_grant values ('admin', 'post/alarm/events/check', array[]::varchar[]);
insert into role_grant values ('admin', 'get/alarm/events', array[]::varchar[]);
insert into role_grant values ('admin', 'get/alarm/events/{id}', array[]::varchar[]);
insert into role_grant values ('admin', 'get/alarm/recips', array[]::varchar[]);
insert into role_grant values ('admin', 'get/alarm/recips/{id}', array[]::varchar[]);
insert into role_grant values ('admin', 'patch/alarm/recips/{id}', array[]::varchar[]);
insert into role_grant values ('admin', 'get/stat/def', array[]::varchar[]);
insert into role_grant values ('admin', 'get/stat/def/{id}', array[]::varchar[]);
insert into role_grant values ('admin', 'post/stat/def', array[]::varchar[]);
insert into role_grant values ('admin', 'delete/stat/def/{id}', array['delete any']::varchar[]);
insert into role_grant values ('admin', 'patch/stat/def/{id}', array['patch any']::varchar[]);
insert into role_grant values ('admin', 'get/stat/data/{id}', array[]::varchar[]);
insert into role_grant values ('admin', 'get/stat/objmeta', array[]::varchar[]);
insert into role_grant values ('admin', 'post/pwdreset/init', array[]::varchar[]);
insert into role_grant values ('admin', 'post/pwdreset/setpass', array[]::varchar[]);
insert into role_grant values ('admin', 'get/pwdreset', array[]::varchar[]);
insert into role_grant values ('admin', 'post/pwdreset/sent', array[]::varchar[]);
insert into role_grant values ('admin', 'post/pwdreset/fail', array[]::varchar[]);
insert into role_grant values ('admin', 'get/settings/{key}', array['access private']::varchar[]);
insert into role_grant values ('admin', 'put/settings/{key}', array[]::varchar[]);
insert into role_grant values ('admin', 'get/ping/noop', array[]::varchar[]);
insert into role_grant values ('admin', 'get/ping/datetime', array[]::varchar[]);
insert into role_grant values ('admin', 'post/ping/noop', array[]::varchar[]);
insert into role_grant values ('admin', 'get/ping/pwd', array[]::varchar[]);
insert into role_grant values ('admin', 'get/ping/sign', array[]::varchar[]);
insert into role_grant values ('admin', 'get/ping/db', array[]::varchar[]);
insert into role_grant values ('admin', 'get/audit', array[]::varchar[]);

insert into "user" (id, name, status, login_name, public_key)
  values ('admin', 'Admin', 'active', 'admin', 'UnkAezftneExNf8W5Py14LiOH4HQLRzbi6c0NY90sSI=');
insert into "user_role" values ('admin', 'admin');

insert into "user" (id, name, status, login_name, password_verifier)
  values ('bastion_admin', 'Bastion Admin', 'active', 'bastion_admin', 'Rvtr9BhIYGud5I1ym7c3igR8djguqXo2ddxwEnnIIcMy4YT1');
insert into "user_role" values ('bastion_admin', 'admin');


insert into role values ('power_user', 'active');

insert into role_grant values ('power_user', 'get/login', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/privs', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/customers', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/files', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/log/snapshot', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/log/find', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/log/meta', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/users/create_password', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/users', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/users/{id}', array[]::varchar[]);
insert into role_grant values ('power_user', 'patch/users/{id}', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/roles', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/roles/{name}', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/projects', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/projects/{name}', array[]::varchar[]);
insert into role_grant values ('power_user', 'post/projects', array[]::varchar[]);
insert into role_grant values ('power_user', 'patch/projects/{name}', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/projects/{name}/v/{ver}', array[]::varchar[]);
insert into role_grant values ('power_user', 'post/projects/{name}/v', array[]::varchar[]);
insert into role_grant values ('power_user', 'patch/projects/{name}/v/{ver}', array[]::varchar[]);
insert into role_grant values ('power_user', 'post/installations/{project}/{version}', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/installations', array[]::varchar[]);
insert into role_grant values ('power_user', 'patch/installations/{id}', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/installations/{id}/{savepath:path}', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/intfiles', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/intfiles/v/{ver}/{path:path}', array[]::varchar[]);
insert into role_grant values ('power_user', 'put/intfiles/v/{ver}/{path:path}', array[]::varchar[]);
insert into role_grant values ('power_user', 'delete/intfiles/v/{ver}/{path:path}', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/workpiece/{id}', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/workpiece', array[]::varchar[]);
insert into role_grant values ('power_user', 'patch/workpiece/{id}', array[]::varchar[]);
insert into role_grant values ('power_user', 'put/tools', array[]::varchar[]);
insert into role_grant values ('power_user', 'delete/tools', array[]::varchar[]);
insert into role_grant values ('power_user', 'patch/tools/{tool_id}', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/tools', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/tools/list_usage', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/batch', array[]::varchar[]);
insert into role_grant values ('power_user', 'put/batch/{id}', array[]::varchar[]);
insert into role_grant values ('power_user', 'put/alarm/defs/{name}', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/alarm/defs/{name}', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/alarm/defs', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/alarm/subsgroupusage', array['any user']::varchar[]);
insert into role_grant values ('power_user', 'get/alarm/subsgroups/{name}', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/alarm/subsgroups', array[]::varchar[]);
insert into role_grant values ('power_user', 'put/alarm/subsgroups/{name}', array[]::varchar[]);
insert into role_grant values ('power_user', 'delete/alarm/subsgroups/{name}', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/alarm/subs', array['any user']::varchar[]);
insert into role_grant values ('power_user', 'get/alarm/subs/{id}', array['any user']::varchar[]);
insert into role_grant values ('power_user', 'post/alarm/subs', array['any user']::varchar[]);
insert into role_grant values ('power_user', 'patch/alarm/subs/{id}', array['any user']::varchar[]);
insert into role_grant values ('power_user', 'post/alarm/events/check', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/alarm/events', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/alarm/events/{id}', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/alarm/recips', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/alarm/recips/{id}', array[]::varchar[]);
insert into role_grant values ('power_user', 'patch/alarm/recips/{id}', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/stat/def', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/stat/def/{id}', array[]::varchar[]);
insert into role_grant values ('power_user', 'post/stat/def', array[]::varchar[]);
insert into role_grant values ('power_user', 'delete/stat/def/{id}', array[]::varchar[]);
insert into role_grant values ('power_user', 'patch/stat/def/{id}', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/stat/data/{id}', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/stat/objmeta', array[]::varchar[]);
insert into role_grant values ('power_user', 'post/pwdreset/init', array[]::varchar[]);
insert into role_grant values ('power_user', 'post/pwdreset/setpass', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/pwdreset', array[]::varchar[]);
insert into role_grant values ('power_user', 'post/pwdreset/sent', array[]::varchar[]);
insert into role_grant values ('power_user', 'post/pwdreset/fail', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/settings/{key}', array[]::varchar[]);
insert into role_grant values ('power_user', 'put/settings/{key}', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/ping/noop', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/ping/datetime', array[]::varchar[]);
insert into role_grant values ('power_user', 'post/ping/noop', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/ping/pwd', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/ping/sign', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/ping/db', array[]::varchar[]);
insert into role_grant values ('power_user', 'get/audit', array[]::varchar[]);


insert into role values ('customer', 'active');

insert into role_grant values ('customer', 'get/log/meta', array[]::varchar[]);
insert into role_grant values ('customer', 'get/login', array[]::varchar[]);
insert into role_grant values ('customer', 'get/workpiece/{id}', array[]::varchar[]);
insert into role_grant values ('customer', 'get/workpiece', array[]::varchar[]);
insert into role_grant values ('customer', 'get/batch', array[]::varchar[]);
insert into role_grant values ('customer', 'get/stat/def', array[]::varchar[]);
insert into role_grant values ('customer', 'get/stat/def/{id}', array[]::varchar[]);
insert into role_grant values ('customer', 'get/stat/data/{id}', array[]::varchar[]);
insert into role_grant values ('customer', 'get/users', array[]::varchar[]);
insert into role_grant values ('customer', 'get/users/{id}', array[]::varchar[]);
insert into role_grant values ('customer', 'patch/users/{id}', array[]::varchar[]);
insert into role_grant values ('customer', 'get/stat/objmeta', array[]::varchar[]);
insert into role_grant values ('customer', 'get/ping/noop', array[]::varchar[]);
insert into role_grant values ('customer', 'get/ping/datetime', array[]::varchar[]);
insert into role_grant values ('customer', 'post/ping/noop', array[]::varchar[]);
insert into role_grant values ('customer', 'get/ping/sign', array[]::varchar[]);
insert into role_grant values ('customer', 'get/ping/db', array[]::varchar[]);


insert into role values ('pwdresetbot', 'active');

insert into role_grant values ('pwdresetbot', 'get/pwdreset', array[]::varchar[]);
insert into role_grant values ('pwdresetbot', 'post/pwdreset/sent', array[]::varchar[]);
insert into role_grant values ('pwdresetbot', 'post/pwdreset/fail', array[]::varchar[]);
insert into role_grant values ('pwdresetbot', 'get/ping/noop', array[]::varchar[]);
insert into role_grant values ('pwdresetbot', 'get/ping/datetime', array[]::varchar[]);
insert into role_grant values ('pwdresetbot', 'post/ping/noop', array[]::varchar[]);
insert into role_grant values ('pwdresetbot', 'get/ping/sign', array[]::varchar[]);
insert into role_grant values ('pwdresetbot', 'get/ping/db', array[]::varchar[]);

insert into "user" (id, name, status, login_name) values ('pwdresetbot', 'pwdresetbot', 'active', 'pwdresetbot');
insert into "user_role" values ('pwdresetbot', 'pwdresetbot');


insert into role values ('logwriter', 'active');

insert into role_grant values ('logwriter', 'post/log', array[]::varchar[]);
insert into role_grant values ('logwriter', 'get/log/last_instance', array[]::varchar[]);
insert into role_grant values ('logwriter', 'put/intfiles/v/{ver}/{path:path}', array[]::varchar[]);
insert into role_grant values ('logwriter', 'get/ping/noop', array[]::varchar[]);
insert into role_grant values ('logwriter', 'get/ping/datetime', array[]::varchar[]);
insert into role_grant values ('logwriter', 'post/ping/noop', array[]::varchar[]);
insert into role_grant values ('logwriter', 'get/ping/sign', array[]::varchar[]);
insert into role_grant values ('logwriter', 'get/ping/db', array[]::varchar[]);

insert into "user" (id, name, status, login_name) values ('logwriter', 'logwriter', 'active', 'logwriter');
insert into "user_role" values ('logwriter', 'logwriter');


insert into role values ('alarmcheckbot', 'active');

insert into role_grant values ('alarmcheckbot', 'post/alarm/events/check', array['noaudit']::varchar[]);
insert into role_grant values ('alarmcheckbot', 'get/ping/noop', array[]::varchar[]);
insert into role_grant values ('alarmcheckbot', 'get/ping/datetime', array[]::varchar[]);
insert into role_grant values ('alarmcheckbot', 'post/ping/noop', array[]::varchar[]);
insert into role_grant values ('alarmcheckbot', 'get/ping/sign', array[]::varchar[]);
insert into role_grant values ('alarmcheckbot', 'get/ping/db', array[]::varchar[]);

insert into "user" (id, name, status, login_name) values ('alarmcheckbot', 'alarmcheckbot', 'active', 'alarmcheckbot');
insert into "user_role" values ('alarmcheckbot', 'alarmcheckbot');


insert into role values ('alarmpushbot', 'active');

insert into role_grant values ('alarmpushbot', 'get/alarm/recips', array['noaudit']::varchar[]);
insert into role_grant values ('alarmpushbot', 'patch/alarm/recips/{id}', array[]::varchar[]);
insert into role_grant values ('alarmpushbot', 'get/settings/{key}', array['access private']::varchar[]);
insert into role_grant values ('alarmpushbot', 'get/ping/noop', array[]::varchar[]);
insert into role_grant values ('alarmpushbot', 'get/ping/datetime', array[]::varchar[]);
insert into role_grant values ('alarmpushbot', 'post/ping/noop', array[]::varchar[]);
insert into role_grant values ('alarmpushbot', 'get/ping/sign', array[]::varchar[]);
insert into role_grant values ('alarmpushbot', 'get/ping/db', array[]::varchar[]);

insert into "user" (id, name, status, login_name) values ('alarmpushbot', 'alarmpushbot', 'active', 'alarmpushbot');
insert into "user_role" values ('alarmpushbot', 'alarmpushbot');


insert into role values ('alarmemailbot', 'active');

insert into role_grant values ('alarmemailbot', 'get/alarm/recips', array['noaudit']::varchar[]);
insert into role_grant values ('alarmemailbot', 'patch/alarm/recips/{id}', array[]::varchar[]);
insert into role_grant values ('alarmemailbot', 'get/ping/noop', array[]::varchar[]);
insert into role_grant values ('alarmemailbot', 'get/ping/datetime', array[]::varchar[]);
insert into role_grant values ('alarmemailbot', 'post/ping/noop', array[]::varchar[]);
insert into role_grant values ('alarmemailbot', 'get/ping/sign', array[]::varchar[]);
insert into role_grant values ('alarmemailbot', 'get/ping/db', array[]::varchar[]);

insert into "user" (id, name, status, login_name) values ('alarmemailbot', 'alarmemailbot', 'active', 'alarmemailbot');
insert into "user_role" values ('alarmemailbot', 'alarmemailbot');


insert into role values ('installbot', 'active');

insert into role_grant values ('installbot', 'get/installations', array['noaudit']::varchar[]);
insert into role_grant values ('installbot', 'patch/installations/{id}', array[]::varchar[]);
insert into role_grant values ('installbot', 'get/installations/{id}/{savepath:path}', array[]::varchar[]);
insert into role_grant values ('installbot', 'get/ping/noop', array[]::varchar[]);
insert into role_grant values ('installbot', 'get/ping/datetime', array[]::varchar[]);
insert into role_grant values ('installbot', 'post/ping/noop', array[]::varchar[]);
insert into role_grant values ('installbot', 'get/ping/sign', array[]::varchar[]);
insert into role_grant values ('installbot', 'get/ping/db', array[]::varchar[]);

insert into "user" (id, name, status, login_name) values ('installbot', 'installbot', 'active', 'installbot');
insert into "user_role" values ('installbot', 'installbot');


create table "projects" (
    name character varying (200) not null primary key,
    status character varying (200) not null,
    extra json null
);

GRANT ALL ON TABLE "projects" TO i4capi;


create table "project_version" (
    id SERIAL PRIMARY KEY,
    project character varying (200) not null constraint fk_project references "projects",
    ver integer not null,
    status character varying (200) not null
);

CREATE UNIQUE INDEX idx_project_ver ON "project_version" (project, ver);

GRANT ALL ON TABLE "project_version" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE project_version_id_seq TO i4capi;


create table "project_label" (
    project_ver integer not null constraint fk_pv references "project_version",
    label character varying (200) null
);

GRANT ALL ON TABLE "project_label" TO i4capi;


create table "file_git" (
    id SERIAL PRIMARY KEY,
    repo character varying (200) not null,
    name character varying (200) not null,
    commit character varying (200) not null
);

GRANT ALL ON TABLE "file_git" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE file_git_id_seq TO i4capi;


create table "file_unc" (
    id SERIAL PRIMARY KEY,
    name character varying (200) not null
);

GRANT ALL ON TABLE "file_unc" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE file_unc_id_seq TO i4capi;


create table "file_int" (
    id SERIAL PRIMARY KEY,
    name character varying (200) not null,
    ver integer,
    content_hash character varying (200) not null
);

CREATE UNIQUE INDEX idx_file_int_name_ver ON "file_int" (name, ver);

GRANT ALL ON TABLE "file_int" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE file_int_id_seq TO i4capi;


create table "project_file" (
    project_ver integer not null constraint pv references "project_version",
    savepath character varying (2000) not null,
    file_git integer null constraint fk_git references "file_git",
    file_unc integer null constraint fk_unc references "file_unc",
    file_int integer null constraint fk_int references "file_int",
    primary key (project_ver, savepath)
);

GRANT ALL ON TABLE "project_file" TO i4capi;


create table "installation" (
    id SERIAL PRIMARY KEY,
    "timestamp" timestamp with time zone NOT NULL,
    project character varying (200) not null constraint fk_project references "projects",
    invoked_version character varying (200) not null,
    real_version int not null,
    status character varying (200) not null,
    status_msg character varying (200) null
);

GRANT ALL ON TABLE "installation" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE installation_id_seq TO i4capi;


create table "installation_file" (
    id SERIAL PRIMARY KEY,
    installation integer not null constraint fk_project references "installation",
    savepath character varying (2000) not null
);

GRANT ALL ON TABLE "installation_file" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE installation_file_id_seq TO i4capi;


create table "workpiece" (
    id character varying (200) not null primary key,
    batch character varying (200) null,
    manual_status character varying (200) null
);
GRANT ALL ON TABLE "workpiece" TO i4capi;


create table "workpiece_note" (
    id SERIAL PRIMARY KEY,
    workpiece character varying (200) not null,
    "user" character varying (200) not null constraint fk_userrole_user references "user",
    "timestamp" timestamp with time zone NOT NULL,
    "text" text NOT NULL,
    deleted boolean NOT NULL default false
);

GRANT ALL ON TABLE "workpiece_note" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE workpiece_note_id_seq TO i4capi;


create table "tools" (
    id character varying (200) not null primary key,
    "type" character varying (200) null
);

GRANT ALL ON TABLE "tools" TO i4capi;


create table alarm_subsgroup (
  "group" varchar(200) not null,
  primary key ("group")
);

GRANT ALL ON TABLE alarm_subsgroup TO i4capi;


create table "alarm" (
    id SERIAL PRIMARY KEY,
    name character varying (200) not null constraint uq_alarm_name unique,
    "window" double precision null,
    max_freq double precision null,
    last_check timestamp with time zone not NULL,
    last_report timestamp with time zone NULL,
    subsgroup character varying (200) not null CONSTRAINT fk_alarm__alarm_subsgroup REFERENCES alarm_subsgroup ("group")
);

GRANT ALL ON TABLE "alarm" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE alarm_id_seq TO i4capi;


create table "alarm_cond" (
    id SERIAL PRIMARY KEY,
    alarm integer not null constraint fk_pv references "alarm",
    log_row_category character varying (200) not null,
    device character varying (200) not null,
    data_id character varying (200) not null,
    aggregate_period double precision null,
    aggregate_count integer null,
    aggregate_method character varying (200) null,
    rel character varying (200) null,
    value_num double precision null,
    value_text character varying (200) null,
    age_min double precision null,
    age_max double precision null
);

GRANT ALL ON TABLE "alarm_cond" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE alarm_cond_id_seq TO i4capi;


create table "alarm_sub" (
    id SERIAL PRIMARY KEY,
    groups character varying (200)[] not null,
    "user" character varying (200) not null constraint fk_alarm_sub_user references "user",
    method character varying (200) not null,
    address text null,
    address_name character varying (200) null,
    status character varying (200) not null
);

GRANT ALL ON TABLE "alarm_sub" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE alarm_sub_id_seq TO i4capi;


create table "alarm_event" (
    id SERIAL PRIMARY KEY,
    alarm integer not null constraint fk_alarm references "alarm",
    created timestamp with time zone NOT NULL,
    summary character varying (200) not null,
    description text NULL
);

GRANT ALL ON TABLE "alarm_event" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE alarm_event_id_seq TO i4capi;


create table "alarm_recipient" (
    id SERIAL PRIMARY KEY,
    event integer not null constraint fk_event references "alarm_event",
    "user" character varying (200) null constraint fk_alarm_sub_user references "user",
    method character varying (200) not null,
    address text null,
    address_name character varying (200) null,
    status character varying (200) not null,
    fail_count integer not null default 0,
    backoff_until timestamp with time zone null
);

GRANT ALL ON TABLE "alarm_recipient" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE alarm_recipient_id_seq TO i4capi;


create table "stat" (
    id SERIAL PRIMARY KEY,
    name character varying (200) not null,
    "user" character varying (200) not null constraint fk_stat_timeseries_filter_user references "user",
    shared boolean NOT NULL default false,
    modified timestamp with time zone not NULL,
    customer VARCHAR(200) null
);

CREATE UNIQUE INDEX idx_name_user ON "stat" (name, "user");

GRANT ALL ON TABLE "stat" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE stat_id_seq TO i4capi;


create table "stat_visual_setting" (
    id integer not null constraint fk_pv references "stat" on delete cascade PRIMARY KEY,
    title character varying (200) null,
    subtitle character varying (200) null,
    xaxis_caption character varying (200) null,
    yaxis_caption character varying (200) null,
    legend_position character varying (200) null,
    legend_align character varying (200) null,
    tooltip_html text null
);

GRANT ALL ON TABLE "stat_visual_setting" TO i4capi;


create table "stat_timeseries" (
    id integer not null constraint fk_pv references "stat" on delete cascade PRIMARY KEY,
    after timestamp with time zone NULL,
    before timestamp with time zone NULL,
    duration interval null,
    metric_device character varying (200) not null,
    metric_data_id character varying (200) not null,
    agg_func character varying (200) null,
    agg_sep_device character varying (200) null,
    agg_sep_data_id character varying (200) null,
    series_name character varying (200) null,
    series_sep_device character varying (200) null,
    series_sep_data_id character varying (200) null,
    xaxis character varying (200) not null
);

GRANT ALL ON TABLE "stat_timeseries" TO i4capi;


create table "stat_timeseries_filter" (
    id SERIAL PRIMARY KEY,
    timeseries integer not null constraint fk_pv references "stat_timeseries" on delete cascade,
    device character varying (200) not null,
    data_id character varying (200) not null,
    rel character varying (200) not null,
    value character varying (200) not null,
    age_min double precision null,
    age_max double precision null
);

GRANT ALL ON TABLE "stat_timeseries_filter" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE stat_timeseries_filter_id_seq TO i4capi;


create table "stat_xy" (
    id integer not null constraint fk_pv references "stat" on delete cascade PRIMARY KEY,
    object_name character varying (200) not null,
    after timestamp with time zone NULL,
    before timestamp with time zone NULL,
    duration interval null,
    x_field character varying (200) not null,
    y_field character varying (200) null,
    shape character varying (200) null,
    color character varying (200) null
);

GRANT ALL ON TABLE "stat_xy" TO i4capi;


create table "stat_xy_object_params" (
    id SERIAL PRIMARY KEY,
    xy integer not null constraint fk_pv references "stat_xy" on delete cascade,
    key character varying (200) not null,
    value character varying (200) null
);

GRANT ALL ON TABLE "stat_xy_object_params" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE stat_xy_object_params_id_seq TO i4capi;


create table "stat_xy_other" (
    id SERIAL PRIMARY KEY,
    xy integer not null constraint fk_pv references "stat_xy" on delete cascade,
    field_name character varying (200) not null
);

GRANT ALL ON TABLE "stat_xy_other" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE stat_xy_other_id_seq TO i4capi;


create table "stat_xy_filter" (
    id SERIAL PRIMARY KEY,
    xy integer not null constraint fk_pv references "stat_xy" on delete cascade,
    field_name character varying (200) not null,
    rel character varying (200) not null,
    value character varying (200) not null
);

GRANT ALL ON TABLE "stat_xy_filter" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE stat_xy_filter_id_seq TO i4capi;


create table "stat_list" (
    id integer not null constraint fk_pv references "stat" on delete cascade PRIMARY KEY,
    object_name character varying (200) not null,
    after timestamp with time zone NULL,
    before timestamp with time zone NULL,
    duration interval null
);

GRANT ALL ON TABLE "stat_list" TO i4capi;


create table "stat_list_object_params" (
    id SERIAL PRIMARY KEY,
    list integer not null constraint fk_pv references "stat_list" on delete cascade,

    key character varying (200) not null,
    value character varying (200) null
);

GRANT ALL ON TABLE "stat_list_object_params" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE stat_list_object_params_id_seq TO i4capi;


create table "stat_list_order_by" (
    id SERIAL PRIMARY KEY,
    list integer not null constraint fk_pv references "stat_list" on delete cascade,
    field character varying (200) not null,
    ascending bool not null default true,
    sortorder integer not null
);

GRANT ALL ON TABLE "stat_list_order_by" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE stat_list_order_by_id_seq TO i4capi;


create table "stat_list_filter" (
    id SERIAL PRIMARY KEY,
    list integer not null constraint fk_pv references "stat_list" on delete cascade,
    field_name character varying (200) not null,
    rel character varying (200) not null,
    value character varying (200) not null
);

GRANT ALL ON TABLE "stat_list_filter" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE stat_list_filter_id_seq TO i4capi;


create table "stat_list_visual_setting" (
    id integer not null constraint fk_pv references "stat_list" on delete cascade PRIMARY KEY,
    title character varying (200) null,
    subtitle character varying (200) null,
    header_bg character varying (200) null,
    header_fg character varying (200) null,
    normal_bg character varying (200) null,
    normal_fg character varying (200) null,
    even_bg character varying (200) null,
    even_fg character varying (200) null
);

GRANT ALL ON TABLE "stat_list_visual_setting" TO i4capi;


create table "stat_list_visual_setting_col" (
    id SERIAL PRIMARY KEY,
    list integer not null constraint fk_pv references "stat_list" on delete cascade,
    field character varying (200) not null,
    caption character varying (200) null,
    width integer null,
    sortorder integer not null
);


GRANT ALL ON TABLE "stat_list_visual_setting_col" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE stat_list_visual_setting_col_id_seq TO i4capi;


create table "stat_capability" (
    id integer not null constraint fk_pv references "stat" on delete cascade PRIMARY KEY,
    after timestamp with time zone NULL,
    before timestamp with time zone NULL,
    duration interval null,
    metric_device character varying (200) not null,
    metric_data_id character varying (200) not null,
    nominal double precision null,
    utl double precision null,
    ltl double precision null,
    ucl double precision null,
    lcl double precision null
);

GRANT ALL ON TABLE "stat_capability" TO i4capi;


create table "stat_capability_filter" (
    id SERIAL PRIMARY KEY,
    capability integer not null constraint fk_pv references "stat_capability" on delete cascade,
    device character varying (200) not null,
    data_id character varying (200) not null,
    rel character varying (200) not null,
    value character varying (200) not null
);

GRANT ALL ON TABLE "stat_capability_filter" TO i4capi;
GRANT USAGE, SELECT ON SEQUENCE stat_capability_filter_id_seq TO i4capi;


create table "stat_capability_visual_setting" (
    id integer not null constraint fk_pv references "stat_capability" on delete cascade PRIMARY KEY,
    title character varying (200) null,
    subtitle character varying (200) null,
    plotdata boolean NOT NULL default false,
    infoboxloc character varying (200) null
);

GRANT ALL ON TABLE "stat_capability_visual_setting" TO i4capi;


create table "batch" (
    id character varying (200) not null primary key,
    customer character varying (200) null,
    project character varying (200) not null constraint fk_project references "projects",
    target_count int null,
    status character varying (200) not null
);

GRANT ALL ON TABLE "batch" TO i4capi;


create table "settings" (
    key character varying (200) not null primary key,
    value text null,
    "public" boolean NOT NULL default false
);

GRANT ALL ON TABLE "settings" TO i4capi;

insert into settings values ('push_email', 'i4c@technocar.hu', true);
insert into settings values ('push_priv_key', null, false);
insert into settings values ('push_public_key', null, true);

create table alarm_subsgroup_map (
  "user" varchar(200) not null CONSTRAINT fk_alarm_subsgroup_map__user REFERENCES "user" ("id"),
  "group" varchar(200) not null CONSTRAINT fk_alarm_subsgroup_map__alarm_subsgroup REFERENCES alarm_subsgroup ("group"),
  primary key ("user", "group")
);

GRANT ALL ON TABLE alarm_subsgroup_map TO i4capi;
