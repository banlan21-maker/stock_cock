"use client";

import { useEffect, useRef } from "react";
import { createChart, CandlestickSeries } from "lightweight-charts";
import type { ChartDataPoint } from "@/types";

const HEIGHT = 320;
const UP_COLOR = "#22C55E";
const DOWN_COLOR = "#EF4444";

function toCandleItem(d: ChartDataPoint): { time: string; open: number; high: number; low: number; close: number } {
  const time = d.date.includes("T") ? d.date.slice(0, 10) : d.date;
  return { time, open: d.open, high: d.high, low: d.low, close: d.close };
}

interface StockChartProps {
  data: ChartDataPoint[];
  height?: number;
  className?: string;
}

export default function StockChart({ data, height = HEIGHT, className = "" }: StockChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || !data.length) return;

    const chart = createChart(containerRef.current, {
      layout: { background: { color: "transparent" }, textColor: "#9ca3af" },
      grid: { vertLines: { color: "rgba(255,255,255,0.06)" }, horzLines: { color: "rgba(255,255,255,0.06)" } },
      width: containerRef.current.clientWidth,
      height,
      rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.1, bottom: 0.2 } },
      timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: UP_COLOR,
      downColor: DOWN_COLOR,
      borderVisible: false,
      wickUpColor: UP_COLOR,
      wickDownColor: DOWN_COLOR,
    });

    candleSeries.setData(data.map(toCandleItem));

    const handleResize = () => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth });
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [data, height]);

  if (!data.length) return null;

  return <div ref={containerRef} className={className} style={{ height }} />;
}
