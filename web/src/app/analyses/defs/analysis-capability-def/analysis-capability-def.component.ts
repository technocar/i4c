import { Component, Input, OnInit, ViewChild } from '@angular/core';
import { ChartConfiguration, ChartTypeRegistry, ScatterDataPoint, BubbleDataPoint, Tick, Chart } from 'chart.js';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { AuthenticationService } from 'src/app/services/auth.service';
import { Device, Meta, NumberRelation, StatCapabilityDef, StatCapabilityDefVisualSettings, StatCapabilityDefVisualSettingsInfoBoxLocation, StatCapabilityFilter, StatData, StatXYFilter, StatXYMeta, StatXYMetaObjectField } from 'src/app/services/models/api';
import { Labels } from 'src/app/services/models/constants';
import { AnalysisChart, AnalysisDef } from '../../analyses.component';
import { AnalysisHelpers } from '../../helpers';
import { AnalysisDatetimeDefComponent } from '../analysis-datetime-def/analysis-datetime-def.component';
/*import 'hammerjs';
import zoomPlugin from 'chartjs-plugin-zoom';
Chart.register(zoomPlugin);*/


@Component({
  selector: 'app-analysis-capability-def',
  templateUrl: './analysis-capability-def.component.html',
  styleUrls: ['./analysis-capability-def.component.scss']
})
export class AnalysisCapabilityDefComponent implements OnInit, AnalysisDef, AnalysisChart {

  @Input("def") def: StatCapabilityDef;
  @Input("metaList") metaList: Meta[];
  @Input("canUpdate") canUpdate: boolean = false;
  @ViewChild('period') period: AnalysisDatetimeDefComponent;

  selectableMetas: Meta[] = [];
  filters$: BehaviorSubject<StatCapabilityFilter[]> = new BehaviorSubject([]);
  eventOps: string[][] = [];

  locations = [
    ['none', $localize `:@@analysis_capability_infobox_loc_none:nincs`],
    ['left', $localize `:@@analysis_capability_infobox_loc_left:baloldalt`],
    ['right', $localize `:@@analysis_capability_infobox_loc_right:jobboldalt`],
    ['bottom', $localize `:@@analysis_capability_infobox_loc_bottom:lent`],
    ['top', $localize `:@@analysis_capability_infobox_loc_top:fent`]
  ]
  labels = Labels.analysis;
  devices: Device[] = [];
  device: string;

  constructor(
    private apiService: ApiService,
    private authService: AuthenticationService
  ) {
    this.eventOps = apiService.getEventOperations();
    apiService.getDevices()
      .subscribe(r => {
        this.devices = r;
        this.device = this.devices[0].id;
      });
  }

  filterMeta() {
    this.selectableMetas = this.metaList.filter(m => m.device === this.device);
  }

  ngOnInit(): void {
    if (!this.def)
      this.def = {
        before: undefined,
        after: undefined,
        duration: undefined,
        filter: [],
        lcl: undefined,
        ltl: undefined,
        metric: undefined,
        nominal: undefined,
        ucl: undefined,
        utl: undefined,
        visualsettings: undefined
      };
    else {
      this.device = this.def.metric?.device ?? this.device;
      this.filters$.next(this.def.filter ?? []);
    }

    this.filterMeta();
    this.setDefualtVisualSettings();
  }

  setDefualtVisualSettings() {
    var defaults: StatCapabilityDefVisualSettings = {
      title: "",
      subtitle: "",
      infoboxloc: StatCapabilityDefVisualSettingsInfoBoxLocation.None,
      plotdata: false
    };

    if (!this.def.visualsettings)
      this.def.visualsettings = defaults;
    else {
      this.def.visualsettings = Object.assign(defaults, this.def.visualsettings);
    }
  }

  getDef(): StatCapabilityDef {
    var pDef = this.period.getDef();
    console.log(pDef);
    this.def.after = pDef.after;
    this.def.before = pDef.before;
    this.def.duration = pDef.duration;
    this.def.filter = this.filters$.value.slice(0);
    return this.def;
  }

  newFilter() {
    var filters = this.filters$.value;
    filters.push({
      id: ((filters ?? []).length === 0 ? 0 : Math.max(...filters.map(f => f.id))) + 1,
      device: undefined,
      data_id: undefined,
      rel: undefined,
      value: undefined
    });
    this.filters$.next(filters);
  }

  updateFilterId(meta: Meta, filter: StatCapabilityFilter) {
    filter.data_id = meta.data_id;
    filter.device = meta.device;
  }

  deleteFilter(filter: StatCapabilityFilter) {
    var filters = this.filters$.value;
    var idx = filters.findIndex((f) => { return f.data_id === filter.data_id && f.device === filter.device });
    if (idx > -1)
      filters.splice(idx, 1);
    this.filters$.next(filters);
  }

  changeMetric(meta: Meta) {
    this.def.metric = {
      device: meta.device,
      data_id: meta.data_id
    }
  }

  changeDevice(deviceId: string) {
    this.device = deviceId;
    this.filterMeta();
  }

  getChartConfiguration(data: StatData): ChartConfiguration {

    function normalDistribution(x: number): number {
      const dividend =
        Math.E ** -((x - data.capabilitydata.mean) ** 2 / (2 * data.capabilitydata.sigma ** 2));
      const divisor = data.capabilitydata.sigma * Math.sqrt(2 * Math.PI);
      return dividend / divisor;
    }

    var myTicks: Tick[] = [
      { label: `${data.capabilitydata.mean?.toFixed(3)}|középérték`, value: data.capabilitydata.mean, major: true  },
      { label: `${data.stat_def.capabilitydef.nominal?.toFixed(3)}|névleges`, value: data.stat_def.capabilitydef.nominal, major: true  },
      { label: `${data.stat_def.capabilitydef.lcl?.toFixed(3)}|${'lcl'}`, value: data.stat_def.capabilitydef.lcl, major: true  },
      { label: `${data.stat_def.capabilitydef.ltl?.toFixed(3)}|${'ltl'}`, value: data.stat_def.capabilitydef.ltl, major: true  },
      { label: `${data.stat_def.capabilitydef.ucl?.toFixed(3)}|${'ucl'}`, value: data.stat_def.capabilitydef.ucl, major: true  },
      { label: `${data.stat_def.capabilitydef.utl?.toFixed(3)}|${'utl'}`, value: data.stat_def.capabilitydef.utl, major: true  },
      { label: `${(data.capabilitydata.mean - 3*data.capabilitydata.sigma)?.toFixed(4)}|-3σ`, value: data.capabilitydata.mean - 3*data.capabilitydata.sigma, major: true  },
      { label: `${(data.capabilitydata.mean - data.capabilitydata.sigma)?.toFixed(4)}|-σ`, value: data.capabilitydata.mean - data.capabilitydata.sigma, major: true  },
      { label: `${(data.capabilitydata.mean + data.capabilitydata.sigma)?.toFixed(4)}|σ`, value: data.capabilitydata.mean + data.capabilitydata.sigma, major: true  },
      { label: `${(data.capabilitydata.mean + 3*data.capabilitydata.sigma)?.toFixed(4)}|3σ`, value: data.capabilitydata.mean + 3*data.capabilitydata.sigma, major: true  }
    ];

    console.log(myTicks);

    if (data.stat_def.capabilitydef.visualsettings.plotdata)
    myTicks.push(...(data.capabilitydata.points ?? []).map(p => {
        return <Tick>{
          label: "",
          value: p,
          major: false
        }
      }));

    myTicks = myTicks.sort((a, b) => {
      if (a.value < b.value)
        return -1;
      if (a.value > b.value)
        return 1;
      return 0;
    });
    myTicks = myTicks.filter((t, i) => myTicks.findIndex(t2 => t2.value === t.value) === i);

    var range = data.capabilitydata.sigma * 4 * 2;
    var start = data.capabilitydata.mean - data.capabilitydata.sigma * 4;
    console.log(range);
    var points: number[] = [];
    for (let i = 0; i < 100; i++) {
      points.push(range * i / 100 + start);
    }

    points.push(data.capabilitydata.mean);
    points.push(data.stat_def.capabilitydef.lcl);
    points.push(data.stat_def.capabilitydef.ltl);
    points.push(data.stat_def.capabilitydef.ucl);
    points.push(data.stat_def.capabilitydef.utl);

    points = points.sort((a, b) => {
      if (a < b)
        return -1;
      if (a > b)
        return 1;
      return 0;
    });
    points = points.filter((p, i) => points.indexOf(p) === i && (p ?? null) !== null);
    console.log(points);

    var chartData = points.map((p) => {
      var v = normalDistribution(p);
      //console.log(`p: ${p} nd: ${v}`);
      return { x: p, y: v };
    });

    console.log(myTicks);
    var options: ChartConfiguration = {
      type: 'line',
      data: {
        datasets: [{
          label: "",
          data: chartData,
          fill: false,
          cubicInterpolationMode: 'monotone',
          tension: 1,
          borderColor: '#b7b7cc'
        }, {
          label: "",
          data: chartData,
          fill: false,
          cubicInterpolationMode: 'monotone',
          tension: 1,
          borderColor: 'transparent',
          xAxisID: "x2"
        }]
      },
      options: {
        elements: {
          point: {
            radius: 0
          }
        },
        plugins: {
          title: AnalysisHelpers.setChartTitle(data.stat_def.capabilitydef.visualsettings?.title),
          subtitle: AnalysisHelpers.setChartTitle(data.stat_def.capabilitydef.visualsettings?.subtitle),
          legend: {
            display: false
          }/*,
          zoom: {
            pan: {
              enabled: false,
              mode: 'xy',
              modifierKey: 'ctrl'
            },
            zoom: {
              wheel: {
                enabled: false,
              },
              drag: {
                enabled: true
              },
              pinch: {
                enabled: false
              },
              mode: 'xy'
            }
          }*/
        },
        scales: {
          y: {
            min: 0,
            grid: {
              drawBorder: false,
              color: function(context) {
                if (context.tick.value !== 0)
                  return '#fff';
                else
                  return '#000';
              }
            },
            ticks: {
              display: false
            }
          },
          x: {
            min: points[0],
            type: "linear",
            grid: {
              drawBorder: true,
              lineWidth: function(context) {
                if (context.tick.value === data.stat_def.capabilitydef.utl || context.tick.value === data.stat_def.capabilitydef.ltl) {
                  return 2
                } else if (context.tick.value === data.stat_def.capabilitydef.ucl || context.tick.value === data.stat_def.capabilitydef.lcl) {
                  return 2;
                } else if (context.tick.value === data.capabilitydata.mean) {
                  return 2;
                } else if (context.tick.value === data.stat_def.capabilitydef.nominal) {
                  return 2;
                } else if (context.tick.value === data.capabilitydata.mean - data.capabilitydata.sigma
                  || context.tick.value === data.capabilitydata.mean - 3*data.capabilitydata.sigma
                  || context.tick.value === data.capabilitydata.mean + data.capabilitydata.sigma
                  || context.tick.value === data.capabilitydata.mean + 3*data.capabilitydata.sigma) {
                  return 2;
                }
                return 1;
              },
              color: function(context) {
                if (context.tick.value === data.stat_def.capabilitydef.utl || context.tick.value === data.stat_def.capabilitydef.ltl) {
                  return '#CC2936'
                } else if (context.tick.value === data.stat_def.capabilitydef.ucl || context.tick.value === data.stat_def.capabilitydef.lcl) {
                  return '#00A3FF';
                } else if (context.tick.value === data.capabilitydata.mean) {
                  return '#000';
                } else if (context.tick.value === data.stat_def.capabilitydef.nominal) {
                  return '#388697';
                } else if (context.tick.value === data.capabilitydata.mean - data.capabilitydata.sigma
                  || context.tick.value === data.capabilitydata.mean - 3*data.capabilitydata.sigma
                  || context.tick.value === data.capabilitydata.mean + data.capabilitydata.sigma
                  || context.tick.value === data.capabilitydata.mean + 3*data.capabilitydata.sigma) {
                  return '#eed2aa';
                }

                return '#ddd';
              },
            },
            ticks: {
              autoSkip: false,
              major: {
                enabled: true
              },
              minRotation: 45,
              callback: (value, index, ticks) => {
                return ticks[index].label
              }
            },
            bounds: "ticks",
            afterBuildTicks: (axis) => {
              axis.ticks.push(...myTicks.map(t => <Tick>{
                label: t.label.toString().split("|")[0],
                value: t.value,
                major: t.major
              }));
            }
          },
          "x2": {
            type: 'linear',
            position: 'top',
            min: points[0],
            ticks: {
              autoSkip: false,
              major: {
                enabled: true
              },
              minRotation: 45,
              callback: (value, index, ticks) => {
                return ticks[index].label
              }
            },
            bounds: "ticks",
            afterBuildTicks: (axis) => {
              axis.ticks.push(...myTicks.map(t => <Tick>{
                label: t.label.toString().split("|")[1],
                value: t.value,
                major: t.major
              }));
            }
          }
        }
      }
    };
    return options;
  }

  resetZoom(chart) {
    chart.resetZoom();
  }

  buildInfoBox(data: StatData): HTMLDivElement {
    if (data.stat_def.capabilitydef.visualsettings.infoboxloc === StatCapabilityDefVisualSettingsInfoBoxLocation.None)
      return null;

    var infoBox = document.createElement('div');
    infoBox.classList.add('row');
    infoBox.classList.add('infobox');
    var setData: [string, string, string][] = [
      ['#388697', $localize `:@@analysis_capability_infobox_nominal:nominális`, data.stat_def.capabilitydef.nominal?.toFixed(3)],
      ['#CC2936', $localize `:@@analysis_capability_infobox_utl:UTL`, data.stat_def.capabilitydef.utl?.toFixed(3)],
      ['#00A3FF', $localize `:@@analysis_capability_infobox_ucl:UCL`, data.stat_def.capabilitydef.ucl?.toFixed(3)],
      ['#CC2936', $localize `:@@analysis_capability_infobox_ltl:LTL`, data.stat_def.capabilitydef.ltl?.toFixed(3)],
      ['#00A3FF', $localize `:@@analysis_capability_infobox_lcl:LCL`, data.stat_def.capabilitydef.lcl?.toFixed(3)]
    ];
    var measuredData: [string, string, string][] = [
      ['#000', $localize `:@@analysis_capability_infobox_mean:középérték`, data.capabilitydata.mean?.toFixed(3)],
      [undefined, $localize `:@@analysis_capability_infobox_count:darab`, data.capabilitydata.count?.toFixed(0)],
      [undefined, $localize `:@@analysis_capability_infobox_min:min`, data.capabilitydata.min?.toFixed(3)],
      [undefined, $localize `:@@analysis_capability_infobox_min:max`, data.capabilitydata.max?.toFixed(3)],
      ['#eed2aa', $localize `:@@analysis_capability_infobox_sigma:σ`, '±' + data.capabilitydata.sigma?.toFixed(4)],
      ['#eed2aa', $localize `:@@analysis_capability_infobox_3sigma:3σ`, '±' + (data.capabilitydata.sigma * 3)?.toFixed(4)],
      ['#eed2aa', $localize `:@@analysis_capability_infobox_c:C`, data.capabilitydata.c?.toFixed(3)],
      ['#eed2aa', $localize `:@@analysis_capability_infobox_ck:Ck`, data.capabilitydata.ck?.toFixed(3)]
    ];

    infoBox.append(this.createBox($localize `:@@analysis_capability_infobox_title_set:beállított paraméterek`, setData, this.def.visualsettings.infoboxloc));
    infoBox.append(this.createBox($localize `:@@analysis_capability_infobox_title_measured:mért értékek`, measuredData, this.def.visualsettings.infoboxloc));

    return infoBox;
  }

  private createBox(title: string, data: [string, string, string][], pos: StatCapabilityDefVisualSettingsInfoBoxLocation): HTMLDivElement {
    var box = document.createElement('div');
    box.classList.add('box');
    box.classList.add(pos === StatCapabilityDefVisualSettingsInfoBoxLocation.Left || pos === StatCapabilityDefVisualSettingsInfoBoxLocation.Right ? "col-12" : "col");
    box.append(this.createBoxRow([title], 'title'));
    data.forEach(d => box.append(this.createBoxRow(d, undefined)))
    return box;
  }

  private createBoxRow(data: string[], css: string): HTMLDivElement {
    var row = document.createElement("div");
    row.classList.add("row");
    data.forEach((d, i) => {
      let col = document.createElement('div');
      if (css)
        col.classList.add(css);
      if (i === 0 && data.length > 1) {
        col.classList.add("col-auto");
        col.style.backgroundColor = d ?? 'transparent';
      } else {
        col.innerText = d ?? "";
        col.classList.add("col");
      }
      row.append(col);
    });
    return row;
  }
}
