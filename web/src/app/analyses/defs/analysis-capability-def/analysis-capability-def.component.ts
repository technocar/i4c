import { Component, Input, OnInit, ViewChild } from '@angular/core';
import { ChartConfiguration, ChartTypeRegistry, ScatterDataPoint, BubbleDataPoint } from 'chart.js';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { AuthenticationService } from 'src/app/services/auth.service';
import { Meta, NumberRelation, StatCapabilityDef, StatCapabilityDefVisualSettings, StatCapabilityDefVisualSettingsInfoBoxLocation, StatCapabilityFilter, StatData, StatXYFilter, StatXYMeta, StatXYMetaObjectField } from 'src/app/services/models/api';
import { Labels } from 'src/app/services/models/constants';
import { AnalysisChart, AnalysisDef } from '../../analyses.component';
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

    var range = (data.capabilitydata.mean + data.capabilitydata.sigma * 3) * 2;
    var start = data.capabilitydata.mean - data.capabilitydata.sigma * 3;
    console.log(range);
    var points: number[] = [];
    for (let i = 0; i < 100; i++)
      points.push(range * Math.random() + start);

    points = points.sort((a, b) => {
      if (a < b)
        return -1;
      if (a > b)
        return 1;
      return 0;
    });

    var options: ChartConfiguration = {
      type: 'line',
      data: {
        datasets: [{
          label: "",
          data: points.map((p) => {
            var v = normalDistribution(p);
            console.log(`p: ${p} nd: ${v}`);
            return { x: p, y: v };
          }),
          fill: false,
          cubicInterpolationMode: 'monotone',
        }]
      },
      options: {
        elements: {
          point: {
            radius: 0
          }
        },
        scales: {
          x: {
            type: "linear"
          }
        }
      }
    };
    console.log(options);
    return options;
  }
}
