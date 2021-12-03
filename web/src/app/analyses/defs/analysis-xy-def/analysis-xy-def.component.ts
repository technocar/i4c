import { Component, Input, OnInit, ViewChild } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { StatXYDef, StatXYField, StatXYFilter, StatXYFilterRel, StatXYMeta, StatXYMetaObject, StatXYMetaObjectField } from 'src/app/services/models/api';
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
export class AnalysisXyDefComponent implements OnInit {

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

  ngOnInit(): void {
    this.getMeta();
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
  }

  getMeta() {
    this.apiService.getStatXYMeta(undefined).subscribe(meta => {
      this.objects$.next(meta.objects);
    });
  }

  objectChanged() {
    var obj = this.objects$.value.filter((o) => o.name === this.def.obj.type);
    this.fields$.next(obj.length > 0 ? obj[0].fields : []);
  }

  deleteFilter(filter: StatXYFilter) {
    var filters = this.filters$.value;
    var idx = filters.findIndex((f) => f.id === filter.id);
    if (idx > -1)
      this.def.filter.splice(idx, 1);

    this.filters$.next(filters);
  }

  newFilter() {
    var filters = this.filters$.value;
    filters.push({
      id: Math.max(...filters.map(f => f.id)) + 1,
      field: { field_name: "", values: [] },
      rel: StatXYFilterRel.Equal,
      value: undefined
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
      return field.value_list;
    else
      return [];
  }
}
