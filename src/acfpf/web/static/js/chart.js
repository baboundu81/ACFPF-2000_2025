// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright (C) 2026 ACFPF contributors

(() => {
  const svg = document.getElementById("macro-chart");
  const dataNode = document.getElementById("chart-data");
  if (!svg || !dataNode) return;

  const payload = JSON.parse(dataNode.textContent);
  const series = ["expenditure", "revenue"]
    .map((key) => [key, payload[key]])
    .filter(([, item]) => item && Array.isArray(item.values) && item.values.length > 0);
  if (series.length === 0) return;

  const width = 920;
  const height = 420;
  const margin = { top: 22, right: 28, bottom: 48, left: 58 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;

  const allPoints = series.flatMap(([, item]) => item.values);
  const years = allPoints.map((point) => point.year);
  const values = allPoints.map((point) => point.value);
  const minYear = Math.min(...years);
  const maxYear = Math.max(...years);
  const maxValue = Math.ceil(Math.max(...values) / 10) * 10;
  const yMax = Math.max(10, maxValue);

  const x = (year) => margin.left + ((year - minYear) / (maxYear - minYear || 1)) * plotWidth;
  const y = (value) => margin.top + plotHeight - (value / yMax) * plotHeight;

  const create = (name, attributes = {}) => {
    const node = document.createElementNS("http://www.w3.org/2000/svg", name);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
    return node;
  };

  const ticks = 5;
  for (let index = 0; index <= ticks; index += 1) {
    const value = (yMax / ticks) * index;
    const yPos = y(value);
    svg.appendChild(create("line", {
      x1: margin.left,
      x2: width - margin.right,
      y1: yPos,
      y2: yPos,
      class: "chart-grid",
    }));

    const label = create("text", {
      x: margin.left - 10,
      y: yPos + 4,
      "text-anchor": "end",
      class: "chart-axis-label",
    });
    label.textContent = `${value.toFixed(0)} %`;
    svg.appendChild(label);
  }

  const yearTicks = [...new Set([minYear, 2005, 2010, 2015, 2020, maxYear])]
    .filter((year) => year >= minYear && year <= maxYear);
  yearTicks.forEach((year) => {
    const label = create("text", {
      x: x(year),
      y: height - 14,
      "text-anchor": year === minYear ? "start" : year === maxYear ? "end" : "middle",
      class: "chart-axis-label",
    });
    label.textContent = year;
    svg.appendChild(label);
  });

  series.forEach(([key, item]) => {
    const points = item.values
      .slice()
      .sort((a, b) => a.year - b.year)
      .map((point) => `${x(point.year)},${y(point.value)}`)
      .join(" ");

    svg.appendChild(create("polyline", {
      points,
      class: `chart-line chart-line--${key}`,
    }));

    item.values.forEach((point) => {
      const dot = create("circle", {
        cx: x(point.year),
        cy: y(point.value),
        r: point.year === maxYear ? 4.5 : 2.4,
        class: `chart-point chart-point--${key}`,
      });
      const title = create("title");
      title.textContent = `${item.label} — ${point.year} : ${point.value.toFixed(1)} % du PIB`;
      dot.appendChild(title);
      svg.appendChild(dot);
    });
  });
})();
