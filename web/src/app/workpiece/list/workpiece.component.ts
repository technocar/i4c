import { AfterViewInit, ChangeDetectorRef, Component, OnInit, ViewChild } from '@angular/core';
import { NgbDateStruct } from '@ng-bootstrap/ng-bootstrap/datepicker/ngb-date-struct';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { BehaviorSubject, forkJoin, Observable } from 'rxjs';
import { filter, tap } from 'rxjs/operators';
import { ApiService } from '../../services/api.service';
import { UpdateResult, WorkPiece, WorkPieceBatch, WorkPieceBatchItemType, WorkPieceStatus } from '../../services/models/api';
import { ActivatedRoute, NavigationEnd, Router, RouterState } from '@angular/router';
import { FilterControlComponent } from 'src/app/commons/filter/filter.component';
import { FiltersService } from 'src/app/services/filters.service';
import { AuthenticationService } from 'src/app/services/auth.service';

interface WorkPieceItem extends WorkPiece {
  selected: boolean
}

interface WorkPieceFilters {
  fd: string,
  fid: string,
  fp: string,
  fb: string,
  fs: string,
  fwob: boolean
}

@Component({
  selector: 'app-workpiece',
  templateUrl: './workpiece.component.html',
  styleUrls: ['./workpiece.component.scss']
})
export class WorkPieceComponent implements OnInit, AfterViewInit {

  @ViewChild("filterProjectCtrl") filterProjectCtrl: FilterControlComponent;
  @ViewChild("filterBatchCtrl") filterBatchCtrl: FilterControlComponent;

  private _filterDate: NgbDateStruct;
  private _filterWOBatch: boolean;
  private _filterProject: string;
  private _filterBatch: string;
  private _filterStatus: string;
  private _filterId: string;

  private _filterDateChanged = false;
  private _filterWOBatchChanged = false;
  private _filterProjectChanged = false;
  private _filterBatchChanged = false;
  private _filterStatusChanged = false;
  private _filterIdChanged = false;

  isAllSelected: boolean = false;
  workPieces$: BehaviorSubject<WorkPieceItem[]> = new BehaviorSubject([]);
  batches$: BehaviorSubject<WorkPieceBatch[]> = new BehaviorSubject([]);
  fetchingList$: BehaviorSubject<boolean> = new BehaviorSubject(false);
  confirmBatchDelete: boolean = false;
  currentSelectedItem: WorkPieceItem;

  queryParamProject: string;
  queryParamBatch: string;

  get filterDate(): NgbDateStruct {
    return this._filterDate;
  }
  set filterDate(value: NgbDateStruct) {
    this._filterDate = value;
    this._filterDateChanged = true;
  }

  get filterId(): string {
    return this._filterId;
  }

  set filterId(value: string) {
    this._filterId = value;
    this._filterIdChanged = true;
  }

  get filterProject(): string {
    return this._filterProject;
  }
  set filterProject(value: string) {
    this._filterProject = value;
    this._filterProjectChanged = true;
  }
  get filterBatch(): string {
    return this._filterBatch;
  }
  set filterBatch(value: string) {
    this._filterBatch = value;
    this._filterBatchChanged = true;
  }
  get filterStatus(): string {
    return this._filterStatus;
  }

  set filterStatus(value: string) {
    this._filterStatus = value;
    this._filterStatusChanged = true;
  }

  get filterWOBatch(): boolean {
    return this._filterWOBatch;
  }
  set filterWOBatch(value: boolean) {
    this._filterWOBatch = value;
    this._filterWOBatchChanged = true;
  }

  noFilter = false;

  statuses: string[][] = [];

  access = {
    canUpdate: false
  }

  private selected: string[] = [];

  constructor(
    private apiService: ApiService,
    private modalService: NgbModal,
    private route: ActivatedRoute,
    private router: Router,
    private cd: ChangeDetectorRef,
    private filtersService: FiltersService,
    private authService: AuthenticationService)
  {
    this.access.canUpdate = authService.hasPrivilige("patch/workpiece/{id}");

    var date = new Date();
    var filters: WorkPieceFilters = {
      fd: undefined,
      fb: undefined,
      fid: undefined,
      fp: undefined,
      fs: undefined,
      fwob: undefined
    };
    filtersService.read("workpiece", filters);

    if (filters.fd) {
      try
      {
        date = new Date(filters.fd)
      }
      catch
      {
        console.error(`Invalid Date value of \"pd\" query param ${filters.fd}`);
      }
    }

    let defaultDate = true;
    for (let prop in filters)
      if (filters[prop] !== undefined) {
        defaultDate = false;
        switch(prop) {
          case "fid": this._filterIdChanged = true; break;
          case "fd": this._filterDateChanged = true; break;
          case "fs": this._filterStatusChanged = true; break;
          case "fp": this._filterProjectChanged = true; break;
          case "fb": this._filterBatchChanged = true; break;
          case "fwob": this._filterWOBatchChanged = true; break;
        }
      }

    if (filters.fd !== undefined || defaultDate)
      this._filterDate = { year: date.getFullYear(), month: date.getMonth() + 1, day: date.getDate() };
    this._filterId = filters.fid ?? undefined;
    this._filterStatus = filters.fs ?? undefined;
    this._filterWOBatch = filters.fwob ?? undefined;
    this._filterProject = filters.fp ?? undefined;
    this._filterBatch = filters.fb ?? undefined;
  }

  ngOnInit(): void {
    this.statuses = this.apiService.getWorkPieceStatuses();
    this.getBacthes();
  }

  ngAfterViewInit(): void {
    this.filterProjectCtrl.queryParam = this._filterProject;
    this._filterProject = this.filterProjectCtrl.value;
    this.filterBatchCtrl.queryParam = this._filterBatch;
    this._filterBatch = this.filterBatchCtrl.value;
    this.getWorkPieces();
    this.cd.detectChanges();
  }

  getWorkPieces() {
    this.noFilter = false;
    if (!this._filterDate?.year && !this._filterDate?.month && !this._filterDate?.day && !this._filterBatch && !this._filterId) {
      this.noFilter = true;
      this.workPieces$.next([]);
      return;
    }

    var startDate = this._filterDate ? Date.UTC(this._filterDate.year, this._filterDate.month - 1, this._filterDate.day, 0, 0, 0, 0) : undefined;
    var endDate = this._filterDate ? Date.UTC(this._filterDate.year, this._filterDate.month - 1, this._filterDate.day + 1, 0, 0, 0, -1) : undefined;
    this.fetchingList$.next(true);
    this.selected = [];
    this.apiService.getWorkPieces({
      with_deleted: false,
      with_details: false,
      after: new Date(startDate),
      before: new Date(endDate),
      id: (this._filterId ?? "") === "" ? undefined : this._filterId,
      project: !this.filterProjectCtrl.mask ? this.filterProject : undefined,
      project_mask: this.filterProjectCtrl.mask ? this.filterProject : undefined,
      batch: !this.filterBatchCtrl.mask ? this.filterBatch : undefined,
      batch_mask: this.filterBatchCtrl.mask ? this.filterBatch : undefined,
      status: (this._filterStatus ?? "") === "" ? undefined : this._filterStatus as WorkPieceStatus
    })
      .subscribe(r => {
        var items: WorkPieceItem[] = [];
        for (let i of r)
          items.push(i  as WorkPieceItem);
        this.workPieces$.next(items);
      },
      err => {},
      () => {
        this.fetchingList$.next(false);
      });
  }

  getBacthes() {
    this.apiService.getWorkPieceBatches()
      .subscribe(r => {
        for (let i of r)
          i.itemType = WorkPieceBatchItemType.Batch;

        r.splice(0, 0, { batch: "- munkaszám törlés -", last: undefined, itemType: WorkPieceBatchItemType.Delete });
        this.batches$.next(r);
      })
  }

  setBatchForWorkPieces(ids: string[], batch: string, remove: boolean): Observable<UpdateResult[]> {
    var reqs: Observable<UpdateResult>[] = [];
    for (let id of ids)
      reqs.push(this.apiService.updateWorkPiece(id, {
        conditions: [],
        change: {
          batch: batch,
          delete_batch: !remove ? undefined : true
        }
      }));

    return forkJoin(reqs).pipe(
      tap((results) => {
        this.getWorkPieces();
      })
    );
  }

  selectAll() {
    this.isAllSelected = !this.isAllSelected;
    for (let i of this.workPieces$.value)
      i.selected = this.isAllSelected;
  }

  select(item: WorkPieceItem, onlySelect: boolean = false, onlyDeselect: boolean = false) {
    if (onlySelect && item.selected)
      return;

    if (onlyDeselect && !item.selected)
      return;

    item.selected = !item.selected;
    let selectedItems = this.workPieces$.value.filter((value: WorkPieceItem) => { return value.selected === true });
    let allSelected = selectedItems.length === this.workPieces$.value.length;
    if (item.selected) {

      if (allSelected && !this.isAllSelected)
        this.isAllSelected = true;
    } else if (this.isAllSelected)
      this.isAllSelected = false;
  }

  filter() {
    var filters: WorkPieceFilters = {
      fd: this._filterDateChanged ? this.filterDate ? `${this.filterDate.year}-${this.filterDate.month}-${this.filterDate.day}` : undefined : undefined,
      fid: this._filterIdChanged ? (this.filterId ?? "") === "" ? undefined : this.filterId : undefined,
      fp: this._filterProjectChanged ? this.filterProjectCtrl.queryParam : undefined,
      fb: this._filterBatchChanged ? this.filterBatchCtrl.queryParam : undefined,
      fs: this._filterStatusChanged ? (this.filterStatus ?? "") === "" ? undefined : this.filterStatus : undefined,
      fwob: this._filterWOBatchChanged ? this.filterWOBatch ?? undefined : undefined
    };
    this.filtersService.save("workpiece", filters);
    this.getWorkPieces();
  }

  getSelectedCount(): number {
    return this.workPieces$.value.filter((value: WorkPieceItem) => { return value.selected }).length;
  }

  selectBatch(batch: WorkPieceBatch, isNew: boolean = false, item: WorkPieceItem) {
    let ids: string[] = item ? [item.id] :
      this.workPieces$.value.filter((item) => { return item.selected === true }).map((item) => { return item.id });
    this.setBatchForWorkPieces(ids,
      batch.itemType === WorkPieceBatchItemType.Delete ? undefined : batch.batch,
      batch.itemType === WorkPieceBatchItemType.Delete)
        .subscribe(results => {
          if (isNew)
            this.getBacthes();
        });
  }

  addNewBacth(name: string) {
    var batch: WorkPieceBatch = { batch: name, last: (new Date()).toISOString(), itemType: WorkPieceBatchItemType.Batch };
    this.selectBatch(batch, true, null);
  }

  showDialog(dialog) {
    this.modalService.open(dialog);
  }

  canAddNewBatch(): boolean {
    return this.workPieces$.value.filter((value: WorkPieceItem) => { return value.selected === true }).length > 0;
  }

  confirmBatchUpdate(dialog, batch: WorkPieceBatch, item: WorkPieceItem = null) {
    this.confirmBatchDelete = batch.itemType === WorkPieceBatchItemType.Delete;
    this.modalService.open(dialog).result.then(result => {
      if (result === "ok") {
        this.selectBatch(batch, false, item);
      }
    });
  }

  confirmStatusUpdate(dialog, status: string[], item: WorkPieceItem = null) {
    this.modalService.open(dialog).result.then(result => {
      if (result === "ok") {
        this.apiService.updateWorkPiece(item.id, {
          conditions: [],
          change: {
            status: status[0] as WorkPieceStatus
          }
        }).subscribe(r => {
          this.getWorkPieces();
        })
      }
    });
  }

  getStatusDesc(code: string): string {
    var status = this.statuses.find((s) => { return s[0] === code; });
    return status ? status[1] : code;
  }

  resetFilter() {
    this.filterId = undefined;
    this.filterDate = undefined;
    let date = new Date();
    this._filterDateChanged = false;
    this._filterDate = { year: date.getFullYear(), month: date.getMonth() + 1, day: date.getDate() };
    this.filterBatch = undefined;
    this.filterProject = undefined;
    this.filterWOBatch = undefined;
    this.filterStatus = undefined;
    this.filterBatchCtrl.queryParam = undefined;
    this.filterProjectCtrl.queryParam = undefined;
    this.filter();
  }
}
