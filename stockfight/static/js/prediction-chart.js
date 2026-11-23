(() => {
    "use strict";

    const compact = new Intl.NumberFormat("sv-SE", { notation: "compact", maximumFractionDigits: 1 });
    const decimal = new Intl.NumberFormat("sv-SE", { maximumFractionDigits: 2 });
    const minimumRadiusBps = 500;

    function axisLabel(bps) {
        const format = Math.abs(bps) >= 1_000_000 ? compact : decimal;
        return `${bps > 0 ? "+" : ""}${format.format(bps / 100)} %`;
    }

    function chartRadius(history, forecast) {
        const historyExtent = Math.max(...history.map((point) => Math.abs(point.bps)));
        const extent = Math.max(minimumRadiusBps, historyExtent * 1.15, ...forecast.map((move) => Math.abs(move ?? 0)));
        const unit = 10 ** Math.floor(Math.log10(extent));
        const step = [1, 2, 2.5, 5, 10].find((value) => value * unit >= extent) ?? 10;
        return step * unit;
    }

    window.createPredictionChart = (canvas, drawTarget, onDraw) => {
        const context = canvas.getContext("2d");
        if (!context) return () => {};

        const theme = getComputedStyle(canvas);
        const colors = {
            grid: theme.getPropertyValue("--chart-line").trim(),
            labels: theme.getPropertyValue("--chart-label").trim(),
            history: "#a8bfd6",
            future: "#162232",
            actual: theme.getPropertyValue("--chart-price").trim(),
            self: theme.getPropertyValue("--prediction-self").trim(),
            opponent: theme.getPropertyValue("--gold").trim(),
        };
        let view;
        let plot;
        let drag;

        function draw() {
            const width = canvas.clientWidth;
            const height = canvas.clientHeight;
            if (!width || !height) {
                plot = undefined;
                drawTarget?.setAttribute("hidden", "");
                return;
            }
            const ratio = window.devicePixelRatio || 1;
            const pixelWidth = Math.round(width * ratio);
            const pixelHeight = Math.round(height * ratio);
            if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
                canvas.width = pixelWidth;
                canvas.height = pixelHeight;
            }
            context.setTransform(ratio, 0, 0, ratio, 0, 0);
            context.clearRect(0, 0, width, height);
            plot = undefined;
            const bars = view?.outcome ? view.bars.slice(0, -1) : view?.bars;
            const last = bars?.at(-1);
            const base = Number(last?.close);
            if (!base) {
                drawTarget?.setAttribute("hidden", "");
                return;
            }
            const history = bars.map(({ time, close }) => ({
                time: time - last.time,
                bps: (Number(close) / base - 1) * 10_000,
            }));
            const own = view.outcome ? view.outcome.selfMoveBps : view.guess;
            const opponent = view.outcome?.opponentMoveBps;
            const actual = view.outcome?.actualMoveBps;
            const radius = drag?.radius ?? chartRadius(history, [own, opponent, actual]);

            context.font = "11px system-ui, sans-serif";
            const ticks = [radius, radius / 2, 0, -radius / 2, -radius]
                .map((bps) => ({ bps, label: axisLabel(bps) }));
            const top = 16;
            const bottom = height - 29;
            const left = Math.ceil(Math.max(...ticks.map(({ label }) => context.measureText(label).width))) + 13;
            const right = width - 14;
            const plotWidth = right - left;
            const anchor = left + plotWidth * 0.59;
            const end = right - plotWidth * 0.12;
            const y = (bps) => top + (bottom - top) * (1 - bps / radius) / 2;
            const firstTime = Math.min(-1, history[0].time);
            const x = (time) => left + (anchor - left) * (time - firstTime) / -firstTime;
            plot = { top, bottom, radius };
            const editable = drawTarget && view.editable && end > anchor && bottom > top;
            if (editable) {
                Object.assign(drawTarget.style, {
                    left: `${anchor}px`,
                    top: `${top}px`,
                    width: `${end - anchor}px`,
                    height: `${bottom - top}px`,
                });
            }
            drawTarget?.toggleAttribute("hidden", !editable);

            context.fillStyle = colors.future;
            context.fillRect(anchor, top, end - anchor, bottom - top);
            context.textBaseline = "middle";
            context.textAlign = "right";
            for (const { bps, label } of ticks) {
                segment(left, y(bps), right, y(bps), bps === 0 ? "#536982" : colors.grid);
                context.fillStyle = colors.labels;
                context.fillText(label, left - 7, y(bps));
            }
            segment(anchor, top, anchor, bottom, "#536982", [4, 4]);
            segment(end, top, end, bottom, colors.grid);
            context.textAlign = "center";
            context.fillStyle = colors.labels;
            context.fillText("Historik", (left + anchor) / 2, height - 11);
            context.fillText(editable ? "Rita prognos" : "Nästa punkt", (anchor + end) / 2, height - 11);

            context.beginPath();
            context.strokeStyle = colors.history;
            context.lineWidth = 2;
            history.forEach((point, index) => {
                if (index === 0) context.moveTo(x(point.time), y(point.bps));
                else context.lineTo(x(point.time), y(point.bps));
            });
            context.stroke();
            mark(anchor, y(0), colors.history, 3);

            function forecast(move, color, dash, thickness) {
                if (move == null) return;
                segment(anchor, y(0), end, y(move), color, dash, thickness);
                mark(end, y(move), color, thickness + 1);
            }

            forecast(own, colors.self, [5, 4], 2);
            forecast(opponent, colors.opponent, [2, 4], 2);
            forecast(actual, colors.actual, [], 3);
        }

        function segment(startX, startY, endX, endY, color, dash = [], thickness = 1) {
            context.beginPath();
            context.strokeStyle = color;
            context.lineWidth = thickness;
            context.setLineDash(dash);
            context.moveTo(startX, startY);
            context.lineTo(endX, endY);
            context.stroke();
            context.setLineDash([]);
        }

        function mark(x, y, color, size) {
            context.beginPath();
            context.fillStyle = color;
            context.arc(x, y, size, 0, 2 * Math.PI);
            context.fill();
        }

        function updatePointer(event, bounds) {
            const y = event.clientY - bounds.top;
            const position = Math.min(1, Math.max(0, (y - plot.top) / (plot.bottom - plot.top)));
            const bps = Math.round(plot.radius * (1 - 2 * position));
            onDraw(Math.max(-10_000, Math.min(Number.MAX_SAFE_INTEGER, bps)));
        }

        drawTarget?.addEventListener("pointerdown", (event) => {
            if (!view?.editable || !plot || drag || event.button !== 0) return;
            drag = { pointer: event.pointerId, radius: plot.radius };
            drawTarget.setPointerCapture(event.pointerId);
            updatePointer(event, canvas.getBoundingClientRect());
        });
        drawTarget?.addEventListener("pointermove", (event) => {
            if (event.pointerId === drag?.pointer && plot) {
                updatePointer(event, canvas.getBoundingClientRect());
            }
        });
        drawTarget?.addEventListener("lostpointercapture", (event) => {
            if (event.pointerId !== drag?.pointer) return;
            drag = undefined;
            draw();
        });
        if (window.ResizeObserver) new ResizeObserver(draw).observe(canvas);
        else window.addEventListener("resize", draw);

        return (data) => {
            view = data;
            if (!view?.editable && drag) {
                if (drawTarget.hasPointerCapture(drag.pointer)) drawTarget.releasePointerCapture(drag.pointer);
                drag = undefined;
            }
            draw();
        };
    };
})();
