import { Component, Input, OnInit, ViewChild } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { StatTimeSeriesAggFunc, Meta, StatDefBase, StatTimeSeriesDef, StatTimesSeriesFilter, StatTimeSeriesName, StatVisualSettingsLegendAlign, StatVisualSettingsLegendPosition } from 'src/app/services/models/api';
import { Labels } from 'src/app/services/models/constants';
import { AanalysisDef } from '../../analyses.component';
import { AnalysisDatetimeDefComponent } from '../analysis-datetime-def/analysis-datetime-def.component';

@Component({
  selector: 'app-analysis-timeseries-def',
  templateUrl: './analysis-timeseries-def.component.html',
  styleUrls: ['./analysis-timeseries-def.component.scss']
})
export class AnalysisTimeseriesDefComponent implements OnInit, AanalysisDef {

  @Input("def") def: StatTimeSeriesDef;
  @Input("metaList") metaList: Meta[];
  @ViewChild('period') period: AnalysisDatetimeDefComponent;


  filters$: BehaviorSubject<StatTimesSeriesFilter[]> = new BehaviorSubject([]);

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

  constructor(private apiService: ApiService)
  {
    this.eventOps = apiService.getEventOperations();
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
      this.filters$.next(this.def.filter ?? []);
    }
    this.setDefualtVisualSettings();
  }

  setDefualtVisualSettings() {
    var defaults = {
      title: "",
      subtitle: "",
      legend: {
        align: StatVisualSettingsLegendAlign.Center,
        position: StatVisualSettingsLegendPosition.Top
      },
      xaxis: {
        caption: ""
      },
      yaxis: {
        caption: ""
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
    return this.def;
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

  updateFilterId(meta: Meta, filter: StatTimesSeriesFilter) {
    filter.data_id = meta.data_id;
    filter.device = meta.device;
  }

  deleteFilter(filter: StatTimesSeriesFilter) {
    var filters = this.filters$.value;
    var idx = filters.findIndex((f) => { return f.data_id === filter.data_id && f.device === filter.device });
    if (idx > -1)
      filters.splice(idx, 1);
    this.filters$.next(filters);
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
}
