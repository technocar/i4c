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
  name: string,
  nice_name: string,
  system1: string,
  system2: string,
  category: Category,
  type: string,
  subtype: string,
  unit: string
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
  pub_key: string,
  roles: string[],
  status: string,
  roles_eff: string[]
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
