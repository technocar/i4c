import { AfterViewInit, Component, Input, OnInit, ViewChild } from '@angular/core';
import { EditorComponent } from '@tinymce/tinymce-angular';
import { ChartConfiguration } from 'chart.js';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { AuthenticationService } from 'src/app/services/auth.service';
import { StatData, StatVisualSettingsChart, StatVisualSettingsChartLegendAlign, StatVisualSettingsChartLegendPosition, StatXYDef, StatXYFilter, NumberRelation, StatXYMeta, StatXYMetaObjectField, StatXYObjectType, StatXYOther, StatMetaObjectFieldType, StatXYMetaObjectFieldUnit, StatXYParam, StatXYMetaObjectParam } from 'src/app/services/models/api';
import { Labels } from 'src/app/services/models/constants';
import { AnalysisChart, AnalysisDef } from '../../analyses.component';
import { AnalysisHelpers } from '../../helpers';
import { AnalysisDatetimeDefComponent } from '../analysis-datetime-def/analysis-datetime-def.component';

interface Filter extends StatXYFilter {
  _id: number,
  _type: string,
  values: string[]
}

interface Other {
  id: number,
  field_name: string
}

interface ObjParam extends StatXYMetaObjectParam {
  value: string
}

@Component({
  selector: 'app-analysis-xy-def',
  templateUrl: './analysis-xy-def.component.html',
  styleUrls: ['./analysis-xy-def.component.scss']
})
export class AnalysisXyDefComponent implements OnInit, AfterViewInit, AnalysisDef, AnalysisChart {

  @Input("def") def: StatXYDef;
  @Input("xymeta") xymeta: StatXYMeta;
  @ViewChild('period') period: AnalysisDatetimeDefComponent;
  @ViewChild('editor') editor: EditorComponent;

  objects$: BehaviorSubject<StatXYMeta[]> = new BehaviorSubject([]);
  fields$: BehaviorSubject<StatXYMetaObjectField[]> = new BehaviorSubject([]);
  numFields$: BehaviorSubject<StatXYMetaObjectField[]> = new BehaviorSubject([]);
  filters$: BehaviorSubject<Filter[]> = new BehaviorSubject([]);
  others$: BehaviorSubject<Other[]> = new BehaviorSubject([]);
  params$: BehaviorSubject<ObjParam[]> = new BehaviorSubject([]);
  operators: NumberRelation[] = [
    NumberRelation.Equal,
    NumberRelation.NotEqual,
    NumberRelation.Lesser,
    NumberRelation.LesserEqual,
    NumberRelation.Greater,
    NumberRelation.GreaterEqual
  ];

  labels = Labels.analysis;
  _defaultTooltip = '<p>X: <span class="graphdata" contenteditable="false" spellcheck="false" id="1">{{X}}</span>  </p><p>Y: <span class="graphdata" contenteditable="false" spellcheck="false" id="2">{{Y}}</span></p>';

  access = {
    canUpdate: false
  }

  quillEvents = {
    enter: {
      key: 13,
      handler: function(range, context) {
        console.log(range, context);
        this.quill.insertText(range.index, '\n');
      }
    }
  }

  editorConfig: Record<string, any>;

  constructor(
    private apiService: ApiService,
    private authService: AuthenticationService
  )
  {
    this.access.canUpdate = authService.hasPrivilige("patch/stat/def/{id}", "patch any");

    this.editorConfig = {
      base_url: '/tinymce',
      suffix: '.min',
      selector: 'textarea',
      plugins: 'noneditable',
      toolbar: 'forecolor backcolor | bold italic underline | data',
      content_css: '/assets/tinymce.css',
      setup: (ctx) => {
        var nonEditableClass = "graphdata";
        // Register a event before certain commands run that will turn contenteditable off temporarilly on noneditable fields
        ctx.on('BeforeExecCommand', function (e) {
          // The commands we want to permit formatting noneditable items for
          var textFormatCommands = [
            'mceToggleFormat',
            'mceApplyTextcolor',
            'mceRemoveTextcolor'
          ];
          if (textFormatCommands.indexOf(e.command) !== -1) {
            // Find all elements in the editor body that have the noneditable class on them
            //  and turn contenteditable off
            var elements = (ctx.getBody() as HTMLElement).querySelectorAll('.' + nonEditableClass);
            elements.forEach(e => e.removeAttribute("contenteditable"));
            console.log(ctx.getBody());
          }
        });
        // Turn the contenteditable attribute back to false after the command has executed
        ctx.on('FormatApply', function (e) {
          // Find all elements in the editor body that have the noneditable class on them
          //  and turn contenteditable back to false
          var elements = (ctx.getBody() as HTMLElement).querySelectorAll('.' + nonEditableClass);
          elements.forEach(e => e.setAttribute("contenteditable", "false"));
          console.log(elements);
        });

        var others$ = this.others$;
        var fields$ = this.fields$;
        ctx.ui.registry.addMenuButton('data', {
          text: 'adatok',
          fetch: function (callback) {
            var items = [
              { id: 'X',  name: 'X' },
              { id: 'Y',  name: 'Y' },
              { id: 'shape',  name: 'forma' },
              { id: 'color',  name: 'szín' }
            ];
            others$.value.forEach(o =>
              items.push({
                id: o.field_name,
                name: (fields$.value.find(f => f.name === o.field_name) ?? {
                  name: o.field_name,
                  displayname: o.field_name
                }).displayname
              })
            );
            var menuItems = [];
            items.forEach(i => {
              menuItems.push({
                type: 'menuitem',
                text: i.name,
                onAction: function () {
                  ctx.insertContent(`<span class="graphdata" contenteditable="false">{{${i.id}}}</span>`);
                }
              })
            })

            callback(menuItems);
          }
        });
      }
    }
  }

  getDef(): StatXYDef {
    var pDef = this.period.getDef();
    console.log(pDef);
    this.def.after = pDef.after;
    this.def.before = pDef.before;
    this.def.duration = pDef.duration;
    this.def.filter = this.filters$.value.slice(0);
    this.def.other = this.others$.value.filter((o) => (o.field_name ?? '') !== '').map((o) => { return o.field_name });

    this.def.x = (this.def.x ?? "") === "" ? null : this.def.x;
    this.def.y = (this.def.y ?? "") === "" ? null : this.def.y;
    this.def.shape = (this.def.shape ?? "") === "" ? null : this.def.shape;
    this.def.color = (this.def.color ?? "") === "" ? null : this.def.color;

    if (this.params$.value.length > 0)
      this.def.obj.params = this.params$.value.map(p => <StatXYParam>{
        key: p.name,
        value: (p.value ?? "") === "" ? null : p.value
      });

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
    this.others$.next(this.def.other.map((o, i) => {
      return <Other>{
        id: i,
        field_name: o
      }
    }));
    this.getMeta();
  }

  ngAfterViewInit() {
    console.log(this.editor);
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
        html: this._defaultTooltip
      }
    };

    if (!this.def.visualsettings)
      this.def.visualsettings = defaults;
    else
      this.def.visualsettings = Object.assign(defaults, this.def.visualsettings);
  }

  getMeta() {
    this.apiService.getStatXYMeta(undefined).subscribe(meta => {
      this.objects$.next(meta);
      var filters = (this.def.filter ?? []).map((f, i) => {
        var result: Filter = {
          _id: i,
          _type: this.getField(f.field)?.type,
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

  getField(fieldname: string): StatXYMetaObjectField {
    for (let object of this.objects$.value) {
      let field = object.fields.find(f => f.name === fieldname);
      if (field)
        return field;
    }
    return undefined;
  }

  objectChanged(type: string, noInteractive: boolean = false) {
    var obj = this.objects$.value.filter((o) => o.name === type);
    if (!noInteractive) {
      this.def.obj = {
        type: type as StatXYObjectType,
        params: []
      };
    }
    let emptyField: StatXYMetaObjectField = {
      displayname: "-",
      name: "",
      type: StatMetaObjectFieldType.Numeric,
      unit: StatXYMetaObjectFieldUnit.Percent,
      value_list: []
    };

    let fields = obj.length > 0 ? obj[0].fields : [];
    fields.splice(0, 0, ...[emptyField]);
    this.fields$.next(fields);
    this.numFields$.next(obj.length > 0 ? fields.filter(f => f.type === StatMetaObjectFieldType.Numeric) : []);
    this.params$.next(obj[0].params.map(p => <ObjParam>{ label: p.label, name: p.name, type: p.type, value: this.def.obj?.params?.find(dp => dp.key === p.name)?.value }));
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
      _type: undefined,
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
      filter._type = metaField.type;
      filter.values = metaField.value_list;
    }
    console.log(metaField);
    console.log(filter.values);
  }

  getFieldValues(name: string): string[] {
    var field = this.fields$.value.find((f) => f.name === name);
    if (field)
      return field.value_list ?? [];
    else
      return [];
  }

  getOperators(filter: Filter): NumberRelation[] {
    var forCategories: NumberRelation[] = [NumberRelation.Equal, NumberRelation.NotEqual];
    return this.operators.filter(o => (filter._type === "category" && forCategories.indexOf(o) > -1) || filter._type !== "category");
  }

  deleteOther(id: number) {
    var others = this.others$.value;
    var idx = others.findIndex((o) => o.id === id);
    if (idx > -1)
      others.splice(idx, 1);

    this.others$.next(others);
  }

  newOther() {
    var others = this.others$.value;
    others.push({
      id: ((others ?? []).length === 0 ? 0 : Math.max(...others.map(f => f.id))) + 1,
      field_name: undefined
    });
    this.others$.next(others);
  }

  updateOther() {
    var others = this.others$.value;
    var list = [
      ["X", "X"],
      ["Y", "Y"],
      ["SHAPE", "forma"],
      ["COLOR", "szín"]
    ];
    for (let other of others)
      list.push([other.field_name, this.fields$.value.find(f => f.name === other.field_name)?.displayname ?? other.field_name]);

  //  (this.quill.quillEditor.getModule("graphdata") as QuillGraphData).reloadList(list);
  }

  editorGraphDataChanged(value) {
    console.log(value);
  }

  validField(selection: string): boolean {
    if ((selection ?? "") === "")
      return true;
    else
      return this.fields$.value.findIndex(f => f.name === selection) > -1;
  }

  validNumField(selection: string): boolean {
    if ((selection ?? "") === "")
      return true;
    else
      return this.numFields$.value.findIndex(f => f.name === selection) > -1;
  }

  getChartConfiguration(data: StatData): ChartConfiguration {
    var shapes = ['circle', 'triangle', 'rect', 'star', 'cross'];
    var shapeFieldValues = this.getFieldValues(data.stat_def.xydef.shape);
    var colors = ['#CC2936', '#3B8E83', '#273E47', '#BD632F', '#00A3FF', '#08415C', '#273E47', '#D8973C', '#388697'];
    var colorFieldValues = this.getFieldValues(data.stat_def.xydef.color);
    var series: string[][] = [];
    data.xydata.map((v) => {
      var color = (v.color ?? "").toString();
      var shape = (v.shape ?? "").toString();
      if (!series.find((s) => s[0] === color && s[1] === shape))
        series.push([color, shape]);
    });

    var xIsCategory = data.xydata.find((v) => typeof v.x === "string") ? true : false;
    var yIsCategory = data.xydata.find((v) => typeof v.y === "string") ? true : false;
    var xLabels = [];
    var yLabels = [];
    if (xIsCategory)
      xLabels = data.xydata.map((v) => v.x).filter((v, index, self) => self.indexOf(v) === index);
    if (yIsCategory)
      yLabels = data.xydata.map((v) => v.y).filter((v, index, self) => self.indexOf(v) === index);

    var othersByDataPointIndex: number[][] = [];

    return {
      type: 'bubble',
      data: {
        datasets: series.map((series, seriesIndex) => {
          console.log(seriesIndex);
          return {
            label: series.join(' '),
            data: data.xydata.filter((d) => series[0] === (d.color ?? "").toString() && series[1] === (d.shape ?? "").toString())
              .map((d) => {
              othersByDataPointIndex.push(d.others);
              return {
                x: xIsCategory ? xLabels.indexOf(d.x) : <number>d.x,
                y: yIsCategory ? yLabels.indexOf(d.y) : <number>d.y,
                r: 10
              }
            }),
            pointStyle: shapes[shapes.length % (shapeFieldValues.indexOf(series[1]) + 1)],
            backgroundColor: colors[colors.length % (colorFieldValues.indexOf(series[0]) + 1)] + "80",
            borderColor: colors[colors.length % (colorFieldValues.indexOf(series[0]) + 1)]
        }})
      },
      options: {
        plugins: {
          tooltip: {
            enabled: false,
            boxWidth: 350,
            position: 'average',
              external: (context) => {

                function getOrCreateTooltip(chart) {
                  let tooltipEl = chart.canvas.parentNode.querySelector('#tooltip') as HTMLDivElement;

                  if (!tooltipEl) {
                    tooltipEl = document.createElement('div');
                    tooltipEl.id = "tooltip";
                    tooltipEl.style.background = 'rgba(0, 0, 0, 0.7)';
                    tooltipEl.style.borderRadius = '3px';
                    tooltipEl.style.color = 'white';
                    tooltipEl.style.opacity = "1";
                    tooltipEl.style.pointerEvents = 'none';
                    tooltipEl.style.position = 'absolute';
                    tooltipEl.style.transform = 'translate(-50%, 0)';
                    tooltipEl.style.transition = 'all .1s ease';

                    const table = document.createElement('table');
                    table.style.margin = '0px';

                    tooltipEl.appendChild(table);

                    chart.canvas.parentNode.appendChild(tooltipEl);
                  }

                  return tooltipEl;
                };

                  // Tooltip Element
                const {chart, tooltip} = context;
                const tooltipEl = getOrCreateTooltip(chart);

                // Hide if no tooltip
                if (tooltip.opacity === 0) {
                  tooltipEl.style.opacity = "0";
                  return;
                }

                // Set Text
                if (tooltip.body) {
                  const titleLines = tooltip.title || [];
                  const bodyLines = tooltip.body.map(b => b.lines);

                  const tableHead = document.createElement('thead');

                  titleLines.forEach(title => {
                    const tr = document.createElement('tr') as HTMLTableRowElement;
                    tr.style.borderWidth = '0';

                    const th = document.createElement('th') as HTMLTableCellElement;
                    th.style.borderWidth = '0';
                    const text = document.createTextNode(title);

                    th.appendChild(text);
                    tr.appendChild(th);
                    tableHead.appendChild(tr);
                  });

                  const tableBody = document.createElement('tbody');
                  const colors = tooltip.labelColors[0];

                  const span = document.createElement('span') as HTMLSpanElement;
                  span.style.background = colors.backgroundColor.toString();
                  span.style.borderColor = colors.borderColor.toString();
                  span.style.borderWidth = '2px';
                  span.style.marginRight = '10px';
                  span.style.height = '10px';
                  span.style.width = '10px';
                  span.style.display = 'inline-block';

                  const tr = document.createElement('tr');
                  tr.style.backgroundColor = 'inherit';
                  tr.style.borderWidth = '0';

                  const td = document.createElement('td');
                  td.style.borderWidth = '0';

                  let dataPointIndex = context.tooltip.dataPoints[0].dataIndex;
                  let seriesIndex = context.tooltip.dataPoints[0].datasetIndex;
                  let html = this.def.visualsettings.tooltip.html ?? `${context.tooltip.dataPoints[0].label}<br/><br/>` + this._defaultTooltip;
                  console.log(context.tooltip);
                  html = html.replace(/{{X}}/gi, context.tooltip.dataPoints[0]?.parsed?.x?.toFixed(3));
                  html = html.replace(/{{Y}}/gi, context.tooltip.dataPoints[0]?.parsed?.y?.toFixed(3));
                  let shapeValue = undefined;
                  let colorValue = undefined;
                  if (context.tooltip.dataPoints?.length > 0) {
                    shapeValue = series[seriesIndex][1];
                    colorValue = series[seriesIndex][0];
                  }
                  html = html.replace(/{{SHAPE}}/gi, shapeValue);
                  html = html.replace(/{{COLOR}}/gi, colorValue);
                  if (othersByDataPointIndex.length > dataPointIndex)
                    this.def.other.forEach((o, i) => {
                      var value = data.xydata[dataPointIndex].others[i];
                      html = html.replace(new RegExp(`{{${o}}}`, 'gi'),
                        typeof value === "number" ? value.toFixed(3) : value );
                    });
                  const text = document.createElement('span');
                  text.innerHTML = html;
                  td.appendChild(span);
                  td.appendChild(text);
                  tr.appendChild(td);
                  tableBody.appendChild(tr);

                  const tableRoot = tooltipEl.querySelector('table');

                  // Remove old children
                  while (tableRoot.firstChild) {
                    tableRoot.firstChild.remove();
                  }

                  // Add new children
                  tableRoot.appendChild(tableHead);
                  tableRoot.appendChild(tableBody);
                }

                const {offsetLeft: positionX, offsetTop: positionY} = chart.canvas;

                // Display, position, and set styles for font
                tooltipEl.style.opacity = "1";
                let left = positionX + tooltip.caretX;
                let position = chart.canvas.getBoundingClientRect();
                if (left < 0)
                  left = 0;
                else if ( position.left + left + tooltipEl.offsetWidth > window.innerWidth)
                  left = window.innerWidth - position.left - positionX - tooltipEl.offsetWidth;

                let top = positionY + tooltip.caretY;
                if (top < 0)
                  top = 0;
                else if (position.top + top + tooltipEl.offsetHeight > window.innerHeight)
                  top = window.innerHeight - position.top - positionY - tooltipEl.offsetHeight;
                tooltipEl.style.left = left + 'px';
                tooltipEl.style.top = top + 'px';
                tooltipEl.style.font = (tooltip.options.bodyFont as any).string;
                tooltipEl.style.padding = tooltip.options.padding + 'px ' + tooltip.options.padding + 'px';
                tooltipEl.style.width =  tooltip.width ? (tooltip.width + 'px') : 'auto';
                console.log(left);
                console.log(top);
              }
          },
          title: AnalysisHelpers.setChartTitle(data.stat_def.xydef.visualsettings?.title),
          subtitle: AnalysisHelpers.setChartTitle(data.stat_def.xydef.visualsettings?.subtitle),
          legend: {
            display:  true,
            align: data.stat_def.xydef.visualsettings?.legend?.align ?? 'center',
            position: data.stat_def.xydef.visualsettings?.legend?.position ?? 'top',
            labels: {
              usePointStyle: true
            }
          }
        },
        scales: {
          y: {
            title: AnalysisHelpers.setChartTitle(data.stat_def.xydef.visualsettings?.yaxis?.caption),
            ticks: {
              callback: function(value, index, values) {
                  return yIsCategory ? yLabels[value] : value;
              }
            }
          },
          x: {
            title: AnalysisHelpers.setChartTitle(data.stat_def.xydef.visualsettings?.xaxis?.caption),
            ticks: {
              callback: function(value, index, values) {
                  return xIsCategory ? xLabels[value] : (typeof value === "number" ? value.toFixed(1) : value);
              }
            }
          },
        }
      }
    };
  }
}
