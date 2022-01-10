import { AfterViewInit, ChangeDetectorRef, Component, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ChartConfiguration } from 'chart.js';
import { BehaviorSubject } from 'rxjs';
import { FilterControlComponent } from '../commons/filter/filter.component';
import { ApiService } from '../services/api.service';
import { AuthenticationService } from '../services/auth.service';
import { StatData, StatDef, StatDefBase } from '../services/models/api';
import * as XLSX from 'xlsx-with-styles';

export interface AnalysisDef {
  getDef(): StatDefBase
}

export interface AnalysisChart {
  getChartConfiguration(data: StatData): ChartConfiguration
}

export enum AnalysisType { TimeSeries = '0', XY = '1', List = '2' }

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
    [AnalysisType.TimeSeries, $localize `:@@analysis_type_timeseries:idősoros`],
    [AnalysisType.XY, $localize `:@@analysis_type_xy:XY`],
    [AnalysisType.List, $localize `:@@analysis_type_list:Lista`]
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
      type: (this.filterType ?? "") === "" ? undefined : this.filterType
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

  getAnalaysisType(analysis: StatDef): AnalysisType {
    return analysis.timeseriesdef ? AnalysisType.TimeSeries : analysis.xydef ? AnalysisType.XY : AnalysisType.List;
  }

  getAnalsysTypeDesc(code: AnalysisType): string {
    var type = this.analysisTypes.find((t) => { return t[0] === code; });
    if (type)
      return type[1];
    else
      return code;
  }

  exportexcel() {
      /* table id is passed over here */
      let element = document.getElementById('analyses');
      const ws: XLSX.WorkSheet = XLSX.utils.table_to_sheet(element);
      (ws["A3"] as XLSX.CellObject).s = {
        fill: {
          patternType: "solid",
          bgColor: { rgb: "007BFF" }
        }
      }
      /* generate workbook and add the worksheet */
      const wb: XLSX.WorkBook = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');

      /* save to file */
      XLSX.writeFile(wb, "test.xlsx");

  }
}
