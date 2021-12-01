import { DatePipe } from '@angular/common';
import { Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { Chart, ChartConfiguration, registerables, TitleOptions  } from 'chart.js';
import { _DeepPartialObject } from 'chart.js/types/utils';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiService } from 'src/app/services/api.service';
import { AuthenticationService } from 'src/app/services/auth.service';
import { Meta, StatData, StatDef, StatTimeSeriesDef } from 'src/app/services/models/api';
import { AnalysisType } from '../analyses.component';
import { AnalysisTimeseriesDefComponent } from '../defs/analysis-timeseries-def/analysis-timeseries-def.component';

Chart.register(...registerables);

class HSLColor {
  hue: number;
  saturation: number;
  lightness: number;

  constructor(hue: number, saturation: number, lightess: number) {
    this.hue = hue;
    this.saturation = saturation;
    this.lightness = lightess;
  }

  public toString(): string {
    return `hsl(${this.hue}, ${this.saturation * 100}%, ${this.lightness * 100}%)`;
  }
}

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
  @ViewChild('new_dialog') newDialog;
  @ViewChild('chart', {static: false}) chart: ElementRef;

  constructor(
    private route: ActivatedRoute,
    private authService: AuthenticationService,
    private modalService: NgbModal,
    private apiService: ApiService
  ) {
    this.analysisType = (route.snapshot.paramMap.get("type") ?? "0") as AnalysisType;
  }

  ngOnInit(): void {
    this.route.data.subscribe(r => {
      this.metaList = r.data[0];
      this.def = r.data[1];
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
      this.chartError = true;
      this.chartErrorMsg = this.apiService.getErrorMsg(err).toLocaleString();
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
        this.chartError = true;
        this.chartErrorMsg = this.apiService.getErrorMsg(err).toString();
      }, () => {
        this.chartLoading$.next(false);
      });
  }

  buildChart(result: StatData) {
    var ctx = this.chart.nativeElement.getContext('2d');

    if (!result?.timeseriesdata || result?.timeseriesdata?.length === 0) {
      this.chartError = true;
      this.chartErrorMsg = $localize `:@@chart_no_data:Nincs megjeleníthető adat!`;
      return;
    }

    var startColor: HSLColor = new HSLColor(191, 0.46, 0.41);
    var endColor: HSLColor = new HSLColor(172, 0.41, 0.39);
    var datePipe = new DatePipe('en-US');

    var options: ChartConfiguration = {
      type: 'line',
      data: {
        datasets: result.timeseriesdata.map((series, seriesIndex, seriesList) => { return  {
          label: seriesList.length === 1 ? "" : series.name,
          data: series.y.map((value, i) => {
            return {
              x: result.stat_def.timeseriesdef.xaxis === "timestamp" ? datePipe.transform(new Date(series["x_" + result.stat_def.timeseriesdef.xaxis][i]), "yyyy.MM.dd HH:mm:ss") : series["x_" + result.stat_def.timeseriesdef.xaxis][i],
              y: value
            }
          }),
          backgroundColor: this.getChartSeriesColor(seriesIndex, seriesList.length, startColor, endColor).toString(),
          borderColor: this.getChartSeriesColor(seriesIndex, seriesList.length, startColor, endColor).toString(),
          borderWidth: 1
        }})
      },
      options: {
        plugins: {
          title: this.setChartTitle(this.def.timeseriesdef.visualsettings?.title),
          subtitle: this.setChartTitle(this.def.timeseriesdef.visualsettings?.subtitle),
          legend: {
            display:  result.timeseriesdata.length > 1,
            align: this.def.timeseriesdef.visualsettings?.legend?.align,
            position: this.def.timeseriesdef.visualsettings?.legend?.position
          }
        },
        scales: {
          yaxis: {
            title: this.setChartTitle(this.def.timeseriesdef.visualsettings?.yaxis?.caption)
          },
          xaxis: {
            title: this.setChartTitle(this.def.timeseriesdef.visualsettings?.xaxis?.caption)
          }
        }
      }
    };

    this._chartInstance = new Chart(ctx, options);
  }

  setChartTitle(title: string): _DeepPartialObject<TitleOptions> {
    return {
      display: (title ?? "") !== "",
      text: title
    };
  }

  save(): Observable<boolean> {
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

  askForName(): Observable<boolean> {
    var result: Observable<boolean> = new Observable((observer) => {
      this.modalService.open(this.newDialog).result.then(r => {
        if (r === "save") {
          this.save().subscribe(r => observer.next(r), (err => observer.error(err)));
          return true;
        } else
          observer.next(false);
          return false;
      });
    });
    return result;
  }

  getChartSeriesColor(index: number, count: number, firstColor: HSLColor, lastColor: HSLColor): HSLColor {
    var color = new HSLColor(
      firstColor.hue * (count - (index + 1)) / count + lastColor.hue * (index + 1) / count,
      firstColor.saturation * (count - (index + 1)) / count + lastColor.saturation * (index + 1) / count,
      firstColor.lightness * (count - (index + 1)) / count + lastColor.lightness * (index + 1) / count
    );
    console.log(color.toString());
    return color;
  }
}
