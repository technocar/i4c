import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { Condition } from 'selenium-webdriver';
import { Category, Meta } from 'src/app/services/models/api';

interface Metric {
  id: string,
  name: string,
  type: string,
  level: string,
  device: string,
  children: Metric[]
}

@Component({
  selector: 'app-meta-selector',
  templateUrl: './meta-selector.component.html',
  styleUrls: ['./meta-selector.component.scss']
})
export class MetaSelectorComponent implements OnInit {

  private _selectedMetaId: string;

  @Input('metaList') metaList: Meta[];
  @Input('selectableTypes') selectableTypes: string[];
  @Input('selectedMetaId')
  public get selectedMetaId(): string {
    return this._selectedMetaId;
  }
  public set selectedMetaId(value: string) {
    this._selectedMetaId = value;
    var meta = this.getMeta(value);
    if (!meta)
      return;

    this.selectedMetric = {
      id: meta.data_id,
      name: meta.nice_name ? meta.nice_name : meta.name,
      device: meta.device,
      type: undefined,
      level: undefined,
      children: []
    }
  }
  @Output('change') change: EventEmitter<Meta> = new EventEmitter();

  metricTree: Metric[] = [];
  selectedMetric: Metric;

  constructor() { }

  ngOnInit(): void {
  }

  getMetrics(ids: string[], parentLevels: string[]): Metric[] {
    let children: Metric[] = [];
    let items: Meta[] = [];
    let level: string;
    ids = ids ?? [];
    parentLevels = parentLevels ?? [];
    let parentLevel = parentLevels.length > 0 ? parentLevels[parentLevels.length - 1] : "";
    switch(parentLevel) {
      case "category":
        level = "system1";
        break;
      case "system1":
        level = "system2";
        break;
      case "system2":
        level = "data_id";
        break;
      case "data_id":
        return [];
      default:
        level = "category";
        break;
    }
    items = this.metaList.filter((value: Meta, index: Number, array: Meta[]) => {

      if ((this.selectableTypes ?? []).length > 0 && this.selectableTypes.indexOf(value.category) === -1)
        return false;

      if (ids.length === 0)
        return true;

      for (let i = 0; i < ids.length; i++)
        if (ids[i] !== value[parentLevels[i]])
          return false;

      return true;
    });

    for (let item of items) {
      let idx = children.findIndex((value) => {
        return value.id === item[level]
      });

      if (idx > -1)
        continue;

      let name = level === "data_id" ? item.nice_name : item[level];
      if (name == undefined || name == "")
        name = item.data_id;

      children.push({
        id: item[level],
        name: name,
        type: ids.length === 0 ? item[level] : ids[0],
        level: level,
        device: item.device,
        children: this.getMetrics(ids.concat([item[level]]), parentLevels.concat([level]))
      });
    }

    children = children.sort((a, b) => {
      return a.name < b.name ? -1 : a.name > b.name ? 1 : 0;
    });

    return children;
  }

  toggleMetricNode(event: Event) {
    let target = (event.target as HTMLElement);
    let isCategorySelection = target.classList.contains("category");
    let allowedNodes = ["LI", "I", "SPAN"];
    if (allowedNodes.indexOf(target.nodeName) === -1 && !isCategorySelection)
      return;

    let node = target.closest('li');

    if (node.classList.contains("leaf") || isCategorySelection) {
      this.selectedMetric = { id: undefined, device: undefined, name: undefined, level: undefined, type: undefined, children: [] }
      this.selectedMetric.type = node.getAttribute("type");
      if (isCategorySelection) {
        this.selectedMetric.id = node.id;
        this.selectedMetric.name = node.querySelector('span').innerText;
      } else {
        this.selectedMetric.id = node.id;
        this.selectedMetric.name = node.innerText;
      }
      node.closest(".dropdown-menu").classList.toggle("show");
      let dropdown = node.closest(".dropdown") as HTMLElement;
      if (dropdown) {
        dropdown.classList.toggle("show");
        let button = dropdown.querySelector(".dropdown-toggle") as HTMLButtonElement;
        button.setAttribute("aria-expanded", "false");
      }
      this._selectedMetaId = this.selectedMetric.id;
      let meta: Meta;
      if (isCategorySelection)
        meta = {
          data_id: this.selectedMetric.id,
          device: undefined,
          category: this.selectedMetric.id as Category,
          name: this.selectedMetric.name
        }
      else
        meta = this.getMeta(this.selectedMetric.id);
      this.change.emit(meta);
    } else {
      if (node.classList.contains("closed"))
      {
        node.classList.remove("closed");
        node.classList.add("opened");
      } else {
        node.classList.remove("opened");
        node.classList.add("closed");
      }
    }
  }

  getMeta(id: string): Meta {
    return this.metaList.find((m) => { return m.data_id === id });
  }

  toggle(open: boolean) {
    if (open) {
      this.metricTree = this.getMetrics(undefined, undefined);
    }
  }
}
