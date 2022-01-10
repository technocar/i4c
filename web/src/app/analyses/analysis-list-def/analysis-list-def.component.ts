import { Component, Input, OnInit, ViewChild } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { NumberRelation, StatData, StatListDef, StatListVisualSettings, StatListVisualSettingsCol, StatXYDef, StatXYFilter, StatXYMeta, StatXYMetaObjectField, StatXYObjectType } from 'src/app/services/models/api';
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
  selectableColumns$: BehaviorSubject<[string, string][]> = new BehaviorSubject([]);
  columns$: BehaviorSubject<StatListVisualSettingsCol[]> = new BehaviorSubject([]);
  operators: NumberRelation[] = [
    NumberRelation.Equal,
    NumberRelation.NotEqual,
    NumberRelation.Lesser,
    NumberRelation.LesserEqual,
    NumberRelation.Greater,
    NumberRelation.GreaterEqual
  ];
  labels = Labels.analysis;
  defaultColors = {
    even_bg: '#ffffff',
    even_fg: '#000000',
    header_bg: '#ffffff',
    header_fg: '#000000',
    normal_bg: '#dee2e6',
    normal_fg: '#000000'
  }

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
      even_bg: this.defaultColors.even_bg,
      even_fg: this.defaultColors.even_fg,
      header_bg: this.defaultColors.header_bg,
      header_fg: this.defaultColors.header_fg,
      normal_bg: this.defaultColors.normal_bg,
      normal_fg: this.defaultColors.normal_fg
    };

    if (!this.def.visualsettings)
      this.def.visualsettings = defaults;
    else {
      for (let color in this.defaultColors)
        if (!this.def.visualsettings[color])
          this.def.visualsettings[color] = this.defaultColors[color];
      this.def.visualsettings = Object.assign(defaults, this.def.visualsettings);
    }

    this.columns$.next(this.def.visualsettings.cols);
  }

  getDef(): StatListDef {
    var pDef = this.period.getDef();
    var def = Object.assign({}, this.def);
    console.log(pDef);
    def.after = pDef.after;
    def.before = pDef.before;
    def.duration = pDef.duration;
    def.filter = this.filters$.value.slice(0);
    for (let color in this.defaultColors)
      if (this.defaultColors[color] === def.visualsettings[color])
        def.visualsettings[color] = undefined;
    def.visualsettings.cols = this.columns$.value;
    return def;
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
      this.collectSelectableColumns();
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

  collectSelectableColumns() {
    var fields = this.objects$.value.find(o => o.name === this.def.obj.type)?.fields;
    var columns = fields.filter(f =>
      this.columns$.value.find(c => c.field === f.name) === undefined
    ).map(f => {
      return <[string, string]>[f.name, f.displayname]
    });

    this.selectableColumns$.next(columns);
  }

  addColumn(columnName: string) {
    var column = this.selectableColumns$.value.find(c => c[0] === columnName);
    if (!column)
      return;

    this.columns$.value.push({
      field: column[0],
      caption: column[1],
      width: undefined
    });

    this.collectSelectableColumns();
  }

  columnTrackBy(index, column: StatListVisualSettingsCol) {
    return column.field;
  }

  deleteColumn(columnName: string) {
    var columns = this.columns$.value;
    var idx = columns.findIndex(c => c.field === columnName);
    if (idx === -1)
      return;

    columns.splice(idx, 1);
    this.columns$.next(columns);
    this.collectSelectableColumns();
  }

  buildTable(result: StatData): HTMLTableElement {
    var table: HTMLTableElement = document.createElement('table');
    var thead = document.createElement('thead');
    var tr: HTMLTableRowElement = document.createElement('tr');

    table.classList.add('table');
    tr.style.backgroundColor = this.def.visualsettings.header_bg;
    tr.style.color = this.def.visualsettings.header_fg;

    for (let header of this.def.visualsettings.cols) {
      let th = document.createElement('th');
      th.textContent = header.caption;
      th.setAttribute("column-name", header.field);
      if (header.width)
        th.style.width = `${header.width}%`;
      tr.append(th);
    }
    thead.append(tr);
    table.append(thead);

    if (!result || !result.listdata)
      return table;

    let tbody = document.createElement('tbody');
    let container = document.createDocumentFragment();
    let rowIdx = 0;
    for (let row of result.listdata) {
      tr = document.createElement('tr');
      if (rowIdx % 2 === 0) {
        tr.style.backgroundColor = this.def.visualsettings.even_bg;
        tr.style.color = this.def.visualsettings.even_fg;
      } else {
        tr.style.backgroundColor = this.def.visualsettings.normal_bg;
        tr.style.color = this.def.visualsettings.normal_fg;
      }
      for (let header of this.def.visualsettings.cols) {
        let td = document.createElement('td');
        if (row[header.field])
          td.innerText = row[header.field];

        tr.append(td);
      }
      container.append(tr);
    }
    tbody.append(container);
    table.append(tbody);

    return table;
  }
}
