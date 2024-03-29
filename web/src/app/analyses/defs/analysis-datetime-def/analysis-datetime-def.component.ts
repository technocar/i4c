import { Component, Input, OnInit } from '@angular/core';
import { AuthenticationService } from 'src/app/services/auth.service';
import { StatDateTimeDef } from 'src/app/services/models/api';
import { AnalysisDef } from '../../analyses.component';

@Component({
  selector: 'app-analysis-datetime-def',
  templateUrl: './analysis-datetime-def.component.html',
  styleUrls: ['./analysis-datetime-def.component.scss']
})
export class AnalysisDatetimeDefComponent implements OnInit, AnalysisDef {

  private _timestamp: string;

  @Input('def') def: StatDateTimeDef;
  @Input("canUpdate") canUpdate: boolean;

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

  constructor(private authService: AuthenticationService) {
    this.timestamp = (new Date()).toISOString();
    this.direction = -1;
    this.count = 1;
    this.period = "M";
  }

  ngOnInit(): void {
    if (this.def) {
      this.direction = this.def.after ? 1 : -1;
      this.timestamp = this.def.after ?? this.def.before ?? this.timestamp;
      if (this.def.duration && this.def.duration.length > 2) {
        let p = "";
        for (let i = 1; i < this.def.duration.length - 1; i++)
          p += this.def.duration[i];

        if (!isNaN(parseInt(p)))
          this.count = parseInt(p);

        if (['Y', 'M', 'd', 'H'].indexOf(this.def.duration[this.def.duration.length - 1]) > -1)
          this.period = this.def.duration[this.def.duration.length - 1];
      }
    }
  }

  getDef(): StatDateTimeDef {
    return {
      after: this.direction === 1 ? this._timestamp : undefined,
      before: this.direction !== 1 ? this._timestamp : undefined,
      duration: `P${this.count}${this.period}`
    };
  }
}
