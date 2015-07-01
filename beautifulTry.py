import requests
from bs4 import BeautifulSoup
import re
import os
from html.parser import HTMLParser
import math

class BM25f:
	def __init__(self, *a, htmlPages = [], paths = [], urls = []):
		if htmlPages:
			self.htmlPages = htmlPages
		elif urls:
			self.htmlPages = self.get_html(urls)
		elif paths:
			htmlPages = []
			for path in paths:
				curPage = open(path, "r")
				htmlPages.append(curPage.read())
				curPage.close()
			self.htmlPages = htmlPages
		else:
			raise Exception("Can't get data!")
		self.pathOFDefaultTagWeights = os.path.dirname(os.path.realpath(__file__)) + "/tags_weights.txt"

	def get_html(self, urls):
		"""
		Return html-version of urls without js and css insertions
		"""
		htmlPages = []
		for url in urls:
			page = requests.get(url)
			soup = BeautifulSoup(page.text)
			for script in soup(["script", "style"]):
				script.extract()
			htmlPages.append(str(soup))
			# print(soup.get_text())
		return htmlPages

	def print_html_pages(self, symbToPrint = 100):
		"""
		Print first symbToPrint symbols of every html page
		"""
		for htmlPage in self.htmlPages:
			print(htmlPage[:symbToPrint] + "\n\nEnd - html - End\n\n")

	def include_tags(self, filePath = ""):
		if not filePath:
			filePath = self.pathOFDefaultTagWeights
		self.set_tag_weights(filePath)
		self.process_html()
		self.text_weighing()

	def set_tag_weights(self, filePath):
		"""
		Gets tags weights information and puts it into self.tagWeights
		"""
		tagWeights = {}
		totalWeight = 0
		for curRow in open(filePath):
			rowToParse = curRow.split()
			tagWeights[rowToParse[0].lower()] = int(rowToParse[1])
			totalWeight += int(rowToParse[1])
		for key in tagWeights:
			tagWeights[key] /= totalWeight
		self.tagWeights = tagWeights

	def process_html(self):
		"""
		Convert string versions of htmls to array of arrays of information about html pages content
		"""
		self.htmlContents = []
		class MyHTMLParser(HTMLParser):
			def __init__(self, *args, **kvargs):
				self.info = []
				super(MyHTMLParser, self).__init__(*args, **kvargs)
			def handle_starttag(self, tag, attrs):
				self.info.append(("start tag", tag.lower()))
			def handle_endtag(self, tag):
				self.info.append(("end tag", tag.lower()))
			def handle_data(self, data):
				self.info.append(("text", data.lower().strip()))
		for htmlPage in self.htmlPages:
			parser = MyHTMLParser()
			parser.feed(htmlPage)
			self.htmlContents.append(parser.info)

	def text_weighing(self):
		"""
		Mathching words of html pages with weights on using htmlWeights
		"""
		self.htmlsWordsWeights = []
		for htmlConent in self.htmlContents:
			currentWeight = 0
			htmlWei = []
			for oneMessage in htmlConent:
				if not oneMessage[1]:
					continue
				if oneMessage[0] == 'start tag':
					if oneMessage[1] in self.tagWeights:
						currentWeight += self.tagWeights[oneMessage[1]]
				elif oneMessage[0] == 'end tag':
					if oneMessage[1] in self.tagWeights:
						currentWeight -= self.tagWeights[oneMessage[1]]
				else:
					for word in oneMessage[1].split():
						htmlWei.append((word, currentWeight))
			self.htmlsWordsWeights.append(htmlWei)
		# print(self.htmlsWordsWeights)

	def get_needed_inf(self, query, tagsWeightCoef):
		"""
		Returns needed information about entries of queries in docs
		tagsWeightCoef impacts on tags weights effect
		"""
		docsInfo = []
		queryFin = [x for x in re.split('\W+', query.lower()) if x]

		for document in self.htmlsWordsWeights:
			docsInfo.append({'len': sum(len(x[0]) for x in document), 'meetCnt': []})
			for queryWord in queryFin:
				curQueryWordMeetCnt = 0
				for oneWordInfo in document:
					if oneWordInfo[0] == queryWord:
						curQueryWordMeetCnt += oneWordInfo[1] * tagsWeightCoef + 1
				docsInfo[-1]['meetCnt'].append(curQueryWordMeetCnt)
		return docsInfo

	def count_IDF(self, N, n):
		return max(math.log((N - n + 0.5) / (n + 0.5)), 0.0000001)

	def count_main_fraction(self, TF, k1, b, avgdl, docLen):
		return TF * (k1 + 1) / (TF + k1 * (1 - b + b * docLen / float(avgdl)))

	def count_score(self, docsInfo, avgdl, k1, b):
		"""
		Counting bm25 score of the document
		"""
		docScore = []
		for doc in docsInfo:
			curDocScore = 0
			for queryWord in range(len(doc['meetCnt'])):
				TF = float(doc['meetCnt'][queryWord])
				freaq = sum(1 for x in docsInfo if x['meetCnt'][queryWord])
				curDocScore += self.count_IDF(len(docsInfo), freaq) * self.count_main_fraction(TF, k1, b, avgdl, doc['len'])
			docScore.append(curDocScore)
		return docScore

	def bm25_algorithm(self, query, k1 = 2.0, b = 0.75, tagsWeightCoef = 1):
		"""
		Counting scores by bm25 algorithm for string query, returns list of scores
		"""
		docsInfo = self.get_needed_inf(query, tagsWeightCoef)
		#average document length
		avgdl = sum(sum(len(entry[0]) for entry in document) for document in self.htmlsWordsWeights) / float(len(docsInfo))
		# print(docsInfo)
		docScore = self.count_score(docsInfo, avgdl, k1, b)
		return docScore

if __name__ == "__main__":
	testQuery = ["https://en.wikipedia.org/wiki/Isaac_Newton", "https://en.wikipedia.org/wiki/Gottfried_Wilhelm_Leibniz", 
"https://en.wikipedia.org/wiki/Johann_Sebastian_Bach"]
	test = BM25f(urls = testQuery)
	test.include_tags()
	print(test.bm25_algorithm("mathematics"))