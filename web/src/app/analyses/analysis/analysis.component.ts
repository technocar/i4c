import { DatePipe } from '@angular/common';
import { Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { Chart, ChartConfiguration, FontSpec, Legend, registerables, TitleOptions  } from 'chart.js';
import 'chartjs-adapter-date-fns';
import { _DeepPartialObject } from 'chart.js/types/utils';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiService } from 'src/app/services/api.service';
import { AuthenticationService } from 'src/app/services/auth.service';
import { Meta, StatData, StatDef, StatTimeSeriesDef } from 'src/app/services/models/api';
import { AnalysisType } from '../analyses.component';
import { AnalysisTimeseriesDefComponent } from '../defs/analysis-timeseries-def/analysis-timeseries-def.component';
import { AnalysisXyDefComponent } from '../defs/analysis-xy-def/analysis-xy-def.component';
import { AnalysisListDefComponent } from '../defs/analysis-list-def/analysis-list-def.component';
import * as Excel from "exceljs";
import { AnalysisCapabilityDefComponent } from '../defs/analysis-capability-def/analysis-capability-def.component';

Chart.register(...registerables);

@Component({
  selector: 'app-analysis',
  templateUrl: './analysis.component.html',
  styleUrls: ['./analysis.component.scss']
})
export class AnalysisComponent implements OnInit {

  private _chartInstance: Chart;

  metaList: Meta[] = [];
  def: StatDef;
  origDef: StatDef;
  analysisType: AnalysisType;
  loading$: BehaviorSubject<boolean> = new BehaviorSubject(false);
  error: boolean = false;
  errorMsg: string = "";
  showResult: boolean = false;

  @ViewChild('timeseries_def') timeseriesDef: AnalysisTimeseriesDefComponent;
  @ViewChild('xy_def') xyDef: AnalysisXyDefComponent;
  @ViewChild('list_def')  listDef: AnalysisListDefComponent;
  @ViewChild('capability_def')  capabilityDef: AnalysisCapabilityDefComponent;
  @ViewChild('new_dialog') newDialog;
  @ViewChild('chart', {static: false}) chart: ElementRef;
  @ViewChild('table', {static: false}) table: ElementRef<HTMLTableElement>;

  access = {
    canUpdate: false
  }

  constructor(
    private route: ActivatedRoute,
    private authService: AuthenticationService,
    private modalService: NgbModal,
    private apiService: ApiService,
    private router: Router
  ) {
    this.access.canUpdate = authService.hasPrivilige("patch/stat/def/{id}", "patch any");
    this.analysisType = (route.snapshot.paramMap.get("type") ?? "0") as AnalysisType;
  }

  ngOnInit(): void {
    this.route.data.subscribe(r => {
      this.metaList = r.data[1];
      this.def = r.data[0];
      this.processDef();
      if (this.def)
        this.origDef = JSON.parse(JSON.stringify(this.def));

      if (!this.access.canUpdate)
        this.getResult();
    });
  }

  processDef() {
    if (this.def.id === -1) {
      this.def.user = {
        id: this.authService.currentUserValue.id,
        login_name: this.authService.currentUserValue.username,
        name: this.authService.currentUserValue.username
      };
    } else {
      this.analysisType = this.def.timeseriesdef ? AnalysisType.TimeSeries :
        this.def.xydef ? AnalysisType.XY :
        this.def.listdef ? AnalysisType.List :
        AnalysisType.Capability;
    }
  }

  isNew(): boolean {
    return (this.def?.id ?? -1) === -1;
  }

  isOwn(): boolean {
    return this.def.user?.id == this.authService.currentUserValue.id;
  }

  hasChanges(): boolean {
    if (this.isNew())
      return true;
    return (JSON.stringify(this.origDef ?? {}) !== JSON.stringify(this.def ?? {}));
  }

  buildDef() {
    switch (this.analysisType) {
      case AnalysisType.TimeSeries:
        this.def.timeseriesdef = this.timeseriesDef.getDef() as StatTimeSeriesDef;
        break;
      case AnalysisType.XY:
        this.def.xydef = this.xyDef.getDef();
        break;
      case AnalysisType.List:
        this.def.listdef = this.listDef.getDef();
        break;
      case AnalysisType.Capability:
        this.def.capabilitydef = this.capabilityDef.getDef();
        break;
    }
  }

  getResult() {
    if (this.access.canUpdate) {
      this.buildDef();

      if (this.hasChanges()) {
        this.def.modified = (new Date()).toISOString();
      }
      var saving: Observable<boolean>;
      if (this.isNew())
        saving = this.askForName();
      else
        saving = this.save();

      saving.subscribe(r => {
        if (r)
          this.getData();
      }, (err) => {
        this.showError(this.apiService.getErrorMsg(err).toString());
      });
    } else {
      this.getData();
    }
  }

  getData() {
    this.showResult = false;
    this.error = false;
    this.errorMsg = "";

    if (this._chartInstance)
      this._chartInstance.destroy();

    this.loading$.next(true);
    this.apiService.getStatData(this.def.id)
      .subscribe(r => {
        if (this.analysisType === AnalysisType.List)
          this.buildTable(r);
        else
          this.buildChart(r);
      }, (err) => {
        this.showError(this.apiService.getErrorMsg(err).toString());
        this.loading$.next(false);
      }, () => {
        this.loading$.next(false);
      });
  }

  buildTable(result: StatData) {
    this.table.nativeElement.innerHTML = "";
    if (!result) {
      this.showError($localize `:@@table_no_data:Nincs megjeleníthető adat!`);
      return;
    }

    try {
      if (result.listdata) {
        this.table.nativeElement.append(this.buildListTable(result));
        this.showResult = true;
      }
    }
    catch(err) {
      this.showError(err);
    }
  }

  buildListTable(result: StatData): HTMLTableElement {
    if (!result?.listdata || result.listdata.length === 0)
      throw ($localize `:@@table_no_data:Nincs megjeleníthető adat!`);

    var table = this.listDef.buildTable(result);

    table.addEventListener("click", (e: KeyboardEvent) => {
      var el = e.target as HTMLElement;
      var multi = e.ctrlKey;
      if (el.nodeName.toLowerCase() === "th") {
        let field = el.getAttribute("column-name");
        if (!field)
          return;

        let direction = el.getAttribute("order-direction");
        if (direction === "asc")
          direction = "desc";
        else if (direction === "desc")
          direction = undefined;
        else
          direction = "asc";

        this.listDef.setOrder(field, direction, multi);
        this.getResult();
      }
    });

    return table;
  }

  buildChart(result: StatData) {
    if (!result) {
      this.showError($localize `:@@chart_no_data:Nincs megjeleníthető adat!`);
      return;
    }

    try {
      let ctx = this.chart.nativeElement.getContext('2d');
      let options: ChartConfiguration;
      if (result.timeseriesdata)
        options = this.buildTimeSeriesChart(result);
      else if (result.xydata)
        options = this.buildXYChart(result);
      else if (result.capabilitydata)
        options = this.buildCapabilityChart(result);

      this._chartInstance = new Chart(ctx, options);
    }
    catch(err) {
      this.showError(err);
    }
  }

  buildXYChart(result: StatData): ChartConfiguration {

    if (!result?.xydata || result.xydata.length === 0)
      throw ($localize `:@@chart_no_data:Nincs megjeleníthető adat!`);

    return this.xyDef.getChartConfiguration(result);

  }

  buildTimeSeriesChart(result: StatData): ChartConfiguration {
    if (!result?.timeseriesdata || result.timeseriesdata.length === 0)
      throw ($localize `:@@chart_no_data:Nincs megjeleníthető adat!`);

    return this.timeseriesDef.getChartConfiguration(result);
  }

  buildCapabilityChart(result: StatData): ChartConfiguration {
    if (!result?.capabilitydata)
      throw ($localize `:@@chart_no_data:Nincs megjeleníthető adat!`);

    return this.capabilityDef.getChartConfiguration(result);
  }

  save(): Observable<boolean> {
    if (!this.isOwn())
      return of(true);

    if (this.isNew())
      return this.apiService.addNewStatDef(this.def)
        .pipe(
          tap(r => {
            this.def.id = r.id;
          }),
          map(r => { return r?.id > 0 ? true : false; })
        );
    else
      return this.apiService.updateStatDef(this.def.id, {
        conditions: [],
        change: this.def
      }).pipe(
        map(r => { return r.changed; })
      );
  }

  askForName(dontSave: boolean = false): Observable<boolean> {
    var result: Observable<boolean> = new Observable((observer) => {
      this.modalService.open(this.newDialog).result.then(r => {
        if (r === "save") {
          if (!dontSave)
            this.save().subscribe(r => observer.next(r), (err => observer.error(err)));
          else
            observer.next(true);
          return true;
        } else
          observer.next(false);
          return false;
      });
    });
    return result;
  }

  shareChanged() {
    this.save().subscribe(
      r => {},
      err => {
        alert(this.apiService.getErrorMsg(err));
      }
    );
  }

  showError(message: string) {
    this.error = true;
    this.errorMsg = message;
  }

  saveAs() {
    this.askForName(true).subscribe(r => {
      if (r) {
        this.def.id = -1;
        this.def.shared = false;
        this.def.user = {
          id: this.authService.currentUserValue.id,
          name: this.authService.currentUserValue.username,
          login_name: this.authService.currentUserValue.username
        }
        this.save().subscribe(sr => {
          if (sr)
            this.router.navigate(['/analyses', this.def.id]);
        }, (err) => {
          alert(this.apiService.getErrorMsg(err));
        })
      }
    })
  }

  exportToExcel(toCSV: boolean = false) {
    let table = document.querySelector('table#result');
    console.log(table);
    const wb = new Excel.Workbook();
    const ws = wb.addWorksheet(this.def.name);

    var rows = table.querySelectorAll("tr");
    var mergeCells = [];
    for (let r = 0; r < rows.length; r++) {
      let row = (rows.item(r) as HTMLTableRowElement);
      let cells = row.childNodes;
      for (let c = 0; c < cells.length; c++) {
        let cell = cells.item(c) as HTMLTableCellElement;
        let excelCell = ws.getCell(r + 1, c + 1);
        excelCell.value = cell.textContent;
        excelCell.font = {
          bold: cell.nodeName.toLowerCase() === "th",
          color: { argb: row.getAttribute("color-fg") ? "ff" + row.getAttribute("color-fg").replace("#", "") : undefined }
        };
        if (row.classList.contains("subtitle")) {
          excelCell.font.color.argb = "ff666666";
          excelCell.font.size = 10;
        }
        excelCell.fill = {
          type: "pattern",
          pattern: "solid",
          fgColor: { argb: row.getAttribute("color-bg") ? "ff" + row.getAttribute("color-bg").replace("#", "") : undefined }
        };
        excelCell.alignment = {
          horizontal: cell.nodeName.toLowerCase() === "th" ? "center" : "left"
        };
        if (cell.colSpan > 1) {
          if (toCSV)
            for (let i = 1; i < cell.colSpan; i++)
            ws.getCell(r + 1, c +1 + i).value = "";
          else
            mergeCells.push([r + 1, c + 1, r + 1, c + cell.colSpan]);
        }
      }
    }

    if (toCSV)
      wb.csv.writeBuffer({
        formatterOptions: {
          delimiter: ';',
        }
      }).then((data) => {
        let blob = new Blob([data], { type: 'text/csv' });
        this.downloadFile(blob, "csv");
      });
    else {
      for (let mergeCell of mergeCells)
        ws.mergeCells(mergeCell[0], mergeCell[1], mergeCell[2], mergeCell[3]);

      wb.xlsx.writeBuffer().then((data) => {
        let blob = new Blob([data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
        this.downloadFile(blob, "xlsx");
      });
    }
  }

  exportToHtml() {
    let table = document.querySelector('table#result');
    let html  = table.outerHTML;
    var uint8 = new Uint8Array(html.length);
    for (var i = 0; i <  uint8.length; i++) {
      uint8[i] = html.charCodeAt(i);
    }
    let blob = new Blob([html], { type: 'text/html' });
    this.downloadFile(blob, "html");
  }

  downloadFile(blob: Blob, fileExt: string) {
    let url = window.URL.createObjectURL(blob);
    let a = document.createElement("a");
    document.body.appendChild(a);
    a.setAttribute("style", "display: none");
    a.href = url;
    a.download = `${this.def.name}.${fileExt}`;
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();
  }
}
