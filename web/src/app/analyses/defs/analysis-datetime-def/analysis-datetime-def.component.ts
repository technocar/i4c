import { Component, OnInit } from '@angular/core';
import { StatDateTimeDef } from 'src/app/services/models/api';
import { AanalysisDef } from '../../analyses.component';

@Component({
  selector: 'app-analysis-datetime-def',
  templateUrl: './analysis-datetime-def.component.html',
  styleUrls: ['./analysis-datetime-def.component.scss']
})
export class AnalysisDatetimeDefComponent implements OnInit, AanalysisDef {

  private _timestamp: string;

  get timestamp(): string { return this._timestamp; }
  set timestamp(value: string) { this._timestamp = (new Date(value)).toISOString(); }
  direction: number;
  count: number;
  periods: string[][] = [
    ['H', $localize `:@@datetime_hour:óra`],
    ['D', $localize `:@@datetime_day:nap`],
    ['M', $localize `:@@datetime_month:hónap`],
    ['Y', $localize `:@@datetime_year:év`]
  ];
  period: string;

  constructor() {
    this.timestamp = (new Date()).toISOString();
    this.direction = -1;
    this.count = 1;
    this.period = "M";
  }

  ngOnInit(): void {
  }

  getDef(): StatDateTimeDef {
    return {
      after: this.direction === 1 ? this._timestamp : undefined,
      before: this.direction !== 1 ? this._timestamp : undefined,
      duration: `P${this.count}${this.period}`
    };
  }
}
