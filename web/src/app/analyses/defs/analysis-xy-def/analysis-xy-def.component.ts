import { Component, Input, OnInit, ViewChild } from '@angular/core';
import { ChartConfiguration, ChartTypeRegistry, ScatterDataPoint, BubbleDataPoint } from 'chart.js';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { StatData, StatVisualSettingsLegendAlign, StatVisualSettingsLegendPosition, StatXYDef, StatXYFilter, StatXYFilterRel, StatXYMeta, StatXYMetaObject, StatXYMetaObjectField, StatXYObjectType, StatXYOther } from 'src/app/services/models/api';
import { Labels } from 'src/app/services/models/constants';
import { AnalysisChart, AnalysisDef } from '../../analyses.component';
import { AnalysisHelpers } from '../../helpers';
import { AnalysisDatetimeDefComponent } from '../analysis-datetime-def/analysis-datetime-def.component';

interface Filter extends StatXYFilter {
  _id: number,
  values: string[]
}

interface Other {
  id: number,
  field_name: string
}

@Component({
  selector: 'app-analysis-xy-def',
  templateUrl: './analysis-xy-def.component.html',
  styleUrls: ['./analysis-xy-def.component.scss']
})
export class AnalysisXyDefComponent implements OnInit, AnalysisDef, AnalysisChart {

  @Input("def") def: StatXYDef;
  @Input("xymeta") xymeta: StatXYMeta;
  @ViewChild('period') period: AnalysisDatetimeDefComponent;

  objects$: BehaviorSubject<StatXYMetaObject[]> = new BehaviorSubject([]);
  fields$: BehaviorSubject<StatXYMetaObjectField[]> = new BehaviorSubject([]);
  filters$: BehaviorSubject<Filter[]> = new BehaviorSubject([]);
  others$: BehaviorSubject<Other[]> = new BehaviorSubject([]);
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
    this.def.other = this.others$.value.filter((o) => (o.field_name ?? '') !== '').map((o) => { return o.field_name });
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

  getFieldValues(name: string): string[] {
    var field = this.fields$.value.find((f) => f.name === name);
    if (field)
      return field.value_list ?? [];
    else
      return [];
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

  getChartConfiguration(data: StatData): ChartConfiguration {
    var shapes = ['circle', 'triangle', 'rect', 'star', 'cross'];
    var shapeFieldValues = this.getFieldValues(data.stat_def.xydef.shape);
    var colors = ['#CC2936', '#3B8E83', '#273E47', '#BD632F', '#00A3FF', '#08415C', '#273E47', '#D8973C', '#388697'];
    var colorFieldValues = this.getFieldValues(data.stat_def.xydef.color);
    var series: string[][] = [];
    data.xydata.map((v) => {
      var color = (v.color ?? "").toString();
      var shape = (v.shape ?? "").toString()
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

    return {
      type: 'bubble',
      data: {
        datasets: series.map((series, seriesIndex) => {
          console.log(seriesIndex);
          return {
            label: series.join(' '),
            data: data.xydata.filter((d) => series[0] === (d.color ?? "").toString() && series[1] === (d.shape ?? "").toString())
              .map((d) => {
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
                  return xIsCategory ? xLabels[value] : value;
              }
            }
          }
        }
      }
    };
  }
}
