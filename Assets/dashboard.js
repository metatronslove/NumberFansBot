import {
	python
} from "https://cdn.jsdelivr.net/npm/@codemirror/lang-python@6.1.3/dist/index.min.js";
import {
	html
} from "https://cdn.jsdelivr.net/npm/@codemirror/lang-html@6.4.5/dist/index.min.js";
import {
	javascript
} from "https://cdn.jsdelivr.net/npm/@codemirror/lang-javascript@6.2.1/dist/index.min.js";
import {
	css
} from "https://cdn.jsdelivr.net/npm/@codemirror/lang-css@6.2.1/dist/index.min.js";
import {
	yaml
} from "https://cdn.jsdelivr.net/npm/@codemirror/lang-yaml@6.0.0/dist/index.min.js";
import {
	sql
} from "https://cdn.jsdelivr.net/npm/@codemirror/lang-sql@6.5.2/dist/index.min.js";
import {
	EditorView,
	basicSetup
} from "https://cdn.jsdelivr.net/npm/codemirror@6.0.1/dist/index.min.js";
import {
	dracula
} from "https://cdn.jsdelivr.net/npm/@codemirror/theme-dracula@0.21.0/dist/index.min.js";
particlesJS('particles-js', {
	"particles": {
		"number": {
			"value": 80,
			"density": {
				"enable": true,
				"value_area": 800
			}
		},
		"color": {
			"value": "#ffffff"
		},
		"shape": {
			"type": "circle"
		},
		"opacity": {
			"value": 0.5,
			"random": true,
			"anim": {
				"enable": true,
				"speed": 1,
				"opacity_min": 0.1,
				"sync": false
			}
		},
		"size": {
			"value": 3,
			"random": true,
			"anim": {
				"enable": true,
				"speed": 2,
				"size_min": 0.1,
				"sync": false
			}
		},
		"line_linked": {
			"enable": true,
			"distance": 150,
			"color": "#ffffff",
			"opacity": 0.4,
			"width": 1
		},
		"move": {
			"enable": true,
			"speed": 2,
			"direction": "none",
			"random": true,
			"straight": false,
			"out_mode": "out",
			"bounce": false,
			"attract": {
				"enable": true,
				"rotateX": 600,
				"rotateY": 1200
			}
		}
	},
	"interactivity": {
		"detect_on": "canvas",
		"events": {
			"onhover": {
				"enable": true,
				"mode": "grab"
			},
			"onclick": {
				"enable": true,
				"mode": "push"
			},
			"resize": true
		},
		"modes": {
			"grab": {
				"distance": 140,
				"line_linked": {
					"opacity": 1
				}
			},
			"push": {
				"particles_nb": 4
			}
		}
	},
	"retina_detect": true
});
document.querySelectorAll('.tab').forEach(tab => {
	tab.addEventListener('click', () => {
		document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
		document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
		tab.classList.add('active');
		document.getElementById(tab.dataset.tab).classList.add('active');
	});
});
document.querySelectorAll('.promote-credits-form').forEach(form => {
	form.style.display = 'flex';
	form.style.gap = '10px';
	form.querySelector('input[type="number"]').style.width = '65%';
	form.querySelector('input[type="number"]').style.backgroundColor = '#2a2a2a';
	form.querySelector('input[type="number"]').style.color = '#fff';
	form.querySelector('input[type="number"]').style.border = '1px solid #48ff00';
	form.querySelector('button').style.width = '33%';
	form.querySelector('button').style.padding = '5px 10px';
});
document.querySelectorAll('.toggle-blacklist-form, .toggle-beta-tester-form').forEach(form => {
	form.style.display = 'inline-block';
	form.querySelector('button').style.padding = '5px 10px';
});
{
	%
	if github_info.url %
}
let allRepos = [];
let currentPage = 1;
let reposPerPage = 25;
const githubInfo = {
	baseUrl: '{{ github_info.url }}',
	username: '{{ github_info.username }}',
	repo: '{{ github_info.repo }}'
};

function githubMarkdownToHtml(markdown) {
	const container = document.createElement('div');
	marked.setOptions({
		gfm: true,
		breaks: true,
		tables: true,
		pedantic: false,
		sanitize: false,
		smartLists: true,
		smartypants: false,
		highlight: function(code, lang) {
			if (typeof hljs !== 'undefined' && lang) {
				try {
					return hljs.highlight(code, {
						language: lang
					}).value;
				} catch (e) {
					console.warn(`Error highlighting ${lang} code:`, e);
				}
			}
			return code;
		}
	});
	container.innerHTML = marked.parse(markdown);
	postProcessHtml(container);
	return container.innerHTML;
}

function postProcessHtml(container) {
	container.querySelectorAll('pre').forEach(pre => {
		pre.classList.add('github-markdown-pre');
		const code = pre.querySelector('code');
		if (code) code.classList.add('github-markdown-code');
	});
	container.querySelectorAll('table').forEach(table => {
		table.classList.add('github-markdown-table');
	});
	container.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(header => {
		const id = header.textContent.toLowerCase().replace(/[^\w\u4e00-\u9fa5]+/g, '-').replace(/^-+|-+$/g, '');
		header.id = id;
		const anchor = document.createElement('a');
		anchor.className = 'github-markdown-header-anchor';
		anchor.href = `#${id}`;
		anchor.innerHTML = '<svg aria-hidden="true" height="16" viewBox="0 0 16 16" width="16"><path fill-rule="evenodd" d="M4 9h1v1H4c-1.5 0-3-1.69-3-3.5S2.55 3 4 3h4c1.45 0 3 1.69 3 3.5 0 1.41-.91 2.72-2 3.25V8.59c.58-.45 1-1.27 1-2.09C10 5.22 8.98 4 8 4H4c-.98 0-2 1.22-2 2.5S3 9 4 9zm9-3h-1v1h1c1 0 2 1.22 2 2.5S13.98 12 13 12H9c-.98 0-2-1.22-2-2.5 0-.83.42-1.64 1-2.09V6.25c-1.09.53-2 1.84-2 3.25C6 11.31 7.55 13 9 13h4c1.45 0 3-1.69 3-3.5S14.5 6 13 6z"></path></svg>';
		header.prepend(anchor);
	});
}

function ToggleReadMe(repoName, fullName) {
	const readmeContainer = document.getElementById(`readme-${repoName}`);
	if (readmeContainer.style.display === 'none') {
		readmeContainer.style.display = 'block';
	} else {
		readmeContainer.style.display = 'none';
	}
}
async function fetchAndDisplayReadme(repoName, fullName) {
	const readmeContainer = document.getElementById(`readme-${repoName}`);
	try {
		const response = await fetch(`https://raw.githubusercontent.com/${fullName}/main/README.md`);
		if (!response.ok) {
			throw new Error(`Failed to fetch README: ${response.status}`);
		}
		let markdown = await response.text();
		markdown = convertRelativeUrls(markdown, fullName);
		const html = githubMarkdownToHtml(markdown);
		const modalHTML = `
                    <div class="readme-modal-overlay" onclick="ToggleReadMe('${repoName}')">
                        <div class="readme-modal-content" onclick="event.stopPropagation()">
                            <div class="readme-modal-body">${html}</div>
                        </div>
                    </div>
                `;
		readmeContainer.innerHTML = modalHTML;
		readmeContainer.style.display = 'none';
		processImagesAndLinks(readmeContainer, fullName);
		if (typeof hljs !== 'undefined') {
			document.querySelectorAll('.readme-modal-body pre code').forEach(block => {
				hljs.highlightElement(block);
			});
		}
	} catch (error) {
		readmeContainer.innerHTML = `
                    <div class="readme-modal-overlay" onclick="ToggleReadMe('${repoName}')">
                        <div class="readme-modal-content" onclick="event.stopPropagation()">
                            <div class="readme-modal-body">
                                <p>{{ i18n.t('README_ERROR', lang) }} ${repoName}</p>
                                <p>${error.message}</p>
                            </div>
                        </div>
                    </div>
                `;
		readmeContainer.style.display = 'none';
	}
}

function convertRelativeUrls(markdown, fullName) {
	markdown = markdown.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, altText, path) => {
		if (!path.startsWith('http') && !path.startsWith('data:')) {
			if (path.startsWith('/')) {
				path = `https://raw.githubusercontent.com/${fullName}/main${path}`;
			} else {
				path = `https://raw.githubusercontent.com/${fullName}/main/${path}`;
			}
		}
		return `![${altText}](${path})`;
	});
	markdown = markdown.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, text, path) => {
		if (!path.startsWith('http') && !path.startsWith('#') && !path.startsWith('mailto:')) {
			if (path.startsWith('/')) {
				path = `https://github.com/${fullName}/blob/main${path}`;
			} else {
				path = `https://github.com/${fullName}/blob/main/${path}`;
			}
		}
		return `[${text}](${path})`;
	});
	return markdown;
}

function processImagesAndLinks(container, fullName) {
	container.querySelectorAll('img').forEach(img => {
		const src = img.getAttribute('src');
		if (src && !src.startsWith('http') && !src.startsWith('data:')) {
			const absoluteSrc = src.startsWith('/') ? `https://raw.githubusercontent.com/${fullName}/main${src}` : `https://raw.githubusercontent.com/${fullName}/main/${src}`;
			img.setAttribute('src', absoluteSrc);
		}
	});
	container.querySelectorAll('a').forEach(a => {
		const href = a.getAttribute('href');
		if (href && !href.startsWith('http') && !href.startsWith('#') && !href.startsWith('mailto:')) {
			const absoluteHref = href.startsWith('/') ? `https://github.com/${fullName}/blob/main${href}` : `https://github.com/${fullName}/blob/main/${href}`;
			a.setAttribute('href', absoluteHref);
			a.setAttribute('target', '_blank');
		}
	});
}

function getBasePath() {
	return githubInfo.baseUrl.endsWith('/') ? githubInfo.baseUrl : githubInfo.baseUrl + '/';
}
async function fetchTrafficData(repoName) {
	try {
		const basePath = getBasePath();
		const [viewsRes, clonesRes] = await Promise.all([
			fetch(`${basePath}data/repos/${encodeURIComponent(repoName)}/views.json`),
			fetch(`${basePath}data/repos/${encodeURIComponent(repoName)}/clones.json`)
		]);
		if (!viewsRes.ok) {
			console.warn(`Views data not found for ${repoName}`);
			return {
				views: {
					views: []
				}
			};
		}
		if (!clonesRes.ok) {
			console.warn(`Clones data not found for ${repoName}`);
			return {
				clones: {
					clones: []
				}
			};
		}
		const views = await viewsRes.json();
		const clones = await clonesRes.json();
		const trafficData = {
			views: views || {
				views: []
			},
			clones: clones || {
				clones: []
			}
		};
		if (!validateTrafficData(trafficData)) {
			throw new Error('Invalid data structure');
		}
		return trafficData;
	} catch (error) {
		console.error(`Error loading traffic data for ${repoName}:`, error);
		return {
			views: {
				views: []
			},
			clones: {
				clones: []
			}
		};
	}
}
async function fetchAllRepos() {
	try {
		const basePath = getBasePath();
		const response = await fetch(`${basePath}data/repo-info.json`);
		let data;
		if (!response.ok) {
			const fallbackUrl = `https://raw.githubusercontent.com/${githubInfo.username}/${githubInfo.repo}/main/data/repo-info.json`;
			const fallbackResponse = await fetch(fallbackUrl);
			if (!fallbackResponse.ok) {
				throw new Error('Repository list not found');
			}
			data = await fallbackResponse.json();
		} else {
			data = await response.json();
		}
		return Array.isArray(data) ? {
			repositories: data
		} : data;
	} catch (error) {
		console.error('Error loading repositories:', error);
		showInfoBox();
		return {
			repositories: []
		};
	}
}

function validateTrafficData(data) {
	if (!data) return false;
	if (data.views && !Array.isArray(data.views.views)) return false;
	if (data.clones && !Array.isArray(data.clones.clones)) return false;
	return true;
}

function formatDate(isoString) {
	const date = new Date(isoString);
	return date.toLocaleDateString('{{ lang }}', {
		year: 'numeric',
		month: 'short',
		day: 'numeric'
	});
}

function fillMissingDates(data, range) {
	if (data.length === 0) return data;
	const dateMap = new Map();
	data.forEach(item => dateMap.set(item.timestamp.split('T')[0], item));
	const sortedDates = [...dateMap.keys()].sort();
	const startDate = new Date(sortedDates[0]);
	const endDate = new Date(sortedDates[sortedDates.length - 1]);
	for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
		const dateStr = d.toISOString().split('T')[0];
		if (!dateMap.has(dateStr)) {
			dateMap.set(dateStr, {
				timestamp: dateStr,
				count: 0,
				uniques: 0
			});
		}
	}
	return [...dateMap.values()].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
}

function createChart(canvasId, label, data, labels, total) {
	const ctx = document.getElementById(canvasId);
	if (!ctx) return;
	if (data.length === 0) {
		ctx.parentElement.innerHTML = `<p>{{ i18n.t('NO_DATA', lang) }}</p>`;
		return;
	}
	return new Chart(ctx, {
		type: 'line',
		data: {
			labels: labels,
			datasets: [{
				label: `${label} ({{ i18n.t('TOTAL', lang) }}: ${total || 0})`,
				data: data,
				borderColor: '#48ff00',
				backgroundColor: 'rgba(72, 255, 0, 0.2)',
				borderWidth: 2,
				tension: 0.3,
				fill: true
			}]
		},
		options: {
			responsive: true,
			maintainAspectRatio: false,
			plugins: {
				legend: {
					display: true,
					position: 'top',
					labels: {
						color: '#fff'
					}
				}
			},
			scales: {
				y: {
					beginAtZero: true,
					ticks: {
						color: '#fff'
					},
					grid: {
						color: 'rgba(255, 255, 255, 0.2)'
					}
				},
				x: {
					ticks: {
						color: '#fff',
						maxRotation: 45,
						minRotation: 45
					},
					grid: {
						color: 'rgba(255, 255, 255, 0.1)'
					}
				}
			}
		}
	});
}

function showError(message) {
	const container = document.getElementById('charts-container');
	container.innerHTML = `<div class="error">${message}</div>`;
}

function showInfoBox() {
	document.getElementById('info-container').innerHTML = `<div class="info-box">{{ i18n.t('INFO_BOX', lang) }}</div>`;
}

function setupPagination(totalRepos, reposPerPage) {
	const totalPages = Math.ceil(totalRepos / reposPerPage);
	const paginationDiv = document.getElementById('pagination');
	paginationDiv.innerHTML = '';
	if (totalPages <= 1) return;
	const prevButton = document.createElement('button');
	prevButton.innerHTML = '{{ i18n.t('
	PREVIOUS_PAGE ', lang) }}';
	prevButton.disabled = currentPage === 1;
	prevButton.addEventListener('click', () => {
		if (currentPage > 1) {
			currentPage -= 1;
			displayRepos();
		}
	});
	paginationDiv.appendChild(prevButton);
	const maxVisiblePages = 5;
	let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
	let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
	if (endPage - startPage + 1 < maxVisiblePages) {
		startPage = Math.max(1, endPage - maxVisiblePages + 1);
	}
	for (let i = startPage; i <= endPage; i++) {
		const pageButton = document.createElement('button');
		pageButton.textContent = i;
		if (i === currentPage) pageButton.classList.add('active');
		pageButton.addEventListener('click', () => {
			currentPage = i;
			displayRepos();
		});
		paginationDiv.appendChild(pageButton);
	}
	const nextButton = document.createElement('button');
	nextButton.innerHTML = '{{ i18n.t('
	NEXT_PAGE ', lang) }}';
	nextButton.disabled = currentPage === totalPages;
	nextButton.addEventListener('click', () => {
		if (currentPage < totalPages) {
			currentPage += 1;
			displayRepos();
		}
	});
	paginationDiv.appendChild(nextButton);
	paginationDiv.style.display = 'flex';
}

function filterDataByDateRange(data, range) {
	if (range === 'all') return data;
	const days = parseInt(range) || 30;
	const cutoffDate = new Date();
	cutoffDate.setDate(cutoffDate.getDate() - days);
	return data.filter(item => new Date(item.timestamp) >= cutoffDate);
}
async function displayRepos() {
	if (!allRepos || !allRepos.repositories) {
		showError('{{ i18n.t('
			ERROR_LOADING_REPOS ', lang) }}');
		return;
	}
	const selectedRange = document.getElementById('time-range').value;
	const startIdx = (currentPage - 1) * reposPerPage;
	const endIdx = startIdx + reposPerPage;
	const reposToShow = allRepos.repositories.slice(startIdx, endIdx);
	const totalPages = Math.ceil(allRepos.repositories.length / reposPerPage);
	document.getElementById('charts-container').innerHTML = '';
	document.getElementById('loading').textContent = '{{ i18n.t('
	LOADING_REPOS ', lang) }}'.replace('(0)', `(${reposToShow.length})`);
	document.querySelector('.per-page-selector').style.display = 'block';
	document.querySelector('.time-range-selector').style.display = 'block';
	document.querySelector('.info-box').style.display = 'none';
	let loadedCount = 0;
	for (const repo of reposToShow) {
		document.getElementById('loading').textContent = '{{ i18n.t('
		LOADING_REPOS ', lang) }}'.replace('%d', ++loadedCount);
		const trafficData = await fetchTrafficData(repo.name);
		const filteredViews = filterDataByDateRange(trafficData.views.views, selectedRange);
		const filteredClones = filterDataByDateRange(trafficData.clones.clones, selectedRange);
		const completeViews = fillMissingDates(filteredViews, selectedRange);
		const completeClones = fillMissingDates(filteredClones, selectedRange);
		const container = document.createElement('div');
		container.className = 'chart-box';
		const escapedRepoName = repo.name.replace(/&/g, '&').replace(/</g, '<').replace(/>/g, '>').replace(/"/g, '"').replace(/'/g, '');
		container.innerHTML = `
                    <h3>
                        <a href="https://github.com/${repo.full_name}" target="_blank">🔗 {{ i18n.t('REPO_HEADER', lang) }}.</a> |
                        <a href="https://github.com/${repo.full_name}/zipball/main" target="_top">zip⬇</a> |
                        <a href="https://github.com/${repo.full_name}/tarball/main" target="_top">tar⬇</a> |
                        <a href="https://github.com/${repo.full_name}/fork" target="_blank">fork🖈</a> |
                        <a onclick="ToggleReadMe('${escapedRepoName}', '${repo.full_name}')" id="toggle-${escapedRepoName}">README.md+</a>
                    </h3>
                    <div id="readme-${escapedRepoName}" style="display:none;"></div>
                    <div class="stats-summary">
                        <div class="stat-item">
                            <span class="stat-label">{{ i18n.t('VIEWS', lang) }}:</span>
                            <span class="stat-value">${trafficData.views.count || 0}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">{{ i18n.t('CLONES', lang) }}:</span>
                            <span class="stat-value">${trafficData.clones.count || 0}</span>
                        </div>
                    </div>
                    <div class="chart-row">
                        <div class="chart-container">
                            <canvas id="views-${escapedRepoName}"></canvas>
                        </div>
                        <div class="chart-container">
                            <canvas id="clones-${escapedRepoName}"></canvas>
                        </div>
                    </div>
                `.replace('%s', escapedRepoName);
		document.getElementById('charts-container').appendChild(container);
		fetchAndDisplayReadme(repo.name, repo.full_name);
		createChart(`views-${escapedRepoName}`, '{{ i18n.t('
			VIEWS ', lang) }}', completeViews.map(v => v.count), completeViews.map(v => formatDate(v.timestamp)), trafficData.views.count);
		createChart(`clones-${escapedRepoName}`, '{{ i18n.t('
			CLONES ', lang) }}', completeClones.map(c => c.count), completeClones.map(c => formatDate(c.timestamp)), trafficData.clones.count);
	}
	document.getElementById('pagination').style.display = 'flex';
	document.getElementById('loading').textContent = '{{ i18n.t('
	PAGE_STATS ', lang) }}'.replace('%d', currentPage).replace('%d', totalPages).replace('%d', allRepos.repositories.length);
	setupPagination(allRepos.repositories.length, reposPerPage);
}
// File Tree and Editor
let editor = null;
let currentFilePath = null;

function renderFileTree(files, parentElement) {
	const ul = document.createElement('ul');
	files.forEach(item => {
		const li = document.createElement('li');
		li.className = item.type;
		const a = document.createElement('a');
		a.textContent = item.name;
		if (item.type === 'directory') {
			a.href = '#';
			a.addEventListener('click', (e) => {
				e.preventDefault();
				const children = li.querySelector('ul');
				children.style.display = children.style.display === 'none' ? 'block' : 'none';
			});
			li.appendChild(a);
			const childrenUl = document.createElement('ul');
			childrenUl.style.display = 'none';
			renderFileTree(item.children, childrenUl);
			li.appendChild(childrenUl);
		} else {
			a.href = '#';
			a.addEventListener('click', (e) => {
				e.preventDefault();
				loadFile(item.path);
			});
			li.appendChild(a);
		}
		ul.appendChild(li);
	});
	parentElement.appendChild(ul);
}

function loadFile(path) {
	fetch(`/{{ lang }}/files/read`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			path
		})
	}).then(response => response.json()).then(data => {
		if (data.error) {
			alert(data.error);
			return;
		}
		currentFilePath = path;
		document.getElementById('editor-title').textContent = `Editing: ${path}`;
		document.getElementById('editor-container').style.display = 'block';
		if (!editor) {
			editor = CodeMirror.fromTextArea(document.getElementById('editor'), {
				lineNumbers: true,
				theme: 'dracula',
				mode: data.mode || 'python'
			});
		} else {
			editor.setOption('mode', data.mode || 'python');
		}
		editor.setValue(data.content);
	}).catch(error => {
		console.error('Error loading file:', error);
		alert('Failed to load file');
	});
}

function saveFile() {
	if (!currentFilePath) {
		alert('No file selected');
		return;
	}
	fetch(`/{{ lang }}/files/save`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			path: currentFilePath,
			content: editor.getValue()
		})
	}).then(response => response.json()).then(data => {
		if (data.error) {
			alert(data.error);
		} else {
			alert(data.message);
		}
	}).catch(error => {
		console.error('Error saving file:', error);
		alert('Failed to save file');
	});
}

function deleteFile() {
	if (!currentFilePath) {
		alert('No file selected');
		return;
	}
	if (!confirm(`Are you sure you want to delete ${currentFilePath}?`)) {
		return;
	}
	fetch(`/{{ lang }}/files/delete`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			path: currentFilePath
		})
	}).then(response => response.json()).then(data => {
		if (data.error) {
			alert(data.error);
		} else {
			alert(data.message);
			document.getElementById('editor-container').style.display = 'none';
			currentFilePath = null;
			editor.setValue('');
			loadFileTree();
		}
	}).catch(error => {
		console.error('Error deleting file:', error);
		alert('Failed to delete file');
	});
}
document.getElementById('create-file-form').addEventListener('submit', (e) => {
	e.preventDefault();
	const path = document.getElementById('new-file-path').value;
	fetch(`/{{ lang }}/files/create`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			path
		})
	}).then(response => response.json()).then(data => {
		if (data.error) {
			alert(data.error);
		} else {
			alert(data.message);
			document.getElementById('new-file-path').value = '';
			loadFileTree();
		}
	}).catch(error => {
		console.error('Error creating file:', error);
		alert('Failed to create file');
	});
});
document.getElementById('save-file').addEventListener('click', saveFile);
document.getElementById('delete-file').addEventListener('click', deleteFile);

function loadFileTree() {
	fetch(`/{{ lang }}/files/list`).then(response => response.json()).then(data => {
		if (data.error) {
			alert(data.error);
			return;
		}
		const fileTree = document.getElementById('file-tree');
		fileTree.innerHTML = '';
		renderFileTree(data.files, fileTree);
	}).catch(error => {
		console.error('Error loading file tree:', error);
		alert('Failed to load file tree');
	});
}
async function main() {
	showInfoBox();
	allRepos = await fetchAllRepos();
	if (!allRepos.repositories || allRepos.repositories.length === 0) {
		showInfoBox();
		return;
	}
	displayRepos();
	{
		%
		if command_usage %
	}
	const commandUsage = {
		{
			command_usage | tojson
		}
	};
	if (commandUsage && commandUsage.length > 0) {
		const ctx = document.createElement('canvas');
		ctx.id = 'command-usage-chart';
		ctx.style.width = '100%';
		ctx.style.height = '400px';
		document.querySelector('#commands').insertBefore(ctx, document.querySelector('#commands-table'));
		const labels = commandUsage.map(usage => `/${usage.command}`);
		const percentages = commandUsage.map(usage => usage.percentage);
		new Chart(ctx, {
			type: 'bar',
			data: {
				labels: labels,
				datasets: [{
					label: '{{ i18n.t('
					COMMAND_USAGE_PERCENTAGE ', lang) }}',
					data: percentages,
					backgroundColor: 'rgba(72, 255, 0, 0.6)',
					borderColor: '#48ff00',
					borderWidth: 1
				}]
			},
			options: {
				responsive: true,
				plugins: {
					legend: {
						display: true,
						position: 'top',
						labels: {
							color: '#fff'
						}
					},
					title: {
						display: true,
						text: '{{ i18n.t('
						COMMAND_USAGE_CHART ', lang) }}',
						color: '#fff'
					}
				},
				scales: {
					y: {
						beginAtZero: true,
						max: 100,
						ticks: {
							color: '#fff',
							callback: value => value + '%'
						},
						grid: {
							color: 'rgba(255, 255, 255, 0.2)'
						}
					},
					x: {
						ticks: {
							color: '#fff'
						},
						grid: {
							color: 'rgba(255, 255, 255, 0.1)'
						}
					}
				}
			}
		});
	} {
		% endif %
	}
	loadFileTree();
}
document.addEventListener('DOMContentLoaded', function() {
	document.getElementById('per-page').addEventListener('change', (e) => {
		reposPerPage = parseInt(e.target.value) || 25;
		currentPage = 1;
		displayRepos();
	});
	document.getElementById('time-range').addEventListener('change', displayRepos);
	main();
});
{
	% endif %
}
(function() {
	function c() {
		var b = a.contentDocument || a.contentWindow.document;
		if (b) {
			var d = b.createElement('script');
			d.innerHTML = "window.__CF$cv$params={r:'93baf7ddafcb53ee',t:'MTc0NjU2MDYyNC4wMDAwMDA='};var a=document.createElement('script');a.nonce='';a.src='/cdn-cgi/challenge-platform/scripts/jsd/main.js';document.getElementsByTagName('head')[0].appendChild(a);";
			b.getElementsByTagName('head')[0].appendChild(d)
		}
	}
	if (document.body) {
		var a = document.createElement('iframe');
		a.height = 1;
		a.width = 1;
		a.style.position = 'absolute';
		a.style.top = 0;
		a.style.left = 0;
		a.style.border = 'none';
		a.style.visibility = 'hidden';
		document.body.appendChild(a);
		if ('loading' !== document.readyState) c();
		else if (window.addEventListener) document.addEventListener('DOMContentLoaded', c);
		else {
			var e = document.onreadystatechange || function() {};
			document.onreadystatechange = function(b) {
				e(b);
				'loading' !== document.readyState && (document.onreadystatechange = e, c())
			}
		}
	}
})();