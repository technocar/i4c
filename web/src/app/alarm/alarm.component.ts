import { AfterViewInit, ChangeDetectorRef, Component, OnInit, ViewChild } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { FilterControlComponent } from '../commons/filter/filter.component';
import { ApiService } from '../services/api.service';
import { FiltersService } from '../services/filters.service';
import { Alarm, AlarmRule } from '../services/models/api';
import { Labels } from '../services/models/constants';
import { AlarmHelpers } from './helpers';

interface Filters {
  name: string,
  last_check: string,
  last_report: string
}

@Component({
  selector: 'app-alarm',
  templateUrl: './alarm.component.html',
  styleUrls: ['./alarm.component.scss']
})
export class AlarmComponent implements OnInit, AfterViewInit {

  @ViewChild('filterNameCtrl') filterNameCtrl: FilterControlComponent;

  listFetching$: BehaviorSubject<boolean> = new BehaviorSubject(false);
  alarms$: BehaviorSubject<Alarm[]> = new BehaviorSubject([]);
  filters: Filters = {
    name: undefined,
    last_check: undefined,
    last_report: undefined
  };

  constructor(
    private apiService: ApiService,
    private filterService: FiltersService,
    private cd: ChangeDetectorRef,
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
}
