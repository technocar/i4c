import { Component, Input, OnInit, ViewChild } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { MetaFilterComponent, MetaFilterMode, MetricFilterModel } from 'src/app/commons/meta-filter/meta-filter.component';
import { ApiService } from 'src/app/services/api.service';
import { AggFunc, Meta, StatDefBase, StatTimeSeriesData, StatTimeSeriesDef, StatTimesSeriesFilter } from 'src/app/services/models/api';
import { AanalysisDef } from '../../analyses.component';

@Component({
  selector: 'app-analysis-timeseries-def',
  templateUrl: './analysis-timeseries-def.component.html',
  styleUrls: ['./analysis-timeseries-def.component.scss']
})
export class AnalysisTimeseriesDefComponent implements OnInit, AanalysisDef {

  @Input("def") def: StatTimeSeriesDef;
  @Input("metaList") metaList: Meta[];
  @ViewChild("metaFilter") metaFilter: MetaFilterComponent;
  @ViewChild("metricSelector") metricSelector: MetaFilterComponent;

  private _selectedFilter: StatTimesSeriesFilter;
  private _metricSelectorMode: string;

  filters$: BehaviorSubject<StatTimesSeriesFilter[]> = new BehaviorSubject([]);

  aggFuncs: string[][] = [
    [AggFunc.Avg, $localize `:@@agg_func_avg:átlag`],
    [AggFunc.Median, $localize `:@@agg_func_median:median`],
    [AggFunc.Min, $localize `:@@agg_func_min:min`],
    [AggFunc.Max, $localize `:@@agg_func_max:max`],
    [AggFunc.FirstQuartile, $localize `:@@agg_func_q1st:1. kvantilis`],
    [AggFunc.ThirdQuartile, $localize `:@@agg_func_q3rd:3. kvantilis`]
  ];

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
        agg_func: AggFunc.Avg,
        agg_sep: undefined,
        series_sep: undefined,
        xaxis: undefined,
        visualsettings: {
          subtitle: "",
          title: ""
        }
      };

  }

  getDef(): StatDefBase {
    throw new Error('Method not implemented.');
  }

  newFilter() {
    var filters = this.filters$.value;
    filters.push({
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

  showMetricSelector(mode: string) {
    this._metricSelectorMode = mode;
    this.metricSelector.selectableTypes = mode == "metric" ? ["EVENT"] : ["SAMPLE"];
    this.metricSelector.show();
  }

  selectMetric(metric: MetricFilterModel) {
    switch (this._metricSelectorMode) {
      case "metric":
        this.def.metric = { data_id: metric.metricId, name: metric.metricName, device: metric.device };
        break;
      case "agg_sep":
        this.def.agg_sep = { data_id: metric.metricId, name: metric.metricName, device: metric.device };
        break;
      case "separator_sep":
        this.def.agg_sep = { data_id: metric.metricId, name: metric.metricName, device: metric.device };
        break;
    }
  }
}
