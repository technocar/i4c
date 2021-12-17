import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { Labels } from 'src/app/services/models/constants';
import { AlarmHelpers, AlarmPeriod } from '../helpers';

@Component({
  selector: 'app-period-selector',
  templateUrl: './period-selector.component.html',
  styleUrls: ['./period-selector.component.scss']
})
export class PeriodSelectorComponent implements OnInit {

  @Input()
    set seconds(value: number) {
      if (!value)
        return;
      this.period = AlarmHelpers.getPeriod(value);
      if (!this.period)
        this.period = this._default;
    };
  @Input()
    set unit(value: number) {
      if (!value)
        return;
      this.period = {
        value: value,
        type: 'unit',
        display: ""
      }
    }
  @Input() unitOption: boolean = false;

  @Output() secondsChange: EventEmitter<number> = new EventEmitter();
  @Output() unitChange: EventEmitter<number> = new EventEmitter();

  private _default: AlarmPeriod = {
    type: "s",
    value: 0,
    display: ""
  };

  period: AlarmPeriod;

  constructor() {
    this.period = this._default;
  }

  ngOnInit(): void {
  }

  getPeriods(): string[][] {
    var periods = Labels.periods.filter(p => p[0] !== "Y");
    if (this.unitOption)
      periods.push(["unit", $localize `:@@alarm_period_unit:darab`, $localize `:@@alarm_period_unit:darab`]);
    return periods;
  }

  periodChange() {
    if (this.period.type === 'unit') {
      this.secondsChange.emit(undefined);
      this.unitChange.emit(this.period.value);
    } else {
      this.secondsChange.emit(AlarmHelpers.getPeriodSeconds(this.period));
      this.unitChange.emit(undefined);
    }
  }
}
