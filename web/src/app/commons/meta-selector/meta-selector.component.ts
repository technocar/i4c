import { Component, ElementRef, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges, TemplateRef, ViewChild } from '@angular/core';
import { Category, Meta } from 'src/app/services/models/api';
import { DeviceType } from 'src/app/services/models/constants';

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
export class MetaSelectorComponent implements OnInit, OnChanges {

  private _selectedMetaId: string;
  private _device: string;

  @ViewChild("button") button: ElementRef<HTMLButtonElement>;
  @ViewChild("dropdown") dropdown: ElementRef<HTMLElement>;

  @Input() disabled: boolean = false;
  @Input('device')
  set device(value: string) {
    this._device = value;
    this.change.emit({
      data_id: null,
      device: this._device as DeviceType
    });
  }
  get device(): string {
    return this._device;
  }
  @Input('metaList') metaList: Meta[];
  @Input('selectableTypes') selectableTypes: string[];
  @Input('selectedMetaId')
  public get selectedMetaId(): string {
    return this._selectedMetaId;
  }
  public set selectedMetaId(value: string) {
    this._selectedMetaId = value;
    var meta = this.getMeta(value);
    if (!meta) {
      this.selectedMetric = undefined;
      return;
    }

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

  ngOnChanges(changes: SimpleChanges) {
    console.log(changes);
  }

  createParents(parentLevels: Metric[], where: Metric[]): Metric[]
  {
    var result: Metric[] = where;
    var lvl = 0;
    for (let s of parentLevels) {
      if ((s.name ?? "") !== "")
      {
        let curr = result.find(v => { return v.id === s.id});
        if (curr === undefined)
        {
          s.level = lvl.toString();
          result.push(s);
          result = s.children;
        }
        else
        {
          result = curr.children;
        }
        lvl = lvl + 1;
      }
    }
    return result;
  }

  getTree(){
    this.metricTree.length = 0;
    this.metaList = this.metaList.sort((a, b) => {
      var a1 = a.category.concat(...[a.system1 ?? "", a.system2 ?? "", (a.nice_name ?? a.name ?? a.data_id)]);
      var b1 = b.category.concat(...[b.system1 ?? "", b.system2 ?? "", (b.nice_name ?? b.name ?? b.data_id)]);
      return a1 > b1 ? 1  : a1 < b1 ? -1 : 0;
    })
    for(let item of this.metaList) {
      if (((this._device === item.device) || !this._device)
      && (this.selectableTypes?.length === 0 || this.selectableTypes.indexOf(item.category) > -1))
      {
        this.createParents([
          {
            id: item.category,
            name: item.category,
            type: item.category,
            level: '0',
            device: item.device,
            children: []
          },
          {
            id: item.system1,
            name: item.system1,
            type: item.category,
            level: '1',
            device: item.device,
            children: []
          },
          {
            id: item.system2,
            name: item.system2,
            type: item.category,
            level: '2',
            device: item.device,
            children: []
          }], this.metricTree).push({
            id: item.data_id,
            name: item.nice_name ?? item.name ?? item.data_id,
            type: item.category,
            level: '3',
            device: item.device,
            children: []
          });
      }
    }
  }


  getMetrics(ids: string[], parentLevels: string[], level: string): Metric[] {
    let children: Metric[] = [];
    let items: Meta[] = [];
    ids = ids ?? [];
    parentLevels = parentLevels ?? [];

    if (level === undefined)
      return [];

    items = this.metaList.filter((value: Meta, index: Number, array: Meta[]) => {

      if (value.device !== this._device && this._device)
        return false;

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

      let name = level === "data_id" ? (item.nice_name ?? item.name) : item[level];
      if (name == undefined || name == "") {
        name = level === "data_id" ? item.data_id : "N/A";
      }

      children.push({
        id: item[level],
        name: name,
        type: ids.length === 0 ? item[level] : ids[0],
        level: level,
        device: item.device,
        children: this.getMetrics(ids.concat([item[level]]), parentLevels.concat([level]), this.getNextLevel(level, ids, parentLevels))
      });
    }

    children = children.sort((a, b) => {
      return a.name < b.name ? -1 : a.name > b.name ? 1 : 0;
    });

    return children;
  }

  getNextLevel(level: string, ids: string[], parentLevels: string[]): string {
      const levels = ["category", "system1", "system2", "data_id"];
      let levelIdx = levels.indexOf(level);
      if (levelIdx === levels.length - 1)
        return undefined;

      let nextLevel = levels[++levelIdx];

      let tmp = this.metaList.filter((value: Meta, index: Number, array: Meta[]) => {

        if (value.device !== this._device && this._device)
          return false;

        if ((this.selectableTypes ?? []).length > 0 && this.selectableTypes.indexOf(value.category) === -1)
          return false;

        if (ids.length === 0)
          return true;

        for (let i = 0; i < ids.length; i++)
          if (ids[i] !== value[parentLevels[i]])
            return false;

        if (!value[nextLevel])
          return false;

        return true;
      });

      if (tmp.length > 0)
        return nextLevel;
      else
        return this.getNextLevel(nextLevel, ids, parentLevels);
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
      this.dropdown.nativeElement.classList.toggle("show");
      this.button.nativeElement.setAttribute("aria-expanded", "false");

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
      //this.metricTree = this.getMetrics(undefined, undefined, "category");
      this.getTree();
    }
  }
}
