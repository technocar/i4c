import { Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { NgbDateStruct } from '@ng-bootstrap/ng-bootstrap/datepicker/ngb-date-struct';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { BehaviorSubject, forkJoin, Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { ApiService } from '../services/api.service';
import { UpdateResult, WorkPiece, WorkPieceBatch, WorkPieceBatchItemType, WorkPieceStatus } from '../services/models/api';

interface WorkPieceItem extends WorkPiece {
  selected: boolean
}

@Component({
  selector: 'app-workpiece',
  templateUrl: './workpiece.component.html',
  styleUrls: ['./workpiece.component.scss']
})
export class WorkPieceComponent implements OnInit {

  private _filterDate: NgbDateStruct;
  private _filterWOBatch: boolean;

  isAllSelected: boolean = false;
  workPieces$: BehaviorSubject<WorkPieceItem[]> = new BehaviorSubject([]);
  batches$: BehaviorSubject<WorkPieceBatch[]> = new BehaviorSubject([]);
  fetchingList: boolean = false;
  confirmBatchDelete: boolean = false;

  get filterDate(): NgbDateStruct {
    return this._filterDate;
  }
  set filterDate(value: NgbDateStruct) {
    this._filterDate = value;
    this.filter();
  }

  get filterWOBatch(): boolean {
    return this._filterWOBatch;
  }
  set filterWOBatch(value: boolean) {
    this._filterWOBatch = value;
    this.filter();
  }

  private selected: string[] = [];

  constructor(private apiService: ApiService, private modalService: NgbModal) {
    var date = new Date();
    this._filterDate = { year: date.getFullYear(), month: date.getMonth() + 1, day: date.getDate() };
  }

  ngOnInit(): void {
    this.getWorkPieces();
    this.getBacthes();
  }

  getWorkPieces() {
    var date = Date.UTC(this._filterDate.year, this._filterDate.month - 1, this._filterDate.day, 0, 0, 0, 0);
    this.fetchingList = true;
    this.selected = [];
    this.apiService.getWorkPieces({ with_deleted: false, with_details: false, after: new Date(date) })
      .subscribe(r => {
        var items: WorkPieceItem[] = [];
        for (let i of r)
          items.push(i  as WorkPieceItem);
        this.workPieces$.next(items);
      },
      err => {},
      () => {
        this.fetchingList = false;
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
}
