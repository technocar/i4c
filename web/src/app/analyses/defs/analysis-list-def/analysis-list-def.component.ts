import { Component, Input, OnInit, ViewChild } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { AuthenticationService } from 'src/app/services/auth.service';
import { NumberRelation, StatData, StatListDef, StatListVisualSettings, StatListVisualSettingsCol, StatXYDef, StatXYFilter, StatXYMeta, StatXYMetaObjectField, StatXYObjectType } from 'src/app/services/models/api';
import { Labels } from 'src/app/services/models/constants';
import { AnalysisDef } from '../../analyses.component';
import { AnalysisDatetimeDefComponent } from '../analysis-datetime-def/analysis-datetime-def.component';

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
    normal_bg: '#ffffff',
    normal_fg: '#000000'
  };
  colors = Object.assign({}, this.defaultColors);
  access = {
    canUpdate: false
  }

  constructor(
    private apiService: ApiService,
    private authService: AuthenticationService
  ) {
    this.access.canUpdate = authService.hasPrivilige("patch/stat/def/{id}", "patch any");
  }

  ngOnInit(): void {
    if (!this.def)
      this.def = {
        before: undefined,
        after: undefined,
        duration: undefined,
        filter: [],
        obj: undefined,
        order_by: [],
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
    else {
      this.def.visualsettings = Object.assign(defaults, this.def.visualsettings);
      for (let color in this.colors)
        if (this.def.visualsettings[color])
          this.colors[color] = this.def.visualsettings[color];
    }

    this.columns$.next(this.def.visualsettings.cols);
  }

  getDef(): StatListDef {
    var pDef = this.period.getDef();
    console.log(pDef);
    this.def.after = pDef.after;
    this.def.before = pDef.before;
    this.def.duration = pDef.duration;
    this.def.filter = this.filters$.value.slice(0);
    for (let color in this.defaultColors)
      if (this.defaultColors[color] === this.colors[color])
        this.def.visualsettings[color] = undefined;
      else
      this.def.visualsettings[color] = this.colors[color];
    this.def.visualsettings.cols = this.columns$.value;
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

  validField(selection: string): boolean {
    if (selection ?? "" === "")
      return true;
    else
      return this.fields$.value.findIndex(f => f.name === selection) > -1;
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

  setOrder(field: string, direction: string, multi: boolean) {
    if ((this.def.order_by ?? undefined) === undefined || !multi)
          this.def.order_by = [];

    let idx = this.def.order_by.findIndex(o => o.field === field);
    if (idx > -1 && direction === undefined)
      this.def.order_by.splice(idx, 1);
    else if (idx > -1)
      this.def.order_by[idx].ascending = direction === "asc";
    else if (direction !== undefined) {
      this.def.order_by.push({
        ascending: direction === "asc",
        field: field
      });
    }
  }

  buildTable(result: StatData): HTMLTableElement {
    var table: HTMLTableElement = document.createElement('table');
    var thead = document.createElement('thead');
    var tr: HTMLTableRowElement;

    function createTitle(text: string, type: string, cols: number) {
      if ((text ?? undefined) === undefined)
        return;

      tr = document.createElement('tr');
      tr.classList.add(type);
      tr.style.textAlign = "center";
      if (type === "subtitle") {
        tr.style.color = "#aaaaaa";
        tr.style.fontSize = "smaller";
      }
      let th = document.createElement('th');
      th.colSpan = cols;
      if (th.colSpan === 0)
        th.colSpan = 1;
      th.innerText = text;
      th.style.padding = "0.75rem";
      th.style.borderBottom = "none";
      th.style.borderTop = "none";
      tr.append(th);
      thead.append(tr);
    }

    table.id = "result";
    //table.classList.add('table');
    table.style.borderCollapse = "collapse";
    table.style.textAlign = "left";
    table.style.width = "100%";

    createTitle(this.def.visualsettings.title, "title", this.def.visualsettings.cols?.length);
    createTitle(this.def.visualsettings.subtitle, "subtitle", this.def.visualsettings.cols?.length);

    tr = document.createElement('tr');
    tr.style.backgroundColor = this.def.visualsettings.header_bg;
    tr.setAttribute("color-bg", this.def.visualsettings.header_bg ?? "");
    tr.style.color = this.def.visualsettings.header_fg;
    tr.setAttribute("color-fg", this.def.visualsettings.header_fg ?? "");
    tr.style.borderTop = "2px solid #dee2e6";
    tr.style.borderBottom = "2px solid #dee2e6";
    for (let header of this.def.visualsettings.cols) {
      let th = document.createElement('th');
      th.textContent = header.caption ?? header.field;
      th.setAttribute("column-name", header.field);
      let order = (this.def.order_by ?? []).find(o => o.field === header.field);
      if (order)
        th.setAttribute("order-direction", order.ascending ? "asc" : "desc");
      if (header.width)
        th.style.width = `${header.width}%`;
      th.style.padding = "0.75rem";
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
      tr.style.borderTop = "1px solid #dee2e6";
      if (rowIdx % 2 === 0) {
        tr.style.backgroundColor = this.def.visualsettings.even_bg;
        tr.setAttribute("color-bg", this.def.visualsettings.even_bg ?? "");
        tr.style.color = this.def.visualsettings.even_fg;
        tr.setAttribute("color-fg", this.def.visualsettings.even_fg ?? "");
      } else {
        tr.style.backgroundColor = this.def.visualsettings.normal_bg;
        tr.setAttribute("color-bg", this.def.visualsettings.normal_bg ?? "");
        tr.style.color = this.def.visualsettings.normal_fg;
        tr.setAttribute("color-fg", this.def.visualsettings.normal_fg ?? "");
      }
      for (let header of this.def.visualsettings.cols) {
        let td = document.createElement('td');
        if (row[header.field])
          td.innerText = row[header.field];
        td.style.padding = "0.75rem";

        tr.append(td);
      }
      container.append(tr);
      rowIdx++;
    }
    tbody.append(container);
    table.append(tbody);

    return table;
  }
}
