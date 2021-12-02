import { DeviceType } from "./constants";

export interface ErrorDetail {
  loc: string[],
  msg: string,
  type: string
}

export interface SnapshotResponse {
  mill: Snapshot,
  lathe: Snapshot,
  gom: Snapshot,
  robot: Snapshot
}

export interface Snapshot {
  status: DeviceStatus,
  event_log: EventLog[],
  conditions: Condition[]
}

export interface DeviceStatus {
  status: Status,
  program: Program,
  subprogram: Program,
  unit: NumberValue,
  sequence: NumberValue,
  tool: NumberValue,
  door: Door,
  lin_axes: Axis[],
  rot_axes: Axis[]
}

export interface Device {
  id: DeviceType,
  name: string
}

export interface Status {
  value: string,
  since: number
}

export interface Program {
  name: string,
  comment: string,
  since: number
}

export interface Door {
  status: string,
  since: number
}

export interface NumberValue {
  num: number,
  since: number
}

export interface Axis {
  name: string,
  mode: string,
  pos: number,
  load: number,
  rate: number
}

export interface EventLog {
  data_id: string,
  name: string,
  timestamp: number,
  value: string
}

export enum ConditionSeverity { Warning = "warning", Fault = "fault" }

export interface Condition {
  severity: ConditionSeverity,
  data_id: string,
  message: string,
  since: number
}

export interface ListItem {
  device: string,
  timestamp: string,
  sequence: number,
  instance: string,
  data_id: string,
  name: string,
  value: string,
  unit: string,
  category: string
}

export enum Category { Condition = "CONDITION", Event = "EVENT", Sample = "SAMPLE" }

export interface FindParams {
  device: DeviceType,
  beforeCount?: number,
  afterCount?: number,
  category?: string,
  name?: string,
  value?: string | string[],
  extra?: string,
  relation?: string,
  sequence?: number,
  timestamp?: Date
}

export interface Meta {
  device: DeviceType,
  data_id: string,
  name?: string,
  nice_name?: string,
  system1?: string,
  system2?: string,
  category?: Category,
  type?: string,
  subtype?: string,
  unit?: string
}

export interface FindResponse {
  timestamp: string
}

export interface EventValues {
  data_id: string,
  values: string[]
}

export interface User {
  id: string,
  name: string,
  login_name: string,
  pub_key?: string,
  roles?: string[],
  status?: string,
  roles_eff?: string[]
}

export interface Extra {
  key: string,
  value: string
}

export interface Note {
  note_id?: number,
  user: string,
  timestamp: Date,
  text: string,
  deleted?: boolean
}

export interface UpdateResult {
  changed: boolean
}

export enum ProjectStatus { Edit = "edit", Final = "final", Deleted = "deleted", Archive = "archive" }
export interface Project {
  name: string,
  status: string,
  versions: string[],
  extra: Extra[]
}

export enum ProjectInstallStatus { Todo = "todo", Working = "working", Done = "done", Fail = "fail" }
export interface ProjectInstall {
  id: number,
  ts: string,
  project: string,
  invoked_version: string,
  real_version: number,
  status: ProjectInstallStatus,
  status_msg: string,
  files: string[]
}

export interface ProjectInstallParams {
  id?: number,
  status?: ProjectInstallStatus,
  after?: Date,
  before?: Date,
  project_name?: string,
  ver?: number
}

export interface WorkPieceNote {
  note_id: number,
  user: string,
  timestamp: string,
  text: string,
  deleted: boolean
}

export interface WorkPieceLog {
  ts: string,
  seq: number,
  data: string,
  text: string
}

export interface WorkPieceFile {
  download_name: string
}

export enum WorkPieceStatus { Good = "good", Bad = "bad", Inprogress = "inprogress", Unknown = "unknown" }

export interface WorkPiece {
  id: string,
  project: string,
  batch: string,
  status: WorkPieceStatus,
  notes: WorkPieceNote[],
  log: WorkPieceLog[],
  files: WorkPieceFile[],
  begin_timestamp: string,
  end_timestamp: string
}

export interface WorkPieceParams {
  before?: Date,
  after?: Date,
  id?: string,
  project?: string,
  project_mask?: string,
  batch?: string,
  batch_mask?: string,
  status?: WorkPieceStatus,
  note_user?: string,
  note_text?: string,
  note_before?: string,
  note_after?: string,
  with_details?: boolean,
  with_deleted?: boolean
}

export interface WorkPieceUpdateCondition {
  flipped: boolean,
  batch?: string,
  empty_batch?: boolean,
  status?: WorkPieceStatus[]
}

export interface WorkPieceUpdateChange {
  batch?: string,
  delete_batch?: boolean,
  status?: WorkPieceStatus,
  add_note?: Note[],
  delete_note?: number[]
}

export interface WorkPieceUpdate {
  conditions: WorkPieceUpdateCondition[],
  change: WorkPieceUpdateChange
}

export enum WorkPieceBatchItemType { Batch = 0, Delete = 1 }
export interface WorkPieceBatch {
  batch: string,
  last: string,
  itemType: number
}

export interface WorkPeiceBatchParams {
  project?: string,
  after?: Date
}

export enum ToolDataId { Install = "install_tool", Remove = "remove_tool" }

export interface Tool {
  timestamp?: string,
  sequence?: number,
  device?: DeviceType,
  data_id?: ToolDataId,
  tool_id?: string,
  slot_number?: string,
  type?: string
}

export interface ToolUsage {
  tool_id: string,
  type: string,
  count: number
}

export interface ToolListParams {
  device: DeviceType,
  timestamp?: Date,
  sequence?: number,
  max_count?: number
}

export interface StatDefParams {
  id?: string,
  user?: string,
  name?: string,
  name_mask?: string,
  type?: string
}

export interface StatDef {
  id: number,
  name: string,
  user: User,
  shared: boolean,
  modified: string,
  timeseriesdef: StatTimeSeriesDef,
  xydef: StatXYDef
}

export interface StatDefBase {
}

export interface StatDateTimeDef extends StatDefBase {
  after: string,
  before: string,
  duration: string
}

export enum StatTimeSeriesAggFunc { Avg = 'avg', Median = 'median', FirstQuartile = 'q1th', FourQuartile = 'q4th', Min = 'min', Max = 'max' }
export enum StatTimeSeriesName { SeparatorEvent = 'seperator_event', Sequence = 'sequence', Timestamp = 'timestamp' }

export interface StatTimeSeriesDef extends StatDateTimeDef {
  filter: StatTimesSeriesFilter[],
  metric: Meta,
  agg_func: StatTimeSeriesAggFunc,
  agg_sep: Meta,
  series_sep: Meta,
  series_name: StatTimeSeriesName,
  xaxis: string | number,
  visualsettings: StatVisualSettings
}

export interface StatTimesSeriesFilter {
  id: number,
  device: DeviceType,
  data_id: string,
  rel: string,
  value: any,
  age_min: number,
  age_max: number
}

export interface StatVisualSettingsAxis {
  caption: string
}

export enum StatVisualSettingsLegendPosition { Top = 'top', Bottom = 'bottom', Left = 'left', Right = 'right', ChartArea = 'chartArea' }
export enum StatVisualSettingsLegendAlign { Start = 'start', Center = 'center', End = 'end' }

export interface StatVisualSettingsLegend {
  position: StatVisualSettingsLegendPosition,
  align: StatVisualSettingsLegendAlign
}

export interface StatVisualSettings {
  title: string,
  subtitle: string,
  xaxis: StatVisualSettingsAxis,
  yaxis: StatVisualSettingsAxis,
  legend: StatVisualSettingsLegend
}

export interface StatDefUpdateConditions {
  flipped?: boolean,
  shared?: boolean
}

export interface StatDefUpdate {
  conditions: StatDefUpdateConditions[],
  change: StatDef
}

export interface StatDataTimeSeries {
  name: string,
  x_timestamp: string[],
  x_relative: number[],
  y: number[]
}

export interface StatData {
  stat_def: StatDef,
  timeseriesdata: StatDataTimeSeries[]
}

export interface StatXYMeta {
  objects: StatXYMetaObject[]
}

export interface StatXYMetaObject {
  name: string,
  displayname: string,
  fields: StatXYMetaObjectField[],
  params: StatXYMetaObjectParam[]
}

export enum StatMetaObjectFieldType { Numeric = 'numeric', Catgeory = 'category', Label = 'label' }

export interface StatXYMetaObjectField {
  name: string,
  displayname: string,
  type: StatXYMetaObjectField,
  value_list: string[]
}

export interface StatXYMetaObjectParam {
  name: string,
  type: number,
  label: string
}

export interface StatXYDef extends StatDateTimeDef {
  obj: StatXYObject,
  x: StatXYField,
  y: StatXYField,
  shape: StatXYField,
  color: StatXYField,
  other: StatXYOther[],
  filter: StatXYFilter[],
  visualsettings: StatVisualSettings
}

export enum StatXYObjectType { Workpiece = 'workpiece', MazakProgram = 'mazakprogram', Batch = 'batch', Tool = 'tool' }
export interface StatXYObject {
  type: StatXYObjectType ,
  params: StatXYParam[]
}

export interface StatXYField {
  field_name: string
}

export interface StatXYOther {
  field_name: string,
  id: number
}

export interface StatXYFilter {
  id: number,
  field: StatXYField
  rel: StatXYFilterRel,
  value: string
}

export enum StatXYFilterRel { Equal = '=', NotEqual = '!=', Lesser = '<', LesserEqual = '<=', Greater = '>', GreaterEqual = '>=' }

export interface StatXYParam {
  id: number,
  key: string,
  value: string
}
