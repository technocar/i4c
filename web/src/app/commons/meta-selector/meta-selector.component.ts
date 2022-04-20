import { DOCUMENT } from '@angular/common';
import { Component, ElementRef, EventEmitter, Inject, Input, OnChanges, OnInit, Output, SimpleChange, SimpleChanges, TemplateRef, ViewChild, ɵSWITCH_CHANGE_DETECTOR_REF_FACTORY__POST_R3__ } from '@angular/core';
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
  private _metaList: Meta[];

  @ViewChild("button") button: ElementRef<HTMLButtonElement>;
  @ViewChild("dropdown") dropdown: ElementRef<HTMLElement>;
  @ViewChild("menu") menu: ElementRef<HTMLElement>;

  @Input() disabled: boolean = false;
  @Input('device')
  set device(value: string) {
    if (value === this._device)
      return;

    this._device = value;
  }
  get device(): string {
    return this._device;
  }

  @Input('conditionSelectable') conditionSelectable: boolean = false;
  @Input('metaList')
  get metaList(): Meta[] {
    return this._metaList;
  }
  set metaList(value: Meta[]) {
    this._metaList = value ?? [];
    if (this._selectedMetaId)
      this.selectedMetaId = this._selectedMetaId;
  }
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

    //this._device = meta.device;
    this.selectedMetric = {
      id: meta.data_id,
      name: meta.nice_name ?? meta.name ?? meta.data_id,
      device: meta.device,
      type: undefined,
      level: undefined,
      children: []
    }
  }
  @Output('change') change: EventEmitter<Meta> = new EventEmitter();

  metricTree: Metric[] = [];
  selectedMetric: Metric;

  constructor(@Inject(DOCUMENT) private document: Document) { }

  ngOnInit(): void {
  }

  ngOnChanges(changes: SimpleChanges) {
    console.log(changes);
    if (changes.device) {
      let device: SimpleChange = changes.device;
      if (device.currentValue !== device.previousValue && !device.firstChange) {
        let meta = this._selectedMetaId ? this.getMeta(this._selectedMetaId) : undefined;
        this.change.emit({
          data_id: meta ? meta.data_id : undefined,
          device: device.currentValue as DeviceType
        });
      }
    }
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

  itemSelected(event: Event) {
    event.stopPropagation();
    this.toggleMetricNode(event.target as HTMLElement);
  }

  toggleMetricNode(target: HTMLElement) {
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
      if (!this.dropdown.nativeElement.classList.contains("show"))
        this.button.nativeElement.scrollIntoView();

      this._selectedMetaId = this.selectedMetric.id;
      let meta: Meta;
      if (isCategorySelection)
        meta = {
          data_id: undefined,
          device: this._device as DeviceType,
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
    let top = this.menu.nativeElement.getBoundingClientRect().top + window.scrollY;
    console.log(top);
    if (top + this.menu.nativeElement.offsetHeight > this.document.body.offsetHeight)
      this.document.body.style.height = (top + this.menu.nativeElement.offsetHeight) + "px";
  }

  getMeta(id: string): Meta {
    return (this.metaList ?? []).find((m) => { return m.data_id === id && (!this._device || m.device === this._device) });
  }

  toggle(open: boolean) {
    if (open) {
      this.getTree();
    }
  }
}
