import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { AuthenticationService } from 'src/app/services/auth.service';
import { DownloadService } from 'src/app/services/download.service';
import { WorkPiece, WorkPieceNote } from 'src/app/services/models/api';

@Component({
  selector: 'app-workpiece-detail',
  templateUrl: './workpiece-detail.component.html',
  styleUrls: ['./workpiece-detail.component.scss']
})
export class WorkpieceDetailComponent implements OnInit {

  private id: string;
  data: WorkPiece;
  notes$: BehaviorSubject<WorkPieceNote[]> = new BehaviorSubject([]);

  constructor(
    private route: ActivatedRoute,
    private authService: AuthenticationService,
    private apiService: ApiService,
    private modalService: NgbModal,
    private downloadService: DownloadService
    ) {
      this.id = route.snapshot.paramMap.get('id');
    }

  ngOnInit(): void {
    this.route.data.subscribe((r: any) => {
      this.data = r.data;
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
}
