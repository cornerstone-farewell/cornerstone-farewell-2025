#!/usr/bin/env python3
"""
PDF Generator - VS Code-like File Tree Interface
Select files from directory with collapsible folders and convert to PDF
"""
import os
import sys
import webbrowser
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import tempfile
import html
import mimetypes
import json

# Check and install dependencies
def install_dependencies():
    """Install required packages if not present."""
    required = ['flask', 'weasyprint']
    import subprocess
    for package in required:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

install_dependencies()

from flask import Flask, render_template_string, request, jsonify, send_file
from weasyprint import HTML, CSS

# Global variables
app = Flask(__name__)
selected_directory = None
server_thread = None
generated_pdf_path = None

# HTML Template with VS Code-like UI
HTML_TEMPLATE = r'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Generator - File Explorer</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📄</text></svg>">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #1e1e1e;
            color: #cccccc;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .header {
            background: #323233;
            padding: 10px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid #404040;
            flex-shrink: 0;
        }
        .header h1 {
            font-size: 14px;
            font-weight: 500;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .header-actions {
            display: flex;
            gap: 8px;
        }
        .main-container {
            display: flex;
            flex: 1;
            overflow: hidden;
        }
        .sidebar {
            width: 350px;
            background: #252526;
            display: flex;
            flex-direction: column;
            border-right: 1px solid #404040;
        }
        .sidebar-header {
            padding: 10px 15px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #bbbbbb;
            background: #252526;
            border-bottom: 1px solid #404040;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .sidebar-actions {
            display: flex;
            gap: 5px;
        }
        .icon-btn {
            background: transparent;
            border: none;
            color: #cccccc;
            cursor: pointer;
            padding: 4px 6px;
            border-radius: 3px;
            font-size: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .icon-btn:hover {
            background: #404040;
        }
        .search-container {
            padding: 8px 10px;
            border-bottom: 1px solid #404040;
        }
        .search-box {
            width: 100%;
            padding: 6px 10px;
            background: #3c3c3c;
            border: 1px solid #3c3c3c;
            border-radius: 4px;
            color: #cccccc;
            font-size: 13px;
        }
        .search-box:focus {
            outline: none;
            border-color: #007acc;
        }
        .search-box::placeholder {
            color: #888888;
        }
        .file-tree {
            flex: 1;
            overflow-y: auto;
            overflow-x: hidden;
            padding: 5px 0;
        }
        .tree-item {
            display: flex;
            align-items: center;
            padding: 3px 10px;
            cursor: pointer;
            user-select: none;
            white-space: nowrap;
            font-size: 13px;
            position: relative;
        }
        .tree-item:hover {
            background: #2a2d2e;
        }
        .tree-item.filtered-out {
            display: none;
        }
        .tree-indent {
            display: inline-block;
            width: 16px;
            flex-shrink: 0;
        }
        .tree-arrow {
            width: 16px;
            height: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            color: #cccccc;
            font-size: 10px;
            transition: transform 0.1s;
        }
        .tree-arrow.expanded {
            transform: rotate(90deg);
        }
        .tree-arrow.no-arrow {
            visibility: hidden;
        }
        .tree-checkbox {
            width: 16px;
            height: 16px;
            margin-right: 6px;
            flex-shrink: 0;
            accent-color: #007acc;
            cursor: pointer;
        }
        .tree-icon {
            width: 16px;
            height: 16px;
            margin-right: 6px;
            flex-shrink: 0;
            font-size: 14px;
        }
        .tree-label {
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .tree-item.folder > .tree-label {
            color: #cccccc;
            font-weight: 500;
        }
        .tree-item.file > .tree-label {
            color: #cccccc;
        }
        .tree-meta {
            font-size: 11px;
            color: #666666;
            margin-left: 10px;
            flex-shrink: 0;
        }
        .folder-actions {
            display: none;
            gap: 2px;
            margin-left: 5px;
        }
        .tree-item.folder:hover .folder-actions {
            display: flex;
        }
        .folder-btn {
            background: transparent;
            border: none;
            color: #888;
            cursor: pointer;
            padding: 2px 4px;
            border-radius: 2px;
            font-size: 10px;
        }
        .folder-btn:hover {
            background: #404040;
            color: #fff;
        }
        .content {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: #1e1e1e;
        }
        .content-header {
            padding: 15px 20px;
            background: #252526;
            border-bottom: 1px solid #404040;
        }
        .stats-row {
            display: flex;
            gap: 30px;
            margin-bottom: 15px;
        }
        .stat-item {
            display: flex;
            flex-direction: column;
        }
        .stat-value {
            font-size: 24px;
            font-weight: 600;
            color: #007acc;
        }
        .stat-label {
            font-size: 11px;
            color: #888;
            text-transform: uppercase;
        }
        .action-buttons {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s;
        }
        .btn-primary {
            background: #007acc;
            color: #fff;
        }
        .btn-primary:hover {
            background: #0098ff;
        }
        .btn-secondary {
            background: #3c3c3c;
            color: #cccccc;
        }
        .btn-secondary:hover {
            background: #505050;
        }
        .btn-success {
            background: #16825d;
            color: #fff;
        }
        .btn-success:hover {
            background: #1a9f6f;
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .selected-panel {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
        }
        .panel-title {
            font-size: 12px;
            font-weight: 600;
            color: #888;
            text-transform: uppercase;
            margin-bottom: 15px;
            letter-spacing: 0.5px;
        }
        .selected-files-list {
            display: flex;
            flex-direction: column;
            gap: 3px;
        }
        .selected-file-item {
            display: flex;
            align-items: center;
            padding: 6px 10px;
            background: #2d2d2d;
            border-radius: 4px;
            font-size: 12px;
        }
        .selected-file-item .file-icon {
            margin-right: 8px;
        }
        .selected-file-item .file-path {
            flex: 1;
            color: #9cdcfe;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .selected-file-item .remove-btn {
            background: transparent;
            border: none;
            color: #666;
            cursor: pointer;
            padding: 2px 6px;
            border-radius: 2px;
        }
        .selected-file-item .remove-btn:hover {
            background: #404040;
            color: #ff6b6b;
        }
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .empty-state-icon {
            font-size: 48px;
            margin-bottom: 15px;
        }
        .status-bar {
            background: #007acc;
            padding: 4px 15px;
            font-size: 12px;
            color: #fff;
            display: flex;
            justify-content: space-between;
            flex-shrink: 0;
        }
        .status-bar.error {
            background: #c72e2e;
        }
        .status-bar.success {
            background: #16825d;
        }
        .status-bar.loading {
            background: #68217a;
        }
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }
        ::-webkit-scrollbar-track {
            background: #1e1e1e;
        }
        ::-webkit-scrollbar-thumb {
            background: #424242;
            border-radius: 5px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #555555;
        }
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.7);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        .modal-overlay.show {
            display: flex;
        }
        .modal {
            background: #252526;
            border-radius: 8px;
            padding: 30px;
            text-align: center;
            max-width: 400px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);
        }
        .modal-icon {
            font-size: 48px;
            margin-bottom: 15px;
        }
        .modal h2 {
            color: #fff;
            margin-bottom: 10px;
            font-size: 18px;
        }
        .modal p {
            color: #888;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .modal-buttons {
            display: flex;
            gap: 10px;
            justify-content: center;
        }
        .spinner {
            display: inline-block;
            width: 14px;
            height: 14px;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .folder-children {
            /* Container for folder contents */
        }
        .folder-children.collapsed {
            display: none;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📄 PDF Generator</h1>
        <div class="header-actions">
            <button class="btn btn-secondary" id="collapseAllBtn">📁 Collapse All</button>
            <button class="btn btn-secondary" id="expandAllBtn">📂 Expand All</button>
        </div>
    </div>

    <div class="main-container">
        <div class="sidebar">
            <div class="sidebar-header">
                <span>Explorer</span>
                <div class="sidebar-actions">
                    <button class="icon-btn" id="refreshBtn" title="Refresh">🔄</button>
                </div>
            </div>
            <div class="search-container">
                <input type="text" class="search-box" id="searchBox" placeholder="Search files...">
            </div>
            <div class="file-tree" id="fileTree"></div>
        </div>

        <div class="content">
            <div class="content-header">
                <div class="stats-row">
                    <div class="stat-item">
                        <span class="stat-value" id="totalFiles">0</span>
                        <span class="stat-label">Total Files</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value" id="selectedCount">0</span>
                        <span class="stat-label">Selected</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value" id="totalFolders">0</span>
                        <span class="stat-label">Folders</span>
                    </div>
                </div>
                <div class="action-buttons">
                    <button class="btn btn-secondary" id="selectAllBtn">☑️ Select All</button>
                    <button class="btn btn-secondary" id="selectNoneBtn">⬜ Select None</button>
                    <button class="btn btn-secondary" id="selectByExtBtn">📋 By Extension</button>
                    <button class="btn btn-secondary" id="invertBtn">🔄 Invert</button>
                    <button class="btn btn-success" id="generateBtn">📄 Generate PDF</button>
                </div>
            </div>

            <div class="selected-panel">
                <div class="panel-title">Selected Files</div>
                <div class="selected-files-list" id="selectedFilesList">
                    <div class="empty-state">
                        <div class="empty-state-icon">📁</div>
                        <div>No files selected</div>
                        <div style="margin-top: 5px; font-size: 12px;">Select files from the explorer on the left</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="status-bar" id="statusBar">
        <span id="statusText">Ready</span>
        <span id="directoryPath"></span>
    </div>

    <div class="modal-overlay" id="successModal">
        <div class="modal">
            <div class="modal-icon">✅</div>
            <h2>PDF Generated Successfully!</h2>
            <p id="modalMessage">Your PDF is ready for download.</p>
            <div class="modal-buttons">
                <button class="btn btn-primary" id="downloadBtn">⬇️ Download PDF</button>
                <button class="btn btn-secondary" id="closeModalBtn">Close</button>
            </div>
        </div>
    </div>

    <script>
        (function() {
            var treeData = {{ tree_data | safe }};
            var baseDirectory = {{ directory_json | safe }};

            var fileIcons = {
                'py': '🐍', 'js': '📜', 'ts': '📘', 'html': '🌐', 'css': '🎨',
                'json': '📋', 'md': '📝', 'txt': '📄', 'xml': '📰', 'yaml': '⚙️',
                'yml': '⚙️', 'sh': '💻', 'bat': '💻', 'sql': '🗃️', 'csv': '📊',
                'java': '☕', 'rb': '💎', 'php': '🐘', 'go': '🔵', 'rs': '🦀',
                'c': '🔧', 'cpp': '🔧', 'h': '🔧', 'hpp': '🔧',
                'default': '📄'
            };

            function getFileIcon(filename) {
                var parts = filename.split('.');
                var ext = parts.length > 1 ? parts[parts.length - 1].toLowerCase() : '';
                return fileIcons[ext] || fileIcons['default'];
            }

            function escapeHtml(text) {
                var div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }

            function escapeAttr(text) {
                if (!text) return '';
                return String(text).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            }

            function renderTree() {
                var container = document.getElementById('fileTree');
                container.innerHTML = renderNode(treeData, 0);
                updateStats();
                attachTreeListeners();
            }

            function renderNode(node, depth) {
                var html = '';
                var i;

                if (node.type === 'folder') {
                    var indents = '';
                    for (i = 0; i < depth; i++) {
                        indents += '<span class="tree-indent"></span>';
                    }
                    var hasChildren = node.children && node.children.length > 0;

                    html += '<div class="tree-item folder" data-path="' + escapeAttr(node.path) + '" data-depth="' + depth + '">';
                    html += indents;
                    html += '<span class="tree-arrow ' + (hasChildren ? 'expanded' : 'no-arrow') + '">▶</span>';
                    html += '<input type="checkbox" class="tree-checkbox folder-checkbox" data-path="' + escapeAttr(node.path) + '">';
                    html += '<span class="tree-icon">📁</span>';
                    html += '<span class="tree-label">' + escapeHtml(node.name) + '</span>';
                    html += '<span class="tree-meta">' + (node.fileCount || 0) + ' files</span>';
                    html += '<div class="folder-actions">';
                    html += '<button class="folder-btn select-folder-btn" title="Select all">☑️</button>';
                    html += '<button class="folder-btn deselect-folder-btn" title="Deselect all">⬜</button>';
                    html += '</div>';
                    html += '</div>';

                    html += '<div class="folder-children" data-folder="' + escapeAttr(node.path) + '">';
                    if (node.children) {
                        var sorted = node.children.slice().sort(function(a, b) {
                            if (a.type === b.type) return a.name.localeCompare(b.name);
                            return a.type === 'folder' ? -1 : 1;
                        });
                        for (i = 0; i < sorted.length; i++) {
                            html += renderNode(sorted[i], depth + 1);
                        }
                    }
                    html += '</div>';
                } else {
                    var indents2 = '';
                    for (i = 0; i < depth; i++) {
                        indents2 += '<span class="tree-indent"></span>';
                    }

                    html += '<div class="tree-item file" data-path="' + escapeAttr(node.path) + '" data-depth="' + depth + '">';
                    html += indents2;
                    html += '<span class="tree-arrow no-arrow">▶</span>';
                    html += '<input type="checkbox" class="tree-checkbox file-checkbox" data-path="' + escapeAttr(node.path) + '">';
                    html += '<span class="tree-icon">' + getFileIcon(node.name) + '</span>';
                    html += '<span class="tree-label">' + escapeHtml(node.name) + '</span>';
                    html += '<span class="tree-meta">' + (node.size || '') + '</span>';
                    html += '</div>';
                }

                return html;
            }

            function attachTreeListeners() {
                var folderItems = document.querySelectorAll('.tree-item.folder');
                for (var i = 0; i < folderItems.length; i++) {
                    (function(item) {
                        item.addEventListener('click', function(e) {
                            if (e.target.classList.contains('tree-checkbox') ||
                                e.target.classList.contains('folder-btn')) {
                                return;
                            }
                            toggleFolder(item);
                        });
                    })(folderItems[i]);
                }

                var folderCheckboxes = document.querySelectorAll('.folder-checkbox');
                for (var j = 0; j < folderCheckboxes.length; j++) {
                    (function(cb) {
                        cb.addEventListener('click', function(e) {
                            e.stopPropagation();
                            toggleFolderCheck(cb);
                        });
                    })(folderCheckboxes[j]);
                }

                var fileCheckboxes = document.querySelectorAll('.file-checkbox');
                for (var k = 0; k < fileCheckboxes.length; k++) {
                    (function(cb) {
                        cb.addEventListener('change', function() {
                            updateSelectedList();
                            updateStats();
                        });
                    })(fileCheckboxes[k]);
                }

                var selectBtns = document.querySelectorAll('.select-folder-btn');
                for (var m = 0; m < selectBtns.length; m++) {
                    (function(btn) {
                        btn.addEventListener('click', function(e) {
                            e.stopPropagation();
                            selectFolderFiles(btn);
                        });
                    })(selectBtns[m]);
                }

                var deselectBtns = document.querySelectorAll('.deselect-folder-btn');
                for (var n = 0; n < deselectBtns.length; n++) {
                    (function(btn) {
                        btn.addEventListener('click', function(e) {
                            e.stopPropagation();
                            deselectFolderFiles(btn);
                        });
                    })(deselectBtns[n]);
                }
            }

            function toggleFolder(element) {
                var arrow = element.querySelector('.tree-arrow');
                var childrenContainer = element.nextElementSibling;

                if (childrenContainer && childrenContainer.classList.contains('folder-children')) {
                    var isCurrentlyExpanded = arrow.classList.contains('expanded');

                    if (isCurrentlyExpanded) {
                        arrow.classList.remove('expanded');
                        childrenContainer.classList.add('collapsed');

                        var nestedArrows = childrenContainer.querySelectorAll('.tree-arrow.expanded');
                        for (var i = 0; i < nestedArrows.length; i++) {
                            nestedArrows[i].classList.remove('expanded');
                        }
                        var nestedChildren = childrenContainer.querySelectorAll('.folder-children');
                        for (var j = 0; j < nestedChildren.length; j++) {
                            nestedChildren[j].classList.add('collapsed');
                        }
                    } else {
                        arrow.classList.add('expanded');
                        childrenContainer.classList.remove('collapsed');
                    }
                }
            }

            function toggleFolderCheck(checkbox) {
                var isChecked = checkbox.checked;
                var folderItem = checkbox.closest('.tree-item.folder');
                var childrenContainer = folderItem.nextElementSibling;

                if (childrenContainer && childrenContainer.classList.contains('folder-children')) {
                    var fileBoxes = childrenContainer.querySelectorAll('.file-checkbox');
                    for (var i = 0; i < fileBoxes.length; i++) {
                        fileBoxes[i].checked = isChecked;
                    }
                    var folderBoxes = childrenContainer.querySelectorAll('.folder-checkbox');
                    for (var j = 0; j < folderBoxes.length; j++) {
                        folderBoxes[j].checked = isChecked;
                    }
                }

                updateSelectedList();
                updateStats();
            }

            function selectFolderFiles(btn) {
                var folderItem = btn.closest('.tree-item');
                var childrenContainer = folderItem.nextElementSibling;

                if (childrenContainer && childrenContainer.classList.contains('folder-children')) {
                    var fileBoxes = childrenContainer.querySelectorAll('.file-checkbox');
                    for (var i = 0; i < fileBoxes.length; i++) {
                        fileBoxes[i].checked = true;
                    }
                    var folderBoxes = childrenContainer.querySelectorAll('.folder-checkbox');
                    for (var j = 0; j < folderBoxes.length; j++) {
                        folderBoxes[j].checked = true;
                    }
                }
                folderItem.querySelector('.folder-checkbox').checked = true;

                updateSelectedList();
                updateStats();
            }

            function deselectFolderFiles(btn) {
                var folderItem = btn.closest('.tree-item');
                var childrenContainer = folderItem.nextElementSibling;

                if (childrenContainer && childrenContainer.classList.contains('folder-children')) {
                    var fileBoxes = childrenContainer.querySelectorAll('.file-checkbox');
                    for (var i = 0; i < fileBoxes.length; i++) {
                        fileBoxes[i].checked = false;
                    }
                    var folderBoxes = childrenContainer.querySelectorAll('.folder-checkbox');
                    for (var j = 0; j < folderBoxes.length; j++) {
                        folderBoxes[j].checked = false;
                    }
                }
                folderItem.querySelector('.folder-checkbox').checked = false;

                updateSelectedList();
                updateStats();
            }

            function collapseAll() {
                var arrows = document.querySelectorAll('.tree-arrow.expanded');
                for (var i = 0; i < arrows.length; i++) {
                    arrows[i].classList.remove('expanded');
                }
                var children = document.querySelectorAll('.folder-children');
                for (var j = 0; j < children.length; j++) {
                    children[j].classList.add('collapsed');
                }
            }

            function expandAll() {
                var arrows = document.querySelectorAll('.tree-arrow');
                for (var i = 0; i < arrows.length; i++) {
                    if (!arrows[i].classList.contains('no-arrow')) {
                        arrows[i].classList.add('expanded');
                    }
                }
                var children = document.querySelectorAll('.folder-children');
                for (var j = 0; j < children.length; j++) {
                    children[j].classList.remove('collapsed');
                }
            }

            function selectAll() {
                var fileBoxes = document.querySelectorAll('.file-checkbox');
                for (var i = 0; i < fileBoxes.length; i++) {
                    if (!fileBoxes[i].closest('.tree-item').classList.contains('filtered-out')) {
                        fileBoxes[i].checked = true;
                    }
                }
                var folderBoxes = document.querySelectorAll('.folder-checkbox');
                for (var j = 0; j < folderBoxes.length; j++) {
                    folderBoxes[j].checked = true;
                }
                updateSelectedList();
                updateStats();
            }

            function selectNone() {
                var boxes = document.querySelectorAll('.tree-checkbox');
                for (var i = 0; i < boxes.length; i++) {
                    boxes[i].checked = false;
                }
                updateSelectedList();
                updateStats();
            }

            function invertSelection() {
                var fileBoxes = document.querySelectorAll('.file-checkbox');
                for (var i = 0; i < fileBoxes.length; i++) {
                    if (!fileBoxes[i].closest('.tree-item').classList.contains('filtered-out')) {
                        fileBoxes[i].checked = !fileBoxes[i].checked;
                    }
                }
                updateSelectedList();
                updateStats();
            }

            function selectByExtension() {
                var ext = prompt('Enter file extension (e.g., py, js, txt):');
                if (ext) {
                    var extList = ext.toLowerCase().split(',');
                    var extensions = [];
                    for (var i = 0; i < extList.length; i++) {
                        extensions.push(extList[i].trim());
                    }
                    var fileBoxes = document.querySelectorAll('.file-checkbox');
                    for (var j = 0; j < fileBoxes.length; j++) {
                        var path = fileBoxes[j].getAttribute('data-path') || '';
                        var parts = path.split('.');
                        var fileExt = parts.length > 1 ? parts[parts.length - 1].toLowerCase() : '';
                        for (var k = 0; k < extensions.length; k++) {
                            if (fileExt === extensions[k]) {
                                fileBoxes[j].checked = true;
                                break;
                            }
                        }
                    }
                    updateSelectedList();
                    updateStats();
                }
            }

            function filterTree() {
                var searchTerm = document.getElementById('searchBox').value.toLowerCase();

                var allItems = document.querySelectorAll('.tree-item');
                for (var i = 0; i < allItems.length; i++) {
                    allItems[i].classList.remove('filtered-out');
                }

                if (!searchTerm) {
                    return;
                }

                var fileItems = document.querySelectorAll('.tree-item.file');
                for (var j = 0; j < fileItems.length; j++) {
                    var labelEl = fileItems[j].querySelector('.tree-label');
                    var label = labelEl ? labelEl.textContent.toLowerCase() : '';
                    var path = (fileItems[j].getAttribute('data-path') || '').toLowerCase();
                    var matches = label.indexOf(searchTerm) !== -1 || path.indexOf(searchTerm) !== -1;
                    if (!matches) {
                        fileItems[j].classList.add('filtered-out');
                    }
                }

                var visibleFiles = document.querySelectorAll('.tree-item.file:not(.filtered-out)');
                for (var k = 0; k < visibleFiles.length; k++) {
                    var parent = visibleFiles[k].parentElement;
                    while (parent) {
                        if (parent.classList && parent.classList.contains('folder-children')) {
                            parent.classList.remove('collapsed');
                            var folderPath = parent.getAttribute('data-folder');
                            if (folderPath) {
                                var folderItems = document.querySelectorAll('.tree-item.folder');
                                for (var m = 0; m < folderItems.length; m++) {
                                    if (folderItems[m].getAttribute('data-path') === folderPath) {
                                        var arrow = folderItems[m].querySelector('.tree-arrow');
                                        if (arrow) arrow.classList.add('expanded');
                                    }
                                }
                            }
                        }
                        parent = parent.parentElement;
                    }
                }
            }

            function updateSelectedList() {
                var container = document.getElementById('selectedFilesList');
                var selectedFiles = [];
                var checkedBoxes = document.querySelectorAll('.file-checkbox:checked');
                for (var i = 0; i < checkedBoxes.length; i++) {
                    selectedFiles.push(checkedBoxes[i].getAttribute('data-path'));
                }

                if (selectedFiles.length === 0) {
                    container.innerHTML = '<div class="empty-state">' +
                        '<div class="empty-state-icon">📁</div>' +
                        '<div>No files selected</div>' +
                        '<div style="margin-top: 5px; font-size: 12px;">Select files from the explorer on the left</div>' +
                        '</div>';
                    return;
                }

                var html = '';

                for (var j = 0; j < selectedFiles.length; j++) {
                    var filePath = selectedFiles[j];
                    var parts = filePath.split(/[\/\\]/);
                    var filename = parts[parts.length - 1];
                    var relativePath = filePath;

                    var baseIdx = filePath.indexOf(baseDirectory);
                    if (baseIdx === 0) {
                        relativePath = filePath.substring(baseDirectory.length);
                        var firstChar = relativePath.charAt(0);
                        if (firstChar === '/' || firstChar === '\\') {
                            relativePath = relativePath.substring(1);
                        }
                    }

                    html += '<div class="selected-file-item">';
                    html += '<span class="file-icon">' + getFileIcon(filename) + '</span>';
                    html += '<span class="file-path" title="' + escapeAttr(filePath) + '">' + escapeHtml(relativePath) + '</span>';
                    html += '<button class="remove-btn" data-path="' + escapeAttr(filePath) + '">✕</button>';
                    html += '</div>';
                }

                container.innerHTML = html;

                var removeBtns = container.querySelectorAll('.remove-btn');
                for (var k = 0; k < removeBtns.length; k++) {
                    (function(btn) {
                        btn.addEventListener('click', function() {
                            deselectFile(btn.getAttribute('data-path'));
                        });
                    })(removeBtns[k]);
                }
            }

            function deselectFile(path) {
                var fileBoxes = document.querySelectorAll('.file-checkbox');
                for (var i = 0; i < fileBoxes.length; i++) {
                    if (fileBoxes[i].getAttribute('data-path') === path) {
                        fileBoxes[i].checked = false;
                    }
                }
                updateSelectedList();
                updateStats();
            }

            function updateStats() {
                var totalFiles = document.querySelectorAll('.file-checkbox').length;
                var selectedFiles = document.querySelectorAll('.file-checkbox:checked').length;
                var totalFolders = document.querySelectorAll('.folder-checkbox').length;

                document.getElementById('totalFiles').textContent = totalFiles;
                document.getElementById('selectedCount').textContent = selectedFiles;
                document.getElementById('totalFolders').textContent = totalFolders;
            }

            function setStatus(message, type) {
                var statusBar = document.getElementById('statusBar');
                var statusText = document.getElementById('statusText');
                statusBar.className = 'status-bar ' + (type || '');
                statusText.innerHTML = message;
            }

            function generatePDF() {
                var selectedFiles = [];
                var checkedBoxes = document.querySelectorAll('.file-checkbox:checked');
                for (var i = 0; i < checkedBoxes.length; i++) {
                    selectedFiles.push(checkedBoxes[i].getAttribute('data-path'));
                }

                if (selectedFiles.length === 0) {
                    setStatus('⚠️ Please select at least one file!', 'error');
                    return;
                }

                var btn = document.getElementById('generateBtn');
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner"></span> Generating...';
                setStatus('⏳ Generating PDF with ' + selectedFiles.length + ' files...', 'loading');

                fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ files: selectedFiles })
                })
                .then(function(response) { return response.json(); })
                .then(function(result) {
                    if (result.success) {
                        setStatus('✅ PDF generated successfully!', 'success');
                        document.getElementById('modalMessage').textContent =
                            'PDF created with ' + selectedFiles.length + ' files.';
                        document.getElementById('successModal').classList.add('show');
                    } else {
                        setStatus('❌ Error: ' + result.message, 'error');
                    }
                    btn.disabled = false;
                    btn.innerHTML = '📄 Generate PDF';
                })
                .catch(function(error) {
                    setStatus('❌ Error: ' + error.message, 'error');
                    btn.disabled = false;
                    btn.innerHTML = '📄 Generate PDF';
                });
            }

            function downloadPDF() {
                window.location.href = '/download';
                closeModal();
            }

            function closeModal() {
                document.getElementById('successModal').classList.remove('show');
            }

            // Initialize
            document.getElementById('directoryPath').textContent = baseDirectory;
            renderTree();
            expandAll();

            // Event listeners
            document.getElementById('collapseAllBtn').addEventListener('click', collapseAll);
            document.getElementById('expandAllBtn').addEventListener('click', expandAll);
            document.getElementById('refreshBtn').addEventListener('click', function() { location.reload(); });
            document.getElementById('searchBox').addEventListener('keyup', filterTree);
            document.getElementById('selectAllBtn').addEventListener('click', selectAll);
            document.getElementById('selectNoneBtn').addEventListener('click', selectNone);
            document.getElementById('selectByExtBtn').addEventListener('click', selectByExtension);
            document.getElementById('invertBtn').addEventListener('click', invertSelection);
            document.getElementById('generateBtn').addEventListener('click', generatePDF);
            document.getElementById('downloadBtn').addEventListener('click', downloadPDF);
            document.getElementById('closeModalBtn').addEventListener('click', closeModal);
        })();
    </script>
</body>
</html>
'''


def format_size(size_bytes):
    """Format file size to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return "{:.1f} {}".format(size_bytes, unit)
        size_bytes /= 1024
    return "{:.1f} TB".format(size_bytes)


def is_text_file(filepath):
    """Check if file is likely a text file."""
    text_extensions = {
        '.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.md',
        '.csv', '.log', '.ini', '.cfg', '.yaml', '.yml', '.sh', '.bat',
        '.c', '.cpp', '.h', '.hpp', '.java', '.rb', '.php', '.sql',
        '.r', '.go', '.rs', '.ts', '.jsx', '.tsx', '.vue', '.svelte',
        '.gitignore', '.env', '.htaccess', '.conf', '.toml', '.rst'
    }

    ext = Path(filepath).suffix.lower()
    name = Path(filepath).name.lower()

    if ext in text_extensions:
        return True

    if name in {'makefile', 'dockerfile', 'jenkinsfile', 'vagrantfile', 'rakefile', 'gemfile', 'procfile'}:
        return True

    mime_type, _ = mimetypes.guess_type(filepath)
    if mime_type and mime_type.startswith('text/'):
        return True

    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(1024)
            if b'\x00' in chunk:
                return False
            try:
                chunk.decode('utf-8')
                return True
            except UnicodeDecodeError:
                return False
    except:
        return False


def read_file_content(filepath):
    """Read file content with various encoding fallbacks."""
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'ascii']

    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding, errors='replace') as f:
                return f.read()
        except Exception:
            continue

    try:
        with open(filepath, 'rb') as f:
            content = f.read()
            return content.decode('utf-8', errors='replace')
    except Exception as e:
        return "[Error reading file: {}]".format(e)


def build_tree(directory):
    """Build tree structure from directory (recursive)."""

    def process_dir(path):
        name = os.path.basename(path) or path
        node = {
            'type': 'folder',
            'name': name,
            'path': path,
            'children': [],
            'fileCount': 0
        }

        try:
            items = sorted(os.listdir(path))
        except PermissionError:
            return node

        for item in items:
            item_path = os.path.join(path, item)

            try:
                if os.path.isdir(item_path):
                    if item.startswith('.') or item in {'node_modules', '__pycache__', 'venv', '.git', '.svn', 'dist', 'build'}:
                        continue

                    child_node = process_dir(item_path)
                    if child_node['fileCount'] > 0 or child_node['children']:
                        node['children'].append(child_node)
                        node['fileCount'] += child_node['fileCount']

                elif os.path.isfile(item_path):
                    try:
                        size = os.path.getsize(item_path)

                        if size > 10 * 1024 * 1024:
                            continue

                        if is_text_file(item_path):
                            node['children'].append({
                                'type': 'file',
                                'name': item,
                                'path': item_path,
                                'size': format_size(size)
                            })
                            node['fileCount'] += 1
                    except Exception:
                        continue
            except Exception:
                continue

        return node

    return process_dir(directory)


def create_pdf_content(files):
    """Create HTML content for PDF generation with SMALLEST possible font."""
    html_parts = ['''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {
            size: A4;
            margin: 1mm;
        }
        body {
            font-family: 'Courier New', Courier, monospace;
            font-size: 1pt;
            line-height: 1.0;
            color: #000;
            word-wrap: break-word;
            white-space: pre-wrap;
            margin: 0;
            padding: 0;
        }
        .file-section {
            margin-bottom: 0.5pt;
        }
        .file-header {
            font-weight: bold;
            font-size: 1.2pt;
            border-bottom: 0.1pt solid #000;
            margin-bottom: 0.2pt;
            padding: 0.1pt;
            background: #eee;
        }
        .file-content {
            font-size: 1pt;
            line-height: 1.0;
        }
        .separator {
            border-top: 0.1pt dashed #666;
            margin: 0.3pt 0;
        }
    </style>
</head>
<body>
''']

    for i, filepath in enumerate(files):
        rel_path = filepath
        if selected_directory:
            rel_path = os.path.relpath(filepath, selected_directory)

        content = read_file_content(filepath)
        escaped_content = html.escape(content)
        escaped_path = html.escape(rel_path)

        html_parts.append('<div class="file-section">')
        html_parts.append('<div class="file-header">=== {} ===</div>'.format(escaped_path))
        html_parts.append('<div class="file-content">{}</div>'.format(escaped_content))
        html_parts.append('</div>')

        if i < len(files) - 1:
            html_parts.append('<div class="separator"></div>')

    html_parts.append('</body></html>')
    return ''.join(html_parts)


@app.route('/')
def index():
    """Main page with file selection UI."""
    tree_data = build_tree(selected_directory)
    return render_template_string(
        HTML_TEMPLATE,
        directory=selected_directory,
        tree_data=json.dumps(tree_data),
        directory_json=json.dumps(selected_directory)
    )


@app.route('/generate', methods=['POST'])
def generate():
    """Generate PDF from selected files."""
    global generated_pdf_path

    try:
        data = request.get_json()
        files = data.get('files', [])

        if not files:
            return jsonify({'success': False, 'message': 'No files selected'})

        valid_files = [f for f in files if os.path.isfile(f)]

        if not valid_files:
            return jsonify({'success': False, 'message': 'No valid files found'})

        html_content = create_pdf_content(valid_files)

        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_pdf.close()

        css = CSS(string='''
            @page { size: A4; margin: 1mm; }
            body { font-size: 1pt !important; line-height: 1.0 !important; }
            .file-content { font-size: 1pt !important; }
            .file-header { font-size: 1.2pt !important; }
        ''')

        HTML(string=html_content).write_pdf(temp_pdf.name, stylesheets=[css])

        generated_pdf_path = temp_pdf.name

        return jsonify({
            'success': True,
            'message': 'PDF generated with {} files!'.format(len(valid_files))
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})


@app.route('/download')
def download():
    """Download the generated PDF."""
    global generated_pdf_path

    if generated_pdf_path and os.path.exists(generated_pdf_path):
        return send_file(
            generated_pdf_path,
            as_attachment=True,
            download_name='generated_output.pdf',
            mimetype='application/pdf'
        )

    return "No PDF generated yet", 404


def open_browser(port):
    """Open browser after short delay."""
    import time
    time.sleep(1)
    webbrowser.open('http://127.0.0.1:{}'.format(port))


def select_directory():
    """Open directory selection dialog."""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    directory = filedialog.askdirectory(
        title='Select Directory with Files to Convert'
    )

    root.destroy()
    return directory


def main():
    """Main entry point."""
    global selected_directory

    print("=" * 60)
    print("   PDF Generator - VS Code-like File Explorer")
    print("=" * 60)
    print()

    print("Opening directory selection dialog...")
    selected_directory = select_directory()

    if not selected_directory:
        print("No directory selected. Exiting.")
        sys.exit(1)

    print("Selected directory: {}".format(selected_directory))
    print()

    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()

    print("Starting web server on http://127.0.0.1:{}".format(port))
    print("Opening browser...")
    print()
    print("Press Ctrl+C to stop the server")
    print()

    threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    try:
        app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == '__main__':
    main()
