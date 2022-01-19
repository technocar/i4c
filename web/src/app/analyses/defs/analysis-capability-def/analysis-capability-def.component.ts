import { Component, Input, OnInit, ViewChild } from '@angular/core';
import { ChartConfiguration, ChartTypeRegistry, ScatterDataPoint, BubbleDataPoint } from 'chart.js';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { AuthenticationService } from 'src/app/services/auth.service';
import { Meta, NumberRelation, StatCapabilityDef, StatCapabilityDefVisualSettings, StatCapabilityDefVisualSettingsInfoBoxLocation, StatCapabilityFilter, StatData, StatXYFilter, StatXYMeta, StatXYMetaObjectField } from 'src/app/services/models/api';
import { Labels } from 'src/app/services/models/constants';
import { AnalysisChart, AnalysisDef } from '../../analyses.component';
import { AnalysisHelpers } from '../../helpers';
import { AnalysisDatetimeDefComponent } from '../analysis-datetime-def/analysis-datetime-def.component';


@Component({
  selector: 'app-analysis-capability-def',
  templateUrl: './analysis-capability-def.component.html',
  styleUrls: ['./analysis-capability-def.component.scss']
})
export class AnalysisCapabilityDefComponent implements OnInit, AnalysisDef, AnalysisChart {

  @Input("def") def: StatCapabilityDef;
  @Input("metaList") metaList: Meta[];
  @ViewChild('period') period: AnalysisDatetimeDefComponent;

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
  access = {
    canUpdate: false
  }

  constructor(
    private apiService: ApiService,
    private authService: AuthenticationService
  ) {
    this.access.canUpdate = authService.hasPrivilige("patch/stat/def/{id}", "patch any");
    this.eventOps = apiService.getEventOperations();
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
      this.filters$.next(this.def.filter ?? []);
    }

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

  getChartConfiguration(data: StatData): ChartConfiguration {

    function normalDistribution(x: number): number {
      const dividend =
        Math.E ** -((x - data.capabilitydata.mean) ** 2 / (2 * data.capabilitydata.sigma ** 2));
      const divisor = data.capabilitydata.sigma * Math.sqrt(2 * Math.PI);
      return dividend / divisor;
    }

    var ticks: [string, number][] = [
      [ "", data.capabilitydata.mean ],
      [ "lcl", data.stat_def.capabilitydef.lcl ],
      [ "ltl", data.stat_def.capabilitydef.ltl ],
      [ "ucl", data.stat_def.capabilitydef.ucl ],
      [ "utl", data.stat_def.capabilitydef.utl ]
    ];

    if (data.stat_def.capabilitydef.visualsettings.plotdata)
      ticks.push(...(data.capabilitydata.points ?? []).map(p => {
        return <[string, number]>["", p]
      }));

    ticks = ticks.sort((a, b) => {
      if (a[1] < b[1])
        return -1;
      if (a[1] > b[1])
        return 1;
      return 0;
    });
    ticks = ticks.filter((t, i) => ticks.findIndex(t2 => t2[1] === t[1]) === i);

    var range = (data.capabilitydata.mean + data.capabilitydata.sigma * 4) * 2;
    var start = data.capabilitydata.mean - data.capabilitydata.sigma * 4;
    console.log(range);
    var points: number[] = [];
    for (let i = 0; i < 100; i++)
      points.push(range * Math.random() + start);

    console.log(points);

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
    points = points.filter((p, i) => points.indexOf(p) === i);

    console.log(ticks);
    var options: ChartConfiguration = {
      type: 'line',
      data: {
        datasets: [{
          label: "",
          data: points.map((p) => {
            var v = normalDistribution(p);
            //console.log(`p: ${p} nd: ${v}`);
            return { x: p, y: v };
          }),
          fill: false,
          cubicInterpolationMode: 'monotone',
          tension: 1,
          borderColor: '#b7b7cc'
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
          }
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
            type: "linear",
            grid: {
              drawBorder: false,
              lineWidth: function(context) {
                if (context.tick.value === data.stat_def.capabilitydef.utl || context.tick.value === data.stat_def.capabilitydef.ltl) {
                  return 2
                } else if (context.tick.value === data.stat_def.capabilitydef.ucl || context.tick.value === data.stat_def.capabilitydef.lcl) {
                  return 2;
                } else if (context.tick.value === data.capabilitydata.mean) {
                  return 2;
                }
                return 1;
              },
              color: function(context) {
                console.log(context);
                if (context.tick.value === data.stat_def.capabilitydef.utl || context.tick.value === data.stat_def.capabilitydef.ltl) {
                  return '#00A3FF'
                } else if (context.tick.value === data.stat_def.capabilitydef.ucl || context.tick.value === data.stat_def.capabilitydef.lcl) {
                  return '#CC2936';
                } else if (context.tick.value === data.capabilitydata.mean) {
                  return '#000';
                }

                return '#ddd';
              },
            },
            ticks: {
              autoSkip: false,
              major: {
                enabled: true
              },
              callback: (value, index, ticks) => {
                return ticks[index].label;
              }
            },
            bounds: "ticks",
            afterBuildTicks: (axis) => {
              axis.ticks = ticks.map(t => {
                return {
                  value: t[1],
                  label: t[0],
                  major: true
                }
              });
            }
          }
        }
      }
    };
    console.log(options);
    return options;
  }

  buildInfoBox(data: StatData): HTMLDivElement {
    if (data.stat_def.capabilitydef.visualsettings.infoboxloc === StatCapabilityDefVisualSettingsInfoBoxLocation.None)
      return null;

    var infoBox = document.createElement('div');
    infoBox.classList.add('row');
    infoBox.classList.add('infobox');
    var setData: [string, string][] = [
      [$localize `:@@analysis_capability_infobox_nominal:névleges`, data.stat_def.capabilitydef.nominal?.toFixed(3)],
      [$localize `:@@analysis_capability_infobox_utl:UTL`, data.stat_def.capabilitydef.utl?.toFixed(3)],
      [$localize `:@@analysis_capability_infobox_ucl:UCL`, data.stat_def.capabilitydef.ucl?.toFixed(3)],
      [$localize `:@@analysis_capability_infobox_ltl:LTL`, data.stat_def.capabilitydef.ltl?.toFixed(3)],
      [$localize `:@@analysis_capability_infobox_lcl:LCL`, data.stat_def.capabilitydef.lcl?.toFixed(3)]
    ];
    var measuredData: [string, string][] = [
      [$localize `:@@analysis_capability_infobox_mean:középérték`, data.capabilitydata.mean?.toFixed(3)],
      [$localize `:@@analysis_capability_infobox_sigma:σ`, '±' + data.capabilitydata.sigma?.toFixed(3)],
      [$localize `:@@analysis_capability_infobox_3sigma:3σ`, '±' + (data.capabilitydata.sigma * 3)?.toFixed(3)],
      [$localize `:@@analysis_capability_infobox_c:C`, data.capabilitydata.c?.toFixed(3)],
      [$localize `:@@analysis_capability_infobox_ck:Ck`, data.capabilitydata.ck?.toFixed(3)]
    ];

    infoBox.append(this.createBox($localize `:@@analysis_capability_infobox_title_set:beállított paraméterek`, setData, data.stat_def.capabilitydef.visualsettings.infoboxloc));
    infoBox.append(this.createBox($localize `:@@analysis_capability_infobox_title_measured:mért értékek`, measuredData, data.stat_def.capabilitydef.visualsettings.infoboxloc));

    return infoBox;
  }

  private createBox(title: string, data: [string, string][], pos: StatCapabilityDefVisualSettingsInfoBoxLocation): HTMLDivElement {
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
    for (let d of data) {
      let col = document.createElement('div');
      if (css)
        col.classList.add(css);
      col.classList.add("col");
      col.innerText = d;
      row.append(col);
    }
    return row;
  }
}
