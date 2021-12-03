import { DatePipe } from '@angular/common';
import { Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { Chart, ChartConfiguration, FontSpec, registerables, TitleOptions  } from 'chart.js';
import 'chartjs-adapter-date-fns';
import { _DeepPartialObject } from 'chart.js/types/utils';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiService } from 'src/app/services/api.service';
import { AuthenticationService } from 'src/app/services/auth.service';
import { Meta, StatData, StatDef, StatTimeSeriesDef } from 'src/app/services/models/api';
import { AnalysisType } from '../analyses.component';
import { AnalysisTimeseriesDefComponent } from '../defs/analysis-timeseries-def/analysis-timeseries-def.component';

Chart.register(...registerables);

class HSLAColor {
  hue: number;
  saturation: number;
  lightness: number;
  alpha: number;

  constructor(hue: number, saturation: number, lightess: number, alpha: number) {
    this.hue = hue;
    this.saturation = saturation;
    this.lightness = lightess;
    this.alpha = alpha;
  }

  public toString(): string {
    return `hsla(${Math.round(this.hue)}, ${Math.round(this.saturation * 100)}%, ${Math.round(this.lightness * 100) }%, ${this.alpha})`;
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
    var ctx = this.chart.nativeElement.getContext('2d');

    if (!result?.timeseriesdata
      || result.timeseriesdata.length === 0) {
      this.showChartError($localize `:@@chart_no_data:Nincs megjeleníthető adat!`);
      return;
    }

    var startColor: HSLAColor = new HSLAColor(240, 0.17, 0.76, 1);
    var endColor: HSLAColor = new HSLAColor(240, 0.82, 0.11 , 1);
    var datePipe = new DatePipe('en-US');
    var relativeChart = result.timeseriesdata.length > 1;
    var xaxisPropName = "x_" + (!relativeChart ? "timestamp" : "relative");
    var xyChart = !(this.def.timeseriesdef.xaxis === 'sequence');

    try {
      var options: ChartConfiguration = {
        type: 'line',
        data: {
          datasets: result.timeseriesdata.map((series, seriesIndex, seriesList) => {
            console.log(seriesIndex);
            return  {
              label: seriesList.length === 1 ? "" : series.name,
              data: series.y.map((value, i) => {
                let xValue = series[xaxisPropName];
                return {
                  x: (xValue ?? null) === null ? i.toString() : (relativeChart ? xValue[i] * 1000.00 : xValue[i]),
                  y: value
                }
              }),
              backgroundColor: this.getChartSeriesColor(seriesIndex, seriesList.length, startColor, endColor, 0.3).toString(),
              borderColor: this.getChartSeriesColor(seriesIndex, seriesList.length, startColor, endColor, 1).toString(),
              borderWidth: 2,
              fill: false
          }})
        },
        options: {
          elements: {
            point: {
              radius: 0
            }
          },
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
            y: {
              title: this.setChartTitle(this.def.timeseriesdef.visualsettings?.yaxis?.caption)
            },
            x: {
              type: xyChart ? 'time' : 'linear',
              title: this.setChartTitle(this.def.timeseriesdef.visualsettings?.xaxis?.caption),
              time: {
                displayFormats: {
                    hour: 'H:mm',
                    millisecond: 's.SSS',
                    second: 's.SSS',
                    minute: 'm:ss',
                    day: relativeChart ? 'd' : 'MMM d'
                },
                tooltipFormat: relativeChart ? 's.SSS' : 'yyyy.MM.dd HH:mm:ss',
                minUnit: 'millisecond'
              },
              grid: {
                display: xyChart
              },
              ticks: {
                display: xyChart,
                font: (ctx, options) => {
                  var font: FontSpec = {
                    family: undefined,
                    lineHeight: undefined,
                    size: undefined,
                    style: undefined,
                    weight: undefined
                  };
                  if (ctx.tick?.major)
                    font.weight = 'bold';
                  return font;
                },
                major: {
                  enabled: true
                }
              },
              bounds: 'ticks'
            }
          }
        }
      };
    }
    catch(err) {
      this.showChartError(err);
    }

    this._chartInstance = new Chart(ctx, options);
  }

  setChartTitle(title: string): _DeepPartialObject<TitleOptions> {
    return {
      display: (title ?? "") !== "",
      text: title
    };
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

  getChartSeriesColor(index: number, count: number, firstColor: HSLAColor, lastColor: HSLAColor, alpha: number): HSLAColor {
    var hsl2hsv = (h,s,l,v=s*Math.min(l,1-l)+l) => [h, v?2-2*l/v:0, v];
    let hsv2hsl = (h,s,v,l=v-v*s/2, m=Math.min(l,1-l)) => [h,m?(v-l)/m:0,l];
    var hsvA = hsl2hsv(firstColor.hue, firstColor.saturation, firstColor.lightness);
    var hsvB = hsl2hsv(lastColor.hue, lastColor.saturation, lastColor.lightness);
    var hsvColor = [
      hsvA[0] * (count - (index + 1)) / count + hsvB[0] * (index + 1) / count,
      hsvA[1] * (count - (index + 1)) / count + hsvB[1] * (index + 1) / count,
      hsvA[2] * (count - (index + 1)) / count + hsvB[2] * (index + 1) / count
    ];
    var hslColor = hsv2hsl(hsvColor[0], hsvColor[1], hsvColor[2]);
    var color = new HSLAColor(hslColor[0], hslColor[1], hslColor[2], alpha);
    console.log(color.toString());
    return color;
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
