import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { AuthenticationService } from 'src/app/services/auth.service';
import { DownloadService } from 'src/app/services/download.service';
import { Device, WorkPiece, WorkPieceNote } from 'src/app/services/models/api';
import { DeviceType } from 'src/app/services/models/constants';

@Component({
  selector: 'app-workpiece-detail',
  templateUrl: './workpiece-detail.component.html',
  styleUrls: ['./workpiece-detail.component.scss']
})
export class WorkpieceDetailComponent implements OnInit {

  private id: string;
  data: WorkPiece;
  notes$: BehaviorSubject<WorkPieceNote[]> = new BehaviorSubject([]);
  statuses: string[][] = [];
  devices: Device[] = [];

  constructor(
    private route: ActivatedRoute,
    private authService: AuthenticationService,
    private apiService: ApiService,
    private modalService: NgbModal,
    private downloadService: DownloadService
    ) {
      this.id = route.snapshot.paramMap.get('id');
      apiService.getDevices().subscribe(r => this.devices = r);
    }

  ngOnInit(): void {
    this.statuses = this.apiService.getWorkPieceStatuses();
    this.route.data.subscribe((r: any) => {
      this.data = r.workpiece;
      this.notes$.next(this.data.notes);
    });
  }

  getData() {
    this.apiService.getWorkPiece(this.id, true)
      .subscribe(r => {
        this.data = r;
        this.notes$.next(r.notes);
      })
  }

  addNote(text: string) {
    var user = this.authService.currentUserValue;
    this.apiService.updateWorkPiece(this.id, {
      conditions: [],
      change: {
        add_note: [{
          timestamp: new Date(),
          user: user.id,
          text: text
        }]
      }
    }).subscribe(r => {
      this.modalService.dismissAll();
      this.getData();
    }, (err) => {
      alert(this.apiService.getErrorMsg(err));
    })
  }

  showDialog(dialog) {
    this.modalService.open(dialog);
  }

  askNoteDelete(dialog, noteId: number) {
    this.modalService.open(dialog).result.then(result => {
      if (result === "ok") {
        this.apiService.updateWorkPiece(this.id, {
          conditions: [],
          change: {
            delete_note: [noteId]
          }
        }).subscribe(r => {
          this.getData();
        })
      }
    });
  }

  getFile(filename: string) {
    var download = this.apiService.getFile('test.pdf', 2);
    this.downloadService.register(download);
    this.downloadService.download();
  }

  getStatusDesc(code: string): string {
    var status = this.statuses.find((s) => { return s[0] === code; });
    return status ? status[1] : code;
  }

  getDeviceName(deviceId: DeviceType): string {
    let device = this.devices.find(d => d.id === deviceId);
    if (device)
      return device.name;
    else
      return deviceId;
  }
}
