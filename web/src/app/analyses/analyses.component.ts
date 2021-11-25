import { AfterViewInit, ChangeDetectorRef, Component, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { BehaviorSubject } from 'rxjs';
import { FilterControlComponent } from '../commons/filter/filter.component';
import { ApiService } from '../services/api.service';
import { AuthenticationService } from '../services/auth.service';
import { StatDef, StatDefBase } from '../services/models/api';

export interface AanalysisDef {
  getDef(): StatDefBase
}

enum AnalsysType { TimeSeries = 'timeseries', XY = 'xy' }

@Component({
  selector: 'app-analyses',
  templateUrl: './analyses.component.html',
  styleUrls: ['./analyses.component.scss']
})
export class AnalysesComponent implements OnInit, AfterViewInit {

  private _filterName: string;
  private _filterModified: string;
  private _filterShared: number;

  @ViewChild('filterNameCtrl') filterNameCtrl: FilterControlComponent;

  get filterName(): string { return this._filterName; }
  set filterName(value: string) { this._filterName = value; this.filter(); }
  filterType: string;
  get filterModified(): string { return this._filterModified; }
  set filterModified(value: string) { this._filterModified = new Date(value).toISOString(); this.filter(); }
  get filterShared(): number { return this._filterShared; }
  set filterShared(value: number) { this._filterShared = value; this.filter(); }

  fetching$: BehaviorSubject<boolean> = new BehaviorSubject(false);
  analysesOwn$: BehaviorSubject<StatDef[]> = new BehaviorSubject([]);
  analysesOthers$: BehaviorSubject<StatDef[]> = new BehaviorSubject([]);
  analysisTypes: string[][] = [
    [AnalsysType.TimeSeries, $localize `:@@analysis_type_timeseries:idősoros`],
    [AnalsysType.XY, $localize `:@@analysis_type_xy:XY`]
  ]

  constructor(
    private apiService: ApiService,
    private router: Router,
    private route: ActivatedRoute,
    private cd: ChangeDetectorRef,
    private authService: AuthenticationService
  ) {
    this._filterModified = route.snapshot.queryParamMap.get("fm");
    this._filterShared = parseInt(route.snapshot.queryParamMap.get("fs") ?? "-1");
    this.filterType = route.snapshot.queryParamMap.get("ft");
  }

  ngOnInit(): void {
  }

  ngAfterViewInit(): void {
    this.filterNameCtrl.queryParam = this.route.snapshot.queryParamMap.get("fn") ?? undefined;
    this.getAnalyses();
    this.cd.detectChanges();
  }

  getAnalyses() {
    this.fetching$.next(true);
    this.apiService.getStatDefs({
      name: !this.filterNameCtrl.mask ? this.filterName : undefined,
      name_mask: this.filterNameCtrl.mask ? this.filterName : undefined,
      type: this.filterType
    }).subscribe(r => {
      r = r ?? [];
      this.analysesOwn$.next(r.filter((i) => i.user?.id === this.authService.currentUserValue.id));
      this.analysesOthers$.next(r.filter((i) => i.user?.id !== this.authService.currentUserValue.id));
    }, (err) => {
    }, () => {
      this.fetching$.next(false);
    });
  }

  filter() {
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: {
        fm: this._filterModified,
        fn: this.filterNameCtrl.queryParam,
        ft: this.filterType,
        fs: this.filterShared
      },
      queryParamsHandling: 'merge'
    });
    this.getAnalyses();
  }

  getAnalaysisType(analysis: StatDef): AnalsysType {
    return analysis.timeseriesdef ? AnalsysType.TimeSeries : AnalsysType.XY;
  }

  getAnalsysTypeDesc(code: AnalsysType): string {
    var type = this.analysisTypes.find((t) => { return t[0] === code; });
    if (type)
      return type[1];
    else
      return code;
  }
}
