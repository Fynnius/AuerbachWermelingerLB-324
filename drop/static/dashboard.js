// Dashboard: lädt /dashboard/data und zeichnet Tabelle, 7-Tage-Verlauf und
// Geräteverteilung. Ohne Bibliothek; Daten nur per textContent ins DOM.
(function () {
  "use strict";

  var SVG_NS = "http://www.w3.org/2000/svg";
  var DAYS = 7;
  var DEVICE_LABELS = {
    mobile: "Mobil",
    desktop: "Desktop",
    bot: "Bot",
    other: "Andere",
  };

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function svg(tag, attrs) {
    var node = document.createElementNS(SVG_NS, tag);
    Object.keys(attrs || {}).forEach(function (name) {
      node.setAttribute(name, String(attrs[name]));
    });
    return node;
  }

  // Lokaler Kalendertag als Schlüssel, z. B. "2026-10-26".
  function dayKey(date) {
    var month = String(date.getMonth() + 1).padStart(2, "0");
    var day = String(date.getDate()).padStart(2, "0");
    return date.getFullYear() + "-" + month + "-" + day;
  }

  function lastDays() {
    var days = [];
    var today = new Date();
    for (var i = DAYS - 1; i >= 0; i--) {
      var date = new Date(today.getFullYear(), today.getMonth(), today.getDate() - i);
      days.push({
        key: dayKey(date),
        label: date.toLocaleDateString("de-CH", { weekday: "short", day: "numeric" }),
        count: 0,
      });
    }
    return days;
  }

  function renderTable(links) {
    var body = document.getElementById("dashboard-links");
    body.replaceChildren();
    if (links.length === 0) {
      var row = el("tr");
      var cell = el("td", "muted", "Noch keine Links.");
      cell.colSpan = 4;
      row.appendChild(cell);
      body.appendChild(row);
      return;
    }
    links.forEach(function (link) {
      var row = el("tr");
      row.appendChild(el("td", "slug", link.slug));
      row.appendChild(el("td", null, link.kind === "url" ? "Kurzlink" : "Drop"));
      row.appendChild(
        link.kind === "url"
          ? el("td", "target", link.target)
          : el("td", "target muted", "verschlüsselter Drop")
      );
      row.appendChild(el("td", "num", String(link.clicks)));
      body.appendChild(row);
    });
  }

  function renderChart(links) {
    var days = lastDays();
    var byKey = {};
    days.forEach(function (day) {
      byKey[day.key] = day;
    });
    links.forEach(function (link) {
      link.visits.forEach(function (visit) {
        var day = byKey[dayKey(new Date(visit.at))];
        if (day) day.count += 1;
      });
    });

    var width = 420;
    var height = 200;
    var top = 20;
    var bottom = 28;
    var plot = height - top - bottom;
    var slot = width / DAYS;
    var barWidth = slot * 0.6;
    var max = Math.max(1, Math.max.apply(null, days.map(function (d) { return d.count; })));
    var total = days.reduce(function (sum, d) { return sum + d.count; }, 0);

    var chart = svg("svg", {
      viewBox: "0 0 " + width + " " + height,
      role: "img",
      "aria-label": "Besuche pro Tag, letzte 7 Tage: insgesamt " + total,
    });
    chart.appendChild(
      svg("line", { x1: 0, x2: width, y1: top + plot, y2: top + plot, class: "axis" })
    );

    days.forEach(function (day, index) {
      var barHeight = (day.count / max) * plot;
      var x = index * slot + (slot - barWidth) / 2;
      var y = top + plot - barHeight;
      var bar = svg("rect", {
        x: x,
        y: y,
        width: barWidth,
        height: barHeight,
        rx: 3,
        class: "bar",
      });
      var title = svg("title");
      title.textContent = day.label + ": " + day.count;
      bar.appendChild(title);
      chart.appendChild(bar);

      var value = svg("text", { x: x + barWidth / 2, y: y - 6, class: "value" });
      value.textContent = String(day.count);
      chart.appendChild(value);

      var label = svg("text", { x: x + barWidth / 2, y: height - 8, class: "label" });
      label.textContent = day.label;
      chart.appendChild(label);
    });

    var container = document.getElementById("dashboard-chart");
    container.replaceChildren(chart);
  }

  function renderDevices(links) {
    var counts = { mobile: 0, desktop: 0, bot: 0, other: 0 };
    var total = 0;
    links.forEach(function (link) {
      link.visits.forEach(function (visit) {
        var device = Object.prototype.hasOwnProperty.call(counts, visit.device)
          ? visit.device
          : "other";
        counts[device] += 1;
        total += 1;
      });
    });

    var list = document.getElementById("dashboard-devices");
    list.replaceChildren();
    if (total === 0) {
      list.appendChild(el("li", "muted", "Noch keine Besuche."));
      return;
    }
    Object.keys(counts).forEach(function (device) {
      var item = el("li");
      item.appendChild(el("span", "device-name", DEVICE_LABELS[device]));
      var track = el("span", "device-track");
      var fill = el("span", "device-fill");
      fill.style.width = (counts[device] / total) * 100 + "%";
      track.appendChild(fill);
      item.appendChild(track);
      item.appendChild(el("span", "num", String(counts[device])));
      list.appendChild(item);
    });
  }

  function load() {
    var status = document.getElementById("dashboard-status");
    fetch("/dashboard/data", { credentials: "same-origin" })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (links) {
        renderTable(links);
        renderChart(links);
        renderDevices(links);
        status.hidden = true;
      })
      .catch(function () {
        status.textContent = "Statistik konnte nicht geladen werden.";
      });
  }

  document.addEventListener("DOMContentLoaded", load);
})();
