import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Alarm } from 'src/app/services/models/api';
import { Labels } from 'src/app/services/models/constants';
import { AlarmHelpers, AlarmPeriod } from '../helpers';


@Component({
  selector: 'app-detail',
  templateUrl: './detail.component.html',
  styleUrls: ['./detail.component.scss']
})
export class AlarmDetailComponent implements OnInit {

  def: Alarm;
  period: AlarmPeriod = {
    type: 's',
    value: 0,
    display: ''
  };

  constructor(
    private route: ActivatedRoute
  ) { }

  ngOnInit(): void {
    this.route.data.subscribe(r => {
      this.def = r.alarm as Alarm;
      var p = AlarmHelpers.getPeriod(this.def.max_freq);
      if (p)
        this.period = p;
    });
  }

  getPeriods(): string[][] {
    return Labels.periods.filter(p => p[0] !== "Y");
  }
}
