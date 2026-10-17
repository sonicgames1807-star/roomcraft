#!/usr/bin/env python3
"""RoomCraft — single-file, privacy-first room editor.

PARTIAL IMPLEMENTATION of RoomCraft R001–R700, not a 10,000-line completion.
Room editing uses a manual parametric room. Optional browser depth estimation
creates a 2.5D photo relief, not a complete measured room. Cozy uses rules.

Local setup:
    python -m pip install streamlit
    python -m streamlit run main.py
Other modes (stdlib only):
    python main.py --self-test
    python main.py --export-html roomcraft.html

Python dependency: streamlit (tested separately; see handoff).
Browser dependencies: Three.js 0.170.0, served by jsDelivr. Internet required.
Personal photographs never enter Python in this implementation.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import unittest
from pathlib import Path

APP_VERSION = "0.1.0"
SCHEMA_VERSION = 1


def finite_number(value, lower, upper):
    """Parse a finite bounded number; support Russian decimal separators."""
    if isinstance(value, bool):
        raise ValueError("Boolean is not a measurement")
    result = float(str(value).replace(",", "."))
    if not math.isfinite(result) or not lower <= result <= upper:
        raise ValueError("Measurement outside allowed range")
    return result


def polygon_area(points):
    if len(points) < 3:
        return 0.0
    return abs(sum(
        points[i][0] * points[(i + 1) % len(points)][1]
        - points[(i + 1) % len(points)][0] * points[i][1]
        for i in range(len(points))
    )) / 2


def safe_csv_cell(value):
    text = str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")):
        text = "'" + text
    return '"' + text.replace('"', '""') + '"'


HTML = r'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>RoomCraft / Студия комнаты</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='16' fill='%23285546'/%3E%3Cpath d='M16 24 32 15 48 24v18L32 51 16 42Zm0 0 16 9 16-9M32 33v18' fill='none' stroke='white' stroke-width='3'/%3E%3C/svg%3E">
<style>
:root {
  --bg: #f6f5f1;
  --panel: #ffffff;
  --ink: #242c29;
  --muted: #626d65;
  --line: #e1e5df;
  --green: #285546;
  --light: #edf3ed;
  --gold: #b88d50;
  --danger: #a92c32;
  --warn: #855c16;
  --radius: 14px;
  --ease: cubic-bezier(.22,1,.36,1);
  font-family: 'Onest', ui-sans-serif, system-ui, -apple-system, sans-serif;
  font-synthesis: none;
  color: var(--ink);
  background: var(--bg);
}
* { box-sizing: border-box; }
body { margin: 0; min-width: 320px; }
button, input, select { font: inherit; }
button { cursor: pointer; }
button, input, select, summary { -webkit-tap-highlight-color: transparent; }
button:focus-visible, input:focus-visible, select:focus-visible,
a:focus-visible, summary:focus-visible {
  outline: 3px solid #a56b1a;
  outline-offset: 3px;
}
button:disabled { cursor: not-allowed; opacity: .45; }
button svg { pointer-events: none; flex-shrink: 0; }
[hidden] { display: none !important; }
button { touch-action: manipulation; }
svg { width: 20px; height: 20px; vertical-align: middle; }
h1, h2, h3, p { margin: 0; }
h1, h2, h3 { text-wrap: balance; }
button, label { user-select: none; }
input, select {
  min-width: 0;
  width: 100%;
  min-height: 44px;
  border: 1px solid #c5cec5;
  border-radius: 8px;
  padding: 9px 11px;
  color: var(--ink);
  background: white;
}
input[type="color"] { padding: 4px; height: 44px; }
input[type="checkbox"] { width: 19px; min-height: 19px; accent-color: var(--green); }
input[type="range"] { border: 0; padding: 0; accent-color: var(--green); }
.field { display: grid; gap: 7px; font-size: 14px; color: var(--muted); }
.fields { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.fields.three { grid-template-columns: repeat(3, 1fr); }
.row { display: flex; align-items: center; gap: 8px; }
.between { justify-content: space-between; }
.wrap { flex-wrap: wrap; }
.muted { color: var(--muted); }
.small { font-size: 13px; line-height: 1.55; }
.stack { display: grid; gap: 16px; }
.divider { height: 1px; background: var(--line); margin: 20px 0; }
.btn {
  border: 1px solid #cdd6cd;
  border-radius: 999px;
  background: transparent;
  padding: 10px 17px;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--ink);
  text-decoration: none;
  transition: background 180ms, transform 220ms var(--ease);
}
.btn:hover:not(:disabled) { background: #e8eee7; transform: translateY(-1px); }
.btn.primary { background: var(--green); color: white; border-color: transparent; }
.btn.primary:hover:not(:disabled) { background: #1a4133; }
.btn.danger { color: var(--danger); border-color: #e7c4c5; }
.btn.full { width: 100%; }
.icon-btn {
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: inherit;
  min-width: 44px;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.icon-btn:hover { background: var(--light); }
.icon-btn.active { background: var(--green); color: white; }
.app-header {
  min-height: 78px;
  padding: 12px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--line);
  background: var(--panel);
}
.brand { display: flex; align-items: center; gap: 11px; }
.brand-mark {
  width: 39px;
  height: 39px;
  border-radius: 11px;
  background: var(--green);
  color: white;
  display: grid;
  place-items: center;
}
.brand-mark svg { width: 25px; height: 25px; }
.brand-name { font-size: 22px; letter-spacing: -.8px; font-weight: 600; }
.brand-sub { font-size: 11px; letter-spacing: 1.7px; text-transform: uppercase; margin-top: 2px; }
.header-divider { width: 1px; height: 30px; background: var(--line); margin: 0 9px; }
.project-title {
  border: 0;
  background: transparent;
  width: 215px;
  padding: 8px;
  font-size: 14px;
}
.save-state { font-size: 12px; color: var(--muted); }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: #4d7a56; }
.intro {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 28px 32px 24px;
}
.eyebrow { font-size: 11px; letter-spacing: 1.6px; text-transform: uppercase; color: var(--green); margin-bottom: 8px; }
.intro h1 { font-size: clamp(26px, 3vw, 37px); letter-spacing: -1.4px; line-height: 1.12; font-weight: 400; }
.intro p { max-width: 58ch; font-size: 14px; line-height: 1.6; color: var(--muted); margin-top: 8px; }
.step-strip { display: flex; align-items: center; gap: 14px; font-size: 12px; color: var(--muted); padding-bottom: 5px; }
.step { display: flex; align-items: center; gap: 7px; white-space: nowrap; }
.step span { border: 1px solid #c7d0c7; border-radius: 50%; width: 23px; height: 23px; display: grid; place-items: center; }
.step.current { color: var(--green); }
.step.current span { background: var(--green); color: white; border-color: var(--green); }
.workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 306px;
  gap: 16px;
  padding: 0 24px 16px;
}
.stage {
  background: #e9ece5;
  border-radius: 18px;
  position: relative;
  min-width: 0;
  overflow: hidden;
  height: 620px;
  border: 1px solid #dce1d8;
}
.stage-top {
  position: absolute;
  left: 18px;
  right: 18px;
  top: 16px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  z-index: 3;
  pointer-events: none;
}
.stage-top > * { pointer-events: auto; }
.segments {
  display: inline-flex;
  padding: 4px;
  background: #ffffffed;
  border: 1px solid #d8dfd4;
  border-radius: 999px;
  gap: 3px;
}
.segments button { border: 0; min-height: 38px; padding: 8px 15px; border-radius: 999px; background: none; font-size: 13px; color: var(--muted); }
.segments button.active { background: var(--green); color: white; }
.room-info { background: #fffffff0; border-radius: 12px; padding: 12px 15px; min-width: 120px; }
.room-info strong { font-size: 23px; font-weight: 400; letter-spacing: -.8px; }
.room-info span { font-size: 11px; color: var(--muted); display: block; margin-top: 2px; }
#scene { position: absolute; inset: 0; }
#scene canvas { display: block; width: 100%; height: 100%; outline-offset: -4px; }
#plan { position: absolute; inset: 0; touch-action: none; }
.stage-tools {
  position: absolute;
  top: 84px;
  left: 18px;
  display: grid;
  gap: 4px;
  background: #fffffff0;
  border: 1px solid #d8dfd4;
  padding: 5px;
  border-radius: 12px;
  z-index: 3;
}
.stage-bottom {
  position: absolute;
  bottom: 18px;
  left: 18px;
  right: 18px;
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 10px;
  pointer-events: none;
  z-index: 3;
}
.stage-bottom > * { pointer-events: auto; }
.stage-label { background: #ffffffe8; border: 1px solid #d8dfd4; border-radius: 999px; padding: 8px 12px; font-size: 11px; color: #485747; }
.zoom-tools { display: flex; align-items: center; background: #fffffff0; border-radius: 999px; padding: 3px; border: 1px solid #d8dfd4; }
.loading {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  text-align: center;
  gap: 16px;
  z-index: 2;
  background: #e9ece5;
  padding: 30px;
}
.spinner { width: 28px; height: 28px; border: 2px solid #b5c2b2; border-top-color: var(--green); border-radius: 50%; margin: auto; animation: spin 900ms linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.sidebar { border-radius: 18px; background: white; border: 1px solid var(--line); overflow: hidden; height: 620px; display: flex; flex-direction: column; }
.side-tabs { display: flex; padding: 8px; gap: 4px; border-bottom: 1px solid var(--line); }
.side-tabs button { flex: 1; border: 0; border-radius: 8px; background: transparent; min-height: 42px; font-size: 13px; color: var(--muted); }
.side-tabs button.active { background: var(--light); color: var(--green); }
.side-content { overflow: auto; padding: 19px; flex: 1; }
.section-title { font-size: 18px; letter-spacing: -.5px; font-weight: 500; margin-bottom: 7px; }
.section-caption { color: var(--muted); font-size: 12px; line-height: 1.65; margin-bottom: 17px; }
.preset-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.preset { padding: 8px 3px; min-height: 70px; border: 1px solid var(--line); border-radius: 10px; background: #fafbf8; font-size: 11px; color: var(--muted); }
.preset.active { border-color: var(--green); background: var(--light); color: var(--green); }
.preset svg { display: block; margin: 0 auto 7px; }
.swatches { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
.swatch { width: 32px; height: 32px; min-width: 32px; border-radius: 50%; border: 3px solid white; outline: 1px solid #c7cfc4; }
.swatch[aria-pressed=true] { outline: 2px solid var(--green); }
.check-label { font-size: 13px; display: flex; align-items: center; gap: 9px; line-height: 1.5; }
.cozy-box { background: #eff4ed; border-radius: 12px; padding: 15px; margin-top: 20px; }
.cozy-box h3 { font-size: 15px; margin-bottom: 7px; font-weight: 500; }
.cozy-box p { color: #546553; font-size: 12px; line-height: 1.65; margin-bottom: 13px; }
.catalog { display: grid; grid-template-columns: 1fr 1fr; gap: 9px; margin-top: 14px; }
.catalog-item { border: 1px solid var(--line); border-radius: 11px; background: #f9faf7; padding: 13px 8px 10px; min-height: 99px; text-align: left; color: var(--ink); }
.catalog-item:hover { background: #eaf0e6; border-color: #a4b8a1; }
.catalog-item svg { display: block; width: 29px; height: 29px; margin: 0 0 8px 3px; color: #6f8069; }
.catalog-name { font-size: 12px; display: block; }
.catalog-size { font-size: 10px; color: var(--muted); display: block; margin-top: 3px; }
.object-list { list-style: none; padding: 0; margin: 0; display: grid; gap: 6px; }
.object-row { display: flex; align-items: center; gap: 3px; padding: 4px; border-radius: 8px; border: 1px solid var(--line); }
.object-row.selected { background: var(--light); border-color: #92ad92; }
.object-select { border: 0; background: none; text-align: left; flex: 1; min-width: 0; padding: 8px; font-size: 12px; overflow-wrap: anywhere; }
.object-row .icon-btn { min-width: 33px; min-height: 38px; }
.notice { background: #faf2e4; color: #785922; border-radius: 8px; padding: 11px 13px; font-size: 12px; line-height: 1.65; }
.footnote { padding: 0 32px 20px; display: flex; justify-content: space-between; gap: 18px; font-size: 11px; line-height: 1.6; color: var(--muted); }
.footnote button { border: 0; background: none; color: var(--green); text-decoration: underline; padding: 0; font-size: 11px; }
.photo-strip { margin-top: 18px; border-radius: 10px; overflow: hidden; background: #f1f2ec; }
.photo-strip img { width: 100%; height: 100px; object-fit: cover; display: block; }
.photo-strip .row { padding: 8px; }
.photo-strip span { font-size: 11px; }
#toast {
  position: fixed;
  bottom: 25px;
  left: 50%;
  transform: translateX(-50%);
  max-width: min(90vw, 560px);
  padding: 13px 21px;
  border-radius: 12px;
  background: #243f32;
  color: white;
  z-index: 30;
  font-size: 14px;
  box-shadow: 0 8px 25px #1e38202b;
}
dialog {
  position: fixed;
  top: 16px;
  bottom: auto;
  margin: 0 auto;
  border: 1px solid #d5ded1;
  border-radius: 20px;
  padding: 0;
  color: var(--ink);
  width: min(680px, calc(100vw - 28px));
  max-height: min(calc(100dvh - 32px), 700px);
  box-shadow: 0 25px 80px #13241a30;
}
dialog::backdrop { background: #1e342a7a; backdrop-filter: blur(4px); }
.dialog-head { position: sticky; top: 0; z-index: 5; background: white; padding: 20px 24px 16px; display: flex; align-items: center; justify-content: space-between; gap: 12px; border-bottom: 1px solid var(--line); }
.dialog-head h2 { font-size: 23px; letter-spacing: -.7px; font-weight: 400; }
.dialog-body { padding: 22px 24px 26px; overflow-wrap: anywhere; }
.dialog-body p { font-size: 14px; line-height: 1.7; margin-bottom: 12px; }
.dialog-body h3 { margin: 20px 0 10px; font-size: 17px; }
.upload-box { border: 1px dashed #90a68c; border-radius: 13px; padding: 24px; display: grid; gap: 13px; text-align: center; background: #f4f7f0; }
#photoCanvas { width: 100%; background: #e9ece5; display: block; border-radius: 11px; touch-action: none; margin-top: 16px; }
.photo-toolbar { margin: 12px 0; display: flex; gap: 8px; align-items: center; justify-content: space-between; }
.photo-error { color: var(--danger); font-size: 13px; min-height: 20px; margin-top: 10px; }
.recommendation { border-bottom: 1px solid var(--line); padding: 14px 0; }
.recommendation:first-child { padding-top: 0; }
.recommendation strong { display: block; font-size: 14px; margin-bottom: 4px; }
.recommendation p { margin: 0; font-size: 12px; color: var(--muted); }
.recommendation label { align-items: flex-start; }
.report { white-space: pre-wrap; font: 12px/1.6 ui-monospace, monospace; background: #eff2eb; border-radius: 9px; padding: 14px; overflow-wrap: anywhere; }
.mobile-panel-toggle { display: none; }
@media (min-width: 1600px) {
  .workspace { grid-template-columns: minmax(0, 1fr) 340px; }
  .stage, .sidebar { height: 700px; }
}
@media (max-width: 1100px) {
  .step-strip { display: none; }
  .app-header { padding: 12px 20px; }
  .header-divider { display: none; }
  .project-title { width: 155px; }
  .header-actions .btn { padding: 9px 13px; }
  .workspace { padding: 0 16px 16px; grid-template-columns: minmax(0, 1fr) 286px; gap: 12px; }
  .intro { padding: 24px 22px; }
}
@media (max-width: 760px) {
  .app-header { flex-wrap: wrap; padding: 12px 16px; gap: 10px; }
  .brand-name { font-size: 20px; }
  .brand-sub { font-size: 9px; }
  .brand-mark { width: 34px; height: 34px; }
  .project-title { width: 140px; font-size: 12px; }
  .save-state { font-size: 10px; }
  .header-actions { width: 100%; justify-content: space-between; }
  .header-actions .btn { flex: 1; font-size: 12px; }
  .header-actions .btn svg { width: 17px; }
  .header-actions .icon-btn { min-width: 44px; }
  .intro { padding: 19px 17px 17px; }
  .intro h1 { font-size: 28px; letter-spacing: -1px; }
  .intro p { font-size: 12px; max-width: 44ch; }
  .eyebrow { font-size: 10px; }
  .workspace { display: flex; flex-direction: column; padding: 0 10px 12px; gap: 12px; }
  .stage { height: clamp(360px, 56dvh, 560px); border-radius: 13px; }
  .sidebar { height: auto; max-height: none; border-radius: 13px; overflow: visible; }
  .side-content { overflow: visible; padding: 18px; }
  .side-tabs { position: sticky; top: 0; background: white; z-index: 4; }
  .stage-top { left: 11px; right: 11px; top: 12px; }
  .stage-tools { left: 11px; top: 75px; }
  .stage-bottom { left: 11px; right: 11px; bottom: 12px; }
  .stage-label { max-width: 190px; font-size: 10px; line-height: 1.4; }
  .room-info { padding: 9px 12px; min-width: 90px; }
  .room-info strong { font-size: 20px; }
  .room-info span { font-size: 10px; }
  .footnote { padding: 0 18px 22px; font-size: 10px; flex-direction: column; gap: 7px; }
  .catalog { grid-template-columns: repeat(3, 1fr); }
  .mobile-panel-toggle { display: inline-flex; }
  dialog { max-height: min(calc(100dvh - 16px), 600px); }
  .dialog-head { position: sticky; top: 0; z-index: 5; background: white; padding: 15px 18px; }
  .dialog-body { padding: 18px; }
  .dialog-head h2 { font-size: 21px; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
}
</style>
<script type="importmap">
{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/"}}
</script>
</head>
<body>
<header class="app-header">
  <div class="row">
    <div class="brand">
      <div class="brand-mark" data-icon="room"></div>
      <div><div class="brand-name">roomcraft</div><div class="brand-sub muted">пространство для тебя</div></div>
    </div>
    <div class="header-divider"></div>
    <div>
      <input class="project-title" id="projectName" aria-label="Название проекта" maxlength="80" value="Моя уютная комната">
      <div class="row"><span class="status-dot"></span><span id="saveState" class="save-state" role="status">Демо / изменения не сохранены</span></div>
    </div>
  </div>
  <nav class="row header-actions" aria-label="Проект">
    <button class="icon-btn" id="undoBtn" title="Отменить" aria-label="Отменить" disabled data-icon="undo"></button>
    <button class="icon-btn" id="redoBtn" title="Повторить" aria-label="Повторить" disabled data-icon="redo"></button>
    <button class="btn" id="photoBtn"><span data-icon="camera"></span>Фото комнаты</button>
    <button class="btn primary" id="exportBtn"><span data-icon="download"></span>Сохранить проект</button>
  </nav>
</header>
<section class="intro">
  <div>
    <div class="eyebrow">ТВОЯ ЛИЧНАЯ ИНТЕРЬЕРНАЯ СТУДИЯ</div>
    <h1>Здесь начинается уют.</h1>
    <p id="introCaption">Исследуй демо или добавь фото своей комнаты. Уточни размеры, расставь мебель и найди своё настроение.</p>
  </div>
  <div class="step-strip" aria-label="Этапы работы">
    <div class="step"><span>1</span>Фото</div>
    <span>/</span><div class="step"><span>2</span>Размеры</div>
    <span>/</span><div class="step current"><span>3</span>Твоё пространство</div>
  </div>
</section>
<main class="workspace" id="main">
  <section class="stage" id="stage" aria-label="Предпросмотр комнаты">
    <div id="scene"></div>
    <canvas id="plan" hidden aria-label="План комнаты. Выбирай предметы касанием или через список." tabindex="0"></canvas>
    <div class="loading" id="loading"><div class="spinner"></div><p>Открываем твоё пространство…</p><p class="small muted">Загружается 3D-библиотека. Фото никуда не отправляется.</p></div>
    <div class="stage-top">
      <div class="segments" aria-label="Вид комнаты">
        <button id="view3d" class="active" aria-pressed="true">3D-комната</button>
        <button id="viewPlan" aria-pressed="false">План</button>
      </div>
      <div class="room-info"><strong id="area">20,2 м²</strong><span id="dimensionSummary">4,8 × 4,2 м</span></div>
    </div>
    <div class="stage-tools" aria-label="Инструменты сцены">
      <button class="icon-btn active" id="selectTool" title="Выделение" aria-label="Режим выделения" data-icon="cursor"></button>
      <button class="icon-btn" id="moveTool" title="Перемещение" aria-label="Перемещение предмета" data-icon="move"></button>
      <button class="icon-btn" id="rotateTool" title="Поворот" aria-label="Поворот предмета" data-icon="rotate"></button>
      <button class="icon-btn" id="gridBtn" title="Сетка" aria-label="Переключить сетку" aria-pressed="false" data-icon="grid"></button>
      <button class="icon-btn" id="homeView" title="Вписать комнату" aria-label="Вписать комнату в кадр" data-icon="frame"></button>
    </div>
    <div class="stage-bottom">
      <span class="stage-label" id="sceneLabel">Демо / приблизительная реконструкция</span>
      <div class="zoom-tools">
        <button class="icon-btn" id="zoomOut" aria-label="Отдалить" data-icon="minus"></button>
        <button class="icon-btn" id="zoomIn" aria-label="Приблизить" data-icon="plus"></button>
      </div>
    </div>
  </section>
  <aside class="sidebar" aria-label="Параметры комнаты">
    <nav class="side-tabs" aria-label="Разделы редактора">
      <button data-tab="room" class="active" aria-pressed="true">Комната</button>
      <button data-tab="catalog" aria-pressed="false">Предметы</button>
      <button data-tab="objects" aria-pressed="false">В сцене</button>
    </nav>
    <div class="side-content">
      <div id="tab-room" class="stack">
        <div>
          <h2 class="section-title">Твоё пространство</h2>
          <p class="section-caption">Размеры задаёшь ты. Фото служит ориентиром, а не точным 3D-сканированием.</p>
          <div class="fields three">
            <label class="field">Ширина, м<input id="roomW" inputmode="decimal" value="4.8" aria-label="Ширина комнаты в метрах"></label>
            <label class="field">Глубина, м<input id="roomD" inputmode="decimal" value="4.2" aria-label="Глубина комнаты в метрах"></label>
            <label class="field">Высота, м<input id="roomH" inputmode="decimal" value="2.8" aria-label="Высота комнаты в метрах"></label>
          </div>
          <button class="btn full" id="applyRoom" style="margin-top:12px">Применить размеры</button>
          <p class="small" id="roomError" role="alert" style="color:var(--danger)"></p>
        </div>
        <div>
          <h3 class="section-title" style="font-size:15px">Настроение света</h3>
          <div class="preset-grid">
            <button class="preset active" data-light="day"><span data-icon="sun"></span>День</button>
            <button class="preset" data-light="evening"><span data-icon="moon"></span>Вечер</button>
            <button class="preset" data-light="neutral"><span data-icon="lamp"></span>Нейтральный</button>
          </div>
        </div>
        <div>
          <div class="row between"><h3 class="section-title" style="font-size:15px;margin:0">Цвет стен</h3><input type="color" id="wallColor" value="#e2e0d2" aria-label="Цвет стен" style="width:44px"></div>
          <div class="swatches" id="wallSwatches"></div>
        </div>
        <div class="fields">
          <label class="field">Пол<select id="floorType"><option value="wood">Дерево</option><option value="tile">Плитка</option><option value="plain">Однотонный</option></select></label>
          <label class="field">Качество<select id="quality"><option value="auto">Авто</option><option value="low">Лёгкое</option><option value="high">Высокое</option></select></label>
        </div>
        <label class="check-label"><input type="checkbox" id="snap" checked>Привязка к сетке 10 см</label>
        <label class="check-label"><input type="checkbox" id="shadows" checked>Мягкие тени</label>
        <details><summary class="small" style="cursor:pointer;min-height:32px">Дверь и окно</summary>
          <div class="stack" style="margin-top:12px">
            <label class="check-label"><input type="checkbox" id="showDoor" checked>Дверь на передней стене</label>
            <label class="check-label"><input type="checkbox" id="showWindow" checked>Окно на дальней стене</label>
            <p class="small muted">В этой версии проёмы фиксированных размеров. Передняя стена скрыта для обзора.</p>
          </div>
        </details>
        <div id="reference" class="photo-strip" hidden><img id="referenceImg" alt="Исходное фото комнаты"><div class="row between"><span>Фото-ориентир / только на устройстве</span><button class="icon-btn" id="deletePhoto" aria-label="Удалить фотографию" data-icon="trash"></button></div></div>
        <div class="cozy-box">
          <h3 class="row"><span data-icon="spark"></span>Добавим немного уюта?</h3>
          <p>Подберём декор по простым правилам. Сначала покажем предложения — ничего не изменится без тебя.</p>
          <button class="btn primary full" id="cozyBtn">Подобрать уютный вариант</button>
        </div>
      </div>
      <div id="tab-catalog" hidden>
        <h2 class="section-title">Новые детали</h2>
        <p class="section-caption">Условные процедурные модели. Не товары реального магазина.</p>
        <label class="field">Найти предмет<input id="catalogSearch" type="search" placeholder="Например, кресло" maxlength="80"></label>
        <label class="field" style="margin-top:12px">Категория<select id="catalogCategory"><option value="all">Все предметы</option><option value="furniture">Мебель</option><option value="decor">Декор и текстиль</option><option value="light">Освещение</option></select></label>
        <div class="catalog" id="catalog"></div>
      </div>
      <div id="tab-objects" hidden>
        <h2 class="section-title">В твоей комнате</h2>
        <p class="section-caption" id="objectCount"></p>
        <label class="field">Поиск в сцене<input id="objectSearch" type="search" placeholder="Название предмета" maxlength="80"></label>
        <ul class="object-list" id="objectList" style="margin-top:12px"></ul>
      </div>
      <div id="selectionPanel" hidden>
        <div class="divider"></div>
        <h2 class="section-title">Выбранный предмет</h2>
        <div class="stack">
          <label class="field">Название<input id="objectName" maxlength="80"></label>
          <div class="fields"><label class="field">X, м<input id="objX" inputmode="decimal"></label><label class="field">Z, м<input id="objZ" inputmode="decimal"></label></div>
          <div class="fields"><label class="field">Высота над полом, м<input id="objY" inputmode="decimal"></label><label class="field">Поворот, °<input id="objR" inputmode="decimal"></label></div>
          <div class="fields three"><label class="field">Ширина, м<input id="objW" inputmode="decimal"></label><label class="field">Глубина, м<input id="objD" inputmode="decimal"></label><label class="field">Высота, м<input id="objH" inputmode="decimal"></label></div>
          <label class="field">Цвет<input id="objColor" type="color"></label>
          <label class="check-label"><input type="checkbox" id="objLocked">Закрепить на месте</label>
          <button class="btn primary full" id="applyObject">Применить свойства</button>
          <div class="row"><button class="btn" id="turnLeft" aria-label="Повернуть влево на 15 градусов">−15°</button><button class="btn" id="turnRight" aria-label="Повернуть вправо на 15 градусов">+15°</button><button class="btn" id="focusObject">В кадр</button></div>
          <div class="row"><button class="btn" id="duplicateObject">Копия</button><button class="btn danger" id="removeObject">Удалить</button></div>
          <p id="objectError" class="small" role="alert" style="color:var(--danger)"></p>
        </div>
      </div>
    </div>
  </aside>
</main>
<footer class="footnote"><span>Фото остаётся в браузере. Комната задаётся вручную; отдельно доступно экспериментальное нейро-объёмное фото.</span><span><button id="helpBtn">Как это работает</button> / RoomCraft 0.1</span></footer>
<div id="toast" role="status" hidden></div>
<dialog id="photoDialog" aria-labelledby="photoTitle">
  <div class="dialog-head"><h2 id="photoTitle">Начнём с твоей комнаты</h2><button class="icon-btn" data-close="photoDialog" aria-label="Закрыть" data-icon="close"></button></div>
  <div class="dialog-body">
    <p class="muted">Добавь фото, отметь четыре угла видимой области пола и введи размеры. Это ручная настройка комнаты. Отдельно можно построить нейросетевое объёмное фото — рельеф видимой части, не полный скан.</p>
    <div class="upload-box" id="dropZone">
      <span data-icon="camera"></span><strong>Твоё фото — только у тебя</strong>
      <span class="small muted">JPEG, PNG или WebP / до 15 МБ и 40 мегапикселей</span>
      <label class="field">Выбери изображение<input type="file" id="photoInput" accept="image/jpeg,image/png,image/webp"></label>
      <label class="field">Или сделай снимок<input type="file" id="cameraInput" accept="image/*" capture="environment"></label>
    </div>
    <p class="photo-error" id="photoError" role="alert"></p>
    <div id="photoEditor" hidden>
      <canvas id="photoCanvas" width="800" height="500" tabindex="0" aria-label="Разметка фото: нажми четыре угла пола по порядку"></canvas>
      <div class="photo-toolbar"><span id="pointStatus" class="small muted">Отметь 4 угла пола по кругу</span><button class="btn" id="undoPoint">Убрать точку</button></div>
      <p class="small muted">Метки сохраняются как ориентир. По ним не вычисляется точная перспектива; ширина и глубина ниже определяют прямоугольную 3D-комнату.</p>
      <div class="fields three" style="margin-top:16px">
        <label class="field">Ширина, м<input id="photoW" value="4.8" inputmode="decimal"></label>
        <label class="field">Глубина, м<input id="photoD" value="4.2" inputmode="decimal"></label>
        <label class="field">Высота, м<input id="photoH" value="2.8" inputmode="decimal"></label>
      </div>
      <label class="check-label" style="margin:16px 0"><input type="checkbox" id="keepFurniture">Оставить текущую мебель, если она помещается</label>
      <button class="btn full" id="openDepth" style="margin:14px 0">Построить объёмное фото / локальная нейросеть</button>
      <button class="btn primary full" id="createFromPhoto">Создать приблизительную комнату</button>
    </div>
  </div>
</dialog>
<dialog id="exportDialog" aria-labelledby="exportTitle">
  <div class="dialog-head"><h2 id="exportTitle">Сохрани своё пространство</h2><button class="icon-btn" data-close="exportDialog" aria-label="Закрыть" data-icon="close"></button></div>
  <div class="dialog-body stack">
    <p class="muted">JSON можно снова открыть в RoomCraft. Локальное сохранение не переносится на другой телефон автоматически.</p>
    <label class="check-label"><input type="checkbox" id="includePhoto">Включить личное фото в JSON-файл</label>
    <button class="btn primary full" id="saveJSON"><span data-icon="download"></span>Скачать проект JSON</button>
    <div class="fields"><button class="btn" id="savePNG">Снимок PNG</button><button class="btn" id="savePlan">План PNG</button><button class="btn" id="saveGLB">Модель GLB</button><button class="btn" id="saveCSV">Мебель CSV</button></div>
    <label class="field">Открыть проект JSON<input id="importInput" type="file" accept=".json,application/json"></label>
    <button class="btn full" id="localSave">Сохранить локально в браузере</button>
    <button class="btn" id="restoreLocal">Открыть локальную копию</button>
    <button class="btn danger" id="clearLocal">Удалить локальную копию</button>
    <p class="notice">Базовый проект сохраняется без фотографии. Файл GLB не сохраняет все параметры редактора; для продолжения работы используй JSON.</p>
  </div>
</dialog>
<dialog id="cozyDialog" aria-labelledby="cozyTitle">
  <div class="dialog-head"><h2 id="cozyTitle">Маленькие изменения, новый уют</h2><button class="icon-btn" data-close="cozyDialog" aria-label="Закрыть" data-icon="close"></button></div>
  <div class="dialog-body">
    <label class="field">Настроение<select id="cozyStyle"><option value="warm">Тёплый минимализм</option><option value="scandi">Светлый скандинавский</option><option value="night">Уютный вечер</option><option value="study">Для учёбы</option></select></label>
    <div class="row wrap" style="margin:14px 0"><label class="check-label"><input type="checkbox" id="allowPlants" checked>Растения</label><label class="check-label"><input type="checkbox" id="allowTextile" checked>Текстиль</label><button class="btn" id="recalculateCozy">Пересчитать</button></div>
    <div id="recommendations"></div>
    <p class="small muted" style="margin-top:15px">Рекомендации рассчитаны локально по правилам и свободному месту. Это не нейросеть и не оценка безопасности интерьера.</p>
    <button class="btn primary full" id="applyCozy" style="margin-top:14px">Применить выбранное</button>
  </div>
</dialog>
<dialog id="helpDialog" aria-labelledby="helpTitle">
  <div class="dialog-head"><h2 id="helpTitle">Пространство без магических обещаний</h2><button class="icon-btn" data-close="helpDialog" aria-label="Закрыть" data-icon="close"></button></div>
  <div class="dialog-body">
    <h3>1. Фото как ориентир</h3><p>Фото декодируется в браузере. Отметки углов помогают запомнить границы, но не вычисляют форму помещения. Версия 0.1 строит прямоугольную комнату по введённым размерам. Отдельная экспериментальная нейросеть оценивает относительную глубину и создаёт 2.5D-рельеф фотографии. Распознавания мебели и точной фотограмметрии нет.</p>
    <h3>2. Твоя расстановка</h3><p>Добавляй предметы из каталога, выбирай их в сцене или списке. Меняй координаты и размеры численно. Для 3D-перетаскивания выбери предмет и инструмент перемещения. Ctrl/Cmd+Z отменяет последнее изменение.</p>
    <h3>3. Уют по правилам</h3><p>Сервис ищет место для декора и предлагает сочетание цветов. Принимаешь изменения только ты. Закреплённые предметы не передвигаются.</p>
    <h3>4. Фото и сохранение</h3><p>Автосохранение в этом выпуске выключено. Сохраняй JSON или локальную копию вручную. Фото не входит в локальную копию; включить его в скачиваемый JSON можно отдельно. Внешний CDN получает обычный запрос библиотеки и сетевые сведения, но не твоё фото.</p>
    <h3>Что пока не реализовано</h3><p>Автоматическая замкнутая модель комнаты по фото, многоугольные комнаты, свободное редактирование проёмов, группы, мультивыделение, AR и офлайн-PWA. Это частичная реализация большого технического задания, не выполнение всех 700 требований.</p>
    <h3>Проверки математики редактора</h3><button class="btn" id="runTests">Запустить встроенные проверки</button><pre id="testResults" class="report" hidden></pre>
    <h3>Диагностика</h3><pre id="diagnostics" class="report"></pre>
  </div>
</dialog>
<dialog id="depthDialog" aria-labelledby="depthTitle" style="width:min(900px,calc(100vw - 24px))">
  <div class="dialog-head"><h2 id="depthTitle">Твоё фото становится объёмным</h2><button class="icon-btn" data-close="depthDialog" aria-label="Закрыть" data-icon="close"></button></div>
  <div class="dialog-body stack">
    <p class="notice">Эксперимент: локальная оценка относительной глубины создаёт 2.5D-рельеф видимого кадра. Это не замкнутая 3D-комната, не точные расстояния и не распознавание мебели. Скрытые поверхности неизвестны.</p>
    <p class="small muted">Модель: Depth Anything V2 Small / ONNX, Apache-2.0. Скачается около 27 МБ весов плюс библиотека и WASM. На телефоне может быть медленно и расходовать память. Фото не отправляется на Hugging Face: загружаются только файлы модели. Нужен интернет и поддержка WebAssembly.</p>
    <div class="row wrap"><button class="btn primary" id="runDepth">Скачать модель и оценить глубину</button><button class="btn" id="cancelDepth" disabled>Игнорировать результат</button></div>
    <p id="depthStatus" class="small muted" role="status">Запуск только по твоему нажатию.</p>
    <div id="depthViewport" style="position:relative;width:100%;height:340px;border-radius:12px;background:#e9ece5;overflow:hidden" aria-label="Объёмное фото, вращение мышью или касанием"></div>
    <div class="fields"><label class="field">Выраженность рельефа<input id="depthStrength" type="range" min="0" max="2" step=".05" value=".9"></label><label class="field">Карта глубины<canvas id="depthMap" width="256" height="180" style="width:100%;max-height:130px;object-fit:contain;background:#eaede5;border-radius:8px"></canvas></label></div>
    <div class="row wrap"><button class="btn" id="exportDepthPNG" disabled>Карта глубины PNG</button><button class="btn" id="exportDepthGLB" disabled>Рельеф GLB</button><button class="btn" id="releaseDepth">Освободить модель</button></div>
    <p class="small muted">Рельеф не подменяет комнату в редакторе. <a href="https://huggingface.co/onnx-community/depth-anything-v2-small" target="_blank" rel="noopener noreferrer">Карточка и лицензия модели</a>.</p>
  </div>
</dialog>
<script type="module">
'use strict';
const $ = id => document.getElementById(id);
const VERSION = 1;
const MAX_OBJECTS = 180;
const MAX_FILE = 15 * 1024 * 1024;
const ICONS = {
  room: '<path d="m3 8 9-5 9 5v10l-9 4-9-4V8Z"/><path d="m3 8 9 5 9-5M12 13v9M7 10V6m10 4V6"/>',
  camera: '<path d="M4 7h4l2-3h4l2 3h4v13H4Z"/><circle cx="12" cy="13" r="4"/>',
  download: '<path d="M12 3v12m-4-4 4 4 4-4M4 16v5h16v-5"/>',
  undo: '<path d="m8 5-5 5 5 5M3 10h11a6 6 0 0 1 0 12"/>',
  redo: '<path d="m16 5 5 5-5 5m5-5H10a6 6 0 0 0 0 12"/>',
  cursor: '<path d="m5 3 14 11-7 1-3 7L5 3Z"/>',
  move: '<path d="M12 3v18M3 12h18m-12-6 3-3 3 3m-6 12 3 3 3-3M6 9l-3 3 3 3m12-6 3 3-3 3"/>',
  rotate: '<path d="M20 8a8 8 0 1 0 0 8M20 3v5h-5"/>',
  grid: '<rect x="3" y="3" width="18" height="18" rx="1"/><path d="M9 3v18m6-18v18M3 9h18M3 15h18"/>',
  frame: '<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  minus: '<path d="M5 12h14"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
  moon: '<path d="M20 15A9 9 0 0 1 9 4a9 9 0 1 0 11 11Z"/>',
  lamp: '<path d="m8 3-3 10h14L16 3H8Zm4 10v8m-5 0h10"/>',
  spark: '<path d="m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3 3-7ZM20 2v4m-2-2h4"/>',
  trash: '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
  close: '<path d="m6 6 12 12M18 6 6 18"/>',
  sofa: '<path d="M5 12V6h14v6M3 11v8h18v-8h-4v5H7v-5H3Zm2 8v3m14-3v3"/>',
  chair: '<path d="M7 3h10v9H7ZM5 12h14v5H5Zm2 5v5m10-5v5"/>',
  bed: '<path d="M3 20V8h18v12M3 16h18M5 8V4h14v4M6 11h5m2 0h5"/>',
  table: '<path d="M3 7h18v4H3Zm3 4v10m12-10v10"/>',
  cabinet: '<rect x="5" y="3" width="14" height="18" rx="1"/><path d="M12 3v18M9 11v3m6-3v3"/>',
  rug: '<path d="M4 4h16v16H4Zm3 3h10v10H7ZM1 5h3m-3 5h3m-3 5h3m16-10h3m-3 5h3m-3 5h3"/>',
  plant: '<path d="m7 15 1 7h8l1-7H7Zm5 0V8m0 3C4 12 3 5 3 5s8-1 9 6Zm0-2c8 0 9-7 9-7s-8 0-9 7Z"/>',
  art: '<rect x="3" y="3" width="18" height="18" rx="1"/><path d="m5 17 5-6 4 4 3-3 4 5"/><circle cx="16" cy="8" r="2"/>',
  eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
  lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V6a4 4 0 0 1 8 0v4"/>',
};
function icon(name) {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ICONS.room}</svg>`;
}
function hydrateIcons(root = document) {
  root.querySelectorAll('[data-icon]').forEach(el => el.innerHTML = icon(el.dataset.icon));
}
hydrateIcons();
const CATALOG = {
  sofa: {name:'Диван',w:2.25,d:.92,h:.82,c:'#b9c0a1',cat:'furniture',icon:'sofa'},
  armchair: {name:'Кресло',w:.85,d:.85,h:.86,c:'#c5aa83',cat:'furniture',icon:'chair'},
  bed: {name:'Кровать',w:1.6,d:2.05,h:.7,c:'#d4c6ac',cat:'furniture',icon:'bed'},
  desk: {name:'Рабочий стол',w:1.3,d:.65,h:.75,c:'#b9996c',cat:'furniture',icon:'table'},
  table: {name:'Обеденный стол',w:1.4,d:.8,h:.75,c:'#bca27c',cat:'furniture',icon:'table'},
  chair: {name:'Стул',w:.48,d:.5,h:.85,c:'#aa9570',cat:'furniture',icon:'chair'},
  coffee: {name:'Журнальный стол',w:1.1,d:.62,h:.38,c:'#c6a478',cat:'furniture',icon:'table'},
  cabinet: {name:'Комод',w:1.2,d:.42,h:.8,c:'#b99e77',cat:'furniture',icon:'cabinet'},
  wardrobe: {name:'Шкаф',w:1.4,d:.6,h:2.1,c:'#d6cfba',cat:'furniture',icon:'cabinet'},
  shelf: {name:'Стеллаж',w:.9,d:.3,h:1.7,c:'#b6a07a',cat:'furniture',icon:'cabinet'},
  nightstand: {name:'Тумба',w:.48,d:.42,h:.5,c:'#c3ad87',cat:'furniture',icon:'cabinet'},
  bench: {name:'Банкетка',w:1.1,d:.42,h:.45,c:'#afa080',cat:'furniture',icon:'sofa'},
  rug: {name:'Ковёр',w:2.3,d:1.65,h:.016,c:'#d9c6a4',cat:'decor',icon:'rug',flat:true},
  cushion: {name:'Подушка',w:.42,d:.42,h:.17,c:'#64745c',cat:'decor',icon:'sofa',flat:true},
  plant: {name:'Растение',w:.55,d:.55,h:1.15,c:'#63804d',cat:'decor',icon:'plant',round:true},
  smallplant: {name:'Небольшое растение',w:.3,d:.3,h:.4,c:'#6d8857',cat:'decor',icon:'plant',round:true},
  art: {name:'Постер',w:.55,d:.045,h:.75,c:'#a2ab83',cat:'decor',icon:'art',wall:true},
  wallshelf: {name:'Настенная полка',w:.9,d:.22,h:.05,c:'#bfa177',cat:'decor',icon:'table',wall:true},
  floorlamp: {name:'Торшер',w:.4,d:.4,h:1.55,c:'#e3d4b4',cat:'light',icon:'lamp',round:true},
  desklamp: {name:'Настольная лампа',w:.25,d:.25,h:.45,c:'#b9c1a5',cat:'light',icon:'lamp',round:true},
};
let project;
let selectedId = null;
let currentTab = 'room';
let mode = '3d';
let tool = 'select';
let dirty = false;
let photoData = null;
let pendingPhoto = null;
let photoImage = null;
let photoPoints = [];
let recommendations = [];
let toastTimer;
let undoStack = [];
let redoStack = [];
let THREE, OrbitControls, TransformControls;
let renderer, scene, camera, controls, transform;
let worldGroup, roomGroup, objectGroup, grid, highlight;
let ambient, sunLight;
let meshes = new Map();
let resizeObserver;
let pointerStart = null;
let dragging = false;
let dragSnapshot = null;
let renderRequested = false;
let database = null;
let storageAvailable = false;
let lastFocus = null;
let planScale = 1;
const numeric = (x, min, max) => {
  if (typeof x === 'boolean' || x === null || x === '') throw new Error('Нужно число');
  const value = Number(String(x).replace(',', '.'));
  if (!Number.isFinite(value) || value < min || value > max) throw new Error(`Значение должно быть от ${min} до ${max}`);
  return value;
};
const clone = value => JSON.parse(JSON.stringify(value));
const id = () => crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
const round = (n, d = 3) => Number(n.toFixed(d));
const format = n => new Intl.NumberFormat('ru-RU', {maximumFractionDigits:2}).format(n);
const colorOK = c => typeof c === 'string' && /^#[0-9a-f]{6}$/i.test(c);
function toast(text) {
  clearTimeout(toastTimer);
  $('toast').textContent = text;
  $('toast').hidden = false;
  toastTimer = setTimeout(() => $('toast').hidden = true, 5000);
}
function openDialog(name) {
  lastFocus = document.activeElement;
  const el = $(name);
  if (!el.open) el.showModal();
}
function closeDialog(name) {
  $(name).close();
  if (lastFocus?.isConnected) lastFocus.focus();
}
document.querySelectorAll('[data-close]').forEach(b => b.addEventListener('click', () => closeDialog(b.dataset.close)));
document.querySelectorAll('dialog').forEach(d => {
  d.addEventListener('cancel', () => { if (lastFocus?.isConnected) setTimeout(() => lastFocus.focus(), 0); });
});
function makeItem(type, options = {}) {
  const def = CATALOG[type];
  if (!def) throw new Error('Неизвестный тип предмета');
  return {
    id: id(), type, name:def.name,
    x:0, y:0, z:0, rotation:0,
    w:def.w, d:def.d, h:def.h,
    color:def.c, locked:false, visible:true,
    ...options,
  };
}
function emptyProject() {
  return {
    version:VERSION, id:id(), name:'Моя уютная комната',
    room:{w:4.8,d:4.2,h:2.8,wall:'#e2e0d2',floor:'wood',light:'day',door:true,window:true},
    objects:[], points:[], source:'manual',
  };
}
function demoProject() {
  const p = emptyProject();
  p.source = 'demo';
  p.objects = [
    makeItem('rug',{x:-.15,z:.25,w:2.5,d:1.9,color:'#d3c09d'}),
    makeItem('sofa',{x:-.45,z:-1.46,color:'#aeb694'}),
    makeItem('coffee',{x:-.4,z:-.15,color:'#bf9b6b'}),
    makeItem('armchair',{x:1.35,z:.52,rotation:-.38,color:'#c3ab86'}),
    makeItem('floorlamp',{x:-1.95,z:-1.48}),
    makeItem('plant',{x:1.94,z:-1.58,h:1.42,w:.62,d:.62}),
    makeItem('cabinet',{x:1.99,z:-.35,rotation:-Math.PI/2,w:1.1}),
    makeItem('art',{x:-1.45,y:1.22,z:-2.06,w:.6,h:.88,color:'#a29c79'}),
    makeItem('art',{x:-.72,y:1.42,z:-2.06,w:.45,h:.62,color:'#c09f78'}),
    makeItem('cushion',{x:-1.1,y:.47,z:-1.45,rotation:.2,color:'#68775a'}),
    makeItem('cushion',{x:.25,y:.47,z:-1.48,rotation:-.15,color:'#d5bd8f'}),
    makeItem('smallplant',{x:2.01,y:.8,z:-.3,h:.33,w:.22,d:.22}),
  ];
  return p;
}
function validateProject(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw new Error('Некорректный проект');
  if (raw.version !== VERSION) throw new Error('Неподдерживаемая версия проекта. Исходный файл не изменён.');
  if (!raw.room || !Array.isArray(raw.objects)) throw new Error('Нет комнаты или списка предметов');
  if (raw.objects.length > MAX_OBJECTS) throw new Error(`Лимит: ${MAX_OBJECTS} предметов`);
  const room = raw.room;
  const out = emptyProject();
  out.name = String(raw.name || 'Моя комната').slice(0,80);
  out.id = typeof raw.id === 'string' ? raw.id.slice(0,100) : id();
  out.room = {
    w:numeric(room.w,1,20),d:numeric(room.d,1,20),h:numeric(room.h,1.8,6),
    wall:colorOK(room.wall) ? room.wall : '#e2e0d2',
    floor:['wood','tile','plain'].includes(room.floor) ? room.floor : 'wood',
    light:['day','evening','neutral'].includes(room.light) ? room.light : 'day',
    door:room.door !== false, window:room.window !== false,
  };
  const seen = new Set();
  out.objects = raw.objects.map(o => {
    if (!o || !Object.hasOwn(CATALOG,o.type)) throw new Error('Недопустимый тип предмета');
    const obj = makeItem(o.type,{
      id:String(o.id || id()).slice(0,100),name:String(o.name || CATALOG[o.type].name).slice(0,80),
      x:numeric(o.x,-30,30),y:numeric(o.y,0,6),z:numeric(o.z,-30,30),
      rotation:numeric(o.rotation,-100,100),
      w:numeric(o.w,.02,10),d:numeric(o.d,.01,10),h:numeric(o.h,.005,6),
      color:colorOK(o.color) ? o.color : CATALOG[o.type].c,
      visible:o.visible !== false,locked:o.locked === true,
    });
    if (seen.has(obj.id)) throw new Error('Повторяющийся ID предмета');
    seen.add(obj.id);
    return obj;
  });
  out.points = Array.isArray(raw.points) ? raw.points.slice(0,4).map(p => ({x:numeric(p.x,0,1),y:numeric(p.y,0,1)})) : [];
  out.source = ['demo','photo','manual'].includes(raw.source) ? raw.source : 'manual';
  return out;
}
function snapshot() { return JSON.stringify(project); }
function pushHistory(before) {
  if (before === snapshot()) return;
  undoStack.push(before);
  if (undoStack.length > 55) undoStack.shift();
  redoStack = [];
  markDirty();
  updateHistory();
}
function transact(action) {
  const before = snapshot();
  try {
    action();
    pushHistory(before);
    syncAll();
  } catch (e) {
    project = JSON.parse(before);
    syncAll();
    throw e;
  }
}
function markDirty() {
  dirty = true;
  $('saveState').textContent = 'Есть несохранённые изменения';
}
function updateHistory() {
  $('undoBtn').disabled = undoStack.length === 0;
  $('redoBtn').disabled = redoStack.length === 0;
}
function historyStep(direction) {
  const from = direction === 'undo' ? undoStack : redoStack;
  const to = direction === 'undo' ? redoStack : undoStack;
  if (!from.length) return;
  to.push(snapshot());
  project = JSON.parse(from.pop());
  selectedId = project.objects.some(o=>o.id===selectedId) ? selectedId : null;
  markDirty();
  syncAll();
  updateHistory();
}
function selection() { return project.objects.find(o=>o.id===selectedId); }
function setTab(tab) {
  currentTab = tab;
  document.querySelectorAll('[data-tab]').forEach(b=>{
    const active = b.dataset.tab === tab;
    b.classList.toggle('active',active);
    b.setAttribute('aria-pressed',String(active));
  });
  ['room','catalog','objects'].forEach(t => $(`tab-${t}`).hidden = t!==tab);
  if (tab === 'objects') renderObjectList();
}
function selectObject(objectId) {
  selectedId = objectId;
  syncSelection();
  renderObjectList();
  syncTransform();
  updateHighlight();
  requestRender();
  drawPlan();
}
function syncSelection() {
  const o = selection();
  $('selectionPanel').hidden = !o;
  $('objectError').textContent = '';
  if (!o) return;
  $('objectName').value = o.name;
  $('objX').value = round(o.x);
  $('objY').value = round(o.y);
  $('objZ').value = round(o.z);
  $('objR').value = round(o.rotation * 180 / Math.PI,1);
  $('objW').value = round(o.w);
  $('objD').value = round(o.d);
  $('objH').value = round(o.h);
  $('objColor').value = o.color;
  $('objLocked').checked = o.locked;
  ['objX','objY','objZ','objR','objW','objD','objH'].forEach(k => $(k).disabled = o.locked);
}
function syncRoomUI() {
  const r = project.room;
  $('projectName').value = project.name;
  $('roomW').value = r.w;
  $('roomD').value = r.d;
  $('roomH').value = r.h;
  $('wallColor').value = r.wall;
  $('floorType').value = r.floor;
  $('showDoor').checked = r.door;
  $('showWindow').checked = r.window;
  $('area').textContent = `${format(r.w*r.d)} м²`;
  $('dimensionSummary').textContent = `${format(r.w)} × ${format(r.d)} м`;
  $('sceneLabel').textContent = `${project.source === 'demo' ? 'Демо / ' : ''}Приблизительная реконструкция`;
  document.querySelectorAll('[data-light]').forEach(b=>b.classList.toggle('active',b.dataset.light===r.light));
  document.querySelectorAll('.swatch').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.color===r.wall)));
}
function syncAll() {
  syncRoomUI();
  renderObjectList();
  syncSelection();
  rebuildScene();
  drawPlan();
  updateHistory();
}
function bounds2D(o) {
  const c=Math.cos(o.rotation),s=Math.sin(o.rotation);
  return [[-1,-1],[1,-1],[1,1],[-1,1]].map(([a,b])=>({
    x:o.x + a*o.w/2*c + b*o.d/2*s,
    z:o.z - a*o.w/2*s + b*o.d/2*c,
  }));
}
function fitsRoom(o, room = project.room) {
  const margin = CATALOG[o.type].wall ? -.06 : .01;
  return bounds2D(o).every(p=>Math.abs(p.x)<=room.w/2-margin && Math.abs(p.z)<=room.d/2-margin);
}
function overlap(a,b, gap=.035) {
  const pa=bounds2D(a),pb=bounds2D(b);
  const angles=[a.rotation,b.rotation];
  for (const angle of angles) {
    for (const axis of [[Math.cos(angle),-Math.sin(angle)],[Math.sin(angle),Math.cos(angle)]]) {
      const va=pa.map(p=>p.x*axis[0]+p.z*axis[1]);
      const vb=pb.map(p=>p.x*axis[0]+p.z*axis[1]);
      if (Math.max(...va)+gap<=Math.min(...vb) || Math.max(...vb)+gap<=Math.min(...va)) return false;
    }
  }
  return true;
}
function doorConflict(o) {
  if (!project.room.door || CATALOG[o.type].wall || CATALOG[o.type].flat) return false;
  const zone={x:-project.room.w/2+.8,z:project.room.d/2-.5,w:1.15,d:1,rotation:0};
  return overlap(o,zone,0);
}
function collides(o, objects=project.objects) {
  if (CATALOG[o.type].flat || CATALOG[o.type].wall || o.y>.15) return false;
  if (doorConflict(o)) return true;
  return objects.some(b=>b.id!==o.id && b.visible && !CATALOG[b.type].flat && !CATALOG[b.type].wall && b.y<.15 && overlap(o,b));
}
function findPosition(type, objects=project.objects) {
  const def=CATALOG[type];
  const candidate=makeItem(type);
  if (def.wall) {
    candidate.z=-project.room.d/2+.04;
    candidate.y=type==='art' ? 1.15 : 1.4;
    return fitsRoom(candidate) ? candidate : null;
  }
  const positions=[];
  for(let z=-project.room.d/2+.2;z<project.room.d/2;z+=.24){
    for(let x=-project.room.w/2+.2;x<project.room.w/2;x+=.24){
      positions.push({x:round(x),z:round(z)});
    }
  }
  positions.sort((a,b)=>(a.x*a.x+a.z*a.z)-(b.x*b.x+b.z*b.z));
  for(const pos of positions){
    candidate.x=pos.x;
    candidate.z=pos.z;
    if(fitsRoom(candidate) && !collides(candidate,objects)) return candidate;
  }
  return null;
}
function addObject(type) {
  if(project.objects.length>=MAX_OBJECTS) return toast(`Лимит ${MAX_OBJECTS} предметов`);
  const o=findPosition(type);
  if(!o) return toast('Не найдено свободное место. Освободи пространство или уменьши другие предметы.');
  transact(()=>project.objects.push(o));
  selectObject(o.id);
  toast(`${o.name}: добавлен в комнату`);
}
function renderCatalog() {
  const query=$('catalogSearch').value.toLowerCase().trim();
  const category=$('catalogCategory').value;
  const root=$('catalog');
  root.replaceChildren();
  Object.entries(CATALOG).filter(([_,d])=>(category==='all'||d.cat===category)&&d.name.toLowerCase().includes(query)).forEach(([type,d])=>{
    const b=document.createElement('button');
    b.className='catalog-item';
    b.innerHTML=icon(d.icon);
    const n=document.createElement('span');
    n.className='catalog-name';
    n.textContent=d.name;
    const size=document.createElement('span');
    size.className='catalog-size';
    size.textContent=`${Math.round(d.w*100)} × ${Math.round(d.d*100)} см`;
    b.append(n,size);
    b.setAttribute('aria-label',`Добавить: ${d.name}`);
    b.addEventListener('click',()=>addObject(type));
    root.append(b);
  });
  if(!root.children.length){
    const p=document.createElement('p');
    p.className='small muted';
    p.textContent='Ничего не найдено. Попробуй другое название.';
    root.append(p);
  }
}
function renderObjectList() {
  $('objectCount').textContent=`${project.objects.length} предметов / выбери любой для изменения`;
  const root=$('objectList');
  const q=$('objectSearch').value.toLowerCase().trim();
  root.replaceChildren();
  project.objects.filter(o=>o.name.toLowerCase().includes(q)).forEach(o=>{
    const li=document.createElement('li');
    li.className=`object-row${o.id===selectedId?' selected':''}`;
    const b=document.createElement('button');
    b.className='object-select';
    b.textContent=`${o.locked?'[закреплён] ':''}${o.visible?'':'[скрыт] '}${o.name}`;
    b.addEventListener('click',()=>selectObject(o.id));
    const visibility=document.createElement('button');
    visibility.className='icon-btn';
    visibility.innerHTML=icon('eye');
    visibility.setAttribute('aria-label',`${o.visible?'Скрыть':'Показать'}: ${o.name}`);
    visibility.setAttribute('aria-pressed',String(o.visible));
    visibility.addEventListener('click',()=>transact(()=>o.visible=!o.visible));
    li.append(b,visibility);
    root.append(li);
  });
  if(!root.children.length){
    const li=document.createElement('li');
    li.className='small muted';
    li.textContent='Пока ничего нет. Добавь предмет из каталога.';
    root.append(li);
  }
}
function applyObjectProperties() {
  const o=selection();
  if(!o) return;
  try{
    const changed={...o,name:$('objectName').value.trim().slice(0,80)||CATALOG[o.type].name,color:$('objColor').value,locked:$('objLocked').checked};
    if(!o.locked){
      Object.assign(changed,{
        x:numeric($('objX').value,-30,30), y:numeric($('objY').value,0,6),z:numeric($('objZ').value,-30,30),
        rotation:numeric($('objR').value,-3600,3600)*Math.PI/180,
        w:numeric($('objW').value,.02,10),d:numeric($('objD').value,.01,10),h:numeric($('objH').value,.005,6),
      });
      if(!fitsRoom(changed)) throw new Error('Предмет выходит за границы комнаты. Уточни координаты или размеры.');
      if(changed.y+changed.h>project.room.h+.01) throw new Error('Предмет выше потолка. Уменьши высоту или положение.');
    }
    transact(()=>Object.assign(o,changed));
    if(collides(o)) toast('Свойства применены. Есть пересечение или конфликт с дверью — проверь расстановку.');
    else toast('Свойства применены');
  }catch(e){$('objectError').textContent=e.message;}
}
function turnSelected(delta) {
  const o=selection();
  if(!o||o.locked) return toast('Выбери незакреплённый предмет');
  const next={...o,rotation:o.rotation+delta};
  if(!fitsRoom(next)) return toast('После поворота предмет выйдет за стену');
  transact(()=>o.rotation=next.rotation);
}
function applyRoom() {
  try{
    const r={...project.room,w:numeric($('roomW').value,1,20),d:numeric($('roomD').value,1,20),h:numeric($('roomH').value,1.8,6)};
    const outside=project.objects.filter(o=>!fitsRoom(o,r)||o.y+o.h>r.h);
    if(outside.length&&!confirm(`${outside.length} предметов окажутся за границами. Применить и затем исправить вручную?`)) return;
    transact(()=>project.room=r);
    $('roomError').textContent='';
    fitCamera();
    if(outside.length) toast('Размеры изменены. Проверь предметы за границами комнаты.');
  }catch(e){$('roomError').textContent=e.message;}
}
function disposeTree(root) {
  if(!root) return;
  const geometries=new Set(),materials=new Set(),textures=new Set();
  root.traverse(o=>{
    if(o.geometry) geometries.add(o.geometry);
    const m=Array.isArray(o.material)?o.material:[o.material];
    m.filter(Boolean).forEach(x=>{
      materials.add(x);
      for(const key of ['map','normalMap','roughnessMap']) if(x[key]) textures.add(x[key]);
    });
  });
  geometries.forEach(g=>g.dispose());
  materials.forEach(m=>m.dispose());
  textures.forEach(t=>t.dispose());
  root.clear();
}
function material(color,extra={}) {
  return new THREE.MeshStandardMaterial({color,roughness:.83,metalness:0,...extra});
}
function mesh(geometry,mat,parent,x=0,y=0,z=0) {
  const m=new THREE.Mesh(geometry,mat);
  m.position.set(x,y,z);
  m.castShadow=true;
  m.receiveShadow=true;
  parent.add(m);
  return m;
}
function box(parent,w,h,d,x,y,z,mat) {
  return mesh(new THREE.BoxGeometry(w,h,d),mat,parent,x,y,z);
}
function cylinder(parent,top,bottom,h,x,y,z,mat,segments=24) {
  return mesh(new THREE.CylinderGeometry(top,bottom,h,segments),mat,parent,x,y,z);
}
function sphere(parent,rx,ry,rz,x,y,z,mat) {
  const m=mesh(new THREE.SphereGeometry(1,18,12),mat,parent,x,y,z);
  m.scale.set(rx,ry,rz);
  return m;
}
function legs(parent,w,d,y,height,mat,thick=.045) {
  for(const x of [-w/2+.08,w/2-.08]){
    for(const z of [-d/2+.08,d/2-.08]) box(parent,thick,height,thick,x,y,z,mat);
  }
}
function makeFurniture(o) {
  const g=new THREE.Group();
  const d=CATALOG[o.type];
  const wood=material('#a48760');
  const dark=material('#565747');
  const primary=material(o.color);
  const light=material('#ece3ce');
  const ceramic=material('#c6a981');
  const normalized=new THREE.Group();
  g.add(normalized);
  const w=d.w,dep=d.d,h=d.h;
  switch(o.type){
    case 'sofa': {
      box(normalized,w-.1,.18,dep-.06,0,.22,0,primary);
      box(normalized,w-.08,.43,.16,0,.58,-dep/2+.08,primary);
      box(normalized,.17,.55,dep,-w/2+.085,.45,0,primary);
      box(normalized,.17,.55,dep,w/2-.085,.45,0,primary);
      for(let i=0;i<3;i++){
        const x=-w/3+i*w/3;
        box(normalized,w/3-.05,.17,dep-.24,x,.4,.055,primary);
        box(normalized,w/3-.06,.29,.13,x,.64,-dep/2+.2,primary);
      }
      legs(normalized,w-.22,dep-.17,.07,.14,wood,.06);
      break;
    }
    case 'armchair': {
      box(normalized,w,.2,dep-.08,0,.32,0,primary);
      box(normalized,w,.49,.16,0,.61,-dep/2+.08,primary);
      box(normalized,.13,.35,dep,-w/2+.065,.49,0,primary);
      box(normalized,.13,.35,dep,w/2-.065,.49,0,primary);
      box(normalized,w-.23,.12,dep-.23,0,.45,.04,primary);
      legs(normalized,w-.1,dep-.1,.13,.26,wood,.05);
      break;
    }
    case 'bed': {
      box(normalized,w,.27,dep,0,.24,0,wood);
      box(normalized,w-.03,.2,dep-.05,0,.46,.01,light);
      box(normalized,w,.68,.08,0,.36,-dep/2,primary);
      box(normalized,w-.04,.05,dep*.58,0,.585,dep*.18,primary);
      sphere(normalized,.31,.07,.2,-w*.24,.59,-dep*.3,light);
      sphere(normalized,.31,.07,.2,w*.24,.59,-dep*.3,light);
      break;
    }
    case 'desk':
    case 'table':
    case 'coffee': {
      const height=h-.055;
      box(normalized,w,.055,dep,0,h-.0275,0,primary);
      legs(normalized,w,dep,height/2,height,wood,o.type==='coffee'?.055:.045);
      if(o.type==='desk'){
        box(normalized,.35,.13,dep*.8,w/2-.23,h-.12,0,wood);
        box(normalized,.15,.01,.015,w/2-.23,h-.13,dep*.405,dark);
      }
      if(o.type==='coffee'){
        box(normalized,w*.65,.018,dep*.65,0,.12,0,wood);
        box(normalized,.24,.032,.18,.1,h+.016,0,light);
        box(normalized,.22,.022,.17,.08,h+.043,0,primary);
      }
      break;
    }
    case 'chair': {
      box(normalized,w,.055,dep,0,.46,0,primary);
      box(normalized,w,.32,.055,0,.69,-dep/2+.025,primary);
      legs(normalized,w+.03,dep+.03,.22,.44,wood,.035);
      break;
    }
    case 'cabinet':
    case 'nightstand':
    case 'wardrobe': {
      box(normalized,w,h-.09,dep,0,h/2+.045,0,primary);
      const fronts=o.type==='wardrobe'?2:3;
      for(let i=0;i<fronts;i++){
        if(o.type==='wardrobe'){
          box(normalized,w/2-.018,h-.14,.02,-w/4+i*w/2,h/2+.055,dep/2+.014,light);
          box(normalized,.012,.16,.025,-.04+i*.08,h*.5,dep/2+.035,dark);
        }else{
          const y=.1+(i+.5)*(h-.12)/fronts;
          box(normalized,w-.04,(h-.15)/fronts-.012,.02,0,y,dep/2+.014,primary);
          box(normalized,.13,.016,.035,0,y+.025,dep/2+.032,dark);
        }
      }
      legs(normalized,w,dep,.045,.09,wood,.05);
      break;
    }
    case 'shelf': {
      box(normalized,.04,h,dep,-w/2+.02,h/2,0,primary);
      box(normalized,.04,h,dep,w/2-.02,h/2,0,primary);
      for(let i=0;i<5;i++) box(normalized,w,.035,dep,0,.05+i*(h-.07)/4,0,primary);
      for(let i=0;i<8;i++){
        const y=.11+Math.floor(i/3)*.41;
        const x=-.3+(i%3)*.18;
        box(normalized,.085,.24+(i%2)*.06,.18,x,y+.12,0,material(['#8b9b80','#cfba96','#a38769'][i%3]));
      }
      break;
    }
    case 'bench': {
      box(normalized,w,.16,dep,0,h-.08,0,primary);
      legs(normalized,w,dep,(h-.16)/2,h-.16,wood,.055);
      break;
    }
    case 'rug': {
      const rugMat=material(o.color);
      box(normalized,w,.012,dep,0,.009,0,rugMat);
      const border=material(new THREE.Color(o.color).multiplyScalar(.88));
      box(normalized,w-.12,.002,.018,0,.016,-dep/2+.065,border);
      box(normalized,w-.12,.002,.018,0,.016,dep/2-.065,border);
      for(const x of [-w/2+.06,w/2-.06]) box(normalized,.018,.002,dep-.12,x,.016,0,border);
      break;
    }
    case 'cushion': {
      sphere(normalized,w/2,h/2,dep/2,0,h/2,0,primary);
      break;
    }
    case 'plant':
    case 'smallplant': {
      const potH=h*.29;
      cylinder(normalized,w*.28,w*.23,potH,0,potH/2,0,ceramic);
      cylinder(normalized,w*.245,w*.245,.014,0,potH,0,material('#514635'));
      cylinder(normalized,.012,.014,h*.53,0,potH+h*.22,0,wood,8);
      const leaves=o.type==='plant'?11:7;
      for(let i=0;i<leaves;i++){
        const angle=i*2.399;
        const level=potH+h*.16+(i%4)*h*.12;
        const leaf=sphere(normalized,w*.14,h*.15,w*.065,Math.cos(angle)*w*.18,level,Math.sin(angle)*w*.18,primary);
        leaf.rotation.z=Math.cos(angle)*.6;
        leaf.rotation.x=Math.sin(angle)*.6;
      }
      break;
    }
    case 'art': {
      box(normalized,w,h,dep,0,h/2,0,wood);
      box(normalized,w-.04,h-.04,.006,0,h/2,dep/2+.005,light);
      const artMat=material(o.color);
      sphere(normalized,w*.22,h*.19,.004,-w*.12,h*.63,dep/2+.012,artMat);
      box(normalized,w*.45,h*.14,.004,w*.11,h*.27,dep/2+.015,artMat);
      break;
    }
    case 'wallshelf': {
      box(normalized,w,h,dep,0,h/2,0,primary);
      break;
    }
    case 'floorlamp':
    case 'desklamp': {
      const pole=o.type==='floorlamp'?.021:.016;
      cylinder(normalized,w*.31,w*.34,.03,0,.015,0,dark);
      cylinder(normalized,pole,pole,h*.78,0,h*.4,0,dark,12);
      cylinder(normalized,w*.26,w*.5,h*.25,0,h*.85,0,primary);
      cylinder(normalized,w*.44,w*.44,.006,0,h*.73,0,material('#fff0bd',{emissive:'#c1a374',emissiveIntensity:project.room.light==='evening'?.5:.12}));
      break;
    }
  }
  normalized.scale.set(o.w/w,o.h/h,o.d/dep);
  g.position.set(o.x,o.y,o.z);
  g.rotation.y=o.rotation;
  g.visible=o.visible;
  g.userData.itemId=o.id;
  g.traverse(child=>child.userData.itemId=o.id);
  return g;
}
function floorTexture(type) {
  if(type==='plain') return null;
  const c=document.createElement('canvas');
  c.width=c.height=512;
  const ctx=c.getContext('2d');
  if(type==='wood'){
    ctx.fillStyle='#c5ac86';ctx.fillRect(0,0,512,512);
    const colors=['#cbb48f','#bfa47e','#c9ae85','#c3a783'];
    for(let row=0;row<8;row++){
      ctx.fillStyle=colors[row%4];ctx.fillRect(0,row*64,512,64);
      ctx.fillStyle='#a58d6c';ctx.fillRect(0,row*64,512,1);
      const shift=(row%2)*180;
      ctx.fillRect(shift,row*64,1,64);
      ctx.fillRect(shift+270,row*64,1,64);
      for(let n=0;n<5;n++){
        ctx.fillStyle='rgba(103,77,44,.045)';
        ctx.fillRect((n*113+row*31)%512,row*64+9+n*9,75+n*15,1);
      }
    }
  }else{
    ctx.fillStyle='#d7d2c5';ctx.fillRect(0,0,512,512);
    ctx.strokeStyle='#aaa99e';ctx.lineWidth=3;
    ctx.strokeRect(1,1,254,254);ctx.strokeRect(257,1,254,254);
    ctx.strokeRect(1,257,254,254);ctx.strokeRect(257,257,254,254);
  }
  const tex=new THREE.CanvasTexture(c);
  tex.colorSpace=THREE.SRGBColorSpace;
  tex.wrapS=tex.wrapT=THREE.RepeatWrapping;
  tex.repeat.set(project.room.w/2,project.room.d/2);
  return tex;
}
function buildRoom() {
  const r=project.room;
  const wall=material(r.wall);
  const trim=material('#eeeadd');
  const floorMat=material(r.floor==='plain'?'#d3c9b4':'#ffffff');
  floorMat.map=floorTexture(r.floor);
  box(roomGroup,r.w,.09,r.d,0,-.055,0,floorMat);
  box(roomGroup,r.w+.12,.18,r.d+.12,0,-.18,0,material('#e2dfd3'));
  const backZ=-r.d/2-.04;
  if(r.window&&r.w>2&&r.h>2.1){
    const winW=Math.min(1.65,r.w*.47),sill=.92,winH=Math.min(1.25,r.h-1.12),winX=r.w*.15;
    const leftEdge=-r.w/2,rightEdge=r.w/2;
    const l=winX-winW/2,rr=winX+winW/2;
    box(roomGroup,l-leftEdge,r.h,.09,(l+leftEdge)/2,r.h/2,backZ,wall);
    box(roomGroup,rightEdge-rr,r.h,.09,(rr+rightEdge)/2,r.h/2,backZ,wall);
    box(roomGroup,winW,sill,.09,winX,sill/2,backZ,wall);
    box(roomGroup,winW,r.h-sill-winH,.09,winX,sill+winH+(r.h-sill-winH)/2,backZ,wall);
    const pane=material('#d5e6dc',{roughness:.3,transparent:true,opacity:.65});
    box(roomGroup,winW,winH,.015,winX,sill+winH/2,backZ,pane);
    for(const x of [l,winX,rr]) box(roomGroup,.045,winH+.06,.09,x,sill+winH/2,backZ+.02,trim);
    for(const y of [sill,sill+winH]) box(roomGroup,winW+.08,.045,.11,winX,y,backZ+.02,trim);
    box(roomGroup,winW+.16,.045,.22,winX,sill-.025,backZ+.08,trim);
  }else box(roomGroup,r.w,r.h,.09,0,r.h/2,backZ,wall);
  box(roomGroup,.09,r.h,r.d,-r.w/2-.04,r.h/2,0,wall);
  box(roomGroup,r.w,.065,.025,0,.033,-r.d/2+.015,trim);
  box(roomGroup,.025,.065,r.d,-r.w/2+.015,.033,0,trim);
  if(r.door){
    const doorW=Math.min(.82,r.w*.38);
    const doorX=-r.w/2+.78;
    const dz=r.d/2-.01;
    box(roomGroup,doorW,.012,.07,doorX,.012,dz,woodMaterial());
    const arcPoints=[];
    for(let i=0;i<=24;i++){
      const a=Math.PI+i/24*Math.PI/2;
      arcPoints.push(new THREE.Vector3(doorX-doorW/2+Math.cos(a+Math.PI)*doorW,.018,dz-Math.sin(a+Math.PI)*doorW));
    }
    const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(arcPoints),new THREE.LineBasicMaterial({color:'#a08e71',transparent:true,opacity:.5}));
    roomGroup.add(line);
  }
}
function woodMaterial(){return material('#b69d78');}
function rebuildScene() {
  if(!THREE||!scene) return;
  if(transform) transform.detach();
  if(highlight){scene.remove(highlight);highlight.geometry.dispose();highlight.material.dispose();highlight=null;}
  disposeTree(roomGroup);
  disposeTree(objectGroup);
  meshes.clear();
  buildRoom();
  project.objects.forEach(o=>{
    const g=makeFurniture(o);
    objectGroup.add(g);
    meshes.set(o.id,g);
  });
  grid.position.y=.002;
  applyLighting();
  syncTransform();
  updateHighlight();
  requestRender();
}
function applyLighting() {
  if(!ambient) return;
  const mood=project.room.light;
  ambient.intensity=mood==='evening'?1.35:2.25;
  ambient.color.set(mood==='evening'?'#ffe5bd':'#ffffff');
  sunLight.intensity=mood==='evening'?2.1:mood==='neutral'?2.7:3.3;
  sunLight.color.set(mood==='evening'?'#ffcd8b':mood==='neutral'?'#ffffff':'#fff0d2');
  if(renderer) renderer.toneMappingExposure=mood==='evening'?.9:1;
}
function updateHighlight() {
  if(!scene||!THREE) return;
  if(highlight){scene.remove(highlight);highlight.geometry.dispose();highlight.material.dispose();highlight=null;}
  const g=meshes.get(selectedId);
  if(g&&g.visible){
    highlight=new THREE.BoxHelper(g,0x426e45);
    highlight.material.depthTest=false;
    highlight.material.transparent=true;
    highlight.material.opacity=.7;
    highlight.renderOrder=10;
    scene.add(highlight);
  }
}
function syncTransform() {
  if(!transform) return;
  transform.detach();
  const o=selection(),g=meshes.get(selectedId);
  if(o&&!o.locked&&o.visible&&g&&tool!=='select'&&mode==='3d'){
    transform.setMode(tool==='rotate'?'rotate':'translate');
    transform.showY=tool==='rotate';
    transform.showX=tool!=='rotate';
    transform.showZ=tool!=='rotate';
    transform.setTranslationSnap($('snap').checked?.1:null);
    transform.setRotationSnap($('snap').checked?Math.PI/12:null);
    transform.attach(g);
  }
}
function setTool(next) {
  tool=next;
  [['selectTool','select'],['moveTool','move'],['rotateTool','rotate']].forEach(([el,t])=>$(el).classList.toggle('active',next===t));
  syncTransform();
  requestRender();
}
function requestRender() {
  if(!renderer||renderRequested||document.hidden||mode!=='3d') return;
  renderRequested=true;
  requestAnimationFrame(()=>{
    renderRequested=false;
    controls?.update();
    if(highlight) highlight.update();
    renderer.render(scene,camera);
  });
}
function fitCamera() {
  if(!camera||!controls) return;
  const r=project.room;
  const size=Math.max(r.w,r.d);
  const narrow=Math.max(1,1.25/(camera.aspect||1));
  camera.position.set(size*1.25*narrow,size*1.08*narrow,size*1.48*narrow);
  controls.target.set(0,r.h*.22,0);
  controls.maxDistance=size*6;
  controls.minDistance=.5;
  camera.far=Math.max(100,size*12);
  camera.updateProjectionMatrix();
  controls.update();
  requestRender();
}
function qualitySettings() {
  if(!renderer) return;
  const q=$('quality').value;
  const low=q==='low'||(q==='auto'&&(innerWidth<760||(navigator.hardwareConcurrency||4)<=4));
  renderer.setPixelRatio(Math.min(devicePixelRatio||1,low?1.25:2));
  renderer.shadowMap.enabled=$('shadows').checked&&!low;
  sunLight.castShadow=renderer.shadowMap.enabled;
  sunLight.shadow.mapSize.set(low?512:1024,low?512:1024);
  resizeScene();
  requestRender();
}
function resizeScene() {
  const rect={width:$('stage').clientWidth,height:$('stage').clientHeight};
  if(renderer){
    renderer.setSize(rect.width,rect.height);
    camera.aspect=rect.width/rect.height;
    camera.updateProjectionMatrix();
    requestRender();
  }
  drawPlan();
}
async function start3D() {
  const wait=setTimeout(()=>{
    if(!renderer){
      $('loading').querySelector('p').textContent='3D загружается дольше обычного…';
      const p=$('loading').querySelectorAll('p')[1];
      p.textContent='Можно открыть план комнаты — он работает без 3D-библиотеки.';
    }
  },12000);
  try{
    THREE=await import('three');
    ({OrbitControls}=await import('three/addons/controls/OrbitControls.js'));
    ({TransformControls}=await import('three/addons/controls/TransformControls.js'));
    scene=new THREE.Scene();
    scene.background=new THREE.Color('#e9ece5');
    camera=new THREE.PerspectiveCamera(36,1,.05,150);
    renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
    renderer.outputColorSpace=THREE.SRGBColorSpace;
    renderer.toneMapping=THREE.ACESFilmicToneMapping;
    renderer.shadowMap.type=THREE.PCFSoftShadowMap;
    renderer.domElement.setAttribute('aria-label','3D-комната. Перетаскивай для вращения, выбирай предметы нажатием.');
    renderer.domElement.tabIndex=0;
    $('scene').append(renderer.domElement);
    controls=new OrbitControls(camera,renderer.domElement);
    controls.enableDamping=false;
    controls.maxPolarAngle=Math.PI/2-.035;
    controls.addEventListener('change',requestRender);
    ambient=new THREE.HemisphereLight('#ffffff','#a5ad91',2.25);
    scene.add(ambient);
    sunLight=new THREE.DirectionalLight('#fff0d2',3.3);
    sunLight.position.set(-3,8,5);
    sunLight.castShadow=true;
    sunLight.shadow.camera.left=-12;
    sunLight.shadow.camera.right=12;
    sunLight.shadow.camera.top=12;
    sunLight.shadow.camera.bottom=-12;
    sunLight.shadow.normalBias=.025;
    sunLight.shadow.bias=-.0002;
    scene.add(sunLight);
    const ground=mesh(new THREE.PlaneGeometry(150,150),material('#e9ece5'),scene,0,-.29,0);
    ground.rotation.x=-Math.PI/2;
    ground.castShadow=false;
    worldGroup=new THREE.Group();
    roomGroup=new THREE.Group();
    objectGroup=new THREE.Group();
    worldGroup.add(roomGroup,objectGroup);
    scene.add(worldGroup);
    grid=new THREE.GridHelper(40,200,'#8a9a81','#bdc6b5');
    grid.visible=false;
    scene.add(grid);
    transform=new TransformControls(camera,renderer.domElement);
    transform.setSize(.8);
    scene.add(transform.getHelper());
    transform.addEventListener('dragging-changed',event=>{
      controls.enabled=!event.value;
      dragging=event.value;
      if(event.value) dragSnapshot=snapshot();
      else {
        const o=selection(),g=meshes.get(selectedId);
        if(o&&g){
          const next={...o,x:round(g.position.x),z:round(g.position.z),rotation:round(g.rotation.y)};
          if(!fitsRoom(next)){
            if(dragSnapshot) project=JSON.parse(dragSnapshot);
            toast('Предмет не должен выходить за стену');
          }else{
            Object.assign(o,next);
            pushHistory(dragSnapshot);
          }
          syncAll();
        }
        dragSnapshot=null;
      }
    });
    transform.addEventListener('objectChange',()=>{updateHighlight();requestRender();});
    transform.addEventListener('change',requestRender);
    renderer.domElement.addEventListener('pointerdown',e=>pointerStart={x:e.clientX,y:e.clientY,at:performance.now()});
    renderer.domElement.addEventListener('pointerup',e=>{
      if(!pointerStart||dragging||transform.axis||Math.hypot(e.clientX-pointerStart.x,e.clientY-pointerStart.y)>5) return;
      const rect=renderer.domElement.getBoundingClientRect();
      const mouse=new THREE.Vector2((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1);
      const ray=new THREE.Raycaster();
      ray.setFromCamera(mouse,camera);
      const hit=ray.intersectObjects([...meshes.values()].filter(m=>m.visible),true)[0];
      selectObject(hit?hit.object.userData.itemId:null);
      pointerStart=null;
    });
    renderer.domElement.addEventListener('webglcontextlost',e=>{
      e.preventDefault();
      toast('3D-контекст потерян. Сохрани JSON; план комнаты остаётся доступен.');
      setView('plan');
    });
    renderer.domElement.addEventListener('webglcontextrestored',()=>{
      rebuildScene();
      toast('3D-контекст восстановлен');
    });
    rebuildScene();
    qualitySettings();
    fitCamera();
    $('loading').hidden=true;
    requestRender();
  }catch(e){
    console.error('3D initialization:',e);
    $('loading').hidden=true;
    setView('plan');
    $('view3d').disabled=true;
    $('view3d').title='3D недоступно: проверь WebGL и доступ к CDN, затем перезагрузи страницу';
    toast('3D недоступно. Открыт рабочий план; фото, размеры и JSON доступны.');
  }finally{
    clearTimeout(wait);
  }
}
function setView(next) {
  mode=next;
  $('view3d').classList.toggle('active',next==='3d');
  $('viewPlan').classList.toggle('active',next==='plan');
  $('view3d').setAttribute('aria-pressed',String(next==='3d'));
  $('viewPlan').setAttribute('aria-pressed',String(next==='plan'));
  $('scene').hidden=next!=='3d';
  $('plan').hidden=next!=='plan';
  if(next==='plan') $('loading').hidden=true;
  syncTransform();
  resizeScene();
}
function planMetrics(canvas) {
  const w=canvas.width/(canvas._ratio||1),h=canvas.height/(canvas._ratio||1);
  const scale=Math.min((w-115)/project.room.w,(h-135)/project.room.d)*planScale;
  return {w,h,scale,cx:w/2+12,cz:h/2+15};
}
function paintPlan(canvas,exporting=false) {
  const ctx=canvas.getContext('2d');
  const ratio=canvas._ratio||1;
  const {w,h,scale,cx,cz}=planMetrics(canvas);
  const r=project.room;
  ctx.setTransform(ratio,0,0,ratio,0,0);
  ctx.fillStyle='#e9ece5';ctx.fillRect(0,0,w,h);
  ctx.save();ctx.translate(cx,cz);ctx.scale(scale,scale);
  ctx.fillStyle='#e1d2b7';ctx.fillRect(-r.w/2,-r.d/2,r.w,r.d);
  if($('gridBtn').getAttribute('aria-pressed')==='true'){
    ctx.strokeStyle='#c1bba9';ctx.lineWidth=.006;
    for(let x=-r.w/2;x<=r.w/2;x+=.2){ctx.beginPath();ctx.moveTo(x,-r.d/2);ctx.lineTo(x,r.d/2);ctx.stroke();}
    for(let z=-r.d/2;z<=r.d/2;z+=.2){ctx.beginPath();ctx.moveTo(-r.w/2,z);ctx.lineTo(r.w/2,z);ctx.stroke();}
  }
  const ordered=[...project.objects].filter(o=>o.visible).sort((a,b)=>(CATALOG[a.type].flat?0:1)-(CATALOG[b.type].flat?0:1));
  for(const o of ordered){
    ctx.save();ctx.translate(o.x,o.z);ctx.rotate(-o.rotation);
    ctx.fillStyle=o.color;ctx.strokeStyle=o.id===selectedId&&!exporting?'#285546':'#8e8e78';
    ctx.lineWidth=o.id===selectedId&&!exporting?.035:.012;
    if(CATALOG[o.type].round){ctx.beginPath();ctx.ellipse(0,0,o.w/2,o.d/2,0,0,Math.PI*2);ctx.fill();ctx.stroke();}
    else{
      ctx.fillRect(-o.w/2,-o.d/2,o.w,o.d);ctx.strokeRect(-o.w/2,-o.d/2,o.w,o.d);
      if(o.type==='sofa'){
        ctx.fillStyle='#00000015';ctx.fillRect(-o.w/2,-o.d/2,o.w,o.d*.17);
        ctx.fillRect(-o.w/2,-o.d/2,o.w*.07,o.d);
        ctx.fillRect(o.w*.43,-o.d/2,o.w*.07,o.d);
      }
    }
    ctx.restore();
  }
  ctx.strokeStyle='#a4aa97';ctx.lineWidth=.065;ctx.strokeRect(-r.w/2,-r.d/2,r.w,r.d);
  if(r.window){
    const win=Math.min(1.65,r.w*.47);
    ctx.strokeStyle='#7fa3a0';ctx.lineWidth=.07;ctx.beginPath();ctx.moveTo(r.w*.15-win/2,-r.d/2);ctx.lineTo(r.w*.15+win/2,-r.d/2);ctx.stroke();
  }
  if(r.door){
    const doorW=Math.min(.82,r.w*.38),dx=-r.w/2+.78;
    ctx.strokeStyle='#e9ece5';ctx.lineWidth=.09;ctx.beginPath();ctx.moveTo(dx-doorW/2,r.d/2);ctx.lineTo(dx+doorW/2,r.d/2);ctx.stroke();
    ctx.strokeStyle='#8e8e78';ctx.lineWidth=.015;
    ctx.beginPath();ctx.arc(dx-doorW/2,r.d/2,doorW,-Math.PI/2,0);ctx.stroke();
    ctx.beginPath();ctx.moveTo(dx-doorW/2,r.d/2);ctx.lineTo(dx-doorW/2,r.d/2-doorW);ctx.stroke();
  }
  ctx.restore();
  ctx.fillStyle='#52604d';ctx.font='12px system-ui';ctx.textAlign='center';
  ctx.fillText(`${format(r.w)} м`,cx,cz-r.d/2*scale-16);
  ctx.save();ctx.translate(cx-r.w/2*scale-17,cz);ctx.rotate(-Math.PI/2);ctx.fillText(`${format(r.d)} м`,0,0);ctx.restore();
}
function drawPlan() {
  const canvas=$('plan');
  const rect={width:$('stage').clientWidth,height:$('stage').clientHeight};
  if(rect.width<1||rect.height<1) return;
  canvas._ratio=Math.min(devicePixelRatio||1,2);
  canvas.width=Math.round(rect.width*canvas._ratio);
  canvas.height=Math.round(rect.height*canvas._ratio);
  if(project) paintPlan(canvas);
}
$('plan').addEventListener('pointerup',e=>{
  const rect=$('plan').getBoundingClientRect();
  const m=planMetrics($('plan'));
  const x=(e.clientX-rect.left-m.cx)/m.scale;
  const z=(e.clientY-rect.top-m.cz)/m.scale;
  const hit=[...project.objects].reverse().filter(o=>o.visible).find(o=>{
    const dx=x-o.x,dz=z-o.z,c=Math.cos(o.rotation),s=Math.sin(o.rotation);
    const lx=dx*c-dz*s,lz=dx*s+dz*c;
    return Math.abs(lx)<=o.w/2&&Math.abs(lz)<=o.d/2;
  });
  selectObject(hit?.id||null);
});
function zoom(factor) {
  if(mode==='plan'){
    planScale=Math.max(.6,Math.min(2,planScale*factor));drawPlan();return;
  }
  if(!camera) return;
  const v=camera.position.clone().sub(controls.target).multiplyScalar(1/factor);
  if(v.length()<controls.minDistance||v.length()>controls.maxDistance) return;
  camera.position.copy(controls.target.clone().add(v));
  controls.update();requestRender();
}
function focusSelected() {
  const o=selection();
  if(!o||!camera) return;
  controls.target.set(o.x,o.y+o.h*.5,o.z);
  camera.position.set(o.x+2.8,o.y+2.6,o.z+3.3);
  controls.update();requestRender();
}
async function readPhoto(file) {
  $('photoError').textContent='';
  if(!file) return;
  if(file.size>MAX_FILE) throw new Error('Файл больше 15 МБ. Уменьши изображение.');
  if(!['image/jpeg','image/png','image/webp'].includes(file.type)) throw new Error('Нужен JPEG, PNG или WebP. HEIC сначала преобразуй в JPEG.');
  if(file.size===0) throw new Error('Файл пустой');
  $('pointStatus').textContent='Декодируем изображение…';
  let bitmap;
  try{bitmap=await createImageBitmap(file);}catch{throw new Error('Не удалось прочитать изображение. Возможно, файл повреждён.');}
  try{
    if(bitmap.width*bitmap.height>40000000) throw new Error('Фото больше 40 мегапикселей. Уменьши разрешение.');
    const scale=Math.min(1,1600/Math.max(bitmap.width,bitmap.height));
    const canvas=document.createElement('canvas');
    canvas.width=Math.round(bitmap.width*scale);canvas.height=Math.round(bitmap.height*scale);
    canvas.getContext('2d').drawImage(bitmap,0,0,canvas.width,canvas.height);
    pendingPhoto=canvas.toDataURL('image/jpeg',.88);
    photoImage=new Image();
    photoImage.src=pendingPhoto;
    await photoImage.decode();
    photoPoints=[];
    clearDepthResult();
    depthMessage('Новое фото. Запусти оценку глубины, чтобы построить его рельеф.');
    $('photoEditor').hidden=false;
    drawPhoto();
    $('photoW').value=project.room.w;$('photoD').value=project.room.d;$('photoH').value=project.room.h;
    $('pointStatus').textContent=`${bitmap.width} × ${bitmap.height} / отметь 4 угла пола`;
  }finally{bitmap.close();}
}
function drawPhoto() {
  if(!photoImage) return;
  const c=$('photoCanvas');
  c.width=1000;c.height=Math.max(300,Math.round(1000*photoImage.height/photoImage.width));
  const ctx=c.getContext('2d');
  ctx.drawImage(photoImage,0,0,c.width,c.height);
  if(photoPoints.length){
    ctx.beginPath();
    photoPoints.forEach((p,i)=>i?ctx.lineTo(p.x*c.width,p.y*c.height):ctx.moveTo(p.x*c.width,p.y*c.height));
    if(photoPoints.length===4) ctx.closePath();
    ctx.strokeStyle='#f6e4a9';ctx.lineWidth=4;ctx.stroke();
    if(photoPoints.length===4){ctx.fillStyle='#f6e4a930';ctx.fill();}
    photoPoints.forEach((p,i)=>{
      ctx.beginPath();ctx.arc(p.x*c.width,p.y*c.height,18,0,Math.PI*2);
      ctx.fillStyle='#285546';ctx.fill();ctx.strokeStyle='white';ctx.lineWidth=3;ctx.stroke();
      ctx.fillStyle='white';ctx.font='bold 18px system-ui';ctx.textAlign='center';ctx.textBaseline='middle';
      ctx.fillText(String(i+1),p.x*c.width,p.y*c.height);
    });
  }
  $('pointStatus').textContent=`${photoPoints.length} / 4 угла отмечено`;
}
$('photoCanvas').addEventListener('pointerdown',e=>{
  if(!photoImage) return;
  const rect=e.currentTarget.getBoundingClientRect();
  const p={x:Math.max(0,Math.min(1,(e.clientX-rect.left)/rect.width)),y:Math.max(0,Math.min(1,(e.clientY-rect.top)/rect.height))};
  if(photoPoints.length===4) return toast('Убери последнюю точку, чтобы поставить её заново');
  photoPoints.push(p);drawPhoto();
});
function polygonArea(points) {
  let sum=0;
  for(let i=0;i<points.length;i++){
    const a=points[i],b=points[(i+1)%points.length];sum+=a.x*b.y-b.x*a.y;
  }
  return Math.abs(sum)/2;
}
function properCross(a,b,c,d) {
  const side=(p,q,r)=>(q.x-p.x)*(r.y-p.y)-(q.y-p.y)*(r.x-p.x);
  return side(a,b,c)*side(a,b,d)<0&&side(c,d,a)*side(c,d,b)<0;
}
function createFromPhoto() {
  try{
    if(!pendingPhoto) throw new Error('Сначала выбери фото');
    if(photoPoints.length!==4) throw new Error('Отметь четыре угла видимой области пола');
    if(polygonArea(photoPoints)<.003) throw new Error('Метки почти на одной линии. Уточни углы.');
    if(properCross(photoPoints[0],photoPoints[1],photoPoints[2],photoPoints[3])||properCross(photoPoints[1],photoPoints[2],photoPoints[3],photoPoints[0])) throw new Error('Контур пересекает сам себя. Отметь углы по кругу.');
    const r={...project.room,w:numeric($('photoW').value,1,20),d:numeric($('photoD').value,1,20),h:numeric($('photoH').value,1.8,6)};
    if(!confirm('Создать комнату по введённым размерам? Это заменит текущую геометрию. Сохрани JSON, если нужна резервная копия.')) return;
    transact(()=>{
      project.room=r;project.source='photo';project.points=clone(photoPoints);
      if(!$('keepFurniture').checked) project.objects=[];
      else project.objects=project.objects.filter(o=>fitsRoom(o,r)&&o.y+o.h<=r.h);
    });
    photoData=pendingPhoto;
    syncReference();fitCamera();closeDialog('photoDialog');setTab('room');
    $('introCaption').textContent='Твоя комната создана по введённым размерам. Добавляй мебель и уточняй расстановку — снимок остаётся ориентиром.';
    toast('Комната готова к ручному редактированию');
  }catch(e){$('photoError').textContent=e.message;}
}
function syncReference() {
  $('reference').hidden=!photoData;
  if(photoData) $('referenceImg').src=photoData;
  else $('referenceImg').removeAttribute('src');
}
function cozySuggestions() {
  const style=$('cozyStyle').value;
  const palette={
    warm:{wall:'#e2e0d2',rug:'#d9c6a4',cushion:'#758267',light:'evening'},
    scandi:{wall:'#e9e9de',rug:'#dcd7c9',cushion:'#9eaa9a',light:'day'},
    night:{wall:'#9caa96',rug:'#c2ac87',cushion:'#6d7658',light:'evening'},
    study:{wall:'#e2e5da',rug:'#ccc8b0',cushion:'#83917a',light:'neutral'},
  }[style];
  const results=[{kind:'mood',name:'Согласовать стены и свет',reason:'Единая палитра и выбранное настроение освещения.',palette}];
  const working=clone(project.objects);
  const types=[];
  if($('allowPlants').checked&&!working.some(o=>o.type==='plant'||o.type==='smallplant')) types.push('plant');
  if($('allowTextile').checked&&!working.some(o=>o.type==='rug')) types.push('rug');
  if(!working.some(o=>o.type==='floorlamp')) types.push('floorlamp');
  if(style==='study'&&!working.some(o=>o.type==='desk')) types.push('desk');
  for(const type of types){
    const item=findPosition(type,working);
    if(item){
      if(type==='rug') item.color=palette.rug;
      working.push(item);
      results.push({kind:'add',name:`Добавить: ${item.name.toLowerCase()}`,reason:type==='rug'?'Обозначит зону и добавит текстиль.':type==='plant'?'Добавит зелёный акцент без блокирования двери.':type==='desk'?'Организует рабочую зону.':'Добавит визуальный источник вечернего света.',item});
    }
  }
  const sofa=working.find(o=>o.type==='sofa'&&!o.locked);
  if(sofa&&$('allowTextile').checked&&!working.some(o=>o.type==='cushion')){
    const cushion=makeItem('cushion',{x:sofa.x,y:sofa.y+sofa.h*.55,z:sofa.z,color:palette.cushion});
    results.push({kind:'add',name:'Добавить подушку',reason:'Текстильный акцент на незакреплённом диване.',item:cushion});
  }
  recommendations=results;
  const root=$('recommendations');root.replaceChildren();
  results.forEach((r,index)=>{
    const row=document.createElement('div');row.className='recommendation';
    const label=document.createElement('label');label.className='check-label';
    const check=document.createElement('input');check.type='checkbox';check.checked=true;check.dataset.recommendation=String(index);
    const content=document.createElement('span');
    const title=document.createElement('strong');title.textContent=r.name;
    const reason=document.createElement('p');reason.textContent=r.reason;
    content.append(title,reason);label.append(check,content);row.append(label);root.append(row);
  });
}
function applyCozy() {
  const chosen=[...document.querySelectorAll('[data-recommendation]:checked')].map(c=>recommendations[Number(c.dataset.recommendation)]);
  if(!chosen.length) return toast('Выбери хотя бы одно изменение');
  if(project.objects.length+chosen.filter(r=>r.kind==='add').length>MAX_OBJECTS) return toast('Слишком много предметов');
  transact(()=>{
    for(const r of chosen){
      if(r.kind==='mood'){
        project.room.wall=r.palette.wall;project.room.light=r.palette.light;
      }else project.objects.push(clone(r.item));
    }
  });
  closeDialog('cozyDialog');
  toast('Вариант применён. Весь набор можно отменить одной кнопкой «Отменить».');
}
function safeName() { return project.name.replace(/[^\p{L}\p{N}_-]+/gu,'_').slice(0,60)||'roomcraft'; }
function download(data,name,type) {
  const blob=data instanceof Blob?data:new Blob([data],{type});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');a.href=url;a.download=name;
  document.body.append(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),10000);
}
function exportJSON() {
  const out=clone(project);
  if($('includePhoto').checked&&photoData) out.referencePhoto=photoData;
  download(JSON.stringify(out,null,2),`${safeName()}.json`,'application/json');
  $('saveState').textContent='JSON подготовлен / проверь загрузки';
  dirty=false;
  toast('JSON подготовлен. Проверь папку загрузок браузера.');
}
async function importJSON(file) {
  if(!file) return;
  if(file.size>MAX_FILE) throw new Error('JSON больше 15 МБ');
  let raw;
  try{raw=JSON.parse(await file.text());}catch{throw new Error('Не удалось разобрать JSON');}
  const validated=validateProject(raw);
  let nextPhoto=null;
  if(typeof raw.referencePhoto==='string'){
    if(!raw.referencePhoto.startsWith('data:image/jpeg;base64,')||raw.referencePhoto.length>MAX_FILE*1.4) throw new Error('Некорректное фото в проекте');
    const image=new Image();image.src=raw.referencePhoto;
    try{await image.decode();}catch{throw new Error('Повреждено фото внутри проекта');}
    if(image.naturalWidth*image.naturalHeight>40000000) throw new Error('Фото в JSON слишком большое');
    nextPhoto=raw.referencePhoto;
  }
  if(!confirm('Открыть проект вместо текущего? Несохранённые изменения будут потеряны.')) return;
  project=validated;photoData=nextPhoto;
  undoStack=[];redoStack=[];selectedId=null;
  syncReference();syncAll();fitCamera();
  $('saveState').textContent='Проект открыт из JSON';dirty=false;
  closeDialog('exportDialog');toast('Проект открыт');
}
function canvasBlob(canvas){return new Promise((resolve,reject)=>canvas.toBlob(blob=>blob?resolve(blob):reject(new Error('Не удалось создать PNG')),'image/png'));}
async function exportPNG() {
  if(mode==='plan') return exportPlan();
  if(!renderer) throw new Error('3D недоступно. Сохрани план PNG.');
  const old=highlight?.visible;
  if(highlight) highlight.visible=false;
  const helper=transform?.getHelper(),visible=helper?.visible;
  if(helper) helper.visible=false;
  try{
    renderer.render(scene,camera);
    download(await canvasBlob(renderer.domElement),`${safeName()}_вид.png`,'image/png');
  }finally{
    if(highlight) highlight.visible=old;
    if(helper) helper.visible=visible;
    requestRender();
  }
}
async function exportPlan() {
  const c=document.createElement('canvas');c.width=1600;c.height=1400;c._ratio=1;
  const previous=planScale;planScale=1;
  try{paintPlan(c,true);download(await canvasBlob(c),`${safeName()}_план.png`,'image/png');}
  finally{planScale=previous;}
}
async function exportGLB() {
  if(!worldGroup) throw new Error('Для GLB требуется доступный 3D-режим');
  const button=$('saveGLB');button.disabled=true;button.textContent='Собираем GLB…';
  try{
    const {GLTFExporter}=await import('three/addons/exporters/GLTFExporter.js');
    const exporter=new GLTFExporter();
    const bytes=await exporter.parseAsync(worldGroup,{binary:true,onlyVisible:true});
    const {GLTFLoader}=await import('three/addons/loaders/GLTFLoader.js');
    const loaded=await new GLTFLoader().parseAsync(bytes,'');
    let count=0;loaded.scene.traverse(o=>{if(o.isMesh) count++;});
    disposeTree(loaded.scene);
    if(!count) throw new Error('Экспорт не содержит геометрии');
    download(bytes,`${safeName()}.glb`,'model/gltf-binary');
    toast(`GLB проверен повторным чтением: ${count} mesh`);
  }finally{button.disabled=false;button.textContent='Модель GLB';}
}
function csvCell(value) {
  let s=String(value);
  if(/^[\s]*[=+@-]/.test(s)) s="'"+s;
  return '"'+s.replaceAll('"','""')+'"';
}
function exportCSV() {
  const rows=[['Название','Тип','Ширина м','Глубина м','Высота м','X м','Y м','Z м','Цвет']];
  project.objects.forEach(o=>rows.push([o.name,o.type,o.w,o.d,o.h,o.x,o.y,o.z,o.color]));
  download('\ufeff'+rows.map(r=>r.map(csvCell).join(';')).join('\r\n'),`${safeName()}_мебель.csv`,'text/csv;charset=utf-8');
}
async function initStorage() {
  try{
    database=await new Promise((resolve,reject)=>{
      const request=indexedDB.open('roomcraft-v1',1);
      request.onupgradeneeded=()=>request.result.createObjectStore('projects');
      request.onsuccess=()=>resolve(request.result);
      request.onerror=()=>reject(request.error);
      request.onblocked=()=>reject(new Error('Хранилище занято другой вкладкой'));
    });
    storageAvailable=true;
  }catch{
    storageAvailable=false;
    $('localSave').disabled=true;$('restoreLocal').disabled=true;$('clearLocal').disabled=true;
    $('localSave').textContent='Локальное хранилище недоступно / скачай JSON';
  }
}
function storageRequest(method,value) {
  if(!storageAvailable) return Promise.reject(new Error('Хранилище недоступно. Скачай JSON.'));
  return new Promise((resolve,reject)=>{
    const tx=database.transaction('projects',method==='get'?'readonly':'readwrite');
    const store=tx.objectStore('projects');
    let request;
    if(method==='put') request=store.put(value,'last');
    else if(method==='delete') request=store.delete('last');
    else request=store.get('last');
    let result;
    request.onsuccess=()=>result=request.result;
    request.onerror=()=>reject(request.error);
    tx.oncomplete=()=>resolve(result);
    tx.onabort=()=>reject(tx.error||new Error('Сохранение отменено'));
    tx.onerror=()=>reject(tx.error||new Error('Ошибка хранилища'));
  });
}
async function localSave() {
  await storageRequest('put',clone(project));
  $('saveState').textContent=`Локально сохранено в ${new Date().toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'})}`;
  dirty=false;toast('Локальная копия сохранена без фотографии');
}
async function restoreLocal() {
  const raw=await storageRequest('get');
  if(!raw) throw new Error('Локальной копии пока нет');
  const next=validateProject(raw);
  if(!confirm('Заменить текущую сцену локальной копией?')) return;
  project=next;photoData=null;selectedId=null;undoStack=[];redoStack=[];
  syncReference();syncAll();fitCamera();dirty=false;
  $('saveState').textContent='Открыта локальная копия';
  closeDialog('exportDialog');toast('Локальная копия открыта');
}
function diagnostics() {
  let count=0;
  worldGroup?.traverse(o=>{if(o.isMesh) count++;});
  return [
    'RoomCraft 0.1.0 / частичная реализация',
    `Проект: ${project.objects.length} предметов`,
    `3D: ${renderer?'доступно':'недоступно'}`,
    `Mesh: ${count}`,
    `Хранилище: ${storageAvailable?'доступно':'недоступно'}`,
    'Реконструкция: ручная прямоугольная комната',
    'Фото: только браузер / без автосохранения',
    'Нейросеть: опциональный Depth Anything V2 Small / 2.5D, не полный скан',
    'Three.js: 0.170.0 / jsDelivr',
  ].join('\n');
}
function runTests() {
  const results=[];
  function test(name,fn){try{fn();results.push({name,ok:true});}catch(e){results.push({name,ok:false,error:e.message});}}
  const assert=(v,msg='Условие не выполнено')=>{if(!v) throw new Error(msg);};
  test('Десятичная запятая',()=>assert(numeric('2,5',0,5)===2.5));
  test('Отрицательный размер отклонён',()=>{let thrown=false;try{numeric(-1,0,5);}catch{thrown=true;}assert(thrown);});
  test('Infinity отклонён',()=>{let thrown=false;try{numeric(Infinity,0,5);}catch{thrown=true;}assert(thrown);});
  test('Пустое значение отклонено',()=>{let thrown=false;try{numeric('',0,5);}catch{thrown=true;}assert(thrown);});
  test('Площадь прямоугольника',()=>assert(polygonArea([{x:0,y:0},{x:4,y:0},{x:4,y:3},{x:0,y:3}])===12));
  test('Пересечение рёбер',()=>assert(properCross({x:0,y:0},{x:1,y:1},{x:0,y:1},{x:1,y:0})));
  test('Проверка цвета',()=>assert(colorOK('#aabbcc')&&!colorOK('url(javascript:x)')));
  test('Объект помещается',()=>assert(fitsRoom(makeItem('chair'),{w:4,d:4,h:3})));
  test('Объект за стеной',()=>assert(!fitsRoom(makeItem('chair',{x:8}),{w:4,d:4,h:3})));
  test('SAT: пересечение',()=>assert(overlap(makeItem('chair'),makeItem('chair',{x:.1,rotation:.7}))));
  test('SAT: отсутствие пересечения',()=>assert(!overlap(makeItem('chair'),makeItem('chair',{x:2}))));
  test('SAT: симметрия',()=>{const a=makeItem('desk',{rotation:.8}),b=makeItem('chair',{x:.2});assert(overlap(a,b)===overlap(b,a));});
  test('JSON: сохранение кириллицы',()=>{const p=emptyProject();p.name='Комната';assert(validateProject(JSON.parse(JSON.stringify(p))).name==='Комната');});
  test('Будущая схема отклонена',()=>{let thrown=false;try{validateProject({...emptyProject(),version:999});}catch{thrown=true;}assert(thrown);});
  test('Дубликат ID отклонён',()=>{const p=emptyProject(),o=makeItem('chair');p.objects=[o,clone(o)];let thrown=false;try{validateProject(p);}catch{thrown=true;}assert(thrown);});
  test('Неизвестный тип отклонён',()=>{const p=emptyProject();p.objects=[{type:'__proto__'}];let thrown=false;try{validateProject(p);}catch{thrown=true;}assert(thrown);});
  test('CSV: кавычки',()=>assert(csvCell('a"b')==='"a""b"'));
  test('CSV: формула',()=>assert(csvCell(' =1').startsWith('"\'')));
  test('Фабрики 20 типов',()=>assert(Object.keys(CATALOG).length===20));
  test('Фабрики имеют размеры',()=>assert(Object.values(CATALOG).every(d=>d.w>0&&d.d>0&&d.h>0)));
  if(THREE){
    test('Геометрия всех предметов',()=>{
      for(const type of Object.keys(CATALOG)){
        const g=makeFurniture(makeItem(type));let count=0;g.traverse(o=>{if(o.isMesh) count++;});
        assert(count>0,`Нет геометрии: ${type}`);disposeTree(g);
      }
    });
  }
  const passed=results.filter(r=>r.ok).length;
  $('testResults').hidden=false;
  $('testResults').textContent=`${passed} / ${results.length} пройдено\n\n`+results.map(r=>`${r.ok?'PASS':'FAIL'} / ${r.name}${r.error?' / '+r.error:''}`).join('\n');
  return results;
}
async function guarded(fn) {
  try{await fn();}catch(e){console.error(e);toast(e.message||'Операция не выполнена');}
}
$('undoBtn').onclick=()=>historyStep('undo');
$('redoBtn').onclick=()=>historyStep('redo');
$('photoBtn').onclick=()=>openDialog('photoDialog');
$('exportBtn').onclick=()=>openDialog('exportDialog');
$('helpBtn').onclick=()=>{$('diagnostics').textContent=diagnostics();openDialog('helpDialog');};
$('cozyBtn').onclick=()=>{cozySuggestions();openDialog('cozyDialog');};
$('applyRoom').onclick=applyRoom;
$('applyObject').onclick=applyObjectProperties;
$('turnLeft').onclick=()=>turnSelected(-Math.PI/12);
$('turnRight').onclick=()=>turnSelected(Math.PI/12);
$('focusObject').onclick=focusSelected;
$('removeObject').onclick=()=>{
  const o=selection();
  if(!o) return;
  if(o.locked) return toast('Сначала сними закрепление предмета');
  if(!confirm(`Удалить «${o.name}»?`)) return;
  transact(()=>{project.objects=project.objects.filter(x=>x.id!==o.id);selectedId=null;});
};
$('duplicateObject').onclick=()=>{
  const o=selection();
  if(!o) return;
  if(project.objects.length>=MAX_OBJECTS) return toast('Достигнут лимит предметов');
  const next={...clone(o),id:id(),name:`${o.name} / копия`.slice(0,80),x:o.x+.2,z:o.z+.2,locked:false};
  if(!fitsRoom(next)) return toast('Копия не помещается. Сдвинь исходный предмет.');
  transact(()=>project.objects.push(next));selectObject(next.id);
  if(collides(next)) toast('Копия создана с пересечением — перемести её.');
};
$('projectName').addEventListener('change',()=>transact(()=>project.name=$('projectName').value.trim().slice(0,80)||'Моя комната'));
$('wallColor').addEventListener('change',()=>transact(()=>project.room.wall=$('wallColor').value));
$('floorType').addEventListener('change',()=>transact(()=>project.room.floor=$('floorType').value));
$('showDoor').addEventListener('change',()=>transact(()=>project.room.door=$('showDoor').checked));
$('showWindow').addEventListener('change',()=>transact(()=>project.room.window=$('showWindow').checked));
$('shadows').addEventListener('change',qualitySettings);
$('quality').addEventListener('change',qualitySettings);
$('snap').addEventListener('change',syncTransform);
$('view3d').onclick=()=>setView('3d');
$('viewPlan').onclick=()=>setView('plan');
$('selectTool').onclick=()=>setTool('select');
$('moveTool').onclick=()=>setTool('move');
$('rotateTool').onclick=()=>setTool('rotate');
$('gridBtn').onclick=()=>{
  const state=$('gridBtn').getAttribute('aria-pressed')!=='true';
  $('gridBtn').setAttribute('aria-pressed',String(state));
  $('gridBtn').classList.toggle('active',state);
  if(grid)grid.visible=state;
  requestRender();drawPlan();
};
$('homeView').onclick=()=>{planScale=1;fitCamera();drawPlan();};
$('zoomIn').onclick=()=>zoom(1.15);
$('zoomOut').onclick=()=>zoom(1/1.15);
$('catalogSearch').addEventListener('input',renderCatalog);
$('catalogCategory').addEventListener('change',renderCatalog);
$('objectSearch').addEventListener('input',renderObjectList);
$('photoInput').addEventListener('change',e=>readPhoto(e.target.files[0]).catch(error=>$('photoError').textContent=error.message));
$('cameraInput').addEventListener('change',e=>readPhoto(e.target.files[0]).catch(error=>$('photoError').textContent=error.message));
$('undoPoint').onclick=()=>{photoPoints.pop();drawPhoto();};
$('createFromPhoto').onclick=createFromPhoto;
$('deletePhoto').onclick=()=>{
  if(!confirm('Удалить фото из текущей сессии? Скачанные ранее файлы не удалятся.'))return;
  photoData=null;pendingPhoto=null;photoImage=null;photoPoints=[];
  depthGeneration++;clearDepthResult();
  $('photoInput').value='';$('cameraInput').value='';$('photoEditor').hidden=true;
  $('photoCanvas').getContext('2d').clearRect(0,0,$('photoCanvas').width,$('photoCanvas').height);
  syncReference();toast('Фото удалено из текущей сессии');
};
$('recalculateCozy').onclick=cozySuggestions;
$('cozyStyle').onchange=cozySuggestions;
$('allowPlants').onchange=cozySuggestions;
$('allowTextile').onchange=cozySuggestions;
$('applyCozy').onclick=applyCozy;
$('saveJSON').onclick=exportJSON;
$('savePNG').onclick=()=>guarded(exportPNG);
$('savePlan').onclick=()=>guarded(exportPlan);
$('saveGLB').onclick=()=>guarded(exportGLB);
$('saveCSV').onclick=exportCSV;
$('importInput').onchange=e=>guarded(()=>importJSON(e.target.files[0])).finally(()=>e.target.value='');
$('localSave').onclick=()=>guarded(localSave);
$('restoreLocal').onclick=()=>guarded(restoreLocal);
$('clearLocal').onclick=()=>guarded(async()=>{
  if(!confirm('Удалить локальную копию? Текущая сцена останется открытой.'))return;
  await storageRequest('delete');toast('Локальная копия удалена');
});
$('runTests').onclick=runTests;
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>setTab(b.dataset.tab));
document.querySelectorAll('[data-light]').forEach(b=>b.onclick=()=>transact(()=>project.room.light=b.dataset.light));
const WALL_COLORS=['#e2e0d2','#ece8dd','#c8cfba','#9caa96','#d5c1a9','#c8cacc'];
WALL_COLORS.forEach(color=>{
  const b=document.createElement('button');b.className='swatch';b.style.backgroundColor=color;
  b.dataset.color=color;b.setAttribute('aria-label',`Цвет стен ${color}`);b.setAttribute('aria-pressed','false');
  b.onclick=()=>transact(()=>project.room.wall=color);$('wallSwatches').append(b);
});
const dropZone=$('dropZone');
dropZone.addEventListener('dragover',e=>{e.preventDefault();dropZone.style.background='#e5eddf';});
dropZone.addEventListener('dragleave',()=>dropZone.style.background='');
dropZone.addEventListener('drop',e=>{
  e.preventDefault();dropZone.style.background='';
  const file=e.dataTransfer.files[0];
  if(file)readPhoto(file).catch(error=>$('photoError').textContent=error.message);
});
document.addEventListener('keydown',e=>{
  if(['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName)||document.querySelector('dialog[open]'))return;
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){
    e.preventDefault();historyStep(e.shiftKey?'redo':'undo');
  }
  if(e.key==='Escape'){
    if(dragging&&dragSnapshot){
      transform?.reset();project=JSON.parse(dragSnapshot);dragSnapshot=null;dragging=false;controls.enabled=true;syncAll();
    }else selectObject(null);
  }
});
document.addEventListener('visibilitychange',()=>{if(!document.hidden)requestRender();});
window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
window.addEventListener('pagehide',()=>{
  if(renderer){renderer.dispose();}
  database?.close();
  resizeObserver?.disconnect();
});
window.addEventListener('error',event=>{
  console.error('RoomCraft runtime error',event.message);
});
project=demoProject();
renderCatalog();syncAll();
resizeObserver=new ResizeObserver(resizeScene);resizeObserver.observe($('stage'));
initStorage();
start3D();

// Optional real neural inference. No photograph is posted to any remote endpoint.
const DEPTH_MODEL='onnx-community/depth-anything-v2-small';
const DEPTH_REVISION='4472b7362082ad9968fee890ca0f1e5aca36b93d';
let depthEstimator=null;
let depthBusy=false;
let depthGeneration=0;
let depthRenderer=null;
let depthScene=null;
let depthCamera=null;
let depthControls=null;
let depthMesh=null;
let depthBytes=null;
let depthImageWidth=0;
let depthImageHeight=0;
let depthPhoto=null;
let depthResizeObserver=null;
function depthMessage(text){$('depthStatus').textContent=text;}
function drawDepthFrame(){
  if(depthRenderer&&$('depthDialog').open) depthRenderer.render(depthScene,depthCamera);
}
function resizeDepth(){
  if(!depthRenderer) return;
  const w=$('depthViewport').clientWidth,h=$('depthViewport').clientHeight;
  depthRenderer.setSize(w,h);
  depthCamera.aspect=w/h;
  depthCamera.updateProjectionMatrix();
  drawDepthFrame();
}
function releaseDepthScene(){
  if(depthMesh){
    depthScene?.remove(depthMesh);
    depthMesh.geometry.dispose();
    depthMesh.material.map?.dispose();
    depthMesh.material.dispose();
    depthMesh=null;
  }
}
function clearDepthResult(){
  releaseDepthScene();
  depthBytes=null;
  depthPhoto=null;
  $('exportDepthPNG').disabled=true;
  $('exportDepthGLB').disabled=true;
  const c=$('depthMap');
  c.getContext('2d').clearRect(0,0,c.width,c.height);
  drawDepthFrame();
}
function buildDepthRelief(){
  if(!THREE||!depthBytes||!depthPhoto) return;
  if(!depthRenderer){
    depthScene=new THREE.Scene();
    depthScene.background=new THREE.Color('#e9ece5');
    depthCamera=new THREE.PerspectiveCamera(42,1,.05,80);
    depthRenderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
    depthRenderer.setPixelRatio(Math.min(devicePixelRatio||1,1.5));
    depthRenderer.outputColorSpace=THREE.SRGBColorSpace;
    depthRenderer.domElement.setAttribute('aria-label','2.5D-рельеф фотографии, не точный скан комнаты');
    $('depthViewport').append(depthRenderer.domElement);
    depthControls=new OrbitControls(depthCamera,depthRenderer.domElement);
    depthControls.maxPolarAngle=Math.PI*.85;
    depthControls.minDistance=2;
    depthControls.maxDistance=15;
    depthControls.addEventListener('change',drawDepthFrame);
    depthResizeObserver=new ResizeObserver(resizeDepth);
    depthResizeObserver.observe($('depthViewport'));
  }
  releaseDepthScene();
  const segments=128;
  const rows=Math.max(32,Math.round(segments*depthImageHeight/depthImageWidth));
  const geometry=new THREE.PlaneGeometry(4,4*depthImageHeight/depthImageWidth,segments,rows);
  const texture=new THREE.Texture(depthPhoto);
  texture.colorSpace=THREE.SRGBColorSpace;
  texture.needsUpdate=true;
  depthMesh=new THREE.Mesh(geometry,new THREE.MeshBasicMaterial({map:texture,side:THREE.DoubleSide}));
  depthScene.add(depthMesh);
  resizeDepth();
  const tangent=Math.tan(42*Math.PI/360);
  const fit=Math.max((2*depthImageHeight/depthImageWidth)/tangent,2/(tangent*depthCamera.aspect))/.78;
  depthCamera.position.set(.12,.06,Math.max(2.2,fit));
  depthControls.target.set(0,0,0);
  depthControls.update();
  updateDepthStrength();
  resizeDepth();
}
function updateDepthStrength(){
  if(!depthMesh||!depthBytes) return;
  const geometry=depthMesh.geometry;
  const positions=geometry.attributes.position;
  const uv=geometry.attributes.uv;
  const strength=Number($('depthStrength').value);
  for(let i=0;i<positions.count;i++){
    const x=Math.min(depthImageWidth-1,Math.max(0,Math.round(uv.getX(i)*(depthImageWidth-1))));
    const y=Math.min(depthImageHeight-1,Math.max(0,Math.round((1-uv.getY(i))*(depthImageHeight-1))));
    const value=depthBytes[y*depthImageWidth+x]/255;
    positions.setZ(i,(value-.5)*strength);
  }
  positions.needsUpdate=true;
  geometry.computeVertexNormals();
  geometry.computeBoundingSphere();
  drawDepthFrame();
}
function displayDepthMap(raw){
  depthImageWidth=raw.width;
  depthImageHeight=raw.height;
  const channels=raw.channels||1;
  depthBytes=new Uint8Array(raw.width*raw.height);
  const rgba=new Uint8ClampedArray(raw.width*raw.height*4);
  for(let i=0;i<depthBytes.length;i++){
    const value=raw.data[i*channels];
    depthBytes[i]=value;
    rgba[i*4]=value;rgba[i*4+1]=value;rgba[i*4+2]=value;rgba[i*4+3]=255;
  }
  const c=$('depthMap');c.width=raw.width;c.height=raw.height;
  c.getContext('2d').putImageData(new ImageData(rgba,raw.width,raw.height),0,0);
}
async function runDepth(){
  if(depthBusy) return;
  if(!pendingPhoto) return depthMessage('Сначала загрузи фотографию.');
  if(!THREE||!OrbitControls) return depthMessage('Для рельефа нужен загруженный 3D-движок. Проверь WebGL и CDN.');
  if(typeof WebAssembly==='undefined') return depthMessage('WebAssembly недоступен в этом браузере.');
  const generation=++depthGeneration;
  depthBusy=true;
  $('runDepth').disabled=true;
  $('cancelDepth').disabled=false;
  $('releaseDepth').disabled=true;
  depthMessage('Загрузка Transformers.js 3.8.1…');
  try{
    const {pipeline,env}=await import('https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.8.1/dist/transformers.min.js');
    env.allowLocalModels=false;
    env.useBrowserCache=true;
    if(env.backends?.onnx?.wasm) env.backends.onnx.wasm.numThreads=1;
    if(generation!==depthGeneration) return;
    if(!depthEstimator){
      depthEstimator=await pipeline('depth-estimation',DEPTH_MODEL,{
        device:'wasm',dtype:'q8',revision:DEPTH_REVISION,
        progress_callback:event=>{
          if(generation!==depthGeneration) return;
          const file=String(event.file||'').split('/').pop();
          if(event.status==='progress'&&Number.isFinite(event.progress)) depthMessage(`Загрузка ${file}: ${Math.round(event.progress)}%`);
          else if(event.status==='initiate') depthMessage(`Запрашиваем ${file}…`);
          else if(event.status==='ready') depthMessage('Модель загружена.');
        },
      });
    }
    if(generation!==depthGeneration) return;
    depthMessage('Модель вычисляет относительную глубину на твоём устройстве. На слабом устройстве это может занять несколько минут…');
    const input=pendingPhoto;
    const started=performance.now();
    const output=await depthEstimator(input);
    if(generation!==depthGeneration) return;
    depthPhoto=new Image();depthPhoto.src=input;await depthPhoto.decode();
    if(generation!==depthGeneration) return;
    displayDepthMap(output.depth);
    buildDepthRelief();
    $('exportDepthPNG').disabled=false;
    $('exportDepthGLB').disabled=false;
    depthMessage(`Готово за ${((performance.now()-started)/1000).toFixed(1)} с. Светлое ближе, тёмное дальше. Глубина относительная, масштаб условный.`);
  }catch(e){
    console.error('Local depth estimation:',e);
    if(generation===depthGeneration) depthMessage(`Не получилось: ${e.message||'нет поддержки модели или загрузка заблокирована'}. Ручной редактор остаётся доступен.`);
  }finally{
    depthBusy=false;
    $('runDepth').disabled=false;
    $('cancelDepth').disabled=true;
    $('releaseDepth').disabled=false;
  }
}
$('openDepth').onclick=()=>{
  if(!pendingPhoto)return;
  closeDialog('photoDialog');openDialog('depthDialog');resizeDepth();
};
$('runDepth').onclick=runDepth;
$('cancelDepth').onclick=()=>{
  depthGeneration++;
  depthMessage('Результат будет проигнорирован. Уже начатая загрузка или вычисление могут продолжаться до завершения; это не мгновенная остановка WASM.');
  $('cancelDepth').disabled=true;
};
$('depthStrength').oninput=updateDepthStrength;
$('depthDialog').addEventListener('close',()=>{
  if(depthBusy){depthGeneration++;}
});
$('releaseDepth').onclick=()=>guarded(async()=>{
  if(depthBusy) return;
  depthGeneration++;
  if(depthEstimator){await depthEstimator.dispose();depthEstimator=null;}
  releaseDepthScene();
  depthBytes=null;depthPhoto=null;
  $('exportDepthPNG').disabled=true;$('exportDepthGLB').disabled=true;
  $('depthMap').getContext('2d').clearRect(0,0,$('depthMap').width,$('depthMap').height);
  drawDepthFrame();
  depthMessage('Модель и рельеф освобождены из памяти. Файлы модели могут остаться в браузерном сетевом кеше.');
});
$('exportDepthPNG').onclick=()=>guarded(async()=>download(await canvasBlob($('depthMap')),`${safeName()}_глубина.png`,'image/png'));
$('exportDepthGLB').onclick=()=>guarded(async()=>{
  if(!depthMesh)throw new Error('Сначала рассчитай рельеф');
  const {GLTFExporter}=await import('three/addons/exporters/GLTFExporter.js');
  const result=await new GLTFExporter().parseAsync(depthMesh,{binary:true});
  download(result,`${safeName()}_2_5D.glb`,'model/gltf-binary');
});

// Deliberate minimal test hook; excludes personal photo and arbitrary execution.
window.RoomCraftTest={
  runTests,
  snapshot:()=>clone(project),
  diagnostics,
  get meshCount(){let n=0;worldGroup?.traverse(o=>{if(o.isMesh)n++;});return n;},
};
</script>
</body>
</html>'''


class CoreTests(unittest.TestCase):
    def test_decimal_comma(self):
        self.assertEqual(finite_number("2,5", 0, 10), 2.5)

    def test_negative_dimension(self):
        with self.assertRaises(ValueError):
            finite_number(-1, 0, 10)

    def test_infinity(self):
        with self.assertRaises(ValueError):
            finite_number("inf", 0, 10)

    def test_nan(self):
        with self.assertRaises(ValueError):
            finite_number("nan", 0, 10)

    def test_boolean(self):
        with self.assertRaises(ValueError):
            finite_number(True, 0, 10)

    def test_rectangle(self):
        self.assertEqual(polygon_area([(0, 0), (4, 0), (4, 3), (0, 3)]), 12)

    def test_empty_polygon(self):
        self.assertEqual(polygon_area([]), 0)

    def test_concave_polygon(self):
        self.assertEqual(polygon_area([(0, 0), (2, 0), (2, 2), (1, 1), (0, 2)]), 3)

    def test_csv_quotes(self):
        self.assertEqual(safe_csv_cell('a"b'), '"a""b"')

    def test_csv_formula(self):
        self.assertEqual(safe_csv_cell("=1+1"), '"\'=1+1"')

    def test_one_html_document(self):
        self.assertEqual(HTML.count("<!doctype html>"), 1)
        self.assertIn('lang="ru"', HTML)

    def test_no_paid_api(self):
        self.assertNotIn("api.openai.com", HTML)
        self.assertNotIn("api.anthropic.com", HTML)

    def test_browser_upload(self):
        self.assertIn("createImageBitmap(file)", HTML)
        self.assertNotIn("fetch('/upload'", HTML)


def run_streamlit():
    try:
        import streamlit as st
        import streamlit.components.v1 as components
    except ImportError:
        print("Установи Streamlit: python -m pip install streamlit", file=sys.stderr)
        print("Затем: python -m streamlit run main.py", file=sys.stderr)
        raise SystemExit(1)
    st.set_page_config(
        page_title="RoomCraft — твоя комната",
        page_icon="🏡",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(
        """<style>
        .block-container { padding: 0 !important; max-width: 100% !important; }
        header[data-testid="stHeader"] { display: none !important; }
        [data-testid="stToolbar"] { display: none !important; }
        [data-testid="stMainBlockContainer"] { padding: 0 !important; }
        iframe { border: 0; display: block; width: 100%; }
        </style>""",
        unsafe_allow_html=True,
    )
    components.html(HTML, height=1000, scrolling=True)


def main():
    if "--self-test" in sys.argv:
        unittest.main(argv=[sys.argv[0]], exit=True, verbosity=2)
        return
    if "--export-html" in sys.argv:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--export-html", metavar="PATH", required=True)
        args = parser.parse_args()
        Path(args.export_html).write_text(HTML, encoding="utf-8")
        print(f"HTML export written: {args.export_html}")
        return
    run_streamlit()


if __name__ == "__main__":
    main()
