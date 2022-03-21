import { Injectable } from "@angular/core";
import { StatDef } from "src/app/services/models/api";

export enum AnalysisType { TimeSeries = '0', XY = '1', List = '2', Capability = '3' }

Injectable({ providedIn: 'root' });
export class AnalysisService {
     analysisTypes: string[][] = [
        [AnalysisType.TimeSeries, $localize `:@@analysis_type_timeseries:idősoros`],
        [AnalysisType.XY, $localize `:@@analysis_type_xy:xy`],
        [AnalysisType.List, $localize `:@@analysis_type_list:lista`],
        [AnalysisType.Capability, $localize `:@@analysis_type_capability:capability`]
      ]  
      getAnalysisType(analysis: StatDef): AnalysisType {
        return analysis.timeseriesdef ? AnalysisType.TimeSeries :
          analysis.xydef ? AnalysisType.XY :
          analysis.listdef ? AnalysisType.List :
          analysis.capabilitydef ? AnalysisType.Capability :
          AnalysisType.TimeSeries;
      }
    
      getAnalysisTypeDesc(code: AnalysisType): string {
        var type = this.analysisTypes.find((t) => { return t[0] === code; });
        if (type)
          return type[1];
        else
          return code;
      }        
}