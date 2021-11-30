import { StatVisualSettingsLegendAlign, StatVisualSettingsLegendPosition } from "./api";

export enum DeviceType { Mill = "mill", Lathe = "lathe", GOM = "gom", Robot = "robot" }

export class Labels {

  static analysis = {
    legend: {
      positions: [
        [StatVisualSettingsLegendPosition.Top, $localize `:@@analysis_legend_position_top:Fent`],
        [StatVisualSettingsLegendPosition.Bottom, $localize `:@@analysis_legend_position_bottom:Lent`],
        [StatVisualSettingsLegendPosition.Left, $localize `:@@analysis_legend_position_left:Baloldal`],
        [StatVisualSettingsLegendPosition.Right, $localize `:@@analysis_legend_position_right:Jobboldal`]
      ],
      aligns: [
        [StatVisualSettingsLegendAlign.Start, $localize `:@@analysis_legend_align_start:Elől`],
        [StatVisualSettingsLegendAlign.End, $localize `:@@analysis_legend_align_end:Hátul`],
        [StatVisualSettingsLegendAlign.Center, $localize `:@@analysis_legend_align_center:Középen`]
      ]
    }
  }

}
