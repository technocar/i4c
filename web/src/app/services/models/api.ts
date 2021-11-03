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
