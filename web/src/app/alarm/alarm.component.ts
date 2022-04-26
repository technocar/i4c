import { AfterViewInit, ChangeDetectorRef, Component, OnInit, ViewChild } from '@angular/core';
import { Router } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { BehaviorSubject } from 'rxjs';
import { FilterControlComponent } from '../commons/filter/filter.component';
import { ApiService } from '../services/api.service';
import { FiltersService } from '../services/filters.service';
import { Alarm } from '../services/models/api';
import { AlarmHelpers } from './helpers';

interface Filters {
  name: string,
  last_check: string,
  last_report: string
}

interface NewAlarm {
  name: string;
  submitted: boolean;
  sameNameError: boolean;
  error: boolean;

}

@Component({
  selector: 'app-alarm',
  templateUrl: './alarm.component.html',
  styleUrls: ['./alarm.component.scss']
})
export class AlarmComponent implements OnInit, AfterViewInit {

  @ViewChild('filterNameCtrl') filterNameCtrl: FilterControlComponent;
  @ViewChild("new_alarm_dialog") newAlarmDialog;

  listFetching$: BehaviorSubject<boolean> = new BehaviorSubject(false);
  alarms$: BehaviorSubject<Alarm[]> = new BehaviorSubject([]);
  filters: Filters = {
    name: undefined,
    last_check: undefined,
    last_report: undefined
  };

  newAlarm: NewAlarm = {
    name: "",
    sameNameError: false,
    submitted: false,
    error: false
  }

  constructor(
    private apiService: ApiService,
    private filterService: FiltersService,
    private cd: ChangeDetectorRef,
    private router: Router
  ) {
    filterService.read("alarm", this.filters);
  }

  ngAfterViewInit(): void {
    this.filterNameCtrl.queryParam = this.filters.name;
    this.getAlarms();
    this.cd.detectChanges();
  }

  ngOnInit(): void {
  }

  getAlarms() {
    this.listFetching$.next(true);
    this.apiService.getAlarms({
      name_mask: (this.filters.name ?? "") === "" ? undefined : this.filters.name,
      report_after: (this.filters.last_report ?? "") === "" ? undefined : new Date(this.filters.last_report)
    })
      .subscribe(r => {
        this.alarms$.next(r);
      }, err => {

      }, () => {
        this.listFetching$.next(false);
      });
  }

  filter(name?: string, value?: any) {
    switch (name) {
      case "last_check":
      case "last_report":
        this.filters[name] = (value ?? "") === "" ? undefined : (new Date(value)).toISOString();
        break;
      default:
        this.filters.name = this.filterNameCtrl.queryParam;
        break;
    }
    this.filterService.save("alarm", this.filters);
    this.getAlarms();
  }

  getMaxFreqDesc(alarm: Alarm): string {
    return AlarmHelpers.getPeriod(alarm.max_freq)?.display;
  }

  createAlarm() {
    this.newAlarm.submitted = true;
    if ((this.newAlarm.name ?? "") === "")
      return;

    this.apiService.getAlarms({
      name_mask: this.newAlarm.name
    }).subscribe(r => {
      if (r.length > 0)
        this.newAlarm.sameNameError = true;
      else
        this.apiService.getAlarmGroups().subscribe(groups => {
          this.apiService.setAlarm(this.newAlarm.name, {
            conditions: [],
            max_freq: 0,
            window: 0,
            subsgroup: groups.length > 0 ? groups.map(g => g.name)[0] : null,
            id: undefined,
            last_check: undefined,
            last_report: undefined,
            name: undefined,
            subs: undefined
          }).subscribe(r => {
            this.router.navigate([r.name]);
          }, (err) => {
            this.newAlarm.error = true;
          })
        })
    })
  }
}
