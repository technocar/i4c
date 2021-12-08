import { Component, Input, OnInit, ViewChild } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { StatDefBase, StatXYDef, StatXYField, StatXYFilter, StatXYFilterRel, StatXYMeta, StatXYMetaObject, StatXYMetaObjectField, StatXYObjectType, StatXYParam } from 'src/app/services/models/api';
import { AanalysisDef } from '../../analyses.component';
import { AnalysisDatetimeDefComponent } from '../analysis-datetime-def/analysis-datetime-def.component';

interface FilterField extends StatXYField {
  values: string[]
}

interface Filter extends StatXYFilter {
  field: FilterField
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

  constructor(
    private apiService: ApiService
  )
  { }

  getDef(): StatXYDef {
    this.def.filter = this.filters$.value;
    return this.def;
  }

  ngOnInit(): void {
    if (!this.def)
      this.def = {
        before: undefined,
        after: undefined,
        duration: undefined,
        filter: [],
        color: { field_name: '' },
        obj: undefined,
        other: [],
        shape: { field_name: '' },
        x: { field_name: '' },
        y: { field_name: '' },
        visualsettings: undefined
      };
    else {
    }
    this.getMeta();
  }

  getMeta() {
    this.apiService.getStatXYMeta(undefined).subscribe(meta => {
      this.objects$.next(meta.objects);
      var filters = (this.def.filter ?? []).map((f) => {
        var result: Filter = {
          id: f.id,
          rel: f.rel,
          value: f.value,
          field: {
            field_name: f.field.field_name,
            values: this.getFieldValues(f.field.field_name)
          }
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
      field: { field_name: "", values: [] },
      rel: StatXYFilterRel.Equal,
      value: ''
    });
    this.filters$.next(filters);
  }

  updateFilterField(filter: Filter) {
    var metaField = this.fields$.value.find((f) => f.name === filter.field.field_name);
    if (metaField) {
      filter.field.values = metaField.value_list;
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
