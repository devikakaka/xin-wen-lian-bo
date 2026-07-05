import fetch from './fetch.js';
import jsdom from 'jsdom';
const { JSDOM } = jsdom;
import fs from 'fs';
import path from 'path';

import { fileURLToPath } from "url";
// const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * 得到当前日期
 * @returns 当前日期, 格式如: 20220929
 */
const getDate = () => {
	const envDate = process.env.NEWS_DATE?.trim();
	if (envDate) {
		if (!/^\d{8}$/.test(envDate)) {
			throw new Error('NEWS_DATE 必须为 YYYYMMDD 格式');
		}
		return envDate;
	}
	const add0 = num => num < 10 ? ('0' + num) : num;
	const date = new Date();
	return '' + date.getFullYear() + add0(date.getMonth() + 1) + add0(date.getDate());
}
// 当前日期
const DATE = getDate();
// /news 目录
const NEWS_PATH = path.join(__dirname, 'news');
// /news/xxxxxxxx.md 文件
const NEWS_MD_PATH = path.join(NEWS_PATH, DATE + '.md');
// /news/xxxxxxxx.json 文件
const NEWS_JSON_PATH = path.join(NEWS_PATH, DATE + '.json');
// /README.md 文件
const README_PATH = path.join(__dirname, 'README.md');
// /news/catalogue.json 文件
const CATALOGUE_JSON_PATH = path.join(NEWS_PATH, 'catalogue.json');
// 打印调试信息
console.log('DATE:', DATE);
console.log('NEWS_PATH:', NEWS_PATH);
console.log('NEWS_JSON_PATH:', NEWS_JSON_PATH);
console.log('README_PATH:', README_PATH);
console.log('CATALOGUE_JSON_PATH:', CATALOGUE_JSON_PATH);

/**
 * 读取文件
 * @param {String} path 需读取文件的路径
 * @returns {String} (Primise) 文件内容
 */
const readFile = path => {
	return new Promise((resolve, reject) => {
		fs.readFile(path, {}, (err, data) => {
			if (err) reject(err);
			resolve(data);
		});
	});
};

/**
 * 写入文件 (覆写)
 * @param {String} path 需写入文件的路径
 * @param {String} data 需写入的数据
 * @returns {*} (Primise)
 */
const writeFile = (path, data) => {
	return new Promise((resolve, reject) => {
		fs.writeFile(path, data, err => {
			if (err) reject(err);
			resolve(true);
		});
	});
};

/**
 * 判断文件是否存在
 * @param {String} filePath 文件路径
 * @returns {Boolean}
 */
const fileExists = filePath => fs.existsSync(filePath);

const normalizeText = text => text?.replace(/\s+/g, ' ').trim() || '';

const getDatePath = date => `${String(date).slice(0, 4)}/${String(date).slice(4, 6)}/${String(date).slice(6, 8)}`;

/**
 * 获取新闻列表
 * @param {String|Number} date 当前日期
 * @returns {Object} abstract为简介的链接, news为新闻链接数组
 */
const getNewsList = async date => {
	const HTML = await fetch(`http://tv.cctv.com/lm/xwlb/day/${date}.shtml`);
	const fullHTML = `<!DOCTYPE html><html><head></head><body>${HTML}</body></html>`;
	const dom = new JSDOM(fullHTML);
	const nodes = dom.window.document.querySelectorAll('a');
	const datePath = getDatePath(date);
	var videoLinks = [];
	nodes.forEach(node => {
		// 从dom节点获得href中的链接
		let link = node.href;
		if (!link || !link.includes('tv.cctv.com') || !link.includes(datePath) || !link.endsWith('.shtml')) return;
		// 如果已经有了就不再添加 (去重)
		if (!videoLinks.includes(link)) videoLinks.push(link);
	});
	const abstract = videoLinks.shift();
	if (!abstract || videoLinks.length === 0) {
		throw new Error(`未能从新闻列表页提取有效链接: ${date}`);
	}
	console.log('成功获取新闻列表');
	return {
		abstract,
		news: videoLinks
	}
}

/**
 * 获取新闻摘要 (简介)
 * @param {String} link 简介的链接
 * @returns {String} 简介内容
 */
const getAbstract = async link => {
	const HTML = await fetch(link);
	const dom = new JSDOM(HTML);
	const selectors = [
		'#page_body > div.allcontent > div.video18847 > div.playingCon > div.nrjianjie_shadow > div > ul > li:nth-child(1) > p',
		'.nrjianjie_shadow p',
		'.nrjianjie p',
		'#content_area p',
		'#content_area'
	];
	const abstractNode = selectors
		.map(selector => dom.window.document.querySelector(selector))
		.find(node => normalizeText(node?.textContent));
	if (!abstractNode) {
		throw new Error(`未找到新闻简介节点: ${link}`);
	}
	const abstract = abstractNode.innerHTML.replaceAll('；', "；\n\n").replaceAll('：', "：\n\n");
	console.log('成功获取新闻简介');
	return abstract;
}

/**
 * 获取新闻本体
 * @param {Array} links 链接数组
 * @returns {Object} title为新闻标题, content为新闻内容
 */
const getNews = async links => {
	const linksLength = links.length;
	console.log('共', linksLength, '则新闻, 开始获取');
	// 所有新闻
	var news = [];
	for (let i = 0; i < linksLength; i++) {
		const url = links[i];
		const html = await fetch(url);
		const dom = new JSDOM(html);
		const title = dom.window.document.querySelector('#page_body > div.allcontent > div.video18847 > div.playingVideo > div.tit')?.innerHTML?.replace('[视频]', '');
		const content = dom.window.document.querySelector('#content_area')?.innerHTML;
		news.push({ title, content, url });
		console.count('获取的新闻则数');
	}
	console.log('成功获取所有新闻');
	return news;
}

/**
 * 将数据处理为md格式
 * @param {Object} object date为获取的时间, abstract为新闻简介, news为新闻数组, links为新闻链接
 * @returns {String} 处理成功后的md文本
 */
const newsToMarkdown = ({ date, abstract, news, links }) => {
	// 将数据处理为md文档
	let mdNews = '';
	const newsLength = news.length;
	for (let i = 0; i < newsLength; i++) {
		const { title, content } = news[i];
		const link = news[i].url || links[i];
		mdNews += `### ${title}\n\n${content}\n\n[查看原文](${link})\n\n`;
	}
	return `# 《新闻联播》 (${date})\n\n## 新闻摘要\n\n${abstract}\n\n## 详细新闻\n\n${mdNews}\n\n---\n\n(更新时间戳: ${new Date().getTime()})\n\n`;
}

const saveTextToFile = async (savePath, text) => {
	// 输出到文件
	await writeFile(savePath, text);
}

const saveJsonToFile = async (savePath, data) => {
	await writeFile(savePath, JSON.stringify(data, null, 2));
}

const updateCatalogue = async ({ catalogueJsonPath, readmeMdPath, date, abstract }) => {
	// 更新 catalogue.json
	await readFile(catalogueJsonPath).then(async data => {
		data = data.toString();
		let catalogueJson = JSON.parse(data || '[]');
		catalogueJson = catalogueJson.filter(item => item.date !== date);
		catalogueJson.unshift({ date, abstract });
		let textJson = JSON.stringify(catalogueJson);
		await writeFile(catalogueJsonPath, textJson);
	});
	console.log('更新 catalogue.json 完成');
	// 更新 README.md
	await readFile(readmeMdPath).then(async data => {
		data = data.toString();
		if (data.includes(`- [${date}](./news/${date}.md)`)) {
			console.log('README.md 已存在当天目录, 跳过插入');
			return;
		}
		let text = data.replace('<!-- INSERT -->', `<!-- INSERT -->\n- [${date}](./news/${date}.md)`)
		await writeFile(readmeMdPath, text);
	});
	console.log('更新 README.md 完成');
}

const hasExistingTranscript = () => {
	const existingFiles = [NEWS_MD_PATH, NEWS_JSON_PATH].filter(fileExists);
	if (existingFiles.length > 0) {
		console.log(`检测到当天稿件已存在, 跳过抓取: ${existingFiles.join(', ')}`);
		return true;
	}
	return false;
}

const main = async () => {
	if (hasExistingTranscript()) {
		console.log('全部成功, 程序结束');
		return;
	}

	const newsList = await getNewsList(DATE);
	const abstract = await getAbstract(newsList.abstract);
	const news = await getNews(newsList.news);
	const md = newsToMarkdown({
		date: DATE,
		abstract,
		news,
		links: newsList.news
	});
	const structuredNews = {
		date: DATE,
		abstract,
		items: news.map(item => ({
			title: item.title,
			content: item.content,
			url: item.url,
		})),
		updatedAt: new Date().toISOString(),
	};

	await saveTextToFile(NEWS_MD_PATH, md);
	await saveJsonToFile(NEWS_JSON_PATH, structuredNews);

	if (!fileExists(CATALOGUE_JSON_PATH)) {
		await saveJsonToFile(CATALOGUE_JSON_PATH, []);
	}

	await updateCatalogue({
		catalogueJsonPath: CATALOGUE_JSON_PATH,
		readmeMdPath: README_PATH,
		date: DATE,
		abstract: abstract
	});
	console.log('全部成功, 程序结束');
}

await main();
