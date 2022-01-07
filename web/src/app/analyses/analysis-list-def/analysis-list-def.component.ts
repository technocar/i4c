import { Component, Input, OnInit, ViewChild } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { NumberRelation, StatListDef, StatListVisualSettings, StatXYDef, StatXYFilter, StatXYMeta, StatXYMetaObjectField, StatXYObjectType } from 'src/app/services/models/api';
import { Labels } from 'src/app/services/models/constants';
import { AnalysisDef } from '../analyses.component';
import { AnalysisDatetimeDefComponent } from '../defs/analysis-datetime-def/analysis-datetime-def.component';

interface Filter extends StatXYFilter {
  _id: number,
  values: string[]
}

@Component({
  selector: 'app-analysis-list-def',
  templateUrl: './analysis-list-def.component.html',
  styleUrls: ['./analysis-list-def.component.scss']
})
export class AnalysisListDefComponent implements OnInit, AnalysisDef {

  @Input("def") def: StatListDef;
  @ViewChild('period') period: AnalysisDatetimeDefComponent;

  objects$: BehaviorSubject<StatXYMeta[]> = new BehaviorSubject([]);
  fields$: BehaviorSubject<StatXYMetaObjectField[]> = new BehaviorSubject([]);
  filters$: BehaviorSubject<Filter[]> = new BehaviorSubject([]);
  operators: NumberRelation[] = [
    NumberRelation.Equal,
    NumberRelation.NotEqual,
    NumberRelation.Lesser,
    NumberRelation.LesserEqual,
    NumberRelation.Greater,
    NumberRelation.GreaterEqual
  ];
  labels = Labels.analysis;

  constructor(private apiService: ApiService) { }

  ngOnInit(): void {
    if (!this.def)
      this.def = {
        before: undefined,
        after: undefined,
        duration: undefined,
        filter: [],
        obj: undefined,
        orderby: [],
        visualsettings: undefined
      };

    this.setDefualtVisualSettings();
    this.getMeta();
  }

  setDefualtVisualSettings() {
    var defaults: StatListVisualSettings = {
      title: "",
      subtitle: "",
      cols: [],
      even_bg: undefined,
      even_fg: undefined,
      header_bg: undefined,
      header_fg: undefined,
      normal_bg: undefined,
      normal_fg: undefined
    };

    if (!this.def.visualsettings)
      this.def.visualsettings = defaults;
    else
      this.def.visualsettings = Object.assign(defaults, this.def.visualsettings);
  }

  getDef(): StatListDef {
    var pDef = this.period.getDef();
    console.log(pDef);
    this.def.after = pDef.after;
    this.def.before = pDef.before;
    this.def.duration = pDef.duration;
    this.def.filter = this.filters$.value.slice(0);
    return this.def;
  }

  getMeta() {
    this.apiService.getStatXYMeta(undefined).subscribe(meta => {
      this.objects$.next(meta);
      var filters = (this.def.filter ?? []).map((f, i) => {
        var result: Filter = {
          _id: i,
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

  deleteFilter(filter: Filter) {
    var filters = this.filters$.value;
    var idx = filters.findIndex((f) => f._id === filter._id);
    if (idx > -1)
      filters.splice(idx, 1);

    this.filters$.next(filters);
  }

  newFilter() {
    var filters = this.filters$.value;
    filters.push({
      _id: ((filters ?? []).length === 0 ? 0 : Math.max(...filters.map(f => f._id))) + 1,
      id: null,
      field: undefined,
      rel: NumberRelation.Equal,
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

  getFieldValues(name: string): string[] {
    var field = this.fields$.value.find((f) => f.name === name);
    if (field)
      return field.value_list ?? [];
    else
      return [];
  }

}
