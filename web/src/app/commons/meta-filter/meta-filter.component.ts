import { Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { NgForm } from '@angular/forms';
import { NgbActiveModal, NgbModal, NgbModalRef, NgbTypeahead } from '@ng-bootstrap/ng-bootstrap';
import { merge, Observable, OperatorFunction, Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, map } from 'rxjs/operators';
import { ApiService } from 'src/app/services/api.service';
import { EventValues, Meta } from 'src/app/services/models/api';
import { DeviceType } from 'src/app/services/models/constants';

interface Metric {
  id: string,
  name: string,
  type: string,
  level: string,
  device: string,
  children: Metric[]
}

interface MetricFilterError {
  show: boolean,
  message: string
}

export interface MetricFilterModel {
  direction: string,
  device?: DeviceType,
  relation?: string,
  metricId?: string,
  metricType?: string,
  metricName?: string,
  value?: string,
  extra?: string
}

interface SelectedEventValues {
  name: string
}

export enum MetaFilterMode { Search = 0, Select = 1 }

@Component({
  selector: 'app-meta-filter',
  templateUrl: './meta-filter.component.html',
  styleUrls: ['./meta-filter.component.scss']
})
export class MetaFilterComponent implements OnInit {

  private _allEventValues: EventValues[] = [];
  private _activeModal: NgbModalRef;

  @Input('metaList') metaList: Meta[];
  @Input('selectableTypes') selectableTypes: string[];
  @Input('mode') mode: MetaFilterMode = MetaFilterMode.Select;
  @Input('onlySelector') onlySelector: boolean;
  @Output("onFilter") onFilter: EventEmitter<MetricFilterModel> = new EventEmitter();

  @ViewChild('dialog') dialog;
  @ViewChild('eventValuesSelector', {static: true}) instance: NgbTypeahead;

  focus$ = new Subject<string>();
  click$ = new Subject<string>();

  metricTree: Metric[] = [];
  searchModel: MetricFilterModel = {
    direction: "-1"
  };
  searchError: MetricFilterError = {
    show: false,
    message: ""
  };
  selectedEventValues: string[] = [];
  eventOps: string[][] = [];

  disableMetricSelection: boolean = false;

  constructor(
    private modalService: NgbModal,
    private apiService: ApiService)
  {
    this.eventOps = apiService.getEventOperations();
  }

  ngOnInit(): void {
  }

  searchForEventValues: OperatorFunction<string, readonly string[]> = (text$: Observable<string>) => {
    const debouncedText$ = text$.pipe(debounceTime(200), distinctUntilChanged());
    const clicksWithClosedPopup$ = this.click$/*.pipe(filter(() => !this.instance.isPopupOpen()))*/;
    const inputFocus$ = this.focus$;

    return merge(debouncedText$, inputFocus$, clicksWithClosedPopup$).pipe(
      map(term => (term === '' ? this.selectedEventValues
        : this.selectedEventValues.filter(v => v.toLowerCase().indexOf(term.toLowerCase()) > -1)).slice(0, 10))
    );
  }

  toggleMetricNode(event: Event) {
    let target = (event.target as HTMLElement);
    let isCategorySelection = target.classList.contains("category");
    let allowedNodes = ["LI", "I", "SPAN"];
    if (allowedNodes.indexOf(target.nodeName) === -1 && !isCategorySelection)
      return;

    let node = target.closest('li');

    if (node.classList.contains("leaf") || isCategorySelection) {
      if (this.searchModel.metricType !== node.getAttribute("type")) {
        this.searchModel.value = undefined;
        this.searchModel.relation = undefined;
        this.searchModel.extra = undefined;
      }
      this.searchModel.metricType = node.getAttribute("type");
      if (isCategorySelection) {
        this.searchModel.metricId = undefined;
        this.searchModel.metricName = node.querySelector('span').innerText;
      } else {
        this.searchModel.metricId = node.id;
        this.searchModel.metricName = node.innerText;
      }
      if (this.searchModel.metricType === "EVENT") {
        this.getEventValues(this.searchModel.metricId);
      }
      node.closest(".dropdown-menu").classList.toggle("show");
      let dropdown = node.closest(".dropdown") as HTMLElement;
      dropdown.classList.toggle("show");
      let button = dropdown.querySelector(".dropdown-toggle") as HTMLButtonElement;
      //button.innerText = node.innerText;
      button.setAttribute("aria-expanded", "false");
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

  getEventValues(id: string) {
    let event = this._allEventValues.find((event) => {
      return event.data_id === id;
    });

    this.selectedEventValues = event?.values ?? [];
  }

  searchDataChanged(event: Event) {
    this.searchError.show = false;
  }

  show(model?: MetricFilterModel, disableMetricSelection?: boolean) {
    if (model)
      this.searchModel = model;
    else
      this.searchModel = { direction: "-1" };
    this.disableMetricSelection = disableMetricSelection === true;

    this.metricTree = this.getMetrics(undefined, undefined) ?? [];
    this._activeModal = this.modalService.open(this.dialog);
  }

  close() {
    if (this._activeModal)
      this._activeModal.close();
  }

  filter(form: NgForm, modal: NgbActiveModal) {
    this.onFilter.emit(this.searchModel);
  }

  showError(message: string) {
    this.searchError.show = true;
    this.searchError.message = message;
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

}
