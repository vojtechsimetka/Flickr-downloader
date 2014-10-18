#!/usr/bin/env python

## Flickr image downloader using tags
# primary use: 3D Reconstruction of Historic Landmarks from Flickr Pictures
# @author xsimet00 Vojtech Simetka

import os
import sys
import urllib
import urllib2
import re
from HTMLParser import HTMLParser
from htmlentitydefs import name2codepoint

## Remove non ASCII characters from string
# @param text String possibly containing nonASCII characters
# @return Same string with nonASCII characters replaced by space
def removeNonASCII(text):
	return re.sub(r'[^\x00-\x7F]+',' ', text)

## Create URL for the tag
# @param tag Photos tag
# @return Flickr URL with for the tag
def createURLforTag(tag):
	return 'https://www.flickr.com/photos/tags/' + re.sub(r'[^a-z0-9]+','', tag.lower())

## Print help
def printHelp():
	print 'Flickr image downloader by tag \n'
	print 'Usage:'
	print '  ' + sys.argv[0] + ' [IMG_COUNT] [TAG]'
	print '    [IMG_COUNT]  Number of photos to be downloaded'
	print '    [TAG]        Images tag'

def isInteger(s):
	try:
		int(s)
		return True
	except ValueError:
		return False

## Parse the tag result page
class PageParser(HTMLParser):
	good_stuff_found = False
	td = 0
	image_link = False
	next_page = True
	link = ''
	next_link = ''
	image_list = []
	results = ''
	results_found = False;

	## Get link to next page with photos
	# @return Next pake link
	def getNextLink(self):
		tmp_link = self.next_link
		self.next_link=''
		return tmp_link

	## Get number of found images
	# @return Number of found images
	def getResultsCount(self):
		return self.results

	## Data handler
	# @param data Data between two tags
	def handle_data(self, data):
		if self.results_found:
			self.results = re.sub(r'[^0-9]','', data)
			self.results_found = False

	## Start tag handler
	# @param tag XML tag name
	# @param attrs List of pairs (attribut, value) for each tag
	def handle_starttag(self, tag, attrs):

		# Search for a <td id="GoodStuff"> which contains the images
		if tag == 'td':
			# Inside <td id="GoodStuff"> found another td, increase counter
			if self.good_stuff_found:
				self.td+=1

			# Not yet encountered <td id="GoodStuff">, check it
			else:
				for attr in attrs:
					if attr[0] == 'id' and attr[1] == 'GoodStuff':
						self.good_stuff_found = True

		# Search for a <td id="GoodStuff"> which contains the images
		elif tag == 'div':
			for attr in attrs:
				if attr[0] == 'class' and attr[1] == 'Results':
					self.results_found = True

		# Already in a <td id="GoodStuff"> get url addresses for images and next page
		elif self.good_stuff_found and tag == 'a':
			self.image_link = False
			self.next_page = False

			# Check if it is a potential image reference
			for attr in attrs:

				# It's an image thumbnail with link on it
				if attr[0] == 'data-track' and attr[1] == 'thumb':
					self.image_link = True

				# It's a next page button
				elif attr[0] == 'data-track' and attr[1] == 'next':
					self.next_page = True

				# Save the link value
				elif attr[0] == 'href':
					self.link = attr[1]

			# It's an image reference, append it to list of images
			if self.image_link:
				self.image_list.append(self.link)

			# It's a reference to next result page, save it
			elif self.next_page:
				self.next_link = self.link

	## End tag handler
	# @param tag XML tag name
	def handle_endtag(self, tag):

		# Found a </td>
		if tag == 'td' and self.good_stuff_found:

			# Enclosing tag for <td id="GoodStuff">, no more images
			if self.td == 0:
				self.good_stuff_found = False

			# Enclosing </td> tag inside <td id="GoodStuff">, decrement td counter
			else:
				self.td -=1

	## Retrieve a URL to image page
	# @return URL to page with image
	def getNextImage(self):
		return self.image_list.pop(0)

	## Check if all pictures from current folder were processed
	# @return True if image_list is empty
	def imagesEmpty(self):
		return not self.image_list

## Parse the one picture page
class ImageParser(HTMLParser):
	picture_found=False
	link=''
	picture_url=''

	## Start tag handler
	# @param tag XML tag name
	# @param attrs List of pairs (attribut, value) for each tag
	def handle_starttag(self, tag, attrs):

		# Search for a <img alt="photo" src="url">
		if tag == 'img':
			for attr in attrs:
				if attr[0] == 'alt' and attr[1] == 'photo':
					self.picture_found=True
				elif attr[0] == 'src':
					self.link=attr[1]

			if self.picture_found:
				self.picture_url = self.link
				self.picture_found=False

	## Get URL of the picture
	def getImageURL(self):
		return self.picture_url

## Image downloader, takes tag and iteratively parses flickr pages in search for photo
class ImageDownloader:
	image_count_requested = 0
	image_count_downloaded = 0
	page_parser = PageParser()
	image_parser = ImageParser()
	image_tag = 'none'
	url = ''

	## Constructor
	# @param img_req Number of images to be downloaded
	# @param tag Tag of the images
	def __init__(self, img_req, tag):
		self.image_count_requested = int(img_req)
		self.image_tag = re.sub(r'[^a-zA-Z0-9 ]+','', tag)
		self.url = createURLforTag(tag)
		if not os.path.exists('downloaded'):
			os.makedirs('downloaded')
		if not os.path.exists('downloaded/' + self.image_tag):
			os.makedirs('downloaded/' + self.image_tag)

	## Download images one by one from URL list generated by page parser
	def downloadImages(self):

		# While the URL list is not empty and not enough images was downloaded
		while not self.page_parser.imagesEmpty() and self.image_count_downloaded < self.image_count_requested:
			url = self.getHTML('https://www.flickr.com' + self.page_parser.getNextImage())
			self.image_parser.feed(url)

			# Replaces found url ending in order to download original sizes
			img_url = self.image_parser.getImageURL().replace('z.jpg', 'b.jpg')
			if img_url.endswith('?zz=1'):
				print str(self.image_count_downloaded+1) + ' Failed to download, continuing with next image'
				continue

			self.image_count_downloaded+=1
			print str(self.image_count_downloaded) + ' ' + img_url

			# Downloads the image and saves it
			urllib.urlretrieve(img_url, 'downloaded/' + self.image_tag + '/' + img_url.split('/', -1)[-1])

	## Get valid unicode HTML page from the url
	def getHTML(self, url):
		response = urllib2.urlopen(url)
		html = response.read()
		return removeNonASCII(html)

	## Download all pictures
	def download(self):
		print '\nAttempting to download ' + str(self.image_count_requested) + ' images with tag: ' + self.image_tag
		print '\nAccessing page: ' + self.url

		# Get list of image page URLs
		self.page_parser.feed(self.getHTML(self.url))

		print 'Found ' + self.page_parser.getResultsCount() + ' images, downloading:'

		# While not enough images were downloaded and there still are images to download
		while self.image_count_requested > self.image_count_downloaded and not self.page_parser.imagesEmpty():
			self.downloadImages()

			# Get list of image page URLs for next page
			if self.image_count_requested > self.image_count_downloaded:
				self.page_parser.feed(self.getHTML('https://www.flickr.com/' + self.page_parser.getNextLink()))

		print 'Downloaded: ' + str(self.image_count_downloaded) + ' of ' + str(self.image_count_requested) + ' requested'

# Parse arguments
if len(sys.argv) != 3 or not isInteger(sys.argv[1]):
	printHelp()
	exit(1)

# Download images
downloader = ImageDownloader(sys.argv[1], sys.argv[2])
downloader.download()
exit(0)

