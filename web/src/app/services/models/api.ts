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
  name: string,
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
  data_id?: string,
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
  unit?: string,
  value_list?: string[]
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
  roles_eff?: string[],
  privs?: UserPrivilige[]
}

export interface UserPrivilige {
  endpoint: string,
  features: string[]
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
  xydef: StatXYDef,
  listdef: StatListDef,
  capabilitydef: StatCapabilityDef
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
  visualsettings: StatVisualSettingsChart
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

export interface StatVisualSettingsChartAxis {
  caption: string
}

export enum StatVisualSettingsChartLegendPosition { Top = 'top', Bottom = 'bottom', Left = 'left', Right = 'right', ChartArea = 'chartArea' }
export enum StatVisualSettingsChartLegendAlign { Start = 'start', Center = 'center', End = 'end' }

export interface StatVisualSettingsChartLegend {
  position: StatVisualSettingsChartLegendPosition,
  align: StatVisualSettingsChartLegendAlign
}

export interface StatVisualSettingsChartTooltip {
  html: string
}

export interface StatVisualSettingsChart extends StatVisualSettings  {
  xaxis: StatVisualSettingsChartAxis,
  yaxis: StatVisualSettingsChartAxis,
  legend: StatVisualSettingsChartLegend,
  tooltip: StatVisualSettingsChartTooltip
}

export interface StatVisualSettings {
  title: string,
  subtitle: string
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

export interface StatDataXY {
  x: number | string,
  y: number | string,
  shape: string | number,
  color: string | number,
  others: any[]
}

export interface StatData {
  stat_def: StatDef,
  timeseriesdata: StatDataTimeSeries[],
  xydata: StatDataXY[],
  listdata: any[],
  capabilitydata: StatCapabilityData
}

export interface StatXYMeta {
  name: string,
  displayname: string,
  fields: StatXYMetaObjectField[],
  params: StatXYMetaObjectParam[]
}

export enum StatMetaObjectFieldType { Numeric = 'numeric', Catgeory = 'category', Label = 'label' }

export interface StatXYMetaObjectField {
  name: string,
  displayname: string,
  type: StatMetaObjectFieldType,
  value_list: string[],
  unit: StatXYMetaObjectFieldUnit
}

export enum StatXYMetaObjectFieldUnit { Percent = 'percent', Second = 'second' }

export enum StatXYMetaObjectParamType { Integer = 'int', Float = 'float', String = 'str', Datetime = 'datetime' }

export interface StatXYMetaObjectParam {
  name: string,
  type: StatXYMetaObjectParamType,
  label: string
}

export interface StatXYDef extends StatDateTimeDef {
  obj: StatXYObject,
  x: string,
  y: string,
  shape: string,
  color: string,
  other: string[],
  filter: StatXYFilter[],
  visualsettings: StatVisualSettingsChart
}

export enum StatXYObjectType { Workpiece = 'workpiece', MazakProgram = 'mazakprogram', MazakSubProgram = 'mazaksubprogram', Batch = 'batch', Tool = 'tool' }
export interface StatXYObject {
  type: StatXYObjectType,
  params: StatXYParam[]
}

export interface StatXYOther {
  field_name: string,
  id: number
}

export interface StatXYFilter {
  id: number,
  field: string
  rel: NumberRelation,
  value: string
}

export enum NumberRelation { Equal = '=', NotEqual = '!=', Lesser = '<', LesserEqual = '<=', Greater = '>', GreaterEqual = '>=' }
export enum StringRelation { Equal = '=', NotEqual = '!=', Contains = '*', NotContains = '!*' }

export interface StatXYParam {
  id: number,
  key: string,
  value: string
}

export interface StatListDef extends StatDateTimeDef {
  obj: StatXYObject,
  order_by: StatListOrderBy[],
  filter: StatXYFilter[],
  visualsettings: StatListVisualSettings
}

export interface StatListOrderBy {
  field: string,
  ascending: boolean
}

export interface StatListVisualSettings extends StatVisualSettings {
  header_bg: string,
  header_fg: string,
  normal_bg: string,
  normal_fg: string,
  even_bg: string,
  even_fg: string,
  cols: StatListVisualSettingsCol[]
}

export interface StatListVisualSettingsCol {
  field: string,
  caption: string,
  width: number
}

export interface StatCapabilityDef extends StatDateTimeDef {
  filter: StatCapabilityFilter[],
  metric: StatCapabilityDefMetric,
  nominal: number,
  utl: number,
  ltl: number,
  ucl: number,
  lcl: number,
  visualsettings: StatCapabilityDefVisualSettings
}


export interface StatCapabilityFilter {
  id: number,
  device: DeviceType,
  data_id: string,
  rel: string,
  value: any
}

export enum StatCapabilityDefVisualSettingsInfoBoxLocation { None = 'none', Left = 'left', Right = 'right', Bottom = 'bottom', Top = 'top' }
export interface StatCapabilityDefVisualSettings extends StatVisualSettings {
  plotdata: boolean,
  infoboxloc: StatCapabilityDefVisualSettingsInfoBoxLocation
}

export interface StatCapabilityDefMetric {
  device: string,
  data_id: string
}

export interface StatCapabilityData {
  points: number[],
  mean: number,
  sigma: number,
  c: number,
  ck: number
}

export interface Alarm {
  conditions: AlarmRule[],
  max_freq: number,
  window: number,
  subsgroup: string,
  id: number,
  name: string,
  last_check: string,
  last_report: string,
  subs: AlarmSubscription[]
}

export interface AlarmGroup {
  name: string,
  users: string[]
}

export interface AlarmRule {
  sample: AlarmRuleSample,
  event: AlarmRuleEvent,
  condition: AlarmRuleCondition
}

export interface AlarmRuleBase {
  device: DeviceType,
  data_id: string
}

export enum AlarmRuleSampleAggMethod { Avg = 'avg', Median = 'median', Q1th = 'q1th', Q4th = 'q4th', Slope = 'slope' }
export interface AlarmRuleSample extends AlarmRuleBase {
  aggregate_period?: number,
  aggregate_count?: number,
  aggregate_method?: AlarmRuleSampleAggMethod,
  rel: NumberRelation,
  value?: number
}

export interface AlarmRuleEvent extends AlarmRuleBase {
  rel: StringRelation,
  value?: string,
  age_min?: number,
  age_max?: number
}

export interface AlarmRuleCondition extends AlarmRuleBase {
  value?: string,
  age_min?: number
}

export enum AlarmNotificationType { Email = 'email', Push = 'push', None = 'none' }
export enum StatusType { Active = 'active', Inactive = 'inactive' }
export interface AlarmSubscription {
  groups: string[],
  user: string,
  method: AlarmNotificationType,
  address: string,
  address_name: string,
  status: StatusType,
  id: number,
  user_name: string
}

export interface AlarmRequestParams {
  name_mask?: string,
  report_after?: Date,
  subs_status?: StatusType,
  subs_method?: AlarmNotificationType,
  subs_address?: string,
  subs_address_mask?: string,
  subs_user?: string,
  subs_user_mask?: string
}

export interface AlarmSubscriptionGroupGrant {
  user: User,
  groups: string[]
}

export interface AlarmSubscriptionRequestParams {
  id: string,
  group: string,
  group_mask: string,
  user: string,
  user_name: string,
  user_name_mask: string,
  method: AlarmNotificationType,
  status: StatusType,
  address: string,
  address_mask: string,
  alarm: string
}

export interface AlarmSubscriptionChange {
  status: StatusType,
  address: string,
  clear_address: boolean,
  address_name: string,
  clear_address_name: boolean,
  add_groups?: string[],
  set_groups: string[],
  remove_groups?: string[]
}

export interface AlarmSubscriptionUpdate {
  conditions: any[],
  change: AlarmSubscriptionChange
}
