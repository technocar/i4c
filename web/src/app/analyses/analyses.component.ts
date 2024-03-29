import { AfterViewInit, ChangeDetectorRef, Component, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ChartConfiguration } from 'chart.js';
import { BehaviorSubject } from 'rxjs';
import { FilterControlComponent } from '../commons/filter/filter.component';
import { ApiService } from '../services/api.service';
import { AuthenticationService } from '../services/auth.service';
import { StatData, StatDef, StatDefBase } from '../services/models/api';
import { AnalysisService, AnalysisType } from './analysis/analysis.service';

export interface AnalysisDef {
  getDef(): StatDefBase
}

export interface AnalysisChart {
  canUpdate: boolean;
  getChartConfiguration(data: StatData): ChartConfiguration;
}

@Component({
  selector: 'app-analyses',
  templateUrl: './analyses.component.html',
  styleUrls: ['./analyses.component.scss']
})
export class AnalysesComponent implements OnInit, AfterViewInit {
  private _filterName: string;
  private _filterModified: string;
  private _filterShared: number;
  private _filterType: string;

  @ViewChild('filterNameCtrl') filterNameCtrl: FilterControlComponent;

  get filterName(): string { return this._filterName; }
  set filterName(value: string) { this._filterName = value; this.filter(); }
  get filterType(): string { return this._filterType; }
  set filterType(value: string) { this._filterType = value; this.filter(); }
  get filterModified(): string { return this._filterModified; }
  set filterModified(value: string) { this._filterModified = new Date(value).toISOString(); this.filter(); }
  get filterShared(): number { return this._filterShared; }
  set filterShared(value: number) { this._filterShared = value; this.filter(); }

  fetching$: BehaviorSubject<boolean> = new BehaviorSubject(false);
  analysesOwn$: BehaviorSubject<StatDef[]> = new BehaviorSubject([]);
  analysesOthers$: BehaviorSubject<StatDef[]> = new BehaviorSubject([]);
  analysisTypes;

  access = {
    canCreate: false,
    canRun: false
  }

  constructor(
    private apiService: ApiService,
    private router: Router,
    private route: ActivatedRoute,
    private cd: ChangeDetectorRef,
    private authService: AuthenticationService,
    public  analysis: AnalysisService

  ) {
    this.access.canCreate = authService.hasPrivilige("post/stat/def");
    this.access.canRun = authService.hasPrivilige("get/stat/def/{id}");
    this._filterModified = route.snapshot.queryParamMap.get("fm");
    this._filterShared = parseInt(route.snapshot.queryParamMap.get("fs") ?? "-1");
    this._filterType = route.snapshot.queryParamMap.get("ft");
    this.analysisTypes = analysis.analysisTypes;
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
      type: (this.filterType ?? "") === "" ? undefined : this.getApiAnalysisType(this.filterType as AnalysisType)
    }).subscribe(r => {
      r = r ?? [];
      this.analysesOwn$.next(r.filter((i) => i.user?.id == this.authService.currentUserValue.id));
      this.analysesOthers$.next(r.filter((i) => i.user?.id != this.authService.currentUserValue.id));
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
        ft: (this.filterType ?? "") === "" ? undefined : this.filterType,
        fs: this.filterShared
      },
      queryParamsHandling: 'merge'
    });
    this.getAnalyses();
  }



  getApiAnalysisType(type: AnalysisType): string {
    switch (type) {
      case "0":
        return "timeseries";
      case "1":
        return "xy";
      case "2":
        return "list";
      case "3":
        return "capability";
      default:
        return undefined;
    }
  }
}
