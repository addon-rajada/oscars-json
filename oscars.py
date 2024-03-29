# -*- coding: utf-8 -*-
# Copyright (C) 2024 gbchr

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from pprint import pprint
from threadpool import indexed_threadpool
from tmdb import QuerySearch

cached_titles = {}
cached_hits = 0
total_searches = 0
total_found = 0
total_not_found = 0
invalid_year_results = []

def get_soup(year):
	headers = {
		'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
	}
	year_url = 'https://www.oscars.org/oscars/ceremonies/%s?qt-honorees=0#qt-honorees'
	response = requests.get(year_url % year, headers=headers)
	soup = BeautifulSoup(response.text, "html.parser")
	decoded = soup.encode('latin-1').decode('utf-8', errors='ignore')
	return BeautifulSoup(decoded, "html.parser")

def get_ids(title, year):

	global cached_titles, cached_hits, total_searches, invalid_year_results, total_found, total_not_found
	if title in cached_titles.keys():
		cached_hits += 1
		return cached_titles[title]

	query = '%s' % (title)
	response = QuerySearch('movie', query, int(year) - 1)
	total_searches += 1
	try:
		release = response['results'][0]['release_date']
		release_year = int(release[:4])
		result = {
			'id': response['results'][0]['id'],
			'original_title': response['results'][0]['original_title'],
			'title': response['results'][0]['title'],
			'release_date': release,
			'backdrop_path': response['results'][0]['backdrop_path'],
			'poster_path': response['results'][0]['poster_path'],
			'overview': response['results'][0]['overview'],
			'vote_average': response['results'][0]['vote_average'],
			'vote_count': response['results'][0]['vote_count'],
		}
		total_found += 1

		if release_year not in [int(year) + 1, int(year), int(year) - 1, int(year) - 2, int(year) - 3]: # check if is a valid movie result for given year. may occur outliers
			invalid_year_results.append({
				'title': title,
				'year': year,
				'result': result,
			})
			result = {'error': 'no ID found'}
			total_found -= 1
			total_not_found += 1
			
		cached_titles[title] = result
		#print(f"found {response['results'][0]['original_title']} for {title}")
	except:
		result = {'error': 'no ID found'}
		total_not_found += 1
		cached_titles[title] = result
	return result

def process_noms(id, nom, cat, year):
	l1 = nom.find('h4', {'class': 'field-content'}).getText().strip()
	l2 = nom.find('span', {'class': 'field-content'}).getText().strip()
	r = {
		'first_label': l1,
		'second_label': l2,
		'category': cat,
		'year': year,
		'tmdb': get_ids(l1, year) # l1 can be movie or person
	}
	return (id, r)

def year_data_by_film(year): # recent ceremonies doesn't have this tab, not using it
	soup = get_soup(year)
	by_film = soup.select('div.view-display-id-osc_honoree_by_film')[0]
	groups = by_film.find('div', {'class': 'view-content'}).find_all('div', {'class': 'view-grouping'}, recursive=False)
	for g in groups:
		films = g.find_all('div', {'class': 'view-grouping'}, recursive=True)
		for f in films:
			name = f.find('div', {'class': 'view-grouping-header'}).getText().strip()
			print(name)
			break
		break

def year_data_by_cat(id, year):
	soup = get_soup(year)
	by_cat = soup.select('div.view-display-id-osc_honoree_by_cat')[0]
	groups = by_cat.find('div', {'class': 'view-content'}).find_all('div', {'class': 'view-grouping'}, recursive=False)
	data_dict = {}
	for g in groups:
		cat = g.find('h2', recursive=True).getText().strip()
		data_dict[cat] = []
		noms = g.find_all('div', {'class': 'views-row'}, recursive=True)
		counter = 0
		result = indexed_threadpool(process_noms, [(nom,cat,year) for nom in noms], {'nom':0, 'cat':1, 'year':2})
		for r in result:
			r['winner'] = True if counter < 1 else False # first result is winner
			data_dict[cat].append(r)
			counter += 1
	return (id, (year, data_dict))

def main():

	global cached_hits, total_searches, invalid_year_results, total_found, total_not_found

	start_year = 1951
	end_year = 1971 #datetime.now().year + 1
	years = [[y] for y in range(start_year, end_year)]

	#final_result = {}
	result = indexed_threadpool(year_data_by_cat, years, {'year': 0}, show_progress=True, max_threads=10)
	for r in result:
		#final_result[r[0]] = r[1]
		with open('year/%s.json' % r[0], 'w') as f:
			j = json.dumps(r[1], indent=4)
			print(j, file = f)

		invalid_tmdb = [x for x in invalid_year_results if x['year'] == r[0]]
		if len(invalid_tmdb) > 0:
			with open('invalid_tmdb_results/%s.json' % r[0], 'w') as f:
				j = json.dumps(invalid_tmdb, indent=4)
				print(j, file = f)
	
	
	print(f'cached hits: {cached_hits}')
	print(f'total searches: {total_searches}')
	print(f'invalid year results: {len(invalid_year_results)}')
	print(f'total found: {total_found}')
	print(f'total not found: {total_not_found}')

	#with open('invalid_year_results.json', 'w') as fy:
	#	j = json.dumps(invalid_year_results, indent=4)
	#	print(j, file = fy)

	#with open('oscars.json', 'w') as fj:
	#	j = json.dumps(final_result, indent=4)
	#	print(j, file = fj)

main()
