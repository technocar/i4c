import { AfterViewInit, ChangeDetectorRef, Component, OnInit, ViewChild } from '@angular/core';
import { NgbDateStruct } from '@ng-bootstrap/ng-bootstrap/datepicker/ngb-date-struct';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { BehaviorSubject, forkJoin, Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { ApiService } from '../../services/api.service';
import { UpdateResult, WorkPiece, WorkPieceBatch, WorkPieceBatchItemType, WorkPieceStatus } from '../../services/models/api';
import { ActivatedRoute, Router } from '@angular/router';
import { FilterControlComponent } from 'src/app/commons/filter/filter.component';

interface WorkPieceItem extends WorkPiece {
  selected: boolean
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

  isAllSelected: boolean = false;
  workPieces$: BehaviorSubject<WorkPieceItem[]> = new BehaviorSubject([]);
  batches$: BehaviorSubject<WorkPieceBatch[]> = new BehaviorSubject([]);
  fetchingList$: BehaviorSubject<boolean> = new BehaviorSubject(false);
  confirmBatchDelete: boolean = false;

  queryParamProject: string;
  queryParamBatch: string;

  get filterDate(): NgbDateStruct {
    return this._filterDate;
  }
  set filterDate(value: NgbDateStruct) {
    this._filterDate = value;
    this.filter();
  }
  filterId: string;
  get filterProject(): string {
    return this._filterProject;
  }
  set filterProject(value: string) {
    this._filterProject = value;
    this.filter();
  }
  get filterBatch(): string {
    return this._filterBatch;
  }
  set filterBatch(value: string) {
    this._filterBatch = value;
    this.filter();
  }
  filterStatus: string;

  get filterWOBatch(): boolean {
    return this._filterWOBatch;
  }
  set filterWOBatch(value: boolean) {
    this._filterWOBatch = value;
    this.filter();
  }

  statuses = [
    ['', ' - '],
    ['good', $localize `:@@workpiece_status_good:Megfelel`],
    ['bad', $localize `:@@workpiece_status_bad:Selejt`],
    ['inprogress', $localize `:@@workpiece_status_inprogress:Folyamatban`],
    ['unknown', $localize `:@@workpiece_status_unknown:Ismeretlen`]
  ];

  private selected: string[] = [];

  constructor(
    private apiService: ApiService,
    private modalService: NgbModal,
    private route: ActivatedRoute,
    private router: Router,
    private cd: ChangeDetectorRef) {
    var date = new Date();
    var pDate = route.snapshot.queryParamMap.get("fd");
    if (pDate) {
      try
      {
        date = new Date(pDate)
      }
      catch
      {
        console.error(`Invalid Date value of \"pd\" query param ${pDate}`);
      }
    }
    this._filterDate = { year: date.getFullYear(), month: date.getMonth() + 1, day: date.getDate() };
    this.filterId = route.snapshot.queryParamMap.get("fid") ?? undefined;
    this.filterStatus = route.snapshot.queryParamMap.get("fs") ?? undefined;
  }

  ngOnInit(): void {
    this.getBacthes();

  }

  ngAfterViewInit(): void {
    this.filterProjectCtrl.queryParam = this.route.snapshot.queryParamMap.get("fp") ?? undefined;
    this._filterProject = this.filterProjectCtrl.value;
    this.filterBatchCtrl.queryParam = this.route.snapshot.queryParamMap.get("fb") ?? undefined;
    this._filterBatch = this.filterBatchCtrl.value;
    this.getWorkPieces();
    this.cd.detectChanges();
  }

  getWorkPieces() {
    var date = Date.UTC(this._filterDate.year, this._filterDate.month - 1, this._filterDate.day, 0, 0, 0, 0);
    this.fetchingList$.next(true);
    this.selected = [];
    this.apiService.getWorkPieces({
      with_deleted: false,
      with_details: false,
      after: new Date(date),
      id: (this.filterId ?? "") === "" ? undefined : this.filterId,
      project: !this.filterProjectCtrl.mask ? this.filterProject : undefined,
      project_mask: this.filterProjectCtrl.mask ? this.filterProject : undefined,
      batch: !this.filterBatchCtrl.mask ? this.filterBatch : undefined,
      batch_mask: this.filterBatchCtrl.mask ? this.filterBatch : undefined,
      status: (this.filterStatus ?? "") === "" ? undefined : this.filterStatus as WorkPieceStatus
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

  select(item: WorkPieceItem) {
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
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: {
        fd: `${this.filterDate.year}-${this.filterDate.month}-${this.filterDate.day}`,
        fid: (this.filterId ?? "") === "" ? undefined : this.filterId,
        fp: this.filterProjectCtrl.queryParam,
        fb: this.filterBatchCtrl.queryParam,
        fs: (this.filterStatus ?? "") === "" ? undefined : this.filterStatus,
        fwob: this.filterWOBatch
      },
      queryParamsHandling: 'merge'
    });
    this.getWorkPieces();
  }

  getSelectedCount(): number {
    return this.workPieces$.value.filter((value: WorkPieceItem) => { return value.selected }).length;
  }

  selectBatch(batch: WorkPieceBatch, isNew: boolean = false) {
    let ids: string[] = this.workPieces$.value.filter((item) => { return item.selected === true }).map((item) => { return item.id });
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
    this.selectBatch(batch, true);
  }

  showDialog(dialog) {
    this.modalService.open(dialog);
  }

  canAddNewBatch(): boolean {
    return this.workPieces$.value.filter((value: WorkPieceItem) => { return value.selected === true }).length > 0;
  }

  confirmBatchUpdate(dialog, batch: WorkPieceBatch) {
    this.confirmBatchDelete = batch.itemType === WorkPieceBatchItemType.Delete;
    this.modalService.open(dialog).result.then(result => {
      if (result === "ok") {
        this.selectBatch(batch);
      }
    });
  }

  getStatusDesc(code: string): string {
    var status = this.statuses.find((s) => { return s[0] === code; });
    return status ? status[1] : code;
  }
}
