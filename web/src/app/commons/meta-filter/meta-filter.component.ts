import { Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { NgForm } from '@angular/forms';
import { NgbActiveModal, NgbModal, NgbModalRef, NgbTypeahead } from '@ng-bootstrap/ng-bootstrap';
import { merge, Observable, OperatorFunction, Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, map } from 'rxjs/operators';
import { ApiService } from 'src/app/services/api.service';
import { Meta } from 'src/app/services/models/api';
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

  private _activeModal: NgbModalRef;

  @Input('metaList') metaList: Meta[];
  @Input('selectableTypes') selectableTypes: string[];
  @Input('mode') mode: MetaFilterMode = MetaFilterMode.Select;
  @Input('onlySelector') onlySelector: boolean;
  @Output("onFilter") onFilter: EventEmitter<MetricFilterModel> = new EventEmitter();

  @ViewChild('dialog') dialog;

  focus$ = new Subject<string>();
  click$ = new Subject<string>();

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

  selectMeta(meta: Meta) {
    console.log(meta);
    this.searchModel.device = meta.device;
    this.searchModel.metricId = meta.data_id;
    this.searchModel.metricName = meta.nice_name ?? meta.name ?? meta.data_id;
    this.searchModel.metricType = meta.category;
    if (this.searchModel.metricType === "EVENT")
      this.selectedEventValues = meta.value_list ?? [];
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

}
