import { DatePipe } from '@angular/common';
import { Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { Chart, ChartConfiguration, FontSpec, Legend, registerables, TitleOptions  } from 'chart.js';
import 'chartjs-adapter-date-fns';
import { _DeepPartialObject } from 'chart.js/types/utils';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiService } from 'src/app/services/api.service';
import { AuthenticationService } from 'src/app/services/auth.service';
import { Meta, StatData, StatDef, StatTimeSeriesDef } from 'src/app/services/models/api';
import { AnalysisType } from '../analyses.component';
import { AnalysisTimeseriesDefComponent } from '../defs/analysis-timeseries-def/analysis-timeseries-def.component';
import { AnalysisXyDefComponent } from '../defs/analysis-xy-def/analysis-xy-def.component';

Chart.register(...registerables);

@Component({
  selector: 'app-analysis',
  templateUrl: './analysis.component.html',
  styleUrls: ['./analysis.component.scss']
})
export class AnalysisComponent implements OnInit {

  private _chartInstance: Chart;

  metaList: Meta[] = [];
  def: StatDef;
  origDef: StatDef;
  analysisType: AnalysisType;
  chartLoading$: BehaviorSubject<boolean> = new BehaviorSubject(false);
  chartError: boolean = false;
  chartErrorMsg: string = "";

  @ViewChild('timeseries_def') timeseriesDef: AnalysisTimeseriesDefComponent;
  @ViewChild('xy_def') xyDef: AnalysisXyDefComponent;
  @ViewChild('new_dialog') newDialog;
  @ViewChild('chart', {static: false}) chart: ElementRef;

  constructor(
    private route: ActivatedRoute,
    private authService: AuthenticationService,
    private modalService: NgbModal,
    private apiService: ApiService,
    private router: Router
  ) {
    this.analysisType = (route.snapshot.paramMap.get("type") ?? "0") as AnalysisType;
  }

  ngOnInit(): void {
    this.route.data.subscribe(r => {
      this.metaList = r.data[1];
      this.def = r.data[0];
      this.processDef();
      if (this.def)
        this.origDef = JSON.parse(JSON.stringify(this.def));
    });
  }

  processDef() {
    if (this.def.id === -1) {
      this.def.user = {
        id: this.authService.currentUserValue.id,
        login_name: this.authService.currentUserValue.username,
        name: this.authService.currentUserValue.username
      };
    } else {
      this.analysisType = this.def.timeseriesdef ? AnalysisType.TimeSeries : AnalysisType.XY;
    }
  }

  isNew(): boolean {
    return (this.def?.id ?? -1) === -1;
  }

  isOwn(): boolean {
    return this.def.user?.id == this.authService.currentUserValue.id;
  }

  hasChanges(): boolean {
    if (this.isNew())
      return true;
    return (JSON.stringify(this.origDef ?? {}) !== JSON.stringify(this.def ?? {}));
  }

  buildDef() {
    switch (this.analysisType) {
      case AnalysisType.TimeSeries:
        this.def.timeseriesdef = this.timeseriesDef.getDef() as StatTimeSeriesDef;
        break;
      case AnalysisType.XY:
        this.def.xydef = this.xyDef.getDef();
        break;
    }
  }

  getChart() {
    this.buildDef();
    if (this.hasChanges()) {
      this.def.modified = (new Date()).toISOString();
    }
    var saving: Observable<boolean>;
    if (this.isNew())
      saving = this.askForName();
    else
      saving = this.save();

    saving.subscribe(r => {
      if (r)
        this.getData();
    }, (err) => {
      this.showChartError(this.apiService.getErrorMsg(err).toString());
    });
  }

  getData() {
    this.chartError = false;
    this.chartErrorMsg = "";

    if (this._chartInstance)
      this._chartInstance.destroy();

    this.chartLoading$.next(true);
    this.apiService.getStatData(this.def.id)
      .subscribe(r => {
        this.buildChart(r);
      }, (err) => {
        this.showChartError(this.apiService.getErrorMsg(err).toString());
      }, () => {
        this.chartLoading$.next(false);
      });
  }

  buildChart(result: StatData) {
    if (!result) {
      this.showChartError($localize `:@@chart_no_data:Nincs megjeleníthető adat!`);
      return;
    }

    try {
      let ctx = this.chart.nativeElement.getContext('2d');
      let options: ChartConfiguration;
      if (result.timeseriesdata)
        options = this.buildTimeSeriesChart(result);
      else
        options = this.buildXYChart(result);

      this._chartInstance = new Chart(ctx, options);
    }
    catch(err) {
      this.showChartError(err);
    }
  }

  buildXYChart(result: StatData): ChartConfiguration {

    if (!result?.xydata || result.xydata.length === 0)
      throw ($localize `:@@chart_no_data:Nincs megjeleníthető adat!`);

    return this.xyDef.getChartConfiguration(result);

  }
  buildTimeSeriesChart(result: StatData): ChartConfiguration {
    if (!result?.timeseriesdata || result.timeseriesdata.length === 0)
      throw ($localize `:@@chart_no_data:Nincs megjeleníthető adat!`);

    return this.timeseriesDef.getChartConfiguration(result);
  }

  save(): Observable<boolean> {
    if (!this.isOwn())
      return of(true);

    if (this.isNew())
      return this.apiService.addNewStatDef(this.def)
        .pipe(
          tap(r => {
            this.def.id = r.id;
          }),
          map(r => { return r?.id > 0 ? true : false; })
        );
    else
      return this.apiService.updateStatDef(this.def.id, {
        conditions: [],
        change: this.def
      }).pipe(
        map(r => { return r.changed; })
      );
  }

  askForName(dontSave: boolean = false): Observable<boolean> {
    var result: Observable<boolean> = new Observable((observer) => {
      this.modalService.open(this.newDialog).result.then(r => {
        if (r === "save") {
          if (!dontSave)
            this.save().subscribe(r => observer.next(r), (err => observer.error(err)));
          else
            observer.next(true);
          return true;
        } else
          observer.next(false);
          return false;
      });
    });
    return result;
  }

  shareChanged() {
    this.save().subscribe(
      r => {},
      err => {
        alert(this.apiService.getErrorMsg(err));
      }
    );
  }

  showChartError(message: string) {
    this.chartError = true;
    this.chartErrorMsg = message;
  }

  saveAs() {
    this.askForName(true).subscribe(r => {
      if (r) {
        this.def.id = -1;
        this.def.shared = false;
        this.def.user = {
          id: this.authService.currentUserValue.id,
          name: this.authService.currentUserValue.username,
          login_name: this.authService.currentUserValue.username
        }
        this.save().subscribe(sr => {
          if (sr)
            this.router.navigate(['/analyses', this.def.id]);
        }, (err) => {
          alert(this.apiService.getErrorMsg(err));
        })
      }
    })
  }
}
