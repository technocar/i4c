import { TitleOptions } from "chart.js";
import { _DeepPartialObject } from "chart.js/types/utils";

export class HSLAColor {
  hue: number;
  saturation: number;
  lightness: number;
  alpha: number;

  constructor(hue: number, saturation: number, lightess: number, alpha: number) {
    this.hue = hue;
    this.saturation = saturation;
    this.lightness = lightess;
    this.alpha = alpha;
  }

  public toString(): string {
    return `hsla(${Math.round(this.hue)}, ${Math.round(this.saturation * 100)}%, ${Math.round(this.lightness * 100) }%, ${this.alpha})`;
  }
}

export class AnalysisHelpers {

  public static getChartSeriesColor(index: number, count: number, firstColor: HSLAColor, lastColor: HSLAColor, alpha: number): HSLAColor {
    var hsl2hsv = (h,s,l,v=s*Math.min(l,1-l)+l) => [h, v?2-2*l/v:0, v];
    let hsv2hsl = (h,s,v,l=v-v*s/2, m=Math.min(l,1-l)) => [h,m?(v-l)/m:0,l];
    var hsvA = hsl2hsv(firstColor.hue, firstColor.saturation, firstColor.lightness);
    var hsvB = hsl2hsv(lastColor.hue, lastColor.saturation, lastColor.lightness);
    var hsvColor = [
      hsvA[0] * (count - (index + 1)) / count + hsvB[0] * (index + 1) / count,
      hsvA[1] * (count - (index + 1)) / count + hsvB[1] * (index + 1) / count,
      hsvA[2] * (count - (index + 1)) / count + hsvB[2] * (index + 1) / count
    ];
    var hslColor = hsv2hsl(hsvColor[0], hsvColor[1], hsvColor[2]);
    var color = new HSLAColor(hslColor[0], hslColor[1], hslColor[2], alpha);
    console.log(color.toString());
    return color;
  }

  public static setChartTitle(title: string): _DeepPartialObject<TitleOptions> {
    return {
      display: (title ?? "") !== "",
      text: title
    };
  }
}
