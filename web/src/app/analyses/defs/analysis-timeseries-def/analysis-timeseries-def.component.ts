import { Component, Input, OnInit, ViewChild } from '@angular/core';
import { ChartConfiguration, ChartTypeRegistry, ScatterDataPoint, BubbleDataPoint, FontSpec } from 'chart.js';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { AuthenticationService } from 'src/app/services/auth.service';
import { StatTimeSeriesAggFunc, Meta, StatDefBase, StatTimeSeriesDef, StatTimesSeriesFilter, StatTimeSeriesName, StatVisualSettingsChartLegendAlign, StatVisualSettingsChartLegendPosition, StatData, StatVisualSettingsChart, Device } from 'src/app/services/models/api';
import { DeviceType, Labels } from 'src/app/services/models/constants';
import { AnalysisChart, AnalysisDef } from '../../analyses.component';
import { AnalysisHelpers, HSLAColor } from '../../helpers';
import { AnalysisDatetimeDefComponent } from '../analysis-datetime-def/analysis-datetime-def.component';

interface StatTimesSeriesFilterEx extends StatTimesSeriesFilter {
  valueList?: string[];
}

@Component({
  selector: 'app-analysis-timeseries-def',
  templateUrl: './analysis-timeseries-def.component.html',
  styleUrls: ['./analysis-timeseries-def.component.scss']
})
export class AnalysisTimeseriesDefComponent implements OnInit, AnalysisDef, AnalysisChart {

  @Input("def") def: StatTimeSeriesDef;
  @Input("metaList") metaList: Meta[];
  @ViewChild('period') period: AnalysisDatetimeDefComponent;


  filters$: BehaviorSubject<StatTimesSeriesFilterEx[]> = new BehaviorSubject([]);

  aggFuncs: string[][] = [
    [StatTimeSeriesAggFunc.Avg, $localize `:@@stat_timeseries_agg_func_avg:átlag`],
    [StatTimeSeriesAggFunc.Median, $localize `:@@stat_timeseries_agg_func_median:median`],
    [StatTimeSeriesAggFunc.Min, $localize `:@@stat_timeseries_agg_func_min:min`],
    [StatTimeSeriesAggFunc.Max, $localize `:@@stat_timeseries_agg_func_max:max`],
    [StatTimeSeriesAggFunc.FirstQuartile, $localize `:@@stat_timeseries_agg_func_q1st:1. kvantilis`],
    [StatTimeSeriesAggFunc.FourQuartile, $localize `:@@stat_timeseries_agg_func_q3rd:4. kvantilis`]
  ];

  seriesNameTypes: string[][] = [
    [StatTimeSeriesName.Timestamp, $localize `:@@stat_timeseries_series_name_type_timestamp:időpont`],
    [StatTimeSeriesName.Sequence, $localize `:@@stat_timeseries_series_name_type_sequence:szekvencia`],
    [StatTimeSeriesName.SeparatorEvent, $localize `:@@stat_timeseries_series_name_type_sepaarator_event:elválasztó`]
  ];

  labels = Labels.analysis;

  eventOps: string[][] = [];

  access = {
    canUpdate: false
  }

  devices: Device[] = [];

  constructor(
    private apiService: ApiService,
    private authService: AuthenticationService
  )
  {
    this.access.canUpdate = authService.hasPrivilige("patch/stat/def/{id}", "patch any");
    this.eventOps = apiService.getEventOperations();
    apiService.getDevices()
      .subscribe(d => {
        this.devices = d;
      });
  }

  ngOnInit(): void {
    if (!this.def)
      this.def = {
        before: undefined,
        after: undefined,
        duration: undefined,
        filter: [],
        metric: undefined,
        agg_func: StatTimeSeriesAggFunc.Avg,
        agg_sep: undefined,
        series_sep: undefined,
        series_name: StatTimeSeriesName.Timestamp,
        xaxis: undefined,
        visualsettings: undefined
      };
    else {
      this.filters$.next((this.def.filter ?? []).map(f => {
        let filter: StatTimesSeriesFilterEx = Object.assign({}, f);
        const meta = this.metaList.find(m => m.device === f.device && m.data_id === f.data_id);
        if (meta)
          filter.valueList = meta.value_list;
        return filter;
      }));
    }
    this.setDefualtVisualSettings();
  }

  setDefualtVisualSettings() {
    var defaults: StatVisualSettingsChart = {
      title: "",
      subtitle: "",
      legend: {
        align: StatVisualSettingsChartLegendAlign.Center,
        position: StatVisualSettingsChartLegendPosition.Top
      },
      xaxis: {
        caption: ""
      },
      yaxis: {
        caption: ""
      },
      tooltip: {
        html: ""
      }
    };

    if (!this.def.visualsettings)
      this.def.visualsettings = defaults;
    else
      this.def.visualsettings = Object.assign(defaults, this.def.visualsettings);
  }

  getDef(): StatDefBase {
    var pDef = this.period.getDef();
    console.log(pDef);
    this.def.after = pDef.after;
    this.def.before = pDef.before;
    this.def.duration = pDef.duration;
    this.def.filter = this.filters$.value.slice(0);
    this.def.agg_func = (this.def.agg_func ?? "") === "" ? undefined : this.def.agg_func;
    this.def.metric = this.handleEmptyMeta(this.def.metric);
    this.def.agg_sep = this.handleEmptyMeta(this.def.agg_sep);
    this.def.series_sep = this.handleEmptyMeta(this.def.series_sep);
    return this.def;
  }

  handleEmptyMeta(meta: Meta): Meta {
    if (!meta)
      return undefined;

    for (let prop of ["device", "data_id"])
      if ((meta[prop] ?? undefined) === undefined) {
          return undefined;
      }
    return meta;
  }

  newFilter() {
    var filters = this.filters$.value;
    filters.push({
      id: ((filters ?? []).length === 0 ? 0 : Math.max(...filters.map(f => f.id))) + 1,
      device: undefined,
      data_id: undefined,
      rel: undefined,
      value: undefined,
      age_max: undefined,
      age_min: undefined
    });
    this.filters$.next(filters);
  }

  updateFilterId(meta: Meta, filter: StatTimesSeriesFilterEx) {
    filter.data_id = meta.data_id;
    filter.device = meta.device;
    filter.valueList = meta.value_list;
  }

  deleteFilter(filter: StatTimesSeriesFilterEx) {
    var filters = this.filters$.value;
    var idx = filters.findIndex((f) => { return f.data_id === filter.data_id && f.device === filter.device });
    if (idx > -1)
      filters.splice(idx, 1);
    this.filters$.next(filters);
  }

  setDevice(device: DeviceType, meta: string) {
    if (!this.def[meta])
    this.def[meta] = { device: undefined, data_id: undefined };
    this.def[meta].device = device;
  }

  selectMetric(meta: Meta) {
    this.def.metric = {
      data_id: meta.data_id,
      device: meta.device
    };
  }

  selectAggSep(meta: Meta) {
    this.def.agg_sep = {
      data_id: meta.data_id,
      device: meta.device
    };
  }

  selectSeriesSep(meta: Meta) {
    this.def.series_sep = {
      data_id: meta.data_id,
      device: meta.device
    };
  }

  getChartConfiguration(data: StatData): ChartConfiguration {
    var startColor: HSLAColor = new HSLAColor(240, 0.17, 0.76, 1);
    var endColor: HSLAColor = new HSLAColor(240, 0.82, 0.11 , 1);
    var relativeChart = data.timeseriesdata.length > 1;
    var xaxisPropName = "x_" + (!relativeChart ? "timestamp" : "relative");
    var xyChart = !(data.stat_def.timeseriesdef.xaxis === 'sequence');

    var options: ChartConfiguration = {
      type: 'line',
      data: {
        datasets: data.timeseriesdata.map((series, seriesIndex, seriesList) => {
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
            backgroundColor: AnalysisHelpers.getChartSeriesColor(seriesIndex, seriesList.length, startColor, endColor, 1).toString(),
            borderColor: AnalysisHelpers.getChartSeriesColor(seriesIndex, seriesList.length, startColor, endColor, 1).toString(),
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
          title: AnalysisHelpers.setChartTitle(data.stat_def.timeseriesdef.visualsettings?.title),
          subtitle: AnalysisHelpers.setChartTitle(data.stat_def.timeseriesdef.visualsettings?.subtitle),
          legend: {
            display:  data.timeseriesdata.length > 1,
            align: data.stat_def.timeseriesdef.visualsettings?.legend?.align ?? 'center',
            position: data.stat_def.timeseriesdef.visualsettings?.legend?.position ?? 'right'
          }
        },
        scales: {
          y: {
            title: AnalysisHelpers.setChartTitle(data.stat_def.timeseriesdef.visualsettings?.yaxis?.caption)
          },
          x: {
            type: xyChart ? 'time' : 'linear',
            title: AnalysisHelpers.setChartTitle(data.stat_def.timeseriesdef.visualsettings?.xaxis?.caption),
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
    return options;
  }
}
