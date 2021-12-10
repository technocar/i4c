import { Component, Input, OnInit, ViewChild } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { StatVisualSettingsLegendAlign, StatVisualSettingsLegendPosition, StatXYDef, StatXYFilter, StatXYFilterRel, StatXYMeta, StatXYMetaObject, StatXYMetaObjectField, StatXYObjectType } from 'src/app/services/models/api';
import { Labels } from 'src/app/services/models/constants';
import { AanalysisDef } from '../../analyses.component';
import { AnalysisDatetimeDefComponent } from '../analysis-datetime-def/analysis-datetime-def.component';

interface Filter extends StatXYFilter {
  values: string[]
}

@Component({
  selector: 'app-analysis-xy-def',
  templateUrl: './analysis-xy-def.component.html',
  styleUrls: ['./analysis-xy-def.component.scss']
})
export class AnalysisXyDefComponent implements OnInit, AanalysisDef {

  @Input("def") def: StatXYDef;
  @Input("xymeta") xymeta: StatXYMeta;
  @ViewChild('period') period: AnalysisDatetimeDefComponent;

  objects$: BehaviorSubject<StatXYMetaObject[]> = new BehaviorSubject([]);
  fields$: BehaviorSubject<StatXYMetaObjectField[]> = new BehaviorSubject([]);
  filters$: BehaviorSubject<Filter[]> = new BehaviorSubject([]);
  operators: StatXYFilterRel[] = [
    StatXYFilterRel.Equal,
    StatXYFilterRel.NotEqual,
    StatXYFilterRel.Lesser,
    StatXYFilterRel.LesserEqual,
    StatXYFilterRel.Greater,
    StatXYFilterRel.GreaterEqual
  ];

  labels = Labels.analysis;

  constructor(
    private apiService: ApiService
  )
  { }

  getDef(): StatXYDef {
    var pDef = this.period.getDef();
    console.log(pDef);
    this.def.after = pDef.after;
    this.def.before = pDef.before;
    this.def.duration = pDef.duration;
    this.def.filter = this.filters$.value.slice(0);
    return this.def;
  }

  ngOnInit(): void {
    if (!this.def)
      this.def = {
        before: undefined,
        after: undefined,
        duration: undefined,
        filter: [],
        color: undefined,
        obj: undefined,
        other: [],
        shape: undefined,
        x: undefined,
        y: undefined,
        visualsettings: undefined
      };

    this.setDefualtVisualSettings();

    this.getMeta();
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

  getMeta() {
    this.apiService.getStatXYMeta(undefined).subscribe(meta => {
      this.objects$.next(meta.objects);
      var filters = (this.def.filter ?? []).map((f) => {
        var result: Filter = {
          id: f.id,
          rel: f.rel,
          value: f.value,
          field: f.field,
          values: this.getFieldValues(f.field)
        }
        return result;
      });
      this.filters$.next(filters);
      if (!this.def.obj) {
        if ((this.objects$.value ?? []).length > 0)
          this.objectChanged(this.objects$.value[0].name);
      } else {
        this.objectChanged(this.def.obj.type, true);
      }
    });
  }

  objectChanged(type: string, noInteractive: boolean = false) {
    var obj = this.objects$.value.filter((o) => o.name === type);
    if (!noInteractive) {
      this.def.obj = {
        type: type as StatXYObjectType,
        params: []
      };
    }
    this.fields$.next(obj.length > 0 ? obj[0].fields : []);
  }

  deleteFilter(filter: StatXYFilter) {
    var filters = this.filters$.value;
    var idx = filters.findIndex((f) => f.id === filter.id);
    if (idx > -1)
      filters.splice(idx, 1);

    this.filters$.next(filters);
  }

  newFilter() {
    var filters = this.filters$.value;
    filters.push({
      id: ((filters ?? []).length === 0 ? 0 : Math.max(...filters.map(f => f.id))) + 1,
      field: undefined,
      rel: StatXYFilterRel.Equal,
      value: '',
      values: []
    });
    this.filters$.next(filters);
  }

  updateFilterField(filter: Filter) {
    var metaField = this.fields$.value.find((f) => f.name === filter.field);
    if (metaField) {
      filter.values = metaField.value_list;
    }
  }

  getFieldValues(id: string): string[] {
    var field = this.fields$.value.find((f) => f.name === id);
    if (field)
      return field.value_list ?? [];
    else
      return [];
  }
}
