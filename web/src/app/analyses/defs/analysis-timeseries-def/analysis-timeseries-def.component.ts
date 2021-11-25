import { Component, Input, OnInit, ViewChild } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { MetaFilterComponent, MetricFilterModel } from 'src/app/commons/meta-filter/meta-filter.component';
import { Meta, StatDefBase } from 'src/app/services/models/api';
import { AanalysisDef } from '../../analyses.component';

@Component({
  selector: 'app-analysis-timeseries-def',
  templateUrl: './analysis-timeseries-def.component.html',
  styleUrls: ['./analysis-timeseries-def.component.scss']
})
export class AnalysisTimeseriesDefComponent implements OnInit, AanalysisDef {

  @Input("metaList") metaList: Meta[];
  @ViewChild("metaFilter") metaFilter: MetaFilterComponent;

  private _selectedFilter: MetricFilterModel;

  filters$: BehaviorSubject<MetricFilterModel[]> = new BehaviorSubject([]);

  constructor() { }

  ngOnInit(): void {
  }

  getDef(): StatDefBase {
    throw new Error('Method not implemented.');
  }

  newFilter() {
    this.metaFilter.show();
  }

  saveFilter(metric: MetricFilterModel) {
    if (this._selectedFilter) {
      this._selectedFilter.relation = metric.relation;
      this._selectedFilter.value = metric.value;
    } else {
      let filters = this.filters$.value ?? [];
      let hasFilter = filters.find((f) => { return f.metricId === metric.metricId && f.metricType === metric.metricType }) ? true : false;
      if (hasFilter) {
        this.metaFilter.showError($localize `:@@analysis_filter_duplicated:Már van ilyen szűrő kiválasztva!`);
        return;
      }
      filters.push(metric);
      this.filters$.next(filters);
    }
  }

  updateFilter(filter: MetricFilterModel) {
    this._selectedFilter = filter;
    this.metaFilter.show(filter, true);
  }
}
